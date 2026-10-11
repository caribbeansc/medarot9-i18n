#!/usr/bin/env python3
"""luma_update_mount.py - code.bin fix: the 1.3.0 update's files go through a mount name Luma3DS redirects (Oct 2026).

The 1.3.0 program mounts the update's own RomFS (SelfNCCH, file path type 5 = update RomFS: FUN_0021cd84, called from
the boot init FUN_003d8288) under the name "prom:", next to the game's "rom:", and the file loader (FUN_001b2010)
tries "prom:<path>" before "rom:<path>". Luma3DS's LayeredFS only redirects to /luma/titles/<id>/romfs the paths that
start with "rom:" or with the first update mount of its list that it finds in the program ("ro2:", "rom2:", "rex:",
"patch:", "ext:", each after a zero byte; Luma3DS sysmodules/loader/source/patcher.c and romfsredir.s). "prom:" is not
in the list, so on a console every file the update ships (all the data tables: part names and descriptions,
techniques, Medals...; and some battle and story scripts) was read untranslated from the update. Emulators are not
affected (Azahar layers the mod over both RomFS) and neither is a translated update .cia (no Luma involved).

The fix renames the mount and its two path formats "prom:" -> "rom2:" (same length; for the game the name is only the
key of its mount table, and the program has no other "rom2" nor "ro2:", which Luma would pick first). The 1.0
programs have no update mount: nothing to do there.

  python3 tools/luma_update_mount.py es en --kuwagata <kwg update .cia | code.bin> --kabuto <kbt update .cia | code.bin>
  (idempotent: the fix is stripped and applied again). tools/port_code.py and tools/port_v10.py strip it before
  porting and apply it to their output.
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OLD, NEW = b'prom:', b'rom2:'
TAILS = (b'%s%s\x00', b'\x00')          # the two path formats ("prom:%s%s") and the mount name itself ("prom:")
LUMA_FIRST = b'\x00ro2:'                # the one name Luma looks for before "rom2:"


class FixError(Exception):
    pass


def sites(jp: bytes):
    """File offsets of the update mount name in a Japanese program: [] (1.0) or the three sites (1.3.0)."""
    found, i = [], jp.find(OLD)
    while i >= 0:
        found.append(i)
        i = jp.find(OLD, i + 1)
    if not found:
        return []
    ok = [o for o in found if jp[o - 1] == 0 and jp[o + len(OLD):].startswith(TAILS)]
    fmt = sum(jp[o + len(OLD):].startswith(TAILS[0]) for o in ok)
    if ok != found or len(ok) != 3 or fmt != 2:
        raise FixError(f'unexpected "prom:" strings at {", ".join(hex(o) for o in found)}')
    if NEW[:4] in jp or LUMA_FIRST in jp:
        raise FixError('the program already has "rom2" or "ro2:"')
    return found


def strip(jp: bytes, out: bytes) -> bytes:
    """The translated program without the fix (the Japanese name back at the sites)."""
    o = bytearray(out)
    for s in sites(jp):
        o[s:s + len(OLD)] = jp[s:s + len(OLD)]
    return bytes(o)


def apply(jp: bytes, out: bytes) -> bytes:
    """out (the translated program, without the fix) + the fix; checks the sites still hold the Japanese name."""
    o = bytearray(out)
    for s in sites(jp):
        if o[s:s + len(OLD)] != OLD:
            raise FixError(f'the translated program changed the mount name at {s + 0x100000:#x}')
        o[s:s + len(NEW)] = NEW
    return bytes(o)


def main():
    sys.path.insert(0, str(REPO))
    from m9 import patch
    from m9.dump import Source
    ap = argparse.ArgumentParser()
    ap.add_argument('langs', nargs='+')
    ap.add_argument('--kuwagata', required=True, help='Kuwagata 1.3.0 update (.cia) or its decompressed code.bin')
    ap.add_argument('--kabuto', help='Kabuto 1.3.0 update (.cia) or its decompressed code.bin')
    a = ap.parse_args()

    def program(path):
        return Path(path).read_bytes() if path.endswith('.bin') else Source(path).code()

    progs = {'code.bin.json': program(a.kuwagata)}
    if a.kabuto:
        progs['code.bin.kabuto.json'] = program(a.kabuto)
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
            print(f'{lang} {name}: update mount "rom2:" at ' + ', '.join(f'{s + 0x100000:#x}' for s in sites(jp)))


if __name__ == '__main__':
    main()
