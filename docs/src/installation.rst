Installation and Usage
======================

Install with pip
----------------

.. code-block:: bash

   pip --index-url https://nexus.engageska-portugal.pt/repository/pypi/simple --extra-index-url https://pypi.org/simple install ska-sdp-config


Basic usage
-----------

Make sure you have a database backend accessible (etcd3 is supported at the
moment). Location can be configured using the ``SDP_CONFIG_HOST`` and
``SDP_CONFIG_PORT`` environment variables. The defaults are ``127.0.0.1`` and
``2379``, which should work with a local ``etcd`` started without any
configuration.

You can find ``etcd`` pre-built binaries, for Linux, Windows, and MacOS,
here: https://github.com/etcd-io/etcd/releases.

You can also use homebrew to install ``etcd`` on a MacOS:

.. code-block:: bash

    brew install etcd

If you encounter issues follow: https://brewinstall.org/install-etcd-on-mac-with-brew/


This should give you access to SDP configuration information, for instance try:

.. code-block:: python

   import ska_sdp_config

   config = ska_sdp_config.Config()

   for txn in config.txn():
       for pb_id in txn.list_processing_blocks():
          pb = txn.get_processing_block(pb_id)
          print("{} ({}:{})".format(pb_id, pb.workflow['id'], pb.workflow['version']))


To read a list of currently active processing blocks with their associated
workflows.

Command line
------------

This package also comes with a command line utility for easy access to
configuration data. For instance run:

.. code-block:: bash

   sdpcfg list values /pb/

to query all processing blocks.

Running unit tests locally
--------------------------

You will need to have a database backend to run the tests as well.
See "Basic usage" above for instructions on how to install an ``etcd`` backend on your machine.

Once you started the database (run ``etcd`` in the command line),
you will be able to run the tests using pytest.