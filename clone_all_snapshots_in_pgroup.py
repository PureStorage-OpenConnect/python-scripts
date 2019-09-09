"""
Create clones on a remote array of all volumes in a pgroup.

Example usage:
     $ python clone_all_snapshots_in_pgroup.py --source pure001 --target pure002 --source-api-token 148b2cca-264d-16ea-a1c9-6ff5fa03c3b4 --target-api-token f5f64bc2-2502-b0f0-30d6-a7408d1ed039
     Enter name of source pgroup: pg1
     Found volumes in pg 'pg1': [u'v1', u'v2', u'v3']
     Confirmed that script target is in pgroup targets
     Snapshotting pgroup 'pg1' and replicating now to pgroup targets '[{u'name': u'pure002', u'allowed': True}]'...
     Enter clone suffix (hit enter for no suffix): clone
     Checking to see that replication has completed...
     Snapshot 'pure001:pg1.5.v1': started 2019-09-10T00:03:27Z, progress 1.0
     Creating 'v1-clone' from 'pure001:pg1.5.v1'
     Checking to see that replication has completed...
     Snapshot 'pure001:pg1.5.v2': started 2019-09-10T00:03:27Z, progress 1.0
     Creating 'v2-clone' from 'pure001:pg1.5.v2'
     Checking to see that replication has completed...
     Snapshot 'pure001:pg1.5.v3': started 2019-09-10T00:03:27Z, progress 1.0
     Creating 'v3-clone' from 'pure001:pg1.5.v3'
"""
import argparse
import purestorage
import requests
import sys
import time

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Making this script work with either python2 or 3
try:
    input = raw_input
except NameError:
    pass


"""
REST API CALLS
"""
def get_volumes_in_pgroup(client, pg_name):
    return client.list_pgroups(names=pg_name)[0]["volumes"]

def get_pgroup_targets(client, pg_name):
    return client.list_pgroups(names=pg_name)[0]["targets"]

def replicate_now(client, pg_name):
    return client.create_pgroup_snapshot(pg_name, replicate_now=True)["name"]

def get_transfer_stats(client, pg_vol_snap_name):
    """ Returns a tuple of (started time, progress) """
    transfer_stats = client.list_volumes(names=pg_vol_snap_name, snap=True, transfer=True)[0]
    return (transfer_stats["started"], transfer_stats["progress"])

def create_clone(client, clone_name, pg_vol_snap_name):
    client.copy_volume(pg_vol_snap_name, clone_name)

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
    parser.add_argument('--target-api-token', help='1.X API token for target array', required=True)

    args = parser.parse_args()
    source_client = purestorage.FlashArray(args.source, api_token=args.source_api_token)
    target_client = purestorage.FlashArray(args.target, api_token=args.target_api_token)

    main(args.source, args.target, source_client, target_client)
