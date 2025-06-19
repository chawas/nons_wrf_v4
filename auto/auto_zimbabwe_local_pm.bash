#!/bin/bash

####################################################
### OBTAIN TODAY'S DATE, FORMAT and REPLCE in SCRIPTS
####################################################
#cd /home/cosmo_zim/Meogram_scripts/MSD_scripts/
#echo "STAR TODAY'S PRODUCTION !!! : $now" >> $log_filename
#tail -f $HOME/nons/gfs-retrieval/logs/zimbabwe_`date +\%Y\%m\%d`.log

find /home/wrf/nons/gfs-retrieval/logs/ -name "*.log" -type f -mtime +1 -delete

#inotifywait /home/wrf/nons/gfs-retrieval/ --recursive --monitor
#echo "Now monitoring gfs-retrival"

#log_filename=$HOME/nons/gfs-retrieval/logs/zimbabwe_`date +\%Y\%m\%d`.log
#echo $log_filename
#echo "STAR TODAY'S PRODUCTION !!! : $now" > $log_filename

dategrib="$(date +"%y%m%d0000")"
start="$(date +"%Y%m%d")"
end="$(date +"%Y%m%d" -d "+16 days")"
now=$(date)
echo $now
echo "chawas 2"
echo $dategrib
echo "Starting $start and ending $end" 
#echo $end
#tail -f $HOME/nons/gfs-retrieval/logs/zimbabwe_`date +\%Y\%m\%d`.log



####################################################
### RETRIVE GFS DATA
####################################################
cd /home/wrf/nons/gfs-retrieval/
#cd /home/chawas/nons/gfs-retrieval/
echo $PWD
set -e
source venv/bin/activate

#delete data from local_outdata
cd /home/wrf/nons/gfs-retrieval/local_outdata/
#cd /home/chawas/nons/gfs-retrieval/local_outdata/
rm -rf *
echo "deleted data from local_indata"

#download data from GFS
cd /home/wrf/nons/gfs-retrieval/
#cd /home/chawas/nons/gfs-retrieval/

python3 retrieve_gfs_data.py

#-tail -f zimbabwe.log

#sleep 180

deactivate

#delete data from aouto/indata
cd /home/wrf/nons/auto/indata/
#cd /home/chawas/nons/auto/indata/
rm -rf *
echo "Deleted data from local_indata"

# copy from local_indata to auto/indata
cd /home/wrf/nons/gfs-retrieval/local_outdata/

cp -r * /home/wrf/nons/auto/indata/
echo "Copied grib to auto/indata"


####################################################
### PLOTTING
####################################################
#cd ../python-plotting-toolbox/
cd /home/wrf/nons/python-plotting-toolbox/

echo $PWD
set -e
source venv/bin/activate
echo "Now at plotting"
python3 plot_runner.py 

sleep 180
echo "Finished plotting !!!!"


####################################################
### EXTRACTING
####################################################

python3 extract_runner.py

sleep 60

echo "Finished extracting !!!!"


deactivate

####################################################
### COPY PRODUCTS FOLDERS to FTP
####################################################






#sleep 600
#cd /home/wrf/zimbabwe/
#mkdir products
cd /home/wrf/ftp/upload/
d="$(date +"%Y%m%d12")"
mkdir /home/wrf/ftp/upload/$d
mkdir /home/wrf/ftp/upload/$d/zim
dd="/home/wrf/ftp/upload/$d/zim"
#cd /home/wrf/nons/python-plotting-toolbox/local_outdata/
echo $dd
#cp -R d01htm_20230621/ "$dd"
#echo "Finished copying d1htm"
#cd /home/wrf/Development/additional_products/WRF/local_outdata/
cd /home/wrf/nons/python-plotting-toolbox/local_outdata/
cp -R acc_precip/ "$dd"
echo "Finished copying acc_precip"

cp -R cloudcover/ "$dd"
echo "Finished copying cloud cover"

cp -R meteograms/ "$dd"
echo "Finished copying meteograms"

cp -R tephigrams/ "$dd"
echo "Finished copying tephigrams"

cp -R extract_acc_precip/ "$dd"
echo "Finished extracting accumulated precipitation"

cp -R extract_temperature/ "$dd"
echo "Finished extracting temperatures"

cp -R symbograms/ "$dd"
echo "Finished copying symbograms"


sleep 60

# take d02htm from southern africa

if [ -d '/home/wrf/uems/runs/southern_africa/emsprd/grads/d02htm' ]; then
    echo 'Directory exists'
    cd /home/wrf/uems/runs/southern_africa/emsprd/grads/
    echo $dd
    cp -r d02htm/ "$dd"
    echo "Finished copying d02.htm from southern africa to dd: $now"
else
	echo 'Veduwee Directory does not exist'
	
fi

# take d01htm from southern africa

if [ -d '/home/wrf/uems/runs/southern_africa/emsprd/grads/d01htm' ]; then
    echo 'Directory exists'
    cd /home/wrf/uems/runs/southern_africa/emsprd/grads/
    echo $dd
    cp -R d01htm/ htm_sa1
    cp -R htm_sa1/ "$dd"
    echo "Finished copying d01.htm from southern africa to dd: $now"
else
	echo 'Veduwee Directory does not exist'
	
fi

#check if d01htm is available if not create it
if [ -d '/home/wrf/uems/runs/zimbabwe/emsprd/grads/d01htm' ]; then
    echo 'Directory exists'
    cd /home/wrf/uems/runs/zimbabwe/emsprd/grads/
    echo $dd
    cp -R d01htm/ htm_zim
    cp -R htm_zim/ "$dd"
    echo "Finished copying d01.htm from zimbabwe to dd: $now"
else
    echo 'Directory does not exist'
    cd /home/wrf/uems/runs/zimbabwe/
    echo "========================="
    echo "I am in folder zimbabwe!!"
    echo "========================="
    a="--grads"
#    module load /home/wrf/uems/etc/modulefiles/UEMSwrkstn
#    which UEMSwrkstn
#    perl ./ems_post --grads
#    sleep 60
    
#   if [ -d '/home/wrf/uems/runs/zimbabwe/emsprd/grads/d01htm' ]; then
#    echo 'Directory exists'
#    cd /home/wrf/uems/runs/zimbabwe/emsprd/grads/
#   echo $dd
#   cp -R d01htm/ "$dd"
#   echo "Finished copying d01.htm from zimbabwe to dd: $now"
   echo "Doing Nothing"
#else
#    echo 'Still after creating it the directory does not exist'
    
#    fi
fi


sleep 60




sleep 60
now=$(date)
#echo "Finished copying tephigrams at : $now"
echo "FINITO TODAY'S PRODUCTION !!! : $now"




#sleep 180
#conda deactivate

