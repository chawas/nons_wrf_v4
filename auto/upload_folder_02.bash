#!/bin/bash
#!/bin/bash

# FTP Credentials
HOST="192.168.0.116"
USER="testftp"
PASS="ftp_user2025"

# Local folder to upload: e.g. /data/ftp/2025072300
NOW=$(date +"%Y%m%d")
HOUR="00"
LOCAL_FOLDER="/data/ftp/${NOW}${HOUR}"

# Remote directory
REMOTE_FOLDER="/local_wrf"

# Show folders
echo "Uploading from local folder: $LOCAL_FOLDER"
echo "Uploading to remote folder: $REMOTE_FOLDER on FTP server $HOST"

# Upload using lftp
lftp -u "$USER","$PASS" $HOST <<EOF
set ftp:ssl-allow no
mirror -R "$LOCAL_FOLDER" "$REMOTE_FOLDER"
bye
EOF
