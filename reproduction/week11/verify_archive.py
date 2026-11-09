#!/usr/bin/env python3
"""Verify and independently audit the published raw-evidence ZIP; no new run."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile


def main():
    root = Path(__file__).resolve().parent
    receipt = json.loads((root/'evidence/archive-manifest.json').read_text())
    archive_name = receipt['archive']
    if Path(archive_name).name != archive_name:
        raise ValueError('Archive filename must not contain a path')
    archive = root/'evidence'/archive_name
    if archive.stat().st_size != receipt['size_bytes']:
        raise ValueError('Archive size mismatch')
    hasher = hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    if digest != receipt['sha256']:
        raise ValueError('Archive SHA256 mismatch')
    with zipfile.ZipFile(archive) as zf:
        infos = zf.infolist()
        if len(infos) != receipt['files'] or sum(i.file_size for i in infos) != receipt['uncompressed_bytes']:
            raise ValueError('Archive inventory differs from receipt')
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError(f'Unsafe archive member: {info.filename}')
            if not path.parts or path.parts[0] != receipt['archive_root']:
                raise ValueError('Unexpected archive root')
        if len({i.filename for i in infos}) != len(infos):
            raise ValueError('Duplicate archive members')
        broken = zf.testzip()
        if broken is not None:
            raise ValueError(f'Archive CRC failure: {broken}')
        with tempfile.TemporaryDirectory(prefix='adapt-week11-audit-') as temp:
            zf.extractall(temp)
            batch = Path(temp)/receipt['archive_root']
            print(f'Archive verified: {len(infos)} files, SHA256 {digest}', flush=True)
            command = [sys.executable, str(root/'verify_results.py'), '--results', str(batch),
                       '--upstream', str(root.parent/'ADAPT-upstream'),
                       '--expected-attempts', str(receipt['formal_missions'])]
            return subprocess.run(command, check=False).returncode


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f'Evidence verification failed: {error}', file=sys.stderr)
        sys.exit(2)
