#!/usr/bin/env python3
# retrieve_gfs_data.py
# Fetch GFS 0.25° data for today, validating files and creating gfs_stamp after full completion.

import os
import sys
import time
import urllib.request
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from config import DOMAIN_URL, OUTDATA_PATH, MAX_FORECAST_LENGTH

GFS_STAMP = os.path.join(OUTDATA_PATH, "gfs_downloaded_today.stamp")

# ---------------------------------------------------------
def log(msg):
    """Simple print logger for wrapper capture."""
    print(f"[{datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC] {msg}", flush=True)

# ---------------------------------------------------------
def is_file_valid(filepath, min_mb=1):
    """Check if file exists and has sufficient size."""
    if not os.path.isfile(filepath):
        return False
    return os.path.getsize(filepath) / (1024 * 1024) > min_mb

# ---------------------------------------------------------
def all_files_complete(outdir, date_prefix, hour_str):
    """Ensure all f000–f384 files are valid."""
    for fh in np.arange(0, MAX_FORECAST_LENGTH + 1, 1):
        fn = f"{date_prefix}{hour_str}00_gfs_global.grb2f{fh:03d}0000"
        fpath = os.path.join(outdir, fn)
        if not is_file_valid(fpath):
            log(f"⚠️ Incomplete or missing file: {fn}")
            return False
    return True

# ---------------------------------------------------------
def retrieve_gfs_data():
    start = time.time()
    today = datetime.utcnow()
    log(f"🚀 Starting GFS retrieval for {today:%Y-%m-%d}")

    forecast_date = today.replace(hour=0)
    url_date_str = forecast_date.strftime("%Y%m%d/%H/")
    parent_url = f"{DOMAIN_URL}gfs.{url_date_str}"

    # Validate cycle URL
    for _ in range(6):
        try:
            urllib.request.urlopen(parent_url)
            log(f"✅ GFS cycle found: {parent_url}")
            break
        except Exception:
            forecast_date -= timedelta(hours=12)
            url_date_str = forecast_date.strftime("%Y%m%d/%H/")
            parent_url = f"{DOMAIN_URL}gfs.{url_date_str}"
            log(f"Retrying previous cycle: {parent_url}")
            time.sleep(10)
    else:
        log("❌ No valid GFS cycle found. Exiting.")
        sys.exit(1)

    date_in = forecast_date.strftime("%Y%m%d")
    date_out = forecast_date.strftime("%y%m%d")
    hour_str = forecast_date.strftime("%H")

    Path(OUTDATA_PATH).mkdir(parents=True, exist_ok=True)

    for fh in np.arange(0, MAX_FORECAST_LENGTH + 1, 1):
        fn_hour = f"{fh:03d}"
        out_filename = f"{date_out}{hour_str}00_gfs_global.grb2f{fn_hour}0000"
        out_path = os.path.join(OUTDATA_PATH, out_filename)

        if is_file_valid(out_path):
            log(f"✅ {out_filename} already exists and valid.")
            continue

        url = (
            f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?"
            f"dir=%2Fgfs.{date_in}%2F{hour_str}%2Fatmos&"
            f"file=gfs.t{hour_str}z.pgrb2.0p25.f{fn_hour}&"
            "var_APCP=on&var_TMP=on&var_UGRD=on&var_VGRD=on&var_RH=on&"
            "var_HCDC=on&var_MCDC=on&var_LCDC=on&var_TCDC=on&"
            "all_lev=on&subregion=&toplat=-15&leftlon=24&rightlon=34&bottomlat=-23"
        )

        try:
            log(f"⬇️ Downloading {out_filename} ...")
            urllib.request.urlretrieve(url, out_path)
            if is_file_valid(out_path):
                log(f"✅ Saved {out_filename}")
            else:
                log(f"⚠️ {out_filename} may be incomplete (too small).")
        except Exception as e:
            log(f"❌ Error downloading {out_filename}: {e}")
            continue

        time.sleep(1)

    # ---------------------------------------------------------
    # Stamp creation only when all files verified
    # ---------------------------------------------------------
    if all_files_complete(OUTDATA_PATH, date_out, hour_str):
        with open(GFS_STAMP, "w") as f:
            f.write(today.strftime("%Y-%m-%d"))
        log("🏁 All files complete — gfs_stamp created.")
    else:
        log("⚠️ Some files missing or incomplete — no stamp written.")

    log(f"Total runtime: {time.time() - start:.1f} seconds")


# ---------------------------------------------------------
if __name__ == "__main__":
    try:
        retrieve_gfs_data()
        sys.exit(0)
    except Exception as e:
        log(f"❌ Fatal error: {e}")
        sys.exit(1)
