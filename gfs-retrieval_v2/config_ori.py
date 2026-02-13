import logging
import os
import json
import ast

logger = logging.getLogger('carl-gfs-data-retrieval.config')

# Load config.json unless a local config.local.json exist.
# We will combine the configuration in "common" and the SMHI-mode,
# For example for test, we will combine "common" with "test" from the json file.
with open('./config.json', 'r') as f:
    config_json = json.load(f)
    print("Loaded config_json:", config_json)
    CONFIG = config_json#["common"]



DOMAIN_URL = CONFIG["common"]["domainURL"]
OUTDATA_PATH = CONFIG["common"]["outdataPath"]
FILE_SUFFIX = CONFIG["common"]["fileSuffix"]
MAX_FORECAST_LENGTH = CONFIG["common"]["maxForecastLength"]
