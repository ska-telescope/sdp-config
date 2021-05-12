"""
Usage:
    ska-sdp list [options] pb <path>
    ska-sdp list [options] workflow <path>
    ska-sdp list (-h | --help)

Arguments:
    <path>       Path within the Config DB. For root: /

Options:
    -h, --help   Show this screen
    -q, --quiet  Cut back on unnecessary output
    -R           Recursive list: list all subdirectories as well
"""

from docopt import docopt

from ska_sdp_config.cli import cmd_list


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    args = docopt(__doc__, argv=argv)

    pb = args["pb"]
    workflow = args["workflow"]

    args["values"] = "pb" if pb else "workflow"

    for txn in config.txn():
        cmd_list(txn, args["<path>"], args)