# -*- coding: utf-8 -*-

'''
Creating meteograms based on data from GFS or WRF GRIB2 files from a UEMS WRF setup

***NOTE: This script assumes that data is available with 1 hour intervalls during the entire forecast period!
'''
# import pytz
import logging

import numpy as np
import pandas as pd

# import cartopy.crs as ccrs
# import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.offsetbox import (TextArea, OffsetImage, AnnotationBbox)
# import matplotlib.gridspec as gridspec
import matplotlib.image as mpimg

# from grib_reader import gribEcCodes, reglambert, grib_read

from tools import config_tools, reset_folders
from config import CONFIG

APP_NAME = 'meteograms'
logger = logging.getLogger("carl-wrf-tools.{}".format(APP_NAME))

APP_CONFIG = CONFIG["plotters"][APP_NAME]
# wanted_parameters = ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["wantedParameters"])
# parameter_names =  ast.literal_eval(APP_CONFIG["parameters"][DATA_SOURCE]["parameterNames"])
locations_file = APP_CONFIG["locationsFile"]
output_time_zone = APP_CONFIG["timeZone"]
symbols = APP_CONFIG["symbols"]
outdata_path = APP_CONFIG["outdataPath"]

# def main(df, grib_use_list, output_start_time, output_end_time):
def main(df, grib_use_list, output_start_time, output_end_time, desired_tz, greenwich_tz):

    misc_path = './misc/'

    reset_folders.refresh(outdata_path, archive=False)  # Clean the outdata folders for this run
    
    ### CREATE METEOGRAMS FROM THE DATAFRAME ###
    match_timestamps = ['00:00', '06:00', '12:00', '18:00']
    createMeteogram_df(df, match_timestamps, misc_path, outdata_path, desired_tz, greenwich_tz, symbols)


def createMeteogram_df(df, match_timestamps, misc_path, outdata_path, desired_tz, greenwich_tz, symbols):
    logger.info('    Creating meteograms...')

    ### HANDLE METEOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    meteogram_cities  = config_tools.readCitiesConfig(locations_file)

    ### matplotlib parameters for plotting ###
    y_fontsize = 30
    x_fontsize = 12
    
    #Locate x axis positions of hours, days and such
    days_loc  = mdates.DayLocator(tz=desired_tz)
    hours_loc = mdates.HourLocator(tz=desired_tz)
    two_hours_loc = mdates.HourLocator(byhour=range(0,24,12), tz=desired_tz)
    six_hours_loc = mdates.HourLocator(byhour=range(0,24,6), tz=desired_tz)
    
    # Specify the ouptut date format
    days_fmt = mdates.DateFormatter('%a \n %b %d', tz=desired_tz)
    hour_fmt = mdates.DateFormatter('%H', tz=desired_tz)
    
    
    for city in df.columns.levels[0]:
        if city in meteogram_cities:
            logger.info('        Working with location: ' + str(city))
            
            fig, axs = plt.subplots(4,2, gridspec_kw={'height_ratios': [20, 9, 7, 3], 'width_ratios': [1,12]}, sharex='col')

            fig.suptitle('Meteogram for ' + city, fontweight='bold', fontsize=30, horizontalalignment='right')

            ### TEMPERATURE PLOT ###
            axs[0,1].plot(df.index, df[city]['t'], color = 'red', linewidth = 3)

            # Format the y-ticks
            data_y_max = df[city]['t'].max()
            data_y_min = df[city]['t'].min()
            if data_y_min > 0.0 and data_y_max < 40.0: #This is the standard
                axs[0,1].set_ylim([0,40])
            elif data_y_min < 0.0: # Adjust for the temp max/min box
                axs[0,1].set_ylim( [ data_y_min - 6.0 , 40.0 ] )
            else: # Adjust for the temp max/min box
                axs[0,1].set_ylim( [ data_y_min - 6.0 , data_y_max + 6.0 ] )

            y_lim_min = axs[0,1].get_ylim()
            
            axs[0,1].grid(True)

            axs[0,1].set_ylabel('$^\circ$C', fontsize = y_fontsize, horizontalalignment='right')#, rotation='horizontal', position=(1,2))
    
            axs[0,1].yaxis.set_label_position('right')
            axs[0,1].tick_params(axis='y', which='major', labelsize=20)
            #axs[0,1].set_xlabel('Temperature', fontweight='bold')

            # ANNOTATIONS
            # Extract the maximums and minimums
            df_temp = pd.DataFrame(df[city]['t'], index = df.index) #Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S') #Convert the index to datetime. Necessary?

            maxs = df_temp.groupby(pd.Grouper(freq='D'))['t'].transform('max') #Get the daily maximum values
            mins = df_temp.groupby(pd.Grouper(freq='D'))['t'].transform('min') #Get the daily minimum values
            df_temp_max = df_temp[df_temp['t'] == maxs] #Create a temporary dataframe of daily max values
            df_temp_min = df_temp[df_temp['t'] == mins] #Create a temporary dataframe of daily min values

            idx_last = None
            for idx, row in df_temp_max.iterrows(): #Loop over the max values and create print boxes
                max_val = row['t']
                offsetbox = TextArea(str(int(np.round(max_val, 0))), textprops = dict(fontsize=25, color='white'))

                if idx_last == None or idx.day != idx_last.day: #In order to not print the same temperature more than once
                    ab = AnnotationBbox(offsetbox, (idx, int(np.round(max_val, 0))),
                                xybox=(20, 40),
                                xycoords='data',
                                boxcoords="offset points",
                                #arrowprops=dict(arrowstyle="-"),
                                bboxprops = dict(boxstyle='round', color='r', edgecolor='r'))#, fc='0.8'))
                    axs[0,1].add_artist(ab)

            # Add weather symbol to plot
            if symbols == True:
                df_symb = pd.DataFrame( df.loc[df.index.strftime('%H:%M').isin(match_timestamps), (city)] )
                # print('')
                # print(df_symb)
                for idx, row in df_symb.iterrows():
                    # print(idx)
                    # print(row)
                    image_file_symbol = row['weatherSymbol6h']
                    img_symbol = mpimg.imread(image_file_symbol)

                    imagebox = OffsetImage(img_symbol, zoom=0.20)
                    imagebox.image.axes = axs[0,1]
                    ib =  AnnotationBbox(imagebox, (idx, y_lim_min[0] + 3),
                            xybox=(0., 0.),
                            xycoords='data',
                            boxcoords="offset points",
                            # pad=0.5,
                            bboxprops = dict(boxstyle='round', color='white'),
                            # arrowprops=dict(
                            #     arrowstyle="->",
                            #     connectionstyle="angle,angleA=0,angleB=90,rad=3")
                            )
                    axs[0,1].add_artist(ib)

                    idx_last = idx

            idx_last = None
            for idx, row in df_temp_min.iterrows(): #Loop over the min values and create print boxes

                min_val = row['t']
                offsetbox = TextArea(str(int(np.round(min_val, 0))), textprops = dict(fontsize=25, color='white'))

                if idx_last == None or idx.day != idx_last.day: #In order to not print the same temperature more than once
                    ab = AnnotationBbox(offsetbox, (idx, int(np.round(min_val, 0))),
                                xybox=(0, -40),
                                xycoords='data',
                                boxcoords="offset points",
                                #arrowprops=dict(arrowstyle="-"),
                                bboxprops = dict(boxstyle='round', color='b'))#, fc='0.8'))
                    axs[0,1].add_artist(ab)
                idx_last = idx

            ##########################

            ### RAIN PLOT ###
            #axs[1,1].bar(df.index, df[city]['prec_24h'], width = 0.15, color = 'orange')
            axs[1,1].bar(df.index, df[city]['acc_6h'], width = 0.1) #0.1 is good for a 6 day span

            # Format the y-ticks
            data_y_max = df[city]['acc_6h'].max()
            if data_y_max < 0.9:
                axs[1,1].set_ylim([0,1])
            else:
                axs[1,1].set_ylim([0, data_y_max + 2.0])
            axs[1,1].grid(True)

            axs[1,1].set_ylabel('mm/6h', fontsize = y_fontsize - 10)#, rotation='horizontal')
            axs[1,1].yaxis.set_label_position('right')
            axs[1,1].tick_params(axis='y', which='major', labelsize=20)
            #axs[1,1].set(xlabel = '6 hour accumulated precipitation', ylabel = 'mm')


            ##################

            ### WIND PLOT ###

            U = df[city]['u_6h'].astype(np.float64)
            V = df[city]['v_6h'].astype(np.float64)
            U_norm = U / np.sqrt(U**2 + V**2)
            V_norm = V / np.sqrt(U**2 + V**2)

            data_y_max = df[city]['U'].max()

            axs[2,1].plot(df.index, df[city]['U'], color = 'k', linewidth = 3)
            #axs[2,1].set(xlabel = 'Average wind speed', ylabel = 'm/s') # plt.show()
            # s
            if data_y_max < 10.0:
                axs[2,1].set_ylim([0, 10])
                axs[2,1].yaxis.set_ticks([0,5,10])

            else:
                axs[2,1].set_ylim([0, data_y_max + 2.0])

            axs[2,1].grid(True)
            # axs[2,1].grid(which='minor', linestyle='-', linewidth='0.5', color='black')
            axs[2,1].set_ylabel('m/s', fontsize = y_fontsize-10)#, rotation='horizontal')
            axs[2,1].yaxis.set_label_position('right')
            axs[2,1].tick_params(axis='y', which='major', labelsize=20)
            #axs[3].plot(df.index, df[city]['Udir'], color = 'blue', linewidth = 3)
            ones = np.ones(len(df.index))
            
            #axs[3].quiver(df.index, ones, df[city]['u_6h'].astype(np.float64)/( np.sqrt( (df[city]['u_6h'].astype(np.float64)**2) + df[city]['v_6h'].astype(np.float64) ) ), df[city]['v_6h'].astype(np.float64)/( np.sqrt( (df[city]['u_6h'].astype(np.float64)**2) + df[city]['v_6h'].astype(np.float64) ) ), units= 'xy', pivot = 'mid', scale = 5, width = 0.007, headwidth=3., headlength=4.)
            axs[3,1].quiver(df.index, ones, U_norm, V_norm, units= 'width', pivot = 'mid', width = 0.004)
            axs[3,1].get_yaxis().set_visible(False)
            #axs[3,1].set(ylabel = 'Wind direction')

            
            # #################
    # plt.show()
            # s
            #round to nearest days
            #greenwich_tz = pytz.timezone('Greenwich')
            datemin = np.datetime64( df.index[0].replace(tzinfo=None).strftime('%Y-%m-%dT%H'), 'D') + np.timedelta64(0, 'h')
            datemax = np.datetime64( df.index[-1].replace(tzinfo=None).strftime('%Y-%m-%dT%H'), 'D') + np.timedelta64(6, 'h')

            axs[-1,1].xaxis.set_major_locator(days_loc)
            axs[-1,1].xaxis.set_major_formatter(days_fmt)

            axs[-1,1].xaxis.set_minor_locator(six_hours_loc)
            axs[-1,1].xaxis.set_minor_formatter(hour_fmt)
            
            axs[-1,1].set_xlim(datemin, datemax)
            #axs[-1,1].xaxis.set_ticks(xtick_date_array)
            axs[-1,1].grid(True)
            axs[-1,1].tick_params(axis='x', labelsize = x_fontsize)

            if desired_tz == greenwich_tz:
                axs[-1,1].set_xlabel('UTC', fontsize = 10)
                fileEnding = '_UTC.png'
            else:
                axs[-1,1].set_xlabel('Local time', fontsize = 10)
                fileEnding = '.png'


            # #Color on background

            # nav = 0 # plt.show()
            # s
            # Make every second day grey using the GridShader class
            for ax_idx in axs[:,1]:
                gs = GridShader(ax_idx, facecolor = '0.2', first = False, alpha = 0.1)
            # gs0 = GridShader(axs[0], facecolor = '0.2', first = False, alpha = 0.1)
            # gs1 = GridShader(axs[1], facecolor = '0.2', first = False, alpha = 0.1)


            # Add parameter symbols as a separate column of plots
            for ax_first_col in axs[:,0]:
                shax = ax_first_col.get_shared_x_axes()
                shax.remove(ax_first_col)

            image_file_temp = misc_path + 'images/Temperature.png'
            img_temp = mpimg.imread(image_file_temp)

            axs[0,0].imshow(img_temp)
            axs[0,0].axis('off')

            image_file_rain = misc_path + 'images/Rain.png'
            img_rain = mpimg.imread(image_file_rain)
            axs[1,0].imshow(img_rain)
            axs[1,0].axis('off')

            image_file_wind = misc_path + 'images/Wind.png'
            img_wind = mpimg.imread(image_file_wind)
            axs[2,0].imshow(img_wind)
            #axs[3,0].imshow(img_wind)
            axs[2,0].axis('off')
            axs[3,0].axis('off')

            plt.subplots_adjust(hspace=0.12)#(hspace=0.075)

            # plt.show()
            # sys.exit()

            figure = plt.gcf()
            figure.set_size_inches(18, 9)
            save = outdata_path + city + fileEnding
            plt.savefig(save,dpi=200)
            #plt.clf()
            plt.close('all')
        # else:
        #     print(f'{city} was filtered out to fit {APP_NAME} meteogram cities.')

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
        for span in self.spans:
            try:
                span.remove()
            except:
                pass
    def shade(self, evt=None):
        self.clear()
        xticks = self.ax.get_xticks()
        xlim = self.ax.get_xlim()
        xticks = xticks[(xticks > xlim[0]) & (xticks < xlim[-1])]

        locs = np.concatenate(([[xlim[0]], xticks, [xlim[-1]]]))

        start = locs[1-int(self.sf)::2]  
        end = locs[2-int(self.sf)::2]

        for s, e in zip(start, end):
            self.spans.append(self.ax.axvspan(s, e, zorder=0, **self.kw))


if __name__ == '__main__':
    main()