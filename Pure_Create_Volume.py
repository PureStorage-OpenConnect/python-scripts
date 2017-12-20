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
VERSION = '1.1.0'
HEADER = 'Pure Storage Create Volume (' + VERSION + ')'
BANNER = ('=' * 132)
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
        
    parser.add_option('-S', '--size',
                      action = 'store',
                      type = 'string',
                      dest = 'size',
                      help = 'Volume size S,K,M,G,T,P')
                      
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

    parser.add_option('-V', '--volume',
                      action = 'store',
                      dest = 'volume',
                      default = False,
                      help = 'Volume name')

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
    volsize = options.size
    volume = options.volume
    DEBUG_LEVEL = options.DEBUG_LEVEL
    VERBOSE_FLAG = options.VERBOSE_FLAG
    
    if DEBUG_LEVEL != 0:
        print('Password', password)
        print('User', user)
        print('Flash Array', flashArray)
        print('Volume name', volume)
        print('Volume size', volsize)
        print('Debug Level:', DEBUG_LEVEL)

    if flashArray == None:
        sys.exit('Exiting: You must provide FlashArray details')

    if user and password == None:
        sys.exit('Exiting: You must provide password if using username')

    print(BANNER)
    print(HEADER + ' - ' + flashArray)
    print(strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))
    print(BANNER)

    # Create session
    array = create_session(flashArray, user, password)

    # Create Volume
    jsonData = array.create_volume(volume, size=volsize)

    if VERBOSE_FLAG:
        print(BANNER)
        print(json.dumps(jsonData, sort_keys=False, indent=4))
    
 
    volname = (jsonData['name'])
    volsize = (jsonData['size'])
    cdate = (jsonData['created'])

    c1 = cdate[0:10]
    c2 = cdate[11:19]
    c3 = c1 + ' ' + c2
    c4 = strptime(c3,'%Y-%m-%d %H:%M:%S')
    created = strftime('%d/%m/%Y %H:%M:%S', c4)

    print('{0:20} {1:>20} {2:20}'.format('Name', 'Size', 'Created'))
    print('{0:20} {1:20} {2:20}'.format(volname, volsize, created))

    # Close API session
    array.invalidate_cookie()

    print(BANNER)
    print(strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))
    print(BANNER)
    sys.exit(exit_code)

main()


