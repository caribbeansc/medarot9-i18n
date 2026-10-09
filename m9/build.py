"""Builds the translated game files (a LayeredFS mod) from the player's dump and a language pack.

  out/0004000000174F00/romfs/...      scripts, data tables, map files, fonts, textures
  out/0004000000174F00/exefs/code.bin the game's code with the translated built-in texts

Azahar loads mods from its "load/mods/<title id>/" folder; on a real console Luma3DS loads them from
"/luma/titles/<title id>/". With the 1.3.0 update installed, the mod of the base title also covers the update.
"""
import json
import shutil
from pathlib import Path

import m9.codec  # noqa: F401
from m9 import names, patch, script, terms
from m9.dump import Dump

REPO = Path(__file__).resolve().parents[1]
TID = '0004000000174F00'


class BuildError(Exception):
    pass


def build(dump: Dump, lang: str, out: Path, log=print):
    pack = REPO / 'langs' / lang
    if not pack.is_dir():
        raise BuildError(f'no language pack langs/{lang}')
    if dump.version != '1.3':
        raise BuildError('the translation is made for the game WITH its 1.3.0 update: point me at the update too '
                         '(its decrypted .cia, or a dumped folder), and install it in your emulator or console')
    root = Path(out) / TID
    if root.exists():
        shutil.rmtree(root)
    romfs, exefs = root / 'romfs', root / 'exefs'
    romfs.mkdir(parents=True)
    exefs.mkdir(parents=True)
    expand = terms.expander(lang)
    problems = []

    # scripts
    n = 0
    for f in sorted((pack / 'script').rglob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        data, probs = script.apply(dump.read(d['file']), d['lines'], expand)
        problems += [(d['file'], i, why) for i, why in probs]
        dst = romfs / d['file']
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        n += 1
    log(f'scripts: {n}')

    # binary patches (data tables, maps, code)
    n = 0
    for f in sorted((pack / 'binary').rglob('*.json')):
        p = patch.load(f)
        if p['file'] == 'exefs/code.bin':
            (exefs / 'code.bin').write_bytes(patch.apply(p, dump.code()))
        else:
            dst = romfs / p['file']
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(patch.apply(p, dump.read(p['file'])))
        n += 1
    log(f'binary patches: {n}')

    # names in the data tables, from the terms (a changed term reaches them too)
    n = 0
    for f in sorted((pack / 'names').glob('*.json')) if (pack / 'names').is_dir() else []:
        d = json.loads(f.read_text(encoding='utf-8'))
        dst = romfs / d['file']
        data, probs = names.apply(dst.read_bytes(), dump.read(d['file']), d['slots'], expand)
        problems += [(d['file'], off, why) for off, why in probs]
        dst.write_bytes(data)
        n += len(d['slots'])
    log(f'names in data tables: {n}')

    # textures (binary patches of the relabelled textures)
    n = 0
    for f in sorted((pack / 'textures').rglob('*.json.gz')):
        p = patch.load(f)
        dst = romfs / p['file']
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(patch.apply(p, dump.read(p['file'])))
        n += 1
    log(f'textures: {n}')
    return problems
