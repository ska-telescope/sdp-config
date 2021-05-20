"""
Import workflow definitions into the Configuration Database.

Usage:
    ska-sdp import [options] <file-or-url>
    ska-sdp import (-h|--help)

Arguments:
    <file-or-url>      File or URL to import workflow definitions from.

Options:
    -h, --help          Show this screen
    --sync              Delete workflows not in the input
        TODO: should it be called delete? or maybe different definition?

TODO: add example of what the file should be like?
"""
# pylint: disable=protected-access
# pylint: disable=too-many-arguments

import logging
import os
from typing import Dict

import requests
import yaml
from docopt import docopt

LOG = logging.getLogger("ska-sdp")
WORKFLOW_PREFIX = "workflow"


def _workflow_path(wf_type, wf_id, version, prefix=""):
    return f"{prefix}/{WORKFLOW_PREFIX}/{wf_type}:{wf_id}:{version}"


def _list_workflows(txn, prefix=""):
    keys = txn.raw.list_keys(f"{prefix}/{WORKFLOW_PREFIX}/")
    workflows = [tuple(k.replace(prefix, "").split("/")[2].split(":")) for k in keys]
    return workflows


def _get_workflow(txn, wf_type, wf_id, version, prefix=""):
    return txn._get(_workflow_path(wf_type, wf_id, version, prefix))


def _create_workflow(txn, wf_type, wf_id, version, workflow, prefix=""):
    txn._create(_workflow_path(wf_type, wf_id, version, prefix), workflow)


def _update_workflow(txn, wf_type, wf_id, version, workflow, prefix=""):
    txn._update(_workflow_path(wf_type, wf_id, version, prefix), workflow)


def _delete_workflow(txn, wf_type, wf_id, version, prefix=""):
    txn.raw.delete(_workflow_path(wf_type, wf_id, version, prefix))


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

    :param definitions: flat workflow definitions
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


def import_workflows(txn, workflows: Dict, sync: bool = True, prefix: str = ""):
    """
    Import the workflow definitions into the Configuration Database.

    :param txn: Config object transaction
    :param workflows: workflow definitions
    :param sync: delete workflows not in the input
    :param prefix: custom-prefix to add to the workflow keys, used for testing only
    """
    # Create sorted list of existing and new workflows
    existing_workflows = _list_workflows(txn, prefix=prefix)
    all_workflows = sorted(list(set(existing_workflows) | set(workflows.keys())))

    change = False
    for key in all_workflows:
        if key in workflows:
            old_value = _get_workflow(txn, *key, prefix=prefix)
            new_value = workflows[key]
            if old_value is None:
                LOG.info("Creating %s", key)
                _create_workflow(txn, *key, new_value, prefix=prefix)
                change = True
            elif new_value != old_value:
                LOG.info("Updating %s", key)
                _update_workflow(txn, *key, new_value, prefix=prefix)
                change = True
        elif sync:
            LOG.info("Deleting %s", key)
            _delete_workflow(txn, *key, prefix=prefix)
            change = True
    if not change:
        LOG.info("No changes")


def main(argv, config):
    """Run ska-sdp import."""
    args = docopt(__doc__, argv=argv)

    LOG.info("Importing workflow definitions from %s", args["<file-or-url>"])
    definitions = read_input(args["<file-or-url>"])
    workflows = parse_definitions(definitions)

    for txn in config.txn():
        import_workflows(txn, workflows, sync=args["--sync"])
