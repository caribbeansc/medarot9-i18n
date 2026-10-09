#!/usr/bin/env python3
"""cgfx_uv.py - Which part of a texture of a CGFX model (.bcmdl) is really visible, and with what stretching.

It reads the model (meshes -> shape -> triangles; material -> textures) and, for each mesh that uses the texture,
extracts the UV window of each face in texture pixels: x = u * width, y = (1 - v) * height (V is inverted: v = 0 is
the BOTTOM ROW). UVs outside [0, 1] wrap (the texture repeats): they are reduced to the equivalent window inside the
image. For each window it gives the UV -> 3D Jacobian: 3D length per texel along x (texture horizontal) and along y,
their ratio (1.0 = no distortion; 1.15 = the face looks 15 % wider than it is painted: it draws the letters
narrower) and how much each texture axis points to the world vertical (3D Y axis: +-1 = vertical, 0 = horizontal),
to know whether the sign is seen rotated.

Limits: only UV set 0 of the interleaved vertex buffers (the ones used by the signs); it applies neither the UV
scale nor the UV translation of the material, nor their animations (e.g. mdr/mdl/panel.bcmdl moves the window by
animation). Reader based on those of the wave-8 labelers (o8r1 cgfxmesh/uvcheck, o8r3 uvwin, o8r4 uvjac), without
numpy.

  python3 tools/tex/texlib.py uv <rel>:<texture> [--es] [--box x,y,w,h] [--scale N] [--out F]
"""
import math
import struct


class Model:
    """Minimal reader of a CGFX: models, textures, meshes, materials and shapes."""

    def __init__(self, data: bytes):
        self.d = data
        if data[:4] != b'CGFX':
            raise ValueError('not a CGFX file')
        self.dicts = {}
        for i in range(16):
            pos = 0x1C + i * 8
            c, o = struct.unpack_from('<II', data, pos)
            self.dicts[i] = (c, pos + 4 + o if c else None)

    def u32(self, p):
        return struct.unpack_from('<I', self.d, p)[0]

    def f32(self, p):
        return struct.unpack_from('<f', self.d, p)[0]

    def rel(self, p):
        return p + self.u32(p)

    def cstr(self, p):
        return self.d[p:self.d.index(b'\0', p)].decode('ascii', 'replace')

    def dict_entries(self, p):
        """[(name, data offset)] of a DICT."""
        n = self.u32(p + 8)
        out = []
        for i in range(1, n + 1):
            q = p + 12 + i * 16
            nm, do = self.u32(q + 8), self.u32(q + 12)
            out.append((self.cstr(self.rel(q + 8)) if nm else None, self.rel(q + 12) if do else None))
        return out

    def ptr_list(self, cnt_pos):
        """[offset] of a (count, pointer to a pointer table) pair."""
        n = self.u32(cnt_pos)
        if not n:
            return []
        arr = self.rel(cnt_pos + 4)
        return [self.rel(arr + 4 * i) for i in range(n)]

    def models(self):
        c, p = self.dicts[0]
        return self.dict_entries(p) if c else []

    def textures(self):
        c, p = self.dicts[1]
        return self.dict_entries(p) if c else []

    def material_textures(self, m):
        """Names of the textures the material m references (pointers to reference TXOBs, type 0x20000004)."""
        d = self.d
        out = []
        for q in range(m + 0x100, min(m + 0x500, len(d) - 8), 4):
            v = self.u32(q)
            t = q + v
            if v and v < 0x100000 and t + 0x1C <= len(d) and d[t + 4:t + 8] == b'TXOB' and self.u32(t) == 0x20000004:
                out.append(self.cstr(self.rel(t + 0x18)))
        return out

    def _val(self, p, fmt, el, sc):
        code = {0x1406: 'f', 0x1400: 'b', 0x1401: 'B', 0x1402: 'h', 0x1403: 'H'}[fmt]
        vals = struct.unpack_from('<' + code * el, self.d, p)
        return tuple(v * (sc if fmt != 0x1406 else 1.0) for v in vals)

    def attrs(self, shape):
        """(positions, uv0) of a shape (interleaved vertex buffer 0x40000002)."""
        for vb in self.ptr_list(shape + 0x38):
            if self.u32(vb) != 0x40000002:
                continue
            size, raw, stride = self.u32(vb + 0x14), self.rel(vb + 0x18), self.u32(vb + 0x24)
            infos = [(self.u32(a + 4), self.u32(a + 0x24), self.u32(a + 0x28), self.f32(a + 0x2C), self.u32(a + 0x30))
                     for a in self.ptr_list(vb + 0x28)]
            pos, uvs = [], []
            for i in range(size // stride if stride else 0):
                rec = {u: self._val(raw + i * stride + off, fmt, el, sc) for u, fmt, el, sc, off in infos}
                pos.append(rec.get(0))
                uvs.append(rec.get(4))
            return pos, uvs
        return [], []

    def triangles(self, shape, nverts):
        tris = []
        for sm in self.ptr_list(shape + 0x2C):
            for f in self.ptr_list(sm + 0xC):
                for dsc in self.ptr_list(f):
                    fmt, cnt, ptr = self.u32(dsc), self.u32(dsc + 8), self.rel(dsc + 0xC)
                    if fmt == 0x1401:
                        idx = list(self.d[ptr:ptr + cnt])
                    else:
                        idx = list(struct.unpack_from('<%dH' % cnt, self.d, ptr))
                        if idx and max(idx) >= nverts:
                            idx = list(struct.unpack_from('<%dH' % (cnt // 2), self.d, ptr))
                    tris += [tuple(idx[k:k + 3]) for k in range(0, len(idx) - 2, 3)]
        return tris


def collect(data: bytes, tex: str):
    """Triangles of the meshes that use the texture: [{model, mesh, mat, P (3D), px (UV in px), wpx (wrapped)}],
    (width, height)."""
    m = Model(data)
    texs = dict(m.textures())
    if tex not in texs:
        raise KeyError(f'the model has no texture "{tex}" (available: {", ".join(n for n in texs if n)})')
    h, w = struct.unpack_from('<II', data, texs[tex] + 0x18)
    out = []
    for name, off in m.models():
        meshes = m.ptr_list(off + 0xB4)
        mats = m.dict_entries(m.rel(off + 0xC0)) if m.u32(off + 0xBC) else []
        shapes = m.ptr_list(off + 0xC4)
        for i, mp in enumerate(meshes):
            sidx, midx = m.u32(mp + 0x18), m.u32(mp + 0x1C)
            if midx >= len(mats) or sidx >= len(shapes):
                continue
            mname, moff = mats[midx]
            if tex not in m.material_textures(moff):
                continue
            pos, uvs = m.attrs(shapes[sidx])
            for (a, b, c) in m.triangles(shapes[sidx], len(pos)):
                if max(a, b, c) >= len(pos) or None in (uvs[a], uvs[b], uvs[c], pos[a], pos[b], pos[c]):
                    continue
                px = [(uvs[k][0] * w, (1 - uvs[k][1]) * h) for k in (a, b, c)]
                ox = math.floor(min(p[0] for p in px) / w + 1e-6) * w
                oy = math.floor(min(p[1] for p in px) / h + 1e-6) * h
                out.append({'model': name, 'mesh': i, 'mat': mname, 'P': [pos[a], pos[b], pos[c]], 'px': px,
                            'wpx': [(x - ox, y - oy) for x, y in px]})
    return out, (w, h)


def jacobian(P, px):
    """(cu, cv): 3D vectors per texel along +x and +y of the texture (affine mapping of the triangle) or None."""
    (u0, v0), (u1, v1), (u2, v2) = px
    du1, dv1, du2, dv2 = u1 - u0, v1 - v0, u2 - u0, v2 - v0
    det = du1 * dv2 - du2 * dv1
    if abs(det) < 1e-9:
        return None
    e1 = [P[1][k] - P[0][k] for k in range(3)]
    e2 = [P[2][k] - P[0][k] for k in range(3)]
    # J = [e1 e2] . inv([[du1 du2], [dv1 dv2]])
    i00, i01, i10, i11 = dv2 / det, -du2 / det, -dv1 / det, du1 / det
    cu = [e1[k] * i00 + e2[k] * i10 for k in range(3)]
    cv = [e1[k] * i01 + e2[k] * i11 for k in range(3)]
    return cu, cv


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _near(a, b, tol=0.04):
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-9)


def windows(tris, min_size=2):
    """UV windows (wrapped) per mesh with their stretching: [{mesh, model, mat, box (x0, y0, x1, y1), ntri, u, v,
    ratio, uy, vy}] (u/v = 3D length per texel along x/y of the texture; uy/vy = world-vertical component of those
    axes). The triangles of a mesh whose boxes overlap form one window (the two of each quad)."""
    groups = []
    for t in tris:
        wp = t['wpx']
        b = (min(p[0] for p in wp), min(p[1] for p in wp), max(p[0] for p in wp), max(p[1] for p in wp))
        hit = [g for g in groups if g['mesh'] == t['mesh'] and min(g['box'][2], b[2]) - max(g['box'][0], b[0]) > 0.5
               and min(g['box'][3], b[3]) - max(g['box'][1], b[1]) > 0.5]
        if not hit:
            groups.append({'mesh': t['mesh'], 'box': b, 'tris': [t]})
            continue
        g = hit[0]
        for o in hit[1:]:
            g['tris'] += o['tris']
            g['box'] = (min(g['box'][0], o['box'][0]), min(g['box'][1], o['box'][1]),
                        max(g['box'][2], o['box'][2]), max(g['box'][3], o['box'][3]))
            groups.remove(o)
        g['tris'].append(t)
        g['box'] = (min(g['box'][0], b[0]), min(g['box'][1], b[1]), max(g['box'][2], b[2]), max(g['box'][3], b[3]))
    out = []
    for g in groups:
        x0, y0, x1, y1 = g['box']
        if x1 - x0 < min_size or y1 - y0 < min_size:
            continue
        # means of the lengths (not of the vectors: mirrored faces have opposite axes), weighted by area
        acc = [0.0] * 5
        for t in g['tris']:
            j = jacobian(t['P'], t['wpx'])
            if not j:
                continue
            nu, nv = _norm(j[0]), _norm(j[1])
            (a0, b0), (a1, b1), (a2, b2) = t['wpx']
            ar = abs((a1 - a0) * (b2 - b0) - (a2 - a0) * (b1 - b0)) / 2 or 1e-6
            acc[0] += ar
            acc[1] += ar * nu
            acc[2] += ar * nv
            acc[3] += ar * (abs(j[0][1]) / nu if nu > 1e-9 else 0.0)
            acc[4] += ar * (abs(j[1][1]) / nv if nv > 1e-9 else 0.0)
        a = acc[0] or 1.0
        nu, nv = acc[1] / a, acc[2] / a
        t0 = g['tris'][0]
        out.append({'mesh': g['mesh'], 'model': t0['model'], 'mat': t0['mat'], 'box': (x0, y0, x1, y1),
                    'ntri': len(g['tris']), 'u': nu, 'v': nv, 'ratio': (nu / nv) if nv > 1e-9 else float('nan'),
                    'uy': acc[3] / a, 'vy': acc[4] / a})
    # contiguous strips of the same face (same stretching and orientation) -> one window
    merged = True
    while merged:
        merged = False
        for i, g in enumerate(out):
            for h in out[i + 1:]:
                gb, hb = g['box'], h['box']
                touch = (min(gb[2], hb[2]) - max(gb[0], hb[0]) > -0.75 and min(gb[3], hb[3]) - max(gb[1], hb[1]) > -0.75)
                if (g['mesh'] == h['mesh'] and touch and _near(g['u'], h['u']) and _near(g['v'], h['v'])
                        and abs(g['uy'] - h['uy']) < 0.15 and abs(g['vy'] - h['vy']) < 0.15):
                    n = g['ntri'] + h['ntri']
                    g.update(box=(min(gb[0], hb[0]), min(gb[1], hb[1]), max(gb[2], hb[2]), max(gb[3], hb[3])), ntri=n)
                    out.remove(h)
                    merged = True
                    break
            if merged:
                break
    return sorted(out, key=lambda g: (g['mesh'], g['box'][1], g['box'][0]))


def overlay(img, tris, scale=4, box=None):
    """Enlarged image with the UV triangles (magenta fill, yellow outline); box (x, y, w, h) crops."""
    from PIL import Image, ImageDraw
    w, h = img.size
    big = img.convert('RGBA').resize((w * scale, h * scale), Image.NEAREST)
    ov = Image.new('RGBA', big.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for t in tris:
        d.polygon([(x * scale, y * scale) for x, y in t['wpx']], fill=(255, 0, 255, 40), outline=(255, 255, 0, 210))
    big.alpha_composite(ov)
    if box:
        x, y, bw, bh = box
        big = big.crop((x * scale, y * scale, (x + bw) * scale, (y + bh) * scale))
    return big
