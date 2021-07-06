.. _cli:

CLI to interact with SDP
========================

Command Line Interface: ``ska-sdp``

To run the CLI, you must start a shell in the ``console pod``.
(assuming you have SDP deployed in Kubernetes/Minikube, for instructions follow:
`SDP standalone <https://developer.skatelescope.org/projects/ska-sdp-integration/en/latest/running/standalone.html>`_)

.. code-block:: bash

    kubectl exec -it sdp-console-0 -- bash

Once in, to access the help window of ``ska-sdp``, run:

.. code-block:: bash

    ska-sdp -h

Command - SDP Object matrix
---------------------------

This is a table/matrix of the existing commands of ``ska-sdp`` and what they can
do with a specific SDP Object.

Commands:

- list
- get/watch
- create
- update/edit
- delete
- import

SDP Objects:

- pb (processing block)
- workflow (workflow definition)
- deployment
- sbi (scheduling block instance)
- master (Tango master device)
- subarray (Tango subarray device)

.. list-table::
   :widths: 5 5 5 5 5 5
   :header-rows: 1

   * -
     - pb
     - workflow
     - deployment
     - sbi
     - other
   * - **list**
     - - list all pbs
       - list pbs for a certain date
     - - list all workflow definitions
       - list a workflow def of a specific type (batch or realtime)
     - list all deployments
     - list all sbis
     - - if **-a | --all**: list all the contents of the Config DB
       - if **-v | --values**: list keys with values (or just values)
       - if **--prefix**: list limited to this prefix (for testing purposes)
       - if master, list the device entry if there is one
       - if subarray, list all subarray device entries
   * - **get/watch**
     - - get the value of a single key
       - get the values of all pb-related keys for a single pb-id
     - get the value of a single key
     - get the value of a single key
     - get the value of a single key
     - *Note: rules for get and watch are the same*
   * - **create**
     - create a pb to **run a workflow**
     - create a key/value pair with prefix of /workflow
     - create a deployment of **given id, type, and parameters**
     - create a key/value pair with prefix of /sbi
     - *Not implemented for Tango devices*
   * - **update/edit**
     - update/edit the **state** of a pb with a **given pb-id**
     - - update a given key with a given value
       - edit a given key
     - - update a given key with a given value
       - edit a given key
     - - update a given key with a given value
       - edit a given key
     - - update a Tango device entry
       - edit a Tango device entry
   * - **delete**
     - - delete all pbs (need confirmation)
       - delete all pb entries for a single pb-id
     - - delete all workflow defs (need confirmation)
       - delete workflow def for a single key (type:id:version)
     - - delete all deployments (need confirmation)
       - delete deployment for a single deploy-id
     - - delete all sbis (need confirmation)
       - delete sbi for a single sbi-id
     - * if **--prefix**: append prefix in front of path and perform same
       * deletion as listed onder SDP object type.
   * - **import**
     - n/a
     - import workflow definitions from file or URL
     - n/a
     - n/a
     -

Relevant environment variables
------------------------------

Backend-related::

  SDP_CONFIG_BACKEND   Database backend (default etcd3)
  SDP_CONFIG_HOST      Database host address (default 127.0.0.1)
  SDP_CONFIG_PORT      Database port (default 2379)
  SDP_CONFIG_PROTOCOL  Database access protocol (default http)
  SDP_CONFIG_CERT      Client certificate
  SDP_CONFIG_USERNAME  User name
  SDP_CONFIG_PASSWORD  User password

When running `ska-sdp edit`::

  EDITOR    Executable of an existing text editor. Recommended: vi, vim, nano (i.e. command line-based editors)

Usage
-----

.. code-block:: none

    > ska-sdp --help

    Command line utility for interacting with SKA Science Data Processor (SDP).

    Usage:
        ska-sdp COMMAND [options] [SDP_OBJECT] [<args>...]
        ska-sdp COMMAND (-h|--help)
        ska-sdp (-h|--help)

    SDP Objects:
        pb           Interact with processing blocks
        workflow     Interact with available workflow definitions
        deployment   Interact with deployments
        sbi          Interact with scheduling block instances
        master       Interact with Tango master device
        subarray     Interact with Tango subarray device

    Commands:
        list            List information of object from the Configuration DB
        get | watch     Print all the information (i.e. value) of a key in the Config DB
        create          Create a new, raw key-value pair in the Config DB;
                        Run a workflow; Create a deployment
        update          Update a raw key value from CLI
        edit            Edit a raw key value from text editor
        delete          Delete a single key or all keys within a path from the Config DB
        import          Import workflow definitions from file or URL


.. code-block:: none

    > ska-sdp list --help

    List keys (and optionally values) within the Configuration Database.

    Usage:
        ska-sdp list (-a |--all) [options]
        ska-sdp list [options] pb [<date>]
        ska-sdp list [options] workflow [<type>]
        ska-sdp list [options] (deployment|sbi|master|subarray)
        ska-sdp list (-h|--help)

    Arguments:
        <date>      Date on which the processing block(s) were created. Expected format: YYYYMMDD
                    If not provided, all pbs are listed.
        <type>      Type of workflow definition. Batch or realtime.
                    If not provided, all workflows are listed.

    Options:
        -h, --help         Show this screen
        -q, --quiet        Cut back on unnecessary output
        -a, --all          List the contents of the Config DB, regardless of object type
        -v, --values       List all the values belonging to a key in the config db; default: False
        --prefix=<prefix>  Path prefix (if other than standard Config paths, e.g. for testing)


.. code-block:: none

    > ska-sdp (get|watch) --help

    Get/Watch all information of a single key in the Configuration Database.

    Usage:
        ska-sdp (get|watch) [options] <key>
        ska-sdp (get|watch) [options] pb <pb_id>
        ska-sdp (get|watch) (-h|--help)

    Arguments:
        <key>       Key within the Config DB.
                    To get the list of all keys:
                        ska-sdp list -a
        <pb_id>     Processing block id to list all entries and their values for.
                    Else, use key to get the value of a specific pb.

    Options:
        -h, --help    Show this screen
        -q, --quiet   Cut back on unnecessary output


.. code-block:: none

    > ska-sdp create --help

    Create a new, raw, key-value pair in the Configuration Database.
    Create a processing block to run a workflow.
    Create a deployment.

    Usage:
        ska-sdp create [options] pb <workflow> [<parameters>]
        ska-sdp create [options] deployment <deploy-id> <type> <parameters>
        ska-sdp create [options] (workflow|sbi) <key> <value>
        ska-sdp create (-h|--help)

    Arguments:
        <workflow>      Workflow that the processing block will run, in the format of: type:id:version
        <parameters>    Optional parameters for a workflow, with expected format:
                            '{"key1": "value1", "key2": "value2"}'
                        For deployments, expected format:
                            '{"chart": <chart-name>, "values": <dict-of-values>}'
        <deploy_id>     Id of the new deployment
        <type>          Type of the new deployment (currently "helm" only)
        Create general key-value pairs:
        <key>           Key to be created in the Config DB.
        <value>         Value belonging to that key.

    Options:
        -h, --help    Show this screen
        -q, --quiet   Cut back on unnecessary output

    Example:
        ska-sdp create sbi sbi-test-20210524-00000 '{"test": true}'
        Result in the config db:
            key: /sbi/sbi-test-20210524-00000
            value: {"test": true}

    Note: You cannot create processing blocks apart from when they are called to run a workflow.


.. code-block:: none

    > ska-sdp (update|edit) --help

    Update the value of a single key or processing block state.
    Can either update from CLI, or edit via a text editor.

    Usage:
        ska-sdp update [options] (workflow|sbi|deployment) <key> <value>
        ska-sdp update [options] pb-state <pb-id> <value>
        ska-sdp update [options] master <value>
        ska-sdp update [options] subarray <array-id> <value>
        ska-sdp edit (workflow|sbi|deployment) <key>
        ska-sdp edit pb-state <pb-id>
        ska-sdp edit master
        ska-sdp edit subarray <array-id>
        ska-sdp (update|edit) (-h|--help)

    Arguments:
        <key>       Key within the Config DB. Cannot be a processing block related key.
        <pb-id>     Processing block id whose state is to be changed.
        <array-id>  Subarray id (number)
        <value>     Value to update the key/pb state with.

    Options:
        -h, --help    Show this screen
        -q, --quiet   Cut back on unnecessary output

    Note:
        ska-sdp edit needs an environment variable defined:
            EDITOR: Has to match the executable of an existing text editor
                    Recommended: vi, vim, nano (i.e. command line-based editors)
            Example: EDITOR=vi ska-sdp edit <key>
        Processing blocks cannot be changed, apart from their state.

    Example:
        ska-sdp edit sbi sbi-test-20210524-00000
            --> key that's edited: /sbi/sbi-test-20210524-00000
        ska-sdp edit workflow batch:test:0.0.0
            --> key that's edited: /workflow/batch:test:0.0.0
        ska-sdp edit pb-state some-pb-id-0000
            --> key that's edited: /pb/some-pb-id-0000/state


.. code-block:: none

    > ska-sdp delete --help

    Delete a key from the Configuration Database.

    Usage:
        ska-sdp delete (-a|--all) [options] (pb|workflow|sbi|deployment|prefix)
        ska-sdp delete [options] (pb|sbi|deployment) <id>
        ska-sdp delete [options] workflow <workflow>
        ska-sdp delete (-h|--help)

    Arguments:
        <id>        ID of the processing block, or deployment, or scheduling block instance
        <workflow>  Workflow definition to be deleted. Expected format: type:id:version
        prefix      Use this "SDP Object" when deleting with a non-object-specific, user-defined prefix

    Options:
        -h, --help             Show this screen
        -q, --quiet            Cut back on unnecessary output
        --prefix=<prefix>      Path prefix (if other than standard Config paths, e.g. for testing)


.. code-block:: none

    > ska-sdp import --help

    Import workflow definitions into the Configuration Database.

    Usage:
        ska-sdp import workflows [options] <file-or-url>
        ska-sdp import (-h|--help)

    Arguments:
        <file-or-url>      File or URL to import workflow definitions from.

    Options:
        -h, --help          Show this screen
        --sync              Delete workflows not in the input


Example workflow definitions file content for import
----------------------------------------------------

Structured::

    {
      "about": [
        "SDP Processing Controller workflow definitions"
      ],
      "version": {
        "date-time": "2021-05-14T16:00:00Z"
      },
      "repositories": [
        {"name": "nexus", "path": "nexus.engageska-portugal.pt/sdp-prototype"}
      ],
      "workflows": [
        {"type": "batch", "id":  "test_batch", "repository": "nexus", "image": "workflow-test-batch", "versions": ["0.2.2"]},
        {"type": "realtime", "id":  "test_realtime", "repository": "nexus", "image": "workflow-test-realtime2", "versions": ["0.2.2"]}
      ]
    }

Flat::

    workflows:
    - type: realtime
      id: test_realtime
      version: 0.2.2
      image: nexus.engageska-portugal.pt/sdp-prototype/workflow-test-realtime:0.2.2
    - type: batch
      id: test_batch
      version: 0.2.2
      image: nexus.engageska-portugal.pt/sdp-prototype/workflow-test-batch:0.2.2

Both YAML and JSON files are accepted.