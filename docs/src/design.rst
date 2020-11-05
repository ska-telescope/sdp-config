Design and Best Practices
=========================

Quick points:

- Uses a key-value store
- Objects are represented as JSON
- Uses watches on a key or range of keys to monitor for any updates

Transaction Basics
------------------

The SDP configuration database interface is built around the concept
of transactions, i.e. blocks of read and write queries to the database
state that are guaranteed to be executed atomically. I.e. if you write
code as follows:

.. code-block:: python

    for txn in config.txn():
       a = txn.get('a')
       if a is None:
           txn.create('a', '1')
       else:
           txn.update('a', str(int(a)+1))
    
It is guaranteed that we increment the `'a'` key by exactly one here, no
matter how many other processes might be operating on it. How does this
work?

The way transactions are implemented follows the philosophy of
`Software Transactional Memory
<https://en.wikipedia.org/wiki/Software_transactional_memory>`_ as
opposed to a lock-based implementation. The idea is that all reads are
performed, but all writes are actually delayed until the end of the
transaction.  So in the above example, `'a'` is actually read from the
database, but the 'put' call is not performed immediately.

Once the transaction finishes (the end of the `for` loop), the
transaction commit sends a single request to the database that updates
all written values **only if** none of the read values having been
written in the meantime. If the commit fails, we repeat the
transaction (that's why it is a loop!) until it succeeds. The
idea is that this is fairly rare, and repeating the transaction should
typically be cheap.

Usage Guidelines
----------------

What does this mean for everyday usage? Transactions should be as
self-contained as possible - i.e. they should explicitly contain all
assumptions about the database state they are making. If we wrote the
above transaction as follows:

.. code-block:: python

    for txn in config.txn():
       a = txn.get('a')

    for txn in config.txn():
       if a is None:
           txn.create('a', '1')
       else:
           txn.update('a', str(int(a)+1))

A whole number of things could happen between the first and the second
transaction:

1. The `'a'` key could not exist in the first transaction, but could
   have been created by the second (which would cause us to fail)

2. The `'a'` key could exist in the first transaction, but could have
   been deleted by the second (which would also cause the above to fail)

3. Another transaction might have updated the `'a'` key with a new value
   (which would cause that update to be lost)

A rule of thumb is that you should assume **nothing** about the
database state at the start of a transaction. If you rely on
something, you need to (re)query it after you enter it. If for some
reason you couldn't merge the transactions above, you should write
something like:

.. code-block:: python

    for txn in config.txn():
       a = txn.get('a')

    for txn in config.txn():
       assert txn.get('a') == a, "database state independently updated!"
       if a is None:
           txn.create('a', '1')
       else:
           txn.update('a', str(int(a)+1))

This would especially catch case (3) above. This sort of approach can
be useful when we want to make sub-transactions that only depend on a
part of the overall state:

.. code-block:: python

    for txn in config.txn():
        keys = txn.list_keys('/as/')
    for key in keys:
        for txn in config.txn():
            a = txn.get(key)
            # Safety check: Path might have vanished in the meantime!
            if a is None:
                continue
            # ... do something that depends solely on existance of "path" ...

This can especially be combined with watchers (see below) to keep
track of many objects without requiring huge transactions.

Wrapping transactions
---------------------

The safest way to work with transactions is to make them as "large" as
possible, spanning all the way from getting inputs to writing
outputs. This should be the default unless we have a strong reason to
do it differently (examples for such reasons would be transactions
becoming too large, or transactions taking so long that they never
finish - but either should be extremely rare).

However, in the context of a program with complex behaviour this might
appear cumbersome: This means we have to pass the transaction object
to every single method that could either read or write the state. An
elegant way to get around this is to move such methods to a "model"
class that wraps the transaction itself:

.. code-block:: python

    def IncrementModel(Transaction):
        def __init__(self, txn):
            self._txn = txn
        def increase(key):
            a = self._txn.get(key)
            if a is None:
                self._txn.create(key, '1')
            else:
                self._txn.update(key, str(int(a)+1))

    # ...
    for txn in config.txn():
       model = IncrementModel(txn)
       model.increase('a')

In fact, we can provide factory functions that entirely hide the
transaction object from view:

.. code-block:: python

    def increment_txn(config):
        for txn in config.txn():
            yield IncrementModel(txn)

    # ...
    for model in increment_txn(config):
       model.increase('a')

We could wrap this model the same way again to build as many
abstraction layers as we want - key is that high-level methods such as
"increase" are now directly tied to the existance of a transaction object.

Dealing with roll-backs
-----------------------

Especially as we start wrapping transactions more and more, we must
keep in mind that while we can easily "roll back" any writes of the
transaction (as they are not actually performed immediately), the same
might not be true for program state. So for instance, the following
would be unsafe:

.. code-block:: python

    to_update = ['a','b','c']
    for model in increment_txn():
        while to_update:
            model.increase(to_update.pop())

Clearly this transaction would work differently the second time
around! For this reason it is a good idea to keep in mind that while
we expect the `for` to only execute once, it is entirely possible that
they would execute multiple times, and the code should be written
accordingly.

Fortunately, this sort of occurance should be relatively rare - the
following might be more typical:

.. code-block:: python

    objects_found = []
    for model in increment_txn():
        for obj in model.list_objects():
            if model.some_check(obj):
                LOGGER.debug(f'Found {obj}!')
                objects_found.append(obj)

In this case, `objects_found` might contain duplicate objects if the
transaction repeats - which could be easily fixed by moving the
initialisation into the `for` loop.

On the other hand, note that transaction loops might also lead to
duplicated log lines here, which might be seen as confusing. In this
case, this is relatively benign and therefore likely acceptable. It
might be possible to generate log messages at the start and end of
transactions to make this more visible.

Another possible approach could be to replicate the transaction
behaviour: for example, we could make the logging calls to
`IncrementModel`, which would internally aggregate the logging lines to
generate, which `increement_txn` could then emit in one go once the
transaction actually goes through.

Watchers
--------

Occasionally we might want to actively track something in the
configuration. For sake of example, let's say we want to wait for a
key to appear so we can print it. A simple implementation using polling
might look like follows:

.. code-block:: python

    while True:
        for txn in config.txn():
            line = txn.get('/line_to_print')
            if line is not None:
                txn.delete('/line_to_print')
        if line is not None:
            print(line)
        time.sleep(1)

(Note that we are making sure to print outside the transaction loop -
otherwise lines might get printed multiple times if we were running
more than one instance of this program in parallel!)

But clearly this is not very good - it re-queries the database every
second, which adds database load *and* is pretty slow. Instead, we can
use a watcher loop:

.. code-block:: python

    for watcher in config.watcher():
        for txn in watcher.txn():
            line = txn.get('/line_to_print')
            if line is not None:
                txn.delete('/line_to_print')
        if line is not None:
            print(line)

Note that we are calling `txn` on the `watcher` instead of `config`:
What is happening here is that the `watcher` object collects keys read
by the transaction, and only iterates once one of them has been
written. It is a concept that has a lot in common with the transaction
loop, except that while the transaction loop only iterates if the
transaction is inconsistent, the watcher loop *always* iterates.

Note that you can have multiple separate transactions within a watcher
loop, which however are not guaranteed to be consistent. For example:

.. code-block:: python

    for watcher in config.watcher():
        for txn in watcher.txn():
            line = txn.get('/line_to_print')
        print('A:', line)
        for txn in watcher.txn():
            line = txn.get('/line_to_print')
        print('B:', line)

In this program we might get different results for `A` and
`B`. However, the watcher *does* guarantee that the loop will iterate
if any of the read values have been invalidated. So if the line was
deleted between the two transaction, the following output would be
generated:

.. code-block::

    A: something
    B: None
    A: None
    B: None

After all, while transaction `B` had a current view of the situation
the first time around, the view of transaction `A` became out-of-date.

