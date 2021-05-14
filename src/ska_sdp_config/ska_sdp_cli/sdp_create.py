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
    ska-sdp create pb my_new_pb '{"test": true}'
    Result in the config db:
        key: /pb/my_new_pb
        value: {"test": true}
"""
import logging
from docopt import docopt

LOG = logging.getLogger("ska-sdp")


def cmd_create(txn, path, value, _args):
    """
    Create raw key.

    :param txn: Config object transaction
    :param path: key to create / path within the config db to be created TODO: rename to key?
    :param value: value of new key to be added
    :param _args: CLI input args TODO: remove, not used, why is it here?
    """
    txn.raw.create(path, value)


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

    LOG.info("%s created", path)
