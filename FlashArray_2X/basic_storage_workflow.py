"""

Download latest pypureclient release from:
    https://pypi.org/project/py-pure-client

Example usage:
         $ python basic_storage_workflow.py --target pure001 --id-token eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImRjMTIzY2EwLTllNDktNDhiZS1iNWQwLTViMGVjMTUxODIwYiJ9.eyJhdWQiOiJmMDI5MGUzNS1hODFlLTQyNzQtODIyYy1mZTMwNmI2NzAxMjUiLCJpc3MiOiJjbGllbnQiLCJyb2xlIjoiYXJyYXlfYWRtaW4iLCJleHAiOjE1OTkxNjUxNjEsImlhdCI6MTU2ODA2MTE2MSwidHlwIjoiSldUIiwic3ViIjoicHVyZXVzZXIifQ.iKujyQZoVRmGLpjxfySBlHfCTq3APNw6mgkMOv35DQ1_MjR-w1r0Rx62XTimLqOKc5ksqhEfvIC62iDJmK70jNPF3XePnMPlpbTmzMKuzGs1xdbVNyqQOCmL4Fk61Wa67frF789PoE0aYtS8Z3vMAYspLnSAcAQk0VGXkaPrbSunEuIABbFgBiqQLAaudPn1Ulm9CA8anqm3X2cjaMWBI8Z3VofiBPDTOGwE9UOMp27zZpCEygBHbuCIBXRhHca_2ycBQ5WbJGF8l3OtrVOva_mFWk2GFWXxhdUZSPeEl1MxNNWiXwL8Y5vGJGiGpnAtucQKBV7LKjYSF9S38q8pjA
         Created volume v3 with provisioned size 1048576
         Created volume v2 with provisioned size 1048576
         Created volume v1 with provisioned size 1048576
         Created host h1 with iqns ['iqn.2001-04.com.ex:sn-a8675308']
         Created connection between host h1 and volume v3
         Created connection between host h1 and volume v2
         Created connection between host h1 and volume v1
         Deleted connections
         Deleted host h1
         Set volume v3 destroyed to True
         Set volume v2 destroyed to True
         Set volume v1 destroyed to True
         Eradicated volumes v1,v2,v3

If you get "PureError: Could not retrieve a new access token", then your
id_token is not valid.

"""
import argparse

from pypureclient import flasharray
from util import print_errs

VOLUME_NAMES = "v1,v2,v3"
HOST_NAME = "h1"
HOST_IQN = "iqn.2001-04.com.ex:sn-a8675308"

def setup(client):
    # Create 3 volumes
    volume_body = flasharray.Volume(provisioned=1048576)
    resp = client.post_volumes(names=VOLUME_NAMES, volume=volume_body)
    assert resp.status_code == 200, print_errs(resp)
    for volume in list(resp.items):
        print("Created volume {} with provisioned size {}".format(volume.name, volume.provisioned))

    # Create 1 host
    resp = client.post_hosts(names=HOST_NAME, host=flasharray.Host(iqns=[HOST_IQN]))
    assert resp.status_code == 200, print_errs(resp)
    for host in list(resp.items):
        print("Created host {} with iqns {}".format(host.name, host.iqns))

    # Connect volumes to this host
    resp = client.post_connections(host_names=HOST_NAME, volume_names=VOLUME_NAMES)
    assert resp.status_code == 200
    for connection in list(resp.items):
        print("Created connection between host {} and volume {}".format(connection.host.name, connection.volume.name))


def cleanup(client):
    resp = client.delete_connections(host_names=HOST_NAME, volume_names=VOLUME_NAMES)
    assert resp.status_code == 200, print_errs(resp)
    print("Deleted connections")

    resp = client.delete_hosts(names=HOST_NAME)
    assert resp.status_code == 200, print_errs(resp)
    print("Deleted host {}".format(HOST_NAME))

    destroy_patch = flasharray.Volume(destroyed=True)
    resp = client.patch_volumes(names=VOLUME_NAMES, volume=destroy_patch)
    assert resp.status_code == 200, print_errs(resp)
    for volume in list(resp.items):
        print("Set volume {} destroyed to {}".format(volume.name, volume.destroyed))

    resp = client.delete_volumes(names=VOLUME_NAMES)
    assert resp.status_code == 200, print_errs(resp)
    print("Eradicated volumes {}".format(VOLUME_NAMES))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', help='FlashArray to run script against', required=True)
    parser.add_argument('--id-token', help='OAuth2 identity token', required=True)

    args = parser.parse_args()
    client = flasharray.Client(target=args.target, id_token=args.id_token)
    try:
        setup(client)
    finally:
        cleanup(client)
