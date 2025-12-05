#!/home/wrf/deployed/nons_wrf_v4/nons_env/bin/bash
###############################################################
###  WRF AUTOMATION PIPELINE
###  MODULES: GFS Retrieval → Plotting → Extraction → FTP Upload
###  Version: 2025-10
###  Exit codes:
###    0 = Success
###   10 = GFS retrieval failure
###   11 = Missing dependency or path
###   12 = Manual keyboard interrupt
###   13 = FTP upload skipped or failed
###    1 = Plotting/Extraction failure
###############################################################

set -e
set -o pipefail
trap "echo 'Keyboard interruption detected'; exit 12" SIGINT

###############################################################
### LOG FILE SETUP
###############################################################
NOW=$(date +"%Y%m%d%H%M%S")
LOGFILE="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/logs/auto_production_$NOW.log"
exec > >(tee -a "$LOGFILE") 2>&1

START_TIME=$(date +%s)
echo "🚀 Script started at: $(date -u)"
echo "📘 Log file: $LOGFILE"

###############################################################
### DETERMINE CYCLE
###############################################################
if [ -n "$WRF_CYCLE" ]; then
    cycle="$WRF_CYCLE"
else
    hour=$(date -u +"%H")
    if [ "$hour" -lt 12 ]; then
        cycle="00"
    else
        cycle="12"
    fi
fi
echo "🕐 Cycle: $cycle"

###############################################################
### CLEAN OLD LOGS
###############################################################
find /home/wrf/deployed/nons_wrf_v4/gfs-retrieval/logs -name "*.log" -type f -mtime +1 -delete
echo "🧹 Old log files cleaned."

###############################################################
### DATE VARIABLES
###############################################################
DATEGRIB="$(date -u +"%y%m%d${cycle}00")"
TODAY=$(date -u +"%Y%m%d")
STAMP_FILE="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/.downloaded_$DATEGRIB"
LOCAL_OUTDATA="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/local_outdata"
echo "📅 GFS retrieval tag: $DATEGRIB"

###############################################################
### ACTIVATE ENVIRONMENT
###############################################################
if [ -f "/home/wrf/deployed/nons_wrf_v4/nons_env/bin/activate" ]; then
    source /home/wrf/deployed/nons_wrf_v4/nons_env/bin/activate
    echo "✅ Python environment activated."
else
    echo "❌ Could not find nons_env virtual environment."
    exit 11
fi

###############################################################
### VERIFY LOCAL_OUTDATA & CHECK FOR TODAY'S DATA
###############################################################
LOCAL_OUTDATA="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/local_outdata"

# Ensure folder exists (only if truly missing)
if [ ! -d "$LOCAL_OUTDATA" ]; then
    echo "⚠️ LOCAL_OUTDATA missing. Recreating..."
    mkdir -p "$LOCAL_OUTDATA"
else
    echo "🔎 LOCAL_OUTDATA exists: $LOCAL_OUTDATA"
fi

ALL_PRESENT=true
MIN_SIZE=50000   # 50 KB minimum
echo "🔍 Verifying today's GFS files for $DATEGRIB..."

# Check files inside LOCAL_OUTDATA
for i in $(seq -w 0 384); do
    FILE="${LOCAL_OUTDATA}/${DATEGRIB}_gfs_global.grb2f${i}0000"
    if [ ! -s "$FILE" ] || [ "$(stat -c%s "$FILE" 2>/dev/null || echo 0)" -lt "$MIN_SIZE" ]; then
        ALL_PRESENT=false
        break
    fi
done

# Decide whether to skip or download
if $ALL_PRESENT && [ -f "$STAMP_FILE" ]; then
    echo "✅ All GFS files verified and stamp exists. Skipping download."
else
    echo "⏳ Missing/invalid GFS files detected."

    # Clean only the data files, not the directory
    echo "🧹 Deleting old GFS data files..."
    find "$LOCAL_OUTDATA" -type f -name "*.grb2" -delete

    # Start download
    echo "🚀 Starting GFS data retrieval..."
    cd /home/wrf/deployed/nons_wrf_v4/gfs-retrieval/ || { echo "❌ Retrieval directory missing"; exit 11; }

    if [ "$cycle" = "00" ]; then
        python retrieve_gfs_data_0000Z.py || { echo "❌ retrieve_gfs_data_0000Z failed"; exit 10; }
    else
        python retrieve_gfs_data_1200Z.py || { echo "❌ retrieve_gfs_data_1200Z failed"; exit 10; }
    fi

    # Re-verify downloaded files
    echo "🔁 Re-verifying downloaded files..."
    VERIFY_PASS=true
    for i in $(seq -w 0 384); do
        FILE="${LOCAL_OUTDATA}/${DATEGRIB}_gfs_global.grb2f${i}0000"
        SIZE=$(stat -c%s "$FILE" 2>/dev/null || echo 0)
        if [ ! -f "$FILE" ]; then
            echo "❌ Missing: $(basename "$FILE")"
            VERIFY_PASS=false
            break
        elif [ "$SIZE" -lt "$MIN_SIZE" ]; then
            echo "❌ File too small: $(basename "$FILE") ($SIZE bytes)"
            VERIFY_PASS=false
            break
        fi
    done

    if $VERIFY_PASS; then
        echo "✅ Download verified. Creating stamp: $STAMP_FILE"
        touch "$STAMP_FILE"
    else
        echo "❌ Download verification failed. Exiting."
        exit 10
    fi
fi

# Ensure subdirectories exist for products
for subdir in 1 12 24 10_day; do
    [ ! -d "$LOCAL_OUTDATA/$subdir" ] && mkdir -p "$LOCAL_OUTDATA/$subdir"
done

###############################################################
### COPY GFS DATA TO AUTO/INDATA
###############################################################
rm -rf /home/wrf/deployed/nons_wrf_v4/auto/indata/*
cp -r "$LOCAL_OUTDATA"/* /home/wrf/deployed/nons_wrf_v4/auto/indata/
echo "📂 Copied GFS data to auto/indata."

###############################################################
### PLOTTING + EXTRACTION
###############################################################
cd /home/wrf/deployed/nons_wrf_v4/python-plotting-toolbox/ || { echo "❌ Plotting directory missing"; exit 11; }

python plot_runner.py || { echo "❌ Plotting failed"; exit 1; }
echo "✅ Plotting completed."

python extract_runner.py || { echo "❌ Extraction failed"; exit 1; }
echo "✅ Extraction completed successfully."

###############################################################
### CREATE LOCAL FTP PRODUCT STRUCTURE
###############################################################
FOLDER_NAME="$(date -u +'%Y_%m_%d_%H_%M_%SZ')"
FTP_DIR="/data/ftp/${FOLDER_NAME}/zim"
mkdir -p "$FTP_DIR"

# Subfolders
for subdir in 1 12 24 10_day; do
    mkdir -p "$LOCAL_OUTDATA/$subdir"
done
echo "📁 FTP directory ready: $FTP_DIR"

PRODUCTS=(acc_precip cloudcover meteograms tephigrams extract_acc_precip extract_temperature symbograms)
for PRODUCT in "${PRODUCTS[@]}"; do
    SRC_DIR="/home/wrf/deployed/nons_wrf_v4/python-plotting-toolbox/local_outdata/$PRODUCT"
    if [ -d "$SRC_DIR" ]; then
        cp -R "$SRC_DIR" "$FTP_DIR/"
        echo "✅ Copied $PRODUCT."
    else
        echo "⚠️ $PRODUCT directory missing."
    fi
done

###############################################################
### REMOTE FTP TRANSFER
###############################################################
HOST="192.168.0.116"
USER="testftp"
PASS="ftp_user2025"
REMOTE_PARENT="/local_wrf"
REMOTE_FOLDER="${REMOTE_PARENT}/${FOLDER_NAME}"

echo "🌐 Starting FTP transfer to $HOST..."
if lftp -u "$USER","$PASS" "$HOST" -e "
set ftp:ssl-allow no
set net:timeout 10
set net:max-retries 1
cls -1 $REMOTE_PARENT
bye
" 2>/dev/null | grep -q "$FOLDER_NAME"; then
    echo "⚠️ Remote folder already exists ($REMOTE_FOLDER)."
    touch "$STAMP_FILE"  # ensure wrapper can detect completion
    exit 13
else
    echo "✅ Folder not found. Uploading..."
    if ! lftp -u "$USER","$PASS" "$HOST" -e "
set ftp:ssl-allow no
set net:timeout 15
set net:max-retries 2
mirror -R '$FTP_DIR' '$REMOTE_FOLDER'
bye
"; then
        echo "❌ FTP upload failed. Exiting with code 13."
        touch "$STAMP_FILE"  # still create stamp for wrapper
        exit 13
    fi
    echo "✅ FTP upload completed successfully."
fi

###############################################################
### CLEANUP LEFTOVER PROCESSES
###############################################################
echo "🧹 Cleaning lingering processes..."
for k in retrieve_gfs_data plot_runner.py extract_runner.py lftp; do
    pkill -f "$k" 2>/dev/null || true
done
echo "✅ Cleanup complete."

###############################################################
### END SCRIPT
###############################################################
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "🏁 Script completed at: $(date -u)"
echo "🕒 Total runtime: ${DURATION}s"
exit 0
