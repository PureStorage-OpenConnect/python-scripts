#!/usr/bin/env python
# Copyright (c) 2018 Pure Storage, Inc.
#
## Overview
#
# This short Nagios/Icinga plugin code shows  how to build a simple plugin to monitor Pure Storage FlashArrays.
# The Pure Storage Python REST Client is used to query the FlashArray performance counters. An optional parameter
# allow to check a single volume instead than the whole flasharray
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

"""Pure Storage FlashArray performance indicators

   Nagios plugin to retrieve the six (6) basic KPIs from a Pure Storage FlashArray.
   Bandwidth counters (read/write), IOPs counters (read/write) and latency (read/write) are collected from the
   The plugin has two mandatory arguments:  'endpoint', which specifies the target FA and 'apitoken', which
   specifies the autentication token for the REST call session. A third optional parameter, 'volname' can
   be used to check a specific named volume.
   target FA using the REST call.
   The plugin accepts multiple warning and critical threshold parameters in a positional fashion:
      1st threshold refers to write latency
      2nd threshold refers to read latency
      3rd threshold refers to write bandwidth
      4th threshold refers to read bandwidth
      5th threshold refers to write IOPS
      6th threshold refers to read IOPS

"""

import argparse
import logging
import nagiosplugin
import purestorage
import urllib3


_log = logging.getLogger('nagiosplugin')


class PureFAperf(nagiosplugin.Resource):
    """Pure Storage FlashArray performance indicators

    Gets the six global KPIs of the flasharray and stores them in the
    metric objects
    """

    def __init__(self, endpoint, apitoken, volname=None):
        self.endpoint = endpoint
        self.apitoken = apitoken
        self.volname = volname

    @property
    def name(self):
        if (self.volname is None):
            return 'PURE_FA_PERF'
        else:
            return 'PURE_VOL_PERF'

    def get_perf(self):
        """Gets performance counters from flasharray."""
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        fa = purestorage.FlashArray(self.endpoint, api_token=self.apitoken)
        if (self.volname is None):
            fainfo = fa.get(action='monitor')[0]
        else:
            fainfo = fa.get_volume(self.volname, action='monitor')[0]
        fa.invalidate_cookie()
        return(fainfo)

    def probe(self):

        fainfo = self.get_perf()
        _log.debug('FA REST call returned "%s" ', fainfo)
        wlat = int(fainfo.get('usec_per_write_op'))
        rlat = int(fainfo.get('usec_per_read_op'))
        wbw = int(fainfo.get('input_per_sec'))
        rbw = int(fainfo.get('output_per_sec'))
        wiops = int(fainfo.get('writes_per_sec'))
        riops = int(fainfo.get('reads_per_sec'))
        if (self.volname is None):
            mlabel = 'FA '
        else:
            mlabel = self.volname + ' '

        metrics = [
                    nagiosplugin.Metric(mlabel + 'wlat', wlat, 'us', min=0, context='wlat'),
                    nagiosplugin.Metric(mlabel + 'rlat', rlat, 'us', min=0, context='wlat'),
                    nagiosplugin.Metric(mlabel + 'wbw', wbw, 'B/s', min=0, context='wbw'),
                    nagiosplugin.Metric(mlabel + 'rbw', rbw, 'B/s', min=0, context='rbw'),
                    nagiosplugin.Metric(mlabel + 'wiops', wiops, 'wr/s', min=0, context='wiops'),
                    nagiosplugin.Metric(mlabel + 'riops', riops, 'rd/s', min=0, context='riops')
                  ]
        return metrics


def parse_args():
    argp = argparse.ArgumentParser()
    argp.add_argument('endpoint', help="FA hostname or ip address")
    argp.add_argument('apitoken', help="FA api_token")
    argp.add_argument('--vol', help="FA volme. If omitted the whole FA performance counters are checked")
    argp.add_argument('--tw', '--ttot-warning', metavar='RANGE[,RANGE,...]',
                      type=nagiosplugin.MultiArg, default='',
                      help="positional thresholds: write_latency, read_latenxy, write_bandwidth, read_bandwidth, write_iops, read_iops")
    argp.add_argument('--tc', '--ttot-critical', metavar='RANGE[,RANGE,...]',
                      type=nagiosplugin.MultiArg, default='',
                      help="positional thresholds: write_latency, read_latenxy, write_bandwidth, read_bandwidth, write_iops, read_iops")
    argp.add_argument('-v', '--verbose', action='count', default=0,
                      help='increase output verbosity (use up to 3 times)')
    argp.add_argument('-t', '--timeout', default=30,
                      help='abort execution after TIMEOUT seconds')
    return argp.parse_args()


@nagiosplugin.guarded
def main():
    args = parse_args()
    check = nagiosplugin.Check( PureFAperf(args.endpoint, args.apitoken, args.vol) )
    check.add(nagiosplugin.ScalarContext('wlat', args.tw[0], args.tc[0]))
    check.add(nagiosplugin.ScalarContext('rlat', args.tw[1], args.tc[1]))
    check.add(nagiosplugin.ScalarContext('wbw', args.tw[2], args.tc[2]))
    check.add(nagiosplugin.ScalarContext('rbw', args.tw[3], args.tc[3]))
    check.add(nagiosplugin.ScalarContext('wiops', args.tw[4], args.tc[4]))
    check.add(nagiosplugin.ScalarContext('riops', args.tw[5], args.tc[5]))
    check.main(args.verbose, args.timeout)

if __name__ == '__main__':
    main()
