"""
List keys (and optionally values) within the Configuration Database.

Usage:
    ska-sdp list (-a |--all)
    ska-sdp list [options] pb [<date>]
    ska-sdp list [options] workflow [<type>]
    ska-sdp list [options] (deployment|sbi)
    ska-sdp list (-h|--help)

Arguments:
    <date>      Date on which the processing block(s) were created. Expected format: YYYYMMDD
                If not provided, all pbs are listed.
    <type>      Type of workflow definition. Batch or realtime.
                If not provided, all workflows are listed.

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output
    -a, --all     List the contents of the Config DB, regardless of object type
    -v, --values  List all the values belonging to a key in the config db; default: False
"""

# For now take it out as an option, it's set to True by default, without it listing doesn't work well
#     -R           Recursive list: list all subdirectories as well
import logging
from docopt import docopt

LOG = logging.getLogger("ska-sdp")


def cmd_list(txn, path, args):
    """
    List raw keys/values from database.

    :param txn: Config object transaction
    :param path: path within the config db to list contents of
    :param args: CLI input args
    """
    recurse = 8 if args["-R"] else 0
    keys = txn.raw.list_keys(path, recurse=recurse)

    if args["--quiet"]:
        if args["values"]:
            values = [txn.raw.get(key) for key in keys]
            return values
        else:
            return keys
    else:
        LOG.info("Keys with {} prefix:".format(path))
        if args["values"]:
            to_list = []
            for key in keys:
                value = txn.raw.get(key)
                to_list.append(f"{key} = {value}")
            return to_list

        else:
            return keys


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    args = docopt(__doc__, argv=argv)

    object_dict = {
        "pb": args["pb"],
        "workflow": args["workflow"],
        "deployment": args["deployment"],
        "sbi": args["sbi"],
    }

    args["-R"] = True
    args["values"] = args["--values"]

    path = "/"
    for k, v in object_dict.items():
        if v:
            path = path + k
            break  # only one can be true, or none

    for txn in config.txn():
        listed_objects = cmd_list(txn, path, args)

    if args["pb"] and args["<date>"]:
        for elem in listed_objects:
            if args["<date>"] in elem:
                LOG.info(elem)

    elif args["workflow"] and args["<type>"]:
        for elem in listed_objects:
            if args["<type>"].lower() in elem:
                LOG.info(elem)

    else:
        for elem in listed_objects:
            LOG.info(elem)
