# -*- coding: utf-8 -*-

import ast
import pytz
import logging

import numpy as np

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D

from grib_reader import grib_read

from tools import time_tools, reset_folders
from config import CONFIG, DATA_SOURCE

APP_NAME = 'cloudcover'
logger = logging.getLogger("carl-wrf-tools.{}".format(APP_NAME))

APP_CONFIG = CONFIG["plotters"][APP_NAME]
wanted_parameters = ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["wantedParameters"])
parameter_names =  ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["parameterNames"])
locations_file = APP_CONFIG["locationsFile"]
output_time_zone = APP_CONFIG["timeZone"]
latS = APP_CONFIG["latS"]
latN = APP_CONFIG["latN"]
lonW = APP_CONFIG["lonW"]
lonE = APP_CONFIG["lonE"]
outdata_path = APP_CONFIG["outdataPath"]

def main(grib_use_list, output_start_time, output_end_time):

    logger.info('Running cloudcover plotting...')

    reset_folders.refresh(outdata_path, archive=False)  # Clean the outdata folders for this run
    
    cities_dict = {}
    with open(locations_file) as f:
        in_lines = f.readlines()
        for line in in_lines:
            line_split = line.split(';')
            city = line_split[0].strip('\n')
            lat  = float(line_split[1].strip('\n'))
            lon  = float(line_split[2].strip('\n'))
            cities_dict.update({city : {'lat' : lat, 'lon' : lon}})   

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
    acc_steps = 1
    for grib_use in grib_use_list:
        try:
            base_time_UTC   = greenwich_tz.localize(time_tools.get_forecast_basetime_UTC(grib_use))
            validTime_UTC   = time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz)
            validTime_local = time_tools.UTCtoLocal( validTime_UTC, desired_tz )
            
            logger.info('Working with time step {}'.format(validTime_UTC.strftime('%Y%m%d %H:%M')))
            if desired_tz != greenwich_tz:
                logger.info('    Which in specified time zone is {}'.format(validTime_local.strftime('%Y%m%d %H:%M')))
            logger.info('    File: ' + grib_use)

            lats, lons, data = grib_read.main(grib_use, parameter_names, wanted_parameters, grib_use_list)
        
            fValid_hour = time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz).hour
            
            create_plot(lats, lons, data, validTime_UTC, outdata_path, parameter_names, cities_dict, latS, latN, lonW, lonE)
        except:
            logger.warning(f'ERROR: The parameters {wanted_parameters} does not seem to exist in {grib_use}')


def create_plot(lats, lons, data, validTime_UTC, outdata_path, parameter_names, cities_dict, latS, latN, lonW, lonE):
    projLat = np.mean([latS, latN])
    projLon = np.mean([lonW, lonE])
    min_latitude = latS-1
    max_latitude = latN+1

    
    fig, ax = plt.subplots(1,1, subplot_kw={'projection' : ccrs.PlateCarree()})
    
    #ax.coastlines(resolution='10m', linewidth=0.3)
    ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor = '#008053')
    ax.add_feature(cfeature.RIVERS.with_scale('10m'), linewidth=0.4)
    ax.add_feature(cfeature.LAKES.with_scale('10m'), linewidth=0.4)
    ax.add_feature(cfeature.BORDERS.with_scale('10m'), linewidth=0.8)
    ax.add_feature(cfeature.STATES.with_scale('10m'), linewidth=0.6)

    ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
    ax.set_extent([lonW, lonE, latS, latN], crs=ccrs.PlateCarree())
    
    # Create color maps for different cloud layers
    no_alpha_levels = 10
    alpha_levels_l = np.linspace(0,1.0,no_alpha_levels)
    alpha_levels_h = np.linspace(0,0.7,no_alpha_levels)
    # alpha_levels = np.logspace(0,1,no_alpha_levels) / 10.0
    # alpha_levels = list(reversed(alpha_levels))
    r = 1.0
    g = 1.0
    b = 0.0
    cmap_data_l = [(r,g,b,alpha) for alpha in alpha_levels_l]
    r = 1.0 #0.6274510025978088
    g = 1.0 #0.42352941632270813
    b = 1.0 #0.23529411852359772
    cmap_data_m = [(r,g,b,alpha) for alpha in alpha_levels_l]
    r = 0.5
    g = 0.7
    b = 1.0
    cmap_data_h = [(r,g,b,alpha) for alpha in alpha_levels_h]
    
    # sys.exit()

    cmap_l = mcolors.ListedColormap(cmap_data_l, 'low_cloudcover')
    cmap_m = mcolors.ListedColormap(cmap_data_m, 'medium_cloudcover')
    cmap_h = mcolors.ListedColormap(cmap_data_h, 'high_cloudcover')

    # cmap_l = mcolors.LinearSegmentedColormap.from_list('lowCloudcover', cmap_data_l)#.reversed()
    # cmap_m = mcolors.LinearSegmentedColormap.from_list('mediumCloudcover', cmap_data_m)#.reversed()
    # cmap_h = mcolors.LinearSegmentedColormap.from_list('highCloudcover', cmap_data_h)#.reversed()

    # cm.register_cmap(cmap=cmap_l.reversed())
    # cm.register_cmap(cmap=cmap_m.reversed())
    # cm.register_cmap(cmap=cmap_h.reversed())

    norm_l = mcolors.BoundaryNorm(alpha_levels_l, cmap_l.N)
    norm_m = mcolors.BoundaryNorm(alpha_levels_l, cmap_m.N)
    norm_h = mcolors.BoundaryNorm(alpha_levels_h, cmap_h.N)
   
    # for param in parameter_names:
    mult_factor = 5
    x, y = np.shape(lats)
    plot_lats = regrid(lats, x*mult_factor, y*mult_factor)
    plot_lons = regrid(lons, x*mult_factor, y*mult_factor)
    
    for param in parameter_names:
        data[param] = data[param] / 100.0
        data[param][data[param] > 1.0] = 0.0
        masked_data = np.ma.masked_where(data[param] < 0.2, data[param])
        plot_data = regrid(masked_data, x*mult_factor, y*mult_factor)
        # plot_data = gaussian_filter(plot_data, 0.5)

        # data[param][data[param] < 0.4] = np.nan
        # masked_data = np.ma.masked_where(data[param] < 0.0, data[param])
        # masked_data = gaussian_filter(data[param], 0.5)
        # print(np.min(masked_data), np.max(masked_data))
        # level = int(param.split('_')[-1])
        # masked_data = np.ma.masked_where(plot_data < 0.4, data[param])
        if param == 'hcc': # level <= 300:
            cmap = cmap_h
            # cmap = 'highCloudcover_r'
            norm = norm_h
            label = 'High clouds'
            # masked_data = np.ma.masked_where(plot_data < 0.8, plot_data)
            # plot_data = gaussian_filter(plot_data, 0.5)
        if param == 'mcc':  # level > 300 and level <= 750:
            cmap = cmap_m
            # cmap = 'mediumCloudcover_r'
            norm = norm_m
            label = 'Medium clouds'
            # masked_data = np.ma.masked_where(plot_data < 0.0, plot_data)
            # plot_data = gaussian_filter(plot_data, 0.5) 
        if param == 'lcc':  # level > 750:
            cmap = cmap_l
            # cmap = 'lowCloudcover_r'
            norm = norm_l
            label = 'Low clouds'
            # masked_data = np.ma.masked_where(plot_data < 0.2, plot_data)
            # plot_data = gaussian_filter(plot_data, 0.5)
        # cf = ax.contourf(lons, lats, masked_data, no_alpha_levels, transform=ccrs.PlateCarree(), cmap=cmap)#, norm=norm)
        # cf = ax.contourf(plot_lons, plot_lats, plot_data, no_alpha_levels, transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, antialiased=False)
        # for c in cf.collections:
        #     c.set_edgecolor(None)

        cf = ax.pcolormesh(plot_lons, plot_lats, plot_data, transform=ccrs.PlateCarree(), cmap=cmap, norm=norm, label=label, edgecolor=None, antialiased=False)
    
    custom_lines = [Line2D([0], [0], color=cmap_h(1.), lw=4),
                    Line2D([0], [0], color=cmap_m(1.), lw=4),
                    Line2D([0], [0], color=cmap_l(1.), lw=4)]

    legend_elements = [Line2D([0], [0], color='b', lw=4, label='Line'),
                   Line2D([0], [0], marker='o', color='w', label='Scatter',
                          markerfacecolor='g', markersize=15),]
    plt.legend(custom_lines, ['High clouds', 'Medium clouds', 'Low clouds'], loc='upper right')
    
    lat_cities = []
    lon_cities = []
    labels = []
    for key in cities_dict:
        labels.append(key)
        lat_cities.append(cities_dict[key]['lat'])
        lon_cities.append(cities_dict[key]['lon'])
    
    ax.plot(lon_cities, lat_cities, 'ko', markersize=4, transform=ccrs.PlateCarree())
    for label, xpt, ypt in zip(labels, lon_cities, lat_cities):
            plt.text(xpt, ypt, label, transform=ccrs.PlateCarree())
   
    titleString = "Cloudcover \n Valid: {}".format(validTime_UTC.strftime('%Y-%m-%d %H UTC') )# + validUTC_dt.strftime('%Y-%m-%d %H:00') + " UTC"
    plt.title(titleString)
    figure = plt.gcf()
    figure.set_size_inches(16, 9)
    save = outdata_path + validTime_UTC.strftime('%Y-%m-%dT%H%M') + '.png'
    plt.savefig(save,dpi=200)
    # plt.clf()
    plt.close('all')

    #plt.show()
   



def regrid(data, out_x, out_y):
    from scipy.interpolate import RegularGridInterpolator
    m = max(data.shape[0], data.shape[1])
    
    x = np.linspace(0, 1.0, data.shape[1])
    y = np.linspace(0, 1.0, data.shape[0])
    interpolating_function = RegularGridInterpolator((y, x), data)

    yv, xv = np.meshgrid(np.linspace(0, 1.0, out_y), np.linspace(0, 1.0, out_x))

    return interpolating_function((xv, yv))


if __name__ == '__main__':
    print('Cloudcover module')
