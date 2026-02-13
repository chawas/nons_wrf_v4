import datetime
import schedule
import os
import sys
import time
import shutil
from log import logger
import numpy as np

import urllib.request
from pathlib import Path

from config import DOMAIN_URL, OUTDATA_PATH, FILE_SUFFIX, MAX_FORECAST_LENGTH


def main():
    '''
    Example url:
    https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfs.20230608/06/atmos/gfs.t06z.pgrb2.0p25.f120
    https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?dir=%2Fgfs.20230629%2F12%2Fatmos&file=gfs.t12z.pgrb2.0p25.f000&var_APCP=on&var_HCDC=on&var_LCDC=on&var_MCDC=on&var_TMP=on&var_UGRD=on&var_VGRD=on&all_lev=on
    '''
    
    #urb=f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?dir=%2Fgfs.{20230612}%2F{06}%2Fatmos&file=gfs.t{06}z.pgrb2.0p25.f{003}&all_var=on&all_lev=on&subregion=&toplat=-15&leftlon=24&rightlon=34&bottomlat=-23"
    start_time = time.time()

    clear_existing_files(OUTDATA_PATH)

    forecast_cycle_date = datetime.datetime.now().replace(hour=00)
    forecast_cycle_URL_date_string = datetime.datetime.strftime(forecast_cycle_date, format='%Y%m%d/%H/')
    print(forecast_cycle_URL_date_string)
    parent_URL = f'{DOMAIN_URL}gfs.{forecast_cycle_URL_date_string}'
    print(parent_URL)
    
    max_no_of_tries = 6
    no_of_tries = 0
    while no_of_tries < max_no_of_tries:
        try:
            logger.info(f'Trying with {parent_URL}...')
            req = urllib.request.urlopen(parent_URL)
            logger.info(f'{parent_URL} seems valid. Will continue')
            time.sleep(1)
            break
        except:
            logger.warning(f'Could not find {parent_URL}. Perhaps the forecast cycle is not available yet. Will back up 12 hours...')
            forecast_cycle_date = forecast_cycle_date - datetime.timedelta(hours=12)
            forecast_cycle_URL_date_string = datetime.datetime.strftime(forecast_cycle_date, format='%Y%m%d/%H/')
            parent_URL = f'{DOMAIN_URL}gfs.{forecast_cycle_URL_date_string}'
            print(parent_URL)

            no_of_tries+=1
            time.sleep(1)
            continue
    else:
        logger.error(f'Maximum number of retries ({max_no_of_tries}) reached. Try again later, or review your settings.')
        sys.exit(1)
    print(parent_URL)

    forecast_cycle_date_str_in = forecast_cycle_date.strftime('%Y%m%d')
    forecast_cycle_date_str_out = forecast_cycle_date.strftime('%y%m%d')  # To match the format of the WRF output
    forecast_cycle_hour_str = forecast_cycle_date.strftime('%H')
    print(f'forecast_cycle_date_str_in ({forecast_cycle_date_str_in})')
    print(forecast_cycle_date_str_out)
    print(forecast_cycle_hour_str)


    for forecast_length_hour in np.arange(0,MAX_FORECAST_LENGTH + 1, 1):  # +3 in order to include the maximum,  3 to jump three hours per step
        if forecast_length_hour < 10:
            forecast_length_hour_str = f'00{forecast_length_hour}'
        elif forecast_length_hour < 100:
            forecast_length_hour_str = f'0{forecast_length_hour}'
        else:
            forecast_length_hour_str = f'{forecast_length_hour}'
        gfs_filename = f'atmos/gfs.t{forecast_cycle_hour_str}z.pgrb2.0p25.f{forecast_length_hour_str}'
        print(f'gfs_filename ({gfs_filename})')
        out_filename = f'{forecast_cycle_date_str_out}{forecast_cycle_hour_str}00_gfs_global.grb2f{forecast_length_hour_str}0000'
        retrieve_data_url = f"https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25_1hr.pl?dir=%2Fgfs.{forecast_cycle_date_str_in}%2F{forecast_cycle_hour_str}%2Fatmos&file=gfs.t{forecast_cycle_hour_str}z.pgrb2.0p25.f{forecast_length_hour_str}&var_APCP=on&var_DPT=on&var_HCDC=on&var_LCDC=on&var_MCDC=on&var_TCDC=on&var_RH=on&var_TMP=on&var_UGRD=on&var_VGRD=on&all_lev=on&subregion=&toplat=-15&leftlon=24&rightlon=34&bottomlat=-23"
        
        print(retrieve_data_url)
        print(forecast_length_hour_str)
        print(OUTDATA_PATH)
        # sys.exit()
        logger.info(f'Trying to retrieve {retrieve_data_url}...')
        try:
            urllib.request.urlretrieve(retrieve_data_url, f'{OUTDATA_PATH}{out_filename}')#, ProgressBar())
            logger.info(f'Success! Saving file to {OUTDATA_PATH}{out_filename}')
            # time.sleep(1)
        except urllib.error.HTTPError:
            logger.error(f'HTTP Error 404: Could not find {retrieve_data_url}')
            continue

    logger.info(f'This whole thing took {time.time() - start_time} seconds')


def clear_existing_files(directory):

    '''
    Make sure the directory exists and is empty
    '''
    if os.path.isdir(directory):
        logger.info('Clearing files in {}'.format(directory))
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))
    else:
        logger.info('{} does not exist. Creating...'.format(directory))
        Path(directory).mkdir()



def updater():
    schedule.every().day.at("07:30").do(main)
    schedule.every().day.at("19:30").do(main)
    while True:
        schedule.run_pending()
        time.sleep(30)
        

if __name__ == '__main__':
    main()
    # updater()