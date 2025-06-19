import datetime
import os
import sys
import time
import urllib.request
from pathlib import Path
import numpy as np

from config import DOMAIN_URL, OUTDATA_PATH, FILE_SUFFIX, MAX_FORECAST_LENGTH
from log import logger


def get_existing_valid_files(directory: Path, today_str: str):
    existing_files = list(directory.glob(f"{today_str}0000_gfs_global.grb2f*0000"))
    valid_files = {
        int(f.name.split("grb2f")[1][:3]) for f in existing_files if f.stat().st_size > 10000
    }
    return valid_files


def main():
    start_time = time.time()
    forecast_cycle_date = datetime.datetime.now().replace(hour=0)
    forecast_cycle_URL_date_string = forecast_cycle_date.strftime('%Y%m%d/%H/')
    forecast_cycle_date_str_in = forecast_cycle_date.strftime('%Y%m%d')
    forecast_cycle_date_str_out = forecast_cycle_date.strftime('%y%m%d')  # To match the WRF format
    forecast_cycle_hour_str = forecast_cycle_date.strftime('%H')

    parent_URL = f'{DOMAIN_URL}gfs.{forecast_cycle_URL_date_string}'
    print(parent_URL)

    max_no_of_tries = 6
    no_of_tries = 0
    while no_of_tries < max_no_of_tries:
        try:
            urllib.request.urlopen(parent_URL)
            logger.info(f'{parent_URL} is accessible.')
            break
        except:
            logger.warning(f'{parent_URL} not available. Retrying with older cycle...')
            forecast_cycle_date -= datetime.timedelta(hours=12)
            forecast_cycle_URL_date_string = forecast_cycle_date.strftime('%Y%m%d/%H/')
            forecast_cycle_date_str_in = forecast_cycle_date.strftime('%Y%m%d')
            forecast_cycle_date_str_out = forecast_cycle_date.strftime('%y%m%d')
            forecast_cycle_hour_str = forecast_cycle_date.strftime('%H')
            parent_URL = f'{DOMAIN_URL}gfs.{forecast_cycle_URL_date_string}'
            no_of_tries += 1
            time.sleep(1)
    else:
        logger.error('Max retries reached. Exiting.')
        sys.exit()

    today_key = forecast_cycle_date_str_out
    valid_files = get_existing_valid_files(Path(OUTDATA_PATH), today_key)
    all_hours = set(range(MAX_FORECAST_LENGTH + 1))
    missing_hours = sorted(all_hours - valid_files)

    for h in missing_hours:
        forecast_hour_str = f'{h:03d}'
        gfs_filename = f'atmos/gfs.t{forecast_cycle_hour_str}z.pgrb2.0p25.f{forecast_hour_str}'
        out_filename = f'{today_key}{forecast_cycle_hour_str}00_gfs_global.grb2f{forecast_hour_str}0000'
        retrieve_data_url = (
            f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl"
            f"?dir=%2Fgfs.{forecast_cycle_date_str_in}%2F{forecast_cycle_hour_str}%2Fatmos"
            f"&file=gfs.t{forecast_cycle_hour_str}z.pgrb2.0p25.f{forecast_hour_str}"
            f"&var_APCP=on&var_DPT=on&var_HCDC=on&var_LCDC=on&var_MCDC=on&var_TCDC=on"
            f"&var_RH=on&var_TMP=on&var_UGRD=on&var_VGRD=on&all_lev=on"
            f"&subregion=&toplat=-15&leftlon=24&rightlon=34&bottomlat=-23"
        )

        logger.info(f"Downloading: {retrieve_data_url}")
        try:
            urllib.request.urlretrieve(retrieve_data_url, f'{OUTDATA_PATH}{out_filename}')
            logger.info(f"Saved: {OUTDATA_PATH}{out_filename}")
        except urllib.error.HTTPError as e:
            logger.error(f"Failed {forecast_hour_str}: HTTP {e.code}")
            continue

    logger.info(f"Download completed in {time.time() - start_time:.1f} seconds.")


if __name__ == '__main__':
    main()
