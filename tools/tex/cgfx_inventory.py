#!/usr/bin/env python3
"""cgfx_inventory.py - Inventory of the textures embedded in the CGFX map models (story/mdl/*.bcmdl).

Used to find the SIGNS with Japanese text (texture wave 8): it groups identical textures (hash of the decoded
level-0 pixels: the same building appears in several maps) and generates contact sheets to review them BY EYE.

  python tools/tex/cgfx_inventory.py scan                         index -> translation-work/tex/cgfx/index.json
  python tools/tex/cgfx_inventory.py sheets [--filter REGEX] [--exclude REGEX] [--min N] [--cols C] [--rows R]
                                     [--cell PX] [--tag T]
                                     sheets -> translation-work/tex/cgfx/sheets/<tag>_NNN.png (one group per cell,
                                     labeled with its gNNNN id and the texture name)
  python tools/tex/cgfx_inventory.py show gNNNN [gNNNN ...] [--scale N]
                                     enlarged view with grid (like texlib inspect) of each group
  python tools/tex/cgfx_inventory.py where gNNNN                  models and texture names of the group

Japanese base: archive/rom_extract/story/mdl/ (the 1.3 update does not change models).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cgfx_tex as G  # noqa: E402

REPO = HERE.parents[1]
MDL = REPO / 'archive' / 'rom_extract' / 'story' / 'mdl'
OUT = REPO / 'translation-work' / 'tex' / 'cgfx'
INDEX = OUT / 'index.json'


def scan():
    groups = {}            # pixel hash -> group
    by_raw = {}            # raw-byte hash -> pixel hash (avoids decoding exact copies)
    thumbs = OUT / 'thumbs'
    thumbs.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(MDL.glob('*.bcmdl')):
        d = p.read_bytes()
        for t in G.textures(d):
            n += 1
            raw = d[t['off']:t['off'] + G.level_size(t['w'], t['h'], t['fmt'])]
            rk = hashlib.md5(raw + bytes([t['fmt']]) + t['w'].to_bytes(2, 'little') + t['h'].to_bytes(2, 'little')).hexdigest()
            pk = by_raw.get(rk)
            if pk is None:
                img = G.decode(d, t)
                pk = hashlib.md5(img.tobytes() + t['w'].to_bytes(2, 'little') + t['h'].to_bytes(2, 'little')).hexdigest()
                by_raw[rk] = pk
                if pk not in groups:
                    groups[pk] = {'hash': pk, 'w': t['w'], 'h': t['h'], 'fmt': t['fmt'], 'mips': t['mips'],
                                  'copies': []}
                    img.save(thumbs / f'{pk}.png')
            groups[pk]['copies'].append({'model': p.name, 'tex': t['name']})
    # stable ids: ordered by (first texture name, first model)
    order = sorted(groups.values(), key=lambda g: (g['copies'][0]['tex'].lower(), g['copies'][0]['model']))
    out = []
    for i, g in enumerate(order):
        g['id'] = f'g{i:04d}'
        g['names'] = sorted({c['tex'] for c in g['copies']})
        g['models'] = sorted({c['model'] for c in g['copies']})
        out.append(g)
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps({'texturas': n, 'grupos': out}, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'{n} textures in {len(out)} groups of identical pixels -> {INDEX}')


def load_index():
    return json.loads(INDEX.read_text(encoding='utf-8'))['grupos']


def _thumb(g, cell):
    im = Image.open(OUT / 'thumbs' / f'{g["hash"]}.png').convert('RGBA')
    w, h = im.size
    s = min(cell / w, cell / h)
    s = min(s, 4.0)
    tw, th = max(1, int(w * s)), max(1, int(h * s))
    im = im.resize((tw, th), Image.NEAREST if s >= 1 else Image.LANCZOS)
    bg = Image.new('RGBA', (tw, th), (120, 120, 130, 255))
    ck = ImageDraw.Draw(bg)
    for y in range(0, th, 8):
        for x in range(0, tw, 8):
            if (x // 8 + y // 8) % 2:
                ck.rectangle((x, y, x + 7, y + 7), fill=(90, 90, 100, 255))
    bg.alpha_composite(im)
    return bg


def sheets(flt=None, min_dim=32, cols=8, rows=6, cell=150, tag='all', exclude=None):
    groups = load_index()
    rx = re.compile(flt, re.I) if flt else None
    ex = re.compile(exclude, re.I) if exclude else None
    sel = [g for g in groups if max(g['w'], g['h']) >= min_dim
           and (rx is None or any(rx.search(nm) for nm in g['names']))
           and (ex is None or not any(ex.search(nm) for nm in g['names']))]
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 11)
    per = cols * rows
    lab = 28
    sd = OUT / 'sheets'
    sd.mkdir(parents=True, exist_ok=True)
    for old in sd.glob(f'{tag}_*.png'):
        old.unlink()
    paths = []
    for k in range(0, len(sel), per):
        page = sel[k:k + per]
        sheet = Image.new('RGB', (cols * (cell + 6), rows * (cell + lab + 6)), (24, 24, 28))
        d = ImageDraw.Draw(sheet)
        for i, g in enumerate(page):
            cx, cy = (i % cols) * (cell + 6), (i // cols) * (cell + lab + 6)
            th = _thumb(g, cell)
            sheet.paste(th.convert('RGB'), (cx + (cell - th.size[0]) // 2, cy + (cell - th.size[1]) // 2))
            nm = g['names'][0]
            d.text((cx + 2, cy + cell + 1), f'{g["id"]} {g["w"]}x{g["h"]} x{len(g["copies"])}', fill=(255, 220, 0), font=font)
            d.text((cx + 2, cy + cell + 14), nm[:24], fill=(200, 200, 210), font=font)
        p = sd / f'{tag}_{k // per:03d}.png'
        sheet.save(p)
        paths.append(p)
    print(f'{len(sel)} groups in {len(paths)} sheets -> {sd}/{tag}_*.png')


def show(ids, scale=None):
    sys.path.insert(0, str(HERE))
    import texlib as T
    groups = {g['id']: g for g in load_index()}
    for gid in ids:
        g = groups[gid]
        im = Image.open(OUT / 'thumbs' / f'{g["hash"]}.png').convert('RGBA')
        s = scale or T.auto_scale(*im.size)
        c = T._grid(im, s, f'{gid} {g["names"][0]} {g["w"]}x{g["h"]} fmt {g["fmt"]} ({len(g["copies"])} copies)')
        p = OUT / 'show' / f'{gid}.png'
        p.parent.mkdir(parents=True, exist_ok=True)
        c.convert('RGB').save(p)
        print(p)


def where(gid):
    g = {g['id']: g for g in load_index()}[gid]
    print(f'{gid} {g["w"]}x{g["h"]} fmt {g["fmt"]} mips {g["mips"]}')
    for c in g['copies']:
        print(f'  {c["model"]:32} {c["tex"]}')


def _arg(flag, default=None, cast=str):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        return cast(sys.argv[i + 1])
    return default


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == 'scan':
        scan()
    elif cmd == 'sheets':
        sheets(_arg('--filter'), _arg('--min', 32, int), _arg('--cols', 8, int), _arg('--rows', 6, int),
               _arg('--cell', 150, int), _arg('--tag', 'all'), _arg('--exclude'))
    elif cmd == 'show':
        show([a for a in sys.argv[2:] if re.fullmatch(r'g\d{4}', a)], _arg('--scale', None, int))
    elif cmd == 'where':
        where(sys.argv[2])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
