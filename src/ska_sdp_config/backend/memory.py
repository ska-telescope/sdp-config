"""
Memory backend for SKA SDP configuration DB.

The main purpose of this is for use in testing.
In principle it should behave in the same way as the etcd backend.
No attempt has been made to make it thread-safe, so it probably isn't.
"""
from typing import List, Callable

from .common import (
    _depth,
    _tag_depth,
    _untag_depth,
    _check_path,
    ConfigCollision,
    ConfigVanished,
)


def _op(
    path: str,
    value: str,
    to_check: Callable[[str], None],
    to_do: Callable[[str, str], None],
):
    _check_path(path)
    tag = _tag_depth(path)
    to_check(tag)
    to_do(tag, value)


class MemoryBackend:
    """In-memory backend implementation, principally for testing."""

    # Class variable to store data
    _data = {}

    def __init__(self):
        """Construct a memory backend."""
        return

    def lease(self, *_args, **_kwargs) -> "Lease":  # pylint: disable=no-self-use
        """
        Generate a dummy lease object.

        This currently has no additional methods.

        :param args: arbitrary, not used
        :param kwargs: arbitrary, not used
        :returns: dummy lease object
        """

        class Lease:  # pylint: disable=too-few-public-methods
            """Dummy lease class."""

            def __enter__(self):
                """Dummy enter method."""

            def __exit__(self, exc_type, exc_val, exc_tb):
                """Dummy exit method."""

        return Lease()

    def txn(self, *_args, **_kwargs) -> "MemoryTransaction":
        """
        Create an in-memory "transaction".

        :param args: arbitrary, not used
        :param kwargs: arbitrary, not used
        :returns: transaction object
        """
        return MemoryTransaction(self)

    def watcher(self, timeout, txn_wrapper, *args, **kwargs):
        """
        Create an in-memory "watcher".

        :param args: arbitrary arguments for mocking method behaviour
        :param kwargs: arbitrary keyword arguments for mocking method behaviour
        :returns: MemoryWatcher object (mock of Etcd3Watcher)
        """
        # pylint: disable=unused-argument
        return MemoryWatcher(txn_wrapper, self, *args, **kwargs)

    def get(self, path: str) -> str:
        """
        Get the value at the given path.

        :param path: to lookup
        :returns: the value
        """
        return self._data.get(_tag_depth(path), None)

    def _put(self, path: str, value: str) -> None:
        self._data[path] = value

    def _check_exists(self, path: str) -> None:
        if path not in self._data.keys():
            raise ConfigVanished(path, "{} not in dictionary".format(path))

    def _check_not_exists(self, path: str) -> None:
        if path in self._data.keys():
            raise ConfigCollision(path, "path {} already in dictionary".format(path))

    def create(self, path: str, value: str, *_args, **_kwargs) -> None:
        """
        Create an entry at the given path.

        :param path: to create an entry
        :param value: of the entry
        :param args: arbitrary, not used
        :param kwargs: arbitrary, not used
        :returns: nothing
        """
        _op(path, value, self._check_not_exists, self._put)

    def update(self, path: str, value: str, *_args, **_kwargs) -> None:
        """
        Update an entry at the given path.

        :param path: to create an entry
        :param value: of the entry
        :param args: arbitrary, not used
        :param kwargs: arbitrary, not used
        :returns: nothing
        """
        _op(path, value, self._check_exists, self._put)

    def delete(
        self,
        path: str,
        must_exist: bool = True,
        recursive: bool = False,
        max_depth: int = 16,
    ) -> None:
        """
        Delete an entry at the given path.

        :param path: to create an entry
        :param value: of the entry
        :param must_exist: if true, gives an error if doesn't exist
        :param recursive: Delete children keys at lower levels recursively
        :param max_depth: maximum depth of recursion
        :returns: nothing
        """
        _check_path(path)
        tag = _tag_depth(path)
        if must_exist:
            self._check_exists(tag)
        if recursive:
            depth = _depth(path)
            for lvl in range(depth, depth + max_depth):
                tag = _tag_depth(path, depth=lvl)
                for key in self._data.copy().keys():
                    if key.startswith(tag):
                        self._data.pop(key)
        elif tag in self._data.keys():
            self._data.pop(tag)

    def list_keys(self, path: str) -> List[str]:
        """
        Get a list of the keys at the given path.

        In common with the etcd backend, the structure is
        "flat" rather than a real hierarchy, even though it looks like one.

        :param path:
        :returns: list of keys
        """
        # Match only at this depth level. Special case for top level.
        if path == "/":
            new_path = path
            depth = 1
        else:
            new_path = path.rstrip("/")
            depth = _depth(new_path) + 1
        tag = _tag_depth(new_path, depth=depth)
        return sorted([_untag_depth(k) for k in self._data if k.startswith(tag)])

    def close(self) -> None:
        """
        Close the resource.

        This does nothing.

        :returns: nothing
        """

    def __repr__(self) -> str:
        return str(self._data)


class MemoryTransaction:
    """
    Transaction wrapper around the backend implementation.

    Transactions always succeed if they are valid, so there is no need
    to loop; however the iterator is supported for compatibility with
    the etcd backend.
    """

    def __init__(self, backend: MemoryBackend):
        """
        Construct an in-memory transaction.

        :param backend: to wrap
        """
        self.backend = backend

    def __iter__(self):
        """
        Iterate over just this object.

        :returns: this object
        """
        yield self

    def commit(self) -> None:
        """
        Commit the transaction.

        This does nothing.

        :returns: nothing
        """

    def get(self, path: str) -> str:
        """
        Get the value at the given path.

        :param path: to lookup
        :returns: the value
        """
        return self.backend.get(path)

    def create(self, path: str, value: str, *_args, **_kwargs) -> None:
        """
        Create an entry at the given path.

        :param path: to create an entry
        :param value: of the entry
        :param args: arbitrary, not used
        :param kwargs: arbitrary, not used
        :returns: nothing
        """
        self.backend.create(path, value)

    def update(self, path: str, value: str, *_args, **_kwargs) -> None:
        """
        Update an entry at the given path.

        :param path: to create an entry
        :param value: of the entry
        :param args: arbitrary, not used
        :param kwargs: arbitrary, not used
        :returns: nothing
        """
        self.backend.update(path, value)

    def delete(
        self, path: str, must_exist: bool = True, recursive: bool = False, **_kwargs
    ):
        """
        Delete an entry at the given path.

        :param path: to create an entry
        :param value: of the entry
        :param must_exist: if true, gives an error if doesn't exist
        :param recursive: Delete children keys at lower levels recursively
        :param kwargs: arbitrary, not used
        :returns: nothing
        """
        self.backend.delete(path, must_exist=must_exist, recursive=recursive)

    def list_keys(self, path: str, **kwargs) -> List[str]:
        """
        Get a list of the keys at the given path.

        In common with the etcd backend, the structure is
        "flat" rather than a real hierarchy, even though it looks like one.

        :param path:
        :returns: list of keys
        """
        # pylint: disable=unused-argument
        return self.backend.list_keys(path)

    def loop(self, *_args, **_kwargs) -> None:
        """
        Loop the transaction.

        This does nothing.

        :returns: nothing
        """


class MemoryWatcher:
    """
    Watcher wrapper around the backend implementation (Etcd3Watcher)
    """

    def __init__(self, txn_wrapper, backend: MemoryBackend, *args, **kwargs):
        """
        param: txn_wrapper: wrapper object, which wraps the txn object with
                            config.Transaction; needed to mitigate real behaviour
        """
        # pylint: disable=unused-argument
        self.backend = backend
        self.txn_wrapper = txn_wrapper

    def __iter__(self):
        """
        Iterate over just this object.

        :returns: this object
        """
        yield self

    def txn(self):
        """
        Yield the wrapped MemoryTransaction object

        It does not implement the commit check that is part of
        Etcd3Watcher.txn(), hence it acts as MemoryBackend.txn()
        """
        for txn in MemoryTransaction(self.backend):
            yield self.txn_wrapper(txn)
