# streamlined_symbograms.py

import sys
import logging
import pandas as pd

sys.path.append("/home/wrf/nons/python-plotting-toolbox")

from tools import config_tools, reset_folders
from config import CONFIG

APP_NAME = 'symbograms'
APP_CONFIG = CONFIG["plotters"][APP_NAME]
locations_file = APP_CONFIG["locationsFile"]
output_time_zone = APP_CONFIG["timeZone"]
outdata_path = APP_CONFIG["outdataPath"]
logger = logging.getLogger(f"carl-wrf-tools.{APP_NAME}")

def main(df, grib_use_list, output_start_time, output_end_time, output_time_zone):
    reset_folders.refresh(outdata_path, archive=False)
    create_symbograms(df, outdata_path, ['Bulilima', 'Mangwe', 'Matobo'])


    create_symbograms_mat_south1(df, outdata_path)

    # create_symbograms_mat_south2(df, outdata_path)
    #
    # create_symbograms_mat_north(df, outdata_path)
    #
    # create_symbograms_manicaland(df, outdata_path)
    #
    # create_symbograms_gwanda_gcf(df, outdata_path)
    #
    # create_symbograms_bulilima_gcf(df, outdata_path)
    #
    create_symbograms_main_city_centers_01(df, outdata_path)
    #
    create_symbograms_main_city_centers_02(df, outdata_path)
    #
    create_symbograms_holiday_resorts_01(df, outdata_path)
    #
    create_symbograms_holiday_resorts_02(df, outdata_path)

def create_symbograms(df, outdata_path, choice_list):
    logger.info('    Creating symbograms...')
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    symbo_divs = ""

    for city in df.columns.levels[0]:
        if city not in symbogram_cities:
            continue

        logger.info(f'        Working with location: {city}')

        df_precip = df[city]['acc_24h'].copy()
        df_temp = df[city]['t'].copy()
        df_symb = df.loc[df.index.strftime('%H:%M') == '00:00', city][['weatherType24h', 'weatherSymbol24h']].copy()

        df_precip.index = df_temp.index = pd.to_datetime(df.index)

        maxs = df_temp.groupby(df_temp.index.date).max()
        mins = df_temp.groupby(df_temp.index.date).min()
        g_min = pd.DataFrame(mins - 3.5)
        g_min.columns = ['g_min']
        g_min.index = pd.to_datetime(g_min.index).date

        symbs = df_symb.copy()
        symbs.index = symbs.index.date
        symbs['day_names'] = pd.to_datetime(symbs.index).day_name()

        temps = pd.merge(maxs, mins, left_index=True, right_index=True)
        tot = pd.merge(temps, symbs, left_index=True, right_index=True)

        # Force merge g_min even if misaligned; fill NaN if needed
        tot = pd.merge(tot, g_min, left_index=True, right_index=True, how='left')

        tot.rename(columns={'t_x': 'max', 't_y': 'min'}, inplace=True)

        # Ensure g_min exists for rendering
        if 'g_min' not in tot.columns:
            logger.warning(f"g_min missing for {city}; filling with NaN")
            tot['g_min'] = float('nan')

        symbogram_table = create_symbotable(tot, city)
        symbo_div = create_symbo_div(symbogram_table, city)
        html = create_html(symbogram_table, city)

        with open(f"{outdata_path}{city}.html", "w") as f:
            f.write(html)

        if city in choice_list:
            symbo_divs += symbo_div

    html2 = create_symbo_html(symbo_divs)
    with open(f"{outdata_path}mat_south_01.html", "w") as fh:
        fh.write(html2)




def create_symbograms_mat_south1(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    choice_list = ['Bulilima', 'Mangwe', 'Matobo']  # list(symbogram_cities.keys())[8:15]
    # choice_list = ['Gwanda']  #list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()


            #begin g_min
            # Properly convert mins Series to DataFrame before renaming
            g_min = pd.DataFrame(mins - 3.5)
            g_min.columns = ['g_min']
            g_min.index = pd.to_datetime(g_min.index).date

            symbs = df_symb.copy()
            symbs.index = symbs.index.date
            symbs['day_names'] = pd.to_datetime(symbs.index).day_name()

            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)

            # Force merge g_min even if misaligned; fill NaN if needed
            tot = pd.merge(tot, g_min, left_index=True, right_index=True, how='left')

            tot.rename(columns={'t_x': 'max', 't_y': 'min'}, inplace=True)

            # Ensure g_min exists for rendering
            if 'g_min' not in tot.columns:
                logger.warning(f"g_min missing for {city}; filling with NaN")
                tot['g_min'] = float('nan')

            # end g_min


            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}mat_south_01.html", "w")
    fh.write(html2)
    fh.close()


def create_symbograms_mat_south2(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    choice_list = ['BeitBridge', 'Gwanda', 'Insiza', 'Umzingwane']  # list(symbogram_cities.keys())[8:15]
    # choice_list = ['Gwanda']  #list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()
            precip = df_precip.groupby(df_precip.index.date).sum()
            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)
            tot = pd.merge(tot, precip, left_index=True, right_index=True)
            tot.rename(columns={'t_x': 'max'}, inplace=True)
            tot.rename(columns={'t_y': 'min'}, inplace=True)

            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}mat_south_02.html", "w")
    fh.write(html2)
    fh.close()


def create_symbograms_mat_north(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    choice_list = ['Hwange', 'Binga']  # list(symbogram_cities.keys())[8:15]
    # choice_list = ['Gwanda']  #list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()
            precip = df_precip.groupby(df_precip.index.date).sum()
            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)
            tot = pd.merge(tot, precip, left_index=True, right_index=True)
            tot.rename(columns={'t_x': 'max'}, inplace=True)
            tot.rename(columns={'t_y': 'min'}, inplace=True)

            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}mat_north_01.html", "w")
    fh.write(html2)
    fh.close()


def create_symbograms_manicaland(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    choice_list = ['Chipinge', 'Chimanimani', 'Buhera']  # list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()
            precip = df_precip.groupby(df_precip.index.date).sum()
            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)
            tot = pd.merge(tot, precip, left_index=True, right_index=True)
            tot.rename(columns={'t_x': 'max'}, inplace=True)
            tot.rename(columns={'t_y': 'min'}, inplace=True)

            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}manicaland.html", "w")
    fh.write(html2)
    fh.close()


def create_symbograms_gwanda_gcf(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    # choice_list = ['Gwanda', 'Bulilima', 'Umzingwane', 'Mangwe']  #list(symbogram_cities.keys())[8:15]
    choice_list = ['Gwanda']  # list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()
            precip = df_precip.groupby(df_precip.index.date).sum()
            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)
            tot = pd.merge(tot, precip, left_index=True, right_index=True)
            tot.rename(columns={'t_x': 'max'}, inplace=True)
            tot.rename(columns={'t_y': 'min'}, inplace=True)

            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}gwanda_gcf.html", "w")
    fh.write(html2)
    fh.close()


def create_symbograms_bulilima_gcf(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    # choice_list = ['Gwanda', 'Bulilima', 'Umzingwane', 'Mangwe']  #list(symbogram_cities.keys())[8:15]
    choice_list = ['Bulilima']  # list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()
            precip = df_precip.groupby(df_precip.index.date).sum()
            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)
            tot = pd.merge(tot, precip, left_index=True, right_index=True)
            tot.rename(columns={'t_x': 'max'}, inplace=True)
            tot.rename(columns={'t_y': 'min'}, inplace=True)

            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}bulilima_gcf.html", "w")
    fh.write(html2)
    fh.close()


def create_symbograms_main_city_centers_01(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    choice_list = ['Harare', 'Bulawayo', 'Gweru', 'Mutare', 'Kwekwe', 'Kadoma', 'Masvingo', 'Chinhoyi', 'Lupane',
                   'Bindura', 'Marondera', 'Gwanda']  # list(symbogram_cities.keys())[8:15]
    # choice_list = ['Gwanda']  #list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()

            # begin g_min
            # Properly convert mins Series to DataFrame before renaming
            g_min = pd.DataFrame(mins - 3.5)
            g_min.columns = ['g_min']
            g_min.index = pd.to_datetime(g_min.index).date

            symbs = df_symb.copy()
            symbs.index = symbs.index.date
            symbs['day_names'] = pd.to_datetime(symbs.index).day_name()

            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)

            # Force merge g_min even if misaligned; fill NaN if needed
            tot = pd.merge(tot, g_min, left_index=True, right_index=True, how='left')

            tot.rename(columns={'t_x': 'max', 't_y': 'min'}, inplace=True)

            # Ensure g_min exists for rendering
            if 'g_min' not in tot.columns:
                logger.warning(f"g_min missing for {city}; filling with NaN")
                tot['g_min'] = float('nan')

            # end g_min

            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}main_city_centers_01.html", "w")
    fh.write(html2)
    fh.close()


def create_symbograms_main_city_centers_02(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    choice_list = ['Masvingo', 'Chinhoyi', 'Lupane', 'Bindura', 'Marondera',
                   'Gwanda']  # list(symbogram_cities.keys())[8:15]
    # choice_list = ['Gwanda']  #list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()


            # precip = df_precip.groupby(df_precip.index.date).sum()
            # temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            # tot = pd.merge(temps, symbs, left_index=True, right_index=True)
            # tot = pd.merge(tot, precip, left_index=True, right_index=True)
            # tot.rename(columns={'t_x': 'max'}, inplace=True)
            # tot.rename(columns={'t_y': 'min'}, inplace=True)

            # begin g_min
            # Properly convert mins Series to DataFrame before renaming
            g_min = pd.DataFrame(mins - 3.5)
            g_min.columns = ['g_min']
            g_min.index = pd.to_datetime(g_min.index).date

            symbs = df_symb.copy()
            symbs.index = symbs.index.date
            symbs['day_names'] = pd.to_datetime(symbs.index).day_name()

            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)

            # Force merge g_min even if misaligned; fill NaN if needed
            tot = pd.merge(tot, g_min, left_index=True, right_index=True, how='left')

            tot.rename(columns={'t_x': 'max', 't_y': 'min'}, inplace=True)

            # Ensure g_min exists for rendering
            if 'g_min' not in tot.columns:
                logger.warning(f"g_min missing for {city}; filling with NaN")
                tot['g_min'] = float('nan')

            # end g_min



            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}main_city_centers_02.html", "w")
    fh.write(html2)
    fh.close()


def create_symbograms_holiday_resorts_01(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    choice_list = ['VicFalls', 'Kariba', 'GreatZimbabwe', 'Nyanga', 'Vumba', 'Matobo', 'Chimanimani', 'ChinhoyiCaves',
                   'Binga', 'HotSprings', 'HwangeNatPark', 'Gonarezhou']  # list(symbogram_cities.keys())[8:15]
    # choice_list = ['Gwanda']  #list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()

            # begin g_min
            # Properly convert mins Series to DataFrame before renaming
            g_min = pd.DataFrame(mins - 3.5)
            g_min.columns = ['g_min']
            g_min.index = pd.to_datetime(g_min.index).date

            symbs = df_symb.copy()
            symbs.index = symbs.index.date
            symbs['day_names'] = pd.to_datetime(symbs.index).day_name()

            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)

            # Force merge g_min even if misaligned; fill NaN if needed
            tot = pd.merge(tot, g_min, left_index=True, right_index=True, how='left')

            tot.rename(columns={'t_x': 'max', 't_y': 'min'}, inplace=True)

            # Ensure g_min exists for rendering
            if 'g_min' not in tot.columns:
                logger.warning(f"g_min missing for {city}; filling with NaN")
                tot['g_min'] = float('nan')

            # end g_min

            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}holiday_resorts_01.html", "w")
    fh.write(html2)
    fh.close()


def create_symbograms_holiday_resorts_02(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities = config_tools.readCitiesConfig(locations_file)
    choice_list = ['Chimanimani', 'ChinhoyiCaves', 'Binga', 'HotSprings', 'HwangeNatPark',
                   'Gonarezhou']  # list(symbogram_cities.keys())[8:15]
    # choice_list = ['Gwanda']  #list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index=df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index=df.index)  # Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index,
                                           format='%Y-%m-%d %H:%M:%S')  # Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame(df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)])
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs = symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()

            # begin g_min
            # Properly convert mins Series to DataFrame before renaming
            g_min = pd.DataFrame(mins - 3.5)
            g_min.columns = ['g_min']
            g_min.index = pd.to_datetime(g_min.index).date

            symbs = df_symb.copy()
            symbs.index = symbs.index.date
            symbs['day_names'] = pd.to_datetime(symbs.index).day_name()

            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)

            # Force merge g_min even if misaligned; fill NaN if needed
            tot = pd.merge(tot, g_min, left_index=True, right_index=True, how='left')

            tot.rename(columns={'t_x': 'max', 't_y': 'min'}, inplace=True)

            # Ensure g_min exists for rendering
            if 'g_min' not in tot.columns:
                logger.warning(f"g_min missing for {city}; filling with NaN")
                tot['g_min'] = float('nan')

            # end g_min

            # Html part
            symbogram_table = create_symbotable(tot, city)
            symbo_div = create_symbo_div(symbogram_table, city)
            html = create_html(symbogram_table, city)
            # Writing html files
            text_file = open(f"{outdata_path}{city}.html", "w")
            text_file.write(html)
            text_file.close()

            if city in choice_list:
                symbo_divs = symbo_divs + symbo_div

    html2 = create_symbo_html(symbo_divs)
    fh = open(f"{outdata_path}holiday_resorts_02.html", "w")
    fh.write(html2)
    fh.close()


def create_symbo_div(table, city):
    return f'''
    <div class = "box">
        <div class="city">
            <h2 class="city-text">{city.upper()}</h2>
        </div>
        {table}
    </div>
    '''

def create_html(table, city):
    with open('style.css') as f:
        css = f.read()
    return f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{city.upper()} Symbogram</title>
        <style>{css}</style>
    </head>
    <body>
        <section>
        <div class = "container">
            <div class = "box">
                <div class="city">
                    <h2 class="city-text">{city.upper()}</h2>
                </div>
                {table}
            </div>
        </div>
        </section>
    </body>
    </html>
    '''

def create_symbo_html(symbo_divs):
    return f'''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MSD Symbograms</title>
        <link rel="stylesheet" href="../../style.css">
    </head>
    <body>
        <section>
            <div class = "container">
                {symbo_divs}
            </div> 
        </section>
    </body>
    </html>
    '''

def create_symbotable(tot, city):
    import base64
    print("DEBUG: tot.columns =", tot.columns)
    print("DEBUG: tot.index =", tot.index)
    print("DEBUG: tot shape =", tot.shape)
    print("DEBUG: city =", city)
    day_names = list(tot['day_names'])
    max_temps = list(tot['max'])
    min_temps = list(tot['min'])
    g_min = list(tot['g_min'])
    symbols = list(tot['weatherSymbol24h'])

    def img_data(symbol):
        with open(symbol, 'rb') as f:
            return base64.b64encode(f.read()).decode()

    img_tags = ''.join([f'<td><img src="data:image/jpeg;base64, {img_data(s)}"></td>' for s in symbols[:5]])

    return f'''<table class="symbogram--table">
    <tr class="days">{''.join([f'<th>{d.upper()[:3]}</th>' for d in day_names[:5]])}</tr>
    <tr class="max-temps">{''.join([f'<td>{int(round(t, 0))}&deg</td>' for t in max_temps[:5]])}</tr>
    <tr class="symbols">{img_tags}</tr>
    <tr class="min-temps">{''.join([f'<td>{int(round(t, 0))}&deg</td>' for t in min_temps[:5]])}</tr>
    <tr class="g_min-temps">{''.join([f'<td>{int(round(t, 0))}&deg</td>' for t in g_min[:5]])}</tr>
    </table>'''

if __name__ == '__main__':
    main()
