"""Tests for sdpcfg command line utility."""

# pylint: disable=missing-docstring

import os
from datetime import date
import pytest

from ska_sdp_config import cli

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


if __name__ == '__main__':
    pytest.main()
