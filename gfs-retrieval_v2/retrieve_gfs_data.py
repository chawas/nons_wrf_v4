#!/usr/bin/env python3
# retrieve_gfs_data.py
"""
GFS Data Retrieval Module
Downloads GFS weather forecast data for WRF model initialization.

Behavior:
- Cleans OUTDATA_PATH (removes previous files) before downloading.
- Finds latest available cycle (tries several URL patterns).
- Downloads forecast hours:
    * hourly: 0 .. 120 (step 1)
    * 3-hourly: 123 .. 384 (step 3)
- Retries each file up to MAX_FILE_RETRIES times.
- Writes gfs_downloaded_today.stamp only when ALL expected files exist and pass MIN_FILE_MB.
- Writes a detailed retrieval logfile in OUTDATA_PATH (use that in wrapper email).
- Exits non-zero (return False / exit 1) on failure so wrapper can email log only.
"""

import os
import sys
import time
import urllib.request
import urllib.error
import numpy as np
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Configuration - try import from config, else use sensible defaults
try:
    from config import DOMAIN_URL, OUTDATA_PATH, MAX_FORECAST_LENGTH
except Exception:
    DOMAIN_URL = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/"
    OUTDATA_PATH = "/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/local_outdata/"
    MAX_FORECAST_LENGTH = 384

# Constants and tuning parameters
GFS_STAMP = os.path.join(os.path.dirname(OUTDATA_PATH), "logs", "gfs_downloaded_today.stamp") \
    if os.path.isdir(os.path.join(os.path.dirname(OUTDATA_PATH), "logs")) else os.path.join(OUTDATA_PATH, "gfs_downloaded_today.stamp")
MIN_FILE_MB = 0.4
MAX_RETRIES = 3                # Number of full download attempt cycles
RETRY_DELAY_SEC = 120          # Wait between attempt cycles
DOWNLOAD_DELAY = 0.5           # Small delay between file downloads to be polite
MAX_FILE_RETRIES = 3           # Per-file retry attempts (HTTP timeouts, 404s etc.)
PER_FILE_RETRY_DELAY = 5       # seconds between per-file retries

# ---- logging setup (per-run logfile inside OUTDATA_PATH) ----
def make_logger(logfile_path):
    logger = logging.getLogger("gfs_retriever")
    logger.setLevel(logging.INFO)

    # remove any existing handlers to avoid duplicates
    if logger.handlers:
        for h in list(logger.handlers):
            logger.removeHandler(h)

    # console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    chfmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    ch.setFormatter(chfmt)
    logger.addHandler(ch)

    # file
    fh = logging.FileHandler(logfile_path)
    fh.setLevel(logging.INFO)
    fh.setFormatter(chfmt)
    logger.addHandler(fh)

    return logger

# ---- helpers ----
def is_file_valid(filepath, min_mb=MIN_FILE_MB):
    """Check if file exists and meets minimum size requirement."""
    try:
        if not os.path.isfile(filepath):
            return False
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        return file_size_mb >= min_mb
    except Exception:
        return False

def build_expected_hours():
    """Return a list of expected forecast hours: 0..120 step1, then 123..384 step3."""
    hours = list(range(0, 121, 1))
    hours += list(range(123, MAX_FORECAST_LENGTH + 1, 3))
    hours = sorted(set(hours))
    return hours

def build_download_url(date_in, hour_str, forecast_hour):
    """Build the GFS data download URL for specific parameters (same as your previous)."""
    return (
        f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?"
        f"dir=%2Fgfs.{date_in}%2F{hour_str}%2Fatmos&"
        f"file=gfs.t{hour_str}z.pgrb2.0p25.f{forecast_hour:03d}&"
        "var_APCP=on&var_TMP=on&var_UGRD=on&var_VGRD=on&var_RH=on&"
        "var_HCDC=on&var_MCDC=on&var_LCDC=on&var_TCDC=on&"
        "all_lev=on&subregion=&toplat=-15&leftlon=24&rightlon=34&bottomlat=-23"
    )

def find_latest_cycle(logger):
    """Find the latest available GFS forecast cycle (tries up to ~48 hours back)."""
    current_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    # round down to plausible cycle: prefer 00 and 12 as your wrapper expects those
    h = current_time.hour
    # We'll prefer the latest of 00 or 12 or 18 or 06 depending on time; check back up to 48h
    if h < 6:
        current_time = current_time.replace(hour=0)
    elif h < 12:
        current_time = current_time.replace(hour=0)
    elif h < 18:
        current_time = current_time.replace(hour=0)
    else:
        current_time = current_time.replace(hour=12)

    logger.info("Starting cycle search from: %sZ", current_time.strftime("%Y-%m-%d %H"))
    print("Starting cycle search from: %sZ", current_time.strftime("%Y-%m-%d %H"))
    checked = 0
    for attempt in range(8):  # up to 8 cycles back (48 hours)
        url_date_str = current_time.strftime("%Y%m%d")
        hour_str = current_time.strftime("%H")

        url_patterns = [
            f"{DOMAIN_URL}gfs.{url_date_str}/{hour_str}/atmos/",
            f"{DOMAIN_URL}gfs.{url_date_str}/{hour_str}/",
            f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfs.{url_date_str}/{hour_str}/atmos/",
        ]

        for url_pattern in url_patterns:
            try:
                logger.debug("Trying URL: %s", url_pattern)
                with urllib.request.urlopen(url_pattern, timeout=20) as resp:
                    if resp.status == 200:
                        logger.info("Found available GFS cycle: %sZ (%s)", current_time.strftime("%Y-%m-%d %H"), url_pattern)
                        return current_time
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    logger.debug("HTTP 404 for %s", url_pattern)
                else:
                    logger.warning("HTTP %s for %s", e.code, url_pattern)
            except urllib.error.URLError as e:
                logger.debug("URL error for %s: %s", url_pattern, e)
            except Exception as e:
                logger.warning("Error checking %s: %s", url_pattern, e)

        # step back 6 hours and try again
        current_time -= timedelta(hours=6)
        checked += 1
        logger.info("Trying previous cycle: %sZ (checked %d)", current_time.strftime("%Y-%m-%d %H"), checked)
        time.sleep(1)

    logger.error("No valid GFS cycle found in the last 48 hours")
    raise RuntimeError("No valid GFS cycle available")

def cleanup_outdata(outdir, logger):
    """Delete everything inside OUTDATA_PATH to ensure a clean start."""
    try:
        if os.path.exists(outdir):
            logger.info("Cleaning OUTDATA_PATH: %s", outdir)
            for entry in os.listdir(outdir):
                path = os.path.join(outdir, entry)
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        os.remove(path)
                except Exception as e:
                    logger.warning("Failed to remove %s: %s", path, e)
        else:
            logger.info("OUTDATA_PATH does not exist; creating: %s", outdir)
            Path(outdir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error("Error cleaning OUTDATA_PATH: %s", e)
        raise

# ---- single-file download with per-file retries ----
def try_download_file(url, out_path, filename, logger):
    """Try to download `url` to out_path with per-file retries."""
    attempts = 0
    while attempts < MAX_FILE_RETRIES:
        attempts += 1
        try:
            logger.info("Downloading %s (attempt %d/%d)", filename, attempts, MAX_FILE_RETRIES)
            urllib.request.urlretrieve(url, out_path)
            # small sleep to ensure filesystem updates
            time.sleep(0.2)
            if is_file_valid(out_path):
                size_mb = os.path.getsize(out_path) / (1024 * 1024)
                logger.info("Downloaded %s OK (%.2f MB)", filename, size_mb)
                return True
            else:
                logger.warning("%s appears too small after download (attempt %d). Removing and retrying.", filename, attempts)
                try:
                    os.remove(out_path)
                except Exception:
                    pass
        except urllib.error.HTTPError as e:
            logger.error("HTTP error for %s: %s", filename, e)
            # If 404 keep retrying because some fh might be generated differently; still retry a few times
        except urllib.error.URLError as e:
            logger.error("Network error for %s: %s", filename, e)
        except Exception as e:
            logger.error("Unexpected error for %s: %s", filename, e)

        if attempts < MAX_FILE_RETRIES:
            logger.info("Waiting %d seconds before next try for %s", PER_FILE_RETRY_DELAY, filename)
            time.sleep(PER_FILE_RETRY_DELAY)

    logger.error("Failed to download %s after %d attempts", filename, MAX_FILE_RETRIES)
    return False

# ---- main retrieval function ----
def retrieve_gfs_data(logger=None):
    logger = logger or logging.getLogger("gfs_retriever")
    start_time = time.time()

    # Create OUTDATA_PATH and logs dir
    Path(OUTDATA_PATH).mkdir(parents=True, exist_ok=True)
    logs_dir = os.path.join(os.path.dirname(OUTDATA_PATH), "logs")
    Path(logs_dir).mkdir(parents=True, exist_ok=True)

    # create run logfile
    run_id = datetime.utcnow().strftime("%y%m%d_%H%M")
    run_log = os.path.join(OUTDATA_PATH, f"gfs_retrieval_{run_id}.log")
    # make a logger bound to this logfile
    run_logger = make_logger(run_log)

    run_logger.info("=== GFS retrieval run started: %s UTC ===", datetime.utcnow().isoformat())
    try:
        # 1) cleanup previous run / remove stale files
        #cleanup_outdata(OUTDATA_PATH, run_logger)

        # 2) find latest cycle
        forecast_date = find_latest_cycle(run_logger)
        date_in = forecast_date.strftime("%Y%m%d")
        date_out = forecast_date.strftime("%y%m%d")
        hour_str = forecast_date.strftime("%H")
        run_logger.info("Selected cycle: %s %sZ (date_in=%s, date_out=%s)", forecast_date.strftime("%Y-%m-%d"), hour_str, date_in, date_out)

        # 3) build expected hours
        expected_hours = build_expected_hours()
        run_logger.info("Expected forecast hours count: %d (0..120 hourly, 123..%d 3-hourly)", len([h for h in expected_hours if h<=120]), MAX_FORECAST_LENGTH)

        # 4) attempt downloads in MAX_RETRIES cycles
        for attempt in range(1, MAX_RETRIES + 1):
            run_logger.info("Download attempt cycle %d/%d", attempt, MAX_RETRIES)
            downloaded_this_cycle = 0

            for fh in expected_hours:
                filename = f"{date_out}{hour_str}00_gfs_global.grb2f{fh:03d}0000"
                outpath = os.path.join(OUTDATA_PATH, filename)

                # skip if already valid
                if is_file_valid(outpath):
                    continue

                url = build_download_url(date_in, hour_str, fh)
                ok = try_download_file(url, outpath, filename, run_logger)
                if ok:
                    downloaded_this_cycle += 1
                # small pause between files
                time.sleep(DOWNLOAD_DELAY)

            run_logger.info("Cycle %d complete: downloaded %d files this cycle", attempt, downloaded_this_cycle)

            # re-evaluate file completeness
            valid_files = [f for f in os.listdir(OUTDATA_PATH) if 'gfs_global.grb2f' in f and is_file_valid(os.path.join(OUTDATA_PATH, f))]
            run_logger.info("Current valid files count: %d / %d", len(valid_files), len(expected_hours))

            # if complete, write stamp and exit success
            if len(valid_files) == len(expected_hours):
                try:
                    with open(GFS_STAMP, "w") as sf:
                        sf.write(datetime.utcnow().strftime("%Y-%m-%d"))
                    run_logger.info("✅ All expected files present. Wrote stamp: %s", GFS_STAMP)
                except Exception as e:
                    run_logger.warning("Could not write stamp file: %s", e)
                    # still treat as success if all files present
                run_logger.info("GFS retrieval finished in %.1f seconds", time.time() - start_time)
                return True

            # else if not complete, retry unless last attempt
            if attempt < MAX_RETRIES:
                run_logger.warning("Not all files present after attempt %d. Waiting %d seconds before retry.", attempt, RETRY_DELAY_SEC)
                time.sleep(RETRY_DELAY_SEC)

        # After retries, check missing files and fail
        valid_files = [f for f in os.listdir(OUTDATA_PATH) if 'gfs_global.grb2f' in f and is_file_valid(os.path.join(OUTDATA_PATH, f))]
        missing = []
        for fh in expected_hours:
            fname = f"{date_out}{hour_str}00_gfs_global.grb2f{fh:03d}0000"
            if not is_file_valid(os.path.join(OUTDATA_PATH, fname)):
                missing.append(fname)

        run_logger.error("❌ GFS retrieval incomplete after %d attempts. Missing files: %d", MAX_RETRIES, len(missing))
        # log a sample of missing files
        for m in missing[:40]:
            run_logger.error("   - %s", m)

        run_logger.error("See run logfile: %s", run_log)
        # do NOT create product zip here; fail and let wrapper email this run_log only
        return False

    except Exception as e:
        run_logger.exception("Fatal exception during GFS retrieval: %s", e)
        return False

def main():
    success = retrieve_gfs_data()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
