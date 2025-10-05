#!/bin/bash
####################################################
### EXIT ON FAILURE
####################################################

set -e  # Exit if any command fails
set -o pipefail  # Exit if any part of a pipeline fails

#python3 /path/to/download_script.py

####################################################
### SET UP LOG FILE WITH TIMESTAMP
####################################################
NOW=$(date +"%Y%m%d%H%M%S")
LOGFILE="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/logs/auto_production_$NOW.log"
exec > >(tee -a "$LOGFILE") 2>&1

# Start time
START_TIME=$(date +%s)
echo "Script started at: $(date)"
echo "Log file: $LOGFILE"


#!/bin/bash

# Get current hour in UTC
hour=$(date -u +"%H")

# Decide cycle (00Z or 12Z)
if [ "$hour" -lt 18 ]; then
    cycle="00"
else
    cycle="12"
fi

# Build folder name with underscores
FOLDER_NAME=$(date -u +"%Y_%m_%d_%H_%M_${cycle}Z")

echo "Folder: $FOLDER_NAME"


####################################################
### CLEAN OLD LOG FILES
####################################################
find /home/wrf/deployed/nons_wrf_v4/gfs-retrieval/logs/ -name "*.log" -type f -mtime +1 -delete
echo "Old log files cleaned."

####################################################
### DATE VARIABLES
####################################################
DATEGRIB="$(date +"%y%m%d0000")"
START_DATE="$(date +"%Y%m%d")"
END_DATE="$(date +"%Y%m%d" -d "+16 days")"
echo "Production started: $START_DATE to $END_DATE"
echo "Date for GFS retrieval: $DATEGRIB"

####################################################
### RETRIEVE GFS DATA
####################################################
echo "Retrieving GFS data..."
cd /home/wrf/deployed/nons_wrf_v4/gfs-retrieval/ || { echo "Error: Failed to enter GFS retrieval directory"; exit 1; }
echo "Current directory: $PWD"

# Activate environment and clean local_outdata
source venv/bin/activate
echo "Virtual environment activated."
#rm -rf /home/wrf/deployed/nons_wrf_v4/gfs-retrieval/local_outdata/*
echo "Deleted data from local_outdata."

# Download GFS data
if [ "$cycle" == "00" ]; then
    echo "➡️ Running 0000Z GFS data retrieval..."
    python3 retrieve_gfs_data_0000Z.py || { echo "❌ Error: Failed to retrieve 0000Z GFS data"; exit 1; }
elif [ "$cycle" == "12" ]; then
    echo "➡️ Running 1200Z GFS data retrieval..."
    python3 retrieve_gfs_data_1200Z.py || { echo "❌ Error: Failed to retrieve 1200Z GFS data"; exit 1; }
else
    echo "❌ Invalid cycle argument: $cycle (must be 00 or 12)"
    exit 1
fi
echo "GFS data retrieved successfully."
deactivate

####################################################
### COPY GFS DATA TO AUTO/INDATA
####################################################
rm -rf /home/wrf/nons_wrf_v4/auto/indata/*
echo "Deleted data from auto/indata."
cp -r /home/wrf/deployed/nons_wrf_v4/gfs-retrieval/local_outdata/* /home/wrf/deployed/nons_wrf_v4/auto/indata/
echo "Copied GFS data to auto/indata."

####################################################
### PLOTTING
####################################################
echo "Starting plotting..."
cd /home/wrf/deployed/nons_wrf_v4/python-plotting-toolbox/ || { echo "Error: Failed to enter plotting directory"; exit 1; }
source venv/bin/activate
python3 plot_runner.py || { echo "Error: Failed to run plot_runner.py"; exit 1; }
echo "Plotting completed successfully."


####################################################
### EXTRACTING
####################################################
echo "Starting extraction..."
python3 extract_runner.py || { echo "Error: Failed to run extract_runner.py"; exit 1; }
echo "Extraction completed successfully."
deactivate
####################################################
### COPY PRODUCTS TO FTP
####################################################
#FTP_DIR="/data/ftp/$(date +"%Y_%m_%d_%H_%M")/zim"
FTP_DIR="/data/ftp/${FOLDER_NAME}/zim"
mkdir -p "$FTP_DIR"
echo "FTP upload directory: $FTP_DIR"

# Copy product directories
PRODUCTS=(acc_precip cloudcover meteograms tephigrams extract_acc_precip extract_temperature symbograms)
for PRODUCT in "${PRODUCTS[@]}"; do
    SRC_DIR="/home/wrf/deployed/nons_wrf_v4/python-plotting-toolbox/local_outdata/$PRODUCT"
    if [ -d "$SRC_DIR" ]; then
        cp -R "$SRC_DIR" "$FTP_DIR/"
        echo "Copied $PRODUCT to FTP directory."
    else
        echo "Warning: Directory $SRC_DIR does not exist."
    fi
done

####################################################
### HANDLE WX PRESENTATION IMAGES
####################################################
WX_DIR="/home/wrf/deployed/chawas_03/wx_presentation/images"
if [ -d "$WX_DIR" ]; then
    cp -R /home/wrf/deployed/chawas_03/wx_presentation/ "$FTP_DIR/presentation"
    echo "Copied wx presentation images to FTP directory."
else
    echo "Warning: WX presentation images directory $WX_DIR does not exist."
fi

####################################################
### HANDLE SOUTHERN AFRICA AND ZIMBABWE GRADS OUTPUTS
####################################################
check_and_copy() {
    SRC_DIR="$1"
    DEST_DIR="$2"
    MESSAGE="$3"

    if [ -d "$SRC_DIR" ]; then
        mkdir -p "$DEST_DIR"
        cp -R "$SRC_DIR" "$DEST_DIR"
        echo "$MESSAGE"
    else
        echo "Warning: $SRC_DIR does not exist."
    fi
}

check_and_copy "/data/uems/runs/southern_africa/emsprd/grads/d02htm" "$FTP_DIR/" "Copied d02htm for Southern Africa."
check_and_copy "/data/uems/runs/southern_africa/emsprd/grads/d01htm" "$FTP_DIR/" "Copied d01htm for Southern Africa."
check_and_copy "/data/uems/runs/zimbabwe/emsprd/grads/d01htm" "$FTP_DIR/" "Copied d01htm for Zimbabwe."

####################################################
### FINISHING UP
####################################################
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "Script completed at: $(date)"
echo "Total duration: $((DURATION / 60)) minutes and $((DURATION % 60)) seconds."
echo "FINITO TODAY'S PRODUCTION !!!"


####################################################
### TRANSFER TO FTP SITE
####################################################
# FTP Credentials
HOST="192.168.0.116"
USER="testftp"
PASS="ftp_user2025"

# Time-based folder name
#NOW=$(date +"%Y%m%d")
#HOUR="00"
#FOLDER_NAME="${NOW}${HOUR}"
LOCAL_FOLDER="/data/ftp/${FOLDER_NAME}"
REMOTE_PARENT="/local_wrf"
REMOTE_FOLDER="${REMOTE_PARENT}/${FOLDER_NAME}"

# Show folders
echo "FOLDER_NAME: $FOLDER_NAME"
echo "Local folder: $LOCAL_FOLDER"
echo "Remote folder: $REMOTE_FOLDER"
echo "Uploading to remote folder: $REMOTE_FOLDER on FTP server $HOST"

# Check if remote folder already exists
echo "Checking if $REMOTE_FOLDER already exists on remote..."

if lftp -u "$USER","$PASS" $HOST <<EOF | grep -q "$FOLDERNAME}"
set ftp:ssl-allow no
cls -1 $REMOTE_PARENT
bye
EOF
then
    echo "❌ Remote folder $REMOTE_FOLDER already exists. Skipping upload."
    exit 0
else
    echo "✅ Folder not found. Proceeding with upload..."
fi

# Upload using lftp
lftp -u "$USER","$PASS" $HOST <<EOF
set ftp:ssl-allow no
mirror -R "$LOCAL_FOLDER" "$REMOTE_FOLDER"
bye
EOF
echo "FINITO TODAY'S TRANSFER !!!"
