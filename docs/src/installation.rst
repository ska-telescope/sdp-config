Installation and Usage
======================

Install with pip
----------------

.. code-block:: bash

   pip --index-url https://artefact.skao.int/repository/pypi-internal/simple --extra-index-url https://pypi.org/simple install ska-sdp-config


Basic usage
-----------

Make sure you have a database backend accessible (etcd3 is supported at the
moment). Location can be configured using the ``SDP_CONFIG_HOST`` and
``SDP_CONFIG_PORT`` environment variables. The defaults are ``127.0.0.1`` and
``2379``, which should work with a local ``etcd`` started without any
configuration.

You can find ``etcd`` pre-built binaries, for Linux, Windows, and macOS,
here: https://github.com/etcd-io/etcd/releases.

You can also use homebrew to install ``etcd`` on macOS:

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

:ref:`cli`

Running unit tests locally
--------------------------

You will need to have a database backend to run the tests as well.
See "Basic usage" above for instructions on how to install an ``etcd`` backend on your machine.

Once you started the database (run ``etcd`` in the command line),
you will be able to run the tests using pytest.

Alternative way is by using the two shell scripts in the scripts directory:

``docker_run_etcd.sh`` -> Which runs etcd in a Docker container for testing the code.
``docker_run_python.sh`` -> Runs a python container and connects to the etcd instance.

Run the scripts from the root of the repository:

.. code-block:: bash

    bash scripts/docker_run_etcd.sh
    bash scripts/docker_run_python.sh

Once the container is started and mounted to the local directory.

Install the dependencies:

.. code-block:: bash

    pip install -r requirements.txt -r requirements-test.txt

Then run the tests:

.. code-block:: bash

    python setup.py test

