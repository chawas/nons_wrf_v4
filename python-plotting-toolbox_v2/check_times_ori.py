'''Look in the indata folder end determine latest available start and end times depending on desired days'''

import os
import sys
import datetime
import glob
import pytz
import logging


from tools import time_tools
from config import INDATA_PATH, PREFIX, DOMAIN

logger = logging.getLogger("carl-wrf-tools.check_times")

def find_latest_available_forecast(days_ahead, force_cycle = None):

    # days = 5  # Number of days to find data for
    cycle_format = '%y%m%d%H%M'

    greenwich_tz   = pytz.timezone('Etc/GMT')

#### PATHS AND PREFIXES ###
    # io_path   = './IO/'
   
    # with open(io_path + 'indata_path.txt') as f:
    #     in_line = f.readlines()[0].strip('\n')
    # indata_path = in_line.split('=')[-1]
    # with open(io_path + 'prefix.txt') as f:
    #     in_line = f.readlines()[0].strip('\n')
    # prefix = in_line.split('=')[-1]

    if force_cycle is not None:
        cycle_to_use = datetime.datetime.strptime(force_cycle, cycle_format)
    else:

        # Find all the cycle dates in directory
        base_dates_in_indata_path = []
        for filename in glob.glob(INDATA_PATH + '*'):
            base_date = time_tools.get_forecast_basetime_UTC(os.path.basename(filename), cycle_format = cycle_format)
            if base_date not in base_dates_in_indata_path:
                base_dates_in_indata_path.append(base_date)

        # Find cycle with corresponding forecast length
        for base_date in sorted(base_dates_in_indata_path, reverse = True):  # Loop through found base times in reverse (latest first)
            forecast_days = []
            data_files = glob.glob(INDATA_PATH + base_date.strftime(cycle_format) + PREFIX + '*')

            for file in data_files:
                date_diff = (time_tools.getForecastValidTime_UTC(os.path.basename(file), greenwich_tz, cycle_format = '%y%m%d%H%M') - greenwich_tz.localize(base_date)).days  # Difference between forecast length and base_date
                forecast_days.append( date_diff )

            if max(forecast_days) >= days_ahead:  # If forecast length long enough...
                cycle_to_use = base_date   # Use this cycle, and break out of the loop
                break
            else:
                logger.error(f'Could not find forecast files with data for {days_ahead} days ahead\nABORTING!')
                sys.exit()

    # Find data files with correct cycle and forecast legnth
    start_time = greenwich_tz.localize(cycle_to_use)
    end_time   = greenwich_tz.localize(cycle_to_use + datetime.timedelta(days=days_ahead))
    # data_files = [x for x in glob.glob(INDATA_PATH + base_date.strftime(cycle_format) + PREFIX + '??.grb2f??????')] #Take all files for fLength < 100 hours
    # data_files = sorted(data_files) + sorted( [x for x in glob.glob(INDATA_PATH + base_date.strftime(cycle_format) + PREFIX + '??.grb2f???????')] ) #Take all files for fLength >= 100 hours
    data_files = [x for x in glob.glob(INDATA_PATH + base_date.strftime(cycle_format) + PREFIX + DOMAIN + '.grb2f*')]
    grib_use_list = time_tools.getFilesBeweenTimes(data_files, start_time, end_time, greenwich_tz) # Get all files between the correct times

    return cycle_to_use, grib_use_list

    
if __name__ == '__main__':
    main()
