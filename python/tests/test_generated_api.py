"""The generated declarations must cover the pinned Java surface exactly."""
import ast
import keyword
import inspect
import json
from pathlib import Path
import pytest
import oculix
from oculix._api import _SCHEMA, _TYPES, JavaMethod, JavaField, _bind
from oculix._bridge import _WRAPPER_TYPES, _decode


def test_every_public_type_and_java_overload_is_declared():
    for name, row in _SCHEMA.items():
        cls = _TYPES[name]
        assert _WRAPPER_TYPES[name] is cls
        for method in row['methods']:
            member = inspect.getattr_static(cls, method['name'] + '_' if keyword.iskeyword(method['name']) else method['name'])
            assert isinstance(member, JavaMethod)
            signature = (method['static'], tuple(p['type'] for p in method['parameters']))
            assert signature in {(m['static'], tuple(p['type'] for p in m['parameters'])) for m in member.members}
        for field in row['fields']:
            if field['name'] not in {m['name'] for m in row['methods']}:
                assert isinstance(inspect.getattr_static(cls, field['name']), JavaField)
    ast.parse(Path(oculix.__file__).parent.joinpath('java/__init__.pyi').read_text())


def test_java_inheritance_nested_types_and_false_argument(bridge=None):
    assert issubclass(oculix.Match, oculix.Region)
    assert issubclass(oculix.Screen, oculix.Region)
    assert oculix.OCR.Options.JAVA_CLASS == 'org.sikuli.script.OCR$Options'
    member = next(m for m in oculix.Region.setThrowException.overloads if len(m['parameters']) == 1)
    args, score = _bind(member, (False,), {})
    assert args == [False]
    assert score >= 0


def test_names_that_never_existed_are_not_exposed():
    assert not hasattr(oculix.PaddleOCREngine, 'getInstance')
    assert not hasattr(oculix.ADBScreen, 'tap')
    assert not hasattr(oculix.Region, 'capture')
    assert hasattr(oculix.Screen, 'capture')
