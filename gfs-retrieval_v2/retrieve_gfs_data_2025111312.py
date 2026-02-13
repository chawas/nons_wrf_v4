import datetime
import schedule
import os
import sys
import time
import shutil
import urllib.request
import numpy as np
from pathlib import Path
from log import logger
from config import DOMAIN_URL, OUTDATA_PATH, FILE_SUFFIX, MAX_FORECAST_LENGTH

GFS_STAMP_FILE = os.path.join(OUTDATA_PATH, "gfs_stamp")

# ============================================================
def main():
    start_time = time.time()
    logger.info("🚀 Starting GFS data retrieval...")

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    logger.info(f"📅 Forecast cycle for {today}")

    # Clean directory if needed
    clear_existing_files(OUTDATA_PATH)

    # Determine valid GFS cycle
    forecast_cycle_date = datetime.datetime.utcnow().replace(hour=0)
    forecast_cycle_URL_date_string = forecast_cycle_date.strftime('%Y%m%d/%H/')
    parent_URL = f"{DOMAIN_URL}gfs.{forecast_cycle_URL_date_string}"

    # ------------------------------------------------------------
    # Retry logic for cycle availability
    # ------------------------------------------------------------
    for attempt in range(6):
        try:
            logger.info(f"🔗 Checking availability of {parent_URL}")
            urllib.request.urlopen(parent_URL)
            logger.info("✅ Valid GFS cycle found.")
            break
        except Exception:
            logger.warning("⚠️ GFS cycle not ready, backing up 12h...")
            forecast_cycle_date -= datetime.timedelta(hours=12)
            forecast_cycle_URL_date_string = forecast_cycle_date.strftime('%Y%m%d/%H/')
            parent_URL = f"{DOMAIN_URL}gfs.{forecast_cycle_URL_date_string}"
            time.sleep(5)
    else:
        logger.error("❌ No valid GFS cycle found after multiple attempts.")
        sys.exit(1)

    forecast_cycle_date_str_in = forecast_cycle_date.strftime('%Y%m%d')
    forecast_cycle_date_str_out = forecast_cycle_date.strftime('%y%m%d')
    forecast_cycle_hour_str = forecast_cycle_date.strftime('%H')

    # ------------------------------------------------------------
    # 🚀 Loop through forecast hours and check/download files
    # ------------------------------------------------------------
    for forecast_length_hour in np.arange(0, MAX_FORECAST_LENGTH + 1, 1):
        forecast_length_hour_str = f"{forecast_length_hour:03d}"
        out_filename = f"{forecast_cycle_date_str_out}{forecast_cycle_hour_str}00_gfs_global.grb2f{forecast_length_hour_str}0000"
        out_path = os.path.join(OUTDATA_PATH, out_filename)

        # Check if file already exists and is valid
        if is_file_valid(out_path):
            logger.info(f"✅ File {out_filename} already complete. Skipping download.")
            continue

        # Otherwise, download
        retrieve_data_url = (
            f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?"
            f"dir=%2Fgfs.{forecast_cycle_date_str_in}%2F{forecast_cycle_hour_str}%2Fatmos&"
            f"file=gfs.t{forecast_cycle_hour_str}z.pgrb2.0p25.f{forecast_length_hour_str}&"
            "var_APCP=on&var_DPT=on&var_HCDC=on&var_LCDC=on&var_MCDC=on&var_TCDC=on&"
            "var_RH=on&var_TMP=on&var_UGRD=on&var_VGRD=on&all_lev=on&"
            "subregion=&toplat=-15&leftlon=24&rightlon=34&bottomlat=-23"
        )

        try:
            logger.info(f"⬇️ Downloading {out_filename} ...")
            urllib.request.urlretrieve(retrieve_data_url, out_path)
            if is_file_valid(out_path):
                logger.info(f"✅ Successfully saved {out_filename}")
            else:
                logger.warning(f"⚠️ {out_filename} seems incomplete. Will retry next run.")
        except Exception as e:
            logger.error(f"❌ Error downloading {out_filename}: {e}")
            continue

        time.sleep(1)  # be kind to the server :)

    # ------------------------------------------------------------
    # 🚀 Write gfs_stamp only after confirming all files exist
    # ------------------------------------------------------------
    if all_files_complete(OUTDATA_PATH, MAX_FORECAST_LENGTH):
        with open(GFS_STAMP_FILE, "w") as f:
            f.write(today)
        logger.info("🏁 All GFS files complete — stamp file created.")
    else:
        logger.warning("⚠️ Some GFS files are missing or incomplete — skipping stamp creation.")

    logger.info(f"🕒 Total time: {time.time() - start_time:.2f} seconds")


# ============================================================
def is_file_valid(filepath, min_size_mb=1):
    """Check if file exists and has a reasonable size (>1 MB)."""
    if not os.path.isfile(filepath):
        return False
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    return size_mb > min_size_mb


# ============================================================
def all_files_complete(directory, max_forecast):
    """Check all f000–fMAX files exist and pass validation."""
    for i in np.arange(0, max_forecast + 1, 1):
        fname = f"{datetime.datetime.utcnow().strftime('%y%m%d')}0000_gfs_global.grb2f{i:03d}0000"
        fpath = os.path.join(directory, fname)
        if not is_file_valid(fpath):
            logger.warning(f"⚠️ Missing or incomplete file: {fname}")
            return False
    return True


# ============================================================
def clear_existing_files(directory):
    """Ensure directory exists and is clean."""
    if os.path.isdir(directory):
        logger.info(f"🧹 Clearing directory: {directory}")
        for filename in os.listdir(directory):
            path = os.path.join(directory, filename)
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.unlink(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")
    else:
        logger.info(f"📁 Creating directory: {directory}")
        Path(directory).mkdir(parents=True, exist_ok=True)


# ============================================================
def updater():
    schedule.every().day.at("07:30").do(main)
    schedule.every().day.at("19:30").do(main)
    while True:
        schedule.run_pending()
        time.sleep(30)


# ============================================================
if __name__ == "__main__":
    main()
    # updater()
