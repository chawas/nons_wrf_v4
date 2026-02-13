import time
import datetime
import schedule
from log import logger

# Local imports
import check_times
from gribloader import gribloading
from plotters import symbograms,  meteograms, acc_precip, cloudcover, t_phi

print("Running plot_runner.py")
print("Imported check_times from:", check_times.__file__)

def runner():

    s_time = time.time()

    logger.info('Searching for available data...')
    days_ahead = 16
    cycle_to_use, indata_files = check_times.find_latest_available_forecast(days_ahead)
    # next_start_of_day = datetime.datetime(cycle_to_use.year, cycle_to_use.month, cycle_to_use.day, 0) + datetime.timedelta(days=1)
    logger.info('Found cycle {} with data for {} days ahead'.format(cycle_to_use.strftime('%Y-%m-%d %H:%M'), days_ahead))

    gribloading_start = time.time()
    logger.info('Starting loading gribfiles...')
    df, desired_tz, greenwich_tz = gribloading.main(indata_files, cycle_to_use, cycle_to_use + datetime.timedelta(days=days_ahead)) #, 'Africa/Harare')
    # df, desired_tz, greenwich_tz = gribloading.load_pickle_data()
    logger.info("Total time for gribloading: {} seconds".format(time.time() - gribloading_start))
    
    symbograms_start = time.time()
    logger.info('Starting symbograms...')
    symbograms.main(df, indata_files, cycle_to_use, cycle_to_use + datetime.timedelta(days=days_ahead), 'Africa/Harare')
    logger.info("Total time for symbograms: {} seconds".format(time.time() - symbograms_start))

    meteograms_start = time.time()
    logger.info('Starting meteograms...')
    # NOTE: days_ahead set to 5 for meteograms since they are graphically adapted for that
    meteograms.main(df, indata_files, cycle_to_use, cycle_to_use + datetime.timedelta(days=10), desired_tz, greenwich_tz)  # Start and end times set in UTC.  'Africa/Harare', 'Greenwich', or 'UTC' for time zone
    logger.info("Total time for meteograms: {} seconds".format(time.time() - meteograms_start))

    tphi_start = time.time()
    logger.info('Starting tephigrams plots...')
    t_phi.main(df, indata_files, cycle_to_use, cycle_to_use + datetime.timedelta(days=days_ahead))
    logger.info("Total time for tephigrams: {} seconds".format(time.time() - tphi_start))

    acc_precip_start = time.time()
    logger.info('Starting accumulated precipitation plots...')
    acc_precip.main(indata_files, cycle_to_use, cycle_to_use + datetime.timedelta(days=days_ahead))
    logger.info("Total time for acc_precip: {} seconds".format(time.time() - acc_precip_start))

    cloudcover_start = time.time()
    logger.info('Starting cloudcover plots...')
    cloudcover.main(indata_files, cycle_to_use, cycle_to_use + datetime.timedelta(days=days_ahead))
    logger.info("Total time for cloudcover: {} seconds".format(time.time() - cloudcover_start))

    logger.info('Total time for plot_runner: {} seconds'.format(time.time() - s_time))


def updater():
    logger.info('Starting updater...')
    schedule.every().day.at("07:40").do(runner)
    schedule.every().day.at("19:40").do(runner)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == '__main__':
    runner()
    # updater()
