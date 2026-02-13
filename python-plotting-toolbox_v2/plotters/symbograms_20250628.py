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
