"""
Command line utility for accessing SKA SDP configuration.

Usage:
  sdpcfg [options] (get|watch) <path>
  sdpcfg [options] [watch] (ls|list) [values] [-R] <path>
  sdpcfg [options] delete [-R] <path>
  sdpcfg [options] (create|update) <path> <value>
  sdpcfg [options] edit <path>
  sdpcfg [options] process <workflow> [<parameters>]
  sdpcfg [options] deploy <type> <name> <parameters>
  sdpcfg --help

Options:
  -q, --quiet          Cut back on unnecessary output
  --prefix <prefix>    Path prefix for high-level API

Environment Variables:
  SDP_CONFIG_BACKEND   Database backend (default etcd3)
  SDP_CONFIG_HOST      Database host address (default 127.0.0.1)
  SDP_CONFIG_PORT      Database port (default 2379)
  SDP_CONFIG_PROTOCOL  Database access protocol (default http)
  SDP_CONFIG_CERT      Client certificate
  SDP_CONFIG_USERNAME  User name
  SDP_CONFIG_PASSWORD  User password
"""

# pylint: disable=assignment-from-no-return
# pylint: disable=too-many-branches

import sys
import re
import logging
import docopt
from ska_sdp_config import config
from ska_sdp_config.ska_sdp_cli.sdp_create import cmd_create, cmd_create_pb, cmd_deploy
from ska_sdp_config.ska_sdp_cli.sdp_delete import cmd_delete
from ska_sdp_config.ska_sdp_cli.sdp_get import cmd_get
from ska_sdp_config.ska_sdp_cli.sdp_list import get_data_from_db
from ska_sdp_config.ska_sdp_cli.sdp_update import cmd_update, cmd_edit

# because functions are migrated to the new cli files, the logger name had to be updated
LOG = logging.getLogger("ska-sdp")
LOG.setLevel(logging.INFO)
LOG.addHandler(logging.StreamHandler(sys.stdout))


def main(argv):
    """Command line interface implementation."""
    args = docopt.docopt(__doc__, argv=argv)

    # Validate
    path = args["<path>"]
    success = True
    if path is not None:
        if path[0] != '/':
            print("Path must start with '/'!", file=sys.stderr)
            success = False
        if args['list'] is None and path[-1] == '/':
            print("Key path must not end with '/'!", file=sys.stderr)
            success = False
        if not re.match('^[a-zA-Z0-9_\\-/]*$', path):
            print("Path contains non-permissible characters!", file=sys.stderr)
            success = False
    workflow = args['<workflow>']
    if workflow is not None:
        workflow = workflow.split(':')
        if len(workflow) != 3:
            print("Please specify workflow as 'type:name:version'!",
                  file=sys.stderr)
            success = False
        else:
            workflow = {
                'type': workflow[0],
                'id': workflow[1],
                'version': workflow[2]
            }

    # Input can be taken from stdin
    value = args["<value>"]
    if value == '-':
        value = sys.stdin.read()
    parameters = args["<parameters>"]
    if parameters == '-':
        parameters = sys.stdin.read()
    if not success:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    cmd(args, path, value, workflow, parameters)


def _list_results(txn, path, args):
    values_dict = get_data_from_db(txn, path, args)

    if args["--quiet"]:
        if args["values"]:
            LOG.info(" ".join(values_dict.values()))
        else:
            LOG.info(" ".join(values_dict.keys()))

    else:
        LOG.info("Keys with %s prefix:", path)
        if args["values"]:
            for key, value in values_dict.items():
                LOG.info("%s = %s", key, value)
        else:
            for key in values_dict.keys():
                LOG.info(key)


def cmd(args, path, value, workflow, parameters):
    """Execute command."""
    # Get configuration client, start transaction
    prefix = ('' if args['--prefix'] is None else args['--prefix'])
    cfg = config.Config(global_prefix=prefix)
    try:
        for txn in cfg.txn():
            if args['ls'] or args['list']:
                _list_results(txn, path, args)
            elif args['watch'] or args['get']:
                cmd_get(txn, path, args)
            elif args['create']:
                cmd_create(txn, path, value, args)
            elif args['edit']:
                cmd_edit(txn, path)
            elif args['update']:
                cmd_update(txn, path, value, args)
            elif args['delete']:
                cmd_delete(txn, path, args)
            elif args['process']:
                pb_id = cmd_create_pb(txn, workflow, parameters, args)
            elif args['deploy']:
                cmd_deploy(txn, args['<type>'], args['<name>'], parameters)
            if args['watch']:
                txn.loop(wait=True)

        # Possibly give feedback after transaction has concluded
        if not args['--quiet']:
            if args['create'] or args['update'] or args['delete'] or \
               args['edit']:
                LOG.info("OK")
            if args['process']:
                LOG.info("OK, pb_id = %s", pb_id)

    except KeyboardInterrupt:
        if not args['watch']:
            raise
