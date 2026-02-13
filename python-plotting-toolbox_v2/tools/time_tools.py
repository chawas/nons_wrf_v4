import os
import sys
import datetime
import pytz
import numpy as np

def handleInputTimes(input_args, nowTime_aware_local_obj, desired_tz):
    if input_args.start is None:
        print('No start time set as argument. Will use hereNow.')
        input_args.start = nowTime_aware_local_obj #This is in local time as a timezone aware object
    else:
        try:
            input_start = desired_tz.localize(datetime.datetime.strptime(input_args.start, '%Y%m%dT%H'))
            input_args.start = input_start.astimezone(desired_tz)
        except:
            print('Start date must be in the format %Y%m%dT%H, e.g.' + nowTime_aware_local_obj.strftime(format='%Y%m%dT%H'))
            sys.exit()

    if input_args.end is None:
        print('No end time set as argument. Will use hereNow + 4 days.')
        input_args.end = nowTime_aware_local_obj + datetime.timedelta(days=4) #This is in local time as a timezone aware object
    else: 
        try:
            input_end = desired_tz.localize(datetime.datetime.strptime(input_args.end, '%Y%m%dT%H'))
            input_args.end = input_end.astimezone(desired_tz)
        except:
            print('End date must be in the format %Y%m%dT%H, e.g.' + nowTime_aware_local_obj.strftime(format='%Y%m%dT%H'))
            sys.exit()

    return input_args


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

    return base_time


def getForecastValidTime_UTC(filename, greenwich_tz, cycle_format = '%y%m%d%H%M'):
    '''
    Get the forecast valid time based on the filename
    NOTE: This is very specific to the UEMS WRF filename convention of:
          YYMMDDHHMM_wrfout_arw_d01.grb2fHH0000   for forecast lengths of < 100 hours
          YYMMDDHHMM_wrfout_arw_d01.grb2fHHH0000   for forecast lengths of >= 100 hours
    '''
    filename = os.path.basename(filename)
    length_of_date_format = len( datetime.datetime.now().strftime(cycle_format) )
    cycle_date = datetime.datetime.strptime(filename[0:length_of_date_format], cycle_format)
    
    fLength_digits = filename.split('.')[-1].replace('grb2f', '') #Veeeery WRF filename convention specific
    len_of_fLength = len(fLength_digits) 

    if len_of_fLength > 6:
        f_length = int(fLength_digits[0:3])
    else:
        f_length = int(fLength_digits[0:2])
    
    f_valid    = cycle_date + datetime.timedelta(hours=f_length)

    f_valid    = greenwich_tz.localize(f_valid)#fValid.astimezone(greenwich_tz)

    return f_valid


def getFilesBeweenTimes(indataList, start_time, end_time, greenwich_tz):
    grib_use_list = []
    for filename in indataList:
        fValid = getForecastValidTime_UTC(os.path.basename(filename), greenwich_tz)

        if fValid >= start_time and fValid <= end_time:
            grib_use_list.append(filename)

    return grib_use_list


def UTCtoLocal(in_UTC, local_tz):
    '''
    Convert an UTC time stamp t local time
    '''
    greenwich_tz = pytz.timezone('Etc/GMT')

    if in_UTC.tzinfo is None:
        in_UTC_aware = greenwich_tz.localize(in_UTC)
    else:
        in_UTC_aware = in_UTC
    out_local = in_UTC_aware.astimezone(local_tz)

    return out_local

def get_time_stamps_for_acc(accumulation_period, start_of_precipitation_day):
    '''
    Get accumulation times to fill a day based on accumulation period and start of precipitation day
    i.e. acc = 24 and start 06:00 gives one accumulation period
         acc = 12 and start 06:00 gives two periods
    '''
    time_steps = np.arange(start_of_precipitation_day, 24+start_of_precipitation_day, accumulation_period)
    for idx, item in enumerate(time_steps):
        if item >= 24.0:
            time_steps[idx] = item - 24.0
    time_steps = list(map(int, time_steps))
    
    return time_steps


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

    return base_time
