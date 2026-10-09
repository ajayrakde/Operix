#!/usr/bin/env python3
"""Check the built distribution's identity, namespace and preserved notices."""
import email
from pathlib import Path
import tarfile
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
project = tomllib.loads((ROOT / 'python/pyproject.toml').read_text())['project']
version = project['version']
assert project['name'] == 'pyulix'
assert 'b' in version, 'This fork is beta-only'
with zipfile.ZipFile(ROOT / f'python/dist/pyulix-{version}-py3-none-any.whl') as wheel:
    prefix = f'pyulix-{version}.dist-info/'
    metadata = email.message_from_bytes(wheel.read(prefix + 'METADATA'))
    assert metadata['Name'] == 'pyulix'
    assert metadata['Author'] == metadata['Maintainer'] == 'Ajay Rakde'
    assert not metadata['Author-email'] and not metadata['Maintainer-email']
    assert metadata['License-Expression'] == 'MIT'
    assert metadata.get_payload().startswith('> **Independent fork:**')
    assert set(metadata.get_all('License-File')) == {'LICENSE', 'NOTICE'}
    assert all(name.startswith(('pyulix/', prefix)) for name in wheel.namelist())
    for filename in ('LICENSE', 'NOTICE'):
        assert wheel.read(prefix + 'licenses/' + filename) == (ROOT / filename).read_bytes()
    for filename in ('py.typed', '_api_schema.json.gz', 'java/__init__.pyi'):
        assert 'pyulix/' + filename in wheel.namelist()
with tarfile.open(ROOT / f'python/dist/pyulix-{version}.tar.gz') as archive:
    for filename in ('LICENSE', 'NOTICE'):
        assert archive.extractfile(f'pyulix-{version}/{filename}').read() == (ROOT / filename).read_bytes()
print('Pyulix metadata, namespace, type assets and license/notice packaging passed')
