"""Tests for sdpcfg command line utility."""

# pylint: disable=missing-docstring
import json
import os
from datetime import date
from unittest.mock import patch, call

import pytest

from ska_sdp_config import cli, config, ConfigCollision
from ska_sdp_config.ska_sdp_cli.sdp_delete import cmd_delete
from ska_sdp_config.ska_sdp_cli.sdp_update import cmd_update
from ska_sdp_config.ska_sdp_cli.sdp_create import cmd_create, cmd_create_pb
from ska_sdp_config.ska_sdp_cli.sdp_list import cmd_list
from ska_sdp_config.ska_sdp_cli.sdp_get import cmd_get
from tests.test_backend_etcd3 import PREFIX as etcd_prefix

# fixture, do not delete
from tests.test_backend_etcd3 import etcd3

PREFIX = "/__test_cli"


def _test_cli_command(argv, message=None):
    with patch("logging.Logger.info") as mock_log:
        cli.main(argv)

    if isinstance(message, str):
        mock_log.assert_called_with(message)

    elif isinstance(message, list):
        mock_log.assert_has_calls(message)


def _delete_test_pb():
    cfg = config.Config(global_prefix=PREFIX)
    for txn in cfg.txn():
        for key in txn.raw.list_keys(PREFIX, recurse=8):
            txn.raw.delete(key)


def test_cli_simple():

    if os.getenv("SDP_TEST_HOST") is not None:
        os.environ["SDP_CONFIG_HOST"] = os.getenv("SDP_TEST_HOST")

    _test_cli_command(['delete', '-R', PREFIX])

    _test_cli_command(['get', PREFIX+'/test'], PREFIX+"/test = None")
    _test_cli_command(['create', PREFIX+'/test', 'asdf'], "OK")
    _test_cli_command(['get', PREFIX+'/test'], PREFIX+"/test = asdf")
    _test_cli_command(['update', PREFIX+'/test', 'asd'], "OK")
    _test_cli_command(['get', PREFIX+'/test'], PREFIX+"/test = asd")
    _test_cli_command(['-q', 'get', PREFIX+'/test'], "asd")
    _test_cli_command(['delete', PREFIX+'/test'], "OK")


def test_cli_simple2():

    if os.getenv("SDP_TEST_HOST") is not None:
        os.environ["SDP_CONFIG_HOST"] = os.getenv("SDP_TEST_HOST")

    _test_cli_command(['create', PREFIX+'/test', 'asdf'], "OK")
    _test_cli_command(['create', PREFIX+'/foo', 'bar'], "OK")
    _test_cli_command(['ls', PREFIX+'/'],
                      [call(f"Keys with {PREFIX}/ prefix:"),
                       call(f"{PREFIX}/foo"),
                       call(f"{PREFIX}/test")])
    _test_cli_command(['-q', 'list', PREFIX+'/'],
                      "{pre}/foo {pre}/test".format(pre=PREFIX))
    _test_cli_command(['--prefix', PREFIX, 'process', 'realtime:test:0.1'],
                      "OK, pb_id = pb-sdpcfg-{}-00000".format(
                          date.today().strftime('%Y%m%d')))
    _test_cli_command(['delete', PREFIX+'/test'], "OK")
    _test_cli_command(['delete', PREFIX+'/foo'], "OK")

    _delete_test_pb()


@pytest.fixture
@patch("ska_sdp_config.config.Config._determine_backend")
def backend_with_data(mock_backend, etcd3):
    mock_backend.return_value = etcd3
    cfg = config.Config(global_prefix=etcd_prefix)
    path = f"{etcd_prefix}/my_path"
    for txn in cfg.txn():
        try:
            txn.raw.create(path, "MyValue")
            txn.raw.create(path+"/nested_dir", "HiddenValue")
        except ConfigCollision:
            # if still in db, do not recreate
            pass

    return cfg, path


@pytest.mark.parametrize("quiet, expected_log", [
    (False, f"{etcd_prefix}/my_path = MyValue"),
    (True, "MyValue")
])
def test_cmd_get(quiet, expected_log, backend_with_data):
    cfg = backend_with_data[0]
    path = backend_with_data[1]

    args = {
        "--quiet": quiet
    }

    with patch("logging.Logger.info") as mock_log:
        for txn in cfg.txn():
            cmd_get(txn, path, args)

        mock_log.assert_called_with(expected_log)


@pytest.mark.parametrize("path, r, quiet, values, expected_calls", [
    # (f"{etcd_prefix}", False, False, False, [
    #     call(f"Keys with {etcd_prefix} prefix:"),
    #     call(f"{etcd_prefix}/my_path")
    # ]),  # note: this version doesn't work, it also doesn't work if path is /
    (f"{etcd_prefix}/", False, False, False, [
        call(f"Keys with {etcd_prefix}/ prefix:"),
        call(f"{etcd_prefix}/my_path")
    ]),  # note: this works because there's a / at the end of the path
    # (f"{etcd_prefix}/", False, False, True, [
    #     call(f"{etcd_prefix}/ path is not a full path, doesn't have values."),
    # ]),  # note: doesn't work well, it should maybe say this is not a full path,
    #   so can't get value, but not return nothing
    (f"{etcd_prefix}/my_path", False, False, True, [
        call(f"{etcd_prefix}/my_path = MyValue"),
    ]),  # this is full path, a key with a value
    # (f"{etcd_prefix}", False, True, False, [
    #     call(f"{etcd_prefix}/my_path")
    # ]),  # note: doesn't return sub dirs in path, expected to return a list of dirs within path
    #   fails if missing / at end of path, but also fails when path is root (/)
    (f"{etcd_prefix}/", False, True, False, [
        call(f"{etcd_prefix}/my_path")
    ]),  # note: this works because path ends on /
    (f"{etcd_prefix}", True, False, False, [
        call(f"Keys with {etcd_prefix} prefix:"),
        call(f"{etcd_prefix}/my_path"),
        call(f"{etcd_prefix}/my_path/nested_dir")
    ]),  # note: works with and without the trailing / in path because -R == True
    # (f"{etcd_prefix}", False, True, True, [
    #     call(f"{etcd_prefix} path is not a full path, doesn't have values.")
    # ]),
    (f"{etcd_prefix}/my_path", False, True, True, [
        call("MyValue")
    ]),  # this is full path, a key with a value
    (f"{etcd_prefix}", True, False, True, [
        call(f"Keys with {etcd_prefix} prefix:"),
        call(f"{etcd_prefix}/my_path = MyValue"),
        call(f"{etcd_prefix}/my_path/nested_dir = HiddenValue")
    ]),  # note: works with and without trailing /, and for root too, because -R == True
    (f"{etcd_prefix}/", True, True, False, [
        call(f"{etcd_prefix}/my_path {etcd_prefix}/my_path/nested_dir")
    ]),  # note: if / not added, it'll match everything that starts with the given path
    (f"{etcd_prefix}/", True, True, True, [
        call("MyValue HiddenValue")
    ]),  # note: if / not added, it'll match everything that starts with the given path
])
def test_cmd_list(path, r, quiet, values, expected_calls, backend_with_data):
    cfg = backend_with_data[0]

    args = {
        "-R": r,
        "--quiet": quiet,
        "values": values,
    }

    with patch("logging.Logger.info") as mock_log:
        for txn in cfg.txn():
            cmd_list(txn, path, args)

        mock_log.assert_has_calls(expected_calls)


def test_cmd_create(backend_with_data):
    cfg = backend_with_data[0]
    key = f"{etcd_prefix}/new_path"
    value = "EnteredValue"

    for txn in cfg.txn():
        cmd_create(txn, key, value, {})

    for txn in cfg.txn():
        assert key in txn.raw.list_keys(f"{etcd_prefix}", recurse=1)
        assert txn.raw.get(key) == "EnteredValue"


def test_cmd_update(backend_with_data):
    cfg = backend_with_data[0]
    path = backend_with_data[1]

    for txn in cfg.txn():
        assert txn.raw.get(path) == "MyValue"

    for txn in cfg.txn():
        cmd_update(txn, path, "new_value", {})

    for txn in cfg.txn():
        assert txn.raw.get(path) == "new_value"


@pytest.mark.parametrize("r", [True, False])
def test_cmd_delete(r, backend_with_data):
    """
    Why is the answer the same? what's the point of allowing for -R?
    """
    cfg = backend_with_data[0]
    path = backend_with_data[1]

    args = {
        "-R": r,
        "--quiet": True
    }
    for txn in cfg.txn():
        assert txn.raw.get(path) is not None

    for txn in cfg.txn():
        cmd_delete(txn, path, args)

    for txn in cfg.txn():
        assert txn.raw.get(path) is None


def test_cmd_create_pb(backend_with_data):
    cfg = backend_with_data[0]

    workflow = {
        "type": "batch",
        "id": "my-workflow",
        "version": "0.1.1"
    }

    parameters = '{"param1": "my_param"}'

    for txn in cfg.txn():
        pb_id = cmd_create_pb(txn, workflow, parameters, {})

    result_path = f"{etcd_prefix}/pb/{pb_id}"
    for txn in cfg.txn():
        result = json.loads(txn.raw.get(result_path))
        assert result["workflow"] == workflow
        assert result["parameters"] == json.loads(parameters)

    for txn in cfg.txn():
        txn.raw.delete(result_path)
