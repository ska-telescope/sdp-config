"""
List keys (and optionally values) within the Configuration Database.

Usage:
    ska-sdp list (-a |--all) [options]
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
    -h, --help         Show this screen
    -q, --quiet        Cut back on unnecessary output
    -a, --all          List the contents of the Config DB, regardless of object type
    -v, --values       List all the values belonging to a key in the config db; default: False
    --prefix=<prefix>  Path prefix (if other than standard Config paths, e.g. for testing)
"""
import logging
from docopt import docopt

LOG = logging.getLogger("ska-sdp")


def get_data_from_db(txn, path, args):
    """Get all key-value pairs from Config DB path."""
    recurse = 8 if args["-R"] else 0
    keys = txn.raw.list_keys(path, recurse=recurse)
    values_dict = {key: txn.raw.get(key) for key in keys}

    return values_dict


def _log_results(key, value, args):
    """Log information based on user input arguments."""
    quiet = args["--quiet"]
    vals = args["--values"]

    if quiet:
        if vals:
            LOG.info(value)
        else:
            LOG.info(key)
    else:
        if vals:
            LOG.info("%s = %s", key, value)
        else:
            LOG.info(key)


def cmd_list(txn, path, args):
    """
    List raw keys/values from database and log them into the console.

    :param txn: Config object transaction
    :param path: path within the config db to list contents of
    :param args: CLI input args
    """
    values_dict = get_data_from_db(txn, path, args)
    quiet = args["--quiet"]

    if args["pb"] and args["<date>"]:
        if not quiet:
            LOG.info("Processing blocks for date %s: ", args['<date>'])

        for key, value in values_dict.items():
            if args["<date>"] in key:
                _log_results(key, value, args)

    elif args["workflow"] and args["<type>"]:
        if not quiet:
            LOG.info("Workflow definitions of type %s: ", args['<type>'])

        for key, value in values_dict.items():
            if args["<type>"].lower() in key:
                _log_results(key, value, args)

    else:
        if not quiet:
            LOG.info("Keys with prefix %s: ", path)

        for key, value in values_dict.items():
            _log_results(key, value, args)


def main(argv, config):
    """Run ska-sdp list."""
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    args = docopt(__doc__, argv=argv)

    object_dict = {
        "pb": args["pb"],
        "workflow": args["workflow"],
        "deploy": args["deployment"],
        "sbi": args["sbi"],
    }

    args["-R"] = True

    if args["--prefix"]:
        path = args["--prefix"].rstrip("/") + "/"
    else:
        path = "/"

    for sdp_object, exists in object_dict.items():
        if exists:
            path = path + sdp_object
            break  # only one can be true, or none

    for txn in config.txn():
        cmd_list(txn, path, args)
