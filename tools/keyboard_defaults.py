#!/usr/bin/env python3
"""keyboard_defaults.py - the names the name keyboard suggests, translated in FULL-WIDTH letters (Oct 2026).

The game opens its name keyboard (mdr/spt/keypad.spt) on a name the script sets just before it (`nameset <var>
<name>` + `scriptcall keypad <var>`): the player's name テンマ (story/spt/name_input.spt), the first Medal's name
ジッパー (Kabuto) / ソウエン (Kuwagata) (story/spt/f01_000_110_00.spt and tri030_00.spt), a new rotation's name ローテ
(mdr/spt/setup_rotation.spt). The boot scripts give S8 the same テンマ before a game is started or loaded, and the
developer's chapter selector (story/spt/1st_set.spt) the same Medal names. They stayed Japanese until 11-oct-2026:
whoever just pressed OK kept a katakana name in every dialogue.

User decision (11-oct-2026): translate them, in full-width letters («ponlos con el texto espaciado para evitar
problemas»). The keyboard only types full-width characters, so the suggested name and an edited one look alike, and
full-width is what the original game always has there (the keyboard's OK check, the name buffers, the widths the
dialogue boxes were fitted to: tools/qa/box_fit.py measures the player's name as 3-6 full-width characters).
Nothing compares these names (scripts or code.bin; the code's own default rotation name is ローテーション, already
translated in the code patches).

  python3 tools/keyboard_defaults.py es en [--game <dump> --update <update .cia>]   (default: the m9 configuration)
Writes langs/<lang>/script/<file>.json (and the .v10.json variant where the pack has one, with the 1.0 indices).
Idempotent.
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from m9 import script  # noqa: E402

FILES = ('story/spt/name_input.spt', 'story/spt/f01_000_110_00.spt', 'story/spt/tri030_00.spt',
         'mdr/spt/setup_rotation.spt', 'spt/boot.spt', 'spt/bootKBT.spt', 'spt/bootKWG.spt', 'spt/bootSHOP.spt',
         'spt/bootTRY.spt', 'spt/game.spt', 'story/spt/1st_set.spt')
NAMES = {'テンマ': 'Ｔｅｎｍａ', 'ジッパー': 'Ｚｉｐｐｅｒ', 'ソウエン': 'Ｓｏｕｅｎ',
         'ローテ': {'es': 'Ｒｏｔａｃｉｏｎ', 'en': 'Ｒｏｔａｔｉｏｎ'}}
MAX_CHARS = 8                                   # the keyboard's limit


def defaults(jp: bytes):
    """[(index, Japanese name)] of every `nameset <var> <suggested name>` in a script."""
    f = script.fields(jp)
    out = []
    for i in range(2, len(f)):
        if f[i - 2] == b'\rnameset':
            try:
                s = f[i].decode('cp932')
            except UnicodeDecodeError:
                continue
            if s in NAMES:
                out.append((i, s))
    return out


def text(name: str, lang: str) -> str:
    t = NAMES[name]
    t = t[lang] if isinstance(t, dict) else t
    assert len(t) <= MAX_CHARS and all(0xFF01 <= ord(c) <= 0xFF5E for c in t), t
    return t


def update_pack(path: Path, rel: str, jp: bytes, lang: str):
    """Adds/replaces the entries of the suggested names in one pack file (made for the script `jp`)."""
    if path.exists():
        raw = path.read_text(encoding='utf-8')
        doc = json.loads(raw)
    else:
        raw, doc = '', {'file': rel, 'lines': []}
    lines = {e['i']: e for e in doc['lines']}
    f = script.fields(jp)
    found = defaults(jp)
    if not found:
        raise SystemExit(f'{rel}: no suggested name found')
    for i, name in found:
        e = {'i': i, 'src': script.fingerprint(f[i]), 't': text(name, lang)}
        old = lines.get(i)
        if old and old['src'] != e['src']:
            raise SystemExit(f'{path}: entry {i} is made for another field')
        lines[i] = e
    doc['lines'] = [lines[i] for i in sorted(lines)]
    out = json.dumps(doc, ensure_ascii=False, indent=1) + '\n'
    if out != raw:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out, encoding='utf-8')
    return [(i, name, text(name, lang)) for i, name in found], out != raw


def main():
    from m9.config import Config
    from m9.dump import Dump
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('langs', nargs='+')
    ap.add_argument('--game', help='the game dump (default: the m9 configuration)')
    ap.add_argument('--update', help='its 1.3.0 update (default: the m9 configuration)')
    a = ap.parse_args()
    cfg = Config()
    d = Dump(a.game or cfg.game, a.update or cfg.update)
    if d.version != '1.3':
        raise SystemExit('needs the game WITH its 1.3.0 update (the 1.0 variants are taken from the base game)')
    for lang in a.langs:
        pack = REPO / 'langs' / lang / 'script'
        for rel in FILES:
            jp13, jp10 = d.read(rel), d.read_base(rel)
            stem = pack / rel[:-len('.spt')]
            done, changed = update_pack(stem.with_name(stem.name + '.json'), rel, jp13, lang)
            v10 = stem.with_name(stem.name + '.v10.json')
            note = ''
            if jp10 != jp13:
                if not v10.exists():
                    raise SystemExit(f'{rel}: the update changed it but the pack has no {v10.name}')
                d10, c10 = update_pack(v10, rel, jp10, lang)
                changed |= c10
                note = ' + 1.0 ' + ', '.join(str(i) for i, _, _ in d10)
            print(f'{lang} {rel}: ' + ', '.join(f'{i} {n} -> {t}' for i, n, t in done) + note +
                  ('' if changed else ' (already)'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
