#!/usr/bin/env python3
# retrieve_gfs_data.py
import os
import sys
import time
import urllib.request
import numpy as np
import logging
from datetime import datetime, timedelta
from pathlib import Path
from config import DOMAIN_URL, OUTDATA_PATH, MAX_FORECAST_LENGTH

GFS_STAMP = os.path.join(OUTDATA_PATH, "gfs_downloaded_today.stamp")
MIN_FILE_MB = 0.4
MAX_RETRIES = 3
RETRY_DELAY_SEC = 120






def get_logger():
    """Return a logger (shared if imported, standalone if run directly)."""
    logger = logging.getLogger("gfs_retriever")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    return logger


def retrieve_gfs_data(logger=None):
    """Main retrieval logic."""
    logger = logger or get_logger()
    start = time.time()
    today = datetime.utcnow()
    logger.info(f"🚀 Starting GFS retrieval for {today:%Y-%m-%d}")

    forecast_date = find_latest_cycle(logger)
    date_in = forecast_date.strftime("%Y%m%d")
    date_out = forecast_date.strftime("%y%m%d")
    hour_str = forecast_date.strftime("%H")
    Path(OUTDATA_PATH).mkdir(parents=True, exist_ok=True)

    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"🔁 Attempt {attempt}/{MAX_RETRIES} to complete dataset")

        for fh in np.arange(0, MAX_FORECAST_LENGTH + 1, 1):
            fn_hour = f"{fh:03d}"
            out_filename = f"{date_out}{hour_str}00_gfs_global.grb2f{fn_hour}0000"
            out_path = os.path.join(OUTDATA_PATH, out_filename)

            if is_file_valid(out_path):
                continue

            url = (
                f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?"
                f"dir=%2Fgfs.{date_in}%2F{hour_str}%2Fatmos&"
                f"file=gfs.t{hour_str}z.pgrb2.0p25.f{fn_hour}&"
                "var_APCP=on&var_TMP=on&var_UGRD=on&var_VGRD=on&var_RH=on&"
                "var_HCDC=on&var_MCDC=on&var_LCDC=on&var_TCDC=on&"
                "all_lev=on&subregion=&toplat=-15&leftlon=24&rightlon=34&bottomlat=-23"
            )

            download_file(url, out_path, out_filename, logger)
            time.sleep(1)

        if all_files_complete(OUTDATA_PATH, date_out, hour_str, logger):
            logger.info("🎉 All GFS files validated successfully!")
            with open(GFS_STAMP, "w") as f:
                f.write(today.strftime("%Y-%m-%d"))
            logger.info(f"📝 Stamp created: {GFS_STAMP}")
            break
        else:
            if attempt < MAX_RETRIES:
                logger.info(f"⏳ Waiting {RETRY_DELAY_SEC//60} min before next retry...")
                time.sleep(RETRY_DELAY_SEC)
            else:
                logger.error("❌ Max retries reached — dataset incomplete.")
                sys.exit(2)

    logger.info(f"🏁 Finished in {time.time() - start:.1f} s")


# The helper functions now all accept logger instead of print/log
def is_file_valid(filepath, min_mb=MIN_FILE_MB):
    return os.path.isfile(filepath) and (os.path.getsize(filepath) / (1024 * 1024) > min_mb)


def all_files_complete(outdir, date_prefix, hour_str, logger):
    missing = []
    for fh in np.arange(0, MAX_FORECAST_LENGTH + 1, 1):
        fn = f"{date_prefix}{hour_str}00_gfs_global.grb2f{fh:03d}0000"
        fpath = os.path.join(outdir, fn)
        if not is_file_valid(fpath):
            missing.append(fn)
    if missing:
        logger.warning(f"Missing/incomplete files ({len(missing)}): {missing[:5]}{'...' if len(missing) > 5 else ''}")
    return len(missing) == 0


def download_file(url, out_path, fn, logger):
    try:
        logger.info(f"⬇️  Downloading {fn} ...")
        urllib.request.urlretrieve(url, out_path)
        if is_file_valid(out_path):
            logger.info(f"✅  Saved {fn}")
            return True
        else:
            logger.warning(f"⚠️  {fn} appears incomplete (<400 KB)")
            return False
    except Exception as e:
        logger.error(f"❌  Error downloading {fn}: {e}")
        return False


def find_latest_cycle(logger):
    forecast_date = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    for _ in range(6):
        url_date_str = forecast_date.strftime("%Y%m%d/%H/")
        parent_url = f"{DOMAIN_URL}gfs.{url_date_str}"
        try:
            urllib.request.urlopen(parent_url, timeout=10)
            logger.info(f"✅  Found available cycle: {parent_url}")
            return forecast_date
        except Exception:
            forecast_date -= timedelta(hours=6)
            logger.info(f"Retrying previous cycle: {forecast_date:%Y%m%d %H}Z")
            time.sleep(5)
    logger.error("❌  No valid GFS cycle found.")
    sys.exit(1)


if __name__ == "__main__":
    retrieve_gfs_data()
