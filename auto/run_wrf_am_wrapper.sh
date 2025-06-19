#!/bin/bash

set -e

# Environment setup for cron
export HOME="/home/wrf"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Configurable variables
MAX_RETRIES=3
DELAY=60
SCRIPT_NAME="auto_zimbabwe_local_am2.bash"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
TIMESTAMP=$(date +%Y%m%d%H%M)
LOGFILE="$HOME/nons/gfs-retrieval/logs/zimbabwe_${TIMESTAMP}.log"
LOGFILE_DIR="/home/wrf/nons/auto/logs"
EMAIL_TO="wilfred.chawaguta@gmail.com babamaketa@gmail.com"
HOSTNAME=$(hostname)
SUBJECT_PREFIX="[WRF Wrapper]"

mkdir -p "$LOGFILE_DIR"

SHOULD_CLEANUP=true

send_email() {
    SUBJECT="$1"
    BODY="$2"
    echo -e "$BODY\n\nHost: $HOSTNAME\nTime: $(date)\nLog: $LOGFILE" | mail -s "$SUBJECT_PREFIX $SUBJECT" "$EMAIL_TO"
}

cleanup() {
    if [[ $SHOULD_CLEANUP == true ]]; then
        echo "Cleaning up... Killing all lingering run_wrf processes." | tee -a "$LOGFILE"
        pkill -f run_wrf || echo "No run_wrf processes found to kill." | tee -a "$LOGFILE"
        send_email "WRF Process Cleanup" "The wrapper script failed or exited abnormally.\nAll lingering run_wrf processes were killed."
    else
        echo "No cleanup needed — script completed successfully." | tee -a "$LOGFILE"
    fi
}
trap cleanup EXIT

echo "Script started at $(date)" | tee -a "$LOGFILE"
echo "Script directory: $SCRIPT_DIR" | tee -a "$LOGFILE"

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
        echo "No suitable terminal emulator found." | tee -a "$LOGFILE"
    fi
else
    echo "No GUI available — skipping tail terminal." | tee -a "$LOGFILE"
fi

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
        formatted_time=$(printf "%02d:%02d:%02d" $((duration/3600)) $((duration%3600/60)) $((duration%60)))
        echo "Time taken: $formatted_time" | tee -a "$LOGFILE"
        send_email "Run Successful" "The wrapper script completed successfully in $formatted_time."
        exit 0

    elif [[ $status -eq 42 ]]; then
        echo "GFS retrieval failed (exit code 42) at $(date). Retrying in $DELAY seconds..." | tee -a "$LOGFILE"
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        formatted_time=$(printf "%02d:%02d:%02d" $((duration/3600)) $((duration%3600/60)) $((duration%60)))
        echo "Time taken: $formatted_time" | tee -a "$LOGFILE"
        sleep $DELAY
    else
        echo "Script failed (exit code $status), not retryable. Continuing with FTP/product steps..." | tee -a "$LOGFILE"
        send_email "Run Failed (non-GFS issue)" "Script $SCRIPT_NAME failed with exit code $status on attempt $i.\nLog file: $LOGFILE"
        break
    fi
done

echo "Max retries reached. $SCRIPT_NAME did not complete successfully." | tee -a "$LOGFILE"
send_email "Max Retries Exceeded" "GFS retrieval failed after $MAX_RETRIES attempts.\nScript exited with failure.\nLog file: $LOGFILE"
exit 1
