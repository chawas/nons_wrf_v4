'''Look in the indata folder and determine latest available start and end times depending on desired days'''

import os
import sys
import datetime
import glob
import pytz
import logging

from tools import time_tools
from config import INDATA_PATH, PREFIX, DOMAIN

logger = logging.getLogger("carl-wrf-tools.check_times")

def find_latest_available_forecast(days_ahead, force_cycle=None):
    cycle_format = '%y%m%d%H%M'
    greenwich_tz = pytz.timezone('Etc/GMT')

    if force_cycle is not None:
        cycle_to_use = datetime.datetime.strptime(force_cycle, cycle_format)
    else:
        cycle_to_use = None  # Prevent UnboundLocalError

        # Find all unique cycle base dates
        base_dates_in_indata_path = []
        for filename in glob.glob(os.path.join(INDATA_PATH, '*')):
            try:
                base_date = time_tools.get_forecast_basetime_UTC(
                    os.path.basename(filename), cycle_format=cycle_format)
                if base_date not in base_dates_in_indata_path:
                    base_dates_in_indata_path.append(base_date)
            except Exception as e:
                logger.warning(f"⛔ Skipping file '{filename}' due to error: {e}")

        # Try cycles in reverse (latest first)
        for base_date in sorted(base_dates_in_indata_path, reverse=True):
            forecast_days = []
            data_files = glob.glob(
                os.path.join(INDATA_PATH, base_date.strftime(cycle_format) + PREFIX + '*'))

            for file in data_files:
                try:
                    valid_time = time_tools.getForecastValidTime_UTC(
                        os.path.basename(file), greenwich_tz, cycle_format=cycle_format)
                    date_diff = (valid_time - greenwich_tz.localize(base_date)).days
                    forecast_days.append(date_diff)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse forecast valid time from '{file}': {e}")

            if forecast_days and max(forecast_days) >= days_ahead:
                cycle_to_use = base_date
                break  # Found a valid cycle

        if cycle_to_use is None:
            logger.error(f"❌ No suitable forecast cycle found for {days_ahead} days ahead in '{INDATA_PATH}'")
            raise RuntimeError("No forecast cycle found.")

    start_time = greenwich_tz.localize(cycle_to_use)
    end_time = greenwich_tz.localize(cycle_to_use + datetime.timedelta(days=days_ahead))

    data_files = glob.glob(
        os.path.join(INDATA_PATH, cycle_to_use.strftime(cycle_format) + PREFIX + DOMAIN + '.grb2f*'))

    grib_use_list = time_tools.getFilesBeweenTimes(data_files, start_time, end_time, greenwich_tz)

    return cycle_to_use, grib_use_list


if __name__ == '__main__':
    print(find_latest_available_forecast(10))  # test with 10-day forecast
