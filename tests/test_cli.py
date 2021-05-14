"""Tests for sdpcfg command line utility."""

# pylint: disable=missing-docstring
import json
import os
from datetime import date
from unittest.mock import patch, call

import pytest

from ska_sdp_config import cli, config, ConfigCollision
from ska_sdp_config.cli import cmd_get, cmd_list, cmd_create, cmd_update, cmd_delete, cmd_create_pb
from tests.test_backend_etcd3 import PREFIX as etcd_prefix

# fixture, do not delete
from tests.test_backend_etcd3 import etcd3


PREFIX = "/__test_cli"


def _test_cli_command(capsys, argv,
                      expected_stdout=None, expected_stderr=None):

    cli.main(argv)
    out, err = capsys.readouterr()
    if expected_stdout is not None:
        assert out == expected_stdout
    if expected_stderr is not None:
        assert err == expected_stderr


def test_cli_simple(capsys):

    if os.getenv("SDP_TEST_HOST") is not None:
        os.environ["SDP_CONFIG_HOST"] = os.getenv("SDP_TEST_HOST")

    _test_cli_command(capsys, ['delete', '-R', PREFIX])

    _test_cli_command(capsys, ['get', PREFIX+'/test'], PREFIX+"/test = None\n", "")
    _test_cli_command(capsys, ['create', PREFIX+'/test', 'asdf'], "OK\n", "")
    _test_cli_command(capsys, ['get', PREFIX+'/test'], PREFIX+"/test = asdf\n", "")
    _test_cli_command(capsys, ['update', PREFIX+'/test', 'asd'], "OK\n", "")
    _test_cli_command(capsys, ['get', PREFIX+'/test'], PREFIX+"/test = asd\n", "")
    _test_cli_command(capsys, ['-q', 'get', PREFIX+'/test'], "asd\n", "")
    _test_cli_command(capsys, ['delete', PREFIX+'/test'], "OK\n", "")


def test_cli_simple2(capsys):

    if os.getenv("SDP_TEST_HOST") is not None:
        os.environ["SDP_CONFIG_HOST"] = os.getenv("SDP_TEST_HOST")

    _test_cli_command(capsys, ['create', PREFIX+'/test', 'asdf'], "OK\n", "")
    _test_cli_command(capsys, ['create', PREFIX+'/foo', 'bar'], "OK\n", "")
    _test_cli_command(capsys, ['ls', PREFIX+'/'],
                      "Keys with {pre}/ prefix:\n{pre}/foo\n{pre}/test\n".format(
                          pre=PREFIX), "")
    _test_cli_command(capsys, ['-q', 'list', PREFIX+'/'],
                      "{pre}/foo {pre}/test\n".format(pre=PREFIX),
                      "")
    _test_cli_command(capsys, ['--prefix', PREFIX, 'process', 'realtime:test:0.1'],
                      "OK, pb_id = pb-sdpcfg-{}-00000\n".format(
                          date.today().strftime('%Y%m%d')), "")
    _test_cli_command(capsys, ['delete', PREFIX+'/test'], "OK\n", "")
    _test_cli_command(capsys, ['delete', PREFIX+'/foo'], "OK\n", "")


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
