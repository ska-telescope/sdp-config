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
from docopt import docopt

from ska_sdp_config.cli import cmd_get


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    args = docopt(__doc__, argv=argv)

    for txn in config.txn():
        cmd_get(txn, args["<key>"], args)

        if args["watch"]:
            txn.loop(wait=True)
