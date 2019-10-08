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
from purity_fb import PurityFb, FileSystem, FileSystemSnapshot, SnapshotSuffix, rest

# Global Variables
VERSION = '1.0.0'
HEADER = 'Pure Storage Take FlashBlade Snapshot (' + VERSION + ')'
BANNER = ('=' * 132)
DEBUG_FLAG = False
VERBOSE_FLAG = False
COOKIE = ''

def parsecl():
    usage = 'usage: %prog [options]'
    version = '%prog ' + VERSION
    description = "This application has been developed using Pure Storage v1.8 RESTful Web Service interfaces. Developed and tested using Python 3.6.8. Please contact ron@purestorage.com for assistance."

    parser = OptionParser(usage=usage, version=version, description=description)


    parser.add_option('-d', '--debug',
                      action = 'store_true',
                      dest = 'DEBUG_FLAG',
                      default = False,
                      help = 'Debug [default: %default]')
    
    parser.add_option('-f', '--filesystem',
                      action = 'store',
                      type = 'string',
                      dest = 'fs',
                      help = 'FlashBlade File System')
        
    parser.add_option('-s', '--server',
                      action = 'store',
                      type = 'string',
                      dest = 'flashBlade',
                      help = 'FlashBlade array')
        
    parser.add_option('-t', '--token',
                      action = 'store',
                      type = 'string',
                      dest = 'API_TOKEN',
                      help = 'Pure API Token')

    parser.add_option('-S', '--suffix',
                      action = 'store',
                      type = 'string',
                      dest = 'suffix',
                      help = 'File system snapshot suffix')

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
    global DEBUG_FLAG
    exit_code = 0

    # Check for command line parameters
    options = parsecl()
    API_TOKEN = options.API_TOKEN
    flashBlade = options.flashBlade
    fs = options.fs
    suffix = options.suffix
    DEBUG_FLAG = options.DEBUG_FLAG
    VERBOSE_FLAG = options.VERBOSE_FLAG
    
    if DEBUG_FLAG:
        print('API Token:', API_TOKEN)
        print('FlashBlade:', flashBlade)
        print('File System:', fs)
        print('Suffix:', suffix)
        print('Debug Flag:', DEBUG_FLAG)
        print('Verbose Flag:', VERBOSE_FLAG)

    if flashBlade == None:
        sys.exit('Exiting: You must provide FlashBlade details')

    if API_TOKEN == None:
        sys.exit('Exiting: You must provide FlashBlade API Token details')

    if fs == None:
        sys.exit('Exiting: You must provide FlashBlade file system')

    print(BANNER)
    print(HEADER + ' - ' + flashBlade)
    print(strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))
    print(BANNER)

    # create PurityFb object for a certain array
    fb = PurityFb(flashBlade)
    # this is required for versions before Purity//FB 2.1.3 because they only supports self-signed
    # certificates. in later versions, this may be unnecessary if you have imported a certificate.
    fb.disable_verify_ssl()
    
    try:
        res= fb.login(API_TOKEN)
    except rest.ApiException as e:
        print("Exception when logging in to the array: %s\n" % e)

    if res:
        try:
            if suffix:
                # create a snapshot with suffix for flashblade file system
                res = fb.file_system_snapshots.create_file_system_snapshots(sources=[fs],
                                                                            suffix=SnapshotSuffix(suffix))
            else:
                # create a snapshot for the file system 
                res = fb.file_system_snapshots.create_file_system_snapshots(sources=[fs])

            if VERBOSE_FLAG:
                print(res)
            
            print('Snapshot created for', fs, 'suffix', res.items[0].suffix) 

        except rest.ApiException as e:
            print("Exception when creating file system snapshots: %s\n" % e)        

    fb.logout()
    print(BANNER)
    print(strftime('%d/%m/%Y %H:%M:%S %Z', gmtime()))
    print(BANNER)
    sys.exit(exit_code)

main()
