#!/usr/bin/env python3
"""save_names.py - put a language pack's names into an existing save: the party Medals' default names (Oct 2026).

A save keeps six name strings (user1.b, 0x12-byte slots from 0x01): S8 the player, S9 the player's Medal, S10-S13
the four party members' Medals. The game copies them in and out of the save as they are (no check; the file's
CRC-16 is the only thing it verifies), so a game started with an older build keeps the Japanese default names
ラピス / サンゴ / タイタニア / ギンセイ, and the dialogues that show S10-S13 keep showing them. The party Medals'
records in the save (5 records of 0xA4 bytes at 0x574; the name at +9; scenario index = u32 +0 & 7, 1-4 = S10-S13)
can hold the same Japanese name once the member has joined, and the game copies those names back into S10-S13
(REFLECT_MEDAL_NAME), so both are changed together.

It also translates the PLACE of the save summary («Lugar»: the global string S3, 0x40 bytes at 0x39E8, the name of
the map where the game was saved, from the map file's header): a save made before the map names were translated
(tools/gdn_area_names.py, 10-oct-2026) keeps showing it in Japanese until it is saved again.

This replaces, in S10-S13 and in the matching Medal records, every Japanese DEFAULT name (or a form an earlier pack
wrote for it: OLD_FORMS) by the form the pack writes in a new game (langs/<lang>/script/story/spt/member_p.json, terms expanded) and recomputes the CRC (CRC-16/ARC, init
0xFACE, over the whole file with its u16 at len-4 zeroed). A name the player typed is never touched: S8/S9, or a
party Medal renamed by the player, change only with an explicit --set SLOT=NAME (S9-S13 also rename the Medal record
that has the slot's current name). Without --write it only shows what it would do; with --write it first copies the
save folder to a backup folder (default ~/Medarot9-save-backups/<time>/).

The save folder is the one that holds user1.b: Azahar "sdmc/Nintendo 3DS/<id>/<id>/title/00040000/00174f00/data/
00000001" (Kabuto: 00174e00), or a Checkpoint backup folder. Close the game (or the emulator) before writing.

  python3 tools/save_names.py <save folder> --lang es [--write] [--set S9=Souen] [--backup DIR]
"""
import argparse
import shutil
import struct
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from m9 import script, terms  # noqa: E402
import m9.codec  # noqa: E402,F401  (registers 'sjis_es')

SIZE = 0x7230
SLOTS = {'S8': 0x01, 'S9': 0x13, 'S10': 0x25, 'S11': 0x37, 'S12': 0x49, 'S13': 0x5B}
SLOT_LEN = 0x12
MEDALS, MEDAL_LEN, MEDAL_NAME, NAME_LEN = 0x574, 0xA4, 9, 17      # 5 records; name field up to +0x19
MAX_NAME = 16                                                    # 8 full-width characters, as the keyboard allows
DEFAULTS = {'S10': 'ラピス', 'S11': 'サンゴ', 'S12': 'タイタニア', 'S13': 'ギンセイ'}   # set by member_p.spt
# forms that earlier versions of the packs wrote for a default (half-width: the keyboard cannot type them, so they
# can only come from a pack): replaced like the Japanese ones. サンゴ was 'Coral' up to v2026.10.11-5aee706.
OLD_FORMS = {'S11': ('Coral',)}
PLACE, PLACE_LEN = 0x39E8, 0x40                                  # S3, the save summary's place (map header name)


def crc16(data: bytes, init=0xFACE) -> int:
    c = init
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c


def crc_of(d: bytes) -> int:
    z = bytearray(d)
    struct.pack_into('<H', z, len(z) - 4, 0)
    return crc16(z)


def pack_names(lang: str) -> dict:
    """{slot: bytes} = what the pack's member_p.spt stores in S10-S13 for each Japanese default."""
    import json
    f = REPO / 'langs' / lang / 'script' / 'story' / 'spt' / 'member_p.json'
    lines = json.loads(f.read_text(encoding='utf-8'))['lines']
    expand = terms.expander(lang)
    out = {}
    for slot, jp in DEFAULTS.items():
        fp = script.fingerprint(jp.encode('cp932'))
        texts = {expand(e['t']) for e in lines if e['src'] == fp and 't' in e}
        if len(texts) != 1:
            raise SystemExit(f'{f}: no single translation of {jp} ({texts or "none"})')
        out[slot] = texts.pop().encode('sjis_es')
    return out


def place_names(lang: str) -> dict:
    """{fingerprint of a Japanese map name: translated name (bytes)}: langs/<lang>/save_places.json, written by
    tools/gdn_area_names.py from the names it puts in the map headers."""
    import json
    f = REPO / 'langs' / lang / 'save_places.json'
    if not f.exists():
        return {}
    return {fp: tr.encode('sjis_es') for fp, tr in json.loads(f.read_text(encoding='utf-8')).items()}


def slot(d: bytes, s: str) -> bytes:
    o = SLOTS[s]
    return bytes(d[o:o + SLOT_LEN]).split(b'\0')[0]


def medal(d: bytes, k: int):
    """(scenario index, in use, name) of Medal record k."""
    o = MEDALS + k * MEDAL_LEN
    return struct.unpack_from('<I', d, o)[0] & 7, d[o + 4] == 1, bytes(d[o + MEDAL_NAME:o + MEDAL_NAME + NAME_LEN]).split(b'\0')[0]


def show(b: bytes) -> str:
    return b.decode('sjis_es', 'replace') if b else '(empty)'


def plan(d: bytes, names: dict, sets: dict, places=None):
    """[(what, offset, field length, old, new)]"""
    out = []
    if places:
        old = bytes(d[PLACE:PLACE + PLACE_LEN]).split(b'\0')[0]
        new = places.get(script.fingerprint(old)) if old else None
        if new and new != old and len(new) < PLACE_LEN:
            out.append(('S3 place', PLACE, PLACE_LEN, old, new))
    for s in SLOTS:
        if s not in sets and s not in DEFAULTS:
            continue
        old = slot(d, s)
        jp = DEFAULTS[s].encode('cp932') if s in DEFAULTS else None
        defaults = {jp} | {o.encode('sjis_es') for o in OLD_FORMS.get(s, ())}
        new = sets.get(s) or names.get(s)
        if (s in sets or old in defaults) and new != old:
            out.append((s, SLOTS[s], SLOT_LEN, old, new))
        if s == 'S8':
            continue
        for k in range(5):        # the Medal record of that slot (scenario index 0 = S9 ... 4 = S13) with that name
            idx, used, name = medal(d, k)
            if idx == int(s[1:]) - 9 and name and name != new and (name in defaults or (s in sets and name == old)):
                out.append((f'Medal record {k} ({"in use" if used else "not in use"}) of {s}',
                            MEDALS + k * MEDAL_LEN + MEDAL_NAME, NAME_LEN, name, new))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('folder', help='the save folder that holds user1.b')
    ap.add_argument('--lang', required=True, help='language pack (langs/<lang>): es, en')
    ap.add_argument('--set', action='append', default=[], metavar='SLOT=NAME',
                    help='also set this slot (S8-S13) to NAME, even if the player typed its current name')
    ap.add_argument('--write', action='store_true', help='write the save (after a backup); otherwise only show')
    ap.add_argument('--backup', help='backup folder (default ~/Medarot9-save-backups/<time>)')
    a = ap.parse_args()
    folder = Path(a.folder).expanduser()
    f = folder / 'user1.b'
    d = bytearray(f.read_bytes())
    if len(d) != SIZE:
        raise SystemExit(f'{f}: {len(d)} bytes, not a Medarot 9 user1.b ({SIZE})')
    if struct.unpack_from('<H', d, len(d) - 4)[0] != crc_of(d):
        raise SystemExit(f'{f}: its checksum is already wrong (the game would reset this save): not touched')
    sets = {}
    for s in a.set:
        k, _, v = s.partition('=')
        k = k.strip().upper()
        if k not in SLOTS:
            raise SystemExit(f'--set {s}: the slot must be one of {", ".join(SLOTS)}')
        b = v.encode('sjis_es')
        if not 0 < len(b) <= MAX_NAME:
            raise SystemExit(f'--set {s}: a name takes 1 to {MAX_NAME} bytes (8 full-width characters)')
        sets[k] = b
    names = pack_names(a.lang)
    for s in SLOTS:
        print(f'  {s:3} {show(slot(d, s))}')
    print(f'  S3  {show(bytes(d[PLACE:PLACE + PLACE_LEN]).split(chr(0).encode())[0])} (place)')
    changes = plan(d, names, sets, place_names(a.lang))
    if not changes:
        print('nothing to change')
        return 0
    for what, o, n, old, new in changes:
        print(f'  {what}: {show(old)} -> {show(new)}')
    if not a.write:
        print('(dry run: add --write to change the save)')
        return 0
    bak = Path(a.backup).expanduser() if a.backup else \
        Path.home() / 'Medarot9-save-backups' / time.strftime('%Y%m%d-%H%M%S')
    if bak.exists() and any(bak.iterdir()):
        raise SystemExit(f'{bak} is not empty')
    shutil.copytree(folder, bak, dirs_exist_ok=True)
    if (bak / 'user1.b').read_bytes() != bytes(d):
        raise SystemExit(f'backup to {bak} failed')
    for _, o, n, _, new in changes:
        d[o:o + n] = new + b'\0' * (n - len(new))
    struct.pack_into('<H', d, len(d) - 4, crc_of(d))
    f.write_bytes(d)
    back = f.read_bytes()
    assert back == bytes(d) and struct.unpack_from('<H', back, len(back) - 4)[0] == crc_of(back)
    print(f'written {f} (backup in {bak})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
