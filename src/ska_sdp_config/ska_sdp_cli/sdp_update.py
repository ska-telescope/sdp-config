"""
Update the value of a single key (full path in the Configuration Database).
Can either update from CLI, or edit via a text editor.

Usage:
    ska-sdp update [options] <key> <value>
    ska-sdp edit <key>
    ska-sdp (update | edit) (-h | --help)

Arguments:
    <key>       Key within the Config DB. Has to be the full path.
                To get the list of all keys:
                    ska-sdp list -a /
    <value>     Value to update the Key with.

Options:
    -h, --help    Show this screen
    -q, --quiet   Cut back on unnecessary output

Note:
    ska-sdp edit needs an environment variable defined:
        EDITOR: Has to match the executable of an existing text editor
                Recommended: vi, vim, nano (i.e. command line-based editors)
        Example: EDITOR=vi ska-sdp edit <key>
"""
import json
import logging
import os
import subprocess
import tempfile
import yaml

from docopt import docopt
from ska_sdp_config import config

LOG = logging.getLogger("ska-sdp")


def cmd_update(txn, path, value, _args):
    """
    Update raw key value.

    :param txn: Config object transaction
    :param path: path within the config db to update the value of, same as key TODO: rename input variable
    :param value: new value to update the key with
    :param _args: CLI input args TODO: remove this, it's not used..
    """
    txn.raw.update(path, value)


def cmd_edit(txn, path):
    """
    Edit the value of a raw key in a CLI text editor.
    Only works if the editor's executable is supplied through the EDITOR env. var.

    :param txn: Config object transaction
    :param path: path within the config db to update/edit the value of, same as key TODO: rename input variable
    """
    val = txn.raw.get(path)
    try:

        # Attempt translation to YAML
        val_dict = json.loads(val)
        val_in = yaml.dump(val_dict)
        have_yaml = True

    except json.JSONDecodeError:

        val_in = val
        have_yaml = False

    # Write to temporary file
    with tempfile.NamedTemporaryFile(
        "w",
        suffix=(".yml" if have_yaml else ".dat"),
        prefix=os.path.basename(path),
        delete=True,
    ) as tmp:
        print(val_in, file=tmp, flush=True)
        fname = tmp.name

        # Start editor
        subprocess.call([os.environ["EDITOR"] + " " + fname], shell=True)

        # Read new value in
        with open(fname) as tmp2:
            new_val = tmp2.read()
        if have_yaml:
            new_val = config.dict_to_json(yaml.safe_load(new_val))

    # Apply update
    if new_val == val:
        LOG.info("No change!")
    else:
        txn.raw.update(path, new_val)


def main(argv, config):
    # TODO: should config be an input, or can I define the object here?
    # TODO: is it ok to get the txn here, or does it have to be within ska_sdp for all commands?
    #   --> see cli.py
    args = docopt(__doc__, argv=argv)
    key = args["<key>"]

    for txn in config.txn():
        if args["update"]:
            cmd_update(txn, key, args["<value>"], args)

        if args["edit"]:
            cmd_edit(txn, key)

    LOG.info("%s updated.", key)
