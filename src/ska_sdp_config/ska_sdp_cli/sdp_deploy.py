"""
TODO: not sure what it means to create a deployments, what are params, and the inputs mean in sdpcfg

Usage:
    ska-sdp deploy [options]
    ska-sdp deploy (-h | --help)

Arguments:

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output
"""
import yaml
from docopt import docopt
from ska_sdp_config import entity


def cmd_deploy(txn, typ, deploy_id, parameters):
    """Create a deployment."""
    dct = yaml.safe_load(parameters)
    txn.create_deployment(entity.Deployment(deploy_id, typ, dct))


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py

    args = docopt(__doc__, argv=argv)

    return
    # for txn in config.txn():
    #     cmd_deploy(txn, path, args)
