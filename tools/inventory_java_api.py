#!/usr/bin/env python3
"""Inventory the pinned Java artifact and measure explicit Python wrapper coverage."""

import argparse
import gzip
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python/src'))
import oculix
from oculix._bridge import _WRAPPER_TYPES


def reflected_inventory(jar, compiler_jar):
    destination = ROOT / 'jvm-bridge/target/api-inventory'
    destination.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'tools/java/ApiInventory.java'
    if compiler_jar:
        command = ['java', '-jar', str(compiler_jar), '-17', '-classpath', str(jar)]
    elif shutil.which('javac'):
        command = ['javac', '-cp', str(jar)]
    else:
        raise SystemExit('A Java 17+ JDK is required; alternatively supply --compiler-jar for Eclipse ECJ.')
    subprocess.run(command + ['-d', str(destination), str(source)], check=True)
    result = subprocess.run(
        ['java', '-cp', os.pathsep.join([str(jar), str(destination)]), 'ApiInventory', str(jar)],
        text=True, capture_output=True, check=True, timeout=120,
    )
    return json.loads(result.stdout)


def python_member(wrapper, name):
    if wrapper is None:
        return None
    for parent in wrapper.__mro__:
        if name in parent.__dict__:
            return parent.__dict__[name]
    return None


def coverage(method, wrapper):
    member = python_member(wrapper, method['name'])
    if member is None:
        return 'missing'
    is_static = isinstance(member, (staticmethod, classmethod))
    if is_static != method['static']:
        return 'static_mismatch'
    function = member.__func__ if is_static else member
    try:
        parameters = list(inspect.signature(function).parameters.values())
    except (TypeError, ValueError):
        return 'signature_unavailable'
    if not isinstance(member, staticmethod):
        parameters = parameters[1:]
    positional = [p for p in parameters if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    minimum = sum(p.default is p.empty for p in positional)
    maximum = len(positional)
    if any(p.kind == p.VAR_POSITIONAL for p in parameters):
        return 'variadic_forwarder'
    if any(p.kind == p.KEYWORD_ONLY and p.default is p.empty for p in parameters):
        return 'arity_mismatch'
    if minimum <= len(method['parameters']) <= maximum:
        return 'explicit_name_and_arity'
    return 'arity_mismatch'


def summarize(inventory):
    wrappers = dict(_WRAPPER_TYPES)
    wrappers[oculix.OCR.JAVA_CLASS] = oculix.OCR
    rows = []
    for cls in inventory['classes']:
        wrapper = wrappers.get(cls['class'])
        methods = [m for m in cls['methods'] if m['declaring_class'] != 'java.lang.Object']
        results = [dict(m, coverage=coverage(m, wrapper)) for m in methods]
        java_names = {m['name'] for m in cls['methods']}
        python_names = set()
        if wrapper is not None:
            for parent in wrapper.__mro__:
                python_names.update(name for name, value in parent.__dict__.items()
                                    if not name.startswith('_') and not inspect.isclass(value)
                                    and (callable(value) or isinstance(value, (staticmethod, classmethod))))
        counts = {}
        for method in results:
            counts[method['coverage']] = counts.get(method['coverage'], 0) + 1
        rows.append({
            'class': cls['class'],
            'python_wrapper': None if wrapper is None else wrapper.__qualname__,
            'methods': results,
            'counts': counts,
            'python_only_names': sorted(python_names - java_names),
            'constructors': cls['constructors'],
            'fields': cls['fields'],
        })
    return rows


def report(rows, version):
    lines = [
        '# Python wrapper coverage against Oculix ' + version, '',
        'Generated from the pinned bridge JAR by `tools/inventory_java_api.py`.', '',
        '**Name and arity coverage is not verified semantic parity.** It only means an',
        'explicit Python method accepts the Java argument count and has matching',
        'static/instance placement. It does not verify parameter types, overload',
        'selection, return annotations, defaults, callbacks or runtime behavior.', '',
        'The complete machine inventory includes inherited methods, constructors,',
        'public fields, exception types and generic types. `java.lang.Object` methods',
        'are retained in that inventory but excluded from coverage counts below.', '',
    ]
    total = sum(len(r['methods']) for r in rows)
    explicit = sum(r['counts'].get('explicit_name_and_arity', 0) for r in rows)
    registered = sum(r['python_wrapper'] is not None for r in rows)
    lines += [
        f'- Public Java classes/interfaces/enums inventoried: **{len(rows)}**.',
        f'- Java types with a Python class facade: **{registered}** (including the static OCR facade).',
        f'- Public method overloads across classes, including inheritance: **{total}**.',
        f'- Overloads with an explicit Python name and matching arity/staticness: **{explicit}**.',
        f'- Remaining method overloads: **{total - explicit}**.',
        '- Constructors and fields are inventoried but not included in method-coverage totals.',
        '- Dynamic forwarding is not counted as explicit coverage.',
        '- The broad inventory includes Oculix support, remote and guide packages, not only desktop automation.', '',
        '## Existing wrapper classes', '',
        '| Java class | Overloads | Explicit name + arity | Missing or incompatible |',
        '|---|---:|---:|---:|',
    ]
    for row in rows:
        if row['python_wrapper'] is not None:
            good = row['counts'].get('explicit_name_and_arity', 0)
            lines.append(f"| `{row['class']}` | {len(row['methods'])} | {good} | {len(row['methods']) - good} |")
    lines += ['', '## Python declarations absent from the Java class', '',
              'These declarations need correction or removal; a dynamic call cannot make',
              'a nonexistent Java method work. Constructors and private helpers are excluded.', '']
    for row in rows:
        if row['python_only_names']:
            lines.append('- `' + row['class'] + '`: ' + ', '.join('`' + name + '`' for name in row['python_only_names']) + '.')
    lines += ['', '## Missing signatures in existing wrapper classes', '',
              'Signatures below identify missing or incompatible declarations. Parameter',
              'names are marked absent in the machine inventory when the Java artifact',
              'was compiled without parameter-name metadata; `arg0` is not an original',
              'source parameter name.', '']
    for row in rows:
        if row['python_wrapper'] is None:
            continue
        missing = [m for m in row['methods'] if m['coverage'] != 'explicit_name_and_arity']
        if not missing:
            continue
        lines += ['### `' + row['class'] + '`', '']
        for method in missing:
            params = ', '.join(p['type'] for p in method['parameters'])
            prefix = 'static ' if method['static'] else ''
            lines.append(f"- `{prefix}{method['return_type']} {method['name']}({params})` — {method['coverage']}.")
        lines += ['']
    lines += ['## Unregistered public Java classes', '',
              'These classes still fall back to generic remote objects where reachable.', '']
    lines += ['- `' + r['class'] + '`' for r in rows if r['python_wrapper'] is None]
    return '\n'.join(lines) + '\n'


def normalized_manifest(inventory, version):
    # Store repeated inherited method definitions once, with per-class indices.
    members = []
    indices = {}
    classes = []
    for cls in inventory['classes']:
        row = dict(cls)
        method_ids = []
        for method in row.pop('methods'):
            member = dict(method)
            member.pop('inherited')
            key = json.dumps(member, sort_keys=True, separators=(',', ':'))
            if key not in indices:
                indices[key] = len(members)
                members.append(member)
            method_ids.append(indices[key])
        row['method_ids'] = method_ids
        classes.append(row)
    return {'oculix_version': version, 'classes': classes, 'methods': members,
            'unavailable_classes': inventory['unavailable_classes']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jar', type=Path)
    parser.add_argument('--compiler-jar', type=Path)
    parser.add_argument('--check', action='store_true', help='Fail if committed inventory or coverage is stale.')
    args = parser.parse_args()
    pom = ET.parse(ROOT / 'jvm-bridge/pom.xml').getroot()
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    version = pom.find('m:properties/m:oculix.version', ns).text
    bridge_version = pom.find('m:version', ns).text
    jar = args.jar or ROOT / f'jvm-bridge/target/operix-jvm-bridge-{bridge_version}.jar'
    if not jar.is_file():
        parser.error(f'Bridge JAR missing: {jar}. Build it with Maven first.')
    inventory = reflected_inventory(jar, args.compiler_jar)
    if inventory['unavailable_classes']:
        raise SystemExit('Incomplete inventory: ' + json.dumps(inventory['unavailable_classes']))
    manifest = normalized_manifest(inventory, version)
    raw = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
    artifacts = {
        ROOT / f'docs/java-api-{version}.json.gz': gzip.compress(raw, mtime=0),
        ROOT / 'docs/python-api-coverage.md': report(summarize(inventory), version).encode(),
    }
    stale = []
    for path, content in artifacts.items():
        if args.check:
            existing = path.read_bytes() if path.exists() else None
            # gzip headers differ across Python versions; compare the actual manifest.
            if path.suffix == '.gz' and existing is not None:
                current, expected = gzip.decompress(existing), gzip.decompress(content)
            else:
                # Windows Git checkouts may convert Markdown LF to CRLF.
                current = None if existing is None else existing.replace(b'\r\n', b'\n')
                expected = content
            if current != expected:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(content)
    if stale:
        raise SystemExit('Stale API coverage; regenerate: ' + ', '.join(stale))
    print(f"Inventoried {len(manifest['classes'])} public classes and {len(manifest['methods'])} distinct method definitions; no classes unavailable.")


if __name__ == '__main__':
    main()
