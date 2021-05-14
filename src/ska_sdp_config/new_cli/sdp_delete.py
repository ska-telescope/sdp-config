"""
Delete a key from the Configuration Database.

Usage:
    ska-sdp delete (-a | --all) (pb | workflow)
    ska-sdp delete [-R -q] <path>
    ska-sdp delete (-h | --help)

Arguments:
    <path>        Path within the Config DB. For root: /

Options:
    -R            Recursive delete: delete everything within given path
                  If -R is not used, <path> has to match the exact key (full path) that has to be deleted
                  To get the list of all keys:
                    ska-sdp list -a /
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output
"""
import logging

from docopt import docopt
from ska_sdp_config.cli import cmd_delete

LOG = logging.getLogger("ska-sdp")


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    # TODO: needs confirmation before deleting more than a single key
    # TODO: should we all for deleting all workflows? (pbs?)
    # TODO: what is the difference between deleting a path and deleting recursively? it does the same, no?
    args = docopt(__doc__, argv=argv)

    object_dict = {"pb": args["pb"], "workflow": args["workflow"]}

    path = args["<path>"]

    for k, v in object_dict.items():
        if v:
            path = "/" + k
            args["-R"] = True
            break  # only one can be true, or none

    for txn in config.txn():
        cmd_delete(txn, path, args)

    LOG.info("Deleted above keys in path %s.", path)
