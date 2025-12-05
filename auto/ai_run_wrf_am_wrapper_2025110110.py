from auto.backup.ai_run_wrf_am_wrapper_2025110310 import handle_failure

#!/usr/bin/env python3
"""
AI_RUN_WRF_AM_WRAPPER
------------------------------------------------------------
Controls daily WRF automation:
  • Checks for existing processes
  • Waits up to 30 min for previous run
  • Verifies GFS data stamp (downloads if missing)
  • Runs the bash automation pipeline
  • Handles logging and cleanup
------------------------------------------------------------
"""

import os
import time
import subprocess
import psutil
import logging
from datetime import datetime, timezone, timedelta

# --------------------------------------------------------
#  CONFIGURATION
# --------------------------------------------------------
BASE_DIR = "/home/wrf/deployed/nons_wrf_v4"
GFS_DIR = f"{BASE_DIR}/gfs-retrieval"
STAMP_FILE = os.path.join(GFS_DIR, f".downloaded_{datetime.utcnow():%y%m%d00}00")
LOCAL_OUTDATA = os.path.join(GFS_DIR, "local_outdata")
BASH_SCRIPT = f"{GFS_DIR}/auto_production.sh"
LOG_DIR = os.path.join(GFS_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"output_WRF_AM_ai_{datetime.utcnow():%Y%m%d_%H%M%S}.txt")

# --------------------------------------------------------
#  LOGGING
# --------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger("WRF_AI_WRAPPER")

# --------------------------------------------------------
#  UTILITY FUNCTIONS
# --------------------------------------------------------
def find_existing_processes(name):
    """Return list of running processes containing the given name."""
    matches = []
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            if p.info["cmdline"] and name in " ".join(p.info["cmdline"]):
                matches.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return matches


def wait_or_kill_existing(max_wait_minutes=10):
    """Wait up to `max_wait_minutes` for previous run, then terminate."""
    existing_procs = find_existing_processes("ai_run_wrf_am_wrapper_2025110310.py")

    if not existing_procs:
        logger.info("✅ No existing WRF_AM_ai process detected.")
        return

    logger.warning("⚠️ Existing WRF_AM_ai process detected. Waiting up to %d minutes...", max_wait_minutes)
    waited = 0
    while waited < max_wait_minutes:
        time.sleep(60)
        waited += 5
        still_running = find_existing_processes("ai_run_wrf_am_wrapper_2025110310.py")
        if not still_running:
            logger.info("✅ Previous process finished after %d minutes. Continuing new run.", waited)
            return
        logger.info("⏳ Still running (%d/%d min)...", waited, max_wait_minutes)

    # If still running after timeout, terminate
    if still_running:
        logger.warning("⛔ Still running after %d minutes — terminating now.", max_wait_minutes)
    current_pid = os.getpid()
    for p in still_running:
        if p.pid == current_pid:
            continue  # skip self
        try:
            logger.warning("Killing old PID %d (%s)", p.pid, " ".join(p.cmdline()))
            p.terminate()
            p.wait(timeout=10)
        except Exception as e:
            logger.error("Failed to terminate PID %d: %s", p.pid, e)
    logger.info("✅ Old process terminated. Proceeding with new run.")



def ensure_gfs_data_ready():
    """Ensure stamp file and GFS data exist; download if missing."""
    logger.info("🔍 Checking for GFS data stamp file...")
    if os.path.exists(STAMP_FILE) and os.path.isdir(LOCAL_OUTDATA) and os.listdir(LOCAL_OUTDATA):
        logger.info("✅ GFS data stamp found: %s", STAMP_FILE)
        return True

    logger.warning("⚠️ No GFS stamp file found — triggering download...")
    # Clean up old data
    subprocess.run(["rm", "-rf", f"{LOCAL_OUTDATA}/*"], shell=True)
    # Trigger retrieval (00Z assumed, adjust if needed)
    retriever = os.path.join(GFS_DIR, "retrieve_gfs_data_0000Z.py")
    start_gfs = datetime.now(timezone.utc)

    r = subprocess.run(["python3", retriever], capture_output=True, text=True, env=os.environ)
    if r.returncode == 0:
        if os.path.exists(STAMP_FILE):
            logger.info("✅ GFS data successfully downloaded after %.1f minutes.", (datetime.now(timezone.utc) - start_gfs).total_seconds()/60)
            return True
        else:
            logger.error("❌ GFS download completed but stamp file missing.")
            return False
    else:
        logger.error("❌ GFS data retrieval failed:\n%s", r.stderr)
        return False


def run_auto_production():
    """Run the main bash automation pipeline."""
    logger.info("🚀 Launching AUTO_PRODUCTION pipeline...")
    proc = subprocess.Popen(["/bin/bash", BASH_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Stream live logs
    for line in proc.stdout:
        logger.info(line.strip())

    stdout, stderr = proc.communicate()
    if proc.returncode == 0:
        logger.info("✅ AUTO_PRODUCTION completed successfully.")
    else:
        logger.error("❌ AUTO_PRODUCTION failed with code %d:\n%s", proc.returncode, stderr)


# --------------------------------------------------------
#  MAIN EXECUTION
# --------------------------------------------------------
if __name__ == "__main__":
    start_time = datetime.now(timezone.utc)
    logger.info("🚀 WRF_AI_WRAPPER started at %s", start_time)

    try:
        wait_or_kill_existing(max_wait_minutes=30)

        if not ensure_gfs_data_ready():
            logger.error("❌ Failed to prepare GFS data. Aborting run.")
        else:
            run_auto_production()

    except KeyboardInterrupt:
        logger.warning("🧩 Interrupted manually. Exiting gracefully.")
    except Exception as e:
        logger.exception("❌ Unexpected error: %s", e)
    finally:
        logger.info("🏁 Wrapper finished at %s", datetime.now(timezone.utc))
