import purestorage
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
HEADER = 'Pure Storage Simple Create Volume (' + VERSION + ')'
BANNER = ('=' * 100)
DEBUG_LEVEL = 0
VERBOSE_FLAG = False
COOKIE = ''

def create_session(flashArray, user, password):

    jsonData = purestorage.FlashArray(flashArray, user, password)
    return(jsonData)

def parsecl():
    usage = 'usage: %prog [options]'
    version = '%prog ' + VERSION
    description = "This application has been developed using Pure Storage v1.4 RESTful Web Service interfaces. Developed and tested using Python 3.6 on Mac OS 10.12. Please contact ron@purestorage.com for assistance."

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
    DEBUG_LEVEL = options.DEBUG_LEVEL
    
    if DEBUG_LEVEL != 0:
        print('Password', password)
        print('User', user)
        print('Flash Array', flashArray)
        print('Debug Level:', DEBUG_LEVEL)

    if flashArray == None:
        sys.exit('Exiting: You must provide FlashArray details')

    if user and password == None:
        sys.exit('Exiting: You must provide password if using username')

    print(BANNER)
    print(HEADER + ' - ' + flashArray)
    print(strftime('%Y/%m/%d %H:%M:%S %Z', gmtime()))
    print(BANNER)

    # Create session
    array = create_session(flashArray, user, password)

    jsonData = array.list_volumes()
    print(json.dumps(jsonData, sort_keys=False, indent=4))

    # Close API session
    array.invalidate_cookie()

    print(BANNER)
    print(strftime('%Y/%m/%d %H:%M:%S %Z', gmtime()))
    print(BANNER)
    sys.exit(exit_code)

main()


