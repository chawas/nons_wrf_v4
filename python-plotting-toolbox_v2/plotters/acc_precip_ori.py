# -*- coding: utf-8 -*-

import os
import ast
import pytz
import logging

import numpy as np

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from grib_reader import grib_read

from tools import time_tools, reset_folders
from config import CONFIG, DATA_SOURCE, ACCUMULATED_PRECIPITATION, PRECIP_MULT_FACTOR

APP_NAME = 'acc_precip'
logger = logging.getLogger("carl-wrf-tools.{}".format(APP_NAME))

APP_CONFIG = CONFIG["plotters"][APP_NAME]
wanted_parameters = ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["wantedParameters"])
parameter_names =  ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["parameterNames"])
locations_file = APP_CONFIG["locationsFile"]
output_time_zone = APP_CONFIG["timeZone"]
start_of_precipitation_day = APP_CONFIG["start_of_precipitation_day"]
accumulation_times = ast.literal_eval(APP_CONFIG["accumulation_times"])
latS = APP_CONFIG["latS"]
latN = APP_CONFIG["latN"]
lonW = APP_CONFIG["lonW"]
lonE = APP_CONFIG["lonE"]
outdata_path_parent = APP_CONFIG["outdataPath"]

def main(grib_use_list, output_start_time, output_end_time):

    logger.info('')
    logger.info('Running acc_precip creation...')

    reset_folders.refresh(outdata_path_parent, archive=False)  # Clean the outdata folders for this run    

    cities_dict = {}
    with open(locations_file) as f:
        in_lines = f.readlines()
        for line in in_lines:
            line_split = line.split(';')
            city = line_split[0].strip('\n')
            lat  = float(line_split[1].strip('\n'))
            lon  = float(line_split[2].strip('\n'))
            cities_dict.update({city : {'lat' : lat, 'lon' : lon}})

    
    acc_dict = {}
    
    for accumulation_time in accumulation_times:
        if not os.path.exists(outdata_path_parent + str(accumulation_time)):  # Create the outdirs if it does not already exist
            logger.info('Creating outdata directory  {}'.format(outdata_path_parent + str(accumulation_time) + '/'))
            os.makedirs(outdata_path_parent + str(accumulation_time))
        if accumulation_time not in acc_dict:
            acc_dict.update({accumulation_time : {'outdata_path' : outdata_path_parent + str(accumulation_time) + '/',
                                                  'acc_array' : [],
                                                  'acc_steps' : 1,
                                                  'acc_time_stamps' : time_tools.get_time_stamps_for_acc(accumulation_time, start_of_precipitation_day),
                                                  'start_of_precipitation_day' : start_of_precipitation_day}})


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

    # Loop over GRIB2-files, parameters, and cities/regions (most efficient to open GRIB2 file only once)
    # acc_steps = 1
    grib_valid_times = sorted([time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz) for grib_use in grib_use_list])

    # Sort GRIB files by valid time
    data = None
    data_past = None
    for grib_valid_time in grib_valid_times:
        for grib_file in grib_use_list:
            validTime_UTC = time_tools.getForecastValidTime_UTC(grib_file, greenwich_tz)
            if validTime_UTC == grib_valid_time:
                grib_use = grib_file
                break

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

            
            #Create an accumulation array with the correct shape
            if 'acc_array' not in locals(): #If it does not already exist
                acc_array = np.zeros(np.shape(lats))

            if ACCUMULATED_PRECIPITATION == False:
                total_precipitation = (data[parameter_names[0]] + data[parameter_names[1]])
            else:
                if data_past is not None:
                    total_precipitation = data[parameter_names[0]] - data_past[parameter_names[0]]
                else:
                    total_precipitation = data[parameter_names[0]]

            if data_past is not None:
                step_range = int( data['stepRange'].split('-')[-1] )  # To get a 3 from a stepRange of '0-3', for instance
                step_range = step_range - int( data_past['stepRange'].split('-')[-1] )  # Subtract the latest stepRange
            else:
                step_range = int( data['stepRange'].split('-')[-1] )  # To get a 3 from a stepRange of '0-3', for instance

            total_precipitation[total_precipitation<0] = 0
            total_precipitation = total_precipitation * PRECIP_MULT_FACTOR

            for accumulation_time in acc_dict:
                if len(acc_dict[accumulation_time]['acc_array']) == 0:
                    acc_dict[accumulation_time]['acc_array'] = np.zeros(np.shape(lats))
                acc_dict[accumulation_time]['acc_array'] = acc_dict[accumulation_time]['acc_array'] + total_precipitation

                fValid_hour = time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz).hour
                
                if fValid_hour in acc_dict[accumulation_time]['acc_time_stamps']:
                    #Create a plot of accumulated precipitation and reset the acc array
                    logger.info('    Creating plot for accumulation time {}'.format(accumulation_time))
                    create_plot(lats, lons, acc_dict[accumulation_time]['acc_array'], validTime_UTC, acc_dict[accumulation_time]['outdata_path'], acc_dict[accumulation_time]['acc_steps'] * step_range, cities_dict, latS, latN, lonW, lonE)
                    acc_dict[accumulation_time]['acc_array'] = []
                    acc_dict[accumulation_time]['acc_steps'] = 1
                else:
                    acc_dict[accumulation_time]['acc_steps'] = acc_dict[accumulation_time]['acc_steps'] + 1

        data_past = data



def create_plot(lats, lons, acc_array, validTime_UTC, outdataPath, acc_steps, cities_dict, latS, latN, lonW, lonE):

    projLat = np.mean([latS, latN])
    projLon = np.mean([lonW, lonE])
    min_latitude = latS-1
    max_latitude = latN+1

    max_precip = 10
    levs = [1, 2.5, 5, 7.5, 10, 15, 20, 30, 40, 50, 70, 100, 150, 200, 250, 300, 400, 500, 600, 750]
    clevs = clevs = [0, 1, 2.5, 5, 7.5, 10, 15, 20, 30, 40, 50, 70, 100, 150, 200, 250, 300, 400, 500, 600, 750]#np.linspace(0.1, max_precip, 21) #[0, 0.2, 0.4, 0.6, 0.8, 1., 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3., 3.2, 3.4, 3.6, 3.8, 4., 4.2, 4.4, 4.6, 4.8, 5., 5.2, 5.4, 5.6, 5.8, 6.]
    
    fig = plt.gcf()
    ax = fig.add_subplot(1,1,1, projection = ccrs.Mercator(central_longitude=projLon, min_latitude = min_latitude, max_latitude = max_latitude))
    #ax.coastlines(resolution='10m', linewidth=0.3)
    
    ax.add_feature(cfeature.RIVERS.with_scale('10m'), linewidth=0.4)
    ax.add_feature(cfeature.LAKES.with_scale('10m'), linewidth=0.4)
    ax.add_feature(cfeature.BORDERS.with_scale('10m'), linewidth=0.6)
       
    ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
    ax.set_extent([lonW, lonE, latS, latN], crs = ccrs.PlateCarree())
    cmap_data = [(1.0, 1.0, 1.0),
                (0.3137255012989044, 0.8156862854957581, 0.8156862854957581),
                (0.0, 1.0, 1.0),
                (0.0, 0.8784313797950745, 0.501960813999176),
                (0.0, 0.7529411911964417, 0.0),
                (0.501960813999176, 0.8784313797950745, 0.0),
                (1.0, 1.0, 0.0),
                (1.0, 0.6274510025978088, 0.0),
                (1.0, 0.0, 0.0),
                (1.0, 0.125490203499794, 0.501960813999176),
                (0.9411764740943909, 0.250980406999588, 1.0),
                (0.501960813999176, 0.125490203499794, 1.0),
                (0.250980406999588, 0.250980406999588, 1.0),
                (0.125490203499794, 0.125490203499794, 0.501960813999176),
                (0.125490203499794, 0.125490203499794, 0.125490203499794),
                (0.501960813999176, 0.501960813999176, 0.501960813999176),
                (0.8784313797950745, 0.8784313797950745, 0.8784313797950745),
                (0.9333333373069763, 0.8313725590705872, 0.7372549176216125),
                (0.8549019694328308, 0.6509804129600525, 0.47058823704719543),
                (0.6274510025978088, 0.42352941632270813, 0.23529411852359772),
                (0.4000000059604645, 0.20000000298023224, 0.0)]
    
    cmap = mcolors.ListedColormap(cmap_data, 'precipitation')
    norm = mcolors.BoundaryNorm(clevs, cmap.N)
    cs = ax.contourf(lons, lats, acc_array, clevs, transform=ccrs.PlateCarree(), cmap=cmap, norm=norm)
    fig.colorbar(cs, ticks = clevs)
    cl = ax.contour(lons, lats, acc_array, levs, colors='k', transform=ccrs.PlateCarree(), linewidths = 0.1)
    plt.clabel(cl, inline=1, fmt='%1.f', fontsize=8)
    
    lat_cities = []
    lon_cities = []
    labels = []
    for key in cities_dict:
        labels.append(key)
        lat_cities.append(cities_dict[key]['lat'])
        lon_cities.append(cities_dict[key]['lon'])
    
    ax.plot(lon_cities, lat_cities, 'ko',markersize=4, transform=ccrs.PlateCarree())
    for label, xpt, ypt in zip(labels, lon_cities, lat_cities):
            plt.text(xpt, ypt, label, transform=ccrs.PlateCarree())
   
    titleString = "Precipitation accumulated over {} hours, mm \n Valid: {}".format(str(acc_steps), validTime_UTC.strftime('%Y-%m-%d %H UTC') )# + validUTC_dt.strftime('%Y-%m-%d %H:00') + " UTC"
    plt.title(titleString)
    figure = plt.gcf()
    figure.set_size_inches(16, 9)
    save = outdataPath + validTime_UTC.strftime('%Y-%m-%dT%H%M') + '_acc{}H.png'.format(acc_steps)
    plt.savefig(save,dpi=200)
    plt.clf()


if __name__ == '__main__':
    main()
