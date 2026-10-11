#!/usr/bin/env python3
"""font_es.py - Adds á é í ó ú ü ñ Á É Í Ó Ú Ü Ñ ¿ ¡ to the BCFNT fonts of the game (Oct 2026).

The fonts are Japanese (Shift-JIS) and only carry ASCII. 16 half-width katakana (one byte, 0xC0-0xCF, which the game
does not use in any text; see python/sjis_es.py, which also patches the engine so that it draws them) are REDRAWN
with the Spanish letters, composed in each font from its own base letter and its own accent glyphs
(´ 0x814C, ¨ 0x814E, ~ 0x7E); ¿ and ¡ are ? and ! rotated 180°. The widths (CWDH) are copied from the base letter.
The DIALOGUE uses font14 (checked on the test bench by replacing the Q of each font with its number).

  CHARMAP (python/sjis_es.py): Spanish character -> SJIS code that represents it in the game.

  python3 tools/font_es.py build <romfs_out>       writes the patched fonts to <romfs_out>/<font>.bcfnt
  python3 tools/font_es.py preview <png>           test sheet: the Spanish alphabet in each patched font
"""
import struct
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'tex'))
import ctpk_tool as C  # noqa: E402

REPO = HERE.parent
sys.path.insert(0, str(REPO / 'python'))
from sjis_es import CHARMAP  # noqa: E402  (Spanish character -> game byte)
# character -> (base letter, diacritic)
COMPOSE = {'á': ('a', 'acute'), 'é': ('e', 'acute'), 'í': ('i', 'acute'), 'ó': ('o', 'acute'), 'ú': ('u', 'acute'),
           'ü': ('u', 'diaer'), 'ñ': ('n', 'tilde'),
           'Á': ('A', 'acute'), 'É': ('E', 'acute'), 'Í': ('I', 'acute'), 'Ó': ('O', 'acute'), 'Ú': ('U', 'acute'),
           'Ü': ('U', 'diaer'), 'Ñ': ('N', 'tilde'), '¿': ('?', 'rot'), '¡': ('!', 'rot')}
MARK_CODE = {'acute': 0x814C, 'diaer': 0x814E, 'tilde': 0x7E}
FONTS = ['font16.bcfnt', 'font14.bcfnt', 'font12.bcfnt', 'font12new.bcfnt', 'fotfont12.bcfnt', 'fotfont10.bcfnt',
         'font10.bcfnt']


SOURCE = None          # m9.dump.Dump of the player: when set, the Japanese fonts come from it


def _jp_font(name: str) -> bytes:
    if SOURCE is not None:
        return SOURCE.read(name)
    for base in (REPO / 'archive' / 'update_extract' / 'romfs', REPO / 'archive' / 'rom_extract'):
        if (base / name).exists():
            return (base / name).read_bytes()
    import romfs                                   # tools/tex/romfs.py: reads from the Japanese ROM
    return romfs.read(name)


class Font:
    def __init__(self, data: bytes):
        self.data = bytearray(data)
        assert data[:4] == b'CFNT', data[:4]
        p = struct.unpack_from('<H', data, 6)[0]                 # FINF
        assert data[p:p + 4] == b'FINF'
        self.enc = data[p + 15]
        ptgl, pcwdh, pcmap = struct.unpack_from('<III', data, p + 16)
        t = ptgl - 8
        assert data[t:t + 4] == b'TGLP'
        self.cellw, self.cellh, self.baseline, self.maxcw = data[t + 8], data[t + 9], data[t + 10], data[t + 11]
        (self.ssize, self.nsheets, self.fmt, self.cols, self.rows, self.sw, self.sh,
         self.doff) = struct.unpack_from('<IHHHHHHI', data, t + 12)
        # CWDH: [ini, fin] -> offset of the entry (left s8, glyph u8, char u8) in the file
        self.wpos = {}
        q = pcwdh - 8
        while q:
            assert data[q:q + 4] == b'CWDH'
            ini, fin, nxt = struct.unpack_from('<HHI', data, q + 8)
            for gi in range(ini, fin + 1):
                self.wpos[gi] = q + 16 + 3 * (gi - ini)
            q = nxt - 8 if nxt else 0
        self.cmap = {}
        q = pcmap - 8
        while q:
            assert data[q:q + 4] == b'CMAP'
            cs, ce, method, _r, nxt = struct.unpack_from('<HHHHI', data, q + 8)
            d = q + 20
            if method == 0:
                off = struct.unpack_from('<H', data, d)[0]
                for c in range(cs, ce + 1):
                    self.cmap[c] = off + c - cs
            elif method == 1:
                for k, c in enumerate(range(cs, ce + 1)):
                    gi = struct.unpack_from('<H', data, d + 2 * k)[0]
                    if gi != 0xFFFF:
                        self.cmap[c] = gi
            else:
                n = struct.unpack_from('<H', data, d)[0]
                for k in range(n):
                    c, gi = struct.unpack_from('<HH', data, d + 2 + 4 * k)
                    self.cmap[c] = gi
            q = nxt - 8 if nxt else 0
        self.sheets = {}
        self.dirty = set()

    def code(self, ch):
        """Font code for a character (1-character string or int)."""
        if isinstance(ch, int):
            return ch
        return int.from_bytes(ch.encode('cp932'), 'big') if self.enc == 2 else ord(ch)

    def sheet(self, i):
        if i not in self.sheets:
            o = self.doff + i * self.ssize
            self.sheets[i] = C.decode_tex(self.fmt, self.sw, self.sh, bytes(self.data[o:o + self.ssize])).convert('RGBA')
        return self.sheets[i]

    def _loc(self, code):
        gi = self.cmap[code]
        per = self.cols * self.rows
        s, k = divmod(gi, per)
        return gi, s, (k % self.cols) * (self.cellw + 1), (k // self.cols) * (self.cellh + 1)

    def cell(self, ch):
        gi, s, x, y = self._loc(self.code(ch))
        return self.sheet(s).crop((x, y, x + self.cellw, y + self.cellh))

    def set_cell(self, ch, img):
        gi, s, x, y = self._loc(self.code(ch))
        self.sheet(s).paste(img, (x, y))
        self.dirty.add(s)

    def width(self, ch):
        gi = self.cmap[self.code(ch)]
        o = self.wpos[gi]
        return struct.unpack_from('<bBB', self.data, o)

    def set_width(self, ch, w):
        gi = self.cmap[self.code(ch)]
        struct.pack_into('<bBB', self.data, self.wpos[gi], *w)

    def build(self) -> bytes:
        for s in sorted(self.dirty):
            o = self.doff + s * self.ssize
            enc = C.encode_image(self.sheets[s], self.fmt)
            assert len(enc) == self.ssize, (len(enc), self.ssize)
            self.data[o:o + self.ssize] = enc
        return bytes(self.data)


def _ink(img, thr=40):
    return img.getchannel('A').point(lambda v: 255 if v > thr else 0).getbbox()


def _paste_ink(dst, src, dx, dy):
    """Pastes into dst the ink pixels of src (RGBA) shifted by (dx, dy); keeps the more opaque one."""
    for y in range(src.height):
        for x in range(src.width):
            p = src.getpixel((x, y))
            if p[3] == 0:
                continue
            X, Y = x + dx, y + dy
            if 0 <= X < dst.width and 0 <= Y < dst.height and p[3] >= dst.getpixel((X, Y))[3]:
                dst.putpixel((X, Y), p)


# Diacritics drawn pixel by pixel for the fonts with an OUTLINE (font14, the dialogue one: white core with a 2 px
# black outline). The Japanese marks (full-width ´ ¨ ~) came out tiny and detached from the letter.
# '#' = core. Gap to the letter: 1 row (like the dot of the i of the font itself).
SHAPES = {'acute': ['.##', '##.'], 'diaer': None, 'tilde': ['.##.#', '#.##.']}


def _core(img):
    return {(x, y) for y in range(img.height) for x in range(img.width)
            if img.getpixel((x, y))[3] >= 200 and img.getpixel((x, y))[0] >= 100}


def _outline_alpha(d):
    """Outline of font14 as a function of the distance to the core (calibrated with its letters: d<=1.41 opaque, d=2
    almost opaque, d=2.24 faint)."""
    return 255 if d <= 1.5 else 204 if d <= 2.01 else 34 if d <= 2.3 else 0


def _components(pts):
    pts = set(pts); out = []
    while pts:
        stack = [pts.pop()]; comp = set(stack)
        while stack:
            x, y = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = (x + dx, y + dy)
                    if q in pts:
                        pts.discard(q); comp.add(q); stack.append(q)
        out.append(comp)
    return out


def compose_outlined(f: Font, ch: str):
    import math
    base, mark = COMPOSE[ch]
    src = f.cell(base)
    left, gw, cw = f.width(base)
    core = _core(src)
    keep = {(x, y): src.getpixel((x, y)) for (x, y) in core}
    if base == 'i':                                   # i without dot: drop everything above the x-height (the dot)
        # (The dot and the stem may touch through grey antialiasing pixels that _core counts, so they are not always
        # two components: until 10-oct-2026 the í of font14 kept its dot under the accent and looked "double".)
        xtop = min(y for _, y in _core(f.cell('n')))
        for q in [q for q in keep if q[1] < xtop]:
            keep.pop(q)
        core = set(keep)
    top = min(y for _, y in core)
    xs = [x for x, _ in core]
    x0, x1 = min(xs), max(xs)
    if mark == 'diaer':
        w = x1 - x0 + 1
        dot = 2 if w >= 6 else 1
        row = ['.'] * w
        for k in range(dot):
            row[k] = row[w - 1 - k] = '#'
        shape = [''.join(row)] * 2
    else:
        shape = SHAPES[mark]
    h, sw = len(shape), len(shape[0])
    bottom = top - 2                                  # 1 row of gap to the letter
    y0 = max(0, bottom - h + 1)
    ax = x0 if mark == 'diaer' else int(math.floor((x0 + x1 + 1) / 2.0 - sw / 2.0 + (0.5 if mark == 'acute' else 0)))
    acc = {(ax + i, y0 + j) for j, r in enumerate(shape) for i, c in enumerate(r) if c == '#'}
    allcore = set(keep) | acc
    out = Image.new('RGBA', src.size, (0, 0, 0, 0))
    regenerate = base == 'i'                          # the i is redone entirely (its outline surrounded the dot)
    for y in range(src.height):
        for x in range(src.width):
            if (x, y) in allcore:
                continue
            p = src.getpixel((x, y))
            a0 = 0 if regenerate else (p[3] if p[0] < 100 or p[3] < 200 else 0)
            near = allcore if regenerate else acc
            d = min(math.hypot(x - cx, y - cy) for cx, cy in near)
            a = max(a0, _outline_alpha(d))
            if a:
                out.putpixel((x, y), (0, 0, 0, a))
    for q, col in keep.items():
        out.putpixel(q, col)
    for q in acc:
        if 0 <= q[0] < src.width and 0 <= q[1] < src.height:
            out.putpixel(q, (255, 255, 255, 255))
    return out, (left, gw, cw)


# SMALL fonts (cell <= 15 px: font12, font12new, fotfont12, fotfont10, font10): the Japanese marks do not fit
# above the capitals (font12 leaves only 1 free row). Pixel diacritics: ´ 2x2, ~ 4x2, ¨ 1 row; 1 row of gap if it
# fits, otherwise touching, and if even that fails, the capital loses repeated rows of its stroke (as pixel fonts
# do with accented capitals).
SMALL_SHAPES = {'acute': ['.#', '#.'], 'tilde': ['.#.#', '#.#.']}


def _squash(img, need, top, bot):
    """Removes `need` rows from the letter (between top and bot) moving the upper part down: first rows EQUAL to a
    neighbor (vertical strokes), far from the ends. -> (image, new top)."""
    w = img.width
    rows = {y: tuple(img.getpixel((x, y)) for x in range(w)) for y in range(top, bot + 1)}
    cands = [y for y in range(top + 1, bot) if rows[y] == rows[y - 1] or rows[y] == rows.get(y + 1)]
    mid = (top + bot) / 2.0
    cands.sort(key=lambda y: abs(y - mid))
    drop = set()
    for y in cands:
        if len(drop) == need:
            break
        if (y - 1) not in drop and (y + 1) not in drop:
            drop.add(y)
    for y in sorted(range(top + 1, bot), key=lambda y: abs(y - mid)):     # if still short, any interior row
        if len(drop) == need:
            break
        drop.add(y)
    kept = [rows[y] for y in range(top, bot + 1) if y not in drop]
    out = img.copy()
    for y in range(0, bot + 1):
        for x in range(w):
            out.putpixel((x, y), (0, 0, 0, 0))
    y0 = bot - len(kept) + 1
    for k, r in enumerate(kept):
        for x in range(w):
            out.putpixel((x, y0 + k), r[x])
    return out, y0


def compose_small(f: Font, ch: str):
    import math
    base, mark = COMPOSE[ch]
    img = f.cell(base).copy()
    left, gw, cw = f.width(base)
    xtop = _ink(f.cell('x'))[1]
    if base == 'i':                                   # i without dot
        for y in range(0, xtop):
            for x in range(img.width):
                img.putpixel((x, y), (0, 0, 0, 0))
    bb = _ink(img)
    x0, top, x1, bot = bb[0], bb[1], bb[2] - 1, bb[3] - 1
    if mark == 'diaer':
        w = x1 - x0 + 1
        shape = ['#' + '.' * max(1, w - 2) + '#']
    else:
        shape = SMALL_SHAPES[mark]
    h, sw = len(shape), len(shape[0])
    gap = 1 if top - 1 - h >= 0 else 0               # 1 row of air if it fits
    if top - gap - h < 0:                             # not even touching: squash the letter
        img, top = _squash(img, h - top, top, bot)
    y0 = top - gap - h
    ax = x0 if mark == 'diaer' else int(math.floor((x0 + x1 + 1) / 2.0 - sw / 2.0 + (0.5 if mark == 'acute' else 0)))
    for j, r in enumerate(shape):
        for i, c in enumerate(r):
            if c == '#' and 0 <= ax + i < img.width and 0 <= y0 + j < img.height:
                img.putpixel((ax + i, y0 + j), (255, 255, 255, 255))
    nb = _ink(img)
    gw2 = max(gw, nb[2] - max(left, 0)) if nb else gw
    return img, (left, min(gw2, f.cellw), cw)


def compose(f: Font, ch: str):
    base, mark = COMPOSE[ch]
    if f.fmt == 0x4 and mark != 'rot':               # RGBA4 with outline (font14)
        return compose_outlined(f, ch)
    if f.cellh <= 15 and mark != 'rot':               # small fonts
        return compose_small(f, ch)
    img = f.cell(base).copy()
    bb = _ink(img)
    left, gw, cw = f.width(base)
    if mark == 'rot':
        x0, y0, x1, y1 = bb
        part = img.crop(bb).rotate(180)
        out = Image.new('RGBA', img.size, (0, 0, 0, 0))
        out.paste(part, (x0, y0))
        return out, (left, gw, cw)
    xtop = _ink(f.cell('x'))[1]
    captop = _ink(f.cell('E'))[1]
    if base == 'i':                                   # i without dot: erase whatever is above the height of the x
        for y in range(0, xtop):
            for x in range(img.width):
                img.putpixel((x, y), (0, 0, 0, 0))
        bb = _ink(img)
    mimg = f.cell(MARK_CODE[mark])
    mb = _ink(mimg)
    acc = mimg.crop(mb)
    upper = base.isupper()
    # bottom row of the accent: 1 px of air on lowercase; on capitals touching the letter and, in the fonts with an
    # OUTLINE (color formats, e.g. font14 RGBA4), merging its edge with the top edge of the letter
    # (otherwise it does not fit: the Ü lost its dots)
    outlined = f.fmt not in (0x8, 0xA, 0xB)
    bottom = (captop if outlined else captop - 1) if upper else (xtop - 2)
    top = bottom - acc.height + 1
    if top < 0:                                       # does not fit: keep the bottom rows of the accent
        acc = acc.crop((0, -top, acc.width, acc.height))
        top = 0
    cx = (bb[0] + bb[2]) / 2.0
    dx = int(round(cx - acc.width / 2.0 + (0.5 if mark == 'acute' else 0)))
    dx = max(0, min(img.width - acc.width, dx))
    _paste_ink(img, acc, dx, top)
    nb = _ink(img)
    gw2 = max(gw, nb[2] - max(left, 0)) if nb else gw
    return img, (left, min(gw2, f.cellw), cw)


def patch_font(name: str) -> bytes:
    f = Font(_jp_font(name))
    for ch, code in CHARMAP.items():
        if code not in f.cmap:
            raise KeyError(f'{name}: no glyph for 0x{code:02X}')
        img, w = compose(f, ch)
        f.set_cell(code, img)
        f.set_width(code, w)
    return f.build()


def build(romfs_out: Path):
    out = {}
    for name in FONTS:
        data = patch_font(name)
        (Path(romfs_out) / name).write_bytes(data)
        out[name] = len(data)
    return out


def preview(png: Path, text='¿Qué pasó? ¡Año, señor! ÁÉÍÓÚ áéíóú üÜ ñÑ'):
    rows = []
    for name in FONTS:
        f = Font(patch_font(name))
        x = 2
        canvas = Image.new('RGBA', (900, f.cellh + 4), (30, 34, 52, 255))
        for ch in text:
            code = CHARMAP.get(ch)
            code = code if code is not None else f.code(ch)
            if code not in f.cmap:
                continue
            gi, s, sx, sy = f._loc(code)
            left, gw, cw = struct.unpack_from('<bBB', f.data, f.wpos[gi])
            cell = f.sheet(s).crop((sx, sy, sx + f.cellw, sy + f.cellh))
            white = Image.new('RGBA', cell.size, (255, 255, 255, 255))
            layer = Image.new('RGBA', cell.size, (0, 0, 0, 0))
            layer.paste(white if f.fmt in (8, 0xA, 0xB) else cell, (0, 0), cell.getchannel('A'))
            canvas.alpha_composite(layer, (x + left, 2))
            x += cw
        rows.append(canvas.resize((canvas.width * 2, canvas.height * 2), Image.NEAREST))
    sheet = Image.new('RGBA', (rows[0].width, sum(r.height for r in rows)), (0, 0, 0, 255))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(png)
    return png


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'build':
        print(build(Path(sys.argv[2])))
    elif len(sys.argv) >= 3 and sys.argv[1] == 'preview':
        print(preview(Path(sys.argv[2])))
    else:
        print(__doc__)
