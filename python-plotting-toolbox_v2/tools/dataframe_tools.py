import pandas as pd
import numpy as np

from tools import calc_tools

def calcU_df(df, parameter_names):

    '''
    Calculate the Pythagorized wind U from u and v
    Return the size of the wind vector U and the wind direction in degrees
    '''
    # logger.info('    Calculating wind...')

    if 'u' in df.columns.levels[1] and 'v' in df.columns.levels[1]:
        # logger.info('        Found wind components u and v')
        # logger.info('        Will create wind U and Udir from \'u\' and \'v\'')
        for city in df.columns.levels[0]:
            df.loc[:, (city, 'U_squared')] = df.loc[:, (city, 'u')]**2 + df.loc[:, (city, 'v')]**2
        #print(df)
        for city in df.columns.levels[0]:
            # df.loc[:, (city, 'U')] =  np.sqrt( df.loc[:, (city, 'U_squared')].astype(np.float64) )
            df[(city, 'U')] =  np.sqrt( df[(city, 'U_squared')].astype(np.float64) )
            
            df.loc[:, (city, 'Udir')] = calc_tools.windDirFromVect(df.loc[:, (city, 'u')].astype(np.float64), df.loc[:, (city, 'v')].astype(np.float64))
            df.drop('U_squared', axis = 1, level = 1)
    return df


def calc6U_df(df, parameter_names, match_timestamps, window_len):
    '''
    Calculate 6 hour average wind (u and v components)
    '''
    # logger.info('    Calculating 6 hour wind...')

    if 'u' in df.columns.levels[1] and 'v' in df.columns.levels[1]:
        for city in df.columns.levels[0]:
            df.loc[df.index.strftime('%H:%M').isin(match_timestamps), (city, 'u_6h')] = pd.Series.rolling(df.loc[:, (city, 'u')], window = window_len, min_periods = 1).mean()
            df.loc[df.index.strftime('%H:%M').isin(match_timestamps), (city, 'v_6h')] = pd.Series.rolling(df.loc[:, (city, 'v')], window = window_len, min_periods = 1).mean()

    return df


def createMultiIndexDataFrame(cities_Dict, timeIndexArray, parameter_names):
    '''
    Creates a multi index dataframe based on the level of keys in incoming dict.
    For now, only two specified index levels is possible
    '''
    # Create a list of empty lists for each city in config file
    columnArrays = [[],[]]
    valuesArray  = []

    #FOR EACH OF THE VALUES IN RE-ORDERED DICT, CREATE MULTIINDEX COLUMN NAMES
    #Example:
    #[['ALPS', 'ALPS', 'ALPS', 'ALPS', 'SE', 'SE', 'SE', 'SE', 'UK', 'UK', 'UK', 'UK'], 
    # ['TEMP', 'TEMP', 'GWH', 'GWH', 'TEMP', 'TEMP', 'GWH', 'GWH', 'TEMP', 'TEMP', 'GWH', 'GWH'], 
    # ['CURRENT', 'REFERENCE', 'CURRENT', 'REFERENCE', 'CURRENT', 'REFERENCE', 'CURRENT', 'REFERENCE', 'CURRENT', 'REFERENCE', 'CURRENT', 'REFERENCE']]
    for city in cities_Dict.keys():
        for param in parameter_names:#cities_Dict[city].keys():
            #for valueType in cities_Dict[city][param].keys():
            columnArrays[0].append(city)
            columnArrays[1].append(param)
                #columnArrays[2].append(valueType)

    #Inititate multiindex datafram from the above
    df_multi = pd.DataFrame(columns=columnArrays, index=timeIndexArray)     ##I THINK THIS IS THE DF STRUCTURE WE WANT
    df_multi.index = pd.to_datetime(df_multi.index) #Convert date indices to datetime
    df_multi.sort_index(inplace=True) #Sort indices

    for city in cities_Dict.keys():
        for param in parameter_names:
            #for valueType in re_ordered_dict[region][param].keys():
                for timeIndex, timeStep in enumerate(timeIndexArray):# cities_Dict[city]['datetimes_utc']:
                    value = cities_Dict[city][param][timeIndex]
                    df_multi.at[timeStep, (city, param)] = value

    return df_multi

def calc_acc_prec_in_df(df, match_timestamps, accumulated_precipitation, precipitation_mult_factor, window_len):
    '''
    Calculate accumulated precipitation
    '''
    new_column = 'acc_{}h'.format(window_len)

    if 'tp' not in df.columns.levels[1] and 'prec' not in df.columns.levels[1]:
        print('        No total precipitation in DataFrame')
        print('        Will create total precipitation \'prec\' from \'acpcp\' and \'ncpcp\'')
        if 'acpcp' in df.columns.levels[1] and 'ncpcp' in df.columns.levels[1]:
            for city in df.columns.levels[0]:
                df.loc[:, (city, 'prec')] = (df.loc[:, (city, 'acpcp')] + df.loc[:, (city, 'ncpcp')]) * precipitation_mult_factor
    elif 'tp' in df.columns.levels[1]:
        for city in df.columns.levels[0]:
                df.loc[:, (city, 'prec')] = df.loc[:, (city, 'tp')] * precipitation_mult_factor

    for city in df.columns.levels[0]:
        if accumulated_precipitation == False:
            df.loc[df.index.strftime('%H:%M').isin(match_timestamps), (city, new_column)] = pd.Series.rolling(df.loc[:, (city, 'prec')], window = window_len).sum()
        elif accumulated_precipitation == True:
            de_acc_series = df.loc[:, (city, 'prec')].rolling(f'{window_len}h').apply(lambda x: x.iloc[-1] - x.iloc[0])
            de_acc_series[de_acc_series<0] = 0
            df.loc[df.index.strftime('%H:%M').isin(match_timestamps), (city, new_column)] = de_acc_series
    
    return df, new_column


def calcTotalCloudCover(df):
    '''Calculating total cloud cover'''

    if 'lcc' in df.columns.levels[1] and 'mcc' in df.columns.levels[1] and 'hcc' in df.columns.levels[1] and 'prec' in df.columns.levels[1]:
        for city in df.columns.levels[0]:
            for time_index in df.index:
                lcc = df.loc[time_index, (city, 'lcc')] / 100.0 #From percent to fraction
                mcc = df.loc[time_index, (city, 'mcc')] / 100.0 #From percent to fraction
                hcc = df.loc[time_index, (city, 'hcc')] / 100.0 #From percent to fraction

                ### The Esbjorn routine for total cloud cover ###
                tcc = 1.0
                tcc = tcc * ( (1.0 - max([hcc, mcc])) / (1.0 - min([hcc, 0.99]))  )
                tcc = tcc * ( (1.0 - max([mcc, lcc])) / (1.0 - min([mcc, 0.99]))  )
                tcc = 1.0 - tcc
                #################################################

                df.loc[time_index, (city, 'tcc')] = tcc

    return df

def getWeatherType(df, parameter_names, match_timestamps, misc_path, acc_prec_column):
    '''Evaluating weather type'''

    light_clouds_thr  = 0.2
    partly_cloudy_thr = 0.4
    mostly_cloudy_thr = 0.6
    overcast_thr      = 0.9

    rain_thr          = 2.0
    heavy_rain_thr    = 10.0

    acc_time = acc_prec_column.split('_')[1]


    weather_type = 'NaN'
    if 'tcc' in df.columns.levels[1] and 'prec' in df.columns.levels[1]:
        for city in df.columns.levels[0]:
            for time_index in df.index:
                tcc = df.loc[time_index, (city, 'tcc')]
                prec = df.loc[time_index, (city, acc_prec_column)]
                
                if tcc >= overcast_thr:
                    print(city)
                    print('I am in the overcast')
                    print(tcc)
                    print(prec)
                    if prec == 0.0 or pd.isna(prec):
                        weather_type = 'overcast'
                        weather_symbol = misc_path + 'symbols/overcast.png'
                    elif prec > 0 and prec < rain_thr:
                        weather_type = 'light rain'
                        weather_symbol = misc_path + 'symbols/light_rain.png'
                    elif prec >= rain_thr and prec < heavy_rain_thr:
                        weather_type = 'rain'
                        weather_symbol = misc_path + 'symbols/rain.png'
                    elif prec >= heavy_rain_thr:
                        weather_type = 'heavy rain'
                        weather_symbol = misc_path + 'symbols/heavy_rain.png'
                
                elif tcc >= mostly_cloudy_thr and tcc < overcast_thr:
                    print('I am in the mostly cloudy')
                    print(tcc)
                    print(prec)
                    if prec == 0.0 or pd.isna(prec):
                        weather_type = 'mostly cloudy'
                        weather_symbol = misc_path + 'symbols/mostly_cloudy.png'
                    elif prec > 0 and prec < rain_thr:
                        weather_type = 'light shower'
                        weather_symbol = misc_path + 'symbols/light_shower.png'
                    elif prec >= rain_thr and prec < heavy_rain_thr:
                        weather_type = 'shower'
                        weather_symbol = misc_path + 'symbols/shower.png'
                    elif prec >= heavy_rain_thr:
                        weather_type = 'heavy shower'
                        weather_symbol = misc_path + 'symbols/heavy_shower.png'

                elif tcc >= partly_cloudy_thr and tcc < mostly_cloudy_thr:
                    print('I am in the partly cloudy')
                    print(tcc)
                    print(prec)
                    if prec == 0.0 or pd.isna(prec):
                        weather_type = 'partly cloudy'
                        weather_symbol = misc_path + 'symbols/partly_cloudy.png'
                    elif prec > 0 and prec < rain_thr:
                        weather_type = 'light shower'
                        weather_symbol = misc_path + 'symbols/light_shower.png'
                    elif prec >= rain_thr and prec < heavy_rain_thr:
                        weather_type = 'shower'
                        weather_symbol = misc_path + 'symbols/shower.png'
                    elif prec >= heavy_rain_thr:
                        weather_type = 'heavy shower'
                        weather_symbol = misc_path + 'symbols/heavy_shower.png'

                elif tcc >= light_clouds_thr and tcc < partly_cloudy_thr:
                    print('I am in the light clouds')
                    print(tcc)
                    print(prec)
                    if prec == 0.0 or pd.isna(prec):
                        weather_type = 'light clouds'
                        weather_symbol = misc_path + 'symbols/light_clouds.png'
                    elif prec > 0 and prec < rain_thr:
                        weather_type = 'light shower'
                        weather_symbol = misc_path + 'symbols/light_shower.png'
                    elif prec >= rain_thr and prec < heavy_rain_thr:
                        weather_type = 'shower'
                        weather_symbol = misc_path + 'symbols/shower.png'
                    elif prec >= heavy_rain_thr:
                        weather_type = 'heavy shower'
                        weather_symbol = misc_path + 'symbols/heavy_shower.png'

                elif tcc < light_clouds_thr and prec > 0:
                    # Looking for rain when there are no clouds
                    if prec > 0 and prec < rain_thr:
                        weather_type = 'light shower'
                        weather_symbol = misc_path + 'symbols/light_shower.png'
                    elif prec >= rain_thr and prec < heavy_rain_thr:
                        weather_type = 'shower'
                        weather_symbol = misc_path + 'symbols/shower.png'
                    elif prec >= heavy_rain_thr:
                        weather_type = 'heavy shower'
                        weather_symbol = misc_path + 'symbols/heavy_shower.png'
                else:
                    print('I am in the sun')
                    print(tcc)
                    print(prec)
                    weather_type = 'sunny'
                    weather_symbol = misc_path + 'symbols/sunny.png'

                df.loc[time_index, (city, 'weatherType'+acc_time)]   = weather_type
                df.loc[time_index, (city, 'weatherSymbol'+acc_time)] = weather_symbol

                # Resetting type and symbols to prevent accidental values from previous time step
                weather_type = 'NaN'
                weather_symbol = 'NaN'

    return df


def extract_temperature_mom_min_max(df, match_timestamps, window_len):

    min_column = 't_min'
    max_column = 't_max'

    for city in df.columns.levels[0]:

        df.loc[df.index.strftime('%H:%M').isin(match_timestamps), (city, min_column)] = pd.Series.rolling(df.loc[:, (city, 't')], window = f'{window_len}h').min()
        df.loc[df.index.strftime('%H:%M').isin(match_timestamps), (city, max_column)] = pd.Series.rolling(df.loc[:, (city, 't')], window = f'{window_len}h').max()
    df = df.loc[df.index.strftime('%H:%M').isin(match_timestamps)]

    return df
