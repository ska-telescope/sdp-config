"""
Update the value of a single key or processing block state.
Can either update from CLI, or edit via a text editor.

Usage:
    ska-sdp update [options] (workflow|sbi|deployment) <item-id> <value>
    ska-sdp update [options] pb-state <item-id> <value>
    ska-sdp update [options] master <value>
    ska-sdp update [options] subarray <item-id> <value>
    ska-sdp edit (workflow|sbi|deployment) <item-id>
    ska-sdp edit pb-state <item-id>
    ska-sdp edit master
    ska-sdp edit subarray <item-id>
    ska-sdp (update|edit) (-h|--help)

Arguments:
    <item-id>   id of the workflow, sbi, deployment, processing block or subarray
    <value>     Value to update the key/pb state with.

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output

Note:
    ska-sdp edit needs an environment variable defined:
        EDITOR: Has to match the executable of an existing text editor
                Recommended: vi, vim, nano (i.e. command line-based editors)
        Example: EDITOR=vi ska-sdp edit <key>
    Processing blocks cannot be changed, apart from their state.

Example:
    ska-sdp edit sbi sbi-test-20210524-00000
        --> key that's edited: /sbi/sbi-test-20210524-00000
    ska-sdp edit workflow batch:test:0.0.0
        --> key that's edited: /workflow/batch:test:0.0.0
    ska-sdp edit pb-state some-pb-id-0000
        --> key that's edited: /pb/some-pb-id-0000/state
"""
import json
import logging
import os
import subprocess
import tempfile
import yaml

from docopt import docopt

from ska_sdp_config.config import dict_to_json

LOG = logging.getLogger("ska-sdp")


class EditorNotFoundError(Exception):
    """Raise when the EDITOR env.var is not set."""


def _clean_filename(name: str):
    # Make file name portable. Use translate if it starts getting complicated.
    delim = "_"
    return name.replace("/", delim).replace(":", delim).replace(".", delim)


def cmd_update(txn, key, value):
    """
    Update raw key value.

    :param txn: Config object transaction
    :param key: Key in the Config DB to update the value of
    :param value: new value to update the key with
    """
    txn.raw.update(key, value)
    LOG.info("%s updated.", key)


def cmd_edit(txn, key):
    """
    Edit the value of a raw key in a CLI text editor.
    Only works if the editor's executable is supplied through the EDITOR env. var.

    :param txn: Config object transaction
    :param key: Key in the Config DB to update the value of
    """
    val = txn.raw.get(key)
    if val is None:
        raise KeyError(f"No match for {key}")

    # Attempt translation to YAML
    val_dict = json.loads(val)
    val_in = yaml.dump(val_dict)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Write to temporary file. Put it in a temp directory to avoid re-opening a
        # file that hasn't been closed (can't do that on Windows).
        fname = os.path.join(temp_dir, _clean_filename(key[1:]) + ".yml")
        with open(fname, "w") as file:
            file.write(f"# Editing key {key}\n")
            file.write(val_in)

        # Start editor
        try:
            subprocess.run((os.environ["EDITOR"], fname), check=True)
        except KeyError as err:
            # if EDITOR env var is not set, a KeyError is raised
            raise EditorNotFoundError from err

        # Read new value in
        with open(fname) as tmp2:
            new_val = tmp2.read()
        new_val = dict_to_json(yaml.safe_load(new_val))
        os.remove(fname)

    # Apply update
    if new_val == val:
        LOG.info("No change!")
    else:
        cmd_update(txn, key, new_val)


def main(argv, config):
    """Run ska-sdp update / edit."""
    args = docopt(__doc__, argv=argv)
    object_dict = {
        "workflow": args["workflow"],
        "sb": args["sbi"],
        "deploy": args["deployment"],
    }

    if args["pb-state"]:
        key = f"/pb/{args['<pb-id>']}/state"
    elif args["master"]:
        key = "/master"
    elif args["subarray"]:
        key = f"/subarray/{args['<array-id>'].zfill(2)}"
    else:
        key = args["<key>"]

    for sdp_object, exists in object_dict.items():
        if exists:
            key = "/" + sdp_object + "/" + key
            break  # only one can be true, or none

    for txn in config.txn():
        if args["update"]:
            cmd_update(txn, key, args["<value>"])

        if args["edit"]:
            try:
                cmd_edit(txn, key)
            except EditorNotFoundError:
                LOG.error(
                    "Please set the EDITOR environment variable with a valid"
                    "command line-based text editor executable, then rerun. "
                    "(See 'ska-sdp edit -h'.)"
                )
                return
