
import os
import sys
import datetime
import pytz
import numpy as np

def get_forecast_basetime_UTC(filename, cycle_format = '%y%m%d%H%M'):
    '''
    Get the forecast valid time based on the filename
    NOTE: This is very specific to the UEMS WRF filename convention of:
          YYMMDDHHMM_wrfout_arw_d01.grb2fHH0000   for forecast lengths of < 100 hours
          YYMMDDHHMM_wrfout_arw_d01.grb2fHHH0000   for forecast lengths of >= 100 hours
    '''
    filename = os.path.basename(filename)
    length_of_date_format = len( datetime.datetime.now().strftime(cycle_format) )
    base_time = datetime.datetime.strptime(filename[0:length_of_date_format], cycle_format)
    print(base_time)
    return base_time
filename ="2509160000_gfs_global.grb2f0000000"

get_forecast_basetime_UTC(filename)