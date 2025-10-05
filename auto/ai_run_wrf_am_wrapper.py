#!/usr/bin/env python3
import os, subprocess, smtplib, socket, ssl, time, logging, zipfile, json, sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# --- Load Config ---
CONFIG_FILE = "/home/wrf/deployed/nons_wrf_v4/auto/config_ai_wrapper.json"
with open(CONFIG_FILE, 'r') as f:
    cfg = json.load(f)

SCRIPT_DIR = cfg["SCRIPT_DIR"]
SCRIPT_NAME_0000Z = os.path.join(SCRIPT_DIR, cfg["SCRIPT_NAME_0000Z"])
SCRIPT_NAME_1200Z = os.path.join(SCRIPT_DIR, cfg["SCRIPT_NAME_1200Z"])

LOGFILE_DIR = cfg["LOGFILE_DIR"]
PRODUCT_PATHS = cfg["PRODUCT_PATHS"]
EMAIL_CONFIG_FILE = cfg["EMAIL_CONFIG_FILE"]
ZIPPED_OUTPUT = cfg["ZIPPED_OUTPUT"]

# --- Load Email Config ---
with open(EMAIL_CONFIG_FILE, 'r') as f:
    email_conf = json.load(f)

EMAIL_SENDER = email_conf["accounts"][0]["EMAIL_USER"]
EMAIL_PASSWORD = email_conf["accounts"][0]["EMAIL_PASS"]
EMAIL_RECEIVER = email_conf.get("recipients", [])
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465


# --- Helpers ---
def is_connected():
    """Check internet connectivity."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False


def send_email(subject, body, attachments=[]):
    """Send an email notification with optional attachments."""
    if not is_connected():
        print("⚠️ No internet connection. Skipping email notification.")
        return
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = ", ".join(EMAIL_RECEIVER) if isinstance(EMAIL_RECEIVER, list) else EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    for path in attachments:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(path)}"'
                msg.attach(part)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)


def check_duplicate_instance():
    """Prevent multiple wrapper instances from running simultaneously."""
    import psutil
    current_pid = os.getpid()
    this_script = os.path.basename(__file__)
    for proc in psutil.process_iter(attrs=['pid', 'cmdline']):
        try:
            cmd = " ".join(proc.info['cmdline'])
            if proc.info['pid'] != current_pid and this_script in cmd:
                msg = (f"⚠️ Duplicate instance detected.\n\n"
                       f"Another ai_run_wrf_am_wrapper is already running.\n"
                       f"PID: {proc.info['pid']}\nCMD: {cmd}")
                print(msg)
                send_email("⚠️ Duplicate AI Wrapper Instance Detected", msg)
                sys.exit(0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def run_cycle(run_type, script_path, stamp_file):
    """Run one WRF cycle (AM or PM) and handle failure cases."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # --- Detect power failure / unclean restart ---
    if os.path.exists(stamp_file):
        with open(stamp_file, 'r') as f:
            last_run = f.read().strip()
        if last_run != today:
            send_email(
                "⚠️ Power Failure or Restart Detected",
                f"The system restarted or power was lost before completing the last WRF run.\n"
                f"Last incomplete run date: {last_run}"
            )
            os.remove(stamp_file)

    # --- Skip if already ran today ---
    if os.path.isfile(stamp_file) and open(stamp_file).read().strip() == today:
        print(f"✅ {run_type} already ran today. Skipping.")
        return

    # --- Wait for internet if needed ---
    retry_count = 0
    while not is_connected():
        retry_count += 1
        print("❌ No internet connection. Retrying in 10 mins...")
        if retry_count >= 6:  # after 1 hour
            send_email(
                f"❌ {run_type} Failed: No Internet",
                f"{run_type} failed to start due to no internet connection for over 1 hour."
            )
            sys.exit(1)
        time.sleep(600)

    # --- Start Run ---
    start_time = datetime.now(timezone.utc)
    send_email(f"{run_type} run started: ai_run_wrf_am_wrapper",
               f"{run_type} automation run started at {start_time} UTC")

    print(f"🚀 Starting {run_type} run using {script_path}")
    result = subprocess.run(['bash', script_path], capture_output=True, text=True)
    with open(f"output_{run_type}.txt", "w") as f:
        f.write(result.stdout + "\n" + result.stderr)

    # --- Detect failure of the bash script (e.g., data download error) ---
    if result.returncode != 0:
        send_email(
            f"❌ {run_type} Failed: Download or Script Error",
            f"{run_type} failed during execution.\n"
            f"Exit code: {result.returncode}\n"
            f"Possible causes: Internet loss, data download failure, or file corruption."
        )
        print(f"❌ {run_type} failed with exit code {result.returncode}")
        sys.exit(1)

    # --- Create ZIP of outputs ---
    folders_to_zip = [
        PRODUCT_PATHS["Symbograms"],
        PRODUCT_PATHS["Accumulated Precip"],
        PRODUCT_PATHS["Meteograms"]
    ]
    with zipfile.ZipFile(ZIPPED_OUTPUT, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder in folders_to_zip:
            if os.path.isdir(folder):
                for root, _, files in os.walk(folder):
                    for fn in files:
                        file_path = os.path.join(root, fn)
                        arcname = os.path.relpath(file_path, os.path.dirname(folder))
                        zipf.write(file_path, arcname)

    end_time = datetime.now(timezone.utc)
    duration = end_time - start_time
    summary = (
        f"{run_type} finished at {end_time} UTC\n"
        f"Duration: {duration}\n"
        f"Exit code: {result.returncode}"
    )

    send_email(f"{run_type} run completed successfully: ai_run_wrf_am_wrapper",
               summary, [ZIPPED_OUTPUT])

    with open(stamp_file, 'w') as f:
        f.write(today)

    print("✅ WRF run completed successfully. Exiting cleanly.")
    sys.exit(0)


# --- MAIN ---
if __name__ == "__main__":
    # --- Check for duplicate instance first ---
    try:
        import psutil
    except ImportError:
        print("Installing psutil for process detection...")
        subprocess.run([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil

    check_duplicate_instance()

    hour = datetime.now(timezone.utc).hour
    if 6 <= hour < 18:
        run_cycle("WRF_AM", SCRIPT_NAME_0000Z, "/home/wrf/.ai_run_stamp_AM")
    elif hour >= 18:
        run_cycle("WRF_PM", SCRIPT_NAME_1200Z, "/home/wrf/.ai_run_stamp_PM")
    else:
        print("🌙 No valid run window right now. Exiting.")
        sys.exit(0)
