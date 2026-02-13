import logging
import numpy as np
from grib_reader import gribEcCodes, reglambert

APP_NAME = 'grib_read'
logger = logging.getLogger("python-plotting-toolbox.{}".format(APP_NAME))


def main(fileName, parameter_names, wanted_parameters, grib_use_list, stations=None, nearest=True):
    """
    Read data from grib file and extract wanted parameters.

    Args:
        fileName (str): GRIB file path
        parameter_names (list): parameters to extract (e.g. ["t", "tp"])
        wanted_parameters (list): list passed to eccodes
        grib_use_list (list): GRIB file sequence
        stations (list): list of stations as [(lat, lon, id), ...]
        nearest (bool): whether to use nearest grid point (True)
                        or bilinear interpolation (False)

    Returns:
        lats, lons, data (full fields)
        station_data (dict) if stations provided
    """

    data, grid_type = gribEcCodes.getGribWithKeys(
        fileName,
        wanted=wanted_parameters,
        names=parameter_names,
        index_keys=["level","shortName"],
        debug=True,
        useStepRange=True,
        indexFile=False
    )

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
    else:  # regular_ll
        if data['LonFG'] == 180.0:
            data['LonFG'] = -180.0  # fix ECMWF convention
        lons, lats = gribEcCodes.get_grid(
            data['Ni'],
            data['Nj'],
            data['LatFG'],
            data['LatLG'],
            data['LonFG'],
            data['LonLG'],
            sydpol_lon=None,
            sydpol_lat=None)

    # Reshape variables to grid
    for param in parameter_names:
        try:
            if param == 't':  # Kelvin -> Celsius
                data[param] = data[param].reshape(np.shape(lats)) - 273.15
            else:
                data[param] = data[param].reshape(np.shape(lats))
        except KeyError:
            if fileName == grib_use_list[0]:
                logger.warning(f"*** KeyError: {param} not found in {fileName}, replacing with zeros")
                data[param] = np.zeros(np.shape(lats))
            else:
                logger.error(f"*** KeyError: {param} not found in {fileName}, replacing with zeros")
                data[param] = np.zeros(np.shape(lats))

    station_data = {}
    if stations:
        # Convert to numpy arrays for searching
        lats_arr = np.array(lats)
        lons_arr = np.array(lons)

        for (slat, slon, sid) in stations:
            # find nearest gridpoint
            dist = (lats_arr - slat)**2 + (lons_arr - slon)**2
            iy, ix = np.unravel_index(np.argmin(dist), dist.shape)

            station_data[sid] = {}
            for param in parameter_names:
                station_data[sid][param] = data[param][iy, ix]

    return lats, lons, data, station_data if stations else None
