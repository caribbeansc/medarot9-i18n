"""Builds the translated game files (a LayeredFS mod) from the player's dump and a language pack.

  out/<title>/romfs/...      scripts, data tables, map files, fonts, textures
  out/<title>/exefs/code.bin the game's code with the translated built-in texts
<title> is 0004000000174F00 (Kuwagata) or 0004000000174E00 (Kabuto). Both editions share every file; each has its
own code.bin patch (binary/exefs/code.bin.json for Kuwagata, code.bin.kabuto.json for Kabuto).

Emulators of the Citra family (Azahar, Citra, Lime3DS...) load mods from their "load/mods/<title id>/" folder; on a
real console Luma3DS loads them from "/luma/titles/<title id>/". With the 1.3.0 update installed, the mod of the base
title also covers the update.

A pack is made for the game with its 1.3.0 update; what the update changed also has a 1.0 variant (`<name>.v10.json`,
tools/port_v10.py), so the same pack builds for the game without the update (version 1.0) too.
"""
import json
import shutil
from pathlib import Path

import m9.codec  # noqa: F401
from m9 import names, patch, script, terms
from m9.dump import Dump

REPO = Path(__file__).resolve().parents[1]


class BuildError(Exception):
    pass


def _groups(files, load):
    """{game file: [pack file contents, ...]}: a game file can have a 1.3.0 and a 1.0 (`.v10`) variant."""
    g = {}
    for f in files:
        d = load(f)
        g.setdefault(d['file'], []).append(d)
    return g


def _misses(lines, jp: bytes) -> int:
    f = script.fields(jp)
    return sum(1 for e in lines if not (0 <= e['i'] < len(f)) or script.fingerprint(f[e['i']]) != e['src'])


def build(dump: Dump, lang: str, out: Path, log=print):
    """Writes the translated files for the player's game: version 1.3.0 (game + update) or 1.0 (game alone). Every
    pack file made for the other version is skipped: the variant whose fingerprints match the player's file wins."""
    pack = REPO / 'langs' / lang
    if not pack.is_dir():
        raise BuildError(f'no language pack langs/{lang}')
    root = Path(out) / dump.title
    if root.exists():
        shutil.rmtree(root)
    romfs, exefs = root / 'romfs', root / 'exefs'
    romfs.mkdir(parents=True)
    exefs.mkdir(parents=True)
    expand = terms.expander(lang)
    problems = []

    def read_json(f):
        return json.loads(f.read_text(encoding='utf-8'))

    # scripts
    n = skipped = 0
    for rel, variants in sorted(_groups(sorted((pack / 'script').rglob('*.json')), read_json).items()):
        if not dump.has(rel):                       # only in the other version (1.3.0-only scripts on a 1.0 game)
            skipped += 1
            continue
        jp = dump.read(rel)
        best = min(variants, key=lambda d: _misses(d['lines'], jp))
        data, probs = script.apply(jp, best['lines'], expand)
        problems += [(rel, i, why) for i, why in probs]
        dst = romfs / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        n += 1
    log(f'scripts: {n}' + (f' ({skipped} only in the other version)' if skipped else ''))

    # binary patches (data tables, maps, code)
    n = 0
    code = dump.code()
    code_sha = patch.sha1(code) if code else None
    code_done = False
    for rel, variants in sorted(_groups(sorted((pack / 'binary').rglob('*.json')), patch.load).items()):
        if rel == 'exefs/code.bin':
            p = next((v for v in variants if v['src'] == code_sha), None)   # this edition and version
            if p:
                (exefs / 'code.bin').write_bytes(patch.apply(p, code))
                code_done = True
                n += 1
            continue
        if not dump.has(rel):
            continue
        jp = dump.read(rel)
        sha = patch.sha1(jp)
        p = next((v for v in variants if v['src'] == sha), None)
        if p is None:
            raise BuildError(f'{rel}: your copy of this file is not the one the language pack was made for '
                             f'(Medarot 9 {dump.edition.title()} {dump.version})')
        dst = romfs / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(patch.apply(p, jp))
        n += 1
    log(f'binary patches: {n}')
    if not code_done:
        raise BuildError(f'this language pack has no code patch for your code.bin (Medarot 9 {dump.edition.title()} '
                         f'{dump.version}): is it the original game (1.0) or the original 1.3.0 update?')

    # names in the data tables, from the terms (a changed term reaches them too)
    n = 0
    if (pack / 'names').is_dir():
        for rel, variants in sorted(_groups(sorted((pack / 'names').glob('*.json')), read_json).items()):
            if not dump.has(rel):
                continue
            jp = dump.read(rel)
            best = min(variants, key=lambda d: sum(1 for s in d['slots']
                                                   if names.fingerprint(jp[s['off']:s['off'] + s['size']]) != s['src']))
            dst = romfs / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            data, probs = names.apply(dst.read_bytes() if dst.exists() else jp, jp, best['slots'], expand)
            problems += [(rel, off, why) for off, why in probs]
            dst.write_bytes(data)
            n += len(best['slots'])
    log(f'names in data tables: {n}')

    # textures (binary patches of the relabelled textures)
    n = 0
    for rel, variants in sorted(_groups(sorted((pack / 'textures').rglob('*.json.gz')), patch.load).items()):
        if not dump.has(rel):
            continue
        jp = dump.read(rel)
        sha = patch.sha1(jp)
        p = next((v for v in variants if v['src'] == sha), None)
        if p is None:
            raise BuildError(f'{rel}: your copy of this texture is not the one the language pack was made for')
        dst = romfs / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(patch.apply(p, jp))
        n += 1
    log(f'textures: {n}')
    return problems
