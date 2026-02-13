import json
import os

# Always resolve relative to this file's directory
config_path = os.path.join(os.path.dirname(__file__), 'config.json')

print("DEBUG: config_path =", config_path)
with open(config_path, 'r') as f:
    config_json = json.load(f)

print("DEBUG: Loaded config_json =", config_json)

if "common" not in config_json:
    raise KeyError(f"'common' key not found in {config_path}")

CONFIG = config_json["common"]
DOMAIN_URL = CONFIG["domainURL"]
OUTDATA_PATH = CONFIG["outdataPath"]
FILE_SUFFIX = CONFIG["fileSuffix"]
MAX_FORECAST_LENGTH = CONFIG["maxForecastLength"]
