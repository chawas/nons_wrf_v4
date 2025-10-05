#!/usr/bin/env python3

import os, subprocess, smtplib, socket, ssl, time, logging, zipfile, json
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import glob


# --- Start Message ---
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] AI WRF wrapper script started.")

# --- Load Configuration ---
CONFIG_FILE = "/home/wrf/deployed/nons_wrf_v4/auto/config_ai_wrapper.json"
with open(CONFIG_FILE, 'r') as f:
    cfg = json.load(f)

#SCRIPT_NAME_0000Z = cfg["SCRIPT_NAME_0000Z"]
SCRIPT_NAME_1200Z = cfg["SCRIPT_NAME_1200Z"]
SCRIPT_DIR = cfg["SCRIPT_DIR"]
script_path = os.path.join(SCRIPT_DIR, SCRIPT_NAME_1200Z)
DATA_DIR = cfg["DATA_DIR"]
LOGFILE_DIR = cfg["LOGFILE_DIR"]
PRODUCT_PATHS = cfg["PRODUCT_PATHS"]
EMAIL_CONFIG_FILE = cfg["EMAIL_CONFIG_FILE"]
ZIPPED_OUTPUT = cfg["ZIPPED_OUTPUT"]

# --- Setup Logging ---
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Match bash timestamp format
#shared_logfile = f"/home/wrf/nons/gfs-retrieval/logs/auto_production_{timestamp}.log"
prefix = "auto_production_"
shared_logfile = os.path.join(LOGFILE_DIR, f"{prefix}{timestamp}*.log")
logfile = shared_logfile  # Use same log file in Python

logging.basicConfig(filename=logfile, level=logging.INFO, format="%(asctime)s - %(message)s")


# --- Load Email Config ---
with open(EMAIL_CONFIG_FILE, 'r') as f:
    email_conf = json.load(f)

EMAIL_SENDER = email_conf["accounts"][0]["EMAIL_USER"]
EMAIL_PASSWORD = email_conf["accounts"][0]["EMAIL_PASS"]
EMAIL_RECEIVER = email_conf.get("recipients", [])

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465

# --- Helper Functions ---
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

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            print("📤 Email sent successfully via SSL.")
    except smtplib.SMTPException as e_ssl:
        print(f"SMTP_SSL failed: {e_ssl}")
        print("Trying TLS fallback...")
        try:
            with smtplib.SMTP(SMTP_SERVER, 587) as server:
                server.starttls(context=context)
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
                print("📤 Email sent successfully via TLS.")
        except Exception as e_tls:
            print(f"TLS fallback failed: {e_tls}")


def find_latest_log_for_today(log_dir, prefix="auto_production_"):
    today_str = datetime.utcnow().strftime("%Y%m%d")  # or local time if needed
    pattern = os.path.join(log_dir, f"{prefix}{today_str}*.log")

    log_files = glob.glob(pattern)
    if not log_files:
        return None

    # Sort by timestamp in filename
    def extract_datetime(filepath):
        filename = os.path.basename(filepath)
        timestamp_str = filename.replace(prefix, "").replace(".log", "")
        return datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")

    log_files.sort(key=extract_datetime, reverse=True)
    return log_files[0]  # latest



def zip_multiple_outputs(zip_path, folders=None, files=None):
    """
    Zip multiple folders and individual files into one archive.
    """
    folders = folders or []
    files = files or []

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for folder in folders:
            if not os.path.isdir(folder):
                logging.warning(f"Folder not found: {folder}")
                continue
            for root, _, filenames in os.walk(folder):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    arcname = os.path.relpath(file_path, os.path.dirname(folder))
                    zipf.write(file_path, arcname)

        for file_path in files:
            if os.path.isfile(file_path):
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname)
            else:
                logging.warning(f"File not found: {file_path}")
    return True






def run_bash_script(cfg):
    # SCRIPT_NAME_1200Z = cfg["SCRIPT_NAME_1200Z"]
    # SCRIPT_DIR = cfg["SCRIPT_DIR"]
    # script_path = os.path.join(SCRIPT_DIR, SCRIPT_NAME_1200Z)

    if not os.path.isfile(script_path):
        print(f"❌ Error: Bash script not found at {script_path}")
        return -1

    try:
        process = subprocess.Popen(
            [script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        print(f"❌ Error: Bash script found at {script_path}")
        for line in process.stdout:
            print(line, end='')

        process.wait()
        return process.returncode

    except KeyboardInterrupt:
        print("\n❌ Script interrupted by user (Ctrl+C).")
        process.terminate()
        return -1


# --- Main Logic ---
if __name__ == "__main__":
    STAMP_FILE = "/home/wrf/.ai_run_stamp"

    def already_ran_today(stamp_file):
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.isfile(stamp_file) and open(stamp_file).read().strip() == today

    def write_run_stamp(stamp_file):
        today = datetime.now().strftime("%Y-%m-%d")
        with open(stamp_file, 'w') as f:
            f.write(today)

    if already_ran_today(STAMP_FILE):
        print("✅ Already ran today. Exiting.")
        exit(0)

    # Wait until internet is restored
    while not is_connected():
        print("❌ No internet connection. Retrying in 10 minutes...")
        time.sleep(600)  # 5 minutes

    start_time = datetime.now()
    logging.info("AI wrapper WRF run started.")
    send_email("WRF-AM run started", f"WRF automation run started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}.")

    result = subprocess.run(['bash', script_path], capture_output=True, text=True)

    with open("output.txt", "w") as f:
        f.write(result.stdout)

    attachments = ["/tmp/wrf_am_run.log"]
    log_dir = "/home/wrf/nons/gfs-retrieval/logs"
    latest_log = find_latest_log_for_today(log_dir)

    folders_to_zip = [
        PRODUCT_PATHS["Symbograms"],
        PRODUCT_PATHS["Accumulated Precip"]
    ]
    log_files_to_zip = [latest_log] if latest_log else []

    if zip_multiple_outputs(ZIPPED_OUTPUT, folders=folders_to_zip, files=log_files_to_zip):
        attachments.append(ZIPPED_OUTPUT)

    end_time = datetime.now()
    duration = end_time - start_time
    summary = (
        f"WRF run finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')}.\n"
        f"Duration: {duration}.\n"
        f"Exit code: {result.returncode}.\n"
    )
    logging.info(summary)
    send_email("WRF-AM run completed", summary, attachments)

    # Record that the run has been completed
    write_run_stamp(STAMP_FILE)

