"""
Get/Watch all information of a single key (full path in the Configuration Database).

Usage:
    ska-sdp (get | watch) [options] <key>
    ska-sdp (get | watch) (-h | --help)

Arguments:
    <key>       Key within the Config DB. Has to be the full path.
                To get the list of all keys:
                    ska-sdp list -a /

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output
"""
import logging
from docopt import docopt

LOG = logging.getLogger("ska-sdp")


def cmd_get(txn, path, args):
    """
    Get raw value from database.

    :param txn: Config object transaction
    :param path: Full path (i.e. key) within the config db to get the values of TODO: maybe rename to key?
    :param args: CLI input args
    """
    val = txn.raw.get(path)
    if args["--quiet"]:
        LOG.info(val)
    else:
        LOG.info("{} = {}".format(path, val))


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    args = docopt(__doc__, argv=argv)

    for txn in config.txn():
        cmd_get(txn, args["<key>"], args)

        if args["watch"]:
            txn.loop(wait=True)
