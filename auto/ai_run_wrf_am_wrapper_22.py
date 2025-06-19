#!/usr/bin/env python3

import os, subprocess, smtplib, socket, ssl, time, logging, zipfile, json
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# --- Start Message ---
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] AI WRF wrapper script started.")

# --- Load Configuration ---
CONFIG_FILE = "/home/wrf/nons/auto/config_ai_wrapper.json"
with open(CONFIG_FILE, 'r') as f:
    cfg = json.load(f)

SCRIPT_NAME = cfg["SCRIPT_NAME"]
SCRIPT_DIR = cfg["SCRIPT_DIR"]
script_path = os.path.join(SCRIPT_DIR, SCRIPT_NAME)
DATA_DIR = cfg["DATA_DIR"]
LOGFILE_DIR = cfg["LOGFILE_DIR"]
PRODUCT_PATHS = cfg["PRODUCT_PATHS"]
EMAIL_CONFIG_FILE = cfg["EMAIL_CONFIG_FILE"]
ZIPPED_OUTPUT = cfg["ZIPPED_OUTPUT"]

# --- Setup Logging ---
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
logfile = os.path.join(LOGFILE_DIR, f"auto_zim_am2_{timestamp}.log")
os.makedirs(LOGFILE_DIR, exist_ok=True)
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

def zip_symbogram_output(output_dir, zip_path):
    if not os.path.isdir(output_dir):
        logging.warning(f"No symbograms found in: {output_dir}")
        return False
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(output_dir):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, output_dir)
                zipf.write(file_path, arcname=arcname)
    return True





def run_bash_script(cfg):
    SCRIPT_NAME = cfg["SCRIPT_NAME"]
    SCRIPT_DIR = cfg["SCRIPT_DIR"]
    script_path = os.path.join(SCRIPT_DIR, SCRIPT_NAME)

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
    start_time = datetime.now()
    logging.info("AI wrapper WRF run started.")

    if is_connected():
        send_email("WRF-AM run started", f"WRF automation run started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    else:
        print("⏩ Skipping start email due to no internet.")

    result = subprocess.run(['bash', script_path], capture_output=True, text=True)

    with open("output.txt", "w") as f:
        f.write(result.stdout)

    attachments = ["/tmp/wrf_am_run.log"]

    if zip_symbogram_output(PRODUCT_PATHS["Symbograms"], ZIPPED_OUTPUT):
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
