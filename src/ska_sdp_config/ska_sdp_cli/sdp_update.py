"""
Update the value of a single key (full path in the Configuration Database).
Can either update from CLI, or edit via a text editor.

Usage:
    ska-sdp update [options] <key> <value>
    ska-sdp edit <key>
    ska-sdp (update | edit) (-h | --help)

Arguments:
    <key>       Key within the Config DB. Has to be the full path.
                To get the list of all keys:
                    ska-sdp list -a /
    <value>     Value to update the Key with.

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output

Note:
    ska-sdp edit needs an environment variable defined:
        EDITOR: Has to match the executable of an existing text editor
                Recommended: vi, vim, nano (i.e. command line-based editors)
        Example: EDITOR=vi ska-sdp edit <key>
"""
import logging

from docopt import docopt
from ska_sdp_config.cli import cmd_update, cmd_edit

LOG = logging.getLogger("ska-sdp")


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    args = docopt(__doc__, argv=argv)
    key = args["<key>"]

    for txn in config.txn():
        if args["update"]:
            cmd_update(txn, key, args["<value>"], args)

        if args["edit"]:
            cmd_edit(txn, key)

    LOG.info("%s updated.", key)
