#!/usr/bin/env python3
"""romfs.py - Reads files from the RomFS of the Japanese ROM (roms/*.3ds) by path, without extracting them.

texlib uses it as a last resort for the Japanese base of files that are not in archive/ (e.g. the battle models
battle/mdl/*.bcmdl or the floating icons story/mdl/e_f_*.bcmdl: the archive/rom_extract extraction only has the
573 map models).

  python tools/tex/romfs.py ls <prefijo>          list the paths starting with the prefix
  python tools/tex/romfs.py get <ruta> <salida>   copy a file out of the ROM
"""
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROM = REPO / 'roms' / 'Medarot 9 - Kuwagata Ver. (Japan).3ds'
_TABLE = None      # path -> (absolute offset, size)


def _dirs(buf):
    dirs = {}
    p = 0
    while p + 0x18 <= len(buf):
        parent, _sib, _child, _fchild, _h, nl = struct.unpack_from('<IIIIII', buf, p)
        name = buf[p + 0x18:p + 0x18 + nl].decode('utf-16-le', 'replace') if nl else ''
        dirs[p] = (parent, name)
        p += 0x18 + ((nl + 3) // 4) * 4
    return dirs


def _path(dirs, off):
    parts = []
    seen = set()
    while off in dirs and dirs[off][1] and off not in seen:
        seen.add(off)
        parts.append(dirs[off][1])
        off = dirs[off][0]
    return '/'.join(reversed(parts))


def table():
    """{path: (offset, size)} of every RomFS file (read once)."""
    global _TABLE
    if _TABLE is not None:
        return _TABLE
    if not ROM.exists():
        raise FileNotFoundError(f'cannot find the ROM {ROM}')
    with open(ROM, 'rb') as f:
        ncsd = f.read(0x200)
        part = struct.unpack_from('<I', ncsd, 0x120)[0] * 0x200
        f.seek(part)
        ncch = f.read(0x200)
        romfs = part + struct.unpack_from('<I', ncch, 0x1B0)[0] * 0x200
        f.seek(romfs)
        if f.read(4) != b'IVFC':
            raise ValueError('RomFS without IVFC header (encrypted ROM?)')
        l3 = romfs + 0x1000
        f.seek(l3)
        h = f.read(0x28)
        dmo, dms = struct.unpack_from('<II', h, 0x0c)
        fmo, fms = struct.unpack_from('<II', h, 0x1c)
        data = l3 + struct.unpack_from('<I', h, 0x24)[0]
        f.seek(l3 + dmo)
        dirs = _dirs(f.read(dms))
        f.seek(l3 + fmo)
        fbuf = f.read(fms)
    out = {}
    p = 0
    while p + 0x20 <= len(fbuf):
        parent, _sib, doff, dsize, _h, nl = struct.unpack_from('<IIQQII', fbuf, p)
        if nl:
            name = fbuf[p + 0x20:p + 0x20 + nl].decode('utf-16-le', 'replace')
            d = _path(dirs, parent)
            out[(d + '/' if d else '') + name] = (data + doff, dsize)
        p += 0x20 + ((nl + 3) // 4) * 4
    _TABLE = out
    return out


def exists(rel):
    try:
        return rel in table()
    except FileNotFoundError:
        return False


def read(rel):
    off, size = table()[rel] if rel in table() else (None, None)
    if off is None:
        raise FileNotFoundError(f'{rel} is not in the RomFS')
    with open(ROM, 'rb') as f:
        f.seek(off)
        return f.read(size)


def listdir(prefix):
    return sorted(r for r in table() if r.startswith(prefix))


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'ls':
        for r in listdir(sys.argv[2]):
            print(r, table()[r][1])
    elif len(sys.argv) >= 4 and sys.argv[1] == 'get':
        Path(sys.argv[3]).write_bytes(read(sys.argv[2]))
        print('ok', sys.argv[3])
    else:
        print(__doc__)
