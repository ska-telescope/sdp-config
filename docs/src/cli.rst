.. _cli:

CLI to interact with SDP
========================

Command Line Interface: ``ska-sdp``

To run the CLI, you will have to start the ``console pod``
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

* list
* get/watch
* create
* update/edit
* delete
* import

SDP Objects:

* pb (processing block)
* workflow (workflow definition)
* deployment
* sbi (scheduling block instance)

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
     - - list all workflow defintions
       - list a workflow def of a specific type (batch or realtime)
     - list all deployments
     - list all sbis
     - - if **-a | --all**: list all the contents of the Config DB
       - if **-v | --values**: list keys with values (or just values)
       - if **--prefix**: list limited to this prefix (for testing purposes)
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
     -
   * - **update/edit**
     - update/edit the **state** of a pb with a **given pb-id**
     - - update a given key with a given value
       - edit a given key
     - - update a given key with a given value
       - edit a given key
     - - update a given key with a given value
       - edit a given key
     -
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
     - x
     - import workflow defs from file or URL
     - x
     - x
     -

Usage
-----

.. code-block:: bash

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

    Commands:
        list            List information of object from the Configuration DB
        get | watch     Print all the information (i.e. value) of a key in the Config DB
        create          Create a new, raw key-value pair in the Config DB;
                        Run a workflow; Create a deployment
        update          Update a raw key value from CLI
        edit            Edit a raw key value from text editor
        delete          Delete a single key or all keys within a path from the Config DB
        import          Import workflow definitions from file or URL


.. code-block:: bash

    > ska-sdp list --help

    List keys (and optionally values) within the Configuration Database.

    Usage:
        ska-sdp list (-a |--all) [options]
        ska-sdp list [options] pb [<date>]
        ska-sdp list [options] workflow [<type>]
        ska-sdp list [options] (deployment|sbi)
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


.. code-block:: bash

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


.. code-block:: bash

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
        ska-sdp create sbi my_new_sbi '{"test": true}'
        Result in the config db:
            key: /sbi/my_new_sbi
            value: {"test": true}

    Note: You cannot create processing blocks apart from when they are called to run a workflow.


.. code-block:: bash

    > ska-sdp (update|edit) --help

    Update the value of a single key or processing block state.
    Can either update from CLI, or edit via a text editor.

    Usage:
        ska-sdp update [options] (workflow|sbi|deployment) <key> <value>
        ska-sdp update [options] pb-state <pb-id> <value>
        ska-sdp edit (workflow|sbi|deployment) <key>
        ska-sdp edit pb-state <pb-id>
        ska-sdp (update|edit) (-h|--help)

    Arguments:
        <key>       Key within the Config DB. Cannot be a processing block related key.
                    To get the list of all keys:
                        ska-sdp list -a
        <pb-id>     Processing block id whose state is to be changed.
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


.. code-block:: bash

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


.. code-block:: bash

    > ska-sdp import --help

    Import workflow definitions into the Configuration Database.

    Usage:
        ska-sdp import [options] <file-or-url>
        ska-sdp import (-h|--help)

    Arguments:
        <file-or-url>      File or URL to import workflow definitions from.

    Options:
        -h, --help          Show this screen
        --sync              Delete workflows not in the input
