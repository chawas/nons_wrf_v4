import ast
import pytz
import logging

from grib_reader import gribEcCodes, grib_read
from tools import config_tools, time_tools, dataframe_tools
from config import CONFIG, DATA_SOURCE, ACCUMULATED_PRECIPITATION, PRECIP_MULT_FACTOR

APP_NAME = 'gribloader'
PLOTTERS = CONFIG["plotters"]
logger = logging.getLogger("carl-wrf-tools.{}".format(APP_NAME))

wanted_parameters = ast.literal_eval(CONFIG["common"][DATA_SOURCE]["wantedParameters"])
parameter_names = ast.literal_eval(CONFIG["common"][DATA_SOURCE]["parameterNames"])
locations_file = CONFIG["plotters"]["meteograms"]["locationsFile"]
output_time_zone = CONFIG["plotters"]["meteograms"]["timeZone"]
symbols = True


def main(grib_use_list, output_start_time, output_end_time):

    misc_path = './misc/'

    #### CREATE CONFIGURATION FILE FOR ALL CITIES IN ALL PLOTTERS ####
    # Loop over all plotters
    ALL_CITIES = {}
    for plotter in PLOTTERS:
        locations_file = CONFIG["plotters"][plotter]["locationsFile"]
        cities = config_tools.readCitiesConfig(locations_file)
        for citie in cities:
            if citie not in ALL_CITIES:
                ALL_CITIES.update({citie: cities[citie]})
            # print(citie, cities[citie])
        # print(cities)
    # for citie in ALL_CITIES:
    #     print(citie, ALL_CITIES[citie])
    # print(len(ALL_CITIES))

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
    # wanted_parameters = []
    # parameter_names   = []
    for level_in_hPa in isobaric_levels_in_hPa:
        wanted_parameters.append(tuple((level_in_hPa, 't')))
        wanted_parameters.append(tuple((level_in_hPa, 'r')))
        parameter_names.append('t_{}'.format(level_in_hPa))
        parameter_names.append('r_{}'.format(level_in_hPa))

    ### HANDLE METEOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    # This cities_dict is where we initially put the data
    # cities_Dict  = config_tools.readCitiesConfig(locations_file)
    
    ### HANDLE TIME GENERALLY ###
    #What time is it here and now??
    greenwich_tz   = pytz.timezone('Greenwich')
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
    # logger.info(grib_use_list)
    # grib_use_list = time_tools.getFilesBeweenTimes(grib_use_list, fc_startHour_UTC, fc_endHour_UTC, desired_tz) # Get all files between the correct times. NOTE: An extra instance of this function call to ensure 5 days for meteograms
    for grib_use in grib_use_list:
        logger.info('    Working with time step ' + time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz).strftime('%Y%m%d %H:%M'))
        logger.info('    Which in specified time zone is ' + time_tools.UTCtoLocal( time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz), desired_tz).strftime('%Y%m%d %H:%M') )
        logger.info('        File: ' + grib_use)

        lats, lons, data = grib_read.main(grib_use, parameter_names, wanted_parameters, grib_use_list)

        # Loop over cities from the meteogram configuration file
        city_count = 0
        for city in ALL_CITIES.keys():

            # if 'datetimes_utc' not in cities_Dict[city]:
            #     cities_Dict[city].update({'datetimes_utc' : []})
            # cities_Dict[city]['datetimes_utc'].append(getForecastValidTime_UTC(grib_use, PREFIX, greenwich_tz))#.strftime('%Y%m%d_%H'))
            
            if 'datetimes_local' not in ALL_CITIES[city]:
                ALL_CITIES[city].update({'datetimes_local' : []})
            ALL_CITIES[city]['datetimes_local'].append( time_tools.UTCtoLocal( time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz), desired_tz ) )
            # cities_Dict[city]['datetimes_local'].append( getForecastValidTime_UTC(grib_use, PREFIX, greenwich_tz) )

            if city_count == 0: #Add datetime objects to citiesDict only once during the first city loop
                timeIndexArray_UTC.append(time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz))#.strftime('%Y%m%d%H'))
                timeIndexArray.append( time_tools.UTCtoLocal( time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz), desired_tz ) )
                # timeIndexArray.append( getForecastValidTime_UTC(grib_use, PREFIX, greenwich_tz) )
            
            # The coordinates for the current city
            latP = ALL_CITIES[city]['coords'][0]
            lonP = ALL_CITIES[city]['coords'][1]

            # Loop over wanted_parameters
            for param in parameter_names:
                # Add parameter to city if not already there
                if param not in ALL_CITIES[city]:
                    ALL_CITIES[city].update({param : []})

                # Find the closest grid point and get the data from it
                closest_point = gribEcCodes.closest_gridpoint(latP, lonP, lats, lons, version = '2d', maxDistInDegrees = 1, n = 1)
                closest_point_data = data[param][closest_point[0], closest_point[1]]

                ALL_CITIES[city][param].append(closest_point_data)

            city_count += 1

   
    ### CREATE A PANDAS DATAFRAME FROM EVERYTHING IN THE CITIES_DICT ###
    logger.info(f'Creating a dataframe with data for cities...{list(ALL_CITIES.keys())}')
    df_multi = dataframe_tools.createMultiIndexDataFrame(ALL_CITIES, timeIndexArray, parameter_names)

    match_timestamps = ['00:00', '06:00', '12:00', '18:00']  # Matching hour timestamps for parameter accumulation below
    
    # print(df_multi)
    df_multi = dataframe_tools.calcU_df(df_multi, parameter_names)
    df_multi = dataframe_tools.calc6U_df(df_multi, parameter_names, match_timestamps, window_len = 6)
    df_multi, new_prec_column_6h  = dataframe_tools.calc_acc_prec_in_df(df_multi, match_timestamps, ACCUMULATED_PRECIPITATION, PRECIP_MULT_FACTOR, window_len = 6)
    df_multi, new_precip_column_24 = dataframe_tools.calc_acc_prec_in_df(df_multi, ['00:00'], ACCUMULATED_PRECIPITATION, PRECIP_MULT_FACTOR, window_len = 24)
    df_multi = dataframe_tools.calcTotalCloudCover(df_multi)
    df_multi = dataframe_tools.getWeatherType(df_multi, parameter_names, match_timestamps, misc_path, new_prec_column_6h) # For meteograms
    df_multi = dataframe_tools.getWeatherType(df_multi, parameter_names, ['00:00'], misc_path, new_precip_column_24) # For symbograms

    # Pickla här så att det går att köra create_symbogram_df() 
    # import pickle, sys
    # dbfile = open('df_multi.pickle', 'wb')
    # pickle.dump(df_multi, dbfile)
    # dbfile.close()
    # props = {
    #     'desired_tz': desired_tz,
    #     'greenwich_tz': greenwich_tz,
    #     }
    # pfile = open('symbogram_props.pickle', 'wb')
    # pickle.dump(props, pfile)
    # pfile.close()
    # sys.exit()

    return df_multi, desired_tz, greenwich_tz

def load_pickle_data():
    import pickle
    fh_data = open('df_multi.pickle', 'rb')
    data = pickle.load(fh_data)
    fh_data.close()
    fh_probs = open('symbogram_props.pickle', 'rb')
    props = pickle.load(fh_probs)
    fh_probs.close()

    return data, props['desired_tz'], props['greenwich_tz']