"""
Create a processing block to run a workflow within SDP.

Usage:
    ska-sdp process <workflow> [<parameters>]
    ska-sdp process (-h | --help)

Arguments:
    <workflow>    Workflow in the format of: type:name:version
    <parameters>  It is in sdpcfg, I don't know what they are

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output
"""
import logging
import yaml

from docopt import docopt
from ska_sdp_config import entity

LOG = logging.getLogger("ska-sdp")


def cmd_create_pb(txn, workflow, parameters, _args):
    """
    Create a processing block to run a workflow.

    :param txn: Config object transaction
    :param workflow: dict of workflow information: type, id, version
    :param parameters: dict of workflow parameters, it can be None
    :param _args: CLI input args TODO: remove, not used
    """
    # Parse parameters
    if parameters is not None:
        pars = yaml.safe_load(parameters)
    else:
        pars = {}

    # Create new processing block ID, create processing block
    pb_id = txn.new_processing_block_id("sdpcfg")
    txn.create_processing_block(
        entity.ProcessingBlock(pb_id, None, workflow, parameters=pars)
    )
    return pb_id


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    # TODO: sdpcfg allows for "parameters", what are those?
    args = docopt(__doc__, argv=argv)

    workflow = args["<workflow>"].split(":")

    if len(workflow) != 3:
        raise ValueError("Please specify workflow as 'type:name:version'!")

    else:
        workflow = {"type": workflow[0], "id": workflow[1], "version": workflow[2]}

    for txn in config.txn():
        pb_id = cmd_create_pb(txn, workflow, args["<parameters>"], args)

    LOG.info("OK; pb_id: %s", pb_id)
