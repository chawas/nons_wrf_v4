#!/bin/bash

# Set strict error handling
set -e

# Configurable variables
MAX_RETRIES=100            # Maximum number of retries
DELAY=60                   # Delay between retries in seconds
SCRIPT_NAME="auto_zimbabwe_local_pm.bash"  # Name of the script to execute
LOGFILE="/home/wrf/deployed/logs/auto_zimbabwe.log"  # Log file path
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)  # Get directory of this script

# Create the logs directory if it doesn't exist
mkdir -p "$(dirname "$LOGFILE")"

# Start the retry loop
for ((i=1; i<=MAX_RETRIES; i++)); do
    echo "Attempt $i of $MAX_RETRIES: Running $SCRIPT_NAME..." | tee -a "$LOGFILE"

    # Run the target script
    if bash "$SCRIPT_DIR/$SCRIPT_NAME" >> "$LOGFILE" 2>&1; then
        echo "Success! $SCRIPT_NAME completed." | tee -a "$LOGFILE"
        exit 0  # Exit if the script runs successfully
    else
        echo "$SCRIPT_NAME failed. Retrying in $DELAY seconds..." | tee -a "$LOGFILE"
        sleep $DELAY  # Wait before retrying
    fi
done

# If we reach here, all retries failed
echo "Max retries reached. $SCRIPT_NAME did not complete successfully." | tee -a "$LOGFILE"
exit 1
