"""
Create a new, raw, key-value pair in the Configuration Database.
Create a processing block to run a workflow.
Create a deployment.

Usage:
    ska-sdp create [options] pb <workflow> [<parameters>]
    ska-sdp create [options] deployment <deploy-id> <type> <parameters>
    ska-sdp create [options] (workflow|sbi) <key> <value>
    ska-sdp create (-h|--help)

Arguments:
    <workflow>      Workflow that the processing block will run, in the format of: type:id:version
    <parameters>    Optional parameters for a workflow, with expected format:
                        '{"key1": "value1", "key2": "value2"}'
                    For deployments, expected format:
                        '{"chart": <chart-name>, "values": <dict-of-values>}'
    <deploy_id>     Id of the new deployment
    <type>          Type of the new deployment (currently "helm" only)
    Create general key-value pairs:
    <key>           Key to be created in the Config DB.
    <value>         Value belonging to that key.

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output

Example:
    ska-sdp create sbi my_new_sbi '{"test": true}'
    Result in the config db:
        key: /sbi/my_new_sbi
        value: {"test": true}

Note: You cannot create processing blocks apart from when they are called to run a workflow.
"""
import logging
import yaml

from docopt import docopt
from ska_sdp_config import entity

LOG = logging.getLogger("ska-sdp")


def cmd_create(txn, key, value):
    """
    Create raw key.

    :param txn: Config object transaction
    :param key: key within the config db to be created
    :param value: value of new key to be added
    """
    txn.raw.create(key, value)


def cmd_create_pb(txn, workflow, parameters):
    """
    Create a processing block to run a workflow.

    :param txn: Config object transaction
    :param workflow: dict of workflow information: type, id, version
    :param parameters: dict of workflow parameters, it can be None

    :return pb_id: ID of the created processing block
    """
    # Parse parameters
    if parameters is not None:
        pars = yaml.safe_load(parameters)
    else:
        pars = {}

    # Create new processing block ID, create processing block
    pb_id = txn.new_processing_block_id("sdp-cli")
    txn.create_processing_block(
        entity.ProcessingBlock(pb_id, None, workflow, parameters=pars)
    )
    return pb_id


def cmd_deploy(txn, deploy_type, deploy_id, parameters):
    """
    Create a deployment.

    :param txn: Config object transaction
    :param deploy_type: Type of the deployment, currently "helm" only
    :param deploy_id: ID of the deployment
    :param parameters: String of deployment parameters in the form of:
                       '{"chart": <chart-name>, "values": <dict-of-values>}'
    """
    params_dict = yaml.safe_load(parameters)
    txn.create_deployment(entity.Deployment(deploy_id, deploy_type, params_dict))


def main(argv, config):
    """Run ska-sdp create."""
    args = docopt(__doc__, argv=argv)

    object_dict = {"workflow": args["workflow"], "sbi": args["sbi"]}

    if args["pb"]:
        workflow = args["<workflow>"].split(":")
        if len(workflow) != 3:
            raise ValueError("Please specify workflow as 'type:name:version'!")

        workflow = {"type": workflow[0], "id": workflow[1], "version": workflow[2]}

        for txn in config.txn():
            pb_id = cmd_create_pb(txn, workflow, args["<parameters>"])

        LOG.info("Processing block created with pb_id: %s", pb_id)
        return

    if args["deployment"]:
        for txn in config.txn():
            cmd_deploy(txn, args["<type>"], args["<deploy-id>"], args["<parameters>"])

        LOG.info("Deployment created with id: %s", args["<deploy-id>"])
        return

    path = "/"
    for sdp_object, exists in object_dict.items():
        if exists:
            path = path + sdp_object
            break  # only one can be true, or none

    path = path + "/" + args["<key>"]

    for txn in config.txn():
        cmd_create(txn, path, args["<value>"])

    LOG.info("%s created", path)
