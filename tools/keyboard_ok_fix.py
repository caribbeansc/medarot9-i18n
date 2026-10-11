#!/usr/bin/env python3
"""keyboard_ok_fix.py - code.bin fix: the name keyboard accepts names made of half-width letters (Oct 2026).

The keyboard (mdr/spt/keypad.spt: player name, Medal names, rotation names) only enables OK when
`ifnospace <name> <space>` is true. That command (Kuwagata 1.3.0: FUN_0013de84) scans the name and is true as soon as
it finds a DOUBLE-BYTE character other than the given space; every one-byte character is skipped. So a name made of
half-width letters counts as blank and cannot be confirmed: the keyboard opens with it, OK stays disabled, and the
player has to type a full-width character first. The Japanese game never meets one (its defaults are full-width and
the keyboard only types full-width characters), but the translation does: the packs name the party Medals in
half-width ("Lapis", member_p.spt -> tinpet_get.spt -> the Medal record) and the Medal table too ("Kabuto", the
default name the keyboard gets when a new Medal is named in medal_get2.spt / medal_get_nadl.spt); renaming one of
them opened the keyboard with OK disabled. Verified on the bench (experiments/partida_nombres/INFORME.md).

The fix: inside the scan loop, a one-byte character above the ASCII space (0x21-0x80; and 0xA0-0xDF / 0xFD-0xFF:
half-width kana, the packs' Spanish letters 0xC0-0xCF) now counts as a character too. Names with full-width
characters behave as before, and spaces/control bytes still do not count. The loop's first instructions recompute
the current byte in seven redundant steps; they become the new test (no code cave):

    +04  cmp r0,#0x20 / bls NEXT     space or control byte: not a character
    +0C  cmp r0,#0x81 / blo FOUND    one-byte character (ASCII): the name is not blank
    +14  and r2,r0,#0xff / nop / nop (r2 = the byte, as before)
    +34  bhi NEXT -> bhi FOUND       one-byte character of the upper half (was skipped)

FOUND (+0x68) is the function's own exit for "found a character", NEXT (+0x140) its "next byte". The loop is found by
its bytes, the same in the four programs (Kuwagata/Kabuto, 1.0/1.3.0; 1.3.0 0x13DFFC, 1.0 0x13DE08).

  python3 tools/keyboard_ok_fix.py es en --kuwagata <kwg update .cia | code.bin> --kuwagata10 <kwg game .3ds/.cia>
          --kabuto <kbt update .cia> --kabuto10 <kbt game .cci/.cia>      # rewrites langs/<lang>/binary/exefs/*
  (idempotent: the fix is stripped and applied again). tools/port_code.py and tools/port_v10.py strip it before
  porting and apply it to their output.
"""
import argparse
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = 0x100000
# the scan loop of ifnospace: ldrb r1,[r4,#1] ... cmp r1,#0x7f / beq NEXT
LOOP = bytes.fromhex('0110d4e5ff20c0e3ff0000e2002082e10134a0e1ff3c03e2032082e1ff2002e2810052e34500003a'
                     '9f0050e3e00040821c0050834100008a400041e2bc0050e33e00008a7f0051e33c00000a')
FOUND, NEXT = 0x68, 0x140
FOUND_CODE = bytes.fromhex('000095e50110a0e36890c0e5')     # ldr r0,[r5] / mov r1,#1 / strb sb,[r0,#0x68]
NOP = 0xE320F000
LS, LO, HI = 0x9, 0x3, 0x8


class FixError(Exception):
    pass


def _b(src, dst, cond):
    return (cond << 28) | 0x0A000000 | (((dst - (src + 8)) >> 2) & 0xFFFFFF)


def site(jp: bytes) -> int:
    """File offset of the scan loop in a Japanese program."""
    i = jp.find(LOOP)
    if i < 0 or jp.find(LOOP, i + 1) >= 0:
        raise FixError('the ifnospace scan loop is not in the program exactly once')
    if jp[i + FOUND:i + FOUND + len(FOUND_CODE)] != FOUND_CODE:
        raise FixError(f'unexpected code at {BASE + i + FOUND:#x}')
    return i


def _fixed(i: int) -> bytes:
    va = BASE + i
    w = [0xE3500020, _b(va + 0x08, va + NEXT, LS), 0xE3500081, _b(va + 0x10, va + FOUND, LO), 0xE20020FF, NOP, NOP]
    loop = bytearray(LOOP)
    struct.pack_into('<7I', loop, 4, *w)
    struct.pack_into('<I', loop, 0x34, _b(va + 0x34, va + FOUND, HI))
    return bytes(loop)


def strip(jp: bytes, out: bytes) -> bytes:
    """The translated program without the fix (the Japanese loop back)."""
    i = site(jp)
    o = bytearray(out)
    o[i:i + len(LOOP)] = LOOP
    return bytes(o)


def apply(jp: bytes, out: bytes) -> bytes:
    """out (the translated program, without the fix) + the fix; checks the loop still holds the Japanese bytes."""
    i = site(jp)
    if out[i:i + len(LOOP)] != LOOP:
        raise FixError(f'the translated program changed the loop at {BASE + i:#x}')
    o = bytearray(out)
    o[i:i + len(LOOP)] = _fixed(i)
    return bytes(o)


def main():
    sys.path.insert(0, str(REPO))
    from m9 import patch
    from m9.dump import Source
    ap = argparse.ArgumentParser()
    ap.add_argument('langs', nargs='+')
    ap.add_argument('--kuwagata', required=True, help='Kuwagata 1.3.0 update (.cia) or its decompressed code.bin')
    ap.add_argument('--kuwagata10', help='Kuwagata game (.3ds / .cia) or its decompressed code.bin')
    ap.add_argument('--kabuto', help='Kabuto 1.3.0 update (.cia) or its decompressed code.bin')
    ap.add_argument('--kabuto10', help='Kabuto game (.cci / .cia) or its decompressed code.bin')
    a = ap.parse_args()

    def program(path):
        return Path(path).read_bytes() if path.endswith('.bin') else Source(path).code()

    progs = {'code.bin.json': program(a.kuwagata)}
    for name, path in (('code.bin.v10.json', a.kuwagata10), ('code.bin.kabuto.json', a.kabuto),
                       ('code.bin.kabuto.v10.json', a.kabuto10)):
        if path:
            progs[name] = program(path)
    for lang in a.langs:
        for name, jp in progs.items():
            f = REPO / 'langs' / lang / 'binary' / 'exefs' / name
            p = patch.load(f)
            if p['src'] != patch.sha1(jp):
                raise SystemExit(f'{f}: made for another code.bin')
            new = apply(jp, strip(jp, patch.apply(p, jp)))
            q = patch.make('exefs/code.bin', jp, new)
            q = {k: q.get(k, p[k]) for k in p}           # the pack's keys (edition, game), in its order
            patch.save(q, f)
            print(f'{lang} {name}: keyboard OK fix at {BASE + site(jp):#x}')


if __name__ == '__main__':
    main()
