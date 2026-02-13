# -*- coding: utf-8 -*-
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
logger = logging.getLogger(f"carl-wrf-tools.{APP_NAME}")

# Load configuration parameters
APP_CONFIG = CONFIG["plotters"][APP_NAME]
wanted_parameters = ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["wantedParameters"])
parameter_names = ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["parameterNames"])
locations_file = APP_CONFIG["locationsFile"]
output_time_zone = APP_CONFIG["timeZone"]
start_of_precipitation_day = APP_CONFIG["start_of_precipitation_day"]

# Only consider 10-hour accumulation
accumulation_times = [10]  # <- Ensures only 10-hour total accumulated rainfall is used

latS = APP_CONFIG["latS"]
latN = APP_CONFIG["latN"]
lonW = APP_CONFIG["lonW"]
lonE = APP_CONFIG["lonE"]
outdata_path_parent = APP_CONFIG["outdataPath"]


def main(grib_use_list, output_start_time, output_end_time):
    logger.info('Running 10-hour accumulated precipitation plot creation...')

    reset_folders.refresh(outdata_path_parent, archive=False)

    # Load city locations
    cities_dict = {}
    with open(locations_file) as f:
        for line in f.readlines():
            line_split = line.split(';')
            city = line_split[0].strip()
            lat = float(line_split[1].strip())
            lon = float(line_split[2].strip())
            cities_dict[city] = {'lat': lat, 'lon': lon}

    acc_dict = {}
    for accumulation_time in accumulation_times:
        acc_dict[accumulation_time] = {
            'outdata_path': os.path.join(outdata_path_parent, str(accumulation_time)),
            'acc_array': [],
            'acc_steps': 1,
            'acc_time_stamps': time_tools.get_time_stamps_for_acc(accumulation_time, start_of_precipitation_day),
            'start_of_precipitation_day': start_of_precipitation_day
        }

        os.makedirs(acc_dict[accumulation_time]['outdata_path'], exist_ok=True)

    # Handle time
    greenwich_tz = pytz.timezone('Greenwich')
    desired_tz = pytz.timezone(output_time_zone) if output_time_zone != 'Greenwich' else greenwich_tz
    fc_startHour_UTC = output_start_time.astimezone(greenwich_tz)
    fc_endHour_UTC = output_end_time.astimezone(greenwich_tz)

    # Process GRIB files
    grib_valid_times = sorted(time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz) for grib_use in grib_use_list)

    data_past = None
    for grib_valid_time in grib_valid_times:
        for grib_file in grib_use_list:
            validTime_UTC = time_tools.getForecastValidTime_UTC(grib_file, greenwich_tz)
            if validTime_UTC == grib_valid_time:
                grib_use = grib_file
                break

        lats, lons, data = grib_read.main(grib_use, parameter_names, wanted_parameters, grib_use_list)

        # Initialize accumulation array
        if 'acc_array' not in locals():
            acc_array = np.zeros(np.shape(lats))

        # Calculate total precipitation
        total_precipitation = data[parameter_names[0]] - data_past[parameter_names[0]] if data_past else data[
            parameter_names[0]]
        total_precipitation = np.maximum(total_precipitation, 0) * PRECIP_MULT_FACTOR  # Ensure non-negative

        for accumulation_time in acc_dict:
            acc_dict[accumulation_time]['acc_array'] = acc_dict[accumulation_time]['acc_array'] + total_precipitation
            fValid_hour = time_tools.getForecastValidTime_UTC(grib_use, greenwich_tz).hour

            if fValid_hour in acc_dict[accumulation_time]['acc_time_stamps']:
                create_plot(lats, lons, acc_dict[accumulation_time]['acc_array'], validTime_UTC,
                            acc_dict[accumulation_time]['outdata_path'], accumulation_time, cities_dict, latS, latN,
                            lonW, lonE)
                acc_dict[accumulation_time]['acc_array'] = np.zeros_like(
                    acc_dict[accumulation_time]['acc_array'])  # Reset accumulation array

        data_past = data


def create_plot(lats, lons, acc_array, validTime_UTC, outdataPath, acc_steps, cities_dict, latS, latN, lonW, lonE):
    """Plots 10-hour total accumulated precipitation."""

    projLat, projLon = np.mean([latS, latN]), np.mean([lonW, lonE])

    # Define color scale
    clevs = [0, 1, 2, 5, 10, 15, 20, 30, 50, 75, 100, 150, 200]
    cmap = plt.get_cmap("Blues")  # Use "Blues" colormap for better rainfall visibility
    norm = mcolors.BoundaryNorm(clevs, cmap.N)

    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent([lonW, lonE, latS, latN])

    ax.add_feature(cfeature.BORDERS, linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.LAKES, alpha=0.5)

    cs = ax.contourf(lons, lats, acc_array, levels=clevs, cmap=cmap, norm=norm, transform=ccrs.PlateCarree())
    plt.colorbar(cs, ax=ax, orientation="vertical", label="Accumulated Rainfall (mm)")

    # Plot city locations
    for city, coords in cities_dict.items():
        ax.plot(coords['lon'], coords['lat'], 'ro', transform=ccrs.PlateCarree())
        ax.text(coords['lon'], coords['lat'], city, fontsize=8, transform=ccrs.PlateCarree())

    plt.title(f"10-Hour Accumulated Rainfall (mm) \nValid: {validTime_UTC.strftime('%Y-%m-%d %H UTC')}")

    # Save the figure
    save_path = os.path.join(outdataPath, f"{validTime_UTC.strftime('%Y-%m-%dT%H%M')}_10hr_acc.png")
    plt.savefig(save_path, dpi=200)
    plt.close()


if __name__ == '__main__':
    main()
