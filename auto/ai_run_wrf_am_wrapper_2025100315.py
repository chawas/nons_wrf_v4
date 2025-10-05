#!/usr/bin/env python3
import os, subprocess, smtplib, socket, ssl, time, zipfile, json, sys
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
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

def send_email(subject, body, attachments=[]):
    if not is_connected():
        print("⚠️ No internet connection. Skipping email.")
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

# --- Main cycle runner ---
def run_cycle(run_type, script_path, stamp_file):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Skip if already ran today
    if os.path.isfile(stamp_file) and open(stamp_file).read().strip() == today:
        print(f"✅ {run_type} already ran today. Skipping.")
        return

    # Wait for internet if needed
    while not is_connected():
        print("❌ No internet connection. Retrying in 10 mins...")
        time.sleep(600)

    start_time = datetime.now(timezone.utc)
    send_email(f"{run_type} run started", f"{run_type} automation run started at {start_time} UTC")

    # Run the bash script (which runs the downloader)
    result = subprocess.run(['bash', script_path], capture_output=True, text=True)

    # Save output to log file
    log_file = f"output_{run_type}.txt"
    with open(log_file, "w") as f:
        f.write(result.stdout)
        f.write(result.stderr)

    # --- Handle failures ---
    if result.returncode != 0:
        fail_time = datetime.now(timezone.utc)
        summary = (
            f"❌ {run_type} FAILED at {fail_time} UTC\n"
            f"Exit code: {result.returncode}\n\n"
            f"Possible causes:\n"
            f"- Internet outage\n"
            f"- Remote server unreachable\n"
            f"- Local script error\n\n"
            f"Check attached log for details."
        )
        print(summary)
        send_email(f"{run_type} run FAILED", summary, [log_file])
        return  # 🚨 Stop here, do not proceed

    # --- If success: create zip of products ---
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
        f"✅ {run_type} finished at {end_time} UTC\n"
        f"Duration: {duration}\n"
        f"Exit code: {result.returncode}"
    )
    print(summary)
    send_email(f"{run_type} run completed", summary, [ZIPPED_OUTPUT])

    # --- Write stamp only if successful ---
    with open(stamp_file, 'w') as f:
        f.write(today)

# --- MAIN ---
if __name__ == "__main__":
    hour = datetime.now(timezone.utc).hour
    # Run 0000Z cycle if between 06–18 UTC
    if 6 <= hour < 18:
        run_cycle("WRF_AM", SCRIPT_NAME_0000Z, "/home/wrf/.ai_run_stamp_AM")
    # Run 1200Z cycle if after 18 UTC
    elif hour >= 18:
        run_cycle("WRF_PM", SCRIPT_NAME_1200Z, "/home/wrf/.ai_run_stamp_PM")
