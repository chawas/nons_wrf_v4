'''
Creating tephigrams based on data from WRF GRIB2 files from a UEMS WRF setup

***NOTE: This script assumes that data is available with 1 hour intervalls during the entire forecast period!
'''

import ast
import logging

import numpy as np
import pandas as pd


# Now make a simple example using the custom projection.
import matplotlib.pyplot as plt

from tools import config_tools, calc_tools, reset_folders
from tephigram_python import Tephigram
from config import CONFIG

APP_NAME = 'tephigrams'
logger = logging.getLogger("carl-wrf-tools.{}".format(APP_NAME))

APP_CONFIG = CONFIG["plotters"][APP_NAME]
# wanted_parameters = ast.literal_eval(APP_CONFIG["wantedParameters"])
# parameter_names =  ast.literal_eval(APP_CONFIG["parameterNames"])
locations_file = APP_CONFIG["locationsFile"]
output_time_zone = APP_CONFIG["timeZone"]
match_timestamps = ast.literal_eval(APP_CONFIG["matchTimestamps"])
outdata_path = APP_CONFIG["outdataPath"]

def main(df, grib_use_list, output_start_time, output_end_time):
    
    reset_folders.refresh(outdata_path, archive=False)  # Clean the outdata folders for this run

    ### HANDLE METEOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    # This cities_dict is where we initially put the data
    cities_Dict  = config_tools.readCitiesConfig(locations_file)

    # Extract isobaric levels in hPa from gribfile
    import eccodes as g
    iid = g.codes_index_new_from_file(grib_use_list[0],["shortName", "typeOfLevel"])
    g.codes_index_select(iid, 'typeOfLevel', 'isobaricInhPa')
    g.codes_index_select(iid, 'shortName', 't')
    isobaric_levels_in_hPa = []
    while True:
        gid = g.codes_new_from_index(iid)
        if gid is None:
            break
        level = g.codes_get(gid, 'level')
        isobaric_levels_in_hPa.append(level)

    # Setup parameters
    wanted_parameters = []
    parameter_names   = []
    for level_in_hPa in isobaric_levels_in_hPa:
        wanted_parameters.append(tuple((level_in_hPa, 't')))
        wanted_parameters.append(tuple((level_in_hPa, 'r')))
        parameter_names.append('t_{}'.format(level_in_hPa))
        parameter_names.append('r_{}'.format(level_in_hPa))


    # ### HANDLE TIME GENERALLY ###
    # #What time is it here and now??
    # greenwich_tz   = pytz.timezone('Greenwich')
    # if output_time_zone == 'Greenwich' or output_time_zone == 'UTC':
    #     desired_tz = greenwich_tz
    #     logger.info('Will create output in time zone {}'.format(desired_tz))
    # else:
    #     try:
    #         desired_tz   = pytz.timezone(output_time_zone)  # Try to find the user specified time zone
    #         logger.info('Will create output in time zone {}'.format(desired_tz))
    #     except:
    #         logger.warning('Time zone {} not valid. Will use UTC times for output'.format(output_time_zone))
    #         logger.debug('Look up the correct string for your desired time zone')
    #         desired_tz = greenwich_tz



    # fc_startHour_UTC = output_start_time.astimezone(greenwich_tz) #This is from when the meteogram should start in UTC, i.e. from what GRIB file time step
    # fc_endHour_UTC   = output_end_time.astimezone(greenwich_tz)   #This is from the meteogram should end in UTC, i.e. from what GRIB file time step

    # fc_startHour_local_aware = time_tools.UTCtoLocal(output_start_time, desired_tz)
    # fc_endHour_local_aware   = time_tools.UTCtoLocal(output_end_time, desired_tz)
   
    # if desired_tz == greenwich_tz:
    #     logger.info(f'The start time for {APP_NAME} is set to ' + fc_startHour_local_aware.strftime('%Y%m%dT%H') + ' UTC.')
    #     logger.info(f'The end time for {APP_NAME} is set to   ' + fc_endHour_local_aware.strftime('%Y%m%dT%H') + ' UTC.')
    # else:
    #     logger.info(f'The start time for {APP_NAME} is set to ' + fc_startHour_local_aware.strftime('%Y%m%dT%H') + ' local time.')
    #     logger.info(f'The end time for {APP_NAME} is set to   ' + fc_endHour_local_aware.strftime('%Y%m%dT%H') + ' local time.')

    # logger.info('Which means')
    # fc_startHour_UTC = fc_startHour_local_aware.astimezone(greenwich_tz) #This is from when the meteogram should start in UTC, i.e. from what GRIB file time step
    # fc_endHour_UTC   = fc_endHour_local_aware.astimezone(greenwich_tz)   #This is from the meteogram should end in UTC, i.e. from what GRIB file time step
    # logger.info(fc_startHour_UTC.strftime('%Y%m%dT%H') + ' UTC.')
    # logger.info(fc_endHour_UTC.strftime('%Y%m%dT%H') + ' UTC.')

   
    # ### THIS IS WHERE THE REAL STUFF STARTS ###
    # timeIndexArray_UTC = [] #for UTC time objects
    # timeIndexArray     = [] #for local time objects

    # # Loop over GRIB2-files, parameters, and cities/regions (most efficient to open GRIB2 file only once)
    # for grib_use in grib_use_list:
    #     logger.info('    Working with time step ' + time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz).strftime('%Y%m%d %H:%M'))
    #     logger.info('    Which in specified time zone is ' + time_tools.UTCtoLocal( time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz), desired_tz).strftime('%Y%m%d %H:%M') )
    #     logger.info('        File: ' + grib_use)

    #     lats, lons, data = grib_read.main(grib_use, parameter_names, wanted_parameters, grib_use_list)

    #     # Loop over cities from the meteogram configuration file
    #     city_count = 0
    #     for city in cities_Dict.keys():

    #         if 'datetimes_local' not in cities_Dict[city]:
    #             cities_Dict[city].update({'datetimes_local' : []})
    #         cities_Dict[city]['datetimes_local'].append( time_tools.UTCtoLocal( time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz), desired_tz ) )
    #         # cities_Dict[city]['datetimes_local'].append( getForecastValidTime_UTC(grib_use, PREFIX, greenwich_tz) )

    #         if city_count == 0: #Add datetime objects to citiesDict only once during the first city loop
    #             timeIndexArray_UTC.append(time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz))#.strftime('%Y%m%d%H'))
    #             timeIndexArray.append( time_tools.UTCtoLocal( time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz), desired_tz ) )
    #             # timeIndexArray.append( getForecastValidTime_UTC(grib_use, PREFIX, greenwich_tz) )
            
    #         # The coordinates for the current city
    #         latP = cities_Dict[city]['coords'][0]
    #         lonP = cities_Dict[city]['coords'][1]

    #         # Loop over wanted_parameters
    #         for param in parameter_names:
    #             # Add parameter to city if not already there
    #             if param not in cities_Dict[city]:
    #                 cities_Dict[city].update({param : []})

    #             # Find the closest grid point and get the data from it
    #             closest_point = gribEcCodes.closest_gridpoint(latP, lonP, lats, lons, version = '2d', maxDistInDegrees = 1, n = 1)
    #             closest_point_data = data[param][closest_point[0], closest_point[1]]

    #             cities_Dict[city][param].append(closest_point_data)

    #         city_count += 1

   
    ### CREATE A PANDAS DATAFRAME FROM EVERYTHING IN THE CITIES_DICT ###
    # logger.info('Creating a dataframe with data for cities...')
    # df_multi = dataframe_tools.createMultiIndexDataFrame(cities_Dict, timeIndexArray, parameter_names)
    # match_timestamps = ['00:00', '06:00', '12:00', '18:00']
    logger.info('Creating tephigrams...')
    createTephigram(df, match_timestamps, parameter_names, isobaric_levels_in_hPa, outdata_path)


def createTephigram(df, match_timestamps, parameter_names, isobaric_levels_in_hPa, outdata_path):

    for city in df.columns.levels[0]:
        
        ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
        # Read the configuration file and create a dictionary for each listed city
        tephigram_cities  = config_tools.readCitiesConfig(locations_file)
        if city in tephigram_cities:
            logger.info('    Working with location: {}'.format(city))

            df_time = pd.DataFrame( df.loc[df.index.strftime('%H:%M').isin(match_timestamps), (city)] )
            
            for time_index in df_time.index:
                plt.close('all')
                tephigram = Tephigram()
                temperature_array = []
                dew_point_array   = []
                for pressure in isobaric_levels_in_hPa:
                    t_param = 't_{}'.format(pressure)
                    r_param = 'r_{}'.format(pressure)
                    temperature_array.append(df_time.loc[time_index, t_param] - 273.15)
                    dew_point_array.append(calc_tools.dewT( df_time.loc[time_index, t_param] - 273.15, df_time.loc[time_index, r_param] / 100.0 ))

                
                outname = outdata_path + city + '_' + time_index.strftime('%Y-%m-%d_%H') + '.png'
                tephigram.plot_sounding(P=np.array(isobaric_levels_in_hPa), T=np.array(temperature_array), T_dp=np.array(dew_point_array))
                # parcel_info = tephigram.plot_test_parcel(z=z, P=P, T=T, RH=RH)
                tephigram.savefig(outname)
        # else:
        #     print(f'{city} was filtered out to fit {APP_NAME} cities.')
            

if __name__ == '__main__':
    print('Tephigram module')