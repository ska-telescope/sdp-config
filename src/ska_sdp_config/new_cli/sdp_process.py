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

from docopt import docopt
from ska_sdp_config.cli import cmd_create_pb

LOG = logging.getLogger("ska-sdp")


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
