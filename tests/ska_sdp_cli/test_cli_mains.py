"""Test the main functions of the various ska-sdp commands"""
# pylint: disable=too-many-arguments

from unittest.mock import patch, Mock
import pytest
from ska_sdp_config.ska_sdp_cli import (
    ska_sdp,
    sdp_list,
    sdp_get,
    sdp_create,
    sdp_update,
    sdp_delete,
    sdp_import,
)

PATH_PREFIX = "ska_sdp_config.ska_sdp_cli"
MAIN = "main"
SKA_SDP = "ska_sdp"
SDP_LIST = "sdp_list"
SDP_GET = "sdp_get"
SDP_CREATE = "sdp_create"
SDP_UPDATE = "sdp_update"
SDP_DELETE = "sdp_delete"
SDP_IMPORT = "sdp_import"


class MockConfig:
    # pylint: disable=no-self-use
    # pylint: disable=too-few-public-methods
    """MockConfig object for testing"""

    def __init__(self):
        pass

    def txn(self):
        """Mock transaction"""
        return [
            Mock(
                raw=Mock(
                    list_keys=Mock(
                        return_value=["/pb/pb-id-333/state", "/pb/pb-id-333/owner"]
                    )
                )
            )
        ]


@pytest.mark.parametrize(
    "command, executable",
    [
        ("list", SDP_LIST),
        ("get", SDP_GET),
        ("watch", SDP_GET),
        ("create", SDP_CREATE),
        ("update", SDP_UPDATE),
        ("edit", SDP_UPDATE),
        ("delete", SDP_DELETE),
        ("import", SDP_IMPORT),
    ],
)
@patch(f"{PATH_PREFIX}.{SKA_SDP}.config")
@patch(f"{PATH_PREFIX}.{SKA_SDP}.{SDP_LIST}.{MAIN}")
@patch(f"{PATH_PREFIX}.{SKA_SDP}.{SDP_GET}.{MAIN}")
@patch(f"{PATH_PREFIX}.{SKA_SDP}.{SDP_CREATE}.{MAIN}")
@patch(f"{PATH_PREFIX}.{SKA_SDP}.{SDP_UPDATE}.{MAIN}")
@patch(f"{PATH_PREFIX}.{SKA_SDP}.{SDP_DELETE}.{MAIN}")
@patch(f"{PATH_PREFIX}.{SKA_SDP}.{SDP_IMPORT}.{MAIN}")
def test_ska_sdp_main(
    mock_sdp_import,
    mock_sdp_delete,
    mock_sdp_update,
    mock_sdp_create,
    mock_sdp_get,
    mock_sdp_list,
    mock_config,
    command,
    executable,
):
    """
    ska_sdp.main calls the correct command main function based on input argv,
    and all other commands are not called.
    """
    command_dict = {
        SDP_LIST: mock_sdp_list,
        SDP_GET: mock_sdp_get,
        SDP_CREATE: mock_sdp_create,
        SDP_UPDATE: mock_sdp_update,
        SDP_DELETE: mock_sdp_delete,
        SDP_IMPORT: mock_sdp_import,
    }

    command_dict[executable].Config().return_value = Mock()
    mock_sdp_import.return_value = Mock()

    argv = [command]

    # run tested function
    ska_sdp.main(argv)

    # the command specified in argv is called
    command_dict[executable].assert_called_with(argv, mock_config.Config())

    # none of the other commands are called
    for key, mock in command_dict.items():
        if key != executable:
            mock.assert_not_called()


@pytest.mark.parametrize(
    "options, expected_path",
    [
        ("-a", "/"),
        ("pb", "/pb"),
        ("pb 20200101", "/pb"),
        ("--quiet workflow", "/workflow"),
        ("workflow realtime", "/workflow"),
        ("-q sbi", "/sbi"),
        ("deployment", "/deploy"),
        ("--prefix=/test pb", "/test/pb"),  # with prefix
        ("--prefix=/test/ pb", "/test/pb"),  # with prefix ending on /
    ],
)
@patch(f"{PATH_PREFIX}.{SDP_LIST}.cmd_list")
def test_sdp_list_main(mock_list_cmd, options, expected_path):
    """
    cmd_list is called with the correct path constructed based on input options.
    """
    mock_list_cmd.return_value = Mock()
    config = MockConfig()
    argv = ["list"] + options.split()

    # run tested function
    sdp_list.main(argv, config)

    # [0][0] --> only one call, to get the tuple of args out of the call(),
    # need to go another layer deep
    result_calls = mock_list_cmd.call_args_list[0][0]
    assert result_calls[1] == expected_path


@pytest.mark.parametrize(
    "options, expected_args, times_called",
    [("my-key", "my-key", 1), ("pb pb-id-333", "/pb/pb-id-333/state", 2)],
)
@patch(f"{PATH_PREFIX}.{SDP_GET}.cmd_get")
def test_sdp_get_main(mock_get_cmd, options, expected_args, times_called):
    """
    cmd_get is called with the correct arguments based on input options.
    When a single key is supplied, we check that cmd_get is called with that.
    When pb is given, with its id, we check that the cmd_get is called as many times
    as keys are turned for that pb-id, and check the first key returned.
    """
    mock_get_cmd.return_value = Mock()
    config = MockConfig()
    argv = ["get"] + options.split()

    # run tested function
    sdp_get.main(argv, config)

    # [0][0] --> 1st call, to get the tuple of args out of the call(),
    # need to go another layer deep
    result_calls = mock_get_cmd.call_args_list[0][0]

    assert result_calls[1] == expected_args
    assert len(mock_get_cmd.call_args_list) == times_called


@pytest.mark.parametrize(
    "options, cmd_to_call, expected_value",
    [
        ("workflow my-key my-workflow", 0, "/workflow/my-key"),  # expected path
        ("sbi my-key my-sbi", 0, "/sbi/my-key"),  # expected path
        (
            "pb batch:test:0.0.0",
            2,
            {"type": "batch", "id": "test", "version": "0.0.0"},
        ),  # expected workflow dict
        ("deployment MyID helm '{}'", 1, "helm"),  # expected type
    ],
)
@patch(f"{PATH_PREFIX}.{SDP_CREATE}.cmd_create_pb")
@patch(f"{PATH_PREFIX}.{SDP_CREATE}.cmd_deploy")
@patch(f"{PATH_PREFIX}.{SDP_CREATE}.cmd_create")
def test_sdp_create_main(
    mock_create_cmd,
    mock_deploy_cmd,
    mock_create_pb_cmd,
    options,
    cmd_to_call,
    expected_value,
):
    """
    Depending on what is being created, one of three commands is called,
    while the others aren't called.
    We also check that some of the arguments are correct, especially for `create pb <workflow>`,
    where the input workflow information is converted to a dict within main.
    """
    mock_create_cmd.return_value = Mock()
    config = MockConfig()

    cmd_map = {0: mock_create_cmd, 1: mock_deploy_cmd, 2: mock_create_pb_cmd}

    argv = ["create"] + options.split()

    # run tested function
    sdp_create.main(argv, config)

    cmd_map[cmd_to_call].assert_called()
    for i, cmd in cmd_map.items():
        if i != cmd_to_call:
            cmd.assert_not_called()

    result_calls = cmd_map[cmd_to_call].call_args_list[0][0]
    assert result_calls[1] == expected_value


@pytest.mark.parametrize(
    "cmd_to_run, options, expected_key",
    [
        (
            "update",
            "--quiet workflow /workflow/batch:test:0.0.0 new-data",
            "/workflow/batch:test:0.0.0",
        ),
        ("update", "pb-state pb-20201010-test new-data", "/pb/pb-20201010-test/state"),
        ("edit", "workflow /workflow/batch:test:0.0.0", "/workflow/batch:test:0.0.0"),
        ("edit", "pb-state pb-20201010-test", "/pb/pb-20201010-test/state"),
    ],
)
@patch(f"{PATH_PREFIX}.{SDP_UPDATE}.cmd_update")
@patch(f"{PATH_PREFIX}.{SDP_UPDATE}.cmd_edit")
def test_sdp_update_main(
    mock_edit_cmd, mock_update_cmd, cmd_to_run, options, expected_key
):
    """
    cmd_update, and cmd_edit are called with the correct keys.
    """
    mock_update_cmd.return_value = Mock()
    mock_edit_cmd.return_value = Mock()
    config = MockConfig()

    cmd_map = {"update": mock_update_cmd, "edit": mock_edit_cmd}

    argv = [cmd_to_run] + options.split()

    # run tested function
    sdp_update.main(argv, config)

    cmd_map[cmd_to_run].assert_called_once()
    for cmd, mock in cmd_map.items():
        if cmd != cmd_to_run:
            mock.assert_not_called()

    result_calls = cmd_map[cmd_to_run].call_args_list[0][0]
    assert result_calls[1] == expected_key


@pytest.mark.parametrize(
    "options, expected_path, log_message",
    [
        ("--all pb", "/pb", ["type", "pb"]),
        ("--all --prefix=/test pb", "/test/pb", ["prefix", "/test"]),
        ("--all --prefix=/test prefix", "/test", ["prefix", "/test"]),
        ("deployment depID", "/deploy/depID", False),
        ("workflow batch:test:0.0.0", "/workflow/batch:test:0.0.0", False),
        ("--prefix=/test/ deployment depID", "/test/deploy/depID", False),
    ],
)
@patch(f"{PATH_PREFIX}.{SDP_DELETE}.cmd_delete")
@patch(f"{PATH_PREFIX}.{SDP_DELETE}._get_input", Mock(return_value="yes"))
def test_sdp_delete_main(mock_delete_cmd, options, expected_path, log_message):
    """
    sdp_delete logs warning when -a / --all is set.
    Continue is always "yes" --> cmd_delete is called with correct path.
    cmd_delete is called with correct path.
    """
    mock_delete_cmd.return_value = Mock()
    config = MockConfig()
    argv = ["delete"] + options.split()

    with patch("logging.Logger.warning") as mock_log:
        # run tested function
        sdp_delete.main(argv, config)

    if log_message:
        result_log = mock_log.call_args_list[0][0]
        assert log_message[0] in result_log[0]
        assert result_log[1] == log_message[1]

    result_calls = mock_delete_cmd.call_args_list[0][0]
    assert result_calls[1] == expected_path


@pytest.mark.parametrize(
    "options, sync",
    [
        (["import", "workflows", "my-file"], False),
        (["import", "workflows", "--sync", "my-file"], True),
    ],
)
@patch(f"{PATH_PREFIX}.{SDP_IMPORT}.import_workflows")
@patch(f"{PATH_PREFIX}.{SDP_IMPORT}.read_input", Mock())
@patch(f"{PATH_PREFIX}.{SDP_IMPORT}.parse_definitions", Mock())
def test_sdp_import_main(mock_import_workflows, options, sync):
    """
    sdp_import executes correctly with both --sync True and False
    """
    mock_import_workflows.return_value = Mock()
    config = MockConfig()
    argv = options

    # run tested function
    sdp_import.main(argv, config)

    # [0][1] --> [1] contains the optional arguments, like --sync
    result_calls = mock_import_workflows.call_args_list[0][1]
    assert result_calls["sync"] == sync
