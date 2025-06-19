#!/bin/bash

####################################################
### DATE VARIABLES
####################################################
START_DATE="$(date +"%Y%m%d")"
END_DATE="$(date +"%Y%m%d" -d "+16 days")"
echo "Production started: $START_DATE to $END_DATE"

####################################################
### COPY GFS DATA TO AUTO/INDATA
####################################################
rm -rf /home/wrf/nons/auto/indata/*
echo "Deleted data from auto/indata."
cp -r /home/wrf/nons/gfs-retrieval/local_outdata/* /home/wrf/nons/auto/indata/
echo "Copied GFS data to auto/indata."

####################################################
### PLOTTING
####################################################
echo "Starting plotting..."
cd /home/wrf/nons/python-plotting-toolbox/ || { echo "Error: Failed to enter plotting directory"; exit 1; }
source venv/bin/activate
python3 plot_runner.py || { echo "Error: Failed to run plot_runner.py"; exit 1; }
echo "Plotting completed successfully."
deactivate

####################################################
### EXTRACTING
####################################################
echo "Starting extraction..."
python3 extract_runner.py || { echo "Error: Failed to run extract_runner.py"; exit 1; }
echo "Extraction completed successfully."

####################################################
### COPY PRODUCTS TO FTP
####################################################
FTP_DIR="/data/ftp/$(date +"%Y%m%d00")/zim"
mkdir -p "$FTP_DIR"
echo "FTP upload directory: $FTP_DIR"

PRODUCTS=(acc_precip cloudcover meteograms tephigrams extract_acc_precip extract_temperature symbograms)
for PRODUCT in "${PRODUCTS[@]}"; do
    SRC_DIR="/home/wrf/nons/python-plotting-toolbox/local_outdata/$PRODUCT"
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

check_and_copy "/home/wrf/uems/runs/southern_africa/emsprd/grads/d02htm" "$FTP_DIR/" "Copied d02htm for Southern Africa."
check_and_copy "/home/wrf/uems/runs/southern_africa/emsprd/grads/d01htm" "$FTP_DIR/" "Copied d01htm for Southern Africa."
check_and_copy "/home/wrf/uems/runs/zimbabwe/emsprd/grads/d01htm" "$FTP_DIR/" "Copied d01htm for Zimbabwe."

####################################################
### FINISHING UP
####################################################
echo "FINITO TODAY'S PRODUCTION !!!"
