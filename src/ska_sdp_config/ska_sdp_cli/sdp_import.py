"""
Import workflow definitions into the Configuration Database.

Usage:
    ska-sdp import [options] <file_or_url>
    ska-sdp import (-h|--help)

Arguments:
    <file-or-url>      File or URL to import workflows from.

Options:
    -h, --help    Show this screen
    --sync        Delete workflows not in the input TODO: should it be called delete? or maybe different definition?

TODO: add example of what the file should be like?
"""
import logging
import os
from typing import Dict

import requests
import yaml
from docopt import docopt

LOG = logging.getLogger("ska-sdp")
WORKFLOW_PREFIX = "workflow"


def workflow_path(wf_type, wf_id, version):
    return f"/{WORKFLOW_PREFIX}/{wf_type}:{wf_id}:{version}"


def list_workflows(txn):
    keys = txn.raw.list_keys("/" + WORKFLOW_PREFIX)
    workflows = [tuple(k.split("/")[2].split(":")) for k in keys]
    return workflows


def get_workflow(txn, wf_type, wf_id, version):
    return txn._get(workflow_path(wf_type, wf_id, version))


def create_workflow(txn, wf_type, wf_id, version, workflow):
    txn._create(workflow_path(wf_type, wf_id, version), workflow)


def update_workflow(txn, wf_type, wf_id, version, workflow):
    txn._update(workflow_path(wf_type, wf_id, version), workflow)


def delete_workflow(txn, wf_type, wf_id, version):
    txn.raw.delete(workflow_path(wf_type, wf_id, version))


def read_input(input_object: str) -> Dict:
    """
    Read workflow definitions from file or URL.

    :param input_object: input filename or URL
    :returns: definitions converted into dict
    """
    if os.path.isfile(input_object):
        with open(input_object, "r") as file:
            data = file.read()
    else:
        with requests.get(input_object) as response:
            data = response.text

    definitions = yaml.safe_load(data)

    return definitions


def _parse_structured(definitions: Dict) -> Dict:
    """
    Parse structured workflow definitions.

    :param definitions: structured workflow definitions
    :returns: dictionary mapping (type, id, version) to definition.

    """
    repositories = {repo["name"]: repo["path"] for repo in definitions["repositories"]}
    workflows = {
        (w["type"], w["id"], v): {
            "image": repositories[w["repository"]] + "/" + w["image"] + ":" + v,
        }
        for w in definitions["workflows"]
        for v in w["versions"]
    }
    return workflows


def _parse_flat(definitions):
    """
    Parse flat workflow definitions. TODO: what is "flat"?

    :param definitions: structured workflow definitions
    :returns: dictionary mapping (type, id, version) to definition.

    """
    workflows = {
        (w["type"], w["id"], w["version"]): {"image": w["image"]}
        for w in definitions["workflows"]
    }
    return workflows


def parse_definitions(definitions: Dict) -> Dict:
    """
    Parse workflow definitions.

    :param definitions: workflow definitions
    :returns: dictionary mapping (type, id, version) to definition.

    """
    if "repositories" in definitions:
        workflows = _parse_structured(definitions)
    else:
        workflows = _parse_flat(definitions)
    return workflows


def import_workflows(txn, workflows: Dict, sync: bool = True):
    """
    Import the workflow definitions into the configuration database.

    :param txn: Config object transaction
    :param workflows: workflow definitions
    :param sync: delete workflows not in the input
    """
    # Create sorted list of existing and new workflows
    all_workflows = sorted(list(set(list_workflows(txn)) | set(workflows.keys())))
    change = False
    for key in all_workflows:
        if key in workflows:
            old_value = get_workflow(txn, *key)
            new_value = workflows[key]
            if old_value is None:
                LOG.info("Creating", *key)
                create_workflow(txn, *key, new_value)
                change = True
            elif new_value != old_value:
                LOG.info("Updating", *key)
                update_workflow(txn, *key, new_value)
                change = True
        elif sync:
            LOG.info("Deleting", *key)
            delete_workflow(txn, *key)
            change = True
    if not change:
        LOG.info("No changes")


def main(argv, config):
    args = docopt(__doc__, argv=argv)

    LOG.info("Importing workflow definitions from", args["<file-or-url>"])
    definitions = read_input(args["<file-or-url>"])
    workflows = parse_definitions(definitions)

    for txn in config.txn():
        import_workflows(txn, workflows, sync=args["--sync"])

