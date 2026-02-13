# -*- coding: utf-8 -*-

import ast
import pytz
import logging

import pandas as pd

from grib_reader import gribEcCodes, grib_read

from tools import config_tools, time_tools, dataframe_tools, reset_folders
from config import CONFIG, DATA_SOURCE, ACCUMULATED_PRECIPITATION, PRECIP_MULT_FACTOR

APP_NAME = 'extract_acc_precip'
logger = logging.getLogger("carl-wrf-tools.{}".format(APP_NAME))

APP_CONFIG = CONFIG["extracters"][APP_NAME]
wanted_parameters = ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["wantedParameters"])
parameter_names =  ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["parameterNames"])
locations_file = APP_CONFIG["locationsFile"]
start_of_precipitation_day = APP_CONFIG["start_of_precipitation_day"]
accumulation_times = ast.literal_eval(APP_CONFIG["accumulation_times"])
output_time_zone = APP_CONFIG["timeZone"]
outdata_path = APP_CONFIG["outdataPath"]

def main(grib_use_list, output_start_time, output_end_time):

    reset_folders.refresh(outdata_path, archive=False)  # Clean the outdata folders for this run

    ### HANDLE METEOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    # This cities_dict is where we initially put the data
    cities_Dict  = config_tools.readCitiesConfig(locations_file)
    
    ### HANDLE TIME GENERALLY ###
    #What time is it here and now??
    greenwich_tz   = pytz.timezone('Etc/GMT')
    if output_time_zone == 'Greenwich' or output_time_zone == 'UTC':
        desired_tz = greenwich_tz
        logger.info('Will create output in time zone {}'.format(desired_tz))
    else:
        try:
            desired_tz   = pytz.timezone(output_time_zone)  # Try to find the user specified time zone
            logger.info('Will create output in time zone {}'.format(desired_tz))
        except:
            logger.warning('Time zone {} not valid. Will use UTC times for output'.format(output_time_zone))
            logger.debug('Look up the correct string for your desired time zone')
            desired_tz = greenwich_tz

    fc_startHour_UTC = output_start_time.astimezone(greenwich_tz) #This is from when the meteogram should start in UTC, i.e. from what GRIB file time step
    fc_endHour_UTC   = output_end_time.astimezone(greenwich_tz)   #This is from the meteogram should end in UTC, i.e. from what GRIB file time step

    fc_startHour_local_aware = time_tools.UTCtoLocal(output_start_time, desired_tz)
    fc_endHour_local_aware   = time_tools.UTCtoLocal(output_end_time, desired_tz)
   
    if desired_tz == greenwich_tz:
        logger.info(f'The start time for {APP_NAME} is set to ' + fc_startHour_local_aware.strftime('%Y%m%dT%H') + ' UTC.')
        logger.info(f'The end time for {APP_NAME} is set to   ' + fc_endHour_local_aware.strftime('%Y%m%dT%H') + ' UTC.')
    else:
        logger.info(f'The start time for {APP_NAME} is set to ' + fc_startHour_local_aware.strftime('%Y%m%dT%H') + ' local time.')
        logger.info(f'The end time for {APP_NAME} is set to   ' + fc_endHour_local_aware.strftime('%Y%m%dT%H') + ' local time.')

    logger.info('Which means')
    fc_startHour_UTC = fc_startHour_local_aware.astimezone(greenwich_tz) #This is from when the meteogram should start in UTC, i.e. from what GRIB file time step
    fc_endHour_UTC   = fc_endHour_local_aware.astimezone(greenwich_tz)   #This is from the meteogram should end in UTC, i.e. from what GRIB file time step
    logger.info(fc_startHour_UTC.strftime('%Y%m%dT%H') + ' UTC.')
    logger.info(fc_endHour_UTC.strftime('%Y%m%dT%H') + ' UTC.')

    ### THIS IS WHERE THE REAL STUFF STARTS ###
    timeIndexArray_UTC = [] #for UTC time objects
    timeIndexArray     = [] #for local time objects

    # Loop over GRIB2-files, parameters, and cities/regions (most efficient to open GRIB2 file only once)
    # grib_use_list = time_tools.getFilesBeweenTimes(grib_use_list, PREFIX, fc_startHour_UTC, fc_endHour_UTC, desired_tz) # Get all files between the correct times. NOTE: An extra instance of this function call to ensure 5 days for meteograms
    for grib_use in grib_use_list:
        base_time_UTC   = greenwich_tz.localize(time_tools.get_forecast_basetime_UTC(grib_use))
        validTime_UTC   = time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz)
        validTime_local = time_tools.UTCtoLocal( validTime_UTC, desired_tz )
        
        logger.info('Working with time step {}'.format(validTime_UTC.strftime('%Y%m%d %H:%M')))
        if desired_tz != greenwich_tz:
            logger.info('    Which in specified time zone is {}'.format(validTime_local.strftime('%Y%m%d %H:%M')))
        logger.info('    File: ' + grib_use)

        if validTime_UTC == base_time_UTC:
            logger.warning('Precipitation data usually not found in first forecast time step. Skipping!')
        else:
            lats, lons, data = grib_read.main(grib_use, parameter_names, wanted_parameters, grib_use_list)

            # Loop over cities from the meteogram configuration file
            city_count = 0
            for city in cities_Dict.keys():

                # if 'datetimes_utc' not in cities_Dict[city]:
                #     cities_Dict[city].update({'datetimes_utc' : []})
                # cities_Dict[city]['datetimes_utc'].append(getForecastValidTime_UTC(grib_use, prefix, greenwich_tz))#.strftime('%Y%m%d_%H'))
                
                if 'datetimes_local' not in cities_Dict[city]:
                    cities_Dict[city].update({'datetimes_local' : []})
                cities_Dict[city]['datetimes_local'].append( time_tools.UTCtoLocal( time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz), desired_tz ) )
                # cities_Dict[city]['datetimes_local'].append( getForecastValidTime_UTC(grib_use, prefix, greenwich_tz) )

                if city_count == 0: #Add datetime objects to citiesDict only once during the first city loop
                    timeIndexArray_UTC.append(time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz))#.strftime('%Y%m%d%H'))
                    timeIndexArray.append( time_tools.UTCtoLocal( time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz), desired_tz ) )
                    # timeIndexArray.append( getForecastValidTime_UTC(grib_use, prefix, greenwich_tz) )
                
                # The coordinates for the current city
                latP = cities_Dict[city]['coords'][0]
                lonP = cities_Dict[city]['coords'][1]

                # Loop over wanted_parameters
                for param in parameter_names:
                    # Add parameter to city if not already there
                    if param not in cities_Dict[city]:
                        cities_Dict[city].update({param : []})

                    # Find the closest grid point and get the data from it
                    closest_point = gribEcCodes.closest_gridpoint(latP, lonP, lats, lons, version = '2d', maxDistInDegrees = 1, n = 1)
                    closest_point_data = data[param][closest_point[0], closest_point[1]]

                    cities_Dict[city][param].append(closest_point_data)

                city_count += 1
   
    ### CREATE A PANDAS DATAFRAME FROM EVERYTHING IN THE CITIES_DICT ###
    df_multi = dataframe_tools.createMultiIndexDataFrame(cities_Dict, timeIndexArray, parameter_names)

    for accumulation_time in accumulation_times:
        acc_time_ints = time_tools.get_time_stamps_for_acc(accumulation_time, start_of_precipitation_day)
        acc_time_stamps = [f'{n:02}:00' for n in acc_time_ints]  # Create %H%M time stamps to fit with pandas
    
        logger.info('    Accumulating precipitation to {} hours'.format(accumulation_time))
        df_extract, new_acc_column = dataframe_tools.calc_acc_prec_in_df(df_multi, acc_time_stamps, ACCUMULATED_PRECIPITATION, PRECIP_MULT_FACTOR, window_len=accumulation_time)
        idx = pd.IndexSlice
        df_extract = df_extract.loc[idx[:],idx[:,[new_acc_column]]].dropna()#.round(1)
        # df_extract[df_extract < 0.0] = 0  # Round precipitation values below zero to zero (a rounding mishap in rolling, I presume)
        # pd.set_option('display.chop_threshold', 0.001)

        out_file_name = '{}precipitation_acc{}h_cycle{}_{}-{}.csv'.format(outdata_path, accumulation_time, base_time_UTC.strftime('%Y%m%dT%H'), output_start_time.strftime('%Y%m%dT%H'), output_end_time.strftime('%Y%m%dT%H'))
        df_extract.loc[idx[:],idx[:,[new_acc_column]]].dropna().to_csv(out_file_name, sep='\t', float_format='%.1f')


if __name__ == '__main__':
    print('This is the precipitation extraction module')
