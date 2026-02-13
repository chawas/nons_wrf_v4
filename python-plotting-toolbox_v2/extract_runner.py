import time
import datetime
# import schedule
from log import logger

# Local imports
import check_times
from extracters import extract_acc_precip, extract_temperature

def runner():

    logger.info('Searching for available data...')
    days_ahead = 16
    
    cycle_to_use, indata_files = check_times.find_latest_available_forecast(days_ahead)
    next_start_of_day = datetime.datetime(cycle_to_use.year, cycle_to_use.month, cycle_to_use.day, 0) + datetime.timedelta(days=1)
    logger.info('Found cycle {} with data for {} days ahead'.format(cycle_to_use.strftime('%Y-%m-%d %H:%M'), days_ahead))

    precip_extract_start = time.time()
    logger.info('Starting extraction of precipitation...')
    extract_acc_precip.main(indata_files, cycle_to_use, cycle_to_use + datetime.timedelta(days=days_ahead))  # Start and end times set in UTC.  'Africa/Harare', 'Greenwich', or 'UTC' for time zone
    logger.info("Total time for precip extract: {} seconds".format(time.time() - precip_extract_start))

    temp_extract_start = time.time()
    logger.info('Starting extraction of temperature...')
    extract_temperature.main(indata_files, cycle_to_use, cycle_to_use + datetime.timedelta(days=days_ahead))  # Start and end times set in UTC.  'Africa/Harare', 'Greenwich', or 'UTC' for time zone
    logger.info("Total time temp extract: {} seconds".format(time.time() - temp_extract_start))

def updater():
    start_updater = time.time()
    logger.info('Starting updater...')

    schedule.every().day.at("08:00").do(runner)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    
    runner()

    #updater()
