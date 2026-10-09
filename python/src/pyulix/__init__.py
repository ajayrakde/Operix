"""Complete named Python facade for the pinned Oculix Java API.

Java method names, constructors and overload arguments are preserved.
Use ``method.overload(*java_type_names)`` for ambiguous null/reference calls.
"""
from ._bridge import Bridge, BridgeError, RemoteObject, RemoteWrapper, default_bridge
from ._api import JavaObject, JavaCallback, java_class
from .java import *
from .java import __all__ as _java_names

__version__ = '1.2.0b2'
__all__ = list(_java_names) + ['Bridge', 'BridgeError', 'JavaObject', 'JavaCallback', 'java_class', 'default_bridge']
