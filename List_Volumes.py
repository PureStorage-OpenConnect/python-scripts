import urllib.request
import urllib.parse
import http.client
#import purestorage
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from base64 import b64encode
import os
import sys
import json
import getpass
from optparse import OptionParser
from datetime import datetime, timedelta
import time
from time import gmtime, strftime, strptime
from operator import itemgetter, attrgetter

# Global Variables
VERSION = '1.0.0'
HEADER = 'Pure Storage List Volumes (' + VERSION + ')'
BANNER = ('=' * 102)
DEBUG_LEVEL = 0
VERBOSE_FLAG = False
COOKIE = ''

def create_session(flashArray, user, password, api_token):
    global COOKIE

    # Set-up HTTP header
    userAgent = 'Jakarta Commons-HttpClient/3.1'
    hdrs= {'Content-Type' : 'application/json', 'User-agent' : userAgent, 'Cookie' : COOKIE}
  
    #Establish Session, if no token provide need to create an API token first
    
    if user:
        data = {
               'password': user,
               'username': password
               }
        params = json.dumps(data)
        path = '/api/1.4/auth/apitoken'
        url = 'http://%s%s'%(flashArray,path)
    
        # Perform action
        conn = http.client.HTTPSConnection(flashArray)
        conn.set_debuglevel(DEBUG_LEVEL)
    
        conn.request('POST', path, params, headers=hdrs)
    
        response = conn.getresponse()
        response_data = response.read()
        COOKIE = response.getheader('set-cookie')
    
        if DEBUG_LEVEL != 0:
            print('Status', response.status)
            print('Reason', response.reason)
            print('msg', response.msg)
            print('HTTP Header:', response.info())
            print('Content-Lenghth', response.getheader('Content-Length'))
            print('Cookie', COOKIE)
    
        if (response.reason) != 'OK':
            print(BANNER)
            sys.exit('Exiting: invalid username / password combination')
                
        jsonString = response_data.decode('utf8')
        jsonData = json.loads(jsonString)
    
        api_token = (jsonData['api_token'])

    '''
    print('u', user)
    print('p', password)
    print('t', api_token)
    '''
    
    data =  {
            'api_token': api_token
            }
    
    params = json.dumps(data)
    path = '/api/1.4/auth/session'
    url = 'http://%s%s'%(flashArray,path)

    # Perform action
    conn = http.client.HTTPSConnection(flashArray)
    conn.set_debuglevel(DEBUG_LEVEL)
    
    conn.request('POST', path, params, headers=hdrs)
    
    response = conn.getresponse()
    response_data = response.read()

    COOKIE = response.getheader('set-cookie')

    if DEBUG_LEVEL != 0:
        print('Status', response.status)
        print('Reason', response.reason)
        print('msg', response.msg)
        print('HTTP Header:', response.info())
        print('Content-Lenghth', response.getheader('Content-Length'))
        print('Cookie', COOKIE)

    if (response.reason) != 'OK':
        print(BANNER)
        sys.exit('Exiting: Unable to establish session')

    if VERBOSE_FLAG:
        print(BANNER)
        print(json.dumps(jsonData, sort_keys=False, indent=4))

    jsonString = response_data.decode('utf8')
    jsonData = json.loads(jsonString)

    name = (jsonData['username'])

    #array = purestorage.FlashArray(flashArray, user, password)

    print('Welcome', name)


def post_url(flashArray,path,params):
    # Set-up HTTP header
    userAgent = 'Jakarta Commons-HttpClient/3.1'
    hdrs= {'Content-Type' : 'application/json', 'User-agent' : userAgent, 'Cookie' : COOKIE}
    
    conn = http.client.HTTPSConnection(flashArray)
    conn.set_debuglevel(DEBUG_LEVEL)
    
    conn.request('POST', path, params, headers=hdrs)
    
    response = conn.getresponse()
    response_data = response.read()
    
    if DEBUG_LEVEL != 0:
        print('Response Status:', response.status)
        print('Reason:', response.reason)
        print('msg', response.msg)
        print('HTTP Header:', response.info())
        print('Content-Lenghth', response.getheader('Content-Length'))
        print('Cookie', COOKIE)
    
    jsonData = response_data.decode('utf8')
    return(jsonData)


def get_url(flashArray,path,params):
    # Set-up HTTP header
    userAgent = 'Jakarta Commons-HttpClient/3.1'
    hdrs= {'Content-Type' : 'application/json', 'User-agent' : userAgent, 'Cookie' : COOKIE}
    
    conn = http.client.HTTPSConnection(flashArray)
    conn.set_debuglevel(DEBUG_LEVEL)
    
    conn.request("GET", path, headers=hdrs)
    
    response = conn.getresponse()
    response_data = response.read()
    
    if DEBUG_LEVEL != 0:
        print('Response Status:', response.status)
        print('Reason:', response.reason)
        print('msg', response.msg)
        print('HTTP Header:', response.info())
        print(response.getheader('Content-Length'))
        print('Cookie:', COOKIE)
    
    jsonData = response_data.decode('utf8')
    return(jsonData)


def list_volumes(flashArray):
    data = ''
    params = json.dumps(data)
    
    path = '/api/1.4/volume?space=true'
    url = 'http://%s%s'%(flashArray,path)
    
    # Perform action
    #jsonData = array.list_volumes()
    
    jsonString = get_url(flashArray,path,params)
    jsonData = json.loads(jsonString)

    if VERBOSE_FLAG:
        print(BANNER)
        print(json.dumps(jsonData, sort_keys=False, indent=4))

    # Count of returned rows
    res = len(jsonData)

    if res == 0:
        print('No Volumes found')
    else:
        x = 0
        print(BANNER)
        print('{0:60} {1:>20} {2:>20}'.format('Volume Name', 'Size (GB)', 'Used (GB)'))
        print(BANNER)
        while (x<res):
            #
            name = (jsonData[x]['name'])
            size = (jsonData[x]['size'])
            used = (jsonData[x]['volumes'])
            
            sz = float(size)
            us = float(used)
            
            sizegb = round((sz/1024/1024/104),2)
            usedgb = round((us/1024/1024/104),2)
            
            print('{0:60} {1:20} {2:20}'.format(name, sizegb, usedgb))
 
            x = x + 1


def parsecl():
    usage = 'usage: %prog [options]'
    version = '%prog ' + VERSION
    description = "Please contact ron@purestorage.com for any assistance."

    parser = OptionParser(usage=usage, version=version, description=description)


    parser.add_option('-d', '--debug',
                      type = 'int',
                      dest = 'DEBUG_LEVEL',
                      default = 0,
                      help = 'Debug level, used for HTTP debugging')
    
    parser.add_option('-p', '--password',
                      action = 'store',
                      type = 'string',
                      dest = 'password',
                      help = 'Pure password')
     
    parser.add_option('-s', '--server',
                      action = 'store',
                      type = 'string',
                      dest = 'flashArray',
                      help = 'Pure FlashArray')
        
    parser.add_option('-t', '--token',
                      action = 'store',
                      type = 'string',
                      dest = 'api_token',
                      help = 'Pure Api Token')

    parser.add_option('-u', '--user',
                      action = 'store',
                      type = 'string',
                      dest = 'user',
                      help = 'Pure user name')

    parser.add_option('-v', '--verbose',
                      action = 'store_true',
                      dest = 'VERBOSE_FLAG',
                      default = False,
                      help = 'Verbose [default: %default]')

    (options, args) = parser.parse_args()

    '''
    print("Options:", options)
    print("Args:", args)
    '''

    if options.api_token and options.user:
        parser.error('options --token and --user are mutually exclusive')
    
    return(options)

def main():
    # Setup variables
    global DEBUG_LEVEL
    exit_code = 0

    # Check for command line parameters
    options = parsecl()
    password = options.password
    user = options.user
    flashArray = options.flashArray
    api_token = options.api_token
    DEBUG_LEVEL = options.DEBUG_LEVEL
    VERBOSE_FLAG = options.VERBOSE_FLAG
    
    if DEBUG_LEVEL != 0:
        print('Password', password)
        print('User', user)
        print('Flash Array', flashArray)
        print('Api Token', api_token)
        print('Debug Level:', DEBUG_LEVEL)

    if flashArray == None:
        sys.exit('Exiting: You must provide FlashArray details')

    if api_token == None and user == None:
        sys.exit('Exiting: You must provide either API Token details or username and password')

    if user and password == None:
        sys.exit('Exiting: You must provide password if using username')

    print(BANNER)
    print(HEADER + ' - ' + flashArray)
    print(strftime('%Y/%m/%d %H:%M:%S %Z', gmtime()))
    print(BANNER)

    # Create session
    create_session(flashArray, user, password, api_token)

    list_volumes(flashArray)

    # Close API session
    #array.invalidate_cookie()

    print(BANNER)
    print(strftime('%Y/%m/%d %H:%M:%S %Z', gmtime()))
    print(BANNER)
    sys.exit(exit_code)

main()


