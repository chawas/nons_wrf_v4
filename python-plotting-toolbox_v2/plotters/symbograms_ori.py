# -*- coding: utf-8 -*-

'''
Creating symboograms based on data from GFS or WRF GRIB2 files from a UEMS WRF setup

***NOTE: This script assumes that data is available with 1 hour intervalls during the entire forecast period!
'''

# import ast
# import pytz
import logging
import pandas as pd


from tools import config_tools, reset_folders
from config import CONFIG

APP_NAME = 'symbograms'
APP_CONFIG = CONFIG["plotters"][APP_NAME]
locations_file = APP_CONFIG["locationsFile"]
output_time_zone = APP_CONFIG["timeZone"]
outdata_path = APP_CONFIG["outdataPath"]
logger = logging.getLogger("carl-wrf-tools.{}".format(APP_NAME))

def main(df, grib_use_list, output_start_time, output_end_time, output_time_zone):

    reset_folders.refresh(outdata_path, archive=False)  # Clean the outdata folders for this run

    create_symbograms(df, outdata_path)


def create_symbograms(df, outdata_path):
    logger.info('    Creating symbograms...')

    ### HANDLE SYMBOGRAM CONFIGURATION FILE ###
    # Read the configuration file and create a dictionary for each listed city
    symbogram_cities  = config_tools.readCitiesConfig(locations_file)
    choice_list = ['Buhera', 'Bulilima', 'Gutu', 'Mberengwa']  #list(symbogram_cities.keys())[8:15]
    symbo_divs = ""
    for city in df.columns.levels[0]:
        if city in symbogram_cities:
            logger.info('        Working with location: ' + str(city))
            # Data part
            df_precip = pd.DataFrame(df[city]['acc_24h'], index = df.index)
            df_precip.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
            df_temp = pd.DataFrame(df[city]['t'], index = df.index) #Make a simple DataFrame of just temperature
            df_temp.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S') #Convert the index to datetime. Necessary?
            df_symb = pd.DataFrame( df.loc[df.index.strftime('%H:%M').isin(['00:00']), (city)] )
            symbs = df_symb[['weatherType24h', 'weatherSymbol24h']]
            symbs=symbs.assign(day_names=symbs.index.day_name())
            symbs.index = symbs.index.date
            maxs = df_temp.groupby(df_temp.index.date).max()
            mins = df_temp.groupby(df_temp.index.date).min()
            precip = df_precip.groupby(df_precip.index.date).sum()
            temps = pd.merge(maxs, mins, left_index=True, right_index=True)
            tot = pd.merge(temps, symbs, left_index=True, right_index=True)
            tot = pd.merge(tot, precip, left_index=True, right_index=True)
            tot.rename(columns = {'t_x':'max'}, inplace=True)
            tot.rename(columns = {'t_y':'min'}, inplace=True)

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
    fh = open(f"{outdata_path}index.html", "w")
    fh.write(html2)
    fh.close()

def create_symbo_html(symbo_divs):
    html_string = f'''<!DOCTYPE html>
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
    return html_string

def create_html(symbogram, city):
    with open('style.css') as f:
        css = f.read()
    html_string = f'''<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="X-UA-Compatible" content="IE=edge">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MSD Symbogram</title>
            <link rel="stylesheet" href="../../style.css">
            <style>{css}</style>
        </head>
        <body>
            <section>
            <div class = "container">
                    <div class = "box">
                    <div class="city">
                        <h2 class="city-text">{city.upper()}</h2>
                    </div>
                        {symbogram}
                    </div>
                </div> 
            </section>
        </body>
        </html>
    '''
    return html_string


def create_symbo_div(symbogram_table, city):
    symbo_div = f'''
    <div class = "box">
        <div class="city">
            <h2 class="city-text">{city.upper()}</h2>
        </div>
        {symbogram_table}
    </div>      
    '''
    return symbo_div


def create_symbotable(tot, city):
    import base64
    day_names = list(tot['day_names'])
    max_temps = list(tot['max'])
    min_temps = list(tot['min'])
    w_types   = list(tot['weatherType24h'])
    w_symbols = list(tot['weatherSymbol24h'])
    with open(w_symbols[0], 'rb') as f:
        data0 = f.read()
        data0_base64 = base64.b64encode(data0)
        data0_base64 = data0_base64.decode()
    with open(w_symbols[1], 'rb') as f:
        data1 = f.read()
        data1_base64 = base64.b64encode(data1)
        data1_base64 = data1_base64.decode()
    with open(w_symbols[2], 'rb') as f:
        data2 = f.read()
        data2_base64 = base64.b64encode(data2)
        data2_base64 = data2_base64.decode()
    with open(w_symbols[3], 'rb') as f:
        data3 = f.read()
        data3_base64 = base64.b64encode(data3)
        data3_base64 = data3_base64.decode()
    with open(w_symbols[4], 'rb') as f:
        data4 = f.read()
        data4_base64 = base64.b64encode(data4)
        data4_base64 = data4_base64.decode()

    precip = list(tot['acc_24h'])
    table_string = f'''<table class="symbogram--table">
    <tr class="days">
        <th>{day_names[0].upper()[:3]}</th>
        <th>{day_names[1].upper()[:3]}</th>
        <th>{day_names[2].upper()[:3]}</th>
        <th>{day_names[3].upper()[:3]}</th>
        <th>{day_names[4].upper()[:3]}</th>
    </tr>
    <tr class="max-temps">
        <td>{int(round(max_temps[0], 0))}&deg</td>
        <td>{int(round(max_temps[1], 0))}&deg</td>
        <td>{int(round(max_temps[2], 0))}&deg</td>
        <td>{int(round(max_temps[3], 0))}&deg</td>
        <td>{int(round(max_temps[4], 0))}&deg</td>
    </tr>
    <tr class="symbols">
        <td><img src="data:image/jpeg;base64, {data0_base64}" alt="{w_types[0]}"></td>
        <td><img src="data:image/jpeg;base64, {data1_base64}"></td>
        <td><img src="data:image/jpeg;base64, {data2_base64}"></td>
        <td><img src="data:image/jpeg;base64, {data3_base64}"></td>
        <td><img src="data:image/jpeg;base64, {data4_base64}"></td>
    </tr>
    <tr class="min-temps">
        <td>{int(round(min_temps[0], 0))}&deg</td>
        <td>{int(round(min_temps[1], 0))}&deg</td>
        <td>{int(round(min_temps[2], 0))}&deg</td>
        <td>{int(round(min_temps[3], 0))}&deg</td>
        <td>{int(round(min_temps[4], 0))}&deg</td>
    </tr>
    <tr class="precipitation">
        <td>{round(precip[0], 1)}</td>
        <td>{round(precip[1], 1)}</td>
        <td>{round(precip[2], 1)}</td>
        <td>{round(precip[3], 1)}</td>
        <td>{round(precip[4], 1)}</td>
    </tr>
    <tr class="units">
        <td>mm</td>
        <td>mm</td>
        <td>mm</td>
        <td>mm</td>
        <td>mm</td>
    </tr>
    </table>
    '''

    return table_string


if __name__ == '__main__':
    main()