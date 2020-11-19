"""Etcd3 backend for SKA SDP configuration DB."""

# pylint: disable=fixme

import time
import queue as queue_m
from typing import Iterable, Callable

from deprecated import deprecated
import etcd3
from .common import (
    _tag_depth, _untag_depth, _check_path, ConfigCollision, ConfigVanished
)


class Etcd3Backend:
    """
    Highly consistent database backend store.

    See https://github.com/etcd-io/etcd

    All parameters will be passed on to :py:meth:`etcd3.Client`.

    """

    def __init__(self, host :str, port :int, *args, **kw_args):
        """Instantiate the database client.
        """

        # Attempting to connect via Kubernetes port-forward?
        if host.endswith('.kubernetes'):

            # Connect to Kubernetes
            from kubernetes import client, config
            config.load_kube_config()
            v1 = client.CoreV1Api()
            v1.read_namespaced_service('sdp-etcd-client', 'skampi-peter')

            # Set up forward
            from . import k8s_fwd
            import socket
            with k8s_fwd.KubernetesPortforward(v1):
                self._client = etcd3.Client(host, port, *args, **kw_args)

        else:
            self._client = etcd3.Client(host, port, *args, **kw_args)

    def lease(self, ttl :int=10) -> etcd3.Lease:
        """Generate a new lease.

        Once entered can be associated with keys, which will be kept
        alive until the end of the lease. Note that this involves
        starting a daemon thread that will refresh the lease
        periodically (default seems to be TTL/4).

        :param ttl: Time to live for lease
        :returns: lease object
        """
        return self._client.Lease(ttl=ttl)

    def txn(self, max_retries :int=64) -> Iterable["Etcd3Transaction"]:
        """Create a new transaction.

        Note that this uses an optimistic STM-style implementation,
        which cannot guarantee that a transaction runs through
        successfully.  Therefore this function returns an iterator,
        which loops until the transaction succeeds:

        .. code-block:: python

             for txn in etcd3.txn():
                 # ... transaction steps ...

        Note that this will in most cases only execute one
        iteration. If you actually want to loop - for instance because
        you intend to wait for something to happen in the
        configuration - use :py:meth:`watcher()` instead.

        :param max_retries: Maximum number of transaction loops
        :returns: Transaction iterator
        """
        for txn in Etcd3Transaction(self, self._client, max_retries):
            yield txn

    def watcher(self, timeout=None,
                txn_wrapper :Callable[["Etcd3Transaction"], object]=None) \
                -> Iterable["Etcd3Watcher"]:
        """Create a new watcher.

        Useful for waiting for changes in the configuration. See
        :py:class:`Etcd3Watcher`.

        :param timeout: Timeout for waiting. Watcher will loop after this time.
        :param txn_wrapper: Function to wrap transactions returned by the
           wrapper.
        :returns: Watcher iterator
        """
        return Etcd3Watcher(self, self._client, timeout, txn_wrapper)

    def get(self, path :str, revision :'Etcd3Revision'=None):
        """
        Get value of a key.

        :param path: Path of key to query
        :param revision: Database revision for which to read key
        :returns: (value, revision). value is None if it doesn't exist
        """
        # Check/prepare parameters
        _check_path(path)
        tagged_path = _tag_depth(path)
        rev = (None if revision is None else revision.revision)

        # Query range
        response = self._client.range(tagged_path, revision=rev)

        # Get value returned
        result = response.kvs
        mod_revision = None
        if result is not None:
            assert len(response.kvs) == 1, \
                "Requesting '{}' yielded more than one match!".format(path)
            mod_revision = result[0].mod_revision
            result = result[0].value.decode('utf-8')

        # Return value together with revision
        return (result, Etcd3Revision(response.header.revision, mod_revision))

    def watch(self, path :str, prefix :bool=False,
              revision :'Etcd3Revision'=None, depth :int=None):
        """Watch key or key range.

        Use a path ending with `'/'` in combination with `prefix` to
        watch all child keys.

        :param path: Path of key to query, or prefix of keys.
        :param prefix: Watch for keys with given prefix if set
        :param revision: Database revision from which to watch
        :returns: `Etcd3Watch` object for watch request
        """
        # Check/prepare parameters
        if not prefix and path and path[-1] == '/':
            raise ValueError("Path should not have a trailing '/'!")
        tagged_path = _tag_depth(path, depth)
        rev = (None if revision is None else revision.revision)

        # Set up watcher
        watcher = self._client.Watcher(
            tagged_path, start_revision=rev, prefix=prefix)
        return Etcd3Watch(watcher, self)

    def list_keys(self, path :str, recurse :int=0, revision :'Etcd3Revision'=None):
        """
        List keys under given path.

        :param path: Prefix of keys to query. Append '/' to list
           child paths.
        :param recurse: Maximum recursion level to query. If iterable,
           cover exactly the recursion levels specified.
        :param revision: Database revision for which to list
        :returns: (sorted key list, revision)
        """
        # Prepare parameters
        path_depth = path.count('/')
        rev = None
        if revision is not None:
            rev = revision.revision

        # Make transaction to collect keys from all levels
        txn = self._client.Txn()
        try:
            depth_iter = iter(recurse)
        except TypeError:
            depth_iter = range(recurse+1)
        for depth in depth_iter:
            tagged_path = _tag_depth(path, depth+path_depth)
            txn.success(txn.range(
                tagged_path, prefix=True, keys_only=True, revision=rev))
        response = txn.commit()

        # We do not return a mod revision here - this would not be
        # very useful anyway as we are not returning values
        revision = Etcd3Revision(response.header.revision, None)
        if response.responses is None:
            return ([], revision)

        # Collect and sort keys
        sorted_keys = sorted([
            _untag_depth(kv.key.decode('utf-8'))
            for res in response.responses
            if res.response_range.kvs is not None
            for kv in res.response_range.kvs
        ])
        return (sorted_keys, revision)

    def create(self, path :str, value :str, lease :etcd3.Lease=None):
        """Create a key and initialise it with the value.

        Fails if the key already exists. If a lease is given, the key will
        automatically get deleted once it expires.

        :param path: Path to create
        :param value: Value to set
        :param lease: Lease to associate
        :raises: ConfigCollision
        """
        # Prepare parameters
        _check_path(path)
        tagged_path = _tag_depth(path)
        lease_id = (0 if lease is None else lease.ID)
        value = str(value).encode('utf-8')

        # Put value if version is zero (i.e. does not exist)
        txn = self._client.Txn()
        txn.compare(txn.key(tagged_path).version == 0)
        txn.success(txn.put(tagged_path, value, lease_id))
        if not txn.commit().succeeded:
            raise ConfigCollision(
                path, "Cannot create {}, as it already exists!".format(path))

    def update(self, path :str, value :str, must_be_rev :'Etcd3Revision'=None):
        """
        Update an existing key. Fails if the key does not exist.

        :param path: Path to update
        :param value: Value to set
        :param must_be_rev: Fail if found value does not match given
            revision (atomic update)
        :raises: ConfigVanished
        """
        # Validate parameters
        _check_path(path)
        tagged_path = _tag_depth(path)
        value = str(value).encode('utf-8')
        # Put value if version is *not* zero (i.e. it exists)
        txn = self._client.Txn()
        txn.compare(txn.key(tagged_path).version != 0)
        if must_be_rev is not None:
            if must_be_rev.mod_revision is None:
                raise ValueError("Did not pass a valid mod_revision!")
            txn.compare(txn.key(tagged_path).mod == must_be_rev.mod_revision)
        txn.success(txn.put(tagged_path, value))
        if not txn.commit().succeeded:
            raise ConfigVanished(
                path, "Cannot update {}, as it does not exist!".format(path))

    def delete(self, path :str,  # pylint: disable=too-many-arguments
               must_exist :bool=True, recursive :bool=False, prefix :bool=False,
               max_depth :int=16):
        """
        Delete the given key or key range.

        :param path: Path (prefix) of keys to remove
        :param must_exist: Fail if path does not exist?
        :param recursive: Delete children keys at lower levels recursively
        :param prefix: Delete all keys at given level with prefix
        :returns: Whether transaction was successful
        """
        # Prepare parameters
        tagged_path = _tag_depth(path)

        # Determine start recursion level
        txn = self._client.Txn()
        if must_exist:
            txn.compare(txn.key(tagged_path).version != 0)
        txn.success(txn.delete(tagged_path, prefix=prefix))

        # If recursive, we also delete all paths at lower recursion
        # levels that have the path as a prefix
        if recursive:
            depth = path.count('/')
            for lvl in range(depth+1, depth+max_depth):
                dpath = _tag_depth(path if prefix else path+'/', lvl)
                txn.success(txn.delete(dpath, prefix=True))

        # Execute
        if not txn.commit().succeeded:
            raise ConfigVanished(
                path, "Cannot delete {}, as it does not exist!".format(path))

    def close(self):
        """Close the client connection."""
        self._client.close()

    # pylint: disable=duplicate-code
    def __enter__(self):
        """Use for scoping client connection to a block."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Use for scoping client connection to a block."""
        self.close()
        return False


class Etcd3Revision:
    """Identifies the revision of the database. """

    def __init__(self, revision :int, mod_revision :int):
        """Instantiate the revision."""
        self._revision = revision
        self._mod_revision = mod_revision

    def __repr__(self):
        """Build string representation."""
        return "Etcd3Revision({},{})".format(self.revision, self.mod_revision)

    @property
    def revision(self):
        """
        The database revision at the point in time when the query was made.

        Can be used for querying a consistent
        snapshot.
        """
        return self._revision

    @property
    def mod_revision(self):
        """
        The revision when a key was last modified.

        This can be used for checking whether a key has
        changed, for instance to implement an atomic update.
        """
        return self._mod_revision


class Etcd3Watch:
    """Wrapper for etc3 watch requests.

    Entering the watcher using a `with` block yields a queue of `(key,
    val, rev)` triples.
    """

    def __init__(self, watcher :etcd3.Watcher, backend :Etcd3Backend):
        """Initialise watcher."""
        self._watcher = watcher
        self._backend = backend
        self.queue = None

    def start(self, queue :queue_m.Queue=None):
        """Activates the watcher, yielding a queue for updates."""
        if queue is None:
            self.queue = queue = queue_m.Queue()

        def on_event(event):
            key = _untag_depth(event.key.decode('utf-8'))
            if event.type == etcd3.EventType.PUT:
                val = event.value.decode('utf-8')
                rev = Etcd3Revision(event.mod_revision, event.mod_revision)
            else:
                val = None
                rev = Etcd3Revision(event.mod_revision, event.mod_revision)
            queue.put((key, val, rev))

        self._watcher.onEvent(on_event)
        self._watcher.runDaemon()

    def stop(self):
        """Deactivates the watcher."""
        self._watcher.clear_callbacks()
        self._watcher.stop()
        self.queue = None

    def __enter__(self):
        """Use for scoping watcher to a block."""
        self.start()
        return self.queue

    def __exit__(self, *args):
        """Use for scoping watcher to a block."""
        self.stop()


class Etcd3Transaction:
    """A series of queries and updates to be executed atomically.

    Use :py:meth:`Etcd3Backend.txn()` or :py:meth:`Etcd3Watcher.txn()`
    to construct transactions.
    """

    # pylint: disable=too-many-instance-attributes

    # Ideas:
    #
    # Ranged deletes - in contrast to the main backend we cannot
    # release a range of keys (especially recursively) in a
    # transaction yet. The tricky bit is to make this consistent with
    # the rest of the transaction machinery and properly
    # atomic. Easiest solution might just be to simply use a bunch of
    # list_key and single delete calls to get the same effect. Would
    # be slightly inefficient, but would get the job done.
    #
    # Caching - especially when looping a transaction most of the
    # queried data from the database might still be valid. So after a
    # loop we could just migrate the known information to a _cache
    # (plus any further information we got from watches). Then once
    # the "new" database revision has been determined we might just
    # send one cheap query to the database to figure out which bits of
    # it are still current.
    #
    # Cheaper update/create checks - right now we query the old value
    # of the key on every update/create call, even though we are only
    # interested in whether or not the key exists. We could instead
    # query this along the same lines as list_keys. Not entirely sure
    # this is worthwhile though, given that it is quite typical to
    # "get" a key before "updating" it anyway, and collisions on
    # "create" should be quite rare.

    def __init__(self, backend :Etcd3Backend, client :etcd3.Client, max_retries :int=64):
        """Initialise transaction."""
        self._backend = backend
        self._client = client
        self._max_retries = max_retries

        self._revision = None  # Revision backed in after first read
        self._get_queries = {}  # Query log
        self._list_queries = {}  # Query log
        self._updates = {}  # Delayed updates

        self._committed = False
        self._loop = False
        self._watch = False
        self._watch_timeout = None
        self._got_timeout = False  # For test cases
        self._retries = 0

        self._watchers = {}
        self._watch_queue = queue_m.Queue()

        self._commit_callbacks = []

    def _ensure_uncommitted(self):
        if self._committed:
            raise RuntimeError("Attempted to modify committed transaction!")

    @property
    def revision(self) -> int:
        """ The last-committed database revision.

        Only valid to call after the transaction has been comitted.
        """
        if not self._committed:
            raise RuntimeError("Revision is undefined on an uncommitted transaction!")
        return self._revision.revision

    def get(self, path :str) -> str:
        """
        Get value of a key.

        :param path: Path of key to query
        :returns: Key value. None if it doesn't exist.
        """
        self._ensure_uncommitted()

        # Check whether it was written as part of this transaction
        if path in self._updates:
            return self._updates[path][0]

        # Check whether we already have the request response
        if path in self._get_queries:
            return self._get_queries[path][0]

        # Perform get request
        val, rev = self._get_queries[path] = \
            self._backend.get(path, revision=self._revision)

        # Set revision, if not already done so
        if self._revision is None:
            self._revision = rev
        return val

    def list_keys(self, path :str, recurse :int=0):
        """
        List keys under given path.

        :param path: Prefix of keys to query. Append '/' to list
           child paths.
        :param recurse: Children depths to include in search
        :returns: sorted key list
        """
        self._ensure_uncommitted()
        path_depth = path.count('/')

        # Walk through depths, collecting known keys
        try:
            depth_iter = iter(recurse)
        except TypeError:
            depth_iter = range(recurse+1)
        keys = []
        for depth in depth_iter:

            # We might have created or deleted an uncommitted key that
            # falls into the range - add to list
            tagged_path = _tag_depth(path, path_depth+depth)
            matching_vals = [
                kv for kv in self._updates.items()
                if _tag_depth(kv[0]).startswith(tagged_path)
            ]
            added_keys = {
                key for key, val in matching_vals if val is not None
            }
            removed_keys = {
                key for key, val in matching_vals if val is None
            }

            # Check whether we need to perform the request
            query = (path, depth+path_depth)
            if query not in self._list_queries:
                self._list_queries[query] = self._backend.list_keys(
                    path, recurse=(depth,), revision=self._revision)

            # Add to key set
            result, rev = self._list_queries[query]
            keys.extend(set(result) - removed_keys | added_keys)

            # Bake in revision if not already done so
            if self._revision is None:
                self._revision = rev

        # Sort
        return sorted(keys)

    def create(self, path :str, value :str, lease=None):
        """Create a key and initialise it with the value.

        Fails if the key already exists. If a lease is given, the key will
        automatically get deleted once it expires.

        :param path: Path to create
        :param value: Value to set
        :param lease: Lease to associate
        :raises: ConfigCollision
        """
        self._ensure_uncommitted()

        # Attempt to get the value - mainly to check whether it exists
        # and put it into the query log
        result = self.get(path)
        if result is not None:
            raise ConfigCollision(
                path, "Cannot create {}, as it already exists!".format(path))

        # Add update request
        self._updates[path] = (value, lease)

    def update(self, path :str, value :str):
        """
        Update an existing key. Fails if the key does not exist.

        :param path: Path to update
        :param value: Value to set
        :raises: ConfigVanished
        """
        self._ensure_uncommitted()

        # As with "update"
        result = self.get(path)
        if result is None:
            raise ConfigVanished(
                path, "Cannot update {}, as it does not exist!".format(path))

        # Add update request
        self._updates[path] = (value, None)

    def delete(self, path, must_exist=True):
        """
        Delete the given key.

        :param path: Path of key to remove
        :param must_exist: Fail if path does not exist?
        """
        if must_exist:
            # As with "update"
            result = self.get(path)
            if result is None:
                raise ConfigVanished(
                    path, "Cannot delete {}, it does not exist!".format(path))

        # Add delete request
        self._updates[path] = (None, None)

    def commit(self):
        """
        Commit the transaction to the database.

        This can fail, in which case the transaction must get `reset`
        and built again.

        :returns: Whether the commit succeeded
        """
        self._ensure_uncommitted()

        # If we have made no updates, we don't need to verify the log
        if not self._updates:
            self._committed = True
            return True

        # Create transaction
        txn = self._client.Txn()

        # Verify get() calls from the query log
        for path, (_, rev) in self._get_queries.items():
            tagged_path = _tag_depth(path)

            if rev.mod_revision is None:
                # Did not exist? Verify continued non-existance. Note
                # that it is possible for the key to have been
                # created, then deleted again in the meantime.
                txn.compare(txn.key(tagged_path).version == 0)
            else:
                # Otherwise check matching mod_revision. This
                # actually guarantees that the key has not been
                # touched since we read it.
                txn.compare(txn.key(tagged_path).mod == rev.mod_revision)

        # Verify list_keys() calls from the query log
        for (path, depth), (result, rev) in self._list_queries.items():
            tagged_path = _tag_depth(path, depth)

            # Make sure that all returned keys still exist
            for res_path in result:
                tagged_res_path = _tag_depth(res_path)
                txn.compare(txn.key(tagged_res_path).version > 0)

            # Also check that no new keys have entered the range
            # (by checking whether the request would contain any
            # keys with a newer create revision than our request)
            txn.compare(txn.key(tagged_path, prefix=True).create
                        < self._revision.revision+1)

        # Commit changes. Note that the dictionary guarantees that we
        # only update any key at most once.
        for path, (value, lease) in self._updates.items():
            tagged_path = _tag_depth(path)
            lease_id = (None if lease is None else lease.ID)
            if value is None:
                txn.success(txn.delete(tagged_path, value, lease_id))
            else:
                txn.success(txn.put(tagged_path, value, lease_id))

        # Done
        self._committed = True
        response = txn.commit()
        if response.succeeded:
            for callback in self._commit_callbacks:
                callback()
        self._commit_callbacks = []
        return response.succeeded

    def on_commit(self, callback :Callable[[],None]):
        """Register a callback to call when the transaction succeeds.

        A bit of a hack, but occassionally useful to add additional
        side-effects to a transaction that are guaranteed to not get
        duplicated.

        :param callback: Callback to call
        """
        self._commit_callbacks.append(callback)

    def reset(self, revision :Etcd3Revision=None):
        """Reset the transaction so it can be restarted after commit()."""
        if not self._committed:
            raise RuntimeError("Called reset on an uncommitted transaction!")

        # Reset
        self._revision = revision
        self._get_queries = {}
        self._list_queries = {}
        self._updates = {}
        self._committed = False
        self._loop = False
        self._watch = False
        self._watch_timeout = None

    @deprecated
    def loop(self, watch :bool=False, watch_timeout :float=None):
        """Repeat transaction execution, even if it succeeds.

        *Deprecated*: Use :py:class:`Etcd3Watcher` instead, or loop manually.

        :param watch: Once the transaction succeeds, block until one of
           the values read changes, then loop the transaction
        """
        if self._loop:
            # If called multiple times, looping immediately takes precedence
            self._watch = (self._watch and watch)
        else:
            self._loop = True
            self._watch = watch
        if watch and watch_timeout is not None:
            self._watch_timeout = watch_timeout

    def __iter__(self):
        """Iterate transaction as requested by loop(), or until it succeeds."""
        try:

            while self._retries <= self._max_retries:

                # Should build up a transaction
                yield self

                # Try to commit, count how many times we have tried
                if not self.commit():
                    self._retries += 1
                else:
                    self._retries = 0

                    # No further loop?
                    if not self._loop:
                        return

                    # Use watches? Then wait for something to happen
                    # before looping.
                    if self._watch:
                        self._do_watch()

                # Repeat after reset otherwise
                self.reset()

        finally:
            self._clear_watch()

        # Ran out of repeats? Fail
        raise RuntimeError("Transaction did not succeed after {} retries!"
                           .format(self._max_retries))

    @deprecated
    def clear_watch(self):
        """Stop all currently active watchers.

        *Deprecated*: Use :py:class:`Etcd3Watcher` instead.
        """
        self._clear_watch()

    def _clear_watch(self):
        """Stop all currently active watchers."""
        # Remove watchers
        for watcher in self._watchers.values():
            watcher.stop()
        self._watchers = {}

    def _update_watchers(self):

        # Watch any ranges we listed. Note that this will trigger also
        # on key updates, we will filter that below.
        prefixes = []
        active_watchers = set()
        for path, depth in self._list_queries:
            query = ('list', path, depth)
            # Add tagged prefixes so we can check for key overlap later
            prefixes.append(_tag_depth(path, depth))
            active_watchers.add(query)
            # Start a watcher, if required
            if self._watchers.get(query) is None:
                self._watchers[query] = self._backend.watch(
                    path, revision=self._revision, prefix=True, depth=depth)
                self._watchers[query].start(self._watch_queue)

        # Watch any individual key we read
        for path in self._get_queries:
            query = ('get', path)

            # Check that we are not already watching this key as
            # part of a range. This is basically using the
            # above-mentioned property of range watches to our
            # advantage. This is actually a fairly important
            # optimisation, as it means that listing keys followed
            # by iterating over the values won't create extra
            # watches here!
            tagged_path = _tag_depth(path)
            if not any([tagged_path.startswith(pre) for pre in prefixes]):
                active_watchers.add(query)
                # Start individual watcher, if required
                if self._watchers.get(query) is None:
                    self._watchers[query] = self._backend.watch(
                        path, revision=self._revision)
                    self._watchers[query].start(self._watch_queue)

        # Remove any watchers that we are not currently using. Note
        # that we only do this on the next watch() call, so watchers
        # will be kept alive through transaction failures *and*
        # non-waiting loops. So as long as the set of keys waited on
        # is relatively constant (and ideally forms ranges), we will
        # not generate much churn here.
        for query, watcher in list(self._watchers.items()):
            if query not in active_watchers:
                watcher.stop()
                del self._watchers[query]

    def watch(self):
        """Wait for a change on one of the values read.

        *Deprecated*: Use :py:class:`Etcd3Watcher` instead.

        :returns: The revision at which a change was detected.
        """
        return self._do_watch()

    def _do_watch(self):
        """Wait for a change on one of the values read.

        :returns: The revision at which a change was detected.
        """

        # Make sure the watchers we have in place match what we read
        self._update_watchers()

        # Wait for updates from the watcher queue
        block = True
        revision = self._revision
        start_time = time.time()
        while True:

            # Determine timeout
            timeout = None
            if self._watch_timeout is not None:
                timeout = max(
                    0, start_time + self._watch_timeout - time.time())

            # Wait for something to get pushed on the queue
            try:
                path, value, rev = self._watch_queue.get(block, timeout)
            except queue_m.Empty:
                self._got_timeout = block
                return revision

            # Manual trigger?
            if rev is None:
                self._got_timeout = False
                break

            # Check that revision is newer (prevent duplicated updates)
            if rev.revision <= revision.revision:
                continue

            # Are we waiting on a value change of this one?
            if path not in self._get_queries:

                # Are we getting this because of one of the list queries?
                tagged_path = _tag_depth(path)
                found_match = False
                for (lpath, depth), (result, _) in self._list_queries.items():
                    if tagged_path.startswith(_tag_depth(lpath, depth)):

                        # We should not notify for a value change,
                        # only if a key was added / removed. Good
                        # thing we can check that using the log.
                        if value is None or path not in result:
                            found_match = True
                            break

                # Otherwise this is either a misfire from an old
                # watcher, or a value update from a list watcher (see
                # above). Ignore.
                if not found_match:
                    continue

            # Alright, we can stop waiting. However, we will attempt
            # to clear the queue before we do so, as we might get a
            # lot of updates in batch
            revision = rev
            block = False

    def trigger_loop(self):
        """Manually triggers a loop

        Effectively makes loop(True) behave like loop(False), looping
        immediately. This is useful for interrupting a blocking
        watch() from a different thread.
        """

        # Push a magic "cancel" entry
        self._watch_queue.put((None,None,None))

class Etcd3Watcher:
    """Watch for database changes by using nested transactions

    Use as follows:

    .. code-block:: python

        for watcher in config.watcher():
            for txn in watcher.txn():
                # ... do something
            for txn in watcher.txn():
                # ... do something else

    At the end of a for loop iteration, the watcher will start
    watching all values read by transactions started through
    :py:meth:`txn`, and only repeat the execution of the loop body
    once one of these values has changed.
    """

    def __init__(self, backend :Etcd3Backend, client :etcd3.Client,
                 timeout :float=None,
                 txn_wrapper :Callable[[Etcd3Transaction], object]=None):
        """Initialise watcher.

        :param timeout: Maximum time to wait per loop. If ``None``, will
            wait indefinetely.
        """

        self._wait_txn = Etcd3Transaction(backend, client)

        self._backend = backend
        self._client = client
        self._timeout = timeout
        self._txn_wrapper = txn_wrapper

    def set_timeout(self, timeout :float):
        """Set a timeout.

        The watch loop will always repeat after waiting for the given
        amount of time.

        :param timeout: Maximum time to wait per loop. If ``None``, will
            wait indefinetely.
        """
        self._timeout = timeout

    def txn(self, max_retries :int=64) -> Etcd3Transaction:
        """Create nested transaction.

        The watcher loop will iterate when any value read by
        transactions created by this method have changed in the
        database.

        Note that these transactions otherwise behave exactly as
        normal transactions: As long as they are internally
        consistent, they will be commited. This means there is no
        consistency guarantees between transactions created from the
        same watcher, i.e. one transaction might read one value from
        the database while a later one reads another.

        :param max_retries: Maximum number of times the transaction will be
           tried before giving up.
        """

        # Make a new transaction.
        # TODO: Would be more efficient if the different transactions
        # could share some sort of cache so they don't need to
        # re-query keys...
        for txn in Etcd3Transaction(self._backend, self._client, max_retries):
            if self._txn_wrapper is not None:
                yield self._txn_wrapper(txn)
            else:
                yield txn

        # Extract read values from transaction
        # pylint: disable=protected-access,undefined-loop-variable
        if txn._committed:

            # Take over earliest revision used in a transaction, as we
            # want to know about any changes from that particular
            # point forward.
            if self._wait_txn._revision is None or \
               self._wait_txn._revision.revision > txn._revision.revision:
                self._wait_txn._revision = txn._revision

            self._wait_txn._get_queries.update(txn._get_queries)
            self._wait_txn._list_queries.update(txn._list_queries)

    def __iter__(self):
        """ Iterate forever, waiting after every interaction for something to change. """

        try:
            while True:
                yield self

                # TODO: Move those to this class!
                # pylint: disable=protected-access
                self._wait_txn.loop(True, self._timeout)
                self._wait_txn._do_watch()

                # Clear current queries
                self._wait_txn._get_queries = {}
                self._wait_txn._list_queries = {}

        finally:
            # pylint: disable=protected-access
            self._wait_txn._clear_watch()

    def trigger(self):
        """Manually triggers a loop

        Can be called from a different thread to force a loop, even if
        the watcher is currently waiting.
        """

        # pylint: disable=protected-access
        self._wait_txn.trigger_loop()
