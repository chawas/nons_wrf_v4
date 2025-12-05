#!/usr/bin/env python3
# ai_run_wrf_wrapper.py
# Fully integrated wrapper for WRF automation with enhanced GFS retrieval logging.

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

# Add console handler for real-time output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.info("=== Starting full WRF production and FTP sequence ===")

# Load additional configuration
PRODUCT_PATHS = cfg["PRODUCT_PATHS"]
EMAIL_CONFIG_FILE = cfg["EMAIL_CONFIG_FILE"]
ZIPPED_OUTPUT = cfg["ZIPPED_OUTPUT"]

# Max attachment size to allow (bytes). Gmail limit ~25MB; use slightly smaller.
MAX_ATTACH_BYTES = 24 * 1024 * 1024  # 24 MB


# ===========================================================
# ERROR CODES
# ===========================================================
ERROR_CODES = {
    14: "Plotting error",

    15: "Data extraction error",
    13: "FTP connection error",
    17: "Missing GRIB/NetCDF file",
    18: "Corrupted file format",
    19: "WRF executable error",
    20: "Post-processing error",
    21: "Raster interpolation error",
    22: "GFS download failed",
    23: "Directory not found",
    24: "Permission denied",
    99: "Unknown fatal error"
}


# Email setup
with open(EMAIL_CONFIG_FILE, "r") as f:
    email_conf = json.load(f)

EMAIL_SENDER = email_conf["accounts"][0]["EMAIL_USER"]
EMAIL_PASSWORD = email_conf["accounts"][0]["EMAIL_PASS"]
EMAIL_RECEIVER = email_conf.get("recipients", [])
SMTP_SERVER = email_conf.get("smtp_server", "smtp.gmail.com")
SMTP_PORT = int(email_conf.get("smtp_port", 465))

def print_fatal(e: Exception):
    logger.critical("❌ FATAL ERROR in wrapper: %s", str(e))
    logger.critical(traceback.format_exc())
    sys.exit(1)

# ===========================================================
# GFS DATA RETRIEVAL WITH ENHANCED LOGGING
# ===========================================================
def setup_gfs_retrieval():
    """Setup and import the GFS retrieval module with enhanced logging"""
    try:
        retriever_path = cfg["SCRIPT_RETRIEVE"]
        retriever_dir = os.path.dirname(retriever_path)

        logger.info("Setting up GFS retrieval module...")
        logger.info("Retriever path: %s", retriever_path)
        logger.info("Retriever directory: %s", retriever_dir)

        if retriever_dir not in sys.path:
            sys.path.insert(0, retriever_dir)
            logger.debug("Added %s to Python path", retriever_dir)

        module_name = "retrieve_gfs_data"
        logger.info("Importing module: %s", module_name)

        spec = importlib.util.spec_from_file_location(module_name, retriever_path)
        if spec is None:
            raise ImportError(f"Could not create spec from {retriever_path}")

        retrieve_module = importlib.util.module_from_spec(spec)

        # Add logger to the module before execution so it can use it
        retrieve_module.logger = logger

        spec.loader.exec_module(retrieve_module)
        logger.info("✅ GFS retriever module imported successfully")

        return retrieve_module

    except Exception as e:
        logger.error("❌ Failed to setup GFS retrieval module: %s", str(e))
        logger.debug(traceback.format_exc())
        raise

def run_gfs_retrieval(retrieve_module, cycle):
    """Run GFS data retrieval with comprehensive logging"""
    logger.info("🚀 Starting GFS data retrieval for cycle %s", cycle)
    start_time = datetime.now(timezone.utc)

    try:
        # Check if the retrieve function exists and is callable
        if not hasattr(retrieve_module, 'retrieve_gfs_data'):
            raise AttributeError("retrieve_gfs_data function not found in module")

        if not callable(retrieve_module.retrieve_gfs_data):
            raise TypeError("retrieve_gfs_data is not callable")

        logger.info("Calling retrieve_gfs_data()...")

        # Pass the logger to the retrieval function
        result = retrieve_module.retrieve_gfs_data(logger=logger)

        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time

        if result:
            logger.info("✅ GFS data retrieval completed successfully")
            logger.info("⏱️  Retrieval duration: %s", duration)
        else:
            logger.error("❌ GFS data retrieval failed")

        return result

    except Exception as e:
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        logger.error("❌ GFS data retrieval failed after %s", duration)
        logger.error("Error details: %s", str(e))
        logger.debug(traceback.format_exc())
        return False

# ===========================================================
# UTILITIES
# ===========================================================
def is_connected():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False





# ---------- Replace send_email() with this robust version ----------
def send_email(subject, body, attachments=None):
    """
    Send email but filter attachments that exceed MAX_ATTACH_BYTES.
    If attachments are too big, send only small ones (preferably logs) and
    mention the large files in the message body.
    """
    if not is_connected():
        logger.warning("No internet connection. Skipping email.")
        return False

    attachments = attachments or []
    small_attach = []
    large_attach = []

    for path in attachments:
        try:
            if not os.path.exists(path):
                logger.debug("Attachment not found: %s", path)
                continue
            size = os.path.getsize(path)
            if size <= MAX_ATTACH_BYTES:
                small_attach.append(path)
            else:
                large_attach.append((path, size))
        except Exception as e:
            logger.warning("Could not stat attachment %s: %s", path, e)

    # If no small attachments, try to prefer the main LOG_FILE if present
    if not small_attach and os.path.exists(LOG_FILE):
        if os.path.getsize(LOG_FILE) <= MAX_ATTACH_BYTES:
            small_attach.append(LOG_FILE)
        else:
            # If even log is big, do not attach anything
            logger.warning("Log file too large to attach (%s bytes). Will not attach files.", os.path.getsize(LOG_FILE))

    # Augment body to list any large files we didn't attach
    if large_attach:
        body += "\n\nNote: The following attachments were omitted due to size limits:\n"
        for p, s in large_attach:
            body += f" - {p} ({s//1024//1024} MB)\n"
        body += "\nYou can fetch them from the server directly.\n"

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = ", ".join(EMAIL_RECEIVER) if isinstance(EMAIL_RECEIVER, list) else EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    for path in small_attach:
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
        return True
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False




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

def get_error_message(return_code):
    """
    Returns a descriptive error message based on exit code.
    """
    return ERROR_CODES.get(return_code, f"Unknown error (code {return_code})")


def handle_failure(run_type, result, start_time, reason="No access to FTP Server", gfs_stamp=None, today=None):
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

def check_gfs_data_status(gfs_dir, today):
    """Check GFS data status and return appropriate action"""
    gfs_stamp = os.path.join(gfs_dir, "logs", "gfs_downloaded_today.stamp")
    data_dir = os.path.join(gfs_dir, "local_outdata")

    # Check if stamp exists and is for today
    if os.path.exists(gfs_stamp):
        try:
            with open(gfs_stamp, "r") as f:
                stamp_date = f.read().strip()
            if stamp_date == today:
                logger.info("✅ GFS data already downloaded today (%s)", today)
                return "skip"  # Skip downloading, proceed to production
        except Exception as e:
            logger.warning("Could not read GFS stamp file: %s", e)

    # Check if data directory exists and has GFS files
    if os.path.exists(data_dir) and os.path.isdir(data_dir):
        # Look for GFS files with the expected pattern: *gfs_global.grb2f*
        gfs_files = [f for f in os.listdir(data_dir) if 'gfs_global.grb2f' in f]

        if gfs_files:
            logger.info("Found %d existing GFS files, will check completeness", len(gfs_files))
            logger.debug("Sample files: %s", gfs_files[:3])  # Log first 3 files for debugging
            return "resume"  # Resume download for missing/incomplete files
        else:
            logger.info("Data directory exists but contains no GFS files, starting fresh download")
            # Debug: list what files ARE there
            all_files = os.listdir(data_dir)
            if all_files:
                logger.debug("Files in directory (non-GFS): %s", all_files[:5])  # First 5 files
            return "download"  # Start fresh download
    else:
        logger.info("No GFS data directory found, starting fresh download")
        return "download"  # Start fresh download

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
        if script_path in " ".join(p.info.get("cmdline", []))
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

    # 4️⃣ Check GFS data status and run retrieval if needed
    gfs_dir = "/home/wrf/deployed/nons_wrf_v4/gfs-retrieval"
    cycle = os.getenv("WRF_CYCLE", "00")
    gfs_status = check_gfs_data_status(gfs_dir, today)

    if gfs_status == "skip":
        logger.info("Skipping GFS download - data already available")
    else:
        logger.info("GFS data status: %s - running retrieval", gfs_status)
        start_gfs = datetime.now(timezone.utc)

        try:
            # Setup and run GFS retrieval with enhanced logging
            retrieve_module = setup_gfs_retrieval()
            success = run_gfs_retrieval(retrieve_module, cycle)

            if not success:
                class MockResult:
                    def __init__(self):
                        self.returncode = 1
                        self.stdout = "GFS retrieval failed - see main log for details"
                        self.stderr = "GFS retrieval failed - see main log for details"

                result = MockResult()
                gfs_stamp_file = os.path.join(gfs_dir, "logs", "gfs_downloaded_today.stamp")
                reason = get_error_message(result.returncode)

                handle_failure(
                    run_type,
                    result,
                    start_gfs,
                    reason,
                    gfs_stamp_file,
                    today
                )

        except Exception as e:
            logger.error("❌ GFS retrieval setup failed: %s", str(e))
            class MockResult:
                def __init__(self):
                    self.returncode = 1
                    self.stdout = f"GFS retrieval setup failed: {str(e)}"
                    self.stderr = traceback.format_exc()

            gfs_stamp_file = os.path.join(gfs_dir, "logs", "gfs_downloaded_today.stamp")
            handle_failure(run_type, MockResult(), start_gfs, "GFS download setup failed", gfs_stamp_file, today)

    # 5️⃣ Run WRF within virtualenv
    start_time = datetime.now(timezone.utc)
    logger.info("Starting WRF production with available GFS data")
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
        gfs_stamp_file = os.path.join(gfs_dir, "logs", "gfs_downloaded_today.stamp")
        handle_failure(run_type, r, start_time, "No access to FTP Server", gfs_stamp_file, today)


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