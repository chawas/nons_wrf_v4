#!/bin/bash

# FTP Credentials
HOST="192.168.0.116"
USER="testftp"
PASS="ftp_user2025"

# Local folder to upload
NOW=$(date +"%Y%m%d")
HOUR="00"
FOLDER_NAME="${NOW}${HOUR}"
LOCAL_FOLDER="/data/ftp/${FOLDER_NAME}"
REMOTE_FOLDER="/${FOLDER_NAME/local_wrf}"

# Show folders
echo "Uploading from local folder: $LOCAL_FOLDER"
echo "Uploading to remote folder: $REMOTE_FOLDER on FTP server $HOST"

# Check if remote folder exists
echo "Checking if remote folder already exists..."

EXISTS=$(lftp -u "$USER","$PASS" $HOST -e "cls -1 $REMOTE_FOLDER; bye" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "❌ Remote folder '$REMOTE_FOLDER' already exists. Skipping upload."
    exit 0
else
    echo "✅ Remote folder not found. Proceeding with upload..."
fi

# Upload using lftp
lftp -u "$USER","$PASS" $HOST <<EOF
set ftp:ssl-allow no
mirror -R "$LOCAL_FOLDER" "$REMOTE_FOLDER"
bye
EOF
