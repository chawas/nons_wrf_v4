#!/usr/bin/env python3
# ai_run_wrf_wrapper.py
# Fully integrated wrapper for WRF automation with environment activation and 30-min wait logic.

import json
import os
import psutil
import smtplib
import socket
import ssl
import subprocess
import sys
import time
import zipfile
import logging
import traceback
import shutil
import importlib.util
from datetime import datetime, timezone, UTC
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ===========================================================
# CONFIG
# ===========================================================
CONFIG_FILE = "/home/wrf/deployed/nons_wrf_v4/auto/config_ai_wrapper.json"
with open(CONFIG_FILE, "r") as f:
    cfg = json.load(f)

SCRIPT_DIR = cfg["SCRIPT_DIR"]

SCRIPT_NAME_0000Z = os.path.join(SCRIPT_DIR, cfg["SCRIPT_NAME_0000Z"])
SCRIPT_NAME_1200Z = os.path.join(SCRIPT_DIR, cfg["SCRIPT_NAME_1200Z"])

# === Configure single shared logger ===
LOGFILE_DIR = "/home/wrf/deployed/nons_wrf_v4/logs"
os.makedirs(LOGFILE_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGFILE_DIR, f"ai_wrapper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
logger.info("=== Starting full WRF production and FTP sequence ===")


try:
    retriever_path = cfg["SCRIPT_RETRIEVE"]
    retriever_dir = os.path.dirname(retriever_path)

    if retriever_dir not in sys.path:
        sys.path.insert(0, retriever_dir)

    module_name = "retrieve_gfs_data"

    spec = importlib.util.spec_from_file_location(module_name, retriever_path)
    retrieve_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(retrieve_module)

    logger.info("Retriever module imported successfully.")

except Exception as e:
    print_fatal(e)
# Run it
retrieve_module.retrieve_gfs_data(logger)






PRODUCT_PATHS = cfg["PRODUCT_PATHS"]
EMAIL_CONFIG_FILE = cfg["EMAIL_CONFIG_FILE"]
ZIPPED_OUTPUT = cfg["ZIPPED_OUTPUT"]

# Email setup
with open(EMAIL_CONFIG_FILE, "r") as f:
    email_conf = json.load(f)

EMAIL_SENDER = email_conf["accounts"][0]["EMAIL_USER"]
EMAIL_PASSWORD = email_conf["accounts"][0]["EMAIL_PASS"]
EMAIL_RECEIVER = email_conf.get("recipients", [])
SMTP_SERVER = email_conf.get("smtp_server", "smtp.gmail.com")
SMTP_PORT = int(email_conf.get("smtp_port", 465))

# ===========================================================
# LOGGING
# ===========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ai_wrapper")


def print_fatal(e: Exception):
    print("❌ FATAL ERROR in wrapper:", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)


# ===========================================================
# UTILITIES
# ===========================================================
def is_connected():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

def send_email(subject, body, attachments=None):
    if not is_connected():
        logger.warning("No internet connection. Skipping email.")
        return
    attachments = attachments or []
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = ", ".join(EMAIL_RECEIVER) if isinstance(EMAIL_RECEIVER, list) else EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    for path in attachments:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(path))
                    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
                    msg.attach(part)
            except Exception as e:
                logger.warning("Could not attach %s: %s", path, e)
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info("Email sent: %s", subject)
    except Exception as e:
        logger.error("Failed to send email: %s", e)

def kill_associated_processes_by_keyword(keywords):
    killed = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline", []))
            if any(k in cmdline for k in keywords):
                logger.warning("Terminating leftover process %s (%s)", proc.pid, cmdline)
                try:
                    proc.terminate()
                    killed.append(proc.pid)
                except Exception:
                    proc.kill()
                    killed.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return killed

def clean_output_dirs():
    for folder in PRODUCT_PATHS.values():
        if os.path.isdir(folder):
            logger.info("Cleaning %s", folder)
            for root, _, files in os.walk(folder):
                for fn in files:
                    try:
                        os.remove(os.path.join(root, fn))
                    except Exception:
                        pass

def create_zip_archive():
    try:
        logger.info("Creating ZIP archive: %s", ZIPPED_OUTPUT)
        with zipfile.ZipFile(ZIPPED_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zipf:
            for folder in PRODUCT_PATHS.values():
                if os.path.isdir(folder):
                    for root, _, files in os.walk(folder):
                        for fn in files:
                            file_path = os.path.join(root, fn)
                            arcname = os.path.relpath(file_path, os.path.dirname(folder))
                            zipf.write(file_path, arcname)
        return True
    except Exception as e:
        logger.error("Failed to create ZIP archive: %s", e)
        return False

# ===========================================================
# ERROR HANDLERS
# ===========================================================
def handle_failure(run_type, result, start_time, reason="WRF run failed", gfs_stamp=None, today=None):
    """
    Handles a failure during the WRF wrapper run:
    - Logs and emails the failure summary
    - Optionally writes a failure stamp
    - Cleans up processes and output directories
    - Exits with code 99
    """
    end_time = datetime.now(timezone.utc)
    duration = end_time - start_time

    stdout_tail = (result.stdout[-1200:] if result and getattr(result, "stdout", None) else "")
    stderr_tail = (result.stderr[-1200:] if result and getattr(result, "stderr", None) else "")

    body = (
        f"❌ {run_type} {reason}\n"
        f"Finished at: {end_time} UTC\nDuration: {duration}\n"
        f"Exit code: {getattr(result, 'returncode', 'N/A')}\n\n"
        f"STDOUT (tail):\n{stdout_tail}\n\nSTDERR (tail):\n{stderr_tail}"
    )

    logger.error(body)

    # 📦 Create ZIP archive for logs/output
    create_zip_archive()

    # 📧 Send email notification
    send_email(f"{run_type} FAILED: {reason}", body, [ZIPPED_OUTPUT, LOG_FILE])

    # 🧾 Write failure stamp if stamp file path is available
    if gfs_stamp:
        try:
            with open(gfs_stamp, "w") as f:
                f.write(today or datetime.now(timezone.utc).strftime("%Y%m%d"))
            logger.warning("Failure stamp written to %s", gfs_stamp)
        except Exception as e:
            logger.error("Could not write failure stamp: %s", e)

    # 🧹 Cleanup
    kill_associated_processes_by_keyword(["nons_wrf_v4", "auto_zimbabwe_local_"])
    clean_output_dirs()

    logger.warning("❌ WRF wrapper terminated due to failure.")
    sys.exit(99)


# ===========================================================
# CORE LOGIC
# ===========================================================
def determine_cycle():
    cycle = os.getenv("WRF_CYCLE")
    if cycle:
        logger.info("Using preset WRF_CYCLE=%s", cycle)
    else:
        hour = datetime.now(timezone.utc).hour
        cycle = "00" if hour < 16 else "12"
        os.environ["WRF_CYCLE"] = cycle
        logger.info("Calculated WRF_CYCLE=%s (UTC hour=%s)", cycle, hour)
    return cycle






def run_cycle(run_type, script_path, stamp_file):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")


    output_log = os.path.join(
        LOGFILE_DIR,
        f"output_{run_type}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.txt"
    )

    venv_python = "/home/wrf/deployed/nons_wrf_v4/nons_env/bin/python"
    venv_activate = "/home/wrf/deployed/nons_wrf_v4/nons_env/bin/activate"

    logger.info("Starting run_cycle: %s", run_type)
    logger.info("Output log: %s", output_log)

    # 1️⃣ Skip if already done today
    if os.path.isfile(stamp_file) and open(stamp_file).read().strip() == today:
        msg = f"{run_type} already completed today ({today})."
        logger.info(msg)
        send_email(f"{run_type} skipped", msg, [LOG_FILE])
        return

    # 2️⃣ Check for duplicate processes
    same_procs = [
        p for p in psutil.process_iter(["pid", "cmdline"])
        if any(script_path in " ".join(p.info.get("cmdline", [])) for _ in [0])
    ]
    if same_procs:
        logger.warning("Existing %s process detected. Waiting 30 minutes...", run_type)
        send_email(f"{run_type} waiting", f"Detected {len(same_procs)} process(es). Waiting 30 min.")
        for i in range(30):
            logger.info("⏳ Still running (%d/30 min)...", i + 1)
            time.sleep(60)
        still_running = [p for p in same_procs if psutil.pid_exists(p.pid)]
        if still_running:
            logger.warning("⛔ Still running after 30 minutes — terminating now.")
            for p in still_running:
                try:
                    p.terminate()
                except Exception:
                    p.kill()
            time.sleep(10)

    # 3️⃣ Ensure internet connectivity
    while not is_connected():
        logger.warning("No internet connection; retrying in 10 minutes.")
        time.sleep(600)

    # 4️⃣ Ensure GFS data present
    gfs_dir = "/home/wrf/deployed/nons_wrf_v4/gfs-retrieval"
    gfs_stamp = os.path.join(gfs_dir, "logs", "gfs_downloaded_today.stamp")
    cycle = os.getenv("WRF_CYCLE", "00")
    retriever = f"{gfs_dir}/retrieve_gfs_data_{'0000Z' if cycle == '00' else '1200Z'}.py"

    if not (os.path.isfile(gfs_stamp) and open(gfs_stamp).read().strip() == today):
        logger.info("⚠️ GFS data missing — downloading now...")
        start_gfs = datetime.now(timezone.utc)

        r = subprocess.run(
            [venv_python, retriever],
            capture_output=True,
            text=True,
            cwd=gfs_dir,
            env=os.environ
        )

        with open(output_log, "a") as f:
            f.write("\n--- GFS STDOUT ---\n" + (r.stdout or "") + "\n--- GFS STDERR ---\n" + (r.stderr or ""))

        if r.returncode == 0:
            try:
                with open(gfs_stamp, "w") as f:
                    f.write(today)
                logger.info("✅ GFS data ready and stamp written.")
            except Exception as e:
                logger.warning("GFS data downloaded but could not write stamp: %s", e)
        else:
            handle_failure(run_type, r, start_gfs, "GFS download failed", gfs_stamp, today)
    else:
        logger.info("✅ GFS data already present for today.")

    # 5️⃣ Run WRF within virtualenv
    start_time = datetime.now(timezone.utc)
    send_email(f"{run_type} started", f"Started at {start_time} UTC")

    bash_command = f"source {venv_activate} && bash {script_path}"
    r = subprocess.run(
        ["bash", "-c", bash_command],
        capture_output=True,
        text=True,
        env=os.environ
    )

    with open(output_log, "a") as f:
        f.write("\n--- WRF STDOUT ---\n" + (r.stdout or "") + "\n--- WRF STDERR ---\n" + (r.stderr or ""))

    if r.returncode == 0:
        with open(stamp_file, "w") as f:
            f.write(today)
        create_zip_archive()
        send_email(f"{run_type} completed", f"✅ Completed successfully.", [LOG_FILE, output_log, ZIPPED_OUTPUT])
        kill_associated_processes_by_keyword(["nons_wrf_v4"])
        clean_output_dirs()
        sys.exit(0)
    else:
        handle_failure(run_type, r, start_time, "WRF run failed", gfs_stamp, today)










# ===========================================================
# MAIN
# ===========================================================
if __name__ == "__main__":
    try:
        cycle = determine_cycle()
        if cycle == "00":
            run_cycle("WRF_AM_ai", SCRIPT_NAME_0000Z, "/home/wrf/.ai_run_stamp_AM")
        else:
            run_cycle("WRF_PM_ai", SCRIPT_NAME_0000Z, "/home/wrf/.ai_run_stamp_PM")
    except Exception as e:
        logger.exception("Critical wrapper exception: %s", e)
        send_email("❌ Wrapper Crash", str(e), [LOG_FILE])
        kill_associated_processes_by_keyword(["nons_wrf_v4"])
        clean_output_dirs()
        sys.exit(99)
