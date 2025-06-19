#!/bin/bash

####################################################
### OBTAIN TODAY'S DATE, FORMAT and REPLCE in SCRIPTS
####################################################
# cd /home/cosmo_zim/Meogram_scripts/MSD_scripts/
# echo "STAR TODAY'S PRODUCTION !!! : $now" >> $log_filename
# tail -f $HOME/nons/gfs-retrieval/logs/zimbabwe_`date +\%Y\%m\%d`.log

import os
import shutil
#import datetime
from datetime import datetime, timedelta

def automate():

    # Specify the directory you want to change to

    #from datetime import datetime, timedelta

    # Get the current date
    #formatted_date = future_date.strftime('%Y%m%d') + ' +00'
    current_date = datetime.now()

    # Add 16 days to the current date
    future_date = current_date + timedelta(days=16)

    # Format the future date as YYYYMMDD
    formatted_date = future_date.strftime('%Y%m%d')

    print("future date : ", formatted_date)


    forecast_cycle_date = datetime.now().replace(hour=00)
    forecast_cycle_URL_date_string = datetime.strftime(forecast_cycle_date, format='%Y%m%d/%H/')
    print("forecast cycle dateforecast_cycle_date :", forecast_cycle_date)
    print("forecast cycle URL date string :", forecast_cycle_URL_date_string)

    dategrib = 'datetime.now().strftime("%Y%m%d%d00")'


    startdate=datetime.now().strftime("%Y%m%d")
    dategrib = datetime.now().strftime("%Y%m%d") + '00'
    print("dategrib", dategrib)

    print("chawas 2")
    #print(dategrib)
    print("Starting", startdate)
    print("ending", future_date)
    # echo $end
    # tail -f $HOME/nons/gfs-retrieval/logs/zimbabwe_`date +\%Y\%m\%d`.log


    ####################################################
    ### RETRIVE GFS DATA
    ####################################################
    directory = '/home/wrf/nons/gfs-retrieval/local_outdata/'

    try:
        os.chdir(directory)
        print(f"Successfully changed the directory to: {os.getcwd()}")
     #   delete_directory_contents('/home/wrf/nons/gfs-retrieval/local_outdata/')
        print("deleted data from local_indata")
    except FileNotFoundError:
        print(f"The directory {directory} does not exist.")
    except PermissionError:
        print(f"You do not have permission to change to {directory}.")

def delete_directory_contents(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # Remove file or symbolic link
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)  # Remove directory and all its contents
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

# Usage
directory = '/home/wrf/nons/gfs-retrieval/local_outdata/'
delete_directory_contents(directory)
automate()
    # # delete data from local_outdata
    # cd / home / wrf / nons / gfs - retrieval / local_outdata /
    # # cd /home/chawas/nons/gfs-retrieval/local_outdata/
    # rm - rf *
    # echo
    # "deleted data from local_indata"
    #
    # # download data from GFS
    # cd / home / wrf / nons / gfs - retrieval /
    # # cd /home/chawas/nons/gfs-retrieval/
    #
    # python3
    # retrieve_gfs_data.py
    #
    # # -tail -f zimbabwe.log
    #
    # # sleep 180
    #
    # deactivate
    #
    # # delete data from aouto/indata
    # cd / home / wrf / nons / auto / indata /
    # # cd /home/chawas/nons/auto/indata/
    # rm - rf *
    # echo
    # "Deleted data from local_indata"
    #
    # # copy from local_indata to auto/indata
    # cd / home / wrf / nons / gfs - retrieval / local_outdata /
    #
    # cp - r * / home / wrf / nons / auto / indata /
    # echo
    # "Copied grib to auto/indata"
    #
    # ####################################################
    # ### PLOTTING
    # ####################################################
    # # cd ../python-plotting-toolbox/
    # cd / home / wrf / nons / python - plotting - toolbox /
    #
    # echo $PWD
    # set - e
    # source
    # venv / bin / activate
    # echo
    # "Now at plotting"
    # python3
    # plot_runner.py
    #
    # sleep
    # 180
    # echo
    # "Finished plotting !!!!"
    #
    # ####################################################
    # ### EXTRACTING
    # ####################################################
    #
    # python3
    # extract_runner.py
    #
    # sleep
    # 60
    #
    # echo
    # "Finished extracting !!!!"
    #
    # deactivate
    #
    # ####################################################
    # ### COPY PRODUCTS FOLDERS to FTP
    # ####################################################
    #
    #
    # # sleep 600
    # # cd /home/wrf/zimbabwe/
    # # mkdir products
    # cd / home / wrf / ftp / upload /
    # d = "$(date +" % Y % m % d00
    # ")"
    # mkdir / home / wrf / ftp / upload /$d
    # mkdir / home / wrf / ftp / upload /$d / zim
    # dd = "/home/wrf/ftp/upload/$d/zim"
    # # cd /home/wrf/nons/python-plotting-toolbox/local_outdata/
    # echo $dd
    # # cp -R d01htm_20230621/ "$dd"
    # # echo "Finished copying d1htm"
    # # cd /home/wrf/Development/additional_products/WRF/local_outdata/
    # cd / home / wrf / nons / python - plotting - toolbox / local_outdata /
    # cp - R
    # acc_precip / "$dd"
    # echo
    # "Finished copying acc_precip"
    #
    # cp - R
    # cloudcover / "$dd"
    # echo
    # "Finished copying cloud cover"
    #
    # cp - R
    # meteograms / "$dd"
    # echo
    # "Finished copying meteograms"
    #
    # cp - R
    # tephigrams / "$dd"
    # echo
    # "Finished copying tephigrams"
    #
    # cp - R
    # extract_acc_precip / "$dd"
    # echo
    # "Finished extracting accumulated precipitation"
    #
    # cp - R
    # extract_temperature / "$dd"
    # echo
    # "Finished extracting temperatures"
    #
    # cp - R
    # symbograms / "$dd"
    # echo
    # "Finished copying symbograms"
    #
    # sleep
    # 60
    #
    # # take d02htm from southern africa
    #
    # if [-d '/home/wrf/uems/runs/southern_africa/emsprd/grads/d02htm']; then
    # echo
    # 'Directory exists'
    # cd / home / wrf / uems / runs / southern_africa / emsprd / grads /
    # echo $dd
    # cp - r
    # d02htm / "$dd"
    # echo
    # "Finished copying d02.htm from southern africa to dd: $now"
    # else
    # echo
    # 'Veduwee Directory does not exist'
    #
    # fi
    #
    # # take d01htm from southern africa
    #
    # if [-d '/home/wrf/uems/runs/southern_africa/emsprd/grads/d01htm']; then
    # echo
    # 'Directory exists'
    # cd / home / wrf / uems / runs / southern_africa / emsprd / grads /
    # echo $dd
    # cp - R
    # d01htm / htm_sa1
    # cp - R
    # htm_sa1 / "$dd"
    # echo
    # "Finished copying d01.htm from southern africa to dd: $now"
    # else
    # echo
    # 'Veduwee Directory does not exist'
    #
    # fi
    #
    # # check if d01htm is available if not create it
    # if [-d '/home/wrf/uems/runs/zimbabwe/emsprd/grads/d01htm']; then
    # echo
    # 'Directory exists'
    # cd / home / wrf / uems / runs / zimbabwe / emsprd / grads /
    # echo $dd
    # cp - R
    # d01htm / htm_zim
    # cp - R
    # htm_zim / "$dd"
    # echo
    # "Finished copying d01.htm from zimbabwe to dd: $now"
    # else
    # echo
    # 'Directory does not exist'
    # cd / home / wrf / uems / runs / zimbabwe /
    # echo
    # "========================="
    # echo
    # "I am in folder zimbabwe!!"
    # echo
    # "========================="
    # a = "--grads"
    # #    module load /home/wrf/uems/etc/modulefiles/UEMSwrkstn
    # #    which UEMSwrkstn
    # #    perl ./ems_post --grads
    # #    sleep 60
    #
    # #   if [ -d '/home/wrf/uems/runs/zimbabwe/emsprd/grads/d01htm' ]; then
    # #    echo 'Directory exists'
    # #    cd /home/wrf/uems/runs/zimbabwe/emsprd/grads/
    # #   echo $dd
    # #   cp -R d01htm/ "$dd"
    # #   echo "Finished copying d01.htm from zimbabwe to dd: $now"
    # echo
    # "Doing Nothing"
    # # else
    # #    echo 'Still after creating it the directory does not exist'
    #
    # #    fi
    # fi
    #
    # sleep
    # 60
    #
    # # take d01htm from southern africa
    #
    # if [-d '/home/wrf/deployed/webb-downloading/wx_presentation/images/' + datetime.now().strftime("%Y%m%d")]; then
    # echo
    # 'Directory exists'
    # cd / home / wrf / deployed / webb - downloading /
    # cp - R
    # d01htm / wx_presentation
    # echo $dd
    # cp - R
    # htm_sa1 / "$dd"
    # echo
    # "Finished copying images from southern africa to dd: $now"
    # else
    # echo
    # 'Veduwee Directory does not exist'
    #
    # fi
    #
    # sleep
    # 60
    # now =$(date)
    # # echo "Finished copying tephigrams at : $now"
    # echo
    # "FINITO TODAY'S PRODUCTION !!! : $now"
    #
    # # sleep 180
    # # conda deactivate
