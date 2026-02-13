import logging
import numpy as np
from grib_reader import gribEcCodes, reglambert

APP_NAME = 'grib_read'
logger = logging.getLogger(f"python-plotting-toolbox.{APP_NAME}")


def _fix_lonfg(data):
    """
    Ensures that LonFG exists for GFS/ECMWF GRIB files.

    ECMWF sometimes provides LonFG = 180 → use -180.
    GFS GRIB2 usually does NOT provide LonFG → we derive it from standard GRIB keys.
    """

    lonfg = data.get('LonFG')

    # Case 1: ECMWF style: LonFG exists
    if lonfg is not None:
        if lonfg == 180.0:
            data['LonFG'] = -180.0
        return

    # Case 2: GFS style: derive LonFG from GRIB2 metadata
    logger.debug("🟡 LonFG missing — deriving from GRIB2 longitude keys (GFS-style grid).")

    lon_first = data.get('longitudeOfFirstGridPointInDegrees')
    lon_last = data.get('longitudeOfLastGridPointInDegrees')

    if lon_first is None or lon_last is None:
        logger.error("❌ Neither LonFG nor GRIB2 longitude fields found in GRIB file.")
        raise KeyError("LonFG and GRIB2 longitude keys missing")

    # Use first longitude as the grid origin
    data['LonFG'] = lon_first
    data['LonLG'] = lon_last

    logger.debug(f"Derived LonFG={lon_first}, LonLG={lon_last}")


def main(fileName, parameter_names, wanted_parameters, grib_use_list):
    """Read data from a GRIB file and extract requested parameters."""

    data, grid_type = gribEcCodes.getGribWithKeys(
        fileName,
        wanted=wanted_parameters,
        names=parameter_names,
        index_keys=["level", "shortName"],
        debug=True,
        useStepRange=True,
        indexFile=False
    )

    # --- NEW: fix LonFG safely for GFS/ECMWF
    _fix_lonfg(data)

    # ==============================================================
    #      GRID HANDLING
    # ==============================================================

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
            gridInLatlon=True
        )

    else:  # regular_ll grid (GFS / ECMWF global)
        lons, lats = gribEcCodes.get_grid(
            data['Ni'],
            data['Nj'],
            data['LatFG'],
            data['LatLG'],
            data['LonFG'],
            data['LonLG'],
            sydpol_lon=None,
            sydpol_lat=None
        )

    # ==============================================================
    #      PARAMETER EXTRACTION AND RESHAPING
    # ==============================================================

    for param in parameter_names:
        try:
            if param == 't':  # Temperature in Kelvin → Celsius
                data[param] = data[param].reshape(np.shape(lats)) - 273.15
            else:
                data[param] = data[param].reshape(np.shape(lats))

        except KeyError:
            # Missing parameter (common for precip at timestep 0)
            first_file = (fileName == grib_use_list[0])

            if first_file:
                logger.warning(f"Parameter '{param}' missing in first timestep {fileName}. Replacing with zeros.")
            else:
                logger.error(f"Parameter '{param}' missing in {fileName}. Replacing with zeros.")

            data[param] = np.zeros(np.shape(lats))

    return lats, lons, data
