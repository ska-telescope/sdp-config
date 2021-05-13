"""
Create a new, raw, key-value pair in the Configuration Database.

Usage:
    ska-sdp create [options] pb <key> <value>
    ska-sdp create [options] workflow <key> <value>
    ska-sdp create (-h | --help)

Arguments:
    <key>      Key to be created in the Config DB.
    <value>    Value belonging to that key.

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output

Example:
    ska-sdp create pb my_new_pb '{test: true}'
    Result in the config db:
        key: /pb/my_new_pb
        value: {test: true}
"""
from docopt import docopt

from ska_sdp_config.cli import cmd_create


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    # TODO: should this create not do processing blocks?
    # TODO: should there be checks, things that should not be created?
    args = docopt(__doc__, argv=argv)

    object_dict = {"pb": args["pb"], "workflow": args["workflow"]}

    path = "/"

    for k, v in object_dict.items():
        if v:
            path = path + k
            break  # only one can be true, or none

    path = path + "/" + args["<key>"]

    for txn in config.txn():
        cmd_create(txn, path, args["<value>"], args)
