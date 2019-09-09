"""
Create clones on a remote array of all volumes in a pgroup.

Download latest pypureclient release from:
    https://pypi.org/project/py-pure-client

Example usage:
         $ python clone_all_snapshots_in_pgroup.py --source pure001 --target pure002 --target-id-token eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImQ2ODNkOWZjLTY0MzUtNDQwOC1iMjEzLTc0ZGUwNTY0ODEzMSJ9.eyJhdWQiOiIxYTZiNjY1NS02ZTdmLTRkMjMtYTY4NC1lYjZiYzljZWNjYmMiLCJpc3MiOiJwZ0NsaWVudCIsInJvbGUiOiJhcnJheV9hZG1pbiIsImV4cCI6MTU5OTE3Mjg3NywiaWF0IjoxNTY4MDY4ODc3LCJ0eXAiOiJKV1QiLCJzdWIiOiJwdXJldXNlciJ9.G8aNq4Jz0PGnFoZD31Y9d_ux-fdHuzJB4R3QPl-zw4V8htB1MCwvQxKTCQ6F8uuhy61yCL18l6rqKmBcPhrrPDQCLF_lJsMBUNycJVQd-DnfWqYIzAzcpMPAf_zNHekEVXfJZd_VQ3Uv4YC2mVtPe6OKR3JiBy42bJ5tDcax4UrUDEPXg-V1QOWhmtycrYCQp2hfQnqtZMQhtOzrsJhN_9DXCpreasgKimBvWhMfbKZyJGdpELGJhO6ItcmeqdiSDSe-t-os4PYonNgB_we2IlpyDHQpQj1lCF5SSqaqFOrx1lyb-Sc0UXitKrSFs8oS5Rs8UXhN6h9gSb8T-v8sJg --source-api-token dfc11fc6-0287-fe15-c4f9-c4e5a7ce5d7d
         Enter name of source pgroup: pg1
         Found volumes in pg 'pg1': [u'vol1', u'vol2']
         Confirmed that script target is in pgroup targets
         Snapshotting pgroup 'pg1' and replicating now to pgroup targets '[{u'name': u'pure002', u'allowed': True}]'...
         Enter clone suffix (hit enter for no suffix): clone2
         Checking to see that replication has completed...
         Snapshot 'pure001:pg1.23.vol1': started 1568071967000, progress 0.0
         Snapshot 'pure001:pg1.23.vol1': started 1568071967000, progress 1.0
         Creating 'vol1-clone2' from 'pure001:pg1.23.vol1'
         Checking to see that replication has completed...
         Snapshot 'pure001:pg1.23.vol2': started 1568071967000, progress 1.0
         Creating 'vol2-clone2' from 'pure001:pg1.23.vol2'

If you get "PureError: Could not retrieve a new access token", then your
id_token is not valid.

"""
import argparse
import purestorage
import requests
import sys
import time

from pypureclient import flasharray
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from util import print_errs

# Making this script work with either python2 or 3
try:
    input = raw_input
except NameError:
    pass

"""

REST API CALLS
Separated so I can swap out 1.X and 2.X clients easily.

In this script, I have to make some calls in 1.X since they
aren't supported in 2.X yet.

"""
def get_volumes_in_pgroup(client_1x, pg_name):
    return client_1x.list_pgroups(names=pg_name)[0]["volumes"]

def get_pgroup_targets(client_1x, pg_name):
    return client_1x.list_pgroups(names=pg_name)[0]["targets"]

def replicate_now(client_1x, pg_name):
    return client_1x.create_pgroup_snapshot(pg_name, replicate_now=True)["name"]

def get_transfer_stats(client_2x, pg_vol_snap_name):
    """ Returns a tuple of (started time, progress) """
    resp = client_2x.get_volume_snapshots_transfer(names=pg_vol_snap_name)
    assert resp.status_code == 200, print_errs(resp)
    transfer_stats = list(resp.items)[0]
    return (transfer_stats.started, transfer_stats.progress)

def create_clone(client_2x, clone_name, pg_vol_snap_name):
    volume_body = flasharray.Volume(source={"name": pg_vol_snap_name})
    resp = client_2x.post_volumes(names=clone_name, volume=volume_body)
    assert resp.status_code == 200, print_errs(resp)

"""
SCRIPT FUNCTIONS
"""
def clone_new_volumes(target_client, source_array_name, source_snapshot_name, source_volumes, clone_suffix=None):
    # For each volume in the source pg snap, create a new volume with suffix clone_suffix
    for volume in source_volumes:
        full_pg_vol_snap_name = "{}:{}.{}".format(source_array_name, source_snapshot_name, volume)
        print("Checking to see that replication has completed...")
        progress = 0.0
        while progress < 1.0:
            transfer_stats = get_transfer_stats(target_client, full_pg_vol_snap_name)
            print("Snapshot '{}': started {}, progress {}".format(full_pg_vol_snap_name,
                transfer_stats[0], transfer_stats[1]))
            progress = transfer_stats[1]
            time.sleep(1)

        clone_name = "{}-{}".format(volume, clone_suffix) if clone_suffix else volume
        print("Creating '{}' from '{}'".format(clone_name, full_pg_vol_snap_name))
        create_clone(target_client, clone_name, full_pg_vol_snap_name)

def main(source, target, source_client, target_client):
    pg_name = input("Enter name of source pgroup: ")
    source_volumes = get_volumes_in_pgroup(source_client, pg_name)
    source_targets = get_pgroup_targets(source_client, pg_name)

    print("Found volumes in pg '{}': {}".format(pg_name, source_volumes))
    target_found = False
    for source_target in source_targets:
        if source_target["name"] == target:
            if not source_target["allowed"]:
                print("Target '{}' is not allowed; exiting...".format(
                    target))
                sys.exit(1)
            target_found = True

    if target_found:
        print("Confirmed that script target is in pgroup targets")
    else:
        print("Target '{}' is not in pgroup targets '{}'; exiting...".format(
            target, source_targets))
        sys.exit(1)

    print("Snapshotting pgroup '{}' and replicating now to pgroup targets '{}'...".format(
        pg_name, source_targets))
    source_snapshot_name = replicate_now(source_client, pg_name)

    clone_suffix = input("Enter clone suffix (hit enter for no suffix): ")
    clone_new_volumes(target_client, source, source_snapshot_name, source_volumes, clone_suffix)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Get all volumes in a pgroup, then snap/clone them to a remote target.')
    parser.add_argument('--source', help='Source array. PG Snapshot will be taken here.', required=True)
    parser.add_argument('--target', help='Target array. Clone volumes will be created here.', required=True)
    parser.add_argument('--source-api-token', help='1.X API token for source array', required=True)
    parser.add_argument('--target-id-token', help='OAuth2 identity token for target array', required=True)

    args = parser.parse_args()
    source_1x_client = purestorage.FlashArray(args.source, api_token=args.source_api_token)
    target_2x_client = flasharray.Client(target=args.target, id_token=args.target_id_token)

    main(args.source, args.target, source_1x_client, target_2x_client)
