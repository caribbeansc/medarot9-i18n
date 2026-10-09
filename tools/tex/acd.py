#!/usr/bin/env python3
"""acd.py - Areas of each CTPK texture that the game really shows (sprites of the .acd files).

The 2D screens are composed with sprites defined in battle/acd and mdr/acd (*.acd, "actd"). Each sprite crops a
rectangle of a texture from the table at the end of the file. Format (checked on the 3,060 .acd files of the ROM:
the read ends exactly at the texture table):

    "actd" name[16] | u8 | u16 n_animations
    animation: name[16] ("normal", "select", "push", "disable"...) | u8 loop | u16 n_frames
      frame: u16 duration | u16 n_sprites | sprites
        sprite (101 bytes + text): name[16] | x, y, w, h (float, screen) | u0, v0, u1, v1 (float, texture px) |
        4 bytes | r, g, b, a (float, color that multiplies the texture) | u8 texture index (255: no texture) |
        float (rotation? varies in animations) | 28 bytes | u16 length | SJIS text (label that the game draws with
        the FONT: python/apply_acd_text.py)
    final table: u16 n | n x name[16] (without '.ctpk'; 16-character ones have no trailing zero)

It tells which part of an atlas is visible (e.g. the furigana drawn on top of a label is NOT visible: the sprite
only crops the text line), how much room there is, and where and at what size it appears on screen (SCALED sprites),
and it is used to compose the screen with the textures (texlib.py screen). Textures used by the scripts (.spt) or
by the code directly do not appear here.

  python tools/tex/acd.py index                index -> translation-work/tex/ctpk_inv/sprites.json
  python tools/tex/acd.py show <rel>           rectangles used of a texture (e.g. mdr/tex/bt_title_m8.ctpk)
  python tools/tex/acd.py dump <acd>           animations, frames and sprites of an .acd
(texlib: `sprites <rel> [--screen]`, `inspect <rel> --sprites` (areas in green) and `screen` (composed screen))
"""
import json
import math
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REPO = HERE.parents[1]
CACHE = REPO / 'translation-work' / 'tex' / 'ctpk_inv' / 'sprites.json'
SPRITE_FIXED = 101          # fixed bytes of a sprite (followed by u16 length + text)


def _name16(b):
    """ASCII name in a 16-byte zero-padded field (or exactly 16 characters), or None."""
    z = b.find(b'\x00')
    if z < 0:
        z = len(b)
    if z <= 0 or any(c for c in b[z:]):
        return None
    s = b[:z]
    if not all(33 <= c < 127 for c in s):
        return None
    return s.decode('ascii')


def _label16(b):
    """Animation/sprite name (may be '0', empty...): text up to the first zero."""
    z = b.find(b'\x00')
    return b[:len(b) if z < 0 else z].decode('cp932', 'replace')


def layout(d):
    """Structural read of an .acd -> {'name', 'anims': [{'name', 'loop', 'frames': [{'dur', 'sprites': [...]}]}],
    'textures': [names]}. Each sprite: {'name', 'x', 'y', 'w', 'h', 'u0', 'v0', 'u1', 'v1', 'color': (r,g,b,a),
    'tex': name or None, 'rot', 'text': SJIS bytes}. ValueError if the file does not fit."""
    if d[:4] != b'actd':
        raise ValueError('not an .acd ("actd" missing)')
    nan = struct.unpack_from('<H', d, 0x15)[0]
    p = 0x17
    anims = []
    raw = []
    for _ in range(nan):
        nm = _label16(d[p:p + 16])
        loop = d[p + 16]
        nfr = struct.unpack_from('<H', d, p + 17)[0]
        p += 19
        frames = []
        for _f in range(nfr):
            dur, nsp = struct.unpack_from('<HH', d, p)
            p += 4
            sps = []
            for _s in range(nsp):
                if p + SPRITE_FIXED + 2 > len(d):
                    raise ValueError('truncated sprite')
                x, y, w, h, u0, v0, u1, v1 = struct.unpack_from('<8f', d, p + 16)
                col = struct.unpack_from('<4f', d, p + 52)
                ti = d[p + 68]
                rot = struct.unpack_from('<f', d, p + 69)[0]
                tl = struct.unpack_from('<H', d, p + SPRITE_FIXED)[0]
                sp = {'name': _label16(d[p:p + 16]), 'x': x, 'y': y, 'w': w, 'h': h,
                      'u0': u0, 'v0': v0, 'u1': u1, 'v1': v1, 'color': col, 'ti': ti, 'rot': rot,
                      'text': d[p + SPRITE_FIXED + 2:p + SPRITE_FIXED + 2 + tl]}
                sps.append(sp)
                raw.append(sp)
                p += SPRITE_FIXED + 2 + tl
            frames.append({'dur': dur, 'sprites': sps})
        anims.append({'name': nm, 'loop': loop, 'frames': frames})
    n = struct.unpack_from('<H', d, p)[0]
    if p + 2 + 16 * n != len(d):
        raise ValueError(f'the texture table does not fit ({p:#x} + {n} names != {len(d):#x})')
    names = [_name16(d[p + 2 + 16 * i:p + 18 + 16 * i]) for i in range(n)]
    for sp in raw:
        sp['tex'] = names[sp['ti']] if sp['ti'] < n else None
    return {'name': _label16(d[4:20]), 'anims': anims, 'textures': names}


def texture_table(d):
    """(offset, [names]) of the final texture table, or (None, [])."""
    for n in range(1, 64):
        p = len(d) - 2 - 16 * n
        if p < 0x14:
            break
        if int.from_bytes(d[p:p + 2], 'little') != n:
            continue
        names = [_name16(d[p + 2 + 16 * i:p + 18 + 16 * i]) for i in range(n)]
        if all(names):
            return p, names
    return None, []


def _parse_scan(d):
    """Heuristic read (looks for sprite records byte by byte): only if the structural one fails."""
    tab, names = texture_table(d)
    if tab is None:
        return []
    out = []
    p = 0x14
    while p + 0x46 <= tab:
        nm = _name16(d[p:p + 16])
        if nm:
            vals = struct.unpack_from('<8f', d, p + 16)
            idx = struct.unpack_from('<H', d, p + 0x44)[0]
            x, y, w, h, u0, v0, u1, v1 = vals
            if (all(math.isfinite(v) and abs(v) < 8192 for v in vals) and idx < len(names)
                    and 0 <= u0 < u1 <= 4096 and 0 <= v0 < v1 <= 4096 and w != 0 and h != 0
                    and all(abs(v - round(v)) < 1e-3 for v in (u0, v0, u1, v1))):
                out.append((nm, x, y, w, h, u0, v0, u1, v1, names[idx]))
                p += 0x46
                continue
        p += 1
    return out


def parse(d):
    """[(sprite, x, y, w, h, u0, v0, u1, v1, texture)] of an .acd: all the sprites with a texture, in file order
    (the frames repeat sprites)."""
    try:
        lay = layout(d)
    except (ValueError, struct.error):
        return _parse_scan(d)
    return [(s['name'], s['x'], s['y'], s['w'], s['h'], s['u0'], s['v0'], s['u1'], s['v1'], s['tex'])
            for a in lay['anims'] for f in a['frames'] for s in f['sprites'] if s['tex']]


def uv_rect(s):
    """Rectangle [x, y, w, h] (integers) of the texture that a sprite shows (minimum 1 px: a degenerate UV stretches
    a single column/row)."""
    u0, u1 = sorted((s['u0'], s['u1']))
    v0, v1 = sorted((s['v0'], s['v1']))
    x0, y0 = int(math.floor(u0 + 1e-3)), int(math.floor(v0 + 1e-3))
    return [x0, y0, max(1, int(math.ceil(u1 - 1e-3)) - x0), max(1, int(math.ceil(v1 - 1e-3)) - y0)]


def tex_rel(root, name, tab=None):
    """Path of the texture of an .acd (in its folder; if it does not exist, in mdr/battle/test)."""
    import romfs
    tab = tab or romfs.table()
    upd = REPO / 'archive' / 'update_extract' / 'romfs'
    for r in (root, 'mdr', 'battle', 'test'):
        rel = f'{r}/tex/{name}.ctpk'
        if rel in tab or (upd / rel).exists():
            return rel
    return f'{root}/tex/{name}.ctpk'


def _acd_files():
    import romfs
    upd = REPO / 'archive' / 'update_extract' / 'romfs'
    rels = set(r for r in romfs.table() if r.endswith('.acd'))
    rels |= {str(q.relative_to(upd)) for q in upd.rglob('*.acd')}
    return sorted(rels)


def build_index():
    import romfs
    import texlib as T
    tab = romfs.table()
    idx = {}
    nfiles = nspr = 0
    for rel in _acd_files():
        try:
            d = T.jp_bytes(rel)
        except FileNotFoundError:
            continue
        try:
            lay = layout(d)
            sp = [s for a in lay['anims'] for f in a['frames'] for s in f['sprites'] if s['tex']]
        except (ValueError, struct.error):
            sp = [dict(zip(('name', 'x', 'y', 'w', 'h', 'u0', 'v0', 'u1', 'v1', 'tex'), t)) for t in _parse_scan(d)]
        if not sp:
            continue
        nfiles += 1
        root = rel.split('/')[0]
        for s in sp:
            trel = tex_rel(root, s['tex'], tab)
            idx.setdefault(trel, []).append({'acd': rel, 'sprite': s['name'], 'rect': uv_rect(s)})
            nspr += 1
    for v in idx.values():
        v.sort(key=lambda e: (e['rect'][1], e['rect'][0], e['acd']))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(idx, ensure_ascii=False, indent=0), encoding='utf-8')
    return idx, nfiles, nspr


def load_index():
    if not CACHE.exists():
        build_index()
    return json.loads(CACHE.read_text(encoding='utf-8'))


def rects_for(rel):
    """Distinct rectangles [x, y, w, h] that the sprites use of the texture rel (with the .acd files that use them)."""
    uses = load_index().get(rel, [])
    merged = {}
    for e in uses:
        merged.setdefault(tuple(e['rect']), []).append(f"{e['acd'].rsplit('/', 1)[-1]}:{e['sprite']}")
    return [(list(r), a) for r, a in sorted(merged.items(), key=lambda kv: (kv[0][1], kv[0][0]))]


def placements(rel, acd_filter=None):
    """How each area of the texture rel looks on screen: [{'rect': texture area, 'screen': [x, y, w, h] in the
    .acd, 'scale': (sx, sy), 'acd', 'sprite', 'anims': [animations where it appears], 'alpha': (min, max)}], grouped
    by (area, screen position). Reads the .acd files that the index associates with the texture."""
    import texlib as T
    users = sorted({e['acd'] for e in load_index().get(rel, [])})
    if acd_filter:
        users = [u for u in users if acd_filter in u]
    name = rel.rsplit('/', 1)[-1].rsplit('.', 1)[0]
    groups = {}
    for u in users:
        try:
            lay = layout(T.jp_bytes(u))
        except (ValueError, struct.error, FileNotFoundError):
            continue
        root = u.split('/')[0]
        for a in lay['anims']:
            for fi, f in enumerate(a['frames']):
                for s in f['sprites']:
                    if s['tex'] != name or tex_rel(root, s['tex']) != rel:
                        continue
                    r = uv_rect(s)
                    scr = [round(s['x'], 1), round(s['y'], 1), round(s['w'], 1), round(s['h'], 1)]
                    key = (tuple(r), tuple(scr), u)
                    g = groups.setdefault(key, {'rect': r, 'screen': scr, 'acd': u, 'sprite': s['name'], 'anims': [],
                                                'alpha': [1.0, 0.0],
                                                'scale': (round(abs(s['w']) / max(1e-6, abs(s['u1'] - s['u0'])), 2)
                                                          if s['u1'] != s['u0'] else None,
                                                          round(abs(s['h']) / max(1e-6, abs(s['v1'] - s['v0'])), 2)
                                                          if s['v1'] != s['v0'] else None)})
                    lab = a['name'] if len(a['frames']) == 1 else f"{a['name']}#{fi}"
                    if lab not in g['anims']:
                        g['anims'].append(lab)
                    g['alpha'] = [min(g['alpha'][0], s['color'][3]), max(g['alpha'][1], s['color'][3])]
    return sorted(groups.values(), key=lambda g: (g['rect'][1], g['rect'][0], g['acd'], g['screen']))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    if sys.argv[1] == 'index':
        idx, nf, ns = build_index()
        print(f'{ns} sprites in {nf} .acd; {len(idx)} textures used -> {CACHE}')
    elif sys.argv[1] == 'show':
        for rel in sys.argv[2:]:
            rs = rects_for(rel)
            print(f'{rel}: {len(rs)} areas used by sprites')
            for r, users in rs:
                more = f' (+{len(users) - 3})' if len(users) > 3 else ''
                print(f'  {r}  {", ".join(users[:3])}{more}')
    elif sys.argv[1] == 'dump':
        import texlib as T
        for rel in sys.argv[2:]:
            lay = layout(T.jp_bytes(rel))
            print(f'{rel}: textures {lay["textures"]}')
            for a in lay['anims']:
                print(f'  animation "{a["name"]}" ({len(a["frames"])} frames, loop {a["loop"]})')
                for fi, f in enumerate(a['frames']):
                    print(f'    frame {fi} (duration {f["dur"]})')
                    for s in f['sprites']:
                        col = '' if s['color'] == (1.0, 1.0, 1.0, 1.0) else \
                            '  color ' + ','.join(f'{c:.2f}' for c in s['color'])
                        txt = f'  text "{s["text"].decode("cp932", "replace")}"' if s['text'] else ''
                        src = f'{s["tex"]} {uv_rect(s)}' if s['tex'] else 'no texture'
                        print(f'      {s["name"]:10} screen ({s["x"]:g}, {s["y"]:g}) {s["w"]:g}x{s["h"]:g}  <- {src}'
                              f'{col}{txt}')
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
