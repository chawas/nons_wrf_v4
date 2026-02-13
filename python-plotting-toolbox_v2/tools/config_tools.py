import argparse

def handle_input_args():
    '''
    Handle input arguments regarding start and end time
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-start",
        "--start",
        default=None,#nowTime_aware_local_obj,#desired_tz.localize(datetime.datetime.utcnow()).astimezone(desired_tz), #Set default time to now time
        help="set a start time for meteograms in local time. Date format should be YYYYMMDDTHH ."
    )
    parser.add_argument(
        "-end",
        "--end",
        default=None, #nowTime_aware_local_obj + datetime.timedelta(days=4), #desired_tz.localize(datetime.datetime.utcnow() + datetime.timedelta(days=4)).astimezone(desired_tz), #Set default length +4 days from now time
        help="set an end time for meteograms in local time. Date format should be YYYYMMDDTHH ."
    )

    parser.add_argument(
        "-tz",
        "--tz",
        default = 'Africa/Harare',
        help = "Specify a timezone for which the meteogram should be printed. The default time is local time in Harare ('Africa/Harare'). Set '-tz UTC' for UTC time."
    )
    # # parser.add_argument(
    #     "--dTmax",
    #     help="dTmax (daily temperature maximum) filename"
    # )
    # parser.add_argument(
    #     "--outDir",
    #     help="Directory for result output"
    # )

    su = parser.parse_args()
    return su


def readCitiesConfig(inPath):

    out_dict = {}

    with open(inPath) as f:
        cities = f.readlines()
    for in_line in cities:
        in_line_spl = in_line.split(';')
        
        city = in_line_spl[0]
        lat  = float(in_line_spl[1])
        lon  = float(in_line_spl[2])
        if city not in out_dict:
            out_dict.update({ city : {'coords' : [lat, lon]} } )

    return out_dict