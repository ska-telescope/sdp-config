"""Tests for sdpcfg command line utility."""

# pylint: disable=missing-docstring
# pylint: disable=redefined-outer-name
# pylint: disable=unused-import

import json
import os
from datetime import date
from unittest.mock import patch, call

import pytest

from ska_sdp_config import cli, config, ConfigCollision, ConfigVanished
from ska_sdp_config.ska_sdp_cli.sdp_delete import cmd_delete
from ska_sdp_config.ska_sdp_cli.sdp_import import parse_definitions, import_workflows
from ska_sdp_config.ska_sdp_cli.sdp_update import cmd_update
from ska_sdp_config.ska_sdp_cli.sdp_create import cmd_create, cmd_create_pb, cmd_deploy
from ska_sdp_config.ska_sdp_cli.sdp_list import cmd_list
from ska_sdp_config.ska_sdp_cli.sdp_get import cmd_get
from tests.test_backend_etcd3 import PREFIX as etcd_prefix

# fixture, do not delete
from tests.test_backend_etcd3 import etcd3

PREFIX = "/__test_cli"

STRUCTURED_WORKFLOW = {
    "about": ["SDP Processing Controller workflow definitions"],
    "version": {"date-time": "2021-05-14T16:00:00Z"},
    "repositories": [
        {"name": "nexus", "path": "some-repo/sdp-prototype"}
    ],
    "workflows": [
        {
            "type": "batch",
            "id": "test_batch",
            "repository": "nexus",
            "image": "workflow-test-batch",
            "versions": ["0.2.2"],
        },
        {
            "type": "realtime",
            "id": "test_realtime",
            "repository": "nexus",
            "image": "workflow-test-realtime",
            "versions": ["0.2.2"],
        },
    ],
}

FLAT_WORKFLOW = {
    "workflows": [
        {
            "type": "realtime",
            "id": "test_realtime",
            "version": "0.2.2",
            "image": "some-repo/sdp-prototype/workflow-test-realtime:0.2.2",
        },
        {
            "type": "batch",
            "id": "test_batch",
            "version": "0.2.2",
            "image": "some-repo/sdp-prototype/workflow-test-batch:0.2.2",
        },
    ]
}


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

    _test_cli_command(["delete", "-R", PREFIX])

    _test_cli_command(
        ["get", PREFIX + "/test"], [call("%s = %s", PREFIX + "/test", None)]
    )
    _test_cli_command(["create", PREFIX + "/test", "asdf"], "OK")
    _test_cli_command(
        ["get", PREFIX + "/test"], [call("%s = %s", PREFIX + "/test", "asdf")]
    )
    _test_cli_command(["update", PREFIX + "/test", "asd"], "OK")
    _test_cli_command(
        ["get", PREFIX + "/test"], [call("%s = %s", PREFIX + "/test", "asd")]
    )
    _test_cli_command(["-q", "get", PREFIX + "/test"], "asd")
    _test_cli_command(["delete", PREFIX + "/test"], "OK")


def test_cli_simple2():

    if os.getenv("SDP_TEST_HOST") is not None:
        os.environ["SDP_CONFIG_HOST"] = os.getenv("SDP_TEST_HOST")

    _test_cli_command(["create", PREFIX + "/test", "asdf"], "OK")
    _test_cli_command(["create", PREFIX + "/foo", "bar"], "OK")
    _test_cli_command(
        ["ls", PREFIX + "/"],
        [
            call("Keys with %s prefix:", PREFIX + "/"),
            call(f"{PREFIX}/foo"),
            call(f"{PREFIX}/test"),
        ],
    )
    _test_cli_command(
        ["-q", "list", PREFIX + "/"], "{pre}/foo {pre}/test".format(pre=PREFIX)
    )
    _test_cli_command(
        ["--prefix", PREFIX, "process", "realtime:test:0.1"],
        [
            call(
                "OK, pb_id = %s",
                "pb-sdpcfg-{}-00000".format(date.today().strftime("%Y%m%d")),
            )
        ],
    )
    _test_cli_command(["delete", PREFIX + "/test"], "OK")
    _test_cli_command(["delete", PREFIX + "/foo"], "OK")

    _delete_test_pb()


@pytest.fixture
@patch("ska_sdp_config.config.Config._determine_backend")
def temp_cfg(mock_backend, etcd3):
    """
    Fixture of temporary config backend, with data in the db,
    which are deleted after the test(s) finished executing.

    Uses the etcd3 fixture.
    """
    mock_backend.return_value = etcd3
    cfg = config.Config(global_prefix=etcd_prefix)

    for txn in cfg.txn():
        try:
            txn.raw.create(f"{etcd_prefix}/my_path", "MyValue")
            txn.raw.create(f"{etcd_prefix}/pb/pb-20210101-test/state", '{"pb": "info"}')
            txn.raw.create(f"{etcd_prefix}/pb/pb-20220101-test/state", '{"pb": "info"}')
            txn.raw.create(
                f"{etcd_prefix}/workflow/batch:test:0.0.0", '{"image": "image"}'
            )
            txn.raw.create(
                f"{etcd_prefix}/workflow/batch:test:0.0.1", '{"image": "image"}'
            )
        except ConfigCollision:
            # if still in db, do not recreate
            pass

    return cfg


@pytest.mark.parametrize(
    "quiet, expected_log",
    [
        (None, [call("%s = %s", f"{etcd_prefix}/my_path", "MyValue")]),
        (True, [call("MyValue")]),
    ],
)
def test_cmd_get(quiet, expected_log, temp_cfg):
    """
    Correct information is logged whether the --quiet switch is set to True or not.
    """
    path = f"{etcd_prefix}/my_path"
    args = {"--quiet": quiet}

    with patch("logging.Logger.info") as mock_log:
        for txn in temp_cfg.txn():
            cmd_get(txn, path, args)

        assert mock_log.call_args_list == expected_log


@pytest.mark.parametrize(
    "quiet, values, expected_calls",
    [
        (
            True,
            False,
            [
                call(f"{etcd_prefix}/my_path"),
                call(f"{etcd_prefix}/pb/pb-20210101-test/state"),
                call(f"{etcd_prefix}/pb/pb-20220101-test/state"),
                call(f"{etcd_prefix}/workflow/batch:test:0.0.0"),
                call(f"{etcd_prefix}/workflow/batch:test:0.0.1"),
            ],
        ),  # list --all without values
        (
            True,
            True,
            [
                call("MyValue"),
                call('{"pb": "info"}'),
                call('{"pb": "info"}'),
                call('{"image": "image"}'),
                call('{"image": "image"}'),
            ],
        ),  # list --all with values
        (
            False,
            False,
            [
                call("Keys with prefix %s: ", etcd_prefix + "/"),
                call(f"{etcd_prefix}/my_path"),
                call(f"{etcd_prefix}/pb/pb-20210101-test/state"),
                call(f"{etcd_prefix}/pb/pb-20220101-test/state"),
                call(f"{etcd_prefix}/workflow/batch:test:0.0.0"),
                call(f"{etcd_prefix}/workflow/batch:test:0.0.1"),
            ],
        ),
    ],
)
def test_cmd_list_all(quiet, values, expected_calls, temp_cfg):
    """
    cmd_list correctly lists all of the contents of the Config DB.
    """
    # ska-sdp uses -R=True, and is not changeable there, so we only test that here
    # -R=False doesn't behave well, if we want -R=False,
    # that will need to be added and tested separately
    args = {
        "-R": True,
        "--quiet": quiet,
        "--values": values,
        "pb": None,
        "workflow": None,
        "<date>": None,
        "<type>": None,
    }

    path = f"{etcd_prefix}/"

    with patch("logging.Logger.info") as mock_log:
        for txn in temp_cfg.txn():
            cmd_list(txn, path, args)

        assert mock_log.call_args_list == expected_calls


@pytest.mark.parametrize(
    "quiet, values, pb_date, expected_calls",
    [
        (
            True,
            False,
            "20210101",
            [call(f"{etcd_prefix}/pb/pb-20210101-test/state")],
        ),  # pb for date in Config DB
        (True, False, "20210102", []),  # pb for date not in Config DB
        (
            True,
            False,
            None,
            [
                call(f"{etcd_prefix}/pb/pb-20210101-test/state"),
                call(f"{etcd_prefix}/pb/pb-20220101-test/state"),
            ],
        ),  # not searching specific pb
        (
            False,
            True,
            "20210101",
            [
                call("Processing blocks for date %s: ", "20210101"),
                call(
                    "%s = %s",
                    f"{etcd_prefix}/pb/pb-20210101-test/state",
                    '{"pb": "info"}',
                ),
            ],
        ),  # pb for date with values
    ],
)
def test_cmd_list_pb(quiet, values, pb_date, expected_calls, temp_cfg):
    """
    cmd_list correctly lists processing block (pb) related content.
    """
    # ska-sdp uses -R=True, and is not changeable there, so we only test that here
    # -R=False doesn't behave well, if we want -R=False,
    # that will need to be added and tested separately
    args = {
        "-R": True,
        "--quiet": quiet,
        "--values": values,
        "pb": True,
        "workflow": None,
        "<date>": pb_date,
        "<type>": None,
    }
    path = f"{etcd_prefix}/pb"

    with patch("logging.Logger.info") as mock_log:
        for txn in temp_cfg.txn():
            cmd_list(txn, path, args)

        assert mock_log.call_args_list == expected_calls


@pytest.mark.parametrize(
    "quiet, values, wf_type, expected_calls",
    [
        (
            True,
            False,
            "batch",
            [
                call(f"{etcd_prefix}/workflow/batch:test:0.0.0"),
                call(f"{etcd_prefix}/workflow/batch:test:0.0.1"),
            ],
        ),  # workflow with type in db
        (True, False, "relatime", []),  # workflow with type not in db
        (
            True,
            False,
            None,
            [
                call(f"{etcd_prefix}/workflow/batch:test:0.0.0"),
                call(f"{etcd_prefix}/workflow/batch:test:0.0.1"),
            ],
        ),  # not searching specific workflow
        (
            False,
            True,
            "batch",
            [
                call("Workflow definitions of type %s: ", "batch"),
                call(
                    "%s = %s",
                    f"{etcd_prefix}/workflow/batch:test:0.0.0",
                    '{"image": "image"}',
                ),
                call(
                    "%s = %s",
                    f"{etcd_prefix}/workflow/batch:test:0.0.1",
                    '{"image": "image"}',
                ),
            ],
        ),  # pb for date with values
    ],
)
def test_cmd_list_workflow(quiet, values, wf_type, expected_calls, temp_cfg):
    """
    cmd_list correctly lists workflow definition related content.
    """
    # ska-sdp uses -R=True, and is not changeable there, so we only test that here
    # -R=False doesn't behave well, if we want -R=False,
    # that will need to be added and tested separately
    args = {
        "-R": True,
        "--quiet": quiet,
        "--values": values,
        "pb": None,
        "workflow": True,
        "<date>": None,
        "<type>": wf_type,
    }
    path = f"{etcd_prefix}/workflow"

    with patch("logging.Logger.info") as mock_log:
        for txn in temp_cfg.txn():
            cmd_list(txn, path, args)

        assert mock_log.call_args_list == expected_calls


def test_cmd_create(temp_cfg):
    """
    cmd_create correctly creates key-value pairs.
    """
    key = f"{etcd_prefix}/new_path"
    value = "EnteredValue"

    for txn in temp_cfg.txn():
        cmd_create(txn, key, value, {})

    for txn in temp_cfg.txn():
        assert key in txn.raw.list_keys(f"{etcd_prefix}", recurse=1)
        assert txn.raw.get(key) == "EnteredValue"


def test_cmd_create_pb(temp_cfg):
    """
    cmd_create_pb correctly creates a processing block with the supplied workflow information.
    """
    workflow = {"type": "batch", "id": "my-workflow", "version": "0.1.1"}

    parameters = '{"param1": "my_param"}'

    for txn in temp_cfg.txn():
        pb_id = cmd_create_pb(txn, workflow, parameters, {})

    result_path = f"{etcd_prefix}/pb/{pb_id}"
    for txn in temp_cfg.txn():
        result = json.loads(txn.raw.get(result_path))
        assert result["workflow"] == workflow
        assert result["parameters"] == json.loads(parameters)

    for txn in temp_cfg.txn():
        txn.raw.delete(result_path)


def test_cmd_deploy(temp_cfg):
    """
    cmd_deploy correctly creates a new deployment.
    """
    typ = "helm"
    deploy_id = "myDeployment"
    parameters = '{"chart": "my-helm-chart", "values": {}}'
    expected_key = f"{etcd_prefix}/deploy/{deploy_id}"

    for txn in temp_cfg.txn():
        cmd_deploy(txn, typ, deploy_id, parameters)

        result_keys = txn.raw.list_keys(f"{etcd_prefix}/", recurse=8)
        assert expected_key in result_keys

        depl = txn.raw.get(expected_key)
        result_depl = json.loads(depl)
        assert result_depl["id"] == deploy_id
        assert result_depl["args"] == json.loads(parameters)
        assert result_depl["type"] == typ


def test_cmd_update(temp_cfg):
    """
    cmd_update updates the key with the given value.
    """
    path = f"{etcd_prefix}/my_path"

    for txn in temp_cfg.txn():
        assert txn.raw.get(path) == "MyValue"

    for txn in temp_cfg.txn():
        cmd_update(txn, path, "new_value", {})

    for txn in temp_cfg.txn():
        assert txn.raw.get(path) == "new_value"


@pytest.mark.parametrize(
    "path, raise_err",
    [(f"{etcd_prefix}/my_path", False), (f"{etcd_prefix}/my_path/not_exist", True)],
)
def test_cmd_delete_non_recursive(path, raise_err, temp_cfg):
    """
    If recursion (-R) is not True, then only exact paths can be deleted.
    """
    args = {"-R": None, "--quiet": True}
    if not raise_err:
        for txn in temp_cfg.txn():
            assert txn.raw.get(path) is not None

        for txn in temp_cfg.txn():
            cmd_delete(txn, path, args)

        for txn in temp_cfg.txn():
            assert txn.raw.get(path) is None

    else:
        with pytest.raises(ConfigVanished) as err:
            for txn in temp_cfg.txn():
                cmd_delete(txn, path, args)

        assert str(err.value) == f"Cannot delete {path}, it does not exist!"


def test_cmd_delete_recursive(temp_cfg):
    """
    If recursion (-R) is True, everything with the prefix is deleted.
    """
    path_prefix = f"{etcd_prefix}/pb"

    args = {"-R": True, "--quiet": True}

    for txn in temp_cfg.txn():
        keys = txn.raw.list_keys(path_prefix, recurse=8)
        assert len(keys) == 2

    for txn in temp_cfg.txn():
        cmd_delete(txn, path_prefix, args)

    for txn in temp_cfg.txn():
        keys = txn.raw.list_keys(path_prefix, recurse=8)
        assert len(keys) == 0


@pytest.mark.parametrize("workflow_def",[
    STRUCTURED_WORKFLOW, FLAT_WORKFLOW
])
def test_parse_definitions_for_import(workflow_def):
    """
    Parse workflow definitions from structured and from flat dictionaries.
    """
    result = parse_definitions(workflow_def)
    expected_keys = [("batch", "test_batch", "0.2.2"), ("realtime", "test_realtime", "0.2.2")]
    expected_values = ["some-repo/sdp-prototype/workflow-test-batch:0.2.2",
                       "some-repo/sdp-prototype/workflow-test-realtime:0.2.2"]

    assert len(result) == 2
    assert sorted(list(result.keys())) == sorted(
        expected_keys
    )
    assert list(result.values())[0]["image"] in expected_values
    assert list(result.values())[1]["image"] in expected_values


@patch("ska_sdp_config.config.Config._determine_backend")
def test_import_workflows(mock_backend, etcd3):
    """
    Test that sdp_import correctly adds, updates, and deletes workflows, from input dictionary.
    """
    mock_backend.return_value = etcd3
    cfg = config.Config(global_prefix=etcd_prefix)
    # clean up before test runs
    for txn in cfg.txn():
        cmd_delete(txn, "/", {"--quiet": True, "-R": True})

    # workflows to be imported
    workflows = {
        ("batch", "test", "0.0.0"): {"image": "batch-test:0.0.0"},  # to update
        ("realtime", "test", "0.1.0"): {"image": "realtime-test:0.1.0"}  # to be inserted
    }

    # keys already in db (added in first txn loop)
    keys_in_db = [
        f"{etcd_prefix}/workflow/batch:test:0.0.0",  # to be updated
        f"{etcd_prefix}/workflow/batch:test:0.0.1"  # to be deleted
    ]
    for txn in cfg.txn():
        txn.raw.create(
            keys_in_db[0], '{"image": "image"}'
        )
        txn.raw.create(
            keys_in_db[1], '{"image": "image"}'
        )

    # double check that keys are there and value is as created above,
    # then import workflows from dict
    for txn in cfg.txn():
        assert json.loads(txn.raw.get(keys_in_db[0]))["image"] == "image"
        assert txn.raw.list_keys(f"{etcd_prefix}/workflow", recurse=8) == keys_in_db

        import_workflows(txn, workflows, sync=True, prefix=etcd_prefix)

    # keys in db after importing
    updated_keys_in_db = [
        f"{etcd_prefix}/workflow/batch:test:0.0.0",  # updated
        f"{etcd_prefix}/workflow/realtime:test:0.1.0"  # added
    ]

    # test that one key is correctly updated, one removed, and one added
    for txn in cfg.txn():
        assert json.loads(txn.raw.get(keys_in_db[0]))["image"] == "batch-test:0.0.0"
        assert txn.raw.list_keys(f"{etcd_prefix}/workflow", recurse=8) == updated_keys_in_db
