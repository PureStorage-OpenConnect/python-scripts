from purestorage import purestorage
import sys
import csv
import requests
import time
import os
import argparse

# Disable certificate warnings

requests.packages.urllib3.disable_warnings()

starttime = time.time()

# Set array variables

flasharray = ''
api_token = '’

# Set script variables

time_stamp = (time.strftime('%m-%d-%y'))
report_file = 'space-report-' + time_stamp + '.csv'
interval_options = '1h, 3h, 24h, 7d, 30d, 90d, 1y'

def fa_connect(flasharray, api_token):

    global array

    try:
        array = purestorage.FlashArray(flasharray, api_token=api_token)
        print('Successfully connected to ', flasharray)
    except Exception as e:
        print(e)
        sys.exit('Exiting: Unable to establish session')

def write_output(interval):
    with open(report_file, 'w') as csvfile:
        fieldnames = ['Volume Name', 'Current Data Reduction', 'Data Reduction ' + interval, 'Current Size(GB)',
                      'Size ' + interval + ' Ago(GB)', interval + ' Growth(GB)']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        print('Parsing volume data.')

        # Loop through all volumes to get historical space data

        for currentvol in allvolumes:
            thisvol = array.get_volume(currentvol['name'], space='True', historical=interval)
            volname = thisvol[0]['name']
            volcurdr = round(thisvol[0]['data_reduction'], 2)
            volstartdr = round(thisvol[len(thisvol) - 1]['data_reduction'], 2)
            volstartsize = round(thisvol[0]['volumes'] / 1024 / 1024 / 1024, 2)
            volcursize = round(thisvol[len(thisvol) - 1]['volumes'] / 1024 / 1024 / 1024, 2)
            volsizedif = volcursize - volstartsize
            volsizedif = round(volsizedif, 2)
            writer.writerow(
                {'Volume Name': volname, 'Current Data Reduction': volcurdr, 'Data Reduction ' + interval: volstartdr,
                 'Current Size(GB)': volcursize, 'Size ' + interval + ' Ago(GB)': volstartsize, interval + ' Growth(GB)': volsizedif})

def arg_parser():

    global interval

    parser = argparse.ArgumentParser('Add interval')
    parser.add_argument('interval', type=str, help='(' + interval_options + ')')

    args = parser.parse_args()
    interval = args.interval

    if interval not in interval_options:
        print('Please enter a valid interval: ' + interval_options)
        sys.exit()

    return interval

def main():

    global allvolumes, interval

    # Check to see if FlashArray and API key have been set

    if flasharray == "":
        sys.exit('Please edit this file and set the IP or DNS name for the variable: flasharray')

    if api_token == "":
        sys.exit('Please edit this file and assign an API token for the variable: api_token for the FlashArray ' + flasharray)

    # Call argument parser to check for command line options

    arg_parser()

    # Call function to connect to the FlashArray

    fa_connect(flasharray, api_token)

    # Gather all volumes on the array

    allvolumes = array.list_volumes()
    print('Gathering all volumes.')

    # Call function to parse and write output to CSV file

    write_output(interval)

    print('Script completed in ', round(time.time()-starttime,2), ' seconds.')
    print('Output file: ', report_file, ' located at: ', os.getcwd())

main()
