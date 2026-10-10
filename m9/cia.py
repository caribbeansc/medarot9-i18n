"""Installable translated copies: the game (or its update) rebuilt with the translated files inside.

For players who install a .cia with FBI instead of using Luma3DS game patching. Made from the player's own decrypted
dump, like everything else; nothing of the game is stored in this repository.

  - with the 1.3.0 update: a translated copy of the UPDATE (.cia). The game itself stays the original one: the update
    is where the game looks for its files first, so its new RomFS carries every translated file, and its ExeFS the
    translated code.bin.
  - without the update (1.0): a translated copy of the GAME, as a .cia when the game was given as a .cia, or as a
    .3ds when it was given as a .3ds/.cci (GodMode9 turns a .3ds into a .cia on the console: "NCSD image options >
    Build CIA from file").

The copies are decrypted ("NoCrypto") and their signatures are not Nintendo's: a console with custom firmware
(Luma3DS) installs them; emulators too.

Formats (3dbrew.org): RomFS = IVFC hash tree (levels 1-2 of SHA-256 over 4 KiB blocks) over level 3 (directory and
file tables + data); ExeFS = 0x200 header (names, offsets, SHA-256 in reverse order) + files; NCCH = header +
extended header + logo + plain region + ExeFS + RomFS; CIA = header + certificates + ticket + TMD + contents + meta.
"""
import hashlib
import shutil
import struct
from pathlib import Path

MEDIA = 0x200
BLOCK = 0x1000
NONE = 0xFFFFFFFF


class CiaError(Exception):
    pass


def _align(n, a):
    return (n + a - 1) // a * a


def _sha(b):
    return hashlib.sha256(b).digest()


# --- RomFS ------------------------------------------------------------------------------------------------------

def _hash_count(n):
    if n < 3:
        return 3
    if n < 19:
        return n | 1
    while any(n % p == 0 for p in (2, 3, 5, 7, 11, 13, 17)):
        n += 1
    return n


def _name_hash(parent, name):
    h = (parent ^ 123456789) & 0xFFFFFFFF
    for i in range(0, len(name), 2):
        h = ((h >> 5) | (h << 27)) & 0xFFFFFFFF
        h ^= name[i] | name[i + 1] << 8
    return h


class RomFS:
    """Level 3 layout of a RomFS holding `sizes` ({path: size}); the data is read later through a callback."""

    def __init__(self, sizes):
        dirs = {'': {'name': b'', 'dirs': [], 'files': []}}
        for path in sorted(sizes):
            parts = path.split('/')
            cur = ''
            for p in parts[:-1]:
                nxt = f'{cur}/{p}' if cur else p
                if nxt not in dirs:
                    dirs[nxt] = {'name': p.encode('utf-16-le'), 'dirs': [], 'files': []}
                    dirs[cur]['dirs'].append(nxt)
                cur = nxt
            dirs[cur]['files'].append(path)
        order_d, order_f = [], []

        def walk(d):
            order_d.append(d)
            for c in sorted(dirs[d]['dirs']):
                walk(c)
        walk('')
        doff, off = {}, 0
        for d in order_d:
            doff[d] = off
            off += 0x18 + _align(len(dirs[d]['name']), 4)
        dmeta_size = off
        foff, off = {}, 0
        for d in order_d:
            for f in sorted(dirs[d]['files']):
                order_f.append(f)
                foff[f] = off
                off += 0x20 + _align(len(f.rsplit('/', 1)[-1].encode('utf-16-le')), 4)
        fmeta_size = off
        # file data: in table order, each aligned to 16
        data_off, pos = {}, 0
        for f in order_f:
            pos = _align(pos, 0x10)
            data_off[f] = pos
            pos += sizes[f]
        data_size = pos
        dh_n, fh_n = _hash_count(len(order_d)), _hash_count(len(order_f))
        dhash, fhash = [NONE] * dh_n, [NONE] * fh_n
        dmeta, fmeta = bytearray(dmeta_size), bytearray(fmeta_size)
        for d in order_d:
            info = dirs[d]
            parent = d.rsplit('/', 1)[0] if '/' in d else ''
            p_off = doff[parent] if d else 0
            sib = NONE
            if d:
                kids = sorted(dirs[parent]['dirs'])
                k = kids.index(d)
                sib = doff[kids[k + 1]] if k + 1 < len(kids) else NONE
            kids = sorted(info['dirs'])
            files = sorted(info['files'])
            b = _name_hash(p_off, info['name']) % dh_n
            struct.pack_into('<IIIIII', dmeta, doff[d], p_off, sib, doff[kids[0]] if kids else NONE,
                             foff[files[0]] if files else NONE, dhash[b], len(info['name']))
            dmeta[doff[d] + 0x18:doff[d] + 0x18 + len(info['name'])] = info['name']
            dhash[b] = doff[d]
            for k, f in enumerate(files):
                name = f.rsplit('/', 1)[-1].encode('utf-16-le')
                fb = _name_hash(doff[d], name) % fh_n
                struct.pack_into('<IIQQII', fmeta, foff[f], doff[d], foff[files[k + 1]] if k + 1 < len(files) else NONE,
                                 data_off[f], sizes[f], fhash[fb], len(name))
                fmeta[foff[f] + 0x20:foff[f] + 0x20 + len(name)] = name
                fhash[fb] = foff[f]
        dh = struct.pack(f'<{dh_n}I', *dhash)
        fh = struct.pack(f'<{fh_n}I', *fhash)
        o_dh = 0x28
        o_dm = o_dh + len(dh)
        o_fh = o_dm + len(dmeta)
        o_fm = o_fh + len(fh)
        o_data = _align(o_fm + len(fmeta), 0x10)
        head = struct.pack('<10I', 0x28, o_dh, len(dh), o_dm, len(dmeta), o_fh, len(fh), o_fm, len(fmeta), o_data)
        self.meta = (head + dh + bytes(dmeta) + fh + bytes(fmeta)).ljust(o_data, b'\0')
        self.order = order_f
        self.data_off = {f: o_data + data_off[f] for f in order_f}
        self.sizes = sizes
        self.l3_size = o_data + data_size
        # IVFC sizes
        n3 = -(-self.l3_size // BLOCK)
        self.l2_size = 32 * n3
        n2 = -(-self.l2_size // BLOCK)
        self.l1_size = 32 * n2
        n1 = -(-self.l1_size // BLOCK)
        self.master_size = 32 * n1
        self.l3_phys = _align(0x60 + self.master_size, BLOCK)
        self.l1_phys = _align(self.l3_phys + self.l3_size, BLOCK)
        self.l2_phys = _align(self.l1_phys + self.l1_size, BLOCK)
        self.size = _align(self.l2_phys + self.l2_size, BLOCK)
        self.hash_region = _align(0x60 + self.master_size, MEDIA) // MEDIA

    def write(self, out, start, read):
        """Writes the RomFS at `start` of the open file `out`; `read(path)` gives each file. Returns the SHA-256
        of its hash region (IVFC header + master hash), for the NCCH header."""
        l2 = bytearray()
        buf = bytearray()
        out.seek(start + self.l3_phys)

        def emit(b):
            nonlocal buf
            out.write(b)
            buf += b
            while len(buf) >= BLOCK:
                l2.extend(_sha(bytes(buf[:BLOCK])))
                del buf[:BLOCK]
        emit(self.meta)
        pos = len(self.meta)
        for f in self.order:
            o = self.data_off[f]
            if o > pos:
                emit(b'\0' * (o - pos))
                pos = o
            data = read(f)
            if len(data) != self.sizes[f]:
                raise CiaError(f'{f}: size changed while writing')
            emit(data)
            pos += len(data)
        if buf:
            l2.extend(_sha(bytes(buf) + b'\0' * (BLOCK - len(buf))))
        l2 = bytes(l2)
        l1 = b''.join(_sha(l2[i:i + BLOCK].ljust(BLOCK, b'\0')) for i in range(0, len(l2), BLOCK))
        master = b''.join(_sha(l1[i:i + BLOCK].ljust(BLOCK, b'\0')) for i in range(0, len(l1), BLOCK))
        out.seek(start + self.l1_phys)
        out.write(l1)
        out.seek(start + self.l2_phys)
        out.write(l2)
        out.seek(start + self.size - 1)
        out.write(b'\0')
        l2_log = _align(self.l1_size, BLOCK)
        l3_log = _align(l2_log + self.l2_size, BLOCK)
        ivfc = struct.pack('<4sII', b'IVFC', 0x10000, self.master_size)
        ivfc += struct.pack('<QQII', 0, self.l1_size, 12, 0)
        ivfc += struct.pack('<QQII', l2_log, self.l2_size, 12, 0)
        ivfc += struct.pack('<QQII', l3_log, self.l3_size, 12, 0)
        ivfc += struct.pack('<II', 0x5C, 0)
        region = (ivfc.ljust(0x60, b'\0') + master).ljust(self.hash_region * MEDIA, b'\0')
        out.seek(start)
        out.write(region)
        return _sha(region)


# --- ExeFS / NCCH -----------------------------------------------------------------------------------------------

def exefs(files):
    """ExeFS image of [(name, bytes)]."""
    head = bytearray(0x200)
    body = bytearray()
    for i, (name, data) in enumerate(files):
        head[i * 16:i * 16 + 8] = name.encode('ascii').ljust(8, b'\0')
        struct.pack_into('<II', head, i * 16 + 8, len(body), len(data))
        head[0x200 - 0x20 * (i + 1):0x200 - 0x20 * i] = _sha(data)
        body += data + b'\0' * (_align(len(data), MEDIA) - len(data))
    return bytes(head + body)


def _exefs_files(ncch):
    off, _ = ncch.exefs
    ncch.f.seek(off)
    hdr = ncch.f.read(0x200)
    out = []
    for i in range(10):
        name, o, s = struct.unpack_from('<8sII', hdr, i * 16)
        if name[0]:
            ncch.f.seek(off + 0x200 + o)
            out.append((name.rstrip(b'\0').decode('ascii'), ncch.f.read(s)))
    return out


def write_ncch(out, start, src, code: bytes, files: dict, read):
    """Writes at `start` a copy of the NCCH `src` (m9.dump._Ncch) whose ExeFS .code is `code` (decompressed) and whose
    RomFS holds `files` ({path: size}, data through `read`). Returns the content size."""
    src.f.seek(src.base)
    head = bytearray(src.f.read(0x200))
    exefs_off = struct.unpack_from('<I', head, 0x1A0)[0] * MEDIA
    src.f.seek(src.base)
    pre = bytearray(src.f.read(exefs_off))                     # header, extended header, logo, plain region
    pre[0x200 + 0xD] &= ~1                                     # the code is stored decompressed
    ex = exefs([('.code', code) if n == '.code' else (n, d) for n, d in _exefs_files(src)])
    romfs_off = _align(exefs_off + len(ex), BLOCK)
    rf = RomFS(files)
    out.seek(start + exefs_off)
    out.write(ex)
    romfs_hash = rf.write(out, start + romfs_off, read)
    size = romfs_off + rf.size
    h = pre
    struct.pack_into('<I', h, 0x104, size // MEDIA)
    h[0x160:0x180] = _sha(bytes(pre[0x200:0x600]))
    struct.pack_into('<II', h, 0x1A4, len(ex) // MEDIA, 1)
    struct.pack_into('<III', h, 0x1B0, romfs_off // MEDIA, rf.size // MEDIA, rf.hash_region)
    h[0x1C0:0x1E0] = _sha(ex[:0x200])
    h[0x1E0:0x200] = romfs_hash
    h[0x188 + 7] = (h[0x188 + 7] | 0x04) & ~0x01             # NoCrypto, no fixed key
    out.seek(start)
    out.write(bytes(h))
    return size


def _hash_region(f, start, size):
    h = hashlib.sha256()
    f.seek(start)
    left = size
    while left:
        b = f.read(min(left, 1 << 22))
        h.update(b)
        left -= len(b)
    return h.digest()


def _copy(src, s_off, dst, size):
    src.seek(s_off)
    left = size
    while left:
        b = src.read(min(left, 1 << 22))
        dst.write(b)
        left -= len(b)


# --- CIA / CCI --------------------------------------------------------------------------------------------------

def write_cia(src_path, src_ncch, out_path, code, files, read, log=print):
    """A copy of the .cia at `src_path` whose first content (the program, `src_ncch`) has the translated code and
    RomFS. The other contents (e-manual, ...), the certificates, the ticket and the meta block are kept."""
    with open(src_path, 'rb') as s:
        hsize, ctype, ver, cert, tik, tmd, meta, csize = struct.unpack_from('<IHHIIIIQ', s.read(0x20))
        s.seek(0)
        header = bytearray(s.read(hsize))
        o_cert = _align(hsize, 64)
        o_tik = o_cert + _align(cert, 64)
        o_tmd = o_tik + _align(tik, 64)
        o_con = o_tmd + _align(tmd, 64)
        o_meta = o_con + _align(csize, 64)
        s.seek(o_cert)
        certs = s.read(cert)
        s.seek(o_tik)
        ticket = s.read(tik)
        s.seek(o_tmd)
        t = bytearray(s.read(tmd))
        s.seek(o_meta)
        meta_b = s.read(meta)
        sig = struct.unpack_from('>I', t, 0)[0]
        body = {0x10000: 0x240, 0x10001: 0x140, 0x10002: 0x80, 0x10003: 0x240, 0x10004: 0x140, 0x10005: 0x80}.get(sig)
        if body is None:
            raise CiaError('unknown TMD signature type')
        count = struct.unpack_from('>H', t, body + 0x9E)[0]
        chunks = body + 0xC4 + 64 * 0x24
        recs = []
        pos = o_con
        for i in range(count):
            cid, idx, typ, sz = struct.unpack_from('>IHHQ', t, chunks + i * 0x30)
            recs.append([cid, idx, typ, sz, pos])
            pos += _align(sz, 64)
        if src_ncch.base != recs[0][4]:
            raise CiaError('the program is not the first content of the .cia')
        with open(out_path, 'w+b') as out:
            o = _align(hsize, 64) + _align(cert, 64) + _align(tik, 64) + _align(tmd, 64)
            log('writing the program (translated code and files)...')
            new0 = write_ncch(out, o, src_ncch, code, files, read)
            h0 = _hash_region(out, o, new0)
            pos = o + _align(new0, 64)
            sizes = [new0]
            for cid, idx, typ, sz, spos in recs[1:]:
                out.seek(pos)
                _copy(s, spos, out, sz)
                pos += _align(sz, 64)
                sizes.append(sz)
            total = pos - o
            # TMD: content 0 size + hash, not encrypted; then the hash chain (chunk records -> info records -> header)
            struct.pack_into('>H', t, chunks + 0x6, recs[0][2] & ~1)
            struct.pack_into('>Q', t, chunks + 0x8, new0)
            t[chunks + 0x10:chunks + 0x30] = h0
            for i in range(1, count):
                struct.pack_into('>H', t, chunks + i * 0x30 + 6, recs[i][2] & ~1)
            info = body + 0xC4
            n_info = struct.unpack_from('>H', t, info + 2)[0] or count
            t[info + 4:info + 0x24] = _sha(bytes(t[chunks:chunks + 0x30 * n_info]))
            t[body + 0xA4:body + 0xC4] = _sha(bytes(t[info:info + 64 * 0x24]))
            struct.pack_into('<Q', header, 0x18, total)
            out.seek(0)
            out.write(bytes(header).ljust(_align(hsize, 64), b'\0'))
            out.write(certs.ljust(_align(cert, 64), b'\0'))
            out.write(ticket.ljust(_align(tik, 64), b'\0'))
            out.write(bytes(t).ljust(_align(tmd, 64), b'\0'))
            out.seek(o + _align(total, 64))
            out.write(meta_b)
            out.truncate()
    return out_path


def write_cci(src_path, src_ncch, out_path, code, files, read, log=print):
    """A copy of the .3ds/.cci at `src_path` whose first partition (the game) has the translated code and RomFS.
    The other partitions (e-manual, ...) follow it, unchanged; the image is not padded to the card size."""
    with open(src_path, 'rb') as s:
        head = bytearray(s.read(0x4000))
        parts = [struct.unpack_from('<II', head, 0x120 + 8 * i) for i in range(8)]
        p0 = parts[0][0] * MEDIA
        if src_ncch.base != p0:
            raise CiaError('the game is not the first partition of the .3ds')
        with open(out_path, 'w+b') as out:
            out.write(bytes(head[:p0]))
            log('writing the game (translated code and files)...')
            new0 = write_ncch(out, p0, src_ncch, code, files, read)
            pos = p0 + _align(new0, MEDIA)
            table = [(p0 // MEDIA, new0 // MEDIA)]
            for off, size in parts[1:]:
                if not size:
                    table.append((0, 0))
                    continue
                out.seek(pos)
                _copy(s, off * MEDIA, out, size * MEDIA)
                table.append((pos // MEDIA, size))
                pos += size * MEDIA
            for i, (off, size) in enumerate(table):
                struct.pack_into('<II', head, 0x120 + 8 * i, off, size)
            struct.pack_into('<I', head, 0x104, pos // MEDIA)
            if len(head) > 0x304:
                struct.pack_into('<I', head, 0x300, pos)       # card info: filled size
            out.seek(0)
            out.write(bytes(head[:p0]))
            out.seek(pos)
            out.truncate()
    return out_path


# --- the translated copies ----------------------------------------------------------------------------------------

def _romfs_files(src, mod_romfs: Path, every: bool):
    """{path: size} and a reader: the program's own files, the translated ones in their place; with every=True the
    translated files are added even where the program has none (the update's RomFS, read first by the game)."""
    sizes = {p: s for p, (_, s) in src._romfs.files.items()} if src._romfs else {}
    mine = {p.relative_to(mod_romfs).as_posix(): p for p in mod_romfs.rglob('*') if p.is_file()}
    for rel, p in mine.items():
        if every or rel in sizes:
            sizes[rel] = p.stat().st_size

    def read(rel):
        return mine[rel].read_bytes() if rel in mine else src.read(rel)
    return sizes, read


def make(dump, mod: Path, out_dir: Path, name: str, log=print):
    """The translated installable copy for this dump (see the module docstring). `mod` is the built mod
    (<title>/romfs, <title>/exefs/code.bin). Returns the written path."""
    code = (mod / 'exefs' / 'code.bin').read_bytes()
    out_dir.mkdir(parents=True, exist_ok=True)
    if dump.update is not None:
        src = dump.update
        if src._ncch is None or src._dir is not None:
            raise CiaError('to make a .cia of the update, choose the update\'s .cia file (not a folder)')
        if not str(src.path).lower().endswith('.cia'):
            raise CiaError('the update must be a .cia file')
        files, read = _romfs_files(src, mod / 'romfs', every=True)
        dst = out_dir / f'{name} (update 1.3.0).cia'
        log(f'{len(files)} files in the update ({sum(files.values()) // (1 << 20)} MB)')
        return write_cia(src.path, src._ncch, dst, code, files, read, log)
    src = dump.game
    if src._ncch is None or src._dir is not None:
        raise CiaError('to make an installable copy, choose the game\'s .cia or .3ds/.cci file (not a folder)')
    files, read = _romfs_files(src, mod / 'romfs', every=False)
    log(f'{len(files)} files in the game ({sum(files.values()) // (1 << 20)} MB): this takes a while')
    if str(src.path).lower().endswith('.cia'):
        return write_cia(src.path, src._ncch, out_dir / f'{name}.cia', code, files, read, log)
    return write_cci(src.path, src._ncch, out_dir / f'{name}.3ds', code, files, read, log)


def split_files(dump, mod: Path, out_dir: Path):
    """The translated files split by where they go when rebuilding the game's own containers by hand (PackHack /
    HackingToolkit3DS): update/exefs/code.bin + update/romfs/ (everything) with the 1.3.0 update; game/exefs/code.bin
    + game/romfs/ without it."""
    part = 'update' if dump.update is not None else 'game'
    dst = out_dir / part
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(mod / 'romfs', dst / 'romfs')
    (dst / 'exefs').mkdir(parents=True)
    shutil.copy2(mod / 'exefs' / 'code.bin', dst / 'exefs' / 'code.bin')
    return dst
