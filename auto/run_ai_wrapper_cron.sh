#!/bin/bash
LOGFILE="/home/wrf/nons/gfs-retrieval/logs/ai_run_$(date +%Y%m%d%H%M).log"
/usr/bin/python3 /home/wrf/nons/auto/ai_run_wrf_am_wrapper_11.py >> "$LOGFILE" 2>&1
