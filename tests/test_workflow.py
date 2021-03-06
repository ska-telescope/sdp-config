"""High-level API tests on workflow."""

import os
import pytest

import ska_sdp_config

# pylint: disable=missing-docstring,redefined-outer-name

PREFIX = "/__test_workflow"
WORKFLOW_IMAGE = "nexus/workflow-test"


# pylint: disable=W0212
@pytest.fixture(scope="session")
def cfg():
    host = os.getenv("SDP_TEST_HOST", "127.0.0.1")
    with ska_sdp_config.Config(global_prefix=PREFIX, host=host) as cfg:
        cfg._backend.delete(PREFIX, must_exist=False, recursive=True)
        yield cfg
        cfg._backend.delete(PREFIX, must_exist=False, recursive=True)


def test_workflow_list_all(cfg):
    """Test list all workflows."""

    workflow_type = "realtime"
    workflow_id = "test_realtime"
    workflow_version = "0.0.1"

    workflow = {"image": f"{WORKFLOW_IMAGE}:{workflow_version}"}

    # Check the workflow list is empty
    for txn in cfg.txn():
        w_list = txn.list_workflows()
        assert w_list == []

    # Create workflow
    for txn in cfg.txn():
        txn.create_workflow(workflow_type, workflow_id, workflow_version, workflow)

    # List all the workflows
    for txn in cfg.txn():
        workflow_keys = txn.list_workflows()
        for w_type, w_id, w_version in workflow_keys:
            assert w_type == workflow_type
            assert w_id == workflow_id
            assert w_version == workflow_version


def test_workflow_list_type(cfg):
    """Test workflows with specific type."""

    workflow_type = "batch"
    workflow_id = "test_batch"
    workflow_version = "0.0.1"

    workflow = {"image": f"{WORKFLOW_IMAGE}:{workflow_version}"}

    # Create workflow
    for txn in cfg.txn():
        txn.create_workflow(workflow_type, workflow_id, workflow_version, workflow)

    # List workflows with specified type
    for txn in cfg.txn():
        workflow_keys = txn.list_workflows(workflow_type)
        for w_type, w_id, w_version in workflow_keys:
            assert w_type == workflow_type
            assert w_id == workflow_id
            assert w_version == workflow_version


def test_workflow_list_type_id(cfg):
    """Test workflows with specific type and id."""

    workflow_type = "batch"
    workflow_id = "test_vis_receive"
    workflow_version = "0.0.1"

    workflow = {"image": f"{WORKFLOW_IMAGE}:{workflow_version}"}

    # Create workflow
    for txn in cfg.txn():
        txn.create_workflow(workflow_type, workflow_id, workflow_version, workflow)

    # List workflows of specified type and name
    for txn in cfg.txn():
        workflow_keys = txn.list_workflows(workflow_type, workflow_id)
        for w_type, w_id, w_version in workflow_keys:
            assert w_type == workflow_type
            assert w_id == workflow_id
            assert w_version == workflow_version


def test_workflow_create_update(cfg):
    """Test create and update workflow."""

    workflow_type = "batch"
    workflow_id = "test_batch"
    workflow_version = "0.2.1"

    workflow = {"image": f"{WORKFLOW_IMAGE}:{workflow_version}"}
    workflow2 = {
        "image": "nexus/workflow-test-realtime:0.2.1",
    }

    # Create workflow
    for txn in cfg.txn():
        txn.create_workflow(workflow_type, workflow_id, workflow_version, workflow)

    # Read workflow and check it is equal to workflow
    for txn in cfg.txn():
        w_get = txn.get_workflow(workflow_type, workflow_id, workflow_version)
        assert w_get == workflow

    # Trying to recreate should raise a collision exception
    for txn in cfg.txn():
        with pytest.raises(ska_sdp_config.ConfigCollision):
            txn.create_workflow(workflow_type, workflow_id, workflow_version, workflow)

    # Update workflow to workflow2
    for txn in cfg.txn():
        txn.update_workflow(workflow_type, workflow_id, workflow_version, workflow2)

    # Read workflow and check it is equal to workflow2
    for txn in cfg.txn():
        w_get = txn.get_workflow(workflow_type, workflow_id, workflow_version)
        assert w_get == workflow2


def test_delete_workflow(cfg):
    """Test deleting workflow."""

    workflow_type = "realtime"
    workflow_id = "test_cbf_recv"
    workflow_version = "0.1.0"

    workflow = {"image": f"{WORKFLOW_IMAGE}:{workflow_version}"}

    # Create workflow
    for txn in cfg.txn():
        txn.create_workflow(workflow_type, workflow_id, workflow_version, workflow)

    # Read workflow and check it is equal to workflow
    for txn in cfg.txn():
        w_get = txn.get_workflow(workflow_type, workflow_id, workflow_version)
        assert w_get == workflow

    # Delete workflow
    for txn in cfg.txn():
        txn.delete_workflow(workflow_type, workflow_id, workflow_version)

    # Read workflow and check it is equal to None
    for txn in cfg.txn():
        w_get = txn.get_workflow(workflow_type, workflow_id, workflow_version)
        assert w_get is None


if __name__ == "__main__":
    pytest.main()
