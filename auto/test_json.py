import json
import os

# Get the absolute path of the current script
script_dir = os.path.dirname(os.path.realpath(__file__))

# Construct the full path to the config.json
config_file_path = os.path.join(script_dir, 'config3.json')

# Load the config.json file
try:
    with open(config_file_path, 'r') as file:
        config = json.load(file)

    # Access general settings
    log_directory = config['nons']['log_directory']

    # Access project-specific settings
    project1_source_directory = config['nons']['source_directory']

    # Example usage
    print(f"Log Directory: {log_directory}")
    print(f"nons Source Directory: {project1_source_directory}")

except FileNotFoundError:
    print(f"Error: The file '{config_file_path}' was not found.")
except json.JSONDecodeError:
    print(f"Error: There was an issue decoding the JSON file.")
except KeyError as e:
    print(f"Error: The key {str(e)} was not found in the config file.")
