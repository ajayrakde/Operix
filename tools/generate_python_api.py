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
        for p, source in zip(member['parameters'], found['parameters']):
            p['name'] = source['name']
            p['name_present'] = True
    return member


def identifier(name):
    return name + '_' if keyword.iskeyword(name) else name


def annotation(name, known):
    if name.endswith('[]'):
        return 'Sequence[' + annotation(name[:-2], known) + ']'
    if name in {'boolean', 'java.lang.Boolean'}: return 'bool'
    if name in {'byte', 'short', 'int', 'long', 'java.lang.Integer', 'java.lang.Long', 'java.lang.Short', 'java.lang.Byte'}: return 'int'
    if name in {'float', 'double', 'java.lang.Double', 'java.lang.Float'}: return 'float'
    if name in {'char', 'java.lang.Character', 'java.lang.String'}: return 'str'
    if name == 'void': return 'None'
    if name in known: return known[name]
    if name.startswith('java.util.') and any(x in name for x in ['List', 'Collection', 'Set']): return 'Sequence[Any]'
    if name.startswith('java.util.') and 'Map' in name: return 'Mapping[Any, Any]'
    return 'Any'


def generate(manifest, sources):
    methods = [enrich(dict(m, parameters=[dict(p) for p in m['parameters']]), sources) for m in manifest['methods']]
    schema = {}
    known = {c['class']: c['class'].split('.')[-1].replace('$', '_') for c in manifest['classes']}
    # Alias collisions across Java packages use the full package in the flat module.
    for name, alias in list(known.items()):
        if list(known.values()).count(alias) > 1: known[name] = name.replace('.', '_').replace('$', '_')
    for c in manifest['classes']:
        row = dict(c)
        row.pop('method_ids')
        row['methods'] = [methods[i] for i in c['method_ids']]
        row['constructors'] = [enrich(dict(m, parameters=[dict(p) for p in m['parameters']]), sources) for m in c['constructors']]
        row['python_name'] = known[c['class']]
        schema[c['class']] = row
    lines = ['"""Generated Oculix 4.0.0 API. Do not edit; run tools/generate_python_api.py."""',
             'from typing import Any, Sequence, Mapping, overload, ClassVar',
             'from oculix._api import JavaObject', '']
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
        lines += [f'class {known[name]}({parent}):', '    JAVA_CLASS: ClassVar[str]']
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
                if len(overloads) > 1: lines.append('    @overload')
                if m['static']: lines.append('    @staticmethod')
                params = [] if m['static'] else ['self']
                for i, p in enumerate(m['parameters']):
                    pname = identifier(p['name'])
                    if pname in {'self', 'cls'}: pname += '_'
                    typ = annotation(p['type'], known)
                    if m['varargs'] and i == len(m['parameters']) - 1:
                        params.append('*' + pname + ': ' + annotation(p['type'][:-2], known))
                    else: params.append(pname + ': ' + typ)
                result = 'None' if pyname == '__init__' else annotation(m['return_type'], known)
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
