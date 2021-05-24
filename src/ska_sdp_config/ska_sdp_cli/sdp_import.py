"""
Import workflow definitions into the Configuration Database.

Usage:
    ska-sdp import workflows [options] <file-or-url>
    ska-sdp import (-h|--help)

Arguments:
    <file-or-url>      File or URL to import workflow definitions from.

Options:
    -h, --help          Show this screen
    --sync              Delete workflows not in the input
"""

import logging
import os
from typing import Dict

import requests
import yaml
from docopt import docopt
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from ska_sdp_config.config import Transaction

LOG = logging.getLogger("ska-sdp")


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


def _parse_flat(definitions: Dict) -> Dict:
    """
    Parse flat workflow definitions.

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


def import_workflows(txn: Transaction, workflows: Dict, sync: bool = True):
    """
    Import the workflow definitions into the Configuration Database.

    :param txn: Config object transaction
    :param workflows: workflow definitions
    :param sync: delete workflows not in the input
    """
    # Create sorted list of existing and new workflows
    existing_workflows = txn.list_workflows()
    all_workflows = sorted(list(set(existing_workflows) | set(workflows.keys())))

    change = False
    for key in all_workflows:
        if key in workflows:
            old_value = txn.get_workflow(*key)
            new_value = workflows[key]
            if old_value is None:
                LOG.info("Creating %s", key)
                txn.create_workflow(*key, new_value)
                change = True
            elif new_value != old_value:
                LOG.info("Updating %s", key)
                txn.update_workflow(*key, new_value)
                change = True
        elif sync:
            LOG.info("Deleting %s", key)
            txn.delete_workflow(*key)
            change = True
    if not change:
        LOG.info("No changes")


def main(argv, config):
    """Run ska-sdp import."""
    args = docopt(__doc__, argv=argv)

    LOG.info("Importing workflow definitions from %s", args["<file-or-url>"])

    try:
        definitions = read_input(args["<file-or-url>"])
    except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
        # MissingSchema exception raised when json file doesn't exist
        # ConnectionError raised when URL is wrong
        LOG.error("Bad file name or URL. Please fix, and retry.")
        return
    except (ParserError, ScannerError):
        LOG.error("Malformed YAML/JSON file. Please fix, and retry.")
        return

    workflows = parse_definitions(definitions)

    for txn in config.txn():
        import_workflows(txn, workflows, sync=args["--sync"])

    LOG.info("Import finished successfully.")
