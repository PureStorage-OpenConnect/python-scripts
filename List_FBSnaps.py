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
HEADER = 'Pure Storage List FlashBlade Snapshots (' + VERSION + ')'
BANNER = ('=' * 132)
DEBUG_LEVEL = 0
VERBOSE_FLAG = False
XTOKEN = ''

def create_session(flashBlade, api_token):
    global XTOKEN

    # Set-up HTTP header
    userAgent = 'Jakarta Commons-HttpClient/3.1'
    hdrs= {'Content-Type' : 'application/json', 'User-agent' : userAgent, 'api-token' : api_token}
  
    data =  {
            } 

    params = json.dumps(data) 
    path = '/api/login'
    url = 'https://%s%s'%(flashBlade,path)

    # Perform action
    print('Attempting to create session')

    response = requests.post(url, params, headers=hdrs, verify=False)

    if DEBUG_LEVEL == 2:
        print('URL', url)
        print('respose', response)
        print('Status', response.status_code)
        print('Text', response.text)
        print('Data', response.json)
        print('HTTP Header:', response.headers)
        print('x-auth-token:', response.headers['x-auth-token'])
        print('')

    if (response):
        print(BANNER)
        XTOKEN = response.headers['x-auth-token']
    else:
        print(BANNER)
        sys.exit('Exiting: Unable to establish session')

    jsonString = response.text
    jsonData = json.loads(jsonString)

    if VERBOSE_FLAG:
        print(BANNER)
        print(json.dumps(jsonData, sort_keys=False, indent=4))

    name = (jsonData['username'])
    welcome = 'Welcome ' + name
    print(welcome)


def post_url(flashBlade,path,params):
    # Set-up HTTP header
    userAgent = 'Jakarta Commons-HttpClient/3.1'
    hdrs= {'Content-Type' : 'application/json', 'User-agent' : userAgent, 'x-auth-token' : XTOKEN}
    url = 'https://%s%s'%(flashBlade,path)
    
    # Perform action
    response = requests.post(url, params, headers=hdrs, verify=False)
    
    if DEBUG_LEVEL != 0:
        print('URL',url)
        print('Response Status:', response.status_code)
        print('Text', response.text)
        print('Data', response.json)
        print('HTTP Header:', response.headers)
        print('')
   
    jsonString = response.text
    jsonData = json.loads(jsonString)
    return(jsonData)


def get_url(flashBlade,path,params):
    # Set-up HTTP header
    userAgent = 'Jakarta Commons-HttpClient/3.1'
    hdrs= {'Content-Type' : 'application/json', 'User-agent' : userAgent, 'x-auth-token' : XTOKEN}
    url = 'https://%s%s'%(flashBlade,path)
    payload = params

    # Perform action
    response = requests.get(url, headers=hdrs, verify=False)
    
    if DEBUG_LEVEL != 0:
        print('URL', url)
        print('Response Status:', response.status_code)
        print('Text', response.text)
        print('Data', response.json)
        print('HTTP Header:', response.headers)
    
    jsonString = response.text
    jsonData = json.loads(jsonString)
    return(jsonData)


def list_fssnaps(flashBlade,fsname,limit):
    data = ''
    params = json.dumps(data)
    
    if fsname == '':
        path = '/api/1.8/file-system-snapshots?sort=name&limit=%s'%(limit)
    else:
        path = '/api/1.8/file-system-snapshots?sort=created&names_or_sources=%s'%(fsname)

    # Perform action
    jsonData = get_url(flashBlade,path,params)

    r =  str(jsonData)

    if VERBOSE_FLAG:
        print(BANNER)
        print(json.dumps(jsonData, sort_keys=False, indent=4))

    # Count of returned rows
    res = len(jsonData['items'])

    if res == 0:
        print('No File System Snapshots found')
    else:
        print('number of snaps:', res)
        x = 0
        print(BANNER)
        print('{0:40} {1:60} {2:20}'.format('File System', 'File System Snapshots', 'Created'))
        print(BANNER)
        while (x<res):
            #
            source = (jsonData['items'][x]['source'])
            name = (jsonData['items'][x]['name'])
            cdate = (jsonData['items'][x]['created'])
            c1 = str(cdate)
            epoch = int(c1[0:10])
            created = time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime(epoch))

            print('{0:40} {1:60} {2:20}'.format(source, name, created))
 
            x = x + 1

def parsecl():
    usage = 'usage: %prog [options]'
    version = '%prog ' + VERSION
    description = "This program returns Snapshots for given File System. Please contact ron@purestorage.com for any assistance."

    parser = OptionParser(usage=usage, version=version, description=description)

    parser.add_option('-d', '--debug',
                      type = 'int',
                      dest = 'DEBUG_LEVEL',
                      default = 0,
                      help = 'Debug level, used for HTTP debugging')
    
    parser.add_option('-l', '--limit',
                      type = 'int',
                      dest = 'limit',
                      default = 999,
                      help = 'Limit number of responses [default: %default]')
    
    parser.add_option('-p', '--password',
                      action = 'store',
                      type = 'string',
                      dest = 'password',
                      help = 'Pure password')
     
    parser.add_option('-f', '--fsname',
                      action = 'store',
                      type = 'string',
                      dest = 'fsname',
                      default = '',
                      help = 'File System name')
     
    parser.add_option('-s', '--server',
                      action = 'store',
                      type = 'string',
                      dest = 'flashBlade',
                      help = 'Pure FlashArray')
        
    parser.add_option('-t', '--token',
                      action = 'store',
                      type = 'string',
                      dest = 'api_token',
                      help = 'Pure Api Token')

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

    return(options)

def main():
    # Setup variables
    global DEBUG_LEVEL
    global VERBOSE_FLAG
    exit_code = 0

    # Check for command line parameters
    options = parsecl()
    flashBlade = options.flashBlade
    limit = options.limit
    fsname = options.fsname
    api_token = options.api_token
    DEBUG_LEVEL = options.DEBUG_LEVEL
    VERBOSE_FLAG = options.VERBOSE_FLAG
    
    if DEBUG_LEVEL != 0:
        print('Flash Blade:', flashBlade)
        print('File System:', fsname)
        print('Limit:', limit)
        print('Api Token:', api_token)
        print('Debug Level:', DEBUG_LEVEL)
        print('Verbose Flag:', VERBOSE_FLAG)

    if flashBlade == None:
        sys.exit('Exiting: You must provide FlashBlade details')

    if api_token == None:
        sys.exit('Exiting: You must provide an API Token')


    print(BANNER)
    print(HEADER + ' - ' + flashBlade)
    print(strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))
    print(BANNER)

    # Create session
    create_session(flashBlade, api_token)

    list_fssnaps(flashBlade,fsname,limit)

    print(BANNER)
    print(strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))
    print(BANNER)
    sys.exit(exit_code)

main()
