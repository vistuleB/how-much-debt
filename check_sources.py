"""Check that every raw source file is present and unchanged (size and SHA-256 in SOURCES.json).

    python3 -I check_sources.py
"""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
bad = 0
for f in json.loads((root / 'SOURCES.json').read_text())['files']:
    b = (root / f['path']).read_bytes()
    ok = len(b) == f['bytes'] and hashlib.sha256(b).hexdigest() == f['sha256']
    bad += not ok
    print('ok  ' if ok else 'BAD ', f['path'])
raise SystemExit(1 if bad else 0)
