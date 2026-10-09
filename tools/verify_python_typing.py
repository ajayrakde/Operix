#!/usr/bin/env python3
"""Verify packaged Pylance/Pyright declarations, including nullable diagnostics."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def check(path):
    result = subprocess.run([sys.executable, '-m', 'pyright', '--pythonpath', sys.executable,
                             '--outputjson', str(path)], text=True, capture_output=True)
    if result.returncode not in (0, 1): raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)

positive = check(ROOT / 'python/typing_examples/api_usage.py')
assert positive['summary']['errorCount'] == 0, positive['generalDiagnostics']
with tempfile.TemporaryDirectory(prefix='operix-typing-') as directory:
    negative = Path(directory) / 'invalid.py'
    negative.write_text("from pyulix import Screen\nscreen = Screen()\nscreen.exists('missing.png').getScore()\nscreen.noSuchJavaMethod()\n")
    result = check(negative)
    rules = {d.get('rule') for d in result['generalDiagnostics'] if d['severity'] == 'error'}
    assert 'reportOptionalMemberAccess' in rules, result
    assert 'reportAttributeAccessIssue' in rules, result
print('Packaged autocomplete, generic returns and nullable diagnostics passed')
