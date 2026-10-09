#!/usr/bin/env python3
"""
ctpk_tool.py - Read/write CTPK textures (PICA200, 3DS) to translate the game images.

  decode(ctpk_bytes)            -> [Tex(name, fmt, w, h, PIL.Image RGBA)]
  encode_image(img, fmt)        -> texture bytes in the PICA format (8x8 Morton tiles, origin at the top)
  replace(ctpk_bytes, {i: img}) -> new CTPK: SAME format, size and header; only the pixels change
  roundtrip_image(ctpk_bytes, img, i=0) -> how img will look in the game (encoded and decoded)

Formatos: RGBA8, RGB8, RGBA5551, RGB565, RGBA4, LA8, L8, A8, LA4, L4, A4, ETC1, ETC1A4
(ETC1 is compressed with etcpak and reordered to the 3DS layout: 4x4 blocks in Z order inside 8x8 tiles,
64 bits little-endian). In ETC the 4x4 blocks that did not change are copied byte for byte from the original
(etcpak's recompression would degrade the whole texture) and, in ETC1A4, the RGB of the invisible pixels
is filled with the neighboring color before compressing (cleaner text edges).

CLI: python tools/ctpk_tool.py decode in.ctpk outprefix   |   roundtrip in.ctpk
"""
import struct
import sys
from dataclasses import dataclass

from PIL import Image

FMT_NAMES = {0: 'RGBA8', 1: 'RGB8', 2: 'RGBA5551', 3: 'RGB565', 4: 'RGBA4', 5: 'LA8', 6: 'HILO8',
             7: 'L8', 8: 'A8', 9: 'LA4', 0xA: 'L4', 0xB: 'A4', 0xC: 'ETC1', 0xD: 'ETC1A4'}
BPP = {0: 32, 1: 24, 2: 16, 3: 16, 4: 16, 5: 16, 6: 16, 7: 8, 8: 8, 9: 8, 0xA: 4, 0xB: 4, 0xC: 4, 0xD: 8}
MORTON = []
for _i in range(64):
    MORTON.append(((_i & 1) | ((_i >> 1) & 2) | ((_i >> 2) & 4),
                   ((_i >> 1) & 1) | ((_i >> 2) & 2) | ((_i >> 3) & 4)))
ETC_ORDER = ((0, 0), (4, 0), (0, 4), (4, 4))


@dataclass
class Tex:
    index: int
    name: str
    fmt: int
    w: int
    h: int
    data_off: int      # absolute offset of the data in the CTPK
    size: int
    img: Image.Image


def _entries(d: bytes):
    assert d[:4] == b'CTPK', 'not a CTPK'
    n = struct.unpack_from('<H', d, 6)[0]
    texsec = struct.unpack_from('<I', d, 8)[0]
    out = []
    for i in range(n):
        e = 0x20 + i * 0x20
        noff, size, doff, fmt = struct.unpack_from('<IIII', d, e)
        w, h = struct.unpack_from('<HH', d, e + 0x10)
        name = d[noff:d.index(b'\0', noff)].decode('ascii', 'replace')
        out.append((i, name, fmt, w, h, texsec + doff, size))
    return out


# ------------------------------------------------------------------------------------------- decode
def _px_decode(fmt, d, o):
    if fmt == 0:
        a, b, g, r = d[o:o + 4]; return (r, g, b, a)
    if fmt == 1:
        b, g, r = d[o:o + 3]; return (r, g, b, 255)
    v = d[o] | (d[o + 1] << 8) if fmt in (2, 3, 4) else 0
    if fmt == 2:
        return (((v >> 11) & 31) * 255 // 31, ((v >> 6) & 31) * 255 // 31, ((v >> 1) & 31) * 255 // 31, 255 if v & 1 else 0)
    if fmt == 3:
        return (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31, 255)
    if fmt == 4:
        return (((v >> 12) & 15) * 17, ((v >> 8) & 15) * 17, ((v >> 4) & 15) * 17, (v & 15) * 17)
    if fmt == 5:
        a, l = d[o:o + 2]; return (l, l, l, a)
    if fmt == 6:
        g, r = d[o:o + 2]; return (r, g, 0, 255)
    if fmt == 7:
        l = d[o]; return (l, l, l, 255)
    if fmt == 8:
        return (255, 255, 255, d[o])
    if fmt == 9:
        v = d[o]; l = (v >> 4) * 17; return (l, l, l, (v & 15) * 17)
    raise ValueError(fmt)


def decode_tex(fmt, w, h, d) -> Image.Image:
    if fmt in (0xC, 0xD):
        import texture2ddecoder as t2d
        bs = 16 if fmt == 0xD else 8
        nbx, nby = w // 4, h // 4
        lin = bytearray(nbx * nby * 8)
        alpha = {}
        p = 0
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                for bx, by in ETC_ORDER:
                    blk = d[p:p + bs]; p += bs
                    gx, gy = (tx + bx) // 4, (ty + by) // 4
                    if gx >= nbx or gy >= nby:
                        continue
                    etc = blk[8:] if fmt == 0xD else blk
                    if fmt == 0xD:
                        alpha[(gx, gy)] = blk[:8]
                    q = (gy * nbx + gx) * 8
                    lin[q:q + 8] = etc[::-1]
        img = Image.frombytes('RGBA', (w, h), t2d.decode_etc1(bytes(lin), w, h), 'raw', 'BGRA')
        if fmt == 0xD:
            a = Image.new('L', (w, h)); ap = a.load()
            for (gx, gy), ab in alpha.items():
                v = int.from_bytes(ab, 'little')
                for i in range(16):
                    ap[gx * 4 + i // 4, gy * 4 + i % 4] = ((v >> (i * 4)) & 15) * 17
            img.putalpha(a)
        return img
    img = Image.new('RGBA', (w, h)); pix = img.load()
    p = 0
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for i in range(64):
                x, y = MORTON[i]
                if fmt in (0xA, 0xB):
                    v = d[p // 2]
                    nib = (v >> 4) if (p % 2) else (v & 15)
                    p += 1
                    c = (nib * 17,) * 3 + (255,) if fmt == 0xA else (255, 255, 255, nib * 17)
                else:
                    c = _px_decode(fmt, d, p); p += BPP[fmt] // 8
                if tx + x < w and ty + y < h:
                    pix[tx + x, ty + y] = c
    return img


def decode(ctpk: bytes):
    out = []
    for i, name, fmt, w, h, off, size in _entries(ctpk):
        out.append(Tex(i, name, fmt, w, h, off, size, decode_tex(fmt, w, h, ctpk[off:off + size])))
    return out


# ------------------------------------------------------------------------------------------- encode
def _q(v, bits):
    return (v * ((1 << bits) - 1) + 127) // 255


def _px_encode(fmt, c):
    r, g, b, a = c
    if fmt == 0:
        return bytes((a, b, g, r))
    if fmt == 1:
        return bytes((b, g, r))
    if fmt == 2:
        v = (_q(r, 5) << 11) | (_q(g, 5) << 6) | (_q(b, 5) << 1) | (1 if a >= 128 else 0); return struct.pack('<H', v)
    if fmt == 3:
        v = (_q(r, 5) << 11) | (_q(g, 6) << 5) | _q(b, 5); return struct.pack('<H', v)
    if fmt == 4:
        v = (_q(r, 4) << 12) | (_q(g, 4) << 8) | (_q(b, 4) << 4) | _q(a, 4); return struct.pack('<H', v)
    lum = (r * 299 + g * 587 + b * 114 + 500) // 1000
    if fmt == 5:
        return bytes((a, lum))
    if fmt == 6:
        return bytes((g, r))
    if fmt == 7:
        return bytes((lum,))
    if fmt == 8:
        return bytes((a,))
    if fmt == 9:
        return bytes(((_q(lum, 4) << 4) | _q(a, 4),))
    raise ValueError(fmt)


# ------------------------------------------------------------------------------------------- ETC1 propio
# etcpak is fast but poor on blocks with text (white/black): gray smudges. For the blocks that change this
# encoder is tried too (table search with refinement, weighted by alpha) and the one with the lower error is kept.
ETC1_TABLES = ((2, 8, -2, -8), (5, 17, -5, -17), (9, 29, -9, -29), (13, 42, -13, -42),
          (18, 60, -18, -60), (24, 80, -24, -80), (33, 106, -33, -106), (47, 183, -47, -183))


def _cl(v):
    return 0 if v < 0 else 255 if v > 255 else v


def _sub_err(pix, w, base, t):
    """Minimum error (and assignment) of a sub-block with base color (8 bits) and table t."""
    mods = ETC1_TABLES[t]
    tot = 0.0
    idx = []
    br, bg, bb = base
    cand = [(_cl(br + m), _cl(bg + m), _cl(bb + m)) for m in mods]
    for (r, g, b), wi in zip(pix, w):
        best = None
        bk = 0
        for k, (cr, cg, cb) in enumerate(cand):
            e = (cr - r) ** 2 + (cg - g) ** 2 + (cb - b) ** 2
            if best is None or e < best:
                best, bk = e, k
        tot += wi * best
        idx.append(bk)
    return tot, idx


def _expand(q, bits):
    return (q << 4) | q if bits == 4 else (q << 3) | (q >> 2)


def _quant_cands(v, bits):
    mx = (1 << bits) - 1
    f = v * mx / 255.0
    lo = max(0, min(mx, int(f)))
    hi = max(0, min(mx, lo + 1))
    return sorted({lo, hi})


def _best_sub(pix, w, bits, tables):
    """Best (err, base_q, t) of a sub-block for the given precision (4 = individual, 5 = differential)."""
    sw = sum(w)
    out = []
    if sw <= 0:
        return [(0.0, (0, 0, 0), 0)]
    mean = [sum(p[c] * wi for p, wi in zip(pix, w)) / sw for c in range(3)]
    for t in tables:
        mods = ETC1_TABLES[t]
        B = list(mean)
        for _ in range(3):
            acc = [0.0, 0.0, 0.0]
            for (r, g, b), wi in zip(pix, w):
                best = None; bm = 0
                for m in mods:
                    e = (_cl(B[0] + m) - r) ** 2 + (_cl(B[1] + m) - g) ** 2 + (_cl(B[2] + m) - b) ** 2
                    if best is None or e < best:
                        best, bm = e, m
                acc[0] += wi * (r - bm); acc[1] += wi * (g - bm); acc[2] += wi * (b - bm)
            B = [min(255.0, max(0.0, a / sw)) for a in acc]
        for qr in _quant_cands(B[0], bits):
            for qg in _quant_cands(B[1], bits):
                for qb in _quant_cands(B[2], bits):
                    base = (_expand(qr, bits), _expand(qg, bits), _expand(qb, bits))
                    e, _ = _sub_err(pix, w, base, t)
                    out.append((e, (qr, qg, qb), t))
    out.sort(key=lambda x: x[0])
    return out


def _tables_for(pix, w):
    vals = [(p[0] + p[1] + p[2]) / 3 for p, wi in zip(pix, w) if wi > 0]
    if not vals:
        return [0]
    spread = max(vals) - min(vals)
    ts = [t for t in range(8) if ETC1_TABLES[t][1] * 2 >= spread * 0.45 and ETC1_TABLES[t][1] <= spread * 1.3 + 8]
    return ts or [7 if spread > 200 else 0]


def etc1_encode_block(px16, weights=None):
    """px16: 16 tuples (r,g,b[,a]) in y*4+x order. weights: 16 weights (e.g. alpha/255). -> 8 bytes ETC1 big-endian."""
    if weights is None:
        weights = [1.0] * 16
    best = None
    for flip in (0, 1):
        if flip == 0:
            s1 = [(x, y) for x in (0, 1) for y in range(4)]
            s2 = [(x, y) for x in (2, 3) for y in range(4)]
        else:
            s1 = [(x, y) for y in (0, 1) for x in range(4)]
            s2 = [(x, y) for y in (2, 3) for x in range(4)]
        subs = []
        for S in (s1, s2):
            pix = [tuple(px16[y * 4 + x][:3]) for x, y in S]
            w = [weights[y * 4 + x] for x, y in S]
            subs.append((S, pix, w, _tables_for(pix, w)))
        # individual mode (4 bits)
        r1 = _best_sub(subs[0][1], subs[0][2], 4, subs[0][3])[0]
        r2 = _best_sub(subs[1][1], subs[1][2], 4, subs[1][3])[0]
        cand = [(r1[0] + r2[0], 0, flip, r1, r2)]
        # differential mode (5 bits + delta)
        c1 = _best_sub(subs[0][1], subs[0][2], 5, subs[0][3])[:6]
        c2 = _best_sub(subs[1][1], subs[1][2], 5, subs[1][3])[:6]
        found = None
        for a in c1:
            for b in c2:
                if all(-4 <= b[1][k] - a[1][k] <= 3 for k in range(3)):
                    if found is None or a[0] + b[0] < found[0]:
                        found = (a[0] + b[0], a, b)
        if found is None:
            a = c1[0]
            qb = tuple(min(a[1][k] + 3, max(a[1][k] - 4, c2[0][1][k])) for k in range(3))
            qb = tuple(max(0, min(31, v)) for v in qb)
            base = tuple(_expand(v, 5) for v in qb)
            bt = min(((_sub_err(subs[1][1], subs[1][2], base, t)[0], t) for t in range(8)))
            found = (a[0] + bt[0], a, (bt[0], qb, bt[1]))
        cand.append((found[0], 1, flip, found[1], found[2]))
        for cnd in cand:
            if best is None or cnd[0] < best[0]:
                best = cnd + (subs,)
    err, diff, flip, a, b, subs = best
    # pack
    if diff:
        d = [b[1][k] - a[1][k] for k in range(3)]
        hi = ((a[1][0] << 3 | (d[0] & 7)) << 16) | ((a[1][1] << 3 | (d[1] & 7)) << 8) | (a[1][2] << 3 | (d[2] & 7))
    else:
        hi = ((a[1][0] << 4 | b[1][0]) << 16) | ((a[1][1] << 4 | b[1][1]) << 8) | (a[1][2] << 4 | b[1][2])
    word = (hi << 8) | (a[2] << 5) | (b[2] << 2) | (diff << 1) | flip
    msb = lsb = 0
    for si, (S, pix, w, _) in enumerate(subs):
        q = a if si == 0 else b
        bits = 5 if diff else 4
        base = tuple(_expand(v, bits) for v in q[1])
        _, idx = _sub_err(pix, [1.0] * len(pix), base, q[2])
        for (x, y), k in zip(S, idx):
            pi = x * 4 + y
            msb |= ((k >> 1) & 1) << pi
            lsb |= (k & 1) << pi
    val = (word << 32) | (msb << 16) | lsb
    return val.to_bytes(8, 'big'), err


def etc1_decode_block(blk):
    """8 ETC1 big-endian bytes -> 16 RGB tuples (y*4+x order)."""
    v = int.from_bytes(blk, 'big')
    word, msb, lsb = v >> 32, (v >> 16) & 0xFFFF, v & 0xFFFF
    diff, flip = (word >> 1) & 1, word & 1
    t1, t2 = (word >> 5) & 7, (word >> 2) & 7
    R, G, B = (word >> 24) & 0xFF, (word >> 16) & 0xFF, (word >> 8) & 0xFF
    if diff:
        def sx(d):
            return d - 8 if d >= 4 else d
        q1 = (R >> 3, G >> 3, B >> 3)
        q2 = (q1[0] + sx(R & 7), q1[1] + sx(G & 7), q1[2] + sx(B & 7))
        c1 = [(c << 3) | (c >> 2) for c in q1]
        c2 = [((c & 31) << 3) | ((c & 31) >> 2) for c in q2]
    else:
        c1 = [(x >> 4) << 4 | (x >> 4) for x in (R, G, B)]
        c2 = [(x & 15) << 4 | (x & 15) for x in (R, G, B)]
    out = [None] * 16
    for x in range(4):
        for y in range(4):
            pi = x * 4 + y
            k = (((msb >> pi) & 1) << 1) | ((lsb >> pi) & 1)
            second = (y >= 2) if flip else (x >= 2)
            base, t = (c2, t2) if second else (c1, t1)
            m = ETC1_TABLES[t][k]
            out[y * 4 + x] = tuple(_cl(c + m) for c in base)
    return out


def _etc1_err(px16, w, rgb16):
    return sum(wi * ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) for a, b, wi in zip(px16, rgb16, w))


def _bleed_rgb(img: Image.Image) -> Image.Image:
    """Copy of img whose TRANSPARENT pixels (alpha 0) take the color of the nearby visible ones.
    In ETC1A4 the alpha is separate: the RGB of an invisible pixel is free, but ETC1 compresses the 16 pixels of
    the block together; if the invisible ones are black (0,0,0,0) they dirty the color of the text edges.
    Pull-push on premultiplied RGB (BOX pyramid + BILINEAR upsampling)."""
    w, h = img.size
    pm = img.convert('RGBa')
    levels = [pm]
    cur = pm
    while cur.size[0] > 1 or cur.size[1] > 1:
        cur = cur.resize((max(1, (cur.size[0] + 1) // 2), max(1, (cur.size[1] + 1) // 2)), Image.BOX)
        levels.append(cur)
    acc = levels[-1].convert('RGBA')
    for lv in reversed(levels[:-1]):
        up = acc.resize(lv.size, Image.BILINEAR)
        here = lv.convert('RGBA')
        # where this level has coverage, its color (un-premultiplied); otherwise the one above
        mask = here.getchannel('A').point(lambda a: 255 if a > 0 else 0)
        up.paste(here, (0, 0), mask)
        acc = up
    out = acc.copy()
    out.putalpha(0)
    out.paste(img, (0, 0), img.getchannel('A').point(lambda a: 255 if a > 0 else 0))
    out.putalpha(img.getchannel('A'))
    return out


def encode_image(img: Image.Image, fmt: int, ref=None) -> bytes:
    """Encodes img in the PICA format fmt. ref=(decoded_original_img, original_bytes): in ETC1/ETC1A4 the 4x4
    blocks whose pixels did NOT change are copied as they are from the original (no recompression loss)."""
    img = img.convert('RGBA')
    w, h = img.size
    if fmt in (0xC, 0xD):
        import etcpak
        src = _bleed_rgb(img) if fmt == 0xD else img
        rgba = src.tobytes()
        etc = etcpak.compress_etc1_rgb(rgba, w, h)          # linear 4x4 blocks, 8 bytes each
        nbx = w // 4
        pix = img.load()
        bs = 16 if fmt == 0xD else 8
        rpix = ref[0].convert('RGBA').load() if ref is not None else None
        rdata = ref[1] if ref is not None else None
        out = bytearray()
        p = 0
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                for bx, by in ETC_ORDER:
                    gx, gy = (tx + bx) // 4, (ty + by) // 4
                    if rpix is not None:
                        same = all(pix[gx * 4 + i // 4, gy * 4 + i % 4] == rpix[gx * 4 + i // 4, gy * 4 + i % 4]
                                   for i in range(16))
                        if same:
                            out += rdata[p:p + bs]
                            p += bs
                            continue
                    p += bs
                    q = (gy * nbx + gx) * 8
                    blk = etc[q:q + 8]
                    px16 = [pix[gx * 4 + i % 4, gy * 4 + i // 4] for i in range(16)]
                    w16 = [c[3] / 255.0 for c in px16] if fmt == 0xD else [1.0] * 16
                    if sum(w16) > 0:
                        e_pak = _etc1_err(px16, w16, etc1_decode_block(blk))
                        if e_pak > 24 * sum(w16):            # mean error > ~3 levels per channel: try our own
                            mine, e_mine = etc1_encode_block(px16, w16)
                            if e_mine < e_pak:
                                blk = mine
                    if fmt == 0xD:
                        v = 0
                        for i in range(16):
                            a = pix[gx * 4 + i // 4, gy * 4 + i % 4][3]
                            v |= _q(a, 4) << (i * 4)
                        out += v.to_bytes(8, 'little')
                    out += blk[::-1] if ETC1_BYTES_REVERSED else blk
        return bytes(out)
    pix = img.load()
    out = bytearray()
    nib = []
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for i in range(64):
                x, y = MORTON[i]
                c = pix[tx + x, ty + y] if (tx + x < w and ty + y < h) else (0, 0, 0, 0)
                if fmt in (0xA, 0xB):
                    r, g, b, a = c
                    lum = (r * 299 + g * 587 + b * 114 + 500) // 1000
                    nib.append(_q(lum if fmt == 0xA else a, 4))
                    if len(nib) == 2:
                        out.append(nib[0] | (nib[1] << 4)); nib = []
                else:
                    out += _px_encode(fmt, c)
    return bytes(out)


ETC1_BYTES_REVERSED = True     # etcpak emits the big-endian bitstream; the 3DS stores it little-endian


def replace(ctpk: bytes, images: dict) -> bytes:
    """New CTPK with the textures {index: image} re-encoded in THEIR format (same size)."""
    out = bytearray(ctpk)
    for i, name, fmt, w, h, off, size in _entries(ctpk):
        if i not in images:
            continue
        img = images[i]
        if img.size != (w, h):
            raise ValueError(f'{name}: size {img.size} != {(w, h)}')
        ref = None
        if fmt in (0xC, 0xD):              # ETC: keep the blocks that did not change intact
            orig = bytes(ctpk[off:off + size])
            ref = (decode_tex(fmt, w, h, orig), orig)
        data = encode_image(img, fmt, ref)
        if len(data) != size:
            raise ValueError(f'{name}: {len(data)} bytes encoded != {size}')
        out[off:off + size] = data
    return bytes(out)


def roundtrip_image(ctpk: bytes, img: Image.Image, index: int = 0) -> Image.Image:
    """Image as it will look in the game: img encoded in the format of texture index and decoded."""
    for i, name, fmt, w, h, off, size in _entries(ctpk):
        if i == index:
            new = replace(ctpk, {i: img})
            return decode_tex(fmt, w, h, new[off:off + size])
    raise IndexError(index)


def _psnr(a: Image.Image, b: Image.Image):
    import math
    pa, pb = a.convert('RGBA').tobytes(), b.convert('RGBA').tobytes()
    se = sum((x - y) ** 2 for x, y in zip(pa, pb)) / len(pa)
    return 99.0 if se == 0 else 10 * math.log10(255 * 255 / se)


if __name__ == '__main__':
    cmd, src = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()
    if cmd == 'decode':
        for t in decode(d):
            t.img.save(f'{sys.argv[3]}_{t.index}.png')
            print(t.name, FMT_NAMES[t.fmt], t.w, t.h)
    elif cmd == 'roundtrip':
        texs = decode(d)
        new = replace(d, {t.index: t.img for t in texs})
        back = decode(new)
        for t, b in zip(texs, back):
            print(f'{t.name} {FMT_NAMES[t.fmt]} {t.w}x{t.h} bytes_equal={new[t.data_off:t.data_off + t.size] == d[t.data_off:t.data_off + t.size]} '
                  f'PSNR={_psnr(t.img, b.img):.1f}dB')
