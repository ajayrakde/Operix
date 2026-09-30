"""Typing facade: known Java classes expose their generated declarations only."""
from typing import Any, ClassVar
from ._bridge import Bridge

class JavaObject:
    JAVA_CLASS: ClassVar[str]
    _ref: str
    _bridge: Bridge
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def _call(self, method: str, *args: Any) -> Any: ...
    @classmethod
    def _wrap(cls, value: Any) -> Any: ...

class JavaCallback:
    interface: str
    handler: Any
    def __init__(self, interface: Any, handler: Any) -> None: ...
    def dispatch(self, method: str, args: Any) -> Any: ...

def java_class(name: str) -> Any: ...
