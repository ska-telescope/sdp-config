"""Frontend module for accessing SKA SDP configuration information.

It provides ways for SDP controller and processing components to
discover and manipulate the intended state of the system.  At the
moment this is implemented on top of `etcd`, a highly-available
database. This library provides primitives for atomic queries and
updates to the stored configuration information.
"""

from .version import __version__
from .backend import ConfigCollision, ConfigVanished
from .config import Config
from .entity import ProcessingBlock, Deployment

__all__ = [
    "__version__",
    "Config",
    "ConfigCollision",
    "ConfigVanished",
    "ProcessingBlock",
    "Deployment",
]
