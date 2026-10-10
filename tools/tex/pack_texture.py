#!/usr/bin/env python3
"""pack_texture.py - re-render textures from their specs and store them in the language pack (Oct 2026).

For each spec name (the file name in translation-work/tex/specs/, e.g. mdr__tex__m9_map_000.ctpk.json):
  1. texlib render  -> data/romfs_tex_<lang>/<rel> (+ preview in translation-work/tex/preview/)
  2. the pack patch -> langs/<lang>/textures/<rel>.json.gz (against the Japanese texture the game reads)
  3. the published spec -> langs/<lang>/texture_specs/<spec> (working notes, keys starting with '_', left out)

Run it with /opt/homebrew/bin/python3 (etcpak; see tools/tex/README.md).

  python3 tools/tex/pack_texture.py <spec name> [...] [--lang es]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'tools'))
sys.path.insert(0, str(REPO))
import texlib  # noqa: E402
from m9 import patch  # noqa: E402

SPECS = REPO / 'translation-work' / 'tex' / 'specs'


def no_notes(x):
    if isinstance(x, dict):
        return {k: no_notes(v) for k, v in x.items() if not k.startswith('_')}
    if isinstance(x, list):
        return [no_notes(v) for v in x]
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('specs', nargs='+')
    ap.add_argument('--lang', default='es')
    a = ap.parse_args()
    for name in a.specs:
        spec_path = SPECS / name
        spec = json.loads(spec_path.read_text(encoding='utf-8'))
        rel = spec['rel']
        texlib.render(spec, write=True, quiet=True)
        out = (REPO / 'data' / f'romfs_tex_{a.lang}' / rel).read_bytes()
        jp = texlib.jp_bytes(rel)
        p = patch.make(rel, jp, out, enc='b64')
        assert patch.apply(p, jp) == out
        patch.save(p, REPO / 'langs' / a.lang / 'textures' / (rel + '.json'), compress=True)
        dst = REPO / 'langs' / a.lang / 'texture_specs' / name
        dst.write_text(json.dumps(no_notes(spec), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'{rel}: rendered, pack patch and spec written')


if __name__ == '__main__':
    main()
