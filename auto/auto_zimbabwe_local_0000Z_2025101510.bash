#!/home/wrf/deployed/nons_wrf_v4/nons_env/bin/bash
####################################################
### WRF AUTOMATION: GFS RETRIEVAL + PLOTTING + FTP
####################################################

set -e
set -o pipefail

# --- Trap keyboard interrupt ---
trap "echo 'Keyboard interruption detected'; exit 12" SIGINT

####################################################
### LOG FILE SETUP
####################################################
NOW=$(date +"%Y%m%d%H%M%S")
LOGFILE="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/logs/auto_production_$NOW.log"
exec > >(tee -a "$LOGFILE") 2>&1

START_TIME=$(date +%s)
echo "Script started at: $(date)"
echo "Log file: $LOGFILE"

####################################################
### DETERMINE CYCLE
####################################################
hour=$(date -u +"%H")
if [ "$hour" -lt 18 ]; then
    cycle="00"
else
    cycle="12"
fi
FOLDER_NAME=$(date -u +"%Y_%m_%d_%H_%M_${cycle}Z")
echo "Cycle: $cycle | Folder: $FOLDER_NAME"

####################################################
### CLEAN OLD LOGS
####################################################
find /home/wrf/deployed/nons_wrf_v4/gfs-retrieval/logs -name "*.log" -type f -mtime +1 -delete
echo "Old log files cleaned."

####################################################
### DATE VARIABLES
####################################################
DATEGRIB="$(date -u +"%y%m%d${cycle}00")"
START_DATE="$(date -u +"%Y%m%d")"
END_DATE="$(date -u +"%Y%m%d" -d "+16 days")"
echo "Production period: $START_DATE to $END_DATE"
echo "Date for GFS retrieval: $DATEGRIB"

####################################################
### ACTIVATE NONS_ENV
####################################################
if [ -f "/home/wrf/deployed/nons_wrf_v4/nons_env/bin/activate" ]; then
    source /home/wrf/deployed/nons_wrf_v4/nons_env/bin/activate
    echo "✅ Correct virtual environment activated."
else
    echo "❌ Error: Could not find nons_env virtual environment."
    exit 11
fi

####################################################
### RETRIEVE GFS DATA IF MISSING
####################################################
STAMP_FILE="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/.downloaded_$DATEGRIB"
LOCAL_OUTDATA="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/local_outdata"
mkdir -p "$LOCAL_OUTDATA"

ALL_PRESENT=true
for i in $(seq -w 0 384); do
    FILE="${LOCAL_OUTDATA}/${DATEGRIB}_gfs_global.grb2f${i}0000"
    if [ ! -f "$FILE" ]; then
        ALL_PRESENT=false
        break
    fi
done

if $ALL_PRESENT && [ -f "$STAMP_FILE" ]; then
    echo "✅ All GFS files for $DATEGRIB already downloaded. Skipping download."
else
    echo "⏳ Missing or incomplete files detected. Starting new download..."
    rm -rf "${LOCAL_OUTDATA:?}"/*
    cd /home/wrf/deployed/nons_wrf_v4/gfs-retrieval/ || { echo "❌ Failed to enter GFS retrieval directory"; exit 11; }

    if [ "$cycle" == "00" ]; then
        python retrieve_gfs_data_0000Z.py || { echo "❌ Error: Failed to retrieve 0000Z GFS data"; exit 10; }
    elif [ "$cycle" == "12" ]; then
        python retrieve_gfs_data_1200Z.py || { echo "❌ Error: Failed to retrieve 1200Z GFS data"; exit 10; }
    fi
    touch "$STAMP_FILE"
    echo "✅ GFS data downloaded and stamp file created."
fi

####################################################
### COPY GFS DATA TO AUTO/INDATA
####################################################
rm -rf /home/wrf/deployed/nons_wrf_v4/auto/indata/*
cp -r "$LOCAL_OUTDATA"/* /home/wrf/deployed/nons_wrf_v4/auto/indata/
echo "Copied GFS data to auto/indata."

####################################################
### PLOTTING
####################################################
cd /home/wrf/deployed/nons_wrf_v4/python-plotting-toolbox/ || { echo "Error: Failed to enter plotting directory"; exit 11; }
python plot_runner.py || { echo "❌ Plotting failed"; exit 1; }
echo "Plotting completed successfully."

####################################################
### EXTRACTION
####################################################
python extract_runner.py || { echo "❌ Extraction failed"; exit 1; }
echo "Extraction completed successfully."

####################################################
### COPY PRODUCTS TO FTP
####################################################
FTP_DIR="/data/ftp/${FOLDER_NAME}/zim"
mkdir -p "$FTP_DIR"
echo "FTP upload directory: $FTP_DIR"

PRODUCTS=(acc_precip cloudcover meteograms tephigrams extract_acc_precip extract_temperature symbograms)
for PRODUCT in "${PRODUCTS[@]}"; do
    SRC_DIR="/home/wrf/deployed/nons_wrf_v4/python-plotting-toolbox/local_outdata/$PRODUCT"
    if [ -d "$SRC_DIR" ]; then
        cp -R "$SRC_DIR" "$FTP_DIR/"
        echo "Copied $PRODUCT to FTP directory."
    else
        echo "⚠️ Directory $SRC_DIR does not exist."
    fi
done

####################################################
### TRANSFER TO REMOTE FTP (blocking, robust)
####################################################
HOST="192.168.0.116"
USER="testftp"
PASS="ftp_user2025"
REMOTE_PARENT="/local_wrf"
REMOTE_FOLDER="${REMOTE_PARENT}/${FOLDER_NAME}"

# Check if remote folder exists
if lftp -u "$USER","$PASS" "$HOST" -e "
set ftp:ssl-allow no
set net:timeout 10
set net:max-retries 1
cls -1 $REMOTE_PARENT
bye
" 2>/dev/null | grep -q "$FOLDER_NAME"; then
    echo "❌ Remote folder $REMOTE_FOLDER exists. Skipping upload."
else
    echo "✅ Folder not found. Uploading..."
    lftp -u "$USER","$PASS" "$HOST" -e "
set ftp:ssl-allow no
set net:timeout 15
set net:max-retries 2
mirror -R '$FTP_DIR' '$REMOTE_FOLDER'
bye
" || { echo "❌ FTP upload failed"; exit 1; }
    echo "✅ FTP upload complete."
fi

####################################################
### CLEANUP: KILL LEFTOVER PROCESSES
####################################################
echo "🔍 Checking for leftover processes..."
RUN_KEYWORDS=("retrieve_gfs_data" "plot_runner.py" "extract_runner.py" "lftp")

for keyword in "${RUN_KEYWORDS[@]}"; do
    PIDS=$(pgrep -f "$keyword" || true)
    if [ -n "$PIDS" ]; then
        echo "🧹 Killing processes for: $keyword ($PIDS)"
        kill -9 $PIDS 2>/dev/null || true
    fi
done
echo "✅ All related processes cleaned up."

####################################################
### END
####################################################
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "Script completed at: $(date)"
echo "Total runtime: ${DURATION}s"
exit 0
