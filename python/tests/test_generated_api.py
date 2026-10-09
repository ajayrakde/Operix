"""The generated declarations must cover the pinned Java surface exactly."""
import ast
import keyword
import inspect
import json
from pathlib import Path
import pytest
import pyulix
from pyulix._api import _SCHEMA, _TYPES, JavaMethod, JavaField, _bind
from pyulix._bridge import _WRAPPER_TYPES, _decode


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
    ast.parse(Path(pyulix.__file__).parent.joinpath('java/__init__.pyi').read_text())


def test_java_inheritance_nested_types_and_false_argument(bridge=None):
    assert issubclass(pyulix.Match, pyulix.Region)
    assert issubclass(pyulix.Screen, pyulix.Region)
    assert pyulix.OCR.Options.JAVA_CLASS == 'org.sikuli.script.OCR$Options'
    member = next(m for m in pyulix.Region.setThrowException.overloads if len(m['parameters']) == 1)
    args = _bind(member, (False,), {})
    assert args == [False]


def test_names_that_never_existed_are_not_exposed():
    assert not hasattr(pyulix.PaddleOCREngine, 'getInstance')
    assert not hasattr(pyulix.ADBScreen, 'tap')
    assert not hasattr(pyulix.Region, 'capture')
    assert hasattr(pyulix.Screen, 'capture')


def test_nullable_and_generic_hints_are_source_backed():
    from tools.generate_python_api import annotation
    assert annotation('java.util.Iterator', {}, 'java.util.Iterator<org.sikuli.script.Match>') == 'Iterable[Any]'
    assert annotation('java.util.List', {'org.sikuli.script.Match': 'Match'}, 'java.util.List<org.sikuli.script.Match>') == 'Sequence[Match]'
    assert annotation('java.util.List', {}, 'java.util.List<? super java.lang.String>') == 'Sequence[Any]'
    for name in ['exists', 'existsText', 'getLastMatch']:
        assert all(m.get('nullable_return') for m in _SCHEMA['org.sikuli.script.Region']['methods'] if m['name'] == name)
