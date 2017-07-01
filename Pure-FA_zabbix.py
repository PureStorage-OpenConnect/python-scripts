#!/usr/bin/python3

#
## Overview
#
# This short Python example illustrates how to build a simple extension to the Zabbix agent to monitor
# Pure Storage FlashArrays. The Pure Storage Python REST Client is used to query the FlashArray basic performance
# counters. The typical sampling mechanism of Zabbix tends to acquire a single counter at time and this
# somewhat discords with the queries that can be executed through the Python REST Client which
# usualy gather multiple counters from a single request. Therefore, in order to avoid multiple call to the
# same method to get different counters the script optimizes the number of calls by using a dedicated SQLite
# database to store the results of a single query and limits the sample rate to the minimum interval of 60 seconds.
#
## Installation
# 
# The script should be copied to a convenient folder location on the machine hosting the Zabbix agent meant to monitor
# also the FlashArray, for example the /usr/local/bin folder.
# Change the execution rights of the program to allow the execution to 'all' (usually chmod 0755).
# Create a file named userparameter_pure.conf in the /etc/zabbix/zabbix_agentd.d/ folder. The file should
# contain just the following line
#
# `UserParameter=pureFA.fainfo[*],/usr/local/bin/pure-FA.py $1 $2 $3 $4`
#
# Restart the Zabbix agent
# Add a template to the Zabbix server configuration to model FlashArrays and populate the template with one application
# containing the seven item representing the monitored counters: 'input_per_sec', 'output_per_sec', 'queue_depth', 'reads_per_sec',
# 'writes_per_sec', 'usec_per_read_op' and 'usec_per_write_op'.
# Each single item should have a Key specified like the following
#
# pureFA.fainfo[{$ENDPOINT},{$APITOKEN},{$CACHE}, *counter_name*]
#
# where *counter_name* is one of above mentioned counters.
# Add to the template the graphs you may want to draw combininig the specified Items. The items can be used
# to define Triggers as well.
# Add each single FlashArray to the monitored hosts of the Zabbix server
# Define the macros to be associated to the key variables {$ENDPOINT},{$APITOKEN} and{$CACHE}. ENDPOINT is 
# the hostname or the IP address of the Pure FlashArray, APITOKEN is the authentication token for that FlashArray
# and CACHE is the local path of the SQLite database to store the temporary sampled counters.
#
#
## Dependencies
#
#  purestorage       Pure Storage Python REST Client (https://github.com/purestorage/rest-client)
#  posix_ipc
#  


 
import argparse
import sys
import json
import purestorage
import urllib3
import sqlite3
import posix_ipc
from dateutil.parser import parse
from datetime import datetime, timedelta
from time import sleep

# Global variables
SEM_NAME = '/pure_sem_01'
MIN_INTERVAL = 60
TIMEOUT = 600


def getFAinfo(flash_array, apitoken):
    # Retrieves the basic statistics of the given flash_array
    urllib3.disable_warnings()
    fa = purestorage.FlashArray(flash_array, api_token=apitoken)
    fainfo = fa.get(action='monitor')
    fa.invalidate_cookie()
    return(fainfo)


parser = argparse.ArgumentParser(description="Retrieves basic FA info")
parser.add_argument("endpoint", help="FA hostname or ip address")
parser.add_argument("apitoken", help="FA api_token")
parser.add_argument("cache", help="SQLite cache database")
parser.add_argument("kpi", choices=['input_per_sec',
                                    'output_per_sec',
                                    'queue_depth',
                                    'reads_per_sec',
                                    'writes_per_sec',
                                    'usec_per_read_op',
                                    'usec_per_write_op'])
args = parser.parse_args()


conn = sqlite3.connect(args.cache, isolation_level=None)

#  Get the most recent sampled data from db
c = conn.cursor()
c.execute("SELECT * FROM fainfo WHERE endpoint=?", (args.endpoint,))
row =  c.fetchone()
fa_info = [{}];

if row is None:
    # table fainfo not initialized with this flasharray
    dt1 = datetime.min
else:
    dt1 = parse(row[8])
    fa_info[0]['input_per_sec'] = row[1]
    fa_info[0]['output_per_sec'] = row[2]
    fa_info[0]['queue_depth'] = row[3]
    fa_info[0]['reads_per_sec'] = row[4]
    fa_info[0]['writes_per_sec'] = row[5]
    fa_info[0]['usec_per_read_op'] = row[6]
    fa_info[0]['usec_per_write_op'] = row[7]
    fa_info[0]['time'] = row[8]

# Check if last sample is too old.
dt2 = datetime.now(dt1.tzinfo)
d = dt2 - dt1

if (d.total_seconds() > MIN_INTERVAL):
    # Last 
    sem = posix_ipc.Semaphore(SEM_NAME, posix_ipc.O_CREAT, initial_value = 1)
    if (d.total_seconds() > TIMEOUT):
        sem.release()
        sem.unlink()
        sem = posix_ipc.Semaphore(SEM_NAME, posix_ipc.O_CREAT, initial_value = 1)

    try:
        # Attempt to enter critical section. This is necessary in order to have a single writer
		# accessing the sqlite database at time
        sem.acquire(0)
		# Get basic statistics from FlashArray
        fa_info = getFAinfo(args.endpoint, args.apitoken)

        if row is None:
		   # No entry for this FlashArrayA. Prepare the statement to add the record for this FlashArray
           sql = ''' INSERT INTO fainfo(
                          in_per_sec,
                          out_per_sec,
                          q_depth,
                          rd_per_sec,
                          wr_per_sec,
                          rd_latency,
                          wr_latency,
                          time,
                          endpoint)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        else:
		    # Prepare the statement to update  the record for this FlashArray.
            sql = ''' UPDATE fainfo
                      SET in_per_sec = ? ,
                          out_per_sec = ? ,
                          q_depth = ? ,
                          rd_per_sec = ? ,
                          wr_per_sec = ? ,
                          rd_latency = ? ,
                          wr_latency = ? ,
                          time = ?
                      WHERE endpoint = ?'''

		# Execute the SQL query 
        c.execute(sql, (fa_info[0]['input_per_sec'],
                        fa_info[0]['output_per_sec'],
                        fa_info[0]['queue_depth'],
                        fa_info[0]['reads_per_sec'],
                        fa_info[0]['writes_per_sec'],
                        fa_info[0]['usec_per_read_op'],
                        fa_info[0]['usec_per_write_op'],
                        fa_info[0]['time'],
                        args.endpoint))
        sem.release()
    except posix_ipc.BusyError:
        pass

# Print to standard outout, This returns the value to the Zabbix agent 
print(fa_info[0][args.kpi])
conn.close()
sys.exit(0)
