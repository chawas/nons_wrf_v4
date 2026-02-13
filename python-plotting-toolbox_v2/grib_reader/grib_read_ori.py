import logging
import numpy as np
from grib_reader import gribEcCodes, reglambert

APP_NAME = 'grib_read'
logger = logging.getLogger("python-plotting-toolbox.{}".format(APP_NAME))


def main(fileName, parameter_names, wanted_parameters, grib_use_list):

    '''Read data from grib file and extract wanted parameters'''

    data, grid_type = gribEcCodes.getGribWithKeys(fileName, wanted = wanted_parameters, names = parameter_names, index_keys = ["level","shortName"], debug=True, useStepRange=True, indexFile=False)
    if grid_type == 'lambert':
        lons, lats = reglambert.lambertGrid(
            data['LatFG'],
            data['LonFG'],
            data['Ni'],
            data['Nj'],
            data['LoVInDegrees'],
            data['DxInMetres'],
            data['DyInMetres'],
            data['Latin1InDegrees'],
            data['Latin2InDegrees'],
            gridInLatlon=True)
    else:#if grid_type == 'regular_ll':
        if data['LonFG'] == 180.0: data['LonFG'] = -180.0  # In order to compensate for 180 to 180 setup in ECMWF data
        lons, lats = gribEcCodes.get_grid(
            data['Ni'],
            data['Nj'],
            data['LatFG'],
            data['LatLG'],
            data['LonFG'],
            data['LonLG'],
            sydpol_lon = None,
            sydpol_lat = None)

    for param in parameter_names:
        try:
            if param == 't': #This is too hardcoded!!! But the intention is to convert Kelvin to Celcius
                data[param] = data[param].reshape(np.shape(lats)) - 273.15 # Reshape field to fit coordinates field and subtract 273.15
            else:
                data[param] = data[param].reshape(np.shape(lats)) # Reshape field to fit coordinates field 

        except KeyError:
            '''
            This handles a KeyError that might arise when taking the first model timestep (f000000) and asking for precipitation.
            Precipitation is generally missing from the first model time step

            If the KeyError arises also on other time steps, you might want to check your parameter request at the top of the script
            '''

            if fileName == grib_use_list[0]:

                logger.warning('*** KeyError: (but don\'t worry)')
                logger.warning('    The requested parameter \'' + param + '\' does not appear to be in the the file ' + fileName)
                logger.warning('    This might be that \'' + param + '\' is a precipitation parameter and that this file is the first time step.')
                logger.warning('    Time step 00 in a forecast run typically lacks precipitation data.')
                logger.warning('')
                logger.warning('->  Replacing with zeros...')
                logger.warning('')

                data[param] = np.zeros(np.shape(lats)) # Make an array of zeros for the missing data

            else:

                logger.error('*** KeyError: Maybe you should worry ******************************')
                logger.error('    The requested parameter \'' + param + '\' does not appear to be in the the file ' + fileName + ' either...')
                logger.error('    You might want to check your parameter request')
                logger.error('')
                logger.error('->  Replacing with zeros...')

                data[param] = np.zeros(np.shape(lats)) # Make an array of zeros for the missing data
   
    return lats, lons, data