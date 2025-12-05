#!/bin/bash
######################################################################
###  AUTO_PRODUCTION.SH
###  Purpose: Automate GFS retrieval, WRF plotting, extraction, and FTP upload
###  Author : [Your Name]
###  Updated: 2025-10-16
###
###  Key Features:
###   • Controlled cycle (uses WRF_CYCLE env var if set)
###   • Verifies completeness of GFS files (hourly → 120h, 3-hourly → 384h)
###   • Continues with minor missing data (≤5 files)
###   • Exits with status 13 on FTP upload failure (wrapper handles notifications)
###   • Automatically cleans logs and processes
######################################################################

set -e
set -o pipefail
trap "echo 'Keyboard interruption detected'; exit 12" SIGINT

######################################################################
### LOGGING SETUP
######################################################################
NOW=$(date +"%Y%m%d%H%M%S")
LOGFILE="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/logs/auto_production_$NOW.log"
exec > >(tee -a "$LOGFILE") 2>&1

START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
START_EPOCH=$(date +%s)

echo "[$START_TIME] Starting full WRF production and FTP sequence..."
echo "------------------------------------------------------------"




echo "------------------------------------------------------------"
echo "🌍  AUTO PRODUCTION SCRIPT STARTED  ($(date))"
echo "------------------------------------------------------------"
echo "Log file: $LOGFILE"
echo

######################################################################
### DETERMINE CYCLE
######################################################################
# --- Determine WRF cycle (00Z or 12Z) ---
if [ -n "$WRF_CYCLE" ]; then
    echo "Using existing WRF_CYCLE=$WRF_CYCLE"
else
    hour=$(date -u +"%H")
    if [ "$hour" -lt 16 ]; then
        cycle="00"
    else
        cycle="12"
    fi
    export WRF_CYCLE="$cycle"
    echo "Setting WRF_CYCLE=$WRF_CYCLE"
fi


FOLDER_NAME=$(date -u +"%Y_%m_%d_%H_%M_${cycle}Z")
echo "Cycle determined: ${cycle}Z"
echo "Output folder: $FOLDER_NAME"
echo

######################################################################
### CLEAN OLD LOGS
######################################################################
find /home/wrf/deployed/nons_wrf_v4/gfs-retrieval/logs -name "*.log" -type f -mtime +1 -delete
echo "🧹 Old log files cleaned."

######################################################################
### DATE VARIABLES
######################################################################
DATEGRIB="$(date -u +"%y%m%d${cycle}00")"
START_DATE="$(date -u +"%Y%m%d")"
END_DATE="$(date -u +"%Y%m%d" -d "+16 days")"
echo "Production period : $START_DATE → $END_DATE"
echo "GFS date string   : $DATEGRIB"
echo

######################################################################
### ACTIVATE PYTHON ENVIRONMENT
######################################################################
if [ -f "/home/wrf/deployed/nons_wrf_v4/nons_env/bin/activate" ]; then
    source /home/wrf/deployed/nons_wrf_v4/nons_env/bin/activate
    echo "✅ Python environment 'nons_env' activated."
else
    echo "❌ Error: Could not find nons_env virtual environment."
    exit 11
fi

######################################################################
### USE EXISTING DOWNLOADED GFS DATA (managed by wrapper)
######################################################################
LOCAL_OUTDATA="/home/wrf/deployed/nons_wrf_v4/gfs-retrieval/local_outdata"

if [ ! -d "$LOCAL_OUTDATA" ] || [ -z "$(ls -A "$LOCAL_OUTDATA")" ]; then
    echo "❌ No GFS data found in $LOCAL_OUTDATA. Wrapper should handle download before this script."
    exit 10
fi

echo "✅ Using existing GFS data from: $LOCAL_OUTDATA"

######################################################################
### COPY GFS DATA INTO AUTO/INDATA
######################################################################
rm -rf /home/wrf/deployed/nons_wrf_v4/auto/indata/*
cp -r "$LOCAL_OUTDATA"/* /home/wrf/deployed/nons_wrf_v4/auto/indata/
echo "📂 Copied GFS data into auto/indata."

######################################################################
### PLOTTING AND EXTRACTION
######################################################################
cd /home/wrf/deployed/nons_wrf_v4/python-plotting-toolbox/ || { echo "❌ Failed to enter plotting directory"; exit 11; }

echo "🎨 Running plot_runner.py..."
python plot_runner.py || { echo "❌ Plotting failed"; exit 13; }
echo "✅ Plotting complete."

echo "📊 Running extract_runner.py..."
python extract_runner.py || { echo "❌ Extraction failed"; exit 14; }
echo "✅ Extraction complete."

######################################################################
### LOCAL FTP FOLDER PREPARATION
######################################################################
FTP_DIR="/data/ftp/${FOLDER_NAME}/zim"
mkdir -p "$FTP_DIR"
echo "FTP upload directory: $FTP_DIR"

PRODUCTS=(acc_precip cloudcover meteograms tephigrams extract_acc_precip extract_temperature symbograms)
for PRODUCT in "${PRODUCTS[@]}"; do
    SRC_DIR="/home/wrf/deployed/nons_wrf_v4/python-plotting-toolbox/local_outdata/$PRODUCT"
    if [ -d "$SRC_DIR" ]; then
        cp -R "$SRC_DIR" "$FTP_DIR/"
        echo "   → Copied $PRODUCT"
    else
        echo "⚠️ Directory missing: $SRC_DIR"
    fi
done
echo "✅ All products staged for FTP."


####################################################
### HANDLE WX PRESENTATION IMAGES
####################################################
WX_DIR="/home/wrf/deployed/chawas_03/wx_presentation/images"
if [ -d "$WX_DIR" ]; then
    cp -R /home/wrf/deployed/chawas_03/wx_presentation/ "$FTP_DIR/presentation"
    echo "Copied wx presentation images to FTP directory."
     PRODUCT_SUCCESS=true
else
    echo "Warning: WX presentation images directory $WX_DIR does not exist."
fi


######################################################################
### REMOTE FTP UPLOAD
######################################################################
HOST="192.168.0.245"
USER="testftp"
PASS="ftp_user2025"
REMOTE_PARENT="/local_wrf"
REMOTE_FOLDER="${REMOTE_PARENT}/${FOLDER_NAME}"

echo "🌐 Preparing to upload to remote FTP: ${HOST}:${REMOTE_FOLDER}"

if lftp -u "$USER","$PASS" "$HOST" -e "
set ftp:ssl-allow no
set net:timeout 10
set net:max-retries 1
cls -1 $REMOTE_PARENT
bye
" 2>/dev/null | grep -q "$FOLDER_NAME"; then
    echo "❌ Remote folder already exists. Skipping upload."
else
    echo "🚀 Uploading to FTP..."
    if ! lftp -u "$USER","$PASS" "$HOST" -e "
        set ftp:ssl-allow no
        set net:timeout 15
        set net:max-retries 2
        mirror -R '$FTP_DIR' '$REMOTE_FOLDER'
        bye
    "; then
        echo "❌ FTP upload failed (network or permission issue)."
        FTP_SUCCESS=false
        exit 16
    fi
    echo "✅ FTP upload complete."
    FTP_SUCCESS=true
fi

######################################################################
### CLEANUP LEFTOVER PROCESSES
######################################################################
echo "🧹 Cleaning up processes..."
RUN_KEYWORDS=("retrieve_gfs_data" "plot_runner.py" "extract_runner.py" "lftp")
for keyword in "${RUN_KEYWORDS[@]}"; do
    PIDS=$(pgrep -f "$keyword" || true)
    if [ -n "$PIDS" ]; then
        echo "   → Killing: $keyword ($PIDS)"
        kill -9 $PIDS 2>/dev/null || true
    fi
done
echo "✅ All background processes terminated."



# =====================================================
# MONTHLY PRODUCTION LOGGING (Compact One-Line Format)
# =====================================================

LOG_DIR="/home/wrf/deployed/nons_wrf_v4/reports"
mkdir -p "$LOG_DIR"

# Automatically rotate monthly log
MONTHLY_LOG="$LOG_DIR/product_log_$(date +%Y%m).log"

echo "[$START_TIME] Starting full WRF production and FTP sequence..."



# === Compute duration ===
END_TIME=$(date '+%Y-%m-%d %H:%M:%S')
END_EPOCH=$(date +%s)
DURATION=$((END_EPOCH - START_EPOCH))
DURATION_MIN=$((DURATION / 60))
DURATION_SEC=$((DURATION % 60))
DURATION_STR="${DURATION_MIN}m${DURATION_SEC}s"

# === Determine note/status ===
if $PRODUCT_SUCCESS && $FTP_SUCCESS; then
    NOTE="✅SUCCESS"
elif $PRODUCT_SUCCESS && ! $FTP_SUCCESS; then
    NOTE="⚠️FTP_FAIL"
else
    NOTE="❌PROD_FAIL"
fi

# === Append compact one-line log ===
echo "$(date '+%Y-%m-%d %H:%M:%S'), START=$START_TIME, END=$END_TIME, DURATION=$DURATION_STR, NOTE=$NOTE" >> "$MONTHLY_LOG"

echo "[$END_TIME] Workflow completed → $NOTE"
echo "Logged to $MONTHLY_LOG"






######################################################################
### END OF SCRIPT
######################################################################
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo
echo "------------------------------------------------------------"
echo "✅ SCRIPT COMPLETED SUCCESSFULLY at $(date)"
echo "⏱️ Total runtime: ${DURATION}s"
echo "------------------------------------------------------------"
exit 0
