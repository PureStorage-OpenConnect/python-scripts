"""
Useful utilities for the FA2.X python client.
"""

def print_errs(resp):
    for error in resp.errors:
        if error.context:
            return "error on {}: {}".format(error.context, error.message)
        return "error: {}".format(error.message)

