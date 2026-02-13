import time
import datetime
import schedule
from log import logger

# Local imports
import check_times
from gribloader import gribloading
from plotters import symbograms_winter, symbograms_summer, meteograms, acc_precip, cloudcover, t_phi

print("Running plot_runner.py")
print("Imported check_times from:", check_times.__file__)


def select_symbogram_module(run_date: datetime.datetime):
    """
    Decide which symbogram module to use based on date.
    - Winter: from 1st May to 31st August
    - Summer: from 1st September to 30th April
    """
    if 5 <= run_date.month <= 8:  # May–August
        return symbograms_winter
    else:  # September–April
        return symbograms_summer


def runner():
    s_time = time.time()

    logger.info('Searching for available data...')
    days_ahead = 16
    cycle_to_use, indata_files = check_times.find_latest_available_forecast(days_ahead)
    logger.info('Found cycle {} with data for {} days ahead'.format(cycle_to_use.strftime('%Y-%m-%d %H:%M'), days_ahead))

    gribloading_start = time.time()
    logger.info('Starting loading gribfiles...')
    df, desired_tz, greenwich_tz = gribloading.main(
        indata_files,
        cycle_to_use,
        cycle_to_use + datetime.timedelta(days=days_ahead)
    )
    logger.info("Total time for gribloading: {} seconds".format(time.time() - gribloading_start))

    # --- Select routine dynamically ---
    symbograms_module = select_symbogram_module(cycle_to_use)
    symbograms_start = time.time()
    logger.info(f'Starting {symbograms_module.__name__}...')
    symbograms_module.main(df, indata_files, cycle_to_use,
                           cycle_to_use + datetime.timedelta(days=days_ahead),
                           'Africa/Harare')
    logger.info("Total time for symbograms: {} seconds".format(time.time() - symbograms_start))

    meteograms_start = time.time()
    logger.info('Starting meteograms...')
    meteograms.main(df, indata_files, cycle_to_use,
                    cycle_to_use + datetime.timedelta(days=10),
                    desired_tz, greenwich_tz)
    logger.info("Total time for meteograms: {} seconds".format(time.time() - meteograms_start))

    tphi_start = time.time()
    logger.info('Starting tephigrams plots...')
    t_phi.main(df, indata_files, cycle_to_use,
               cycle_to_use + datetime.timedelta(days=days_ahead))
    logger.info("Total time for tephigrams: {} seconds".format(time.time() - tphi_start))

    acc_precip_start = time.time()
    logger.info('Starting accumulated precipitation plots...')
    acc_precip.main(indata_files, cycle_to_use,
                    cycle_to_use + datetime.timedelta(days=days_ahead))
    logger.info("Total time for acc_precip: {} seconds".format(time.time() - acc_precip_start))

    cloudcover_start = time.time()
    logger.info('Starting cloudcover plots...')
    cloudcover.main(indata_files, cycle_to_use,
                    cycle_to_use + datetime.timedelta(days=days_ahead))
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
