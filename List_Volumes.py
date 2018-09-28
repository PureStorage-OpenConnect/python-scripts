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
VERSION = '1.1.0'
DEFAULT_API_VERSION = '1.12'
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
        path = '/api' + API_VERSION + '/auth/apitoken'
        url = 'https://%s%s'%(flashArray,path)
    
        # Perform action
        response = requests.post(url, params, headers=hdrs, verify=False)

        COOKIE = response.cookies
    
        if DEBUG_LEVEL == 2:
            print('Status', response.status_code)
            print('Reason', response.reason)
            print('Text', response.text)
            print('Data', response.json)
            print('HTTP Header:', response.headers)
            print('Cookie', COOKIE)
            print('')
    
        if (response.reason) != 'OK':
            print(BANNER)
            sys.exit('Exiting: invalid username / password combination')
                
        jsonString = response.text
        jsonData = json.loads(jsonString)
    
        api_token = (jsonData['api_token'])

    data =  {
            'api_token': api_token
            }
    
    params = json.dumps(data)
    path = '/api/'+ API_VERSION + '/auth/session'
    url = 'https://%s%s'%(flashArray,path)

    # Perform action
    print('Attempting to create session')

    response = requests.post(url, params, headers=hdrs, verify=False)

    COOKIE = response.cookies

    if DEBUG_LEVEL == 2:
        print('Status', response.status_code)
        print('Reason', response.reason)
        print('Text', response.text)
        print('Data', response.json)
        print('HTTP Header:', response.headers)
        print('Cookie', COOKIE)
        print('')

    if (response.reason) != 'OK':
        print(BANNER)
        sys.exit('Exiting: Unable to establish session')

    jsonString = response.text
    jsonData = json.loads(jsonString)

    if VERBOSE_FLAG:
        print(BANNER)
        print(json.dumps(jsonData, sort_keys=False, indent=4))

    name = (jsonData['username'])
    print('Welcome', name)


def post_url(flashArray,path,params):
    # Set-up HTTP header
    userAgent = 'Jakarta Commons-HttpClient/3.1'
    hdrs= {'Content-Type' : 'application/json', 'User-agent' : userAgent}
    url = 'https://%s%s'%(flashArray,path)
    
    # Perform action
    response = requests.post(url, params, headers=hdrs, cookie=COOKIE, verify=False)
    
    if DEBUG_LEVEL != 0:
        print('Response Status:', response.status_code)
        print('Reason:', response.reason)
        print('Text', response.text)
        print('Data', response.json)
        print('HTTP Header:', response.headers)
        print('Cookie', COOKIE)
        print('')
   
    jsonString = response.text
    jsonData = json.loads(jsonString)
    return(jsonData)


def get_url(flashArray,path,params):
    # Set-up HTTP header
    userAgent = 'Jakarta Commons-HttpClient/3.1'
    hdrs= {'Content-Type' : 'application/json', 'User-agent' : userAgent}
    url = 'https://%s%s'%(flashArray,path)
    payload = params

    # Perform action
    response = requests.get(url, headers=hdrs, cookies=COOKIE, verify=False)
    
    if DEBUG_LEVEL != 0:
        print('Response Status:', response.status_code)
        print('Reason:', response.reason)
        print('Text', response.text)
        print('Data', response.json)
        print('HTTP Header:', response.headers)
        print('Cookie:', COOKIE)
    
    jsonString = response.text
    jsonData = json.loads(jsonString)
    return(jsonData)


def list_volumes(flashArray):
    data = ''
    params = json.dumps(data)
    
    path = '/api/' + API_VERSION + '/volume?space=true'
    
    # Perform action
    jsonData = get_url(flashArray,path,params)

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

    parser.add_option('-V', '--apiversion',
                      action = 'store',
                      type = 'string',
                      dest = 'API_VERSION',
                      help = 'Pure FlashArray API Version')

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
    global VERBOSE_FLAG
    global API_VERSION
    exit_code = 0

    # Check for command line parameters
    options = parsecl()
    password = options.password
    user = options.user
    flashArray = options.flashArray
    api_token = options.api_token
    DEBUG_LEVEL = options.DEBUG_LEVEL
    VERBOSE_FLAG = options.VERBOSE_FLAG
    API_VERSION = options.API_VERSION
    
    if DEBUG_LEVEL != 0:
        print('Password', password)
        print('User', user)
        print('Flash Array', flashArray)
        print('Api Token', api_token)
        print('Debug Level:', DEBUG_LEVEL)
        print('Verbose Flag:', VERBOSE_FLAG)

    if flashArray == None:
        sys.exit('Exiting: You must provide FlashArray details')

    if API_VERSION == None:
        API_VERSION = DEFAULT_API_VERSION

    if api_token == None and user == None:
        sys.exit('Exiting: You must provide either API Token details or username and password')

    if user and password == None:
        sys.exit('Exiting: You must provide password if using username')

    print(BANNER)
    print(HEADER + ' - ' + flashArray)
    print(strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))
    print(BANNER)

    # Create session
    create_session(flashArray, user, password, api_token)

    list_volumes(flashArray)

    print(BANNER)
    print(strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))
    print(BANNER)
    sys.exit(exit_code)

main()
