from purity_fb import PurityFb, FileSystem, FileSystemSnapshot, SnapshotSuffix, rest
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
HEADER = 'Pure Storage Take FileSystem Snapshot (' + VERSION + ')'
BANNER = ('=' * 132)
DEBUG_LEVEL = 0
VERBOSE_FLAG = False
COOKIE = ''

def create_session(flashBlade, token ):

    fb = PurityFb(flashBlade)

    # Disable SSL verification
    fb.disable_verify_ssl()
    
    fb.login(token) # login to the array with your API_TOKEN

    return(fb)

def parsecl():
    usage = 'usage: %prog [options]'
    version = '%prog ' + VERSION
    description = "This python script creates a Pure Storage FlashBlade Snapshot, you need to provide FlashBlade details and file system name, the suffix is optional. This application has been developed using Pure Storage v1.8 FlashBlade RESTful Web Service interfaces. Please contact ron@purestorage.com for assistance."

    parser = OptionParser(usage=usage, version=version, description=description)

    parser.add_option('-s', '--server',
                      action = 'store',
                      type = 'string',
                      dest = 'flashBlade',
                      help = 'Pure FlashBlade')

    parser.add_option('-t', '--token',
                      action = 'store',
                      type = 'string',
                      dest = 'token',
                      help = 'Pure FlashBlade user token')

    parser.add_option('-f', '--filesys',
                      action = 'store',
                      type = 'string',
                      dest = 'filesys',
                      help = 'Pure FlashBlade file system')

    parser.add_option('-S', '--suffix',
                      action = 'store',
                      type = 'string',
                      dest = 'suffix',
                      help = 'Pure FlashBlade snapshot suffix')

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
    token = options.token
    filesys = options.filesys
    suffix = options.suffix
    VERBOSE_FLAG = options.VERBOSE_FLAG
    
    if VERBOSE_FLAG:
        print('FlashBlade:', flashBlade)
        print('FlashBlade Token:', token)
        print('File System:', filesys)
        print('Suffix:', suffix)
        print('Debug Level:', DEBUG_LEVEL)
        print('Verbose Flag:', VERBOSE_FLAG)

    if flashBlade == None:
        sys.exit('Exiting: You must provide FlashBlade details')

    if token == None:
        sys.exit('Exiting: You must provide FlashBlade token')

    if filesys == None:
        sys.exit('Exiting: You must specify a FlashBlade File System')

    print(BANNER)
    print(HEADER + ' - ' + flashBlade)
    print(strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))
    print(BANNER)

    # Create FlashBlade session
    fb = create_session(flashBlade, token)
    
    # Create FileSystem Snapshot

    if suffix == None:
       epoch = int(time.time())
       suffix = 'SNAP-' + str(epoch) 
    
    created = (strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))

    # Create Snaphost
    res = fb.file_system_snapshots.create_file_system_snapshots(sources=[filesys], suffix=SnapshotSuffix(suffix))
 
    if VERBOSE_FLAG:
        print(BANNER)
        print("res:", res.items)

    print('{0:40} {1:60} {2:20}'.format('Source', 'Suffix', 'Created'))
    print('{0:40} {1:60} {2:20}'.format(filesys, suffix, created))
 
    print(BANNER)
    sys.exit(exit_code)

main()


