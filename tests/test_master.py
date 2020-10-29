"""High-level API tests on master device."""

import os
import pytest

import ska_sdp_config

# pylint: disable=missing-docstring,redefined-outer-name

PREFIX = "/__test_master"


# pylint: disable=W0212
@pytest.fixture(scope="session")
def cfg():
    host = os.getenv('SDP_TEST_HOST', '127.0.0.1')
    with ska_sdp_config.Config(global_prefix=PREFIX, host=host) as cfg:
        cfg.backend.delete(PREFIX, must_exist=False, recursive=True)
        yield cfg
        cfg.backend.delete(PREFIX, must_exist=False, recursive=True)


def test_master_create_update(cfg):

    state1 = {
        'state': 'OFF'
    }

    state2 = {
        'state': 'ON'
    }

    # Master has not been created, so should return None
    for txn in cfg.txn():
        state = txn.get_master()
        assert state is None

    # Create master as state1
    for txn in cfg.txn():
        txn.create_master(state1)

    # Read master and check it is equal to state1
    for txn in cfg.txn():
        state = txn.get_master()
        assert state == state1

    # Trying to recreate should raise a collision exception
    for txn in cfg.txn():
        with pytest.raises(ska_sdp_config.ConfigCollision):
            txn.create_master(state1)

    # Update master to state2
    for txn in cfg.txn():
        txn.update_master(state2)

    # Read master and check it is equal to state2
    for txn in cfg.txn():
        state = txn.get_master()
        assert state == state2
