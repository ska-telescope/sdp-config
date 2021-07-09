"""
Delete a key from the Configuration Database.

Usage:
    ska-sdp delete (-a|--all) [options] (pb|workflow|sbi|deployment|prefix)
    ska-sdp delete [options] (pb|sbi|deployment) <item-id>
    ska-sdp delete [options] workflow <workflow>
    ska-sdp delete (-h|--help)

Arguments:
    <item-id>   ID of the processing block, or deployment, or scheduling block instance
    <workflow>  Workflow definition to be deleted. Expected format: type:id:version
    prefix      Use this "SDP Object" when deleting with a non-object-specific, user-defined prefix

Options:
    -h, --help             Show this screen
    -q, --quiet            Cut back on unnecessary output
    --prefix=<prefix>      Path prefix (if other than standard Config paths, e.g. for testing)
"""
# pylint: disable=too-many-branches

import logging
from docopt import docopt

LOG = logging.getLogger("ska-sdp")


def cmd_delete(txn, path, recurse=True, quiet=False):
    """
    Delete a key from the Config DB.

    :param txn: Config object transaction
    :param path: path within the Config DB to delete
    :param recurse: if True, run recursive query of key as a prefix
    :param quiet: quiet logging
    """
    if recurse:
        for key in txn.raw.list_keys(path, recurse=8):
            if not quiet:
                LOG.info(key)
            txn.raw.delete(key)
    else:
        txn.raw.delete(path)


def _get_input():
    return input("Continue? (yes, no) ")


def main(argv, config):
    """Run ska-sdp delete."""
    args = docopt(__doc__, argv=argv)

    object_dict = {
        "pb": args["pb"],
        "workflow": args["workflow"],
        "deploy": args["deployment"],
        "sb": args["sbi"],
    }
    prefix = args["--prefix"]
    path = ""

    cont = False
    if prefix:
        if args["--all"] or args["-a"]:
            LOG.warning(
                "You are attempting to delete all entries with prefix %s "
                "from the Configuration DB.",
                prefix,
            )
            cont = _get_input()
            if cont == "yes":
                path = prefix.rstrip("/")
            else:
                LOG.info("Aborted")
                return
        else:
            path = prefix.rstrip("/")

    for sdp_object, exists in object_dict.items():
        if exists:
            if args["--all"] or args["-a"]:
                if not cont:  # first time checking if user wants to delete all
                    LOG.warning(
                        "You are attempting to delete all entries of type %s "
                        "from the Configuration DB.",
                        sdp_object,
                    )
                    cont = _get_input()
                    if cont == "yes":
                        path = "/" + sdp_object
                    else:
                        LOG.info("Aborted")
                        return
                else:  # already checked if user wants to delete all with prefix
                    path = path + "/" + sdp_object

            elif sdp_object == "workflow":
                path = f"{path}/workflow/{args['<workflow>']}"

            else:
                path = f"{path}/{sdp_object}/{args['<id>']}"

            break  # only one can be true, or none

    for txn in config.txn():
        cmd_delete(txn, path, recurse=True, quiet=args["--quiet"])

    LOG.info("Deleted above keys with prefix %s.", path)
