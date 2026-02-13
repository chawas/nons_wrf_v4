#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Interval Accumulated Rainfall Plotter
Generates accumulated rainfall maps for 1-hour, 12-hour, 24-hour, and 10-day totals.
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

# read accumulation intervals (in hours) from config
acc_intervals = APP_CONFIG.get("accumulation_intervals_hours", [1, 12, 24, 240])

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

    # sort GRIB files chronologically
    grib_files = sorted(grib_files, key=lambda f: time_tools.getForecastValidTime_UTC(f, greenwich))

    lats, lons = None, None
    data_prev = None
    accum = np.zeros((len(acc_intervals),))  # dummy init for loop logic
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
    """Plot accumulated rainfall for given interval."""
    cmap = plt.get_cmap("turbo")
    clevs = [0, 1, 5, 10, 25, 50, 75, 100, 150, 200, 300, 400, 600]
    norm = mcolors.BoundaryNorm(clevs, cmap.N)

    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.set_extent([lonW, lonE, latS, latN])
    ax.add_feature(cfeature.BORDERS, linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.LAKES, alpha=0.5)
    ax.add_feature(cfeature.RIVERS, alpha=0.3)

    cs = ax.contourf(lons, lats, rain, levels=clevs, cmap=cmap, norm=norm, transform=ccrs.PlateCarree())
    cbar = plt.colorbar(cs, ax=ax, orientation="vertical", pad=0.02)
    cbar.set_label("Accumulated Rainfall (mm)")

    for city, coords in cities.items():
        ax.plot(coords['lon'], coords['lat'], 'r^', transform=ccrs.PlateCarree())
        ax.text(coords['lon'] + 0.1, coords['lat'] + 0.1, city, fontsize=8, transform=ccrs.PlateCarree())

    label = f"{hours//24}-day" if hours >= 24 else f"{hours}-hour"
    plt.title(f"{label} Accumulated Rainfall (mm)\n{start_t.strftime('%d %b %Y %H UTC')} – {end_t.strftime('%d %b %Y %H UTC')}",
              fontsize=11, pad=15)

    subdir = os.path.join(outdir, f"{label.replace('-','_')}")
    os.makedirs(subdir, exist_ok=True)
    outfile = os.path.join(subdir, f"{end_t.strftime('%Y%m%d_%H')}UTC_acc_{label}.png")
    plt.savefig(outfile, dpi=250, bbox_inches="tight")
    plt.close()
    logger.info(f"🖼️  Saved {label} plot: {outfile}")


def main(grib_files, output_start_time, output_end_time):
    """
    Wrapper entrypoint for compatibility with plot_runner.py
    """
    accumulate_and_plot(grib_files, output_start_time, output_end_time)

if __name__ == '__main__':
    now = datetime.utcnow()
    start = now - timedelta(days=10)
    grib_dir = "/home/wrf/deployed/nons_wrf_v4/gfs-data"
    grib_files = [os.path.join(grib_dir, f) for f in os.listdir(grib_dir) if f.endswith(".grb2")]
    main(grib_files, start, now)
