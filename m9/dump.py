"""Reading the game from the player's own dump.

Medarot 9 comes in two editions: Kuwagata (title 0004000000174F00, update 0004000E00174F00) and Kabuto
(0004000000174E00, update 0004000E00174E00). With the 1.3.0 update both have exactly the same files; only their code
(code.bin) differs. The tools need the Japanese files of the game and of its update. Accepted sources, for both:

  - a decrypted cartridge image (.3ds / .cci) or a decrypted .cia (game or update);
  - a folder: a dumped RomFS (with Azahar: right click the game -> Dump RomFS), optionally next to an
    `exefs/` folder holding `code.bin` (decompressed or not).

Encrypted images are refused with a clear message: decrypt them first with your own console (GodMode9) or tool.

A Dump answers `read(path)` with the file the game really loads: the update's copy when the update has it, the
base game's otherwise (the 1.3.0 update ships only the files it changes). `code()` returns the decompressed
code.bin of the newest program present.
"""
import struct
from pathlib import Path

MEDIA = 0x200


class DumpError(Exception):
    pass


# --- containers -------------------------------------------------------------------------------------------------

def _align(n, a):
    return (n + a - 1) // a * a


class _Ncch:
    """An NCCH partition inside a file (offset `base`)."""

    def __init__(self, f, base, label):
        self.f, self.base, self.label = f, base, label
        f.seek(base)
        h = f.read(0x200)
        if h[0x100:0x104] != b'NCCH':
            raise DumpError(f'{label}: this file is still ENCRYPTED (or is not a 3DS game). Decrypt it first, e.g. with '
                            f'GodMode9 on your console ("decrypt" on the .cia / cartridge dump), then choose the '
                            f'"-decrypted" file.')
        flags = h[0x188:0x190]
        self.encrypted = not (flags[7] & 0x04)
        self.title_id = struct.unpack_from('<Q', h, 0x118)[0]
        self.exh_size = struct.unpack_from('<I', h, 0x180)[0]
        self.exefs = (base + struct.unpack_from('<I', h, 0x1A0)[0] * MEDIA, struct.unpack_from('<I', h, 0x1A4)[0] * MEDIA)
        self.romfs = (base + struct.unpack_from('<I', h, 0x1B0)[0] * MEDIA, struct.unpack_from('<I', h, 0x1B4)[0] * MEDIA)
        if self.encrypted:
            raise DumpError(f'{label}: the image is ENCRYPTED. Decrypt it first (e.g. GodMode9 "decrypt" on your console).')

    def exheader(self) -> bytes:
        self.f.seek(self.base + 0x200)
        return self.f.read(0x800)

    def exefs_file(self, name: str) -> bytes:
        off, size = self.exefs
        if not size:
            raise DumpError(f'{self.label}: no ExeFS')
        self.f.seek(off)
        hdr = self.f.read(0x200)
        for i in range(10):
            n, o, s = struct.unpack_from('<8sII', hdr, i * 16)
            if n.rstrip(b'\0').decode('ascii', 'replace') == name:
                self.f.seek(off + 0x200 + o)
                return self.f.read(s)
        raise DumpError(f'{self.label}: ExeFS has no {name}')

    def code(self) -> bytes:
        raw = self.exefs_file('.code')
        compressed = self.exheader()[0xD] & 1
        return blz_decompress(raw) if compressed else raw


class _RomFs:
    """Files of a RomFS (IVFC) stored at `off` of an open file."""

    def __init__(self, f, off, label):
        self.f, self.label = f, label
        f.seek(off)
        h = f.read(0x60)
        if h[:4] != b'IVFC':
            raise DumpError(f'{label}: RomFS without IVFC header')
        master = struct.unpack_from('<I', h, 0x8)[0]
        l3_block = 1 << struct.unpack_from('<I', h, 0x4C)[0]
        l3 = off + _align(0x60 + master, l3_block)
        f.seek(l3)
        lh = f.read(0x28)
        dmo, dms = struct.unpack_from('<II', lh, 0x0C)
        fmo, fms = struct.unpack_from('<II', lh, 0x1C)
        data = l3 + struct.unpack_from('<I', lh, 0x24)[0]
        f.seek(l3 + dmo)
        dirs = self._dirs(f.read(dms))
        f.seek(l3 + fmo)
        fbuf = f.read(fms)
        self.files = {}
        p = 0
        while p + 0x20 <= len(fbuf):
            parent, _sib, doff, dsize, _h, nl = struct.unpack_from('<IIQQII', fbuf, p)
            if nl:
                name = fbuf[p + 0x20:p + 0x20 + nl].decode('utf-16-le', 'replace')
                d = self._path(dirs, parent)
                self.files[(d + '/' if d else '') + name] = (data + doff, dsize)
            p += 0x20 + _align(nl, 4)

    @staticmethod
    def _dirs(buf):
        dirs, p = {}, 0
        while p + 0x18 <= len(buf):
            parent, _s, _c, _fc, _h, nl = struct.unpack_from('<IIIIII', buf, p)
            dirs[p] = (parent, buf[p + 0x18:p + 0x18 + nl].decode('utf-16-le', 'replace') if nl else '')
            p += 0x18 + _align(nl, 4)
        return dirs

    @staticmethod
    def _path(dirs, off):
        parts, seen = [], set()
        while off in dirs and dirs[off][1] and off not in seen:
            seen.add(off)
            parts.append(dirs[off][1])
            off = dirs[off][0]
        return '/'.join(reversed(parts))

    def read(self, rel):
        off, size = self.files[rel]
        self.f.seek(off)
        return self.f.read(size)


def blz_decompress(data: bytes) -> bytes:
    """Decompress a 3DS .code (backward LZ77, "BLZ"): the footer gives the sizes; the stream is read from the end."""
    buf_top, off_bot = struct.unpack_from('<II', data, len(data) - 8)
    inc = struct.unpack_from('<I', data, len(data) - 4)[0]
    hdr_len = buf_top >> 24
    enc_len = buf_top & 0xFFFFFF
    out = bytearray(data) + bytearray(inc)
    src = len(data) - hdr_len
    dst = len(out)
    stop = len(data) - enc_len
    while src > stop:
        src -= 1
        flags = out[src]
        for _ in range(8):
            if src <= stop:
                break
            if flags & 0x80:
                src -= 2
                pair = out[src] | out[src + 1] << 8
                length = (pair >> 12) + 3
                disp = (pair & 0x0FFF) + 3
                for _ in range(length):
                    dst -= 1
                    out[dst] = out[dst + disp]
            else:
                src -= 1
                dst -= 1
                out[dst] = out[src]
            flags = (flags << 1) & 0xFF
    del off_bot
    return bytes(out)


# --- one source (a file or a folder) -----------------------------------------------------------------------------

class Source:
    """The Japanese files of one program (the base game or the update)."""

    def __init__(self, path):
        self.path = Path(path).expanduser()
        self.label = self.path.name
        self._f = None
        self._romfs = None
        self._ncch = None
        if self.path.is_dir():
            root = self.path / 'romfs' if (self.path / 'romfs').is_dir() else self.path
            self._dir = root
            code = next((p for p in (self.path / 'exefs' / 'code.bin', self.path / 'code.bin', self.path / '.code')
                         if p.is_file()), None)
            self._code_file = code
            self.title_id = None
            return
        self._dir = None
        self._f = open(self.path, 'rb')
        head = self._f.read(0x200)
        if head[0x100:0x104] == b'NCSD':                                   # .3ds / .cci
            part0 = struct.unpack_from('<I', head, 0x120)[0] * MEDIA
            self._ncch = _Ncch(self._f, part0, self.label)
        elif head[0x100:0x104] == b'NCCH':                                 # bare .cxi / .app
            self._ncch = _Ncch(self._f, 0, self.label)
        else:                                                              # .cia
            hsize, _t, _v, cert, tik, tmd = struct.unpack_from('<IHHIII', head, 0)
            if hsize != 0x2020:
                raise DumpError(f'{self.label}: not a .3ds, .cci, .cia or NCCH file')
            content = _align(hsize, 64) + _align(cert, 64) + _align(tik, 64) + _align(tmd, 64)
            self._ncch = _Ncch(self._f, content, self.label)
        self.title_id = self._ncch.title_id
        off, size = self._ncch.romfs
        self._romfs = _RomFs(self._f, off, self.label) if size else None

    def files(self):
        if self._dir is not None:
            return {p.relative_to(self._dir).as_posix() for p in self._dir.rglob('*') if p.is_file()}
        return set(self._romfs.files) if self._romfs else set()

    def has(self, rel):
        if self._dir is not None:
            return (self._dir / rel).is_file()
        return bool(self._romfs) and rel in self._romfs.files

    def read(self, rel):
        if self._dir is not None:
            return (self._dir / rel).read_bytes()
        return self._romfs.read(rel)

    def code(self):
        if self._dir is not None:
            if not self._code_file:
                return None
            raw = self._code_file.read_bytes()
            return raw if len(raw) > 0x300000 else blz_decompress(raw)
        return self._ncch.code() if self._ncch.exefs[1] else None


EDITIONS = {'kuwagata': (0x0004000000174F00, 0x0004000E00174F00, b'MDR9KWG'),
            'kabuto': (0x0004000000174E00, 0x0004000E00174E00, b'MDR9KBT')}


class Dump:
    """Base game + optional update: `read` gives the file the game really loads."""

    def __init__(self, game, update=None):
        self.game = Source(game)
        self.update = Source(update) if update else None
        self.edition = self._edition()

    def _edition(self):
        for src, k in ((self.game, 0), (self.update, 1)):
            if src and src.title_id:
                ed = next((e for e, ids in EDITIONS.items() if ids[k] == src.title_id), None)
                if ed is None:
                    raise DumpError(f'{src.label}: title {src.title_id:016X} is not Medarot 9 '
                                    f'({"game" if k == 0 else "update"} expected)')
                return self._check(ed)
        has_code = any(getattr(src, '_code_file', None) for src in (self.game, self.update) if src)
        code = self.code() if has_code else None
        if code:
            for ed, ids in EDITIONS.items():
                if ids[2] in code[:0x400]:
                    return self._check(ed)
        return 'kuwagata'

    def _check(self, ed):
        ids = EDITIONS[ed]
        for src, k in ((self.game, 0), (self.update, 1)):
            if src and src.title_id and src.title_id != ids[k]:
                raise DumpError(f'{src.label} is not the {"game" if k == 0 else "update"} of Medarot 9 {ed.title()} '
                                f'(the game and its update must be the same edition)')
        return ed

    @property
    def title(self) -> str:
        """Title ID of the base game: the folder name of its mod."""
        return f'{EDITIONS[self.edition][0]:016X}'

    @property
    def version(self):
        return '1.3' if self.update else '1.0'

    def has(self, rel):
        return (self.update and self.update.has(rel)) or self.game.has(rel)

    def read(self, rel):
        if self.update and self.update.has(rel):
            return self.update.read(rel)
        return self.game.read(rel)

    def read_base(self, rel):
        """The base game's copy (1.0), even when the update replaces it."""
        return self.game.read(rel)

    def files(self):
        return self.game.files() | (self.update.files() if self.update else set())

    def code(self):
        """Decompressed code.bin of the newest program (the update's when present)."""
        c = self.update.code() if self.update else None
        return c if c is not None else self.game.code()
