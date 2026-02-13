#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Interval Accumulated Rainfall Plotter
Generates accumulated rainfall maps for 1-hour, 12-hour, 24-hour, and 10-day totals.
With 0 mm shown as white background.
"""

import os, ast, pytz, logging
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timedelta

from grib_reader import grib_read
from tools import time_tools, reset_folders
from config import CONFIG, DATA_SOURCE, PRECIP_MULT_FACTOR

APP_NAME = 'acc_precip_multi'
logger = logging.getLogger(f"carl-wrf-tools.{APP_NAME}")

APP_CONFIG = CONFIG["plotters"]["acc_precip"]
wanted_parameters = ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["wantedParameters"])
parameter_names = ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["parameterNames"])
locations_file = APP_CONFIG["locationsFile"]
output_time_zone = APP_CONFIG["timeZone"]
latS, latN = APP_CONFIG["latS"], APP_CONFIG["latN"]
lonW, lonE = APP_CONFIG["lonW"], APP_CONFIG["lonE"]
outdata_parent = APP_CONFIG["outdataPath"]

# Fixed accumulation intervals (hours)
acc_intervals = [1, 12, 24, 240]  # 1h, 12h, 24h, 10 days


def load_cities():
    cities = {}
    with open(locations_file) as f:
        for line in f:
            if not line.strip():
                continue
            name, lat, lon = line.strip().split(';')
            cities[name] = {'lat': float(lat), 'lon': float(lon)}
    return cities


def accumulate_and_plot(grib_files, output_start_time, output_end_time):
    reset_folders.refresh(outdata_parent, archive=False)
    cities = load_cities()
    greenwich = pytz.timezone('Greenwich')
    output_tz = pytz.timezone(output_time_zone) if output_time_zone != 'Greenwich' else greenwich

    # Sort GRIB files chronologically
    grib_files = sorted(grib_files, key=lambda f: time_tools.getForecastValidTime_UTC(f, greenwich))

    lats, lons = None, None
    data_prev = None
    interval_data = {h: None for h in acc_intervals}
    interval_start = {h: None for h in acc_intervals}

    for grib_file in grib_files:
        try:
            lats, lons, data = grib_read.main(grib_file, parameter_names, wanted_parameters, grib_files)
            valid_time = time_tools.getForecastValidTime_UTC(grib_file, greenwich)
        except Exception as e:
            logger.warning(f"Skipping {grib_file}: {e}")
            continue

        precip = np.maximum(data[parameter_names[0]], 0)
        if data_prev is not None:
            inc = np.maximum((precip - data_prev[parameter_names[0]]) * PRECIP_MULT_FACTOR, 0)
        else:
            inc = precip * PRECIP_MULT_FACTOR
        data_prev = data

        for hours in acc_intervals:
            if interval_data[hours] is None:
                interval_data[hours] = np.zeros_like(inc)
                interval_start[hours] = valid_time
            interval_data[hours] += inc

            if (valid_time - interval_start[hours]) >= timedelta(hours=hours):
                plot_accum(lats, lons, interval_data[hours], interval_start[hours],
                           valid_time, outdata_parent, hours, cities, latS, latN, lonW, lonE)
                interval_data[hours] = np.zeros_like(interval_data[hours])
                interval_start[hours] = valid_time

    logger.info("✅ Completed accumulation plots for all intervals.")


def plot_accum(lats, lons, rain, start_t, end_t, outdir, hours, cities, latS, latN, lonW, lonE):
    """Plot accumulated rainfall for given interval with 0 mm as white background."""

    # Custom colormap with white for 0 mm
    clevs = [0, 1, 5, 10, 25, 50, 75, 100, 150, 200, 300, 400, 600]
    base_cmap = plt.get_cmap("turbo")
    colors = base_cmap(np.linspace(0, 1, len(clevs)))
    colors[0] = [1, 1, 1, 1]  # 0 mm = white
    cmap = mcolors.ListedColormap(colors)
    norm = mcolors.BoundaryNorm(clevs, cmap.N)

    # Figure setup
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw={'projection': ccrs.PlateCarree()})
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.set_extent([lonW, lonE, latS, latN])

    ax.add_feature(cfeature.BORDERS, linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.LAKES, edgecolor='black', facecolor='none', linewidth=0.5)
    ax.add_feature(cfeature.RIVERS, linewidth=0.4, alpha=0.5)

    cs = ax.contourf(lons, lats, rain, levels=clevs, cmap=cmap, norm=norm, transform=ccrs.PlateCarree())
    cbar = plt.colorbar(cs, ax=ax, orientation="vertical", pad=0.02)
    cbar.set_label("Accumulated Rainfall (mm)")

    for city, coords in cities.items():
        ax.plot(coords['lon'], coords['lat'], 'r^', transform=ccrs.PlateCarree(), markersize=5)
        ax.text(coords['lon'] + 0.2, coords['lat'] + 0.2, city, fontsize=8, transform=ccrs.PlateCarree())

    # Folder name based on interval
    if hours == 1:
        folder = "1"
        label = "1-hour"
    elif hours == 12:
        folder = "12"
        label = "12-hour"
    elif hours == 24:
        folder = "24"
        label = "24-hour"
    elif hours == 240:
        folder = "10_day"
        label = "10-day"
    else:
        folder = str(hours)
        label = f"{hours}-hour"

    plt.title(
        f"{label.capitalize()} Accumulated Rainfall (mm)\n"
        f"{start_t.strftime('%d %b %Y %H UTC')} – {end_t.strftime('%d %b %Y %H UTC')}",
        fontsize=11, pad=15
    )

    subdir = os.path.join(outdir, folder)
    os.makedirs(subdir, exist_ok=True)
    outfile = os.path.join(subdir, f"{end_t.strftime('%Y%m%d_%H')}UTC_acc_{label.replace('-', '_')}.png")

    plt.savefig(outfile, dpi=250, bbox_inches="tight", facecolor='white')
    plt.close()
    logger.info(f"🖼️  Saved {label} rainfall plot: {outfile}")


def main(grib_files, output_start_time, output_end_time):
    """Wrapper entrypoint for compatibility with plot_runner.py"""
    accumulate_and_plot(grib_files, output_start_time, output_end_time)


if __name__ == '__main__':
    now = datetime.utcnow()
    start = now - timedelta(days=10)
    grib_dir = "/home/wrf/deployed/nons_wrf_v4/gfs-data"
    grib_files = [os.path.join(grib_dir, f) for f in os.listdir(grib_dir) if f.endswith(".grb2")]
    main(grib_files, start, now)
