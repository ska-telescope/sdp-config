"""
List keys (and optionally values) within the Configuration Database.

Usage:
    ska-sdp list (-a | --all) <path>
    ska-sdp list [options] pb <path>
    ska-sdp list [options] workflow <path>
    ska-sdp list (-h | --help)

Arguments:
    <path>      Path within the Config DB. For root: /

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output
    -a, --all     List all of the keys within a path, regardless of object type
    -v, --values  List all the values belonging to a key in the config db; default: False
"""

# For now take it out as an option, it's set to True by default, without it listing doesn't work well
#     -R           Recursive list: list all subdirectories as well

from docopt import docopt
from ska_sdp_config.cli import cmd_list


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    args = docopt(__doc__, argv=argv)

    object_dict = {"pb": args["pb"], "workflow": args["workflow"]}

    args["-R"] = True
    args["values"] = args["--values"]

    path = args["<path>"]
    if path[-1] != "/":
        path = path + "/"

    for k, v in object_dict.items():
        if v:
            path = path + k
            break  # only one can be true, or none

    for txn in config.txn():
        cmd_list(txn, path, args)
