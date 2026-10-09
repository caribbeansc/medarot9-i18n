#!/usr/bin/env python3
"""ctpk_inventory.py - Inventory of ALL the CTPK textures of the game (battle/tex, mdr/tex, test/tex; version 1.3)
to find those with visible text and check that they are in the waves (translation-work/tex/waves.json).

  python tools/tex/ctpk_inventory.py scan       index -> translation-work/tex/ctpk_inv/index.json + thumbnails
  python tools/tex/ctpk_inventory.py sheets [--grupo G] [--cols C] [--rows R] [--cell PX] [--tag T]
                                     contact sheets -> translation-work/tex/ctpk_inv/sheets/<tag>_NNN.png
  python tools/tex/ctpk_inventory.py show <rel> [<rel> ...]      enlarged view with grid (= texlib inspect)

Groups ("grupo" field of the index): "oleadas" (waves, already in waves.json), "medabot" (Medabot textures of
battle/tex: uppercase codes, KBT00_M...), "piloto" (pilot faces battle/tex/pNNN_pl), "retrato" (busts mdr/tex/bu*,
bbu*, mup*), "prueba" (test textures mdr/tex/test*), "invalido" (not a CTPK) and "candidata" (the rest: review by
eye).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import texlib as T  # noqa: E402

OUT = T.WORK / 'ctpk_inv'
INDEX = OUT / 'index.json'


def grupo(rel, waves):
    name = rel.rsplit('/', 1)[-1][:-5]
    if rel in waves:
        return 'oleadas'
    if rel.startswith('battle/tex/'):
        if re.match(r'^[A-Z]{3}', name):
            return 'medabot'
        if re.match(r'^p\d+_pl$', name):
            return 'piloto'
    if rel.startswith('mdr/tex/'):
        if re.match(r'^(bu|bbu|bu9|mup)[_\d]', name):
            return 'retrato'
        if name.startswith('test'):
            return 'prueba'
    return 'candidata'


def waves_set():
    w = json.loads((T.WORK / 'waves.json').read_text(encoding='utf-8'))
    return {r for x in w for lot in x['lots'] for r in lot}


def scan():
    waves = waves_set()
    rels = sorted({str(p.relative_to(T.ROM_TEX)) for p in T.ROM_TEX.rglob('*.ctpk')}
                  | {str(p.relative_to(T.UPD_TEX)) for p in T.UPD_TEX.rglob('*.ctpk')})
    thumbs = OUT / 'thumbs'
    thumbs.mkdir(parents=True, exist_ok=True)
    out = []
    for rel in rels:
        e = {'rel': rel, 'en': bool(T.en_path(rel)), 'update': (T.UPD_TEX / rel).exists()}
        try:
            data = T.jp_bytes(rel)
            t = T.tex_list(data, rel)[0]
            img = T.decode_bytes(data, rel)
        except Exception as ex:   # 'icon*.ctpk' are not CTPKs
            e.update(grupo='invalido', error=str(ex)[:80])
            out.append(e)
            continue
        e.update(w=t['w'], h=t['h'], fmt=T.C.FMT_NAMES[t['fmt']], grupo=grupo(rel, waves),
                 hash=hashlib.md5(img.tobytes()).hexdigest())
        img.save(thumbs / (T.tex_key(rel) + '.png'))
        out.append(e)
    INDEX.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding='utf-8')
    from collections import Counter
    print(len(out), 'CTPK:', dict(Counter(e['grupo'] for e in out)), '->', INDEX)


def load_index():
    return json.loads(INDEX.read_text(encoding='utf-8'))


def _thumb(rel, cell):
    im = Image.open(OUT / 'thumbs' / (T.tex_key(rel) + '.png')).convert('RGBA')
    s = min(cell / im.size[0], cell / im.size[1], 4.0)
    tw, th = max(1, int(im.size[0] * s)), max(1, int(im.size[1] * s))
    im = im.resize((tw, th), Image.NEAREST if s >= 1 else Image.LANCZOS)
    bg = Image.new('RGBA', (tw, th), (120, 120, 130, 255))
    d = ImageDraw.Draw(bg)
    for y in range(0, th, 8):
        for x in range(0, tw, 8):
            if (x // 8 + y // 8) % 2:
                d.rectangle((x, y, x + 7, y + 7), fill=(90, 90, 100, 255))
    bg.alpha_composite(im)
    return bg


def sheets(grp='candidata', cols=6, rows=5, cell=200, tag=None):
    idx = [e for e in load_index() if e['grupo'] == grp]
    tag = tag or grp
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 11)
    sd = OUT / 'sheets'
    sd.mkdir(parents=True, exist_ok=True)
    for old in sd.glob(f'{tag}_*.png'):
        old.unlink()
    per = cols * rows
    lab = 28
    n = 0
    for k in range(0, len(idx), per):
        page = idx[k:k + per]
        sheet = Image.new('RGB', (cols * (cell + 6), rows * (cell + lab + 6)), (24, 24, 28))
        d = ImageDraw.Draw(sheet)
        for i, e in enumerate(page):
            cx, cy = (i % cols) * (cell + 6), (i // cols) * (cell + lab + 6)
            th = _thumb(e['rel'], cell)
            sheet.paste(th.convert('RGB'), (cx + (cell - th.size[0]) // 2, cy + (cell - th.size[1]) // 2))
            d.text((cx + 2, cy + cell + 1), e['rel'].split('/')[-1][:30], fill=(255, 220, 0), font=font)
            d.text((cx + 2, cy + cell + 14), f"{e['rel'].split('/')[0]} {e['w']}x{e['h']}" + (' EN' if e['en'] else ''),
                   fill=(200, 200, 210), font=font)
        sheet.save(sd / f'{tag}_{n:03d}.png')
        n += 1
    print(f'{len(idx)} textures of group {grp} in {n} sheets -> {sd}/{tag}_*.png')


def _arg(flag, default=None, cast=str):
    if flag in sys.argv:
        return cast(sys.argv[sys.argv.index(flag) + 1])
    return default


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == 'scan':
        scan()
    elif cmd == 'sheets':
        sheets(_arg('--grupo', 'candidata'), _arg('--cols', 6, int), _arg('--rows', 5, int), _arg('--cell', 200, int),
               _arg('--tag'))
    elif cmd == 'show':
        for rel in sys.argv[2:]:
            print(T.inspect(rel, out=OUT / 'show' / (T.tex_key(rel) + '.png')))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
