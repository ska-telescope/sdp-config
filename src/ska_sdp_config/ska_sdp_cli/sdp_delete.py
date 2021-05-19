"""
Delete a key from the Configuration Database.

Usage:
    ska-sdp delete (-a|--all) [options] (pb|workflow|sbi|deployment|prefix)
    ska-sdp delete [options] (pb|sbi|deployment) <id>
    ska-sdp delete [options] workflow <workflow>
    ska-sdp delete (-h|--help)

Arguments:
    <id>        Id of the processing block, or deployment, or scheduling block instance to be deleted
    <workflow>  Workflow definition to be deleted. Expected format: type:id:version
    prefix      Use this "SDP Object" when deleting with a user-defined prefix, that is not object-specific

Options:
    -h, --help             Show this screen
    -q, --quiet            Cut back on unnecessary output
    --prefix=<prefix>      Path prefix for high-level API
"""
import logging
from docopt import docopt

LOG = logging.getLogger("ska-sdp")


def cmd_delete(txn, path, args):
    """
    Delete a key from the Config DB.

    :param txn: Config object transaction
    :param path: path within the Config DB to delete
    :param args: CLI input args
    """
    if args["-R"]:
        for key in txn.raw.list_keys(path, recurse=8):
            if not args["--quiet"]:
                LOG.info(key)
            txn.raw.delete(key)
    else:
        txn.raw.delete(path)


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
    if args["--prefix"]:
        path = args["--prefix"].rstrip("/")+"/"

    for sdp_object, exists in object_dict.items():
        if exists:
            if args["--all"] or args["-a"]:
                LOG.warning(
                    "You are attempting to delete all entries of type %s "
                    "from the Configuration DB.",
                    sdp_object,
                )
                cont = input("Continue? (yes, no) ")
                if cont == "yes":
                    path = "/" + sdp_object
                else:
                    LOG.info("Aborted")
                    return

            elif sdp_object == "workflow":
                path = f"/workflow/{args['<workflow>']}"

            else:
                path = f"/{sdp_object}/{args['<id>']}"

            break  # only one can be true, or none

    for txn in config.txn():
        cmd_delete(txn, path, args)

    LOG.info("Deleted above keys with prefix %s.", path)
