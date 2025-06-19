#!/bin/bash

# Set strict error handling
set -e

# Environment setup for cron
export HOME="/home/wrf"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Configurable variables
MAX_RETRIES=3
DELAY=60
SCRIPT_NAME="auto_zimbabwe_local_am2.bash"
LOGFILE_DIR="/home/wrf/nons/auto/logs"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

TIMESTAMP=$(date +%Y%m%d%H%M)
LOGFILE="$HOME/nons/gfs-retrieval/logs/zimbabwe_${TIMESTAMP}.log"

# Create the logs directory if it doesn't exist
mkdir -p "$LOGFILE_DIR"

# Track whether cleanup should run
SHOULD_CLEANUP=true

# Cleanup function
cleanup() {
    if [[ $SHOULD_CLEANUP == true ]]; then
        echo "Cleaning up... Killing all lingering run_wrf processes." | tee -a "$LOGFILE"
        pkill -f run_wrf || echo "No run_wrf processes found to kill." | tee -a "$LOGFILE"
    else
        echo "No cleanup needed — script completed successfully." | tee -a "$LOGFILE"
    fi
}
trap cleanup EXIT

# Start the log
echo "Script started at $(date)" | tee -a "$LOGFILE"
echo "Script directory: $SCRIPT_DIR" | tee -a "$LOGFILE"

# Launch tail -f in GUI terminal (only if running in a graphical session)
if [[ -n "$DISPLAY" ]]; then
    if command -v xterm &>/dev/null; then
        xterm -e "tail -f $LOGFILE" &
    elif command -v gnome-terminal &>/dev/null; then
        gnome-terminal -- tail -f "$LOGFILE" &
    elif command -v konsole &>/dev/null; then
        konsole -e tail -f "$LOGFILE" &
    elif command -v xfce4-terminal &>/dev/null; then
        xfce4-terminal --command "tail -f $LOGFILE" &
    else
        echo "No suitable terminal emulator found. You can manually monitor the log with: tail -f \"$LOGFILE\"" | tee -a "$LOGFILE"
    fi
else
    echo "No GUI available (likely running from cron). Skipping terminal tail." | tee -a "$LOGFILE"
fi

# Retry loop
for ((i=1; i<=MAX_RETRIES; i++)); do
    echo "Attempt $i of $MAX_RETRIES: Running $SCRIPT_NAME at $(date)..." | tee -a "$LOGFILE"
    start_time=$(date +%s)

    bash "$SCRIPT_DIR/$SCRIPT_NAME" >> "$LOGFILE" 2>&1
    status=$?

    if [[ $status -eq 0 ]]; then
        SHOULD_CLEANUP=false
        echo "Success! $SCRIPT_NAME completed at $(date)." | tee -a "$LOGFILE"
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        printf "Time taken: %02d:%02d:%02d\n" $((duration/3600)) $((duration%3600/60)) $((duration%60)) | tee -a "$LOGFILE"
        exit 0

    elif [[ $status -eq 42 ]]; then
        echo "GFS retrieval failed (exit code 42) at $(date). Retrying in $DELAY seconds..." | tee -a "$LOGFILE"
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        printf "Time taken: %02d:%02d:%02d\n" $((duration/3600)) $((duration%3600/60)) $((duration%60)) | tee -a "$LOGFILE"
        sleep $DELAY
    else
        echo "Script failed, but not due to GFS network issue. Continuing with FTP and product generation..." | tee -a "$LOGFILE"
        break
    fi
done

# Final failure
echo "Max retries reached or script ended with non-retryable error." | tee -a "$LOGFILE"
exit 1
