#!/usr/bin/env python3
"""Local-only dependency extraction, build and one real original-code mission."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parent
for cmd in ('cmake', 'g++'):
    if not shutil.which(cmd):
        sys.exit(f'Missing {cmd}. See reproduction/README.md for prerequisites.')
header = root / 'deps/boost/usr/include/boost/math/distributions/students_t.hpp'
system_header = Path('/usr/include/boost/math/distributions/students_t.hpp')
if not header.exists() and not system_header.exists():
    package = root / 'deps/libboost1.83-dev_1.83.0-2.1ubuntu3.2_amd64.deb'
    if not package.exists() or not shutil.which('dpkg-deb'):
        sys.exit('Install Boost >= 1.78 headers; see README. Bundled package extraction requires dpkg-deb.')
    expected = '519ecf2c64308527e15b6582955681d192a832250baa4bc424967aaf7d02d68f'
    if hashlib.sha256(package.read_bytes()).hexdigest() != expected:
        sys.exit('Boost package hash mismatch; stop.')
    subprocess.run(['dpkg-deb','-x',str(package),str(root/'deps/boost')],check=True)
for command in (
    ['cmake','-S',str(root),'-B',str(root/'build'),'-DCMAKE_BUILD_TYPE=Release'],
    ['cmake','--build',str(root/'build'),'-j','2'],
    [sys.executable,str(root/'run_smoke.py')],
):
    print('+', ' '.join(command), flush=True)
    subprocess.run(command,check=True)
