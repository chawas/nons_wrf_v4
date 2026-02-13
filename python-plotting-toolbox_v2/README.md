# python-plotting-toolbox


The two scripts that need to run are plot_runner.py and extract_runner.py. The function check_times.find_latest_available_forecast(days_ahead) will automatically find the forecast cycle with enough data for 'days_ahead' to create plots or extractions. For automatic update, activate the update() function and set an regular update time as "HH:MM".

All of the indvidual plotting and extracting scripts will reset their respective outdata directories. Whenever a new run is made, data will have been replaced.

Configurations are handled in the config.json file. Set DATA_SOURCE to either "GFS", "ECMWF" or "WRF". The toolbox handles one of these datasets at a time, and two parallel version of the scripts will have to be used to plot from both data sources.
For WRF or ECMWF, set the indata paths, the prefixes for the file structures, the domain, wether precipitation is accumulated or not in the GRIB file setup for that particular data set (for WRF it is usually intentsity per time step and for ECMWF accumulated since beginning of run) and the multiplication factor for the precipitation

All location conf files in IO/plotters and IO/extracters should be semicolon separated as name;lat;lon . Lat and lon are in global wgs84.

Preciptation extraction
In IO/extracters/io_extract_acc_precipitation.conf, set the start of the precipitaion day (usually 06 UTC) as an integer. Set the accumulation times as comma separated integers. Extraction times will be created from this. For example, an start of day of 06 UTC and accumulation times of 12, 24 gives extraction time 06:00 for 24 hours and 06:00 and 18:00 for 12 hours.