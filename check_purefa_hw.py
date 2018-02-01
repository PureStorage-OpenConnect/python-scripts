#!/usr/bin/env python3
# Copyright (c) 2018 Pure Storage, Inc.
#
## Overview
#
# This short Nagios/Icinga plugin code shows  how to build a simple plugin to monitor Pure Storage FlashArrays.
# The Pure Storage Python REST Client is used to query the FlashArray occupancy indicators.
# Plugin leverages the remarkably helpful nagiosplugin library by Christian Kauhaus.
#
## Installation
#
# The scripo should be copied to the Nagios plugins directory on the machine hosting the Nagios server or the NRPE
# for example the /usr/lib/nagios/plugins folder.
# Change the execution rights of the program to allow the execution to 'all' (usually chmod 0755).
#
## Dependencies
#
#  nagiosplugin      helper Python class library for Nagios plugins by Christian Kauhaus (http://pythonhosted.org/nagiosplugin)
#  purestorage       Pure Storage Python REST Client (https://github.com/purestorage/rest-client)

__author__ = "Eugenio Grosso"
__copyright__ = "Copyright 2018, Pure Storage Inc."
__credits__ = "Christian Kauhaus"
__license__ = "Apache v2.0"
__version__ = "1.0"
__maintainer__ = "Eugenio Grosso"
__email__ = "geneg@purestorage.com"
__status__ = "Production"

"""Pure Storage FlashArray occupancy status

   Nagios plugin to retrieve the current status of hardware components from a Pure Storage FlashArray.
   Hardware status indicators are collected from the target FA using the REST call.
   The plugin has threew mandatory arguments:  'endpoint', which specifies the target FA, 'apitoken', which
   specifies the autentication token for the REST call session and 'component', that is the name of the
   hardware component to be monitored. The component must be specified using the internal naming schema of
   the Pure FlashArray: i.e CH0 for the main chassis, CH1 for the secondary chassis (shelf 1), CT0 for controller 0,i
   CT1 for controller 1i, CH0.NVB0 for the first NVRAM module, CH0.NVB1 for the second NVRAM module, CH0.BAY0 for
   the first flash module, CH0.BAY10 for the tenth flash module, CH1.BAY1, for the first flash module on the
   first additional shelf,...

"""

import argparse
import logging
import nagiosplugin
import purestorage
import urllib3


_log = logging.getLogger('nagiosplugin')

class PureFAhw(nagiosplugin.Resource):
    """Pure Storage FlashArray overall occupancy

    Calculates the overall FA storage occupancy

    """

    def __init__(self, endpoint, apitoken, component):
        self.endpoint = endpoint
        self.apitoken = apitoken
        self.component = component

    @property
    def name(self):
        return 'PURE_' + str(self.component)

    def get_perf(self):
        """Gets hardware element status from flasharray."""
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        fa = purestorage.FlashArray(self.endpoint, api_token=self.apitoken)
        fainfo = fa.get_hardware(component=self.component)
        fa.invalidate_cookie()
        return(fainfo)

    def probe(self):

        fainfo = self.get_perf()
        _log.debug('FA REST call returned "%s" ', fainfo)
        status = fainfo.get('status')
        if (status == 'ok') or (status == 'not_installed'):
            metric = nagiosplugin.Metric(self.component + ' status', 0, context='default' )
        else:
            metric = nagiosplugin.Metric(self.component + ' status', 1, context='default')
        return metric


def parse_args():
    argp = argparse.ArgumentParser()
    argp.add_argument('endpoint', help="FA hostname or ip address")
    argp.add_argument('apitoken', help="FA api_token")
    argp.add_argument('component', help="FA hardware component")
    argp.add_argument('-v', '--verbose', action='count', default=0,
                      help='increase output verbosity (use up to 3 times)')
    argp.add_argument('-t', '--timeout', default=30,
                      help='abort execution after TIMEOUT seconds')
    return argp.parse_args()


@nagiosplugin.guarded
def main():
    args = parse_args()
    check = nagiosplugin.Check( PureFAhw(args.endpoint, args.apitoken, args.component) )
    check.add(nagiosplugin.ScalarContext('default', 1, 1))
    check.main(args.verbose, args.timeout)

if __name__ == '__main__':
    main()
