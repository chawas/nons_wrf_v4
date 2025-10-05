#!/bin/bash

# FTP Credentials
HOST="192.168.0.116"
USER="testftp"
PASS="ftp_user2025"

# Time-based folder name
NOW=$(date +"%Y%m%d")
HOUR="00"
FOLDER_NAME="${NOW}${HOUR}"
LOCAL_FOLDER="/data/ftp/${FOLDER_NAME}"
REMOTE_PARENT="/local_wrf"
REMOTE_FOLDER="${REMOTE_PARENT}/${FOLDER_NAME}"

# Show folders
echo "Local folder: $LOCAL_FOLDER"
echo "Remote folder: $REMOTE_FOLDER"

# Check if remote folder already exists
echo "Checking if $REMOTE_FOLDER already exists on remote..."

if lftp -u "$USER","$PASS" $HOST <<EOF | grep -q "${FOLDER_NAME}"
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
