"""
Command line utility for interacting with SKA Science Data Processor (SDP).

Usage:
    ska-sdp COMMAND [options] [SDP_OBJECT] [<args>...]
    ska-sdp COMMAND (-h|--help)
    ska-sdp (-h|--help)

SDP Objects:
    pb           Interact with processing blocks
    workflow     Interact with available workflow definitions
    deployment   Interact with deployments
    sbi          Interact with scheduling block instances

Commands:
    list            List information of object from the Configuration DB
    get | watch     Print all the information (i.e. value) of a key in the Config DB
    create          Create a new, raw key-value pair in the Config DB;
                    Run a workflow; Create a deployment
    update          Update a raw key value from CLI
    edit            Edit a raw key value from text editor
    delete          Delete a single key or all keys within a path from the Config DB
    import          Import workflow definitions from file or URL (only works with 'workflow' SDP Object)
"""
import logging
import sys

from docopt import docopt
from ska_sdp_config import config

from ska_sdp_config.ska_sdp_cli import (
    sdp_get,
    sdp_create,
    sdp_update,
    sdp_list,
    sdp_delete, sdp_import,
)

LOG = logging.getLogger("ska-sdp")
LOG.setLevel(logging.INFO)
LOG.addHandler(logging.StreamHandler(sys.stdout))

COMMAND = "COMMAND"


def main(argv):
    args = docopt(__doc__, argv=argv, options_first=True)

    # prefix = ('' if args['--prefix'] is None else args['--prefix'])
    prefix = ""
    cfg = config.Config(global_prefix=prefix)

    if args[COMMAND] == "list":
        sdp_list.main(argv, cfg)

    if args[COMMAND] == "get" or args[COMMAND] == "watch":
        sdp_get.main(argv, cfg)

    if args[COMMAND] == "create":
        sdp_create.main(argv, cfg)

    if args[COMMAND] == "update" or args[COMMAND] == "edit":
        sdp_update.main(argv, cfg)

    if args[COMMAND] == "delete":
        sdp_delete.main(argv, cfg)

    if args[COMMAND] == "import":
        sdp_import.main(argv, cfg)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
