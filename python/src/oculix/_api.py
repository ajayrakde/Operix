"""Java overload binding, fields and typed facades for the generated API."""
from __future__ import annotations

import inspect
import gzip
import json
import keyword
from pathlib import Path
from typing import Any

from ._bridge import RemoteWrapper, RemoteObject, register_wrapper, _WRAPPER_TYPES

_SCHEMA = json.loads(gzip.decompress(Path(__file__).with_name('_api_schema.json.gz').read_bytes()))
_TYPES = {}


def _default_bridge():
    import oculix
    return oculix.default_bridge()


def _identifier(name):
    return name + '_' if keyword.iskeyword(name) or name in {'self', 'cls'} else name


def _is_java_type(actual, formal):
    if actual == formal or formal == 'java.lang.Object': return True
    seen = set()
    pending = [actual]
    while pending:
        name = pending.pop()
        if name == formal: return True
        if name in seen: continue
        seen.add(name)
        row = _SCHEMA.get(name, {})
        pending.extend(row.get('interfaces', []))
        if row.get('superclass'): pending.append(row['superclass'])
    return False


def _score(value, formal):
    if value is None:
        return -1 if formal in {'boolean','byte','short','int','long','float','double','char'} else 0
    if isinstance(value, RemoteWrapper): value = value._remote
    if isinstance(value, RemoteObject):
        if value._class == formal: return 12
        if _is_java_type(value._class, formal): return 8 if formal != 'java.lang.Object' else 1
        # External Java inheritance is verified by the JVM resolver.
        return 2 if value._class not in _SCHEMA else -1
    if isinstance(value, JavaCallback): return 8 if formal in {value.interface, 'java.lang.Object'} else -1
    if callable(value): return 5 if formal == 'java.lang.Object' or _SCHEMA.get(formal, {}).get('interface') else -1
    if formal == 'java.lang.Object': return 1
    if type(value) is bool: return 12 if formal in {'boolean','java.lang.Boolean'} else -1
    if type(value) is int:
        if formal in {'int','java.lang.Integer'}: return 12 if -(2**31) <= value < 2**31 else -1
        if formal in {'long','java.lang.Long'}: return 10 if -(2**63) <= value < 2**63 else -1
        if formal in {'short','java.lang.Short'}: return 8 if -(2**15) <= value < 2**15 else -1
        if formal in {'byte','java.lang.Byte'}: return 7 if -128 <= value <= 127 else -1
        return 5 if formal in {'double','float','java.lang.Double','java.lang.Float'} else -1
    if isinstance(value, float):
        return 12 if formal in {'double','java.lang.Double'} else 8 if formal in {'float','java.lang.Float'} else -1
    if isinstance(value, str):
        if formal == 'java.lang.String': return 12
        if formal == 'java.lang.CharSequence': return 10
        if formal in {'char','java.lang.Character'}: return 8 if len(value) == 1 else -1
        return 5 if _SCHEMA.get(formal, {}).get('enum') else -1
    if isinstance(value, (bytes, bytearray)) and formal == 'byte[]': return 12
    if isinstance(value, (list, tuple, bytes, bytearray)):
        if formal.endswith('[]'):
            scores = [_score(v, formal[:-2]) for v in value]
            return -1 if any(v < 0 for v in scores) else 8
        return 6 if formal in {'java.util.List','java.util.Collection','java.lang.Iterable','java.util.Set'} else -1
    if isinstance(value, dict): return 8 if formal == 'java.util.Map' else -1
    return -1


def _bind(member, args, kwargs):
    parameters = member['parameters']
    values = list(args)
    varargs = member['varargs']
    fixed = len(parameters) - int(varargs)
    if not varargs and len(values) > len(parameters): raise TypeError('Too many positional arguments')
    for i, p in enumerate(parameters):
        name = _identifier(p['name'])
        if name in kwargs:
            if i < len(args): raise TypeError('Multiple values for ' + name)
            if i != len(values): raise TypeError('Missing preceding argument')
            values.append(kwargs[name])
        elif i >= len(values) and i < fixed:
            raise TypeError('Missing argument ' + name)
    known = {_identifier(p['name']) for p in parameters}
    if set(kwargs) - known: raise TypeError('Unknown argument: ' + ', '.join(set(kwargs) - known))
    if varargs:
        # Both Java's explicit array form and Python's expanded positional form.
        if len(values) == len(parameters) and isinstance(values[-1], (list, tuple)):
            pass
        else: values = values[:fixed] + [values[fixed:]]
    elif len(values) != len(parameters): raise TypeError('Wrong argument count')
    scores = [_score(v, p['type']) for v, p in zip(values, parameters)]
    if any(s < 0 for s in scores): raise TypeError('Argument types do not match')
    return values, sum(scores) - int(varargs)


class BoundJavaMethod:
    def __init__(self, descriptor, instance, owner):
        self.descriptor, self.instance, self.owner = descriptor, instance, owner
        self.__name__ = descriptor.name
        self.__doc__ = descriptor.__doc__
        self.overloads = tuple(descriptor.members)
        member = next((m for m in descriptor.members if m['static'] or instance is not None), descriptor.members[0])
        params = [inspect.Parameter(_identifier(p['name']), inspect.Parameter.VAR_POSITIONAL
                  if member['varargs'] and i == len(member['parameters']) - 1 else inspect.Parameter.POSITIONAL_OR_KEYWORD)
                  for i, p in enumerate(member['parameters'])]
        self.__signature__ = inspect.Signature(params)

    def overload(self, *parameter_types):
        """Choose an exact Java overload where Python values cannot disambiguate it."""
        members = [m for m in self.descriptor.members if tuple(p['type'] for p in m['parameters']) == parameter_types]
        if not members: raise TypeError('No Java overload with types ' + repr(parameter_types))
        return BoundJavaMethod(JavaMethod(self.descriptor.name, members), self.instance, self.owner)

    def __call__(self, *args, **kwargs):
        candidates = []
        for m in self.descriptor.members:
            if self.instance is None and not m['static'] and self.__name__ != '<init>': continue
            try: values, score = _bind(m, args, kwargs)
            except TypeError: continue
            candidates.append((score, m, values))
        if not candidates:
            raise TypeError(f'No matching overload for {self.owner.JAVA_CLASS}.{self.__name__}; see .overloads')
        best_score = max(c[0] for c in candidates)
        best = [c for c in candidates if c[0] == best_score]
        # Drop less specific reference overloads for null/reference arguments.
        if len(best) > 1:
            specific = [c for c in best if all(c is other or all(
                a['type'] == b['type'] or _is_java_type(a['type'], b['type'])
                for a, b in zip(c[1]['parameters'], other[1]['parameters'])) for other in best)]
            if len(specific) == 1: best = specific
        signatures = {tuple(p['type'] for p in c[1]['parameters']) for c in best}
        if len(signatures) > 1:
            raise TypeError(f'Ambiguous Java overload for {self.__name__}: {sorted(signatures)}; use .overload(*types)')
        _, member, values = best[0]
        bridge = self.instance._remote._bridge if self.instance is not None else _default_bridge()
        prepared = []
        for p, v in zip(member['parameters'], values):
            if callable(v) and not isinstance(v, JavaCallback):
                interface = p['type']
                if interface == 'java.lang.Object': interface = 'org.sikuli.script.ObserverCallBack'
                v = JavaCallback(interface, v)
            prepared.append(v)
        types = [p['type'] for p in member['parameters']]
        if self.__name__ == '<init>': return bridge.create(self.owner.JAVA_CLASS, prepared, parameter_types=types)
        if member['static']:
            return bridge.call_static(self.owner.JAVA_CLASS, self.__name__, prepared, parameter_types=types)
        return bridge.call(self.instance._remote._ref, self.__name__, prepared, parameter_types=types)


class JavaMethod:
    """A declared, finite set of Java overloads; no arbitrary method forwarding."""
    def __init__(self, name, members):
        self.name, self.members = name, members
        self.__doc__ = '\n'.join(m['name'] + '(' + ', '.join(p['type'] + ' ' + p['name'] for p in m['parameters']) + ')' for m in members)

    def __get__(self, instance, owner=None):
        return BoundJavaMethod(self, instance, owner)


class JavaField:
    def __init__(self, field): self.field = field
    def __get__(self, instance, owner=None):
        if instance is None and not self.field['static']: return self
        bridge = instance._remote._bridge if instance is not None else _default_bridge()
        req = {'class': owner.JAVA_CLASS, 'field': self.field['name']}
        if instance is not None and not self.field['static']: req = {'ref': instance._remote._ref, 'field': self.field['name']}
        from ._bridge import _decode
        return _decode(bridge, bridge._request(req))
    def __set__(self, instance, value):
        self.set(type(instance), instance, value)
    def set(self, owner, instance, value):
        if self.field['final']: raise AttributeError('Java field is final: ' + self.field['name'])
        if _score(value, self.field['type']) < 0: raise TypeError('Value does not match Java field type ' + self.field['type'])
        bridge = instance._remote._bridge if instance is not None else _default_bridge()
        from ._bridge import _encode
        req = {'class': owner.JAVA_CLASS, 'field': self.field['name'], 'value': _encode(value, bridge)}
        if instance is not None and not self.field['static']: req['ref'] = instance._remote._ref
        bridge._request(req)


class JavaMeta(type):
    def __setattr__(cls, name, value):
        descriptor = next((p.__dict__[name] for p in cls.__mro__ if name in p.__dict__), None)
        if isinstance(descriptor, JavaField): descriptor.set(cls, None, value)
        else: super().__setattr__(name, value)


class JavaObject(RemoteWrapper, metaclass=JavaMeta):
    JAVA_CLASS = 'java.lang.Object'
    def __init__(self, *args, **kwargs):
        schema = _SCHEMA.get(self.JAVA_CLASS)
        if schema is None: result = _default_bridge().create(self.JAVA_CLASS, list(args))
        else:
            if not schema['constructors']: raise TypeError(self.JAVA_CLASS + ' has no public constructors')
            result = BoundJavaMethod(JavaMethod('<init>', schema['constructors']), None, type(self))(*args, **kwargs)
        self._remote = result._remote if isinstance(result, RemoteWrapper) else result
        self._remote._bridge._cache[self._remote._ref] = self
    @property
    def _ref(self): return self._remote._ref
    @property
    def _bridge(self): return self._remote._bridge
    def __getattr__(self, name):
        if self.JAVA_CLASS in _SCHEMA: raise AttributeError(name)
        return super().__getattr__(name)
    def __iter__(self):
        if self._remote._class.startswith('java.util.'):
            iterator = self if self._remote._kind == 'iterator' or 'Iterator' in self._remote._class else self._call('iterator')
            while iterator._call('hasNext'): yield iterator._call('next')
        else: raise TypeError(self.JAVA_CLASS + ' is not an iterable')
    def __repr__(self): return f'<{type(self).__name__} {self._remote._class}#{self._remote._ref}>'


class JavaCallback:
    """Python implementation of a Java interface or ObserverCallBack.

    handler may be a function (single method) or an object/dict of method handlers.
    Keep this object alive while Java may invoke it; the bridge retains it until stop.
    """
    def __init__(self, interface, handler):
        self.interface = interface.JAVA_CLASS if hasattr(interface, 'JAVA_CLASS') else interface
        self.handler = handler
    def dispatch(self, method, args):
        if isinstance(self.handler, dict): function = self.handler[method]
        elif callable(self.handler): function = self.handler
        else: function = getattr(self.handler, method)
        return function(*args)


def java_class(name):
    if name in _TYPES: return _TYPES[name]
    cls = JavaMeta(name.rsplit('.', 1)[-1].replace('$', '_'), (JavaObject,), {'JAVA_CLASS': name, '__module__': 'oculix.java'})
    _TYPES[name] = cls
    register_wrapper(name, cls)
    return cls


def load_api(namespace):
    todo = set(_SCHEMA)
    while todo:
        ready = sorted(n for n in todo if _SCHEMA[n]['superclass'] not in todo)
        for name in ready:
            row = _SCHEMA[name]
            base = _TYPES.get(row['superclass'], JavaObject)
            attrs = {'JAVA_CLASS': name, '__module__': 'oculix.java', '__doc__': 'Java ' + name}
            groups = {}
            for m in row['methods']: groups.setdefault(m['name'], []).append(m)
            for mname, members in groups.items():
                descriptor = JavaMethod(mname, members)
                attrs[_identifier(mname)] = descriptor
                attrs[mname] = descriptor
            for f in row['fields']:
                if _identifier(f['name']) not in attrs: attrs[_identifier(f['name'])] = JavaField(f)
            cls = JavaMeta(row['python_name'], (base,), attrs)
            _TYPES[name] = cls
            register_wrapper(name, cls)
            namespace[row['python_name']] = cls
        todo -= set(ready)
    for name, cls in _TYPES.items():
        if '$' in name and name.rsplit('$', 1)[0] in _TYPES:
            setattr(_TYPES[name.rsplit('$', 1)[0]], name.rsplit('$', 1)[1], cls)
    namespace['__all__'] = sorted(row['python_name'] for row in _SCHEMA.values())
