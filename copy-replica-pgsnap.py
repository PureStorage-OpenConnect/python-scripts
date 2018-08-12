#!/usr/bin/env python
# Copyright (c) 2018 Pure Storage, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
 Simple python program for restoring locally on the target FlashArray the volumes contained
 in a replica protection group. This action is particularly useful for a rapid restore
 in a disaster recovery situation.
 A temporary protection group is created on the FlashArray to host the volumes in order
 to perform a copy of the protection group snapshot. The temporary volumes is deleted and
 eradicated immediately after.
"""

from __future__ import print_function

__author__ = "Eugenio Grosso"
__copyright__ = "Copyright 2018, Pure Storage Inc."
__credits__ = ""
__license__ = "Apache v2.0"
__version__ = "0.1"
__maintainer__ = "Eugenio Grosso"
__email__ = "geneg@purestorage.com"
__status__ = "Development"


import purestorage
import urllib3
import argparse


def parse_args():
    argp = argparse.ArgumentParser()
    argp.add_argument('-e','--endpoint',
                      required=True,
                      action='store',
                      help="FA hostname or ip address")
    argp.add_argument('-t','--apitoken',
                      required=True,
                      action='store',
                      help="FA api_token")
    argp.add_argument('-s','--suffix',
                      required=False,
                      action='store',
                      help="Protection group snapshot to restore on this FA. If you specify just the pgname then the most recent snapshot is used.")
    argp.add_argument('-p','--pgroup',
                      required=True,
                      action='store',
                      help="Protection group to create/overwrite on this FA")
    return argp.parse_args()


def main():

    # Key function to retrieve the most recent snapshot
    def return_created(elem):
        return elem['created']

    args = parse_args()
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    vol_list = []
    vol_hg_list = []
    fainfo = {}
    pgsnap = args.pgroup

    if args.suffix:
        pgsnap = pgroup + '.' + args.suffix

    try:
        fa = purestorage.FlashArray(args.endpoint, api_token=args.apitoken)
        # Retrieve existing volumes already created from
        # the same protection group snapshot
        fainfo = fa.get_pgroup(args.pgroup)
        pgvol = fainfo['volumes']
        volumes = fa.list_volumes()
        for pv in pgvol:
            for v in volumes:
                if v['source'] == pv:
                    vol_list.append(v['name'])
                    break
        # Create temporay protection group to store
        # volumes
        tmp_pgroup = args.pgroup.split(':')[1] + '---tmp'
        fainfo = fa.list_pgroups()
        for pg in fainfo:
            if pg['name'] == tmp_pgroup:
                fa.destroy_pgroup(tmp_pgroup)
                fa.eradicate_pgroup(tmp_pgroup)
                break

        fa.create_pgroup(tmp_pgroup)
        for v in vol_list:
            fa.add_volume(v, tmp_pgroup)

        # Disconnect host group from target volumes.
        # This is required for the copy over to succeed
        for vol in vol_list:
            sh_conn = fa.list_volume_shared_connections(vol)
            if not sh_conn:
                continue
            vol_hg_list.append({'name': sh_conn[0]['name'],
                          'lun': sh_conn[0]['lun'],
                          'hgroup': sh_conn[0]['hgroup']})
            fa.disconnect_hgroup(sh_conn[0]['hgroup'], vol)
            print("Volume '" + vol + "' disconnected from host group '" + sh_conn[0]['hgroup'] + "'")

        # Retrieve the most recent snapshot. If the full name of as snapshot is provided
        # this search returns the very same name
        fainfo = fa.get_pgroup(pgsnap, snap=True)
        snap_sorted = sorted(fainfo, key=return_created, reverse=True)
        pgsnap = snap_sorted[0]['name']

        fa.create_pgroup(tmp_pgroup, source=pgsnap, overwrite=True)
        fa.destroy_pgroup(tmp_pgroup)
        fa.eradicate_pgroup(tmp_pgroup)
        print("Recovered volumes using pg snapshot '" + pgsnap + "'")

    except purestorage.PureError as e:
        print(e)
        return (-1)
    finally:
        # Reconnect volumes if we disconnected them before
        for vol in vol_hg_list:
            fa.connect_hgroup(vol['hgroup'], vol['name'], lun = vol['lun'])
            print("Volume '" + vol['name'] + "' reconnected to hostgroup '" + vol['hgroup'] + "'")

    fa.invalidate_cookie()


if __name__ == '__main__':
    main()

