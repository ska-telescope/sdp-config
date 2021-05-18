"""
Get/Watch all information of a single key (full path in the Configuration Database).

Usage:
    ska-sdp (get|watch) [options] <key>
    ska-sdp (get|watch) [options] pb <pb_id>
    ska-sdp (get|watch) (-h|--help)

Arguments:
    <key>       Key within the Config DB.
                To get the list of all keys:
                    ska-sdp list -a
    <pb_id>     Processing block id to list all entries and their values for.
                Else, use key to get the value of a specific pb.

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output
"""
import logging
from docopt import docopt

LOG = logging.getLogger("ska-sdp")


def cmd_get(txn, key, args):
    """
    Get raw value from database.

    :param txn: Config object transaction
    :param key: Key within the Config DB to get the values of
    :param args: CLI input args
    """
    val = txn.raw.get(key)
    if args["--quiet"]:
        LOG.info(val)
    else:
        LOG.info("{} = {}".format(key, val))


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    args = docopt(__doc__, argv=argv)

    if args["<key>"]:
        for txn in config.txn():
            cmd_get(txn, args["<key>"], args)

            if args["watch"]:
                txn.loop(wait=True)

    elif args["pb"]:
        for txn in config.txn():
            keys = txn.raw.list_keys("/pb", recurse=8)
            for k in keys:
                if args["<pb_id>"] in k:
                    cmd_get(txn, k, args)

            if args["watch"]:
                txn.loop(wait=True)
