#!/usr/bin/env python3
"""
Split data/characters.json into data/characters/{id}.json files.
Run this when you want per-character files for easier editing.
"""
from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
IN = DATA / 'characters.json'
OUTDIR = DATA / 'characters'

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if not IN.exists():
        print('No', IN)
        return
    arr = json.loads(IN.read_text(encoding='utf-8'))
    for c in arr:
        cid = c.get('id')
        if not cid:
            print('Skipping entry without id:', c)
            continue
        p = OUTDIR / f"{cid}.json"
        p.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Wrote', p)

if __name__ == '__main__':
    main()
