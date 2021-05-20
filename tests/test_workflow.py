"""High-level API tests on workflow."""

import os
import pytest

import ska_sdp_config

# pylint: disable=missing-docstring,redefined-outer-name

PREFIX = "/__test_sb"
WORKFLOW_PREFIX = "/workflow"


# pylint: disable=W0212
@pytest.fixture(scope="session")
def cfg():
    host = os.getenv("SDP_TEST_HOST", "127.0.0.1")
    with ska_sdp_config.Config(global_prefix=WORKFLOW_PREFIX, host=host) as cfg:
        cfg._backend.delete(WORKFLOW_PREFIX, must_exist=False, recursive=True)
        yield cfg
        cfg._backend.delete(WORKFLOW_PREFIX, must_exist=False, recursive=True)


def test_workflow_create_update(cfg):

    WORKFLOW_TYPE = "batch"
    WORKFLOW_ID = "test_batch"
    WORKFLOW_VERSION = "0.2.1"
    WORKFLOW_IMAGE = "workflow-test-batch"

    workflow = {
        "type": WORKFLOW_TYPE,
        "id": WORKFLOW_ID,
        "repository": "nexus",
        "image": WORKFLOW_IMAGE,
        "versions": [WORKFLOW_VERSION],
    }

    workflow2 = {
        "type": "batch",
        "id": "test_realtime",
        "repository": "nexus",
        "image": "workflow-test-realtime",
        "versions": ["0.0.1"],
    }

    # Create workflow
    for txn in cfg.txn():
        txn.create_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION, workflow)

    # Read master and check it is equal to state1
    for txn in cfg.txn():
        state = txn.get_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION)
        assert state == workflow

    # Trying to recreate should raise a collision exception
    for txn in cfg.txn():
        with pytest.raises(ska_sdp_config.ConfigCollision):
            txn.create_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION, workflow)

    # Update master to state2
    for txn in cfg.txn():
        txn.update_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION, workflow2)

    # Read master and check it is equal to state2
    for txn in cfg.txn():
        state = txn.get_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION)
        assert state == workflow2

#TODO NEED TO TEST ALL WORKFLOW, TYPE AND TYPE AND ID
def test_workflow_list(cfg):

    workflow_list = ["/workflow/realtime:test_real:0.2.1"]
    WORKFLOW_TYPE = "realtime"
    WORKFLOW_ID = "test_real"
    WORKFLOW_VERSION = "0.2.1"
    WORKFLOW_IMAGE = "workflow-test-real"


    # Check the workflow list is empty
    for txn in cfg.txn():
        w_list = txn.list_workflows()
        assert w_list == []

    workflow = {
        "type": WORKFLOW_TYPE,
        "id": WORKFLOW_ID,
        "repository": "nexus",
        "image": WORKFLOW_IMAGE,
        "versions": [WORKFLOW_VERSION],
    }

    # Create workflow
    for txn in cfg.txn():
        txn.create_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION, workflow)

    # List all the workflows
    for txn in cfg.txn():
        w_list = txn.list_workflows()
        assert w_list == workflow_list

    # # List workflows with specified type
    # for txn in cfg.txn():
    #     w_list = txn.list_workflows(WORKFLOW_TYPE)
    #     assert w_list == []
    #
    #
    # # List workflows of specified type and name
    # for txn in cfg.txn():
    #     w_list = txn.list_workflows(WORKFLOW_TYPE)
    #     assert w_list == []

    # # Check scheduling block list is empty
    # for txn in cfg.txn():
    #     w_list = txn.list_workflows(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION)
    #     assert w_list == workflow_list


def test_delete_workflow(cfg):
    WORKFLOW_TYPE = "realtime"
    WORKFLOW_ID = "test_r"
    WORKFLOW_VERSION = "0.2.1"
    WORKFLOW_IMAGE = "workflow-test-r"

    workflow = {
        "type": WORKFLOW_TYPE,
        "id": WORKFLOW_ID,
        "repository": "nexus",
        "image": WORKFLOW_IMAGE,
        "versions": [WORKFLOW_VERSION],
    }

    # Create workflow
    for txn in cfg.txn():
        txn.create_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION, workflow)

    # Read master and check it is equal to state1
    for txn in cfg.txn():
        state = txn.get_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION)
        assert state == workflow

    for txn in cfg.txn():
        txn.delete_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION)

    # Read master and check it is equal to state1
    for txn in cfg.txn():
        state = txn.get_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION)
        assert state == None


if __name__ == "__main__":
    pytest.main()
