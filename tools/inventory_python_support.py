#!/usr/bin/env python3
"""Inventory bounded public dependency types used by the selected Oculix API."""
import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SUPPORT_TYPES = [
    'java.io.File', 'java.net.URL', 'java.awt.image.BufferedImage',
    'java.awt.Rectangle', 'java.awt.Point', 'org.opencv.core.Mat',
    'java.awt.Dimension', 'java.awt.Color', 'java.io.BufferedReader',
    'java.lang.Class', 'java.net.Proxy', 'java.net.InetAddress',
    'java.awt.Robot', 'javax.swing.JPanel', 'java.awt.Graphics2D',
    'java.awt.Insets',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--compiler-jar', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    destination = ROOT / 'jvm-bridge/target/support-inventory'
    destination.mkdir(parents=True, exist_ok=True)
    if args.compiler_jar:
        command = ['java', '-jar', str(args.compiler_jar), '-17', '-classpath', str(args.jar)]
    elif shutil.which('javac'):
        command = ['javac', '-cp', str(args.jar)]
    else:
        raise SystemExit('Java compiler required; alternatively supply --compiler-jar.')
    subprocess.run(command + ['-d', str(destination), str(ROOT / 'tools/java/ApiInventory.java')], check=True)
    result = subprocess.run(['java', '-cp', os.pathsep.join([str(args.jar), str(destination)]),
                             'ApiInventory', str(args.jar), ','.join(SUPPORT_TYPES)],
                            text=True, capture_output=True, check=True, timeout=120)
    inventory = json.loads(result.stdout)
    if inventory['unavailable_classes']:
        raise SystemExit(str(inventory['unavailable_classes']))
    path = ROOT / 'tools/java-support-api-4.0.0.json.gz'
    data = json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()
    if args.check:
        if gzip.decompress(path.read_bytes()) != data:
            raise SystemExit('Stale Java support inventory')
    else:
        path.write_bytes(gzip.compress(data, mtime=0))
    print(f"Verified {len(inventory['classes'])} public support types")


if __name__ == '__main__':
    main()
