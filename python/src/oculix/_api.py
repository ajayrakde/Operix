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
        final = values[-1] if values else None
        remote = final._remote if isinstance(final, RemoteWrapper) else final
        explicit_array = (final is None or isinstance(final, (list, tuple))
                          or isinstance(final, (bytes, bytearray)) and parameters[-1]['type'] == 'byte[]'
                          or isinstance(remote, RemoteObject) and remote._class.startswith('['))
        if len(values) == len(parameters) and explicit_array:
            pass
        else: values = values[:fixed] + [values[fixed:]]
    elif len(values) != len(parameters): raise TypeError('Wrong argument count')
    return values


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
        bridge = self.instance._remote._bridge if self.instance is not None else _default_bridge()
        candidates = []
        for member in self.descriptor.members:
            if self.instance is None and not member['static'] and self.__name__ != '<init>': continue
            try: values = _bind(member, args, kwargs)
            except TypeError: continue
            prepared = []
            for parameter, value in zip(member['parameters'], values):
                if callable(value) and not isinstance(value, JavaCallback):
                    interface = parameter['type']
                    if interface == 'java.lang.Object': interface = 'org.sikuli.script.ObserverCallBack'
                    value = JavaCallback(interface, value)
                prepared.append(value)
            candidates.append((member, prepared))
        if not candidates:
            raise TypeError(f'No matching argument names/count for {self.owner.JAVA_CLASS}.{self.__name__}; see .overloads')
        # Java owns assignability, interface inheritance, unboxing and conversion.
        # Python only binds argument names/counts; stubs never gate runtime values.
        if len(candidates) > 1:
            index = bridge.resolve_overload(self.owner.JAVA_CLASS, self.__name__, candidates)
        else: index = 0
        member, prepared = candidates[index]
        for parameter, value in zip(member['parameters'], prepared):
            if value is None and parameter.get('non_null'):
                raise TypeError(f"{self.owner.JAVA_CLASS}.{self.__name__}: {parameter['name']} "
                                f"must not be None ({parameter['type']})")
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
        bridge = instance._remote._bridge if instance is not None else _default_bridge()
        from ._bridge import _encode
        req = {'class': owner.JAVA_CLASS, 'field': self.field['name'], 'value': _encode(value, bridge)}
        if instance is not None and not self.field['static']: req['ref'] = instance._remote._ref
        bridge._request(req)


class JavaMeta(type):
    def overload(cls, *parameter_types):
        """Select an exact public constructor, including null reference calls."""
        members = _SCHEMA.get(cls.JAVA_CLASS, {}).get('constructors', [])
        return BoundJavaMethod(JavaMethod('<init>', members), None, cls).overload(*parameter_types)
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
        if any(_SCHEMA.get(parent.JAVA_CLASS, {}).get('opaque') for parent in type(self).__mro__
               if hasattr(parent, 'JAVA_CLASS')):
            raise AttributeError(f'{self._remote._class} is an opaque Java handle; use the public owner API')
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


def java_class(name, *, parent=None):
    if name in _TYPES: return _TYPES[name]
    cls = JavaMeta(name.rsplit('.', 1)[-1].replace('$', '_'), (parent or JavaObject,), {'JAVA_CLASS': name, '__module__': 'oculix.java'})
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
