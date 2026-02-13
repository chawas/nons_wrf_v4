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
    OUTDATA_PATH = "./local_outdata/"
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


def all_files_complete(outdir, date_prefix, hour_str, logger):
    """Verify all forecast files are present and valid."""
    missing_files = []

    for forecast_hour in np.arange(0, MAX_FORECAST_LENGTH + 1, 1):
        filename = f"{date_prefix}{hour_str}00_gfs_global.grb2f{forecast_hour:03d}0000"
        filepath = os.path.join(outdir, filename)

        if not is_file_valid(filepath):
            missing_files.append(filename)

    if missing_files:
        logger.warning(
            f"Missing/incomplete files ({len(missing_files)}): "
            f"{missing_files[:5]}{'...' if len(missing_files) > 5 else ''}"
        )
        return False

    return True


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
    """Find the latest available GFS forecast cycle."""
    current_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    for attempt in range(6):  # Check up to 6 cycles back (36 hours)
        url_date_str = current_time.strftime("%Y%m%d/%H/")
        parent_url = f"{DOMAIN_URL}gfs.{url_date_str}"

        try:
            with urllib.request.urlopen(parent_url, timeout=30) as response:
                if response.status == 200:
                    logger.info(f"Found available GFS cycle: {current_time:%Y%m%d %H}Z")
                    return current_time
        except urllib.error.URLError as e:
            logger.debug(f"Cycle {current_time:%Y%m%d %H}Z not available: {e}")
        except Exception as e:
            logger.warning(f"Error checking cycle {current_time:%Y%m%d %H}Z: {e}")

        # Try previous cycle
        current_time -= timedelta(hours=6)
        if attempt < 5:  # Don't sleep after the last attempt
            time.sleep(5)

    logger.error("No valid GFS cycle found in the last 36 hours")
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

        forecast_date = find_latest_cycle(logger)
        date_in = forecast_date.strftime("%Y%m%d")
        date_out = forecast_date.strftime("%y%m%d")
        hour_str = forecast_date.strftime("%H")

        # Ensure output directory exists
        Path(OUTDATA_PATH).mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {OUTDATA_PATH}")
        logger.info(f"Target cycle: {forecast_date:%Y-%m-%d %H}Z")

        # Check if already completed today
        if (os.path.exists(GFS_STAMP) and
                open(GFS_STAMP).read().strip() == today.strftime("%Y-%m-%d")):
            logger.info("GFS data already retrieved today")
            return True

        # Download attempt loop
        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"Download attempt {attempt}/{MAX_RETRIES}")
            successful_downloads = 0

            # Download each forecast hour
            for forecast_hour in np.arange(0, MAX_FORECAST_LENGTH + 1, 1):
                filename = f"{date_out}{hour_str}00_gfs_global.grb2f{forecast_hour:03d}0000"
                filepath = os.path.join(OUTDATA_PATH, filename)

                # Skip if file already exists and is valid
                if is_file_valid(filepath):
                    successful_downloads += 1
                    continue

                # Build URL and download
                url = build_download_url(date_in, hour_str, forecast_hour)
                if download_file(url, filepath, filename, logger):
                    successful_downloads += 1

                # Be nice to the server
                time.sleep(DOWNLOAD_DELAY)

            # Validate completion
            logger.info(f"Downloaded {successful_downloads}/{(MAX_FORECAST_LENGTH + 1)} files")

            if all_files_complete(OUTDATA_PATH, date_out, hour_str, logger):
                # Create success stamp
                with open(GFS_STAMP, "w") as f:
                    f.write(today.strftime("%Y-%m-%d"))
                logger.info(f"GFS retrieval completed successfully in {time.time() - start_time:.1f} seconds")
                return True
            else:
                if attempt < MAX_RETRIES:
                    logger.warning(f"Retrying in {RETRY_DELAY_SEC//60} minutes...")
                    time.sleep(RETRY_DELAY_SEC)
                else:
                    logger.error("Maximum retry attempts reached")
                    return False

    except Exception as e:
        logger.error(f"GFS retrieval failed: {e}")
        logger.debug("Exception details:", exc_info=True)
        return False


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