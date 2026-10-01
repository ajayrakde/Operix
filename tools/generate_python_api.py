#!/usr/bin/env python3
"""Generate the complete named Python API and overload stubs from the pinned inventory."""
import argparse
import gzip
import json
import keyword
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'python/src/oculix'


def simple_type(name):
    name = re.sub(r'<.*>', '', name).replace('...', '[]').replace(' ', '')
    return name.replace('$', '.').split('.')[-1]


def enrich(member, sources):
    candidates = [m for m in sources.get(member['declaring_class'], [])
                  if m['name'] == member['name'] and len(m['parameters']) == len(member['parameters'])]
    matching = [m for m in candidates if all(simple_type(a['type']) == simple_type(b['source_type'])
                or simple_type(a.get('generic_type', a['type'])) == simple_type(b['source_type'])
                for a, b in zip(member['parameters'], m['parameters']))]
    found = matching[0] if len(matching) == 1 else candidates[0] if len(candidates) == 1 else None
    if member['name'] == 'valueOf' and len(member['parameters']) == 1 and member['parameters'][0]['type'] == 'java.lang.String':
        member['parameters'][0].update(name='name', name_present=True)
    if found:
        member['nullable_return'] = found.get('nullable_return', False)
        for p, source in zip(member['parameters'], found['parameters']):
            p['name'] = source['name']
            p['name_present'] = True
    # Reviewed nullable fields / catch paths: initialization alone cannot
    # establish return nullability (e.g. Match.getTarget repairs its null field).
    if (member['declaring_class'], member['name']) in {
            ('org.sikuli.script.Element', 'getLastMatch'),
            ('org.sikuli.script.Element', 'getLastMatches'),
            ('org.sikuli.script.Image', 'getURL'),
            ('org.sikuli.script.Image', 'getLastSeen'),
            ('org.sikuli.script.Pattern', 'getFileURL'),
            ('org.sikuli.script.Pattern', 'getBImage'),
            ('org.sikuli.script.ImagePath$PathEntry', 'getURL'),
            ('org.sikuli.script.ImagePath', 'get'),
            ('org.sikuli.script.ImagePath', 'append'),
            ('org.sikuli.script.ImagePath', 'insert'),
            ('org.sikuli.script.ImagePath', 'replace'),
            ('org.sikuli.script.ImagePath', 'find'),
            ('org.sikuli.guide.SxImage', 'getImage'),
            ('org.sikuli.guide.SxArrow', 'getSource'),
            ('org.sikuli.guide.SxArrow', 'getDestination'),
            ('org.sikuli.util.OverlayCapturePrompt', 'getOriginal'),
            ('org.sikuli.util.SikulixFileChooser', 'open'),
            ('org.sikuli.util.SikulixFileChooser', 'save'),
            ('org.sikuli.util.SikulixFileChooser', 'saveAs'),
            ('org.sikuli.util.SikulixFileChooser', 'export'),
            ('org.sikuli.util.SikulixFileChooser', 'loadImage'),
            ('org.sikuli.support.FileManager', 'getProxy'),
            ('org.sikuli.support.gui.SXDialog', 'getItem'),
            ('org.sikuli.support.Commons', 'getStartClass'),
            ('org.sikuli.util.OverlayTransparentWindow', 'getJPanel'),
            ('org.sikuli.util.OverlayTransparentWindow', 'getJPanelGraphics'),
            ('java.io.File', 'getParent'),
            ('java.io.File', 'getParentFile'),
            ('java.io.File', 'list'),
            ('java.io.File', 'listFiles'),
            ('java.io.BufferedReader', 'readLine'),
            ('java.lang.Class', 'getSuperclass'),
            ('java.lang.Class', 'getDeclaringClass'),
            ('java.lang.Class', 'getEnclosingClass'),
            ('java.lang.Class', 'getComponentType'),
            ('java.awt.Graphics', 'getClipBounds'),
            ('org.sikuli.script.Region', 'existsText')}:
        member['nullable_return'] = True
    owner, name = member['declaring_class'], member['name']
    types = [p['type'] for p in member['parameters']]
    required = []
    if owner == 'org.sikuli.script.Image' and name == 'create' and types in [
            ['java.io.File'], ['java.net.URL'], ['org.sikuli.script.Image'], ['org.sikuli.script.Pattern']]:
        required = [0]
    if owner == 'org.sikuli.script.Pattern' and name == owner and types and types != ['java.lang.String']:
        required = [0]
    if owner == 'org.sikuli.script.Pattern' and name == 'targetOffset' and types == ['org.sikuli.script.Location']:
        required = [0]
    if owner == 'org.sikuli.script.OCR$Options' and name == 'psm' and types == ['org.sikuli.script.OCR$PSM']:
        required = [0]
    if owner == 'org.sikuli.script.OCR' and name == 'readText' and len(types) == 2:
        required = [1]
    if owner == 'org.sikuli.script.Region' and name == 'create' and types and types[0] in {
            'org.sikuli.script.Location', 'java.awt.Rectangle', 'org.sikuli.script.Region'}:
        required = [0]
    for index in required: member['parameters'][index]['non_null'] = True
    return member


def identifier(name):
    return name + '_' if keyword.iskeyword(name) else name


def split_generic(value):
    result, start, depth = [], 0, 0
    for i, char in enumerate(value):
        if char == '<': depth += 1
        elif char == '>': depth -= 1
        elif char == ',' and depth == 0:
            result.append(value[start:i].strip()); start = i + 1
    return result + [value[start:].strip()]


def annotation(name, known, generic=None):
    generic = generic or name
    # Java Object and erased/unbounded type variables remain permissive even
    # when Object itself has a facade. Python values can legitimately satisfy it.
    if name == 'java.lang.Object': return 'Any'
    if name.endswith('[]'):
        return 'Sequence[' + annotation(name[:-2], known, generic[:-2] if generic.endswith('[]') else name[:-2]) + ']'
    if name in {'boolean', 'java.lang.Boolean'}: return 'bool'
    if name in {'byte', 'short', 'int', 'long', 'java.lang.Integer', 'java.lang.Long', 'java.lang.Short', 'java.lang.Byte'}: return 'int'
    if name in {'float', 'double', 'java.lang.Double', 'java.lang.Float'}: return 'float'
    if name in {'char', 'java.lang.Character', 'java.lang.String'}: return 'str'
    if name == 'void': return 'None'
    if name in known: return known[name]
    args = split_generic(generic[generic.index('<') + 1:-1]) if '<' in generic and generic.endswith('>') else []
    def element(index):
        if index >= len(args) or args[index].startswith('?'): return 'Any'
        raw = args[index].split('<', 1)[0]
        return annotation(raw, known, args[index])
    if name.startswith('java.util.') and any(x in name for x in ['List', 'Collection', 'Set']): return 'Sequence[' + element(0) + ']'
    if name.startswith('java.util.') and 'Map' in name: return 'Mapping[' + element(0) + ', ' + element(1) + ']'
    if name in {'java.util.Iterator', 'java.lang.Iterable'}: return 'Iterable[' + element(0) + ']'
    return 'Any'


def input_annotation(parameter, known, schema):
    name = parameter['type']
    typ = annotation(name, known, parameter.get('generic_type'))
    if typ == 'Any': return typ
    choices = [typ, 'JavaObject']
    if name == 'byte[]': choices += ['bytes', 'bytearray']
    if schema.get(name, {}).get('enum'): choices.append('str')
    if schema.get(name, {}).get('interface') or name == 'org.sikuli.script.ObserverCallBack':
        choices += ['JavaCallback', 'Callable[..., Any]']
    if name not in {'boolean', 'byte', 'short', 'int', 'long', 'float', 'double', 'char'} and not parameter.get('non_null'):
        choices.append('None')
    return 'Union[' + ', '.join(dict.fromkeys(choices)) + ']'


def generate(manifest, sources):
    # Propagate explicit return-null evidence through same-class return delegates.
    changed = True
    while changed:
        changed = False
        for members in sources.values():
            for member in members:
                if member.get('nullable_return'): continue
                if any(other.get('nullable_return') and other['name'] == call['name'] and len(other['parameters']) == call['arity']
                       for call in member.get('return_calls', []) for other in members):
                    member['nullable_return'] = True; changed = True
    methods = [enrich(dict(m, parameters=[dict(p) for p in m['parameters']]), sources) for m in manifest['methods']]
    schema = {}
    known = {c['class']: c['class'].split('.')[-1].replace('$', '_') for c in manifest['classes']}
    # Alias collisions across Java packages use the full package in the flat module.
    for name, alias in list(known.items()):
        if list(known.values()).count(alias) > 1: known[name] = name.replace('.', '_').replace('$', '_')
    # Preserve Oculix aliases: java.awt.Image must not rename oculix.Image.
    support = json.loads(gzip.decompress((ROOT / 'tools/java-support-api-4.0.0.json.gz').read_bytes()))
    additional = []
    for c in support['classes']:
        name = c['class']
        if name in known: continue
        alias = name.rsplit('.', 1)[-1].replace('$', '_')
        if alias in known.values(): alias = 'Java' + alias
        if alias in known.values(): alias = name.replace('.', '_').replace('$', '_')
        known[name] = alias
        start = len(methods)
        methods.extend(enrich(dict(m, parameters=[dict(p) for p in m['parameters']]), sources) for m in c['methods'])
        additional.append(dict(c, method_ids=list(range(start, len(methods))), support_type=True))
    for name in ['org.sikuli.guide.NewAnimator', 'org.sikuli.support.gui.SXDialog$BasicItem']:
        known[name] = name.rsplit('.', 1)[-1].replace('$', '_')
        additional.append({'class': name, 'superclass': 'java.lang.Object', 'interfaces': [],
                           'interface': False, 'enum': False, 'constructors': [], 'fields': [],
                           'method_ids': [], 'opaque': True})
    for c in manifest['classes'] + additional:
        row = dict(c)
        row.pop('method_ids')
        row['methods'] = [methods[i] for i in c['method_ids']]
        row['constructors'] = [enrich(dict(m, parameters=[dict(p) for p in m['parameters']]), sources) for m in c['constructors']]
        row['python_name'] = known[c['class']]
        schema[c['class']] = row
    lines = ['"""Generated Oculix 4.0.0 API. Do not edit; run tools/generate_python_api.py."""', 'import typing',
             'from typing import Any, Sequence, Mapping, Iterable, Union, Optional, Callable, overload, ClassVar',
             'from oculix._api import JavaObject, JavaCallback', '']
    ordered = []
    todo = set(schema)
    while todo:
        ready = sorted(n for n in todo if schema[n]['superclass'] not in todo)
        if not ready: raise RuntimeError('Cyclic Java inheritance')
        ordered += ready
        todo -= set(ready)
    for name in ordered:
        c = schema[name]
        parent = known.get(c['superclass'], 'JavaObject')
        lines += [f'class {known[name]}({parent}):', '    JAVA_CLASS: ClassVar[str]',
                  '    @classmethod',
                  f'    def overload(cls, *parameter_types: str) -> Callable[..., {known[name]}]: ...']
        groups = {'__init__': c['constructors']}
        for m in c['methods']:
            groups.setdefault(identifier(m['name']), []).append(m)
        for field in c['fields']:
            if identifier(field['name']) not in groups:
                typ = annotation(field['type'], known)
                if field['static']: typ = f'ClassVar[{typ}]'
                lines.append(f"    {identifier(field['name'])}: {typ}")
        for pyname, overloads in groups.items():
            if not overloads: continue
            seen = set()
            for m in overloads:
                key = (m['static'], tuple(p['type'] for p in m['parameters']))
                if key in seen: continue
                seen.add(key)
                if len(overloads) > 1: lines.append('    @typing.overload')
                if m['static']: lines.append('    @staticmethod')
                params = [] if m['static'] else ['self']
                for i, p in enumerate(m['parameters']):
                    pname = identifier(p['name'])
                    if pname in {'self', 'cls'}: pname += '_'
                    typ = input_annotation(p, known, schema)
                    if m['varargs'] and i == len(m['parameters']) - 1:
                        params.append('*' + pname + ': Union[' + input_annotation(dict(p, type=p['type'][:-2], generic_type=p.get('generic_type', p['type'])[:-2]), known, schema) + ', ' + typ + ']')
                    else: params.append(pname + ': ' + typ)
                result = 'None' if pyname == '__init__' else annotation(m['return_type'], known, m.get('generic_return_type'))
                if m.get('nullable_return') and result not in {'Any', 'None'}: result = f'Optional[{result}]'
                lines.append(f"    def {pyname}({', '.join(params)}) -> {result}: ...")
        # Nested public classes retain Java's Outer.Inner access.
        for child in sorted(schema):
            if child.startswith(name + '$') and '$' not in child[len(name) + 1:]:
                lines.append(f"    {identifier(child.rsplit('$', 1)[-1])}: ClassVar[type[{known[child]}]]")
        lines += ['']
    runtime = ['"""Generated named Oculix API, with exact overload metadata."""',
               'from oculix._api import load_api', '',
               'load_api(globals())', '']
    return {
        PACKAGE / '_api_schema.json.gz': gzip.compress(json.dumps(schema, sort_keys=True, separators=(',', ':')).encode(), mtime=0),
        PACKAGE / 'java/__init__.py': '\n'.join(runtime).encode(),
        PACKAGE / 'java/__init__.pyi': '\n'.join(lines).encode(),
        PACKAGE / 'py.typed': b'',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-parameters', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(gzip.decompress((ROOT / 'docs/java-api-4.0.0.json.gz').read_bytes()))
    source_path = args.source_parameters or ROOT / 'tools/java-source-parameters.json.gz'
    data = source_path.read_bytes()
    sources = json.loads(gzip.decompress(data) if source_path.suffix == '.gz' else data)
    artifacts = generate(manifest, sources)
    for path, content in artifacts.items():
        if args.check:
            current = path.read_bytes() if path.exists() else None
            if path.suffix == '.gz' and current is not None:
                current, content = gzip.decompress(current), gzip.decompress(content)
            elif current is not None: current = current.replace(b'\r\n', b'\n')
            if current != content: raise SystemExit('Stale generated API: ' + str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    classes = json.loads(gzip.decompress(artifacts[PACKAGE / '_api_schema.json.gz']))
    own = [m for c in classes.values() for m in c['methods'] if m['declaring_class'] == c['class']]
    named = sum(all(p['name_present'] for p in m['parameters']) for m in own)
    print(f"Generated {len(classes)} types; {len(own)} declared method signatures; {named} signatures with source parameter names.")

if __name__ == '__main__': main()
