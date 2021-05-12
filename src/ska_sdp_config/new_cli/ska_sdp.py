"""
Command line utility for interacting with SKA Science Data Processor (SDP).

Usage:
    ska-sdp COMMAND [options] SDP_OBJECT [<args>...]
    ska-sdp COMMAND (-h|--help)
    ska-sdp (-h|--help)

SDP Objects:
    pb           Interact with processing blocks
    workflow     Interact with available workflows

Commands:
    list     List information of object from the Configuration DB
"""

from docopt import docopt
from ska_sdp_config import config

import ska_sdp_config.new_cli.sdp_list as sdp_list


def main(argv):
    args = docopt(__doc__, argv=argv, options_first=True)

    # prefix = ('' if args['--prefix'] is None else args['--prefix'])
    prefix = ""
    cfg = config.Config(global_prefix=prefix)

    if args['COMMAND'] == "list":
        sdp_list.main(argv, cfg)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
