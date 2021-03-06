# pylint: disable=missing-docstring,redefined-outer-name

import pytest
from ska_sdp_config.backend import ConfigVanished, ConfigCollision, MemoryBackend
from ska_sdp_config.backend.memory import MemoryTransaction
from ska_sdp_config.config import dict_to_json


@pytest.fixture
def txn() -> MemoryTransaction:
    return MemoryBackend().txn()


def test_stuff(txn: MemoryTransaction):
    txn.create("/x", "v0")
    assert txn.get("/x") == "v0"
    txn.create("/x/y", "v1")
    assert txn.get("/x/y") == "v1"
    txn.update("/x/y", "v3")
    assert txn.get("/x/y") == "v3"
    txn.create("/x/y/z", "v2")

    with pytest.raises(ConfigCollision):
        txn.create("/x/y", "v")
    with pytest.raises(ConfigVanished):
        txn.update("/y/x", "v")
    with pytest.raises(ConfigVanished):
        txn.delete("/y/x", "v")

    paths = txn.list_keys("/x")
    assert len(paths) == 1
    assert paths[0] == "/x/y"
    paths = txn.list_keys("/")
    assert len(paths) == 1
    assert paths[0] == "/x"
    txn.delete("/x")
    paths = txn.list_keys("/")
    assert len(paths) == 0

    txn.delete("/x/y/z")
    txn.delete("/x/y/z", must_exist=False)
    txn.create("/x/y/z", "v")
    txn.delete("/x", must_exist=False, recursive=True)
    assert len(txn.list_keys("/")) == 0

    txn.commit()
    txn.loop()
    assert next(iter(txn)) == txn

    assert txn.backend.lease() is not None
    txn.backend.close()


def test_state(txn: MemoryTransaction):
    txn.create("/master", dict_to_json({"state": "standby"}))
    txn.delete("/master", must_exist=False, recursive=True)
    paths = txn.list_keys("/")
    assert len(paths) == 0
