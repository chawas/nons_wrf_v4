#!/usr/bin/env python3
# retrieve_gfs_data.py
"""
GFS Data Retrieval Module
Downloads GFS weather forecast data for WRF model initialization.
"""

import os
import sys
import time
import urllib.request
import urllib.error
import numpy as np
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Configuration - should be imported from config
try:
    from config import DOMAIN_URL, OUTDATA_PATH, MAX_FORECAST_LENGTH
except ImportError:
    # Fallback configuration
    DOMAIN_URL = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/"
    OUTDATA_PATH = "/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/local_outdata/"
    MAX_FORECAST_LENGTH = 384

# Constants
GFS_STAMP = os.path.join(OUTDATA_PATH, "gfs_downloaded_today.stamp")
MIN_FILE_MB = 0.4
MAX_RETRIES = 3
RETRY_DELAY_SEC = 120
DOWNLOAD_DELAY = 1  # seconds between downloads


def get_logger(logger=None):
    """Return a logger instance."""
    if logger is not None:
        return logger

    # Create standalone logger if not provided
    logger = logging.getLogger("gfs_retriever")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    return logger


def is_file_valid(filepath, min_mb=MIN_FILE_MB):
    """Check if file exists and meets minimum size requirement."""
    if not os.path.isfile(filepath):
        return False

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    return file_size_mb > min_mb


def check_existing_files(outdir, date_prefix, hour_str, logger):
    """Check existing files and return lists of valid, incomplete, and missing files."""
    valid_files = []
    incomplete_files = []
    missing_files = []

    for forecast_hour in np.arange(0, MAX_FORECAST_LENGTH + 1, 1):
        filename = f"{date_prefix}{hour_str}00_gfs_global.grb2f{forecast_hour:03d}0000"
        filepath = os.path.join(outdir, filename)

        if is_file_valid(filepath):
            valid_files.append(filename)
        elif os.path.exists(filepath):
            incomplete_files.append(filename)
        else:
            missing_files.append(filename)

    logger.info(f"File status - Valid: {len(valid_files)}, Incomplete: {len(incomplete_files)}, Missing: {len(missing_files)}")

    if incomplete_files:
        logger.info(f"Incomplete files: {incomplete_files[:3]}{'...' if len(incomplete_files) > 3 else ''}")
    if missing_files:
        logger.info(f"Missing files: {missing_files[:3]}{'...' if len(missing_files) > 3 else ''}")

    return valid_files, incomplete_files, missing_files


def download_file(url, out_path, filename, logger):
    """Download a single GFS file with error handling."""
    try:
        logger.info(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, out_path)

        if is_file_valid(out_path):
            file_size_mb = os.path.getsize(out_path) / (1024 * 1024)
            logger.info(f"Downloaded {filename} ({file_size_mb:.1f} MB)")
            return True
        else:
            logger.warning(f"File {filename} appears incomplete (<{MIN_FILE_MB} MB)")
            # Clean up incomplete file
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except OSError:
                pass
            return False

    except urllib.error.URLError as e:
        logger.error(f"Network error downloading {filename}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {filename}: {e}")
        return False


def find_latest_cycle(logger):
    """Find the latest available GFS forecast cycle with improved error handling."""
    current_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    # GFS cycles are at 00, 06, 12, 18 UTC
    # Round down to the nearest cycle
    current_hour = current_time.hour
    print("current hour: ", current_hour)
    if current_hour < 6:
        current_time = current_time.replace(hour=0)
    elif current_hour < 15:
        current_time = current_time.replace(hour=0)
    elif current_hour < 18:
        current_time = current_time.replace(hour=0)
    else:
        current_time = current_time.replace(hour=18)

    logger.info(f"Starting cycle search from: {current_time:%Y-%m-%d %H}Z")

    for attempt in range(8):  # Check up to 8 cycles back (48 hours)
        url_date_str = current_time.strftime("%Y%m%d")
        hour_str = current_time.strftime("%H")

        # Try multiple URL patterns - GFS data can be in different locations
        url_patterns = [
            f"{DOMAIN_URL}gfs.{url_date_str}/{hour_str}/atmos/",
            f"{DOMAIN_URL}gfs.{url_date_str}/{hour_str}/",
            f"https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfs.{url_date_str}/{hour_str}/atmos/",
        ]

        for url_pattern in url_patterns:
            try:
                logger.debug(f"Trying URL: {url_pattern}")
                with urllib.request.urlopen(url_pattern, timeout=30) as response:
                    if response.status == 200:
                        logger.info(f"✅ Found available GFS cycle: {current_time:%Y-%m-%d %H}Z at {url_pattern}")
                        return current_time
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    logger.debug(f"HTTP 404 for {url_pattern}")
                    continue
                else:
                    logger.warning(f"HTTP error {e.code} for {url_pattern}: {e}")
                    continue
            except urllib.error.URLError as e:
                logger.debug(f"URL error for {url_pattern}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error checking {url_pattern}: {e}")
                continue

        # Try previous cycle (6 hours back)
        current_time -= timedelta(hours=6)
        logger.info(f"Trying previous cycle: {current_time:%Y-%m-%d %H}Z")

        if attempt < 7:  # Don't sleep after the last attempt
            time.sleep(2)  # Shorter delay between attempts

    logger.error("❌ No valid GFS cycle found in the last 48 hours")
    # Let's try one more approach - check the latest available on nomads
    try:
        logger.info("Attempting to find latest cycle from nomads index...")
        latest_url = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/"
        with urllib.request.urlopen(latest_url, timeout=30) as response:
            content = response.read().decode('utf-8')
            logger.info("Available directories from nomads:")
            # Extract gfs directories from the index page
            import re
            gfs_dirs = re.findall(r'gfs\.\d{8}', content)
            if gfs_dirs:
                logger.info(f"Found GFS directories: {sorted(set(gfs_dirs))[-5:]}")  # Last 5
    except Exception as e:
        logger.warning(f"Could not check nomads index: {e}")

    raise RuntimeError("No valid GFS cycle available")


def build_download_url(date_in, hour_str, forecast_hour):
    """Build the GFS data download URL for specific parameters."""
    return (
        f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?"
        f"dir=%2Fgfs.{date_in}%2F{hour_str}%2Fatmos&"
        f"file=gfs.t{hour_str}z.pgrb2.0p25.f{forecast_hour:03d}&"
        "var_APCP=on&var_TMP=on&var_UGRD=on&var_VGRD=on&var_RH=on&"
        "var_HCDC=on&var_MCDC=on&var_LCDC=on&var_TCDC=on&"
        "all_lev=on&subregion=&toplat=-15&leftlon=24&rightlon=34&bottomlat=-23"
    )


def retrieve_gfs_data(logger=None):
    """
    Main GFS data retrieval function.

    Args:
        logger: Optional logger instance. If not provided, creates one.

    Returns:
        bool: True if successful, False otherwise
    """
    logger = get_logger(logger)
    start_time = time.time()

    try:
        # Get current date and find latest cycle
        today = datetime.utcnow()
        logger.info(f"Starting GFS retrieval for {today:%Y-%m-%d %H:%M} UTC")

        cleanup_previous_run(OUTDATA_PATH, logger)

        # Check if stamp exists for today
        if os.path.exists(GFS_STAMP):
            try:
                with open(GFS_STAMP, "r") as f:
                    stamp_date = f.read().strip()
                if stamp_date == today.strftime("%Y-%m-%d"):
                    logger.info("✅ GFS data already retrieved today - skipping download")
                    return True
            except Exception as e:
                logger.warning("Could not read GFS stamp file: %s", e)

        forecast_date = find_latest_cycle(logger)
        date_in = forecast_date.strftime("%Y%m%d")
        date_out = forecast_date.strftime("%y%m%d")
        hour_str = forecast_date.strftime("%H")

        # Ensure output directory exists
        Path(OUTDATA_PATH).mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {OUTDATA_PATH}")
        logger.info(f"Target cycle: {forecast_date:%Y-%m-%d %H}Z")

        # Check existing files
        valid_files, incomplete_files, missing_files = check_existing_files(
            OUTDATA_PATH, date_out, hour_str, logger
        )

        # If we have some valid files, we can resume download
        if valid_files:
            logger.info(f"Resuming download - {len(valid_files)} files already valid")

        # Clean up incomplete files
        for filename in incomplete_files:
            filepath = os.path.join(OUTDATA_PATH, filename)
            try:
                os.remove(filepath)
                logger.info(f"Removed incomplete file: {filename}")
            except OSError as e:
                logger.warning(f"Could not remove incomplete file {filename}: {e}")

        # If no files to download and we have all files, create stamp and return
        if not missing_files and not incomplete_files and len(valid_files) == (MAX_FORECAST_LENGTH + 1):
            logger.info("✅ All GFS files already present and valid")
            with open(GFS_STAMP, "w") as f:
                f.write(today.strftime("%Y-%m-%d"))
            return True

        # Download attempt loop
        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"Download attempt {attempt}/{MAX_RETRIES}")
            successful_downloads = len(valid_files)
            files_to_download = missing_files + incomplete_files

            if not files_to_download:
                logger.info("All files already downloaded and valid")
                break

            logger.info(f"Need to download {len(files_to_download)} files")

            # Download each forecast hour that's missing or incomplete
            download_count = 0
            for forecast_hour in np.arange(0, MAX_FORECAST_LENGTH + 1, 1):
                filename = f"{date_out}{hour_str}00_gfs_global.grb2f{forecast_hour:03d}0000"

                # Skip if file is already valid
                if filename in valid_files:
                    continue

                filepath = os.path.join(OUTDATA_PATH, filename)

                # Build URL and download
                url = build_download_url(date_in, hour_str, forecast_hour)
                if download_file(url, filepath, filename, logger):
                    successful_downloads += 1
                    download_count += 1

                # Be nice to the server
                time.sleep(DOWNLOAD_DELAY)

            logger.info(f"Downloaded {download_count} new files this attempt")
            logger.info(f"Total valid files: {successful_downloads}/{(MAX_FORECAST_LENGTH + 1)}")

            # Check if all files are complete
            valid_files, incomplete_files, missing_files = check_existing_files(
                OUTDATA_PATH, date_out, hour_str, logger
            )

            if len(valid_files) == (MAX_FORECAST_LENGTH + 1):
                # Create success stamp
                with open(GFS_STAMP, "w") as f:
                    f.write(today.strftime("%Y-%m-%d"))
                logger.info(f"✅ GFS retrieval completed successfully in {time.time() - start_time:.1f} seconds")
                return True
            else:
                if attempt < MAX_RETRIES:
                    logger.warning(f"Retrying in {RETRY_DELAY_SEC//60} minutes...")
                    time.sleep(RETRY_DELAY_SEC)
                else:
                    logger.error("❌ Maximum retry attempts reached")
                    return False

    except Exception as e:
        logger.error(f"❌ GFS retrieval failed: {e}")
        logger.debug("Exception details:", exc_info=True)
        return False




def cleanup_previous_run(today_dir, logger):
    """
    Delete yesterday's GFS files from the same OUTPUT directory.
    Example:
        today_dir = /data/gfs/20251115_00
        yesterday_dir = /data/gfs/20251114_00
    """
    try:
        base = os.path.dirname(today_dir)
        today_name = os.path.basename(today_dir)

        # Extract date and hour
        date_str, hour_str = today_name.split("_")
        today_date = datetime.strptime(date_str, "%Y%m%d")
        yesterday_date = today_date - timedelta(days=1)

        yesterday_dir = os.path.join(base, f"{yesterday_date.strftime('%Y%m%d')}_{hour_str}")

        if os.path.exists(yesterday_dir):
            logger.info(f"🧹 Removing yesterday's GFS directory: {yesterday_dir}")
            shutil.rmtree(yesterday_dir, ignore_errors=True)
            logger.info("✔ Yesterday's files removed successfully")
        else:
            logger.info("ℹ No previous day's directory found — nothing to delete.")

    except Exception as e:
        logger.error(f"⚠ Failed to clean previous day's directory: {e}")





def main():
    """Main entry point when run as a script."""
    try:
        success = retrieve_gfs_data()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)






if __name__ == "__main__":
    main()