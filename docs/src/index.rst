SDP Configuration Library
=========================

This repository contains the library for accessing SKA SDP configuration
information. It provides ways for SDP controller and processing components to
discover and manipulate the intended state of the system.

At the moment this is implemented on top of ``etcd``, a highly-available
database. This library provides primitives for atomic queries and updates to
the stored configuration information.

.. toctree::
  :maxdepth: 1

  installation
  design
  schema
  api
  cli


Indices and tables
------------------

- :ref:`genindex`
- :ref:`modindex`
- :ref:`search`
