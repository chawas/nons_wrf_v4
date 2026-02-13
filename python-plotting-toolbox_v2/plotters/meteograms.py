
# -*- coding: utf-8 -*-
"""
Meteograms from GFS/WRF GRIB2 data.

Assumes data is available with regular intervals for the forecast period.
"""
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.offsetbox import (TextArea, OffsetImage, AnnotationBbox)
import matplotlib.image as mpimg
import os

from tools import config_tools, reset_folders
from config import CONFIG

APP_NAME = 'meteograms'
logger = logging.getLogger("carl-wrf-tools.{}".format(APP_NAME))

APP_CONFIG = CONFIG["plotters"][APP_NAME]
locations_file = APP_CONFIG["locationsFile"]
output_time_zone = APP_CONFIG["timeZone"]
symbols = APP_CONFIG["symbols"]
outdata_path = APP_CONFIG["outdataPath"]


def main(df, grib_use_list, output_start_time, output_end_time, desired_tz, greenwich_tz):
    """
    Entry point used by plot_runner.py
    df: multi-index DataFrame with top-level columns = locations
    """
    misc_path = './misc/'
    reset_folders.refresh(outdata_path, archive=False)  # Clean the outdata folders for this run

    match_timestamps = ['00:00', '06:00', '12:00', '18:00']
    createMeteogram_df(df, match_timestamps, misc_path, outdata_path, desired_tz, greenwich_tz, symbols)


def createMeteogram_df(df, match_timestamps, misc_path, outdata_path, desired_tz, greenwich_tz, symbols):
    logger.info('    Creating meteograms...')

    meteogram_cities = config_tools.readCitiesConfig(locations_file)

    y_fontsize = 30
    x_fontsize = 12

    days_loc = mdates.DayLocator(tz=desired_tz)
    hours_loc = mdates.HourLocator(tz=desired_tz)
    two_hours_loc = mdates.HourLocator(byhour=range(0, 24, 12), tz=desired_tz)
    six_hours_loc = mdates.HourLocator(byhour=range(0, 24, 6), tz=desired_tz)

    days_fmt = mdates.DateFormatter('%a \n %b %d', tz=desired_tz)
    hour_fmt = mdates.DateFormatter('%H', tz=desired_tz)

    # iterate over top-level columns (cities)
    for city in df.columns.levels[0]:
        if city not in meteogram_cities:
            continue

        logger.info('        Working with location: %s', city)

        fig, axs = plt.subplots(4, 2,
                                gridspec_kw={'height_ratios': [20, 9, 7, 3], 'width_ratios': [1, 12]},
                                sharex='col')

        fig.suptitle('Meteogram for ' + city, fontweight='bold', fontsize=30, horizontalalignment='right')

        # TEMPERATURE
        axs[0, 1].plot(df.index, df[city]['t'], color='red', linewidth=3)

        data_y_max = df[city]['t'].max()
        data_y_min = df[city]['t'].min()
        if data_y_min > 0.0 and data_y_max < 40.0:
            axs[0, 1].set_ylim([0, 40])
        elif data_y_min < 0.0:
            axs[0, 1].set_ylim([data_y_min - 6.0, 40.0])
        else:
            axs[0, 1].set_ylim([data_y_min - 6.0, data_y_max + 6.0])

        y_lim_min = axs[0, 1].get_ylim()

        axs[0, 1].grid(True)
        axs[0, 1].set_ylabel('$^\circ$C', fontsize=y_fontsize, horizontalalignment='right')
        axs[0, 1].yaxis.set_label_position('right')
        axs[0, 1].tick_params(axis='y', which='major', labelsize=20)

        # ANNOTATIONS - daily max/min
        df_temp = pd.DataFrame(df[city]['t'], index=df.index)
        # ensure index is datetime
        df_temp.index = pd.to_datetime(df_temp.index)

        maxs = df_temp.groupby(pd.Grouper(freq='D'))['t'].transform('max')
        mins = df_temp.groupby(pd.Grouper(freq='D'))['t'].transform('min')
        df_temp_max = df_temp[df_temp['t'] == maxs]
        df_temp_min = df_temp[df_temp['t'] == mins]

        idx_last = None
        for idx, row in df_temp_max.iterrows():
            max_val = row['t']
            offsetbox = TextArea(str(int(np.round(max_val, 0))), textprops=dict(fontsize=25, color='white'))

            if idx_last is None or idx.day != idx_last.day:
                try:
                    ab = AnnotationBbox(offsetbox, (idx, int(np.round(max_val, 0))),
                                        xybox=(20, 40),
                                        xycoords='data',
                                        boxcoords="offset points",
                                        bboxprops=dict(boxstyle='round', color='r', edgecolor='r'))
                    axs[0, 1].add_artist(ab)
                except Exception:
                    logger.debug("Could not place max annotation at %s", idx)
            idx_last = idx

        # Add weather symbol to plot (if enabled)
        if symbols:
            try:
                df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(match_timestamps), (city)])
            except Exception:
                df_symb = pd.DataFrame()
            idx_last = None
            for idx, row in df_symb.iterrows():
                image_file_symbol = row.get('weatherSymbol6h', None)
                if image_file_symbol and os.path.exists(image_file_symbol):
                    try:
                        img_symbol = mpimg.imread(image_file_symbol)
                        imagebox = OffsetImage(img_symbol, zoom=0.20)
                        imagebox.image.axes = axs[0, 1]
                        ib = AnnotationBbox(imagebox, (idx, y_lim_min[0] + 3),
                                            xybox=(0., 0.),
                                            xycoords='data',
                                            boxcoords="offset points",
                                            bboxprops=dict(boxstyle='round', color='white'))
                        axs[0, 1].add_artist(ib)
                    except Exception:
                        logger.debug("Failed to add symbol %s for %s", image_file_symbol, city)
                idx_last = idx

        idx_last = None
        for idx, row in df_temp_min.iterrows():
            min_val = row['t']
            offsetbox = TextArea(str(int(np.round(min_val, 0))), textprops=dict(fontsize=25, color='white'))

            if idx_last is None or idx.day != idx_last.day:
                try:
                    ab = AnnotationBbox(offsetbox, (idx, int(np.round(min_val, 0))),
                                        xybox=(0, -40),
                                        xycoords='data',
                                        boxcoords="offset points",
                                        bboxprops=dict(boxstyle='round', color='b'))
                    axs[0, 1].add_artist(ab)
                except Exception:
                    logger.debug("Could not place min annotation at %s", idx)
            idx_last = idx

        # RAIN
        axs[1, 1].bar(df.index, df[city]['acc_6h'], width=0.1)
        data_y_max = df[city]['acc_6h'].max()
        if data_y_max < 0.9:
            axs[1, 1].set_ylim([0, 1])
        else:
            axs[1, 1].set_ylim([0, data_y_max + 2.0])
        axs[1, 1].grid(True)
        axs[1, 1].set_ylabel('mm/6h', fontsize=y_fontsize - 10)
        axs[1, 1].yaxis.set_label_position('right')
        axs[1, 1].tick_params(axis='y', which='major', labelsize=20)

        # WIND
        U = df[city]['u_6h'].astype(np.float64)
        V = df[city]['v_6h'].astype(np.float64)
        denom = np.sqrt(U ** 2 + V ** 2)
        # avoid division by zero
        denom[denom == 0] = 1.0
        U_norm = U / denom
        V_norm = V / denom

        data_y_max = df[city]['U'].max()
        axs[2, 1].plot(df.index, df[city]['U'], color='k', linewidth=3)
        if data_y_max < 10.0:
            axs[2, 1].set_ylim([0, 10])
            axs[2, 1].yaxis.set_ticks([0, 5, 10])
        else:
            axs[2, 1].set_ylim([0, data_y_max + 2.0])

        axs[2, 1].grid(True)
        axs[2, 1].set_ylabel('m/s', fontsize=y_fontsize - 10)
        axs[2, 1].yaxis.set_label_position('right')
        axs[2, 1].tick_params(axis='y', which='major', labelsize=20)

        ones = np.ones(len(df.index))
        axs[3, 1].quiver(df.index, ones, U_norm, V_norm, units='width', pivot='mid', width=0.004)
        axs[3, 1].get_yaxis().set_visible(False)

        # X axis limits and formatting
        datemin = np.datetime64(pd.to_datetime(df.index[0]).strftime('%Y-%m-%dT%H'), 'D')
        datemax = np.datetime64(pd.to_datetime(df.index[-1]).strftime('%Y-%m-%dT%H'), 'D') + np.timedelta64(6, 'h')

        axs[-1, 1].xaxis.set_major_locator(days_loc)
        axs[-1, 1].xaxis.set_major_formatter(days_fmt)
        axs[-1, 1].xaxis.set_minor_locator(six_hours_loc)
        axs[-1, 1].xaxis.set_minor_formatter(hour_fmt)

        axs[-1, 1].set_xlim(datemin, datemax)
        axs[-1, 1].grid(True)
        axs[-1, 1].tick_params(axis='x', labelsize=x_fontsize)

        if desired_tz == greenwich_tz:
            axs[-1, 1].set_xlabel('UTC', fontsize=10)
            fileEnding = '_UTC.png'
        else:
            axs[-1, 1].set_xlabel('Local time', fontsize=10)
            fileEnding = '.png'

        # Background shading
        from matplotlib.patches import Rectangle
        for ax_idx in axs[:, 1]:
            try:
                gs = GridShader(ax_idx, facecolor='0.2', first=False, alpha=0.1)
            except Exception:
                logger.debug("GridShader failed for axis")

        # Remove / hide first column axes (parameter icons column)
        for ax_first_col in axs[:, 0]:
            try:
                # try removing from the figure (preferred)
                fig.delaxes(ax_first_col)
            except Exception:
                try:
                    ax_first_col.remove()
                except Exception:
                    try:
                        ax_first_col.set_visible(False)
                    except Exception:
                        logger.debug("Could not remove or hide ax: %s", ax_first_col)

        # Add icons
        image_file_temp = os.path.join(misc_path, 'images', 'Temperature.png')
        if os.path.exists(image_file_temp):
            try:
                img_temp = mpimg.imread(image_file_temp)
                # pick the first remaining axis (axs[0,1]) for displaying the icons column effect
                # we use a new small axes for the image if needed, but previously we removed the left column,
                # so we'll place images directly onto an inset or the figure as needed.
                ax_icon = fig.add_axes([0.02, 0.7, 0.07, 0.18], frameon=False)
                ax_icon.imshow(img_temp)
                ax_icon.axis('off')
            except Exception:
                logger.debug("Could not read temperature icon %s", image_file_temp)

        image_file_rain = os.path.join(misc_path, 'images', 'Rain.png')
        if os.path.exists(image_file_rain):
            try:
                img_rain = mpimg.imread(image_file_rain)
                ax_icon = fig.add_axes([0.02, 0.45, 0.07, 0.12], frameon=False)
                ax_icon.imshow(img_rain)
                ax_icon.axis('off')
            except Exception:
                logger.debug("Could not read rain icon %s", image_file_rain)

        image_file_wind = os.path.join(misc_path, 'images', 'Wind.png')
        if os.path.exists(image_file_wind):
            try:
                img_wind = mpimg.imread(image_file_wind)
                ax_icon = fig.add_axes([0.02, 0.2, 0.07, 0.12], frameon=False)
                ax_icon.imshow(img_wind)
                ax_icon.axis('off')
            except Exception:
                logger.debug("Could not read wind icon %s", image_file_wind)

        plt.subplots_adjust(hspace=0.12)

        figure = fig
        figure.set_size_inches(18, 9)
        save = os.path.join(outdata_path, city + fileEnding)
        try:
            plt.savefig(save, dpi=200)
        except Exception as e:
            logger.error("Failed saving %s: %s", save, e)
        plt.close('all')

    return


class GridShader():
    def __init__(self, ax, first=True, **kwargs):
        self.spans = []
        self.sf = first
        self.ax = ax
        self.kw = kwargs
        self.ax.autoscale(False, axis="x")
        self.cid = self.ax.callbacks.connect('xlim_changed', self.shade)
        self.shade()

    def clear(self):
        for span in list(self.spans):
            try:
                span.remove()
            except Exception:
                pass
        self.spans = []

    def shade(self, evt=None):
        self.clear()
        xticks = self.ax.get_xticks()
        xlim = self.ax.get_xlim()
        # filter ticks inside xlim
        xticks = xticks[(xticks > xlim[0]) & (xticks < xlim[-1])]

        locs = np.concatenate(([[xlim[0]], xticks, [xlim[-1]]]))

        start = locs[1 - int(self.sf)::2]
        end = locs[2 - int(self.sf)::2]

        for s, e in zip(start, end):
            try:
                self.spans.append(self.ax.axvspan(s, e, zorder=0, **self.kw))
            except Exception:
                pass
