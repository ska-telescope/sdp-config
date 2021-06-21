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

from ska_sdp_config.config import Transaction

LOG = logging.getLogger("ska-sdp")


def _get_data_from_db(txn: Transaction, path: str):
    """Get all key-value pairs from Config DB path."""
    keys = txn.raw.list_keys(path, recurse=8)
    values_dict = {key: txn.raw.get(key) for key in keys}

    return values_dict


def _log_results(key: str, value: str, list_values=True, quiet_logging=False):
    """Log information based on user input arguments."""
    if quiet_logging:
        if list_values:
            LOG.info(value)
        else:
            LOG.info(key)
    else:
        if list_values:
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
    values_dict = _get_data_from_db(txn, path)
    quiet = args["--quiet"]
    list_values = args["--values"]

    if args["pb"] and args["<date>"]:
        if not quiet:
            LOG.info("Processing blocks for date %s: ", args["<date>"])

        for key, value in values_dict.items():
            if args["<date>"] in key:
                _log_results(key, value, list_values=list_values, quiet_logging=quiet)

    elif args["workflow"] and args["<type>"]:
        if not quiet:
            LOG.info("Workflow definitions of type %s: ", args["<type>"])

        for key, value in values_dict.items():
            if args["<type>"].lower() in key:
                _log_results(key, value, list_values=list_values, quiet_logging=quiet)

    else:
        if not quiet:
            LOG.info("Keys with prefix %s: ", path)

        for key, value in values_dict.items():
            _log_results(key, value, list_values=list_values, quiet_logging=quiet)


def main(argv, config):
    """Run ska-sdp list."""
    args = docopt(__doc__, argv=argv)

    object_dict = {
        "pb": args["pb"],
        "workflow": args["workflow"],
        "deploy": args["deployment"],
        "sb": args["sbi"],
    }

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
