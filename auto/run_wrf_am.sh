#!/bin/bash

# Set strict error handling
set -e

# Configurable variables
MAX_RETRIES=10                                           # Maximum number of retries
DELAY=60                                                 # Delay between retries in seconds
SCRIPT_NAME="auto_zimbabwe_local_am2.bash"               # Name of the script to execute
LOGFILE_DIR="/home/wrf/nons/auto/logs"                   # Log file directory
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")                   # Current date and time
LOGFILE="${LOGFILE_DIR}/auto_zimbabwe_${TIMESTAMP}.log"  # Log file with timestamp
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)  # Get directory of this script

# Create the logs directory if it doesn't exist
mkdir -p "$LOGFILE_DIR"

# Log the script directory and start the log file
echo "Script started at $(date)" | tee -a "$LOGFILE"
echo "Script directory: $SCRIPT_DIR" | tee -a "$LOGFILE"

# Start a `tail -f` in a new terminal window for real-time log viewing
if command -v xterm &>/dev/null; then
    xterm -e "tail -f $LOGFILE" &
elif command -v gnome-terminal &>/dev/null; then
    gnome-terminal -- tail -f "$LOGFILE" &
elif command -v konsole &>/dev/null; then
    konsole -e tail -f "$LOGFILE" &
elif command -v xfce4-terminal &>/dev/null; then
    xfce4-terminal --command "tail -f $LOGFILE" &
else
    echo "No suitable terminal emulator found. You can manually monitor the log with: tail -f \"$LOGFILE\""
fi

# Start the retry loop
for ((i=1; i<=MAX_RETRIES; i++)); do
    echo "Attempt $i of $MAX_RETRIES: Running $SCRIPT_NAME at $(date)..." | tee -a "$LOGFILE"

    # Record start time
    start_time=$(date +%s)

    # Run the target script
    if bash "$SCRIPT_DIR/$SCRIPT_NAME" >> "$LOGFILE" 2>&1; then
        echo "Success! $SCRIPT_NAME completed at $(date)." | tee -a "$LOGFILE"
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        printf "Time taken: %02d:%02d:%02d\n" $((duration/3600)) $((duration%3600/60)) $((duration%60)) | tee -a "$LOGFILE"
        exit 0  # Exit if the script runs successfully
    else
        echo "$SCRIPT_NAME failed at $(date). Retrying in $DELAY seconds..." | tee -a "$LOGFILE"
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        printf "Time taken: %02d:%02d:%02d\n" $((duration/3600)) $((duration%3600/60)) $((duration%60)) | tee -a "$LOGFILE"
        sleep $DELAY  # Wait before retrying
    fi
done

# If we reach here, all retries failed
echo "Max retries reached. $SCRIPT_NAME did not complete successfully." | tee -a "$LOGFILE"
exit 1
