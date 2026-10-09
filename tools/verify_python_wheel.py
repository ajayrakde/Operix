#!/usr/bin/env python3
"""Install the wheel outside the checkout and exercise its real JVM/OCR API."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--jar', type=Path, default=ROOT / 'jvm-bridge/target/operix-jvm-bridge-1.2.0b2.jar')
parser.add_argument('--download', action='store_true', help='Exercise automatic download of the released fork JAR.')
args = parser.parse_args()
wheel = next((ROOT / 'python/dist').glob('pyulix-1.2.0b2-*.whl'))
with tempfile.TemporaryDirectory(prefix='operix-wheel-') as directory:
    target = Path(directory) / 'site'
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-deps', '--target', str(target), str(wheel)], check=True)
    env = dict(os.environ, PYTHONPATH=str(target))
    # A subprocess ensures an editable checkout cannot satisfy missing wheel files.
    code = '''
from pathlib import Path
import sys
import pyulix
import pyulix._bridge as transport
assert Path(pyulix.__file__).is_relative_to(Path(sys.argv[1]))
assert len(pyulix.java.__all__) == 240
if sys.argv[2] == 'download':
    transport.JAR_DIR = Path(sys.argv[1]).parent / 'fresh-jars'
    bridge = pyulix.Bridge()
else:
    bridge = pyulix.Bridge(jar_path=Path(sys.argv[2]))
transport._default_bridge = bridge
try:
    point = pyulix.Location(x=3, y=4)
    assert point.getX() == 3 and point.getY() == 4
    options = pyulix.OCR.Options().language('eng').psm(7)
    assert 'Submit 12345' in pyulix.OCR.readText(sys.argv[3], options)
finally:
    bridge.stop()
print('Clean wheel installation, typed API and real OCR passed')
'''
    subprocess.run([sys.executable, '-c', code, str(target), 'download' if args.download else str(args.jar.resolve()),
                    str(ROOT / 'python/tests/fixtures/ocr-submit.png')], cwd=directory, env=env, check=True, timeout=120)
