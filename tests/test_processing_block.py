"""High-level API tests on processing blocks."""

import os
import pytest

from ska_sdp_config import config, entity, ConfigCollision

# pylint: disable=missing-docstring,redefined-outer-name

PREFIX = "/__test_pb"

WORKFLOW = {"type": "realtime", "id": "test_rt_workflow", "version": "0.0.1"}


# pylint: disable=duplicate-code
@pytest.fixture(scope="session")
def cfg():
    host = os.getenv("SDP_TEST_HOST", "127.0.0.1")
    with config.Config(global_prefix=PREFIX, host=host) as cfg:
        cfg.backend.delete(PREFIX, must_exist=False, recursive=True)
        yield cfg
        cfg.backend.delete(PREFIX, must_exist=False, recursive=True)


def test_simple_pb():

    for missing in ["id", "version", "type"]:
        with pytest.raises(ValueError, match="Workflow must"):
            workflow = dict(WORKFLOW)
            del workflow[missing]
            entity.ProcessingBlock("foo-bar", None, workflow)
    with pytest.raises(ValueError, match="Processing block ID"):
        entity.ProcessingBlock("asd_htb", None, WORKFLOW)
    with pytest.raises(ValueError, match="Processing block ID"):
        entity.ProcessingBlock("foo/bar", None, WORKFLOW)

    pblock = entity.ProcessingBlock("foo-bar", None, WORKFLOW)
    # pylint: disable=W0123
    assert pblock == eval("entity." + repr(pblock))


def test_create_pblock(cfg):

    # Create 3 processing blocks
    for txn in cfg.txn():

        pblock1_id = txn.new_processing_block_id("test")
        pblock1 = entity.ProcessingBlock(pblock1_id, None, WORKFLOW)
        assert txn.get_processing_block(pblock1_id) is None
        txn.create_processing_block(pblock1)
        with pytest.raises(ConfigCollision):
            txn.create_processing_block(pblock1)
        assert txn.get_processing_block(pblock1_id).id == pblock1_id

        pblock2_id = txn.new_processing_block_id("test")
        pblock2 = entity.ProcessingBlock(pblock2_id, None, WORKFLOW)
        txn.create_processing_block(pblock2)

        pblock_ids = txn.list_processing_blocks()
        assert pblock_ids == [pblock1_id, pblock2_id]

    # Make sure that it stuck
    for txn in cfg.txn():
        pblock_ids = txn.list_processing_blocks()
        assert pblock_ids == [pblock1_id, pblock2_id]

    # Make sure we can update them
    for txn in cfg.txn():
        pblock1.parameters["test"] = "test"
        pblock1.dependencies.append({"pblockId": pblock2_id, "type": []})
        txn.update_processing_block(pblock1)

    # Check that update worked
    for txn in cfg.txn():
        pblock1x = txn.get_processing_block(pblock1.id)
        assert pblock1x.sbi_id is None
        assert pblock1x.parameters == pblock1.parameters
        assert pblock1x.dependencies == pblock1.dependencies


def test_take_pblock(cfg):

    workflow2 = dict(WORKFLOW)
    workflow2["id"] += "-take"

    # Create another processing block
    for txn in cfg.txn():

        pblock_id = txn.new_processing_block_id("test")
        pblock = entity.ProcessingBlock(pblock_id, None, workflow2)
        txn.create_processing_block(pblock)

    with cfg.lease() as lease:

        for txn in cfg.txn():
            txn.take_processing_block(pblock_id, lease)

        for txn in cfg.txn():
            assert txn.get_processing_block_owner(pblock_id) == cfg.owner
            assert txn.is_processing_block_owner(pblock_id)

    for txn in cfg.txn():
        assert txn.get_processing_block_owner(pblock_id) is None
        assert not txn.is_processing_block_owner(pblock_id)


def test_pblock_state(cfg):

    pblock_id = "teststate-00000000-0000"
    state1 = {
        "resources_available": True,
        "state": "RUNNING",
        "receive_addresses": {"1": {"1": ["0.0.0.0", 1024]}},
    }
    state2 = {
        "resources_available": True,
        "state": "FINISHED",
        "receive_addresses": {"1": {"1": ["0.0.0.0", 1024]}},
    }

    # Create processing block
    for txn in cfg.txn():
        pblock = entity.ProcessingBlock(pblock_id, None, WORKFLOW)
        txn.create_processing_block(pblock)

    # Check PBLOCK state is None
    for txn in cfg.txn():
        state_out = txn.get_processing_block_state(pblock_id)
        assert state_out is None

    # Create PBLOCK state as state1
    for txn in cfg.txn():
        txn.create_processing_block_state(pblock_id, state1)

    # Read PBLOCK state and check it matches state1
    for txn in cfg.txn():
        state_out = txn.get_processing_block_state(pblock_id)
        assert state_out == state1

    # Try to create PBLOCK state again and check it raises a collision exception
    for txn in cfg.txn():
        with pytest.raises(ConfigCollision):
            txn.create_processing_block_state(pblock_id, state1)

    # Update PBLOCK state to state2
    for txn in cfg.txn():
        txn.update_processing_block_state(pblock_id, state2)

    # Read PBLOCK state and check it now matches state2
    for txn in cfg.txn():
        state_out = txn.get_processing_block_state(pblock_id)
        assert state_out == state2


if __name__ == "__main__":
    pytest.main()
