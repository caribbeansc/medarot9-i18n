#!/usr/bin/env python3
"""
texlib.py - Tools to translate the game's TEXTURES: CTPK (interface) and textures embedded in CGFX 3D models
(.bcmdl: building signs, 3D labels). Full guide: translation-work/tex/INSTRUCCIONES_TEX.md;
recipes by family: translation-work/tex/LECCIONES.md.

<rel> = path in the RomFS. In CGFX models: <rel>:<texture> (or <rel> --tex <texture>), e.g.
story/mdl/m160.bcmdl:m160_sign.
Japanese base: archive/update_extract (1.3) > archive/rom_tex > archive/rom_extract > the ROM itself
(tools/tex/romfs.py).

Commands (from the repo root):
  list <rel>                                   textures of the file (name, size, format, mipmaps)
  inspect <rel> [--scale N] [--crop x,y,w,h]   enlarged PNG with grid: original JP (1.3) and Omnija's EN
  boxes <rel> [--trazos]                       candidate text boxes [x, y, w, h]; --trazos: also, the box fitted
                                               to the strokes inside each one (useful for loose labels on a
                                               transparent background; for buttons and 3D textures use sample)
  sample <rel> x,y,w,h [--from jp|en] [--bg mode|#RRGGBBAA]  analyzes the ORIGINAL text of a box: background, fill,
                                               outline, thickness, gradient, fitted stroke box, letter height, palette
  fonts [--text "Text"] [--cap N] [--only a,b] [--out F]
                                               font sampler; no arguments -> translation-work/tex/fuentes.png
                                               (reference); with arguments -> translation-work/tex/variantes/fuentes.*
  copies <rel:tex>                             other textures with the same pixels in the same folder (models)
  uv <rel:tex> [--es] [--box x,y,w,h] [--scale N] [--out F]
                                               3D models: which part of the texture each mesh shows (UV windows in
                                               px; V flipped: y = (1-v)*height; UVs outside [0,1] wrapped) and with what
                                               stretching (3D per texel in x/y, rotated axes); PNG with the triangles
                                               -> translation-work/tex/inspect/<key>.uv.png (--es: over the written ES)
  sprites <rel> [--compose | --screen [--escalados] [--acd X]]
                                               areas [x, y, w, h] of the texture shown by the .acd sprites
                                               (what is seen on screen; e.g. the furigana of the label atlases is
                                               not seen). inspect <rel> --sprites draws them in green. --compose:
                                               "segments" ready for labels that the screen composes from several strips.
                                               --screen: position and size ON SCREEN of each area (SCALE, alpha,
                                               animations); --escalados: only those drawn at another size
  render <spec.json> [--dry] [--out DIR] [--scale N] [--crop x,y,w,h]
                                               applies the specification; writes data/romfs_tex_es/<rel> (unless --dry;
                                               for models, also the copies from "also", accumulating on what is written)
                                               and the previews preview/<key>.png (JP | EN | ES exactly as it will look
                                               in the game) and preview/<key>.zoom.png (detail of each label). Warns
                                               about pixels changed OUTSIDE the boxes
  variants <spec.json> [--item N] [--try clave=v1,v2]... [--var 'clave=v;clave=v' | --var '{json}']...
           [--text "..."] [--bg todos|oscuro|medio|claro|magenta|R,G,B] [--scale N] [--out F]
                                               tries variants of ONE item (font, cap, colors, box, text...) without
                                               writing or touching the previews: sheet JP | current spec | variants,
                                               already passed through the codec, on plain backgrounds ->
                                               translation-work/tex/variantes/<key>.item<N>.png (--try combine)
  screen <spec.json | rel.ctpk | rel.acd> [--acd X] [--anim a,b] [--frame auto|N|all] [--bg ...] [--scale N]
           [--es-dir DIR] [--out F] [--sin-marcas]
                                               composes the screens (.acd) that use the texture with the JP and ES side
                                               by side (the label on its real button or window; spec = its render)
                                               -> translation-work/tex/pantallas/<key>[.<acd>][.<anim>][.f<N>].png
  render-all <dir> [--dry]                     renders all the specs in a folder (regression)
  tiles [--only substring]                     areas that the .acd files STRETCH (frames, fills, 1-2 px lines) and that
                                               change between the JP and what is written: an erase or an ink that eats
                                               part of a frame -> "protect" in the spec
  verify [--out DIR]                           checks data/romfs_tex_es: same size as the original and only texture
                                               bytes change (headers, meshes and materials intact)
  verify --specs <dir> [--out DIR]             each spec in the folder against what is written: what is written must be
                                               exactly its current render (DIFFERENT / NOT WRITTEN)

Specification (JSON) -- everything is optional except rel/items/box (details in
translation-work/tex/INSTRUCCIONES_TEX.md):
{
  "rel": "mdr/tex/bt_back.ctpk",
  "tex": "m160_sign",                        # CGFX models: texture to edit (required)
  "also": "auto" | ["rel", "rel:tex", {"rel": .., "tex": ..}],  # models: copies with the same pixels
  "base": "jp" | "en",                       # starting image (default "en" if it exists, otherwise "jp")
  "defaults": {...},                         # keys common to all items (style and item take priority)
  "styles": {"name": {...}},                  # own styles (in addition to this library's STYLES)
  "protect": [[x, y, w, h], ...],            # areas restored from the base at the end (icons)
  "items": [
    {"box": [x, y, w, h],                    # area where it is written (and by default, where it is erased and sampled)
     "segments": [[x, y, w, h(, px, py)], ...], # label split into strips that the screen or the model composes:
                                             # in a row (same height) or at (px, py) of the composed strip; the text is
                                             # drawn continuously over it (box in strip coordinates)
     "erase": "glyph" | "glyph:transparent" | "glyph:bg" | "inpaint" | "transparent" | "hfill" | "vfill" |
              "solid:auto" | "solid:#RRGGBB" | "copy:X,Y" | "none",
     "erase_box": [x, y, w, h] | [[...], ...], # area(s) to erase if it is not the box
     "keep": [[x, y, w, h], ...],            # areas the erase does NOT touch (icons inside the box)
     "grow": 1, "thr": 40,                   # glyph mode: mask dilation and detection threshold
     "bg": "mode" | "transparent" | "#RRGGBBAA", # fixed background to detect strokes (cells surrounded by lines)
     "check": true,                          # warn if the erase box cuts strokes (or shadows)
     "text": "Volver",                       # ASCII; \n separates lines
     "font": "rounded" (see FONTS or "path.ttc#index"), "font_var": "Heavy", "wght": 800, "wdth": 75,
     "size": 0 (em px; 0 = auto), "cap": 9 | "jp" (height of CAPITALS in px), "max_cap": 10, "min_size": 5,
     "scale_x": 1.0, "min_scale_x": 0.85,    # fixed horizontal condensing / limit of the automatic condensing
     "tracking": 0, "leading": 1.2, "line_gap": 0, "wrap": false,
     "fill": "#FFFFFF" | "auto" | "auto-grad" | {"top": "#..", "bottom": "#.."} | {"stops": [[0, "#.."], [1, "#.."]]},
     "stroke": "#000000" | "auto" | null, "stroke_w": 1 | "auto",
     "strokes": [{"color": "#..", "w": 1}, ...],   # several outlines (from inside out)
     "shadow": {"dx": 1, "dy": 1, "color": "#000000", "blur": 0, "opacity": 1} | [ ... ],
     "extrude": {"dx": 0, "dy": 3, "color": "#04133C"},   # 3D depth (the outlines surround it)
     "embolden": 0, "italic_skew": 0.0, "rotate": 0 | 90 | 270, "opacity": 1.0, "blur": 0, "crisp": 0,
     "dark_edges": false,                    # RGB x alpha (dark edges), like the original glow of loading
     "align": "center|left|right", "valign": "middle|top|bottom", "baseline": y, "pad": 1 | [l, t, r, b],
     "dx": 0, "dy": 0, "snap": true,
     "sample_box": [x, y, w, h], "sample_from": "jp" | "base",
     "repeat": [[dx, dy], ...],              # repeats the item shifted (states of the same button)
     "style": "name" | ["a", "b"]},
    {"copy": [x, y, w, h], "to": [x, y], "blend": "replace" | "over"}   # copies a piece of the base
  ]
}
"""
import json
import math
import statistics
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageMath

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
sys.path.insert(0, str(REPO / 'tools' / 'tex'))
import ctpk_tool as C  # noqa: E402
import cgfx_tex as G  # noqa: E402
import romfs  # noqa: E402

ROM_TEX = REPO / 'archive' / 'rom_tex'
ROM_EXTRACT = REPO / 'archive' / 'rom_extract'
UPD_TEX = REPO / 'archive' / 'update_extract' / 'romfs'
EN_TEX = REPO / 'data' / 'romfs'
OUT_TEX = REPO / 'data' / 'romfs_tex_es'
WORK = REPO / 'translation-work' / 'tex'
SS = 4   # text supersampling
CGFX_EXT = ('.bcmdl', '.bcres', '.bctex', '.cgfx')

# ------------------------------------------------------------------------------------------- fonts
_SYS = '/System/Library/Fonts/'
_SUP = _SYS + 'Supplemental/'
_USR = str(Path.home() / 'Library' / 'Fonts') + '/'
# name: (path, index within the .ttc, variation: None | 'Instance' | {'Weight': 800, 'Width': 75})
FONTS = {
    # --- originals (compatible with earlier specs)
    'rounded': (_SUP + 'Arial Rounded Bold.ttf', 0, None),
    'bold': (_SUP + 'Arial Bold.ttf', 0, None),
    'black': (_SUP + 'Arial Black.ttf', 0, None),
    'italic': (_SUP + 'Arial Bold Italic.ttf', 0, None),
    'narrow': (_SUP + 'Arial Narrow Bold.ttf', 0, None),
    'impact': (_SUP + 'Impact.ttf', 0, None),
    'regular': (_SUP + 'Arial.ttf', 0, None),
    'verdana': (_SUP + 'Verdana Bold.ttf', 0, None),
    # --- rounded (buttons and menus: the style of the Japanese UI)
    'sf-rounded': (_SYS + 'SFNSRounded.ttf', 0, 'Bold'),
    'sf-rounded-heavy': (_SYS + 'SFNSRounded.ttf', 0, 'Heavy'),
    'sf-rounded-black': (_SYS + 'SFNSRounded.ttf', 0, 'Black'),
    'compact-rounded': (_SYS + 'SFCompactRounded.ttf', 0, 'Bold'),
    'compact-rounded-heavy': (_SYS + 'SFCompactRounded.ttf', 0, 'Heavy'),
    'maru': (_SYS + 'ヒラギノ丸ゴ ProN W4.ttc', 1, None),
    # --- legible sans-serifs at small sizes (HUD, labels of 6-9 px)
    'tahoma': (_SUP + 'Tahoma Bold.ttf', 0, None),
    'hiragino': (_SYS + 'ヒラギノ角ゴシック W6.ttc', 0, None),
    'hiragino-heavy': (_SYS + 'ヒラギノ角ゴシック W8.ttc', 0, None),
    'sf': (_SYS + 'SFNS.ttf', 0, 'Bold'),
    'sf-heavy': (_SYS + 'SFNS.ttf', 0, 'Heavy'),
    'trebuchet': (_SUP + 'Trebuchet MS Bold.ttf', 0, None),
    # --- condensed (long texts in little width)
    'sf-cond': (_SYS + 'SFNS.ttf', 0, 'Condensed Bold'),
    'sf-cond-heavy': (_SYS + 'SFNS.ttf', 0, 'Condensed Heavy'),
    'sf-compressed': (_SYS + 'SFNS.ttf', 0, 'Compressed Heavy'),
    'avenir-cond': (_SYS + 'Avenir Next Condensed.ttc', 0, None),
    'avenir-cond-heavy': (_SYS + 'Avenir Next Condensed.ttc', 8, None),
    'helv-cond': (_SYS + 'HelveticaNeue.ttc', 4, None),
    'helv-cond-black': (_SYS + 'HelveticaNeue.ttc', 9, None),
    'din': (_SUP + 'DIN Condensed Bold.ttf', 0, None),
    # --- posters (battle, logos, Medaforces)
    'avenir-heavy': (_SYS + 'Avenir Next.ttc', 8, None),
    'avenir-heavy-italic': (_SYS + 'Avenir Next.ttc', 9, None),
    'avenir-cond-heavy-italic': (_SYS + 'Avenir Next Condensed.ttc', 9, None),
    'futura': (_SUP + 'Futura.ttc', 2, None),
    'futura-cond': (_SUP + 'Futura.ttc', 4, None),
    'din-alt': (_SUP + 'DIN Alternate Bold.ttf', 0, None),
    'gill-ultra': (_SUP + 'GillSans.ttc', 6, None),
    'anton': (_USR + 'Anton-Regular.ttf', 0, None),
    'sf-black': (_SYS + 'SFNS.ttf', 0, 'Black'),
    'sf-black-italic': (_SYS + 'SFNSItalic.ttf', 0, 'Black Italic'),
    'sf-heavy-italic': (_SYS + 'SFNSItalic.ttf', 0, 'Heavy Italic'),
}
_FONT_CACHE = {}
_CAP_CACHE = {}


def _font_entry(it_or_name):
    """(path, index, variation) of a font by name, path ('x.ttc#3') or item (with font_var/wght/wdth)."""
    if isinstance(it_or_name, dict):
        name = it_or_name.get('font', 'bold')
        path, idx, var = _font_entry(name)
        if it_or_name.get('font_var'):
            var = it_or_name['font_var']
        if it_or_name.get('wght') or it_or_name.get('wdth'):
            var = dict(var) if isinstance(var, dict) else {}
            if it_or_name.get('wght'):
                var['Weight'] = it_or_name['wght']
            if it_or_name.get('wdth'):
                var['Width'] = it_or_name['wdth']
        return path, idx, var
    name = it_or_name or 'bold'
    if name in FONTS:
        return FONTS[name]
    if '#' in name:
        p, i = name.rsplit('#', 1)
        return p, int(i), None
    if Path(name).exists():
        return name, 0, None
    raise ValueError(f'unknown font: {name} (use one of: {", ".join(FONTS)})')


def get_font(entry, size):
    path, idx, var = entry
    key = (path, idx, json.dumps(var, sort_keys=True), round(size, 3))
    f = _FONT_CACHE.get(key)
    if f is None:
        f = ImageFont.truetype(path, size, index=idx)
        if isinstance(var, str):
            names = [n.decode() if isinstance(n, bytes) else n for n in f.get_variation_names()]
            match = [n for n in names if n.lower() == var.lower()] or [n for n in names if var.lower() in n.lower()]
            if not match:
                raise ValueError(f'variation "{var}" does not exist in {Path(path).name}; '
                                 f'available: {", ".join(names[:40])}')
            f.set_variation_by_name(match[0])
        elif isinstance(var, dict):
            vals = []
            for a in f.get_variation_axes():
                nm = a['name'].decode() if isinstance(a['name'], bytes) else a['name']
                vals.append(var.get(nm, a.get('default', a['minimum'])))
            f.set_variation_by_axes(vals)
        if len(_FONT_CACHE) > 400:
            _FONT_CACHE.clear()
        _FONT_CACHE[key] = f
    return f


def _is_pixel_font(entry):
    """Bitmap fonts (translation-work/tex/fuentes_pixel, pixfont): only read at scale 1 in x."""
    path = str(entry[0]).replace('\\', '/').lower()
    return '/fuentes_pixel/' in path or '/pixfont/' in path or Path(path).name.startswith('pix')


def cap_ratio(entry):
    """Height of the 'H' / em size of the font."""
    key = (entry[0], entry[1], json.dumps(entry[2], sort_keys=True))
    if key not in _CAP_CACHE:
        f = get_font(entry, 200)
        bb = f.getbbox('H', anchor='ls')
        _CAP_CACHE[key] = max(0.3, -bb[1] / 200.0)
    return _CAP_CACHE[key]


# ------------------------------------------------------------------------------------------- utilities
def _hex(c):
    if c is None:
        return None
    if isinstance(c, (tuple, list)):
        c = tuple(int(v) for v in c)
        return c if len(c) == 4 else c + (255,)
    c = c.strip().lstrip('#')
    if len(c) == 3:
        c = ''.join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + ((int(c[6:8], 16),) if len(c) == 8 else (255,))


def _to_hex(c):
    if c is None:
        return None
    s = '#%02X%02X%02X' % tuple(int(round(v)) for v in c[:3])
    return s + ('%02X' % int(round(c[3])) if len(c) > 3 and c[3] < 255 else '')


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _cdist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _rects(v):
    """[x,y,w,h] or [[x,y,w,h],...] -> list of tuples."""
    if not v:
        return []
    if isinstance(v[0], (int, float)):
        return [tuple(int(round(t)) for t in v)]
    return [tuple(int(round(t)) for t in r) for r in v]


def _clip(r, W, H):
    x, y, w, h = r
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def _pixels(im):
    """List of pixels (compatible with old and new Pillow)."""
    f = getattr(im, 'get_flattened_data', None)
    return list(f() if f else im.getdata())


def _median(cols):
    if not cols:
        return (0, 0, 0, 0)
    return tuple(int(statistics.median(c[i] for c in cols)) for i in range(4))


def _pads(p):
    if isinstance(p, (int, float)):
        return (p, p, p, p)
    p = list(p)
    if len(p) == 2:
        return (p[0], p[1], p[0], p[1])
    return tuple(p[:4])


def is_cgfx(rel):
    return rel.lower().endswith(CGFX_EXT)


def split_rel(arg, tex=None):
    """'story/mdl/m101.bcmdl:m101_name' -> ('story/mdl/m101.bcmdl', 'm101_name'); otherwise (arg, tex)."""
    if ':' in arg:
        r, t = arg.split(':', 1)
        if is_cgfx(r):
            return r, t
    return arg, tex


def tex_key(rel, tex=None):
    """File name of specs/previews: rel with '__' (+ '__texture' in CGFX models)."""
    return rel.replace('/', '__') + (f'__{tex}' if tex else '')


def jp_path(rel):
    """Effective Japanese file (1.3) on disk: update > archive/rom_tex > archive/rom_extract (or None)."""
    for base in (UPD_TEX, ROM_TEX, ROM_EXTRACT):
        p = base / rel
        if p.exists():
            return p
    return None


SOURCE = None          # m9.dump.Dump of the player: when set, the Japanese textures come from it


def jp_bytes(rel):
    """Bytes of the effective Japanese file; if it is not extracted in archive/, it is read from the ROM
    (tools/tex/romfs.py)."""
    if SOURCE is not None:
        return SOURCE.read(rel)
    p = jp_path(rel)
    return p.read_bytes() if p is not None else romfs.read(rel)


def en_path(rel):
    if SOURCE is not None:          # building from the player's dump: no other translation's files
        return None
    p = EN_TEX / rel
    return p if p.exists() else None


def tex_list(data, rel):
    """[{name, w, h, fmt, ...}] of the textures of the file (CTPK or CGFX model)."""
    if is_cgfx(rel):
        return G.textures(data)
    return [{'name': n, 'w': w, 'h': h, 'fmt': f, 'mips': 1, 'off': o, 'size': s}
            for (_i, n, f, w, h, o, s) in C._entries(data)]


def _need_tex(rel, tex, data=None):
    if is_cgfx(rel) and not tex:
        names = ', '.join(t['name'] for t in G.textures(data if data is not None else jp_bytes(rel)))
        raise ValueError(f'{rel} is a CGFX model: give the texture ("tex" in the spec, or {rel}:<texture>). '
                         f'Textures: {names}')


def decode_bytes(data, rel, tex=None):
    """RGBA image (level 0) of the texture: CTPK -> the only texture; CGFX -> the texture with that name."""
    _need_tex(rel, tex, data)
    if is_cgfx(rel):
        return G.decode(data, G.get(data, tex))
    return C.decode(data)[0].img


def encode_bytes(data, rel, img, tex=None, orig=None):
    """data with the texture re-encoded from img (same format and size). orig = original reference file
    (CGFX: blocks and mipmaps unchanged byte for byte; in CTPK replace() already uses data as a reference)."""
    if is_cgfx(rel):
        return G.replace(data, tex, img, orig=orig if orig is not None else data)
    return C.replace(data, {0: img})


def fmt_name(data, rel, tex=None):
    if is_cgfx(rel):
        t = G.get(data, tex)
        return f'{C.FMT_NAMES[t["fmt"]]}, {t["w"]}x{t["h"]}, mipmaps {len(G.levels(t))}'
    return C.FMT_NAMES[C._entries(data)[0][2]]


def roundtrip(data, rel, img, tex=None):
    """How img will look in the game (encoded in the texture's format and decoded)."""
    if is_cgfx(rel):
        try:
            return decode_bytes(encode_bytes(data, rel, img, tex), rel, tex)
        except Exception:
            return img
    return _final_view(data, img)


def load(rel, which='jp', tex=None):
    if which == 'jp':
        return decode_bytes(jp_bytes(rel), rel, tex)
    p = en_path(rel)
    if p is None:
        return None
    return decode_bytes(p.read_bytes(), rel, tex)


# ------------------------------------------------------------------------------------------- inspect
def _checker(w, h):
    tile = Image.new('RGBA', (8, 8), (95, 95, 105, 255))
    d = ImageDraw.Draw(tile)
    d.rectangle((4, 0, 7, 3), fill=(70, 70, 80, 255))
    d.rectangle((0, 4, 3, 7), fill=(70, 70, 80, 255))
    ck = Image.new('RGBA', (w, h))
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            ck.paste(tile, (x, y))
    return ck


def _grid(img: Image.Image, scale: int, label: str, origin=(0, 0), rects=None) -> Image.Image:
    """Enlarged panel with a checkerboard (transparency), a grid every 8 px and coordinates every 32 px.
    origin = texture coordinates of the (0,0) pixel of img (for crops). rects = [(x,y,w,h,color)]."""
    w, h = img.size
    ck = _checker(w, h)
    ck.alpha_composite(img)
    big = ck.resize((w * scale, h * scale), Image.NEAREST)
    m = 26
    canvas = Image.new('RGBA', (w * scale + m, h * scale + m + 14), (30, 30, 34, 255))
    canvas.paste(big, (m, m + 14))
    d = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONTS['regular'][0], 10)
    d.text((2, 0), label, fill=(255, 220, 0, 255), font=font)
    ox, oy = origin
    step_lbl = 32 if scale < 6 else 16 if scale < 12 else 8
    for x in range(0, w + 1):
        tx = ox + x
        if tx % 8:
            continue
        X = m + x * scale
        col = (255, 80, 80, 170) if tx % 32 == 0 else (255, 255, 255, 50)
        d.line([(X, m + 14), (X, m + 14 + h * scale)], fill=col)
        if tx % step_lbl == 0 and x < w:
            d.text((X + 1, m), str(tx), fill=(255, 120, 120, 255), font=font)
    for y in range(0, h + 1):
        ty = oy + y
        if ty % 8:
            continue
        Y = m + 14 + y * scale
        col = (255, 80, 80, 170) if ty % 32 == 0 else (255, 255, 255, 50)
        d.line([(m, Y), (m + w * scale, Y)], fill=col)
        if ty % step_lbl == 0 and y < h:
            d.text((0, Y + 1), str(ty), fill=(255, 120, 120, 255), font=font)
    for r in rects or []:
        x, y, rw, rh, col = r
        X0, Y0 = m + (x - ox) * scale, m + 14 + (y - oy) * scale
        d.rectangle((X0, Y0, X0 + rw * scale - 1, Y0 + rh * scale - 1), outline=col)
    return canvas


def auto_scale(w, h):
    big = max(w, h)
    return 4 if big <= 64 else 3 if big <= 128 else 2 if big <= 256 else 1


def _stack(panels, vertical=True, gap=6):
    if vertical:
        W = max(p.size[0] for p in panels)
        H = sum(p.size[1] for p in panels) + gap * (len(panels) - 1)
    else:
        W = sum(p.size[0] for p in panels) + gap * (len(panels) - 1)
        H = max(p.size[1] for p in panels)
    canvas = Image.new('RGBA', (W, H), (20, 20, 22, 255))
    o = 0
    for p in panels:
        canvas.paste(p, (0, o) if vertical else (o, 0))
        o += (p.size[1] if vertical else p.size[0]) + gap
    return canvas


def _panel_layout(w, h, n, scale=None, max_dim=1500):
    """Scale and orientation for n panels of w x h within max_dim."""
    if scale:
        return scale, (w >= h)
    best = None
    for vertical in (True, False):
        W, H = (w, h * n) if vertical else (w * n, h)
        s = max(1, min(8, int(max_dim // max(W, H * 0.75))))
        if best is None or s > best[0]:
            best = (s, vertical)
    return best


def _axis_dir(c):
    a = abs(c)
    return 'vertical' if a > 0.7 else ('horizontal' if a < 0.3 else 'inclinado')


def uv_report(rel, tex, box=None, scale=None, out=None, es=False):
    """Which part of a CGFX model texture is visible and with what stretching (tools/tex/cgfx_uv.py): UV windows per
    mesh (in texture px, V flipped and UVs wrapped) and a PNG with the triangles over the JP texture (or the written
    ES one, with es=True) -> translation-work/tex/inspect/<key>.uv.png. Returns the path of the PNG."""
    import cgfx_uv as UV
    tris, (w, h) = UV.collect(jp_bytes(rel), tex)
    wins = UV.windows(tris)
    if box:
        bx, by, bw, bh = box
        wins = [g for g in wins if g['box'][2] > bx and g['box'][0] < bx + bw and g['box'][3] > by and g['box'][1] < by + bh]
    meshes = sorted({t['mesh'] for t in tris})
    print(f'{rel}:{tex} {w}x{h}: {len(tris)} triangles in {len(meshes)} mesh(es) of this model'
          + (f'; windows touching the box {list(box)}' if box else ''))
    if not tris:
        print('  no mesh of THIS model uses the texture: it is seen in another model (look at its copies with `copies`)'
              ' '
              'or it is not seen')
    for g in wins:
        x0, y0, x1, y1 = g['box']
        print(f'  mesh {g["mesh"]} ({g["model"]}, material {g["mat"]!r}): window x {x0:.1f}-{x1:.1f}, y {y0:.1f}-{y1:.1f}'
              f' ({x1 - x0:.0f}x{y1 - y0:.0f} px, {g["ntri"]} tri) | 3D per texel: x {g["u"]:.4f}, y {g["v"]:.4f}, '
              f'x/y {g["ratio"]:.2f} | texture x axis {_axis_dir(g["uy"])}, y axis {_axis_dir(g["vy"])}')
    if wins:
        print('  x/y = how much wider the face gets compared to what is painted (1.15: it looks 15 % wider -> narrower '
              'letters, scale_x ~ 1/1.15); vertical x axis = the label looks rotated')
    src = None
    if es:
        p = OUT_TEX / rel
        if p.exists():
            src = decode_bytes(p.read_bytes(), rel, tex)
        else:
            print('  (no written ES version: drawn over the JP)')
    if src is None:
        src = load(rel, 'jp', tex)
    if scale is None:
        ref = max(box[2], box[3]) if box else max(w, h)
        scale = max(1, min(10, 1024 // max(1, ref)))
    img = UV.overlay(src, tris, scale, box)
    out = Path(out) if out else WORK / 'inspect' / (tex_key(rel, tex) + ('.es' if es else '') + '.uv.png')
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert('RGB').save(out)
    return out


def sprite_rects(rel):
    """Areas [x, y, w, h] of the texture shown by the sprites of the .acd files (tools/tex/acd.py), clipped to the
    texture: [(rect, users, overflows)]. Empty list if no .acd uses it (scripts or the code may use it)."""
    if is_cgfx(rel):
        return []
    import acd
    W, H = load(rel).size
    out = []
    for r, users in acd.rects_for(rel):
        x, y, w, h = r
        cl = [max(0, x), max(0, y), min(W, x + w) - max(0, x), min(H, y + h) - max(0, y)]
        if cl[2] > 0 and cl[3] > 0:
            out.append((cl, users, cl != r))
    return out


def inspect(rel, out=None, scale=None, crop=None, tex=None, sprites=False):
    jp = load(rel, 'jp', tex)
    en = load(rel, 'en', tex) if en_path(rel) else None
    full = jp.size
    origin = (0, 0)
    if crop:
        x, y, w, h = crop
        jp = jp.crop((x, y, x + w, y + h))
        en = en.crop((x, y, x + w, y + h)) if en is not None else None
        origin = (x, y)
    n = 2 if en is not None else 1
    s, vertical = _panel_layout(*jp.size, n, scale)
    name = f'{rel}:{tex}' if tex else rel
    srects = [(*r, (60, 255, 90, 255)) for r, _u, _o in sprite_rects(rel)] if sprites else None
    lab = f'JP 1.3  {name}  {full[0]}x{full[1]}  (x{s})' + ('  [green = areas shown by the sprites]' if sprites else '')
    panels = [_grid(jp, s, lab, origin, srects)]
    if en is not None:
        panels.append(_grid(en, s, 'EN (Omnija) - layout reference', origin))
    canvas = _stack(panels, vertical)
    suffix = f'.crop{origin[0]}_{origin[1]}' if crop else ''
    out = Path(out or (WORK / 'inspect' / (tex_key(rel, tex) + suffix + '.png')))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert('RGB').save(out)
    return out


# ------------------------------------------------------------------------------------------- inpainting
def _fsplit_premul(reg):
    """RGBA region -> 4 premultiplied 'F' images (R*A/255, G*A/255, B*A/255, A)."""
    r, g, b, a = (ch.convert('F') for ch in reg.split())
    pm = [ImageMath.lambda_eval(lambda e: e['c'] * e['a'] / 255.0, c=c, a=a) for c in (r, g, b)]
    return pm + [a]


def _fmerge_unpremul(chs):
    r, g, b, a = chs
    out = []
    for c in (r, g, b):
        out.append(ImageMath.lambda_eval(
            lambda e: e['convert'](e['min'](e['max'](e['c'] * 255.0 / e['max'](e['a'], 0.0001), 0.0), 255.0) + 0.5, 'L'),
            c=c, a=a))
    out.append(ImageMath.lambda_eval(lambda e: e['convert'](e['min'](e['max'](e['a'], 0.0), 255.0) + 0.5, 'L'), a=a))
    return Image.merge('RGBA', out)


def _shift(im, dx, dy):
    """Shifts an 'F' image; the uncovered border keeps its own value (Neumann condition)."""
    W, H = im.size
    out = im.copy()
    out.paste(im.crop((max(0, -dx), max(0, -dy), W - max(0, dx), H - max(0, dy))), (max(0, dx), max(0, dy)))
    return out


def _pullpush(chans, known):
    levels = [(known, chans)]
    cur_w, cur_v = known, chans
    while cur_w.size != (1, 1):
        ns = (max(1, (cur_w.size[0] + 1) // 2), max(1, (cur_w.size[1] + 1) // 2))
        aw = cur_w.resize(ns, Image.BOX)
        vw = [ImageMath.lambda_eval(lambda e: e['v'] * e['w'], v=v, w=cur_w).resize(ns, Image.BOX) for v in cur_v]
        val = [ImageMath.lambda_eval(lambda e: e['x'] / e['max'](e['w'], 0.000001), x=x, w=aw) for x in vw]
        wc = ImageMath.lambda_eval(lambda e: e['min'](e['w'] * 4.0, 1.0), w=aw)
        levels.append((wc, val))
        cur_w, cur_v = wc, val
    acc = levels[-1][1]
    for wl, vl in reversed(levels[:-1]):
        up = [a.resize(wl.size, Image.BILINEAR) for a in acc]
        acc = [ImageMath.lambda_eval(lambda e: e['w'] * e['v'] + (1.0 - e['w']) * e['u'], w=wl, v=v, u=u)
               for v, u in zip(vl, up)]
    return acc


def _harmonic(chans, known, iters=None):
    """Fills the unknown pixels (known=0) by solving Laplace (smooth membrane) with the known ones as the
    boundary: pull-push initialization + Jacobi iterations. All in 'F' images (fast)."""
    W, H = known.size
    filled = _pullpush(chans, known)
    if iters is None:
        iters = min(400, 60 + 3 * max(W, H))
    for _ in range(iters):
        nxt = []
        for c, orig in zip(filled, chans):
            s = ImageMath.lambda_eval(lambda e: (e['p'] + e['q'] + e['r'] + e['t']) * 0.25,
                                      p=_shift(c, 1, 0), q=_shift(c, -1, 0), r=_shift(c, 0, 1), t=_shift(c, 0, -1))
            nxt.append(ImageMath.lambda_eval(lambda e: e['k'] * e['o'] + (1.0 - e['k']) * e['s'], k=known, o=orig, s=s))
        filled = nxt
    return filled


def _unknown_mask(region, rects, keep):
    """'L' mask (255 = unknown) of the size of the region with the rects (texture coords) minus keep."""
    x0, y0, x1, y1 = region
    m = Image.new('L', (x1 - x0, y1 - y0), 0)
    d = ImageDraw.Draw(m)
    for (x, y, w, h) in rects:
        d.rectangle((x - x0, y - y0, x - x0 + w - 1, y - y0 + h - 1), fill=255)
    for (x, y, w, h) in keep or []:
        d.rectangle((x - x0, y - y0, x - x0 + w - 1, y - y0 + h - 1), fill=0)
    return m


def _region_for(img, rects, margin=2):
    W, H = img.size
    xs0 = min(r[0] for r in rects) - margin
    ys0 = min(r[1] for r in rects) - margin
    xs1 = max(r[0] + r[2] for r in rects) + margin
    ys1 = max(r[1] + r[3] for r in rects) + margin
    return (max(0, xs0), max(0, ys0), min(W, xs1), min(H, ys1))


def inpaint(img, region, unknown_L, iters=None):
    """Fills (in place) the pixels of img marked in unknown_L (region (x0,y0,x1,y1)) by diffusion from the
    known pixels around them. Works in premultiplied RGBA (respects transparency)."""
    reg = img.crop(region)
    chans = _fsplit_premul(reg)
    known = unknown_L.point(lambda v: 0 if v else 255).convert('F')
    known = ImageMath.lambda_eval(lambda e: e['k'] / 255.0, k=known)
    if known.getextrema()[1] <= 0:
        img.paste(Image.new('RGBA', reg.size, (0, 0, 0, 0)), region[:2], unknown_L)
        return
    filled = _fmerge_unpremul(_harmonic(chans, known, iters))
    reg.paste(filled, (0, 0), unknown_L)
    img.paste(reg, region[:2])


def _background(img, rects, keep=None, margin=2):
    """Estimate of the BACKGROUND under the rects (without text) by diffusion from the outer ring.
    Returns (region, F channels of the original, F channels of the background, L mask of the rects)."""
    region = _region_for(img, rects, margin)
    unk = _unknown_mask(region, rects, keep)
    reg = img.crop(region)
    chans = _fsplit_premul(reg)
    known = ImageMath.lambda_eval(lambda e: e['k'] / 255.0, k=unk.point(lambda v: 0 if v else 255).convert('F'))
    if known.getextrema()[1] <= 0:
        bg = [Image.new('F', reg.size, 0.0) for _ in range(4)]
    else:
        bg = _harmonic(chans, known)
    return region, chans, bg, unk


def _dilate(mask, r):
    """Roughly circular grayscale dilation (alternates 3x3 square and cross) of r steps."""
    m = mask
    for i in range(int(r)):
        h = ImageChops.lighter(ImageChops.lighter(m, ImageChops.offset(m, 1, 0)), ImageChops.offset(m, -1, 0))
        if i % 2 == 0:      # square (separable)
            m = ImageChops.lighter(ImageChops.lighter(h, ImageChops.offset(h, 0, 1)), ImageChops.offset(h, 0, -1))
        else:               # cross
            m = ImageChops.lighter(h, ImageChops.lighter(ImageChops.offset(m, 0, 1), ImageChops.offset(m, 0, -1)))
    return m


def _dilate_frac(mask, r):
    """Dilation of r steps (r may be fractional: blend between floor and ceil)."""
    lo = int(math.floor(r))
    f = r - lo
    a = _dilate(mask, lo)
    if f < 0.05:
        return a
    b = _dilate(a, 1)
    return Image.blend(a, b, f)


def mode_color(img, rects, keep=None):
    """Most frequent color (quantized) within rects: the background of a cell with text."""
    from collections import Counter
    cnt = Counter()
    acc = {}
    keep = _rects(keep)
    W, H = img.size
    px = img.load()
    for (x, y, w, h) in _rects(rects):
        for yy in range(max(0, y), min(H, y + h)):
            for xx in range(max(0, x), min(W, x + w)):
                if any(k[0] <= xx < k[0] + k[2] and k[1] <= yy < k[1] + k[3] for k in keep):
                    continue
                c = px[xx, yy]
                q = (c[0] >> 4, c[1] >> 4, c[2] >> 4, c[3] >> 4) if c[3] else (0, 0, 0, 0)
                cnt[q] += 1
                acc.setdefault(q, []).append(c)
    if not cnt:
        return (0, 0, 0, 0)
    q = cnt.most_common(1)[0][0]
    return _median(acc[q])


def _bg_param(img, rects, keep, bg):
    """bg of the specification -> RGBA color or None (None = background by diffusion from the ring)."""
    if bg in (None, '', 'ring', 'auto'):
        return None
    if bg == 'mode':
        return mode_color(img, rects, keep)
    if bg == 'transparent':
        return (0, 0, 0, 0)
    return _hex(bg)


def glyph_mask(img, rects, keep=None, thr=None, margin=2, bg=None):
    """Mask of the text STROKES within rects: pixels that deviate from the background. Background = diffusion from
    the outer ring of the box (default) or a fixed color (bg = "#RRGGBBAA" | "mode" = most frequent color
    of the box; useful in cells surrounded by lines). Hysteresis threshold (strong = thr, weak = thr/2 connected
    to a strong one). Returns (region, L mask, F channels of the background)."""
    thr = thr or 40
    bgc = _bg_param(img, rects, keep, bg)
    if bgc is None:
        region, chans, bgch, unk = _background(img, rects, keep, margin)
    else:
        region = _region_for(img, rects, margin)
        unk = _unknown_mask(region, rects, keep)
        chans = _fsplit_premul(img.crop(region))
        a = bgc[3] / 255.0
        bgch = [Image.new('F', unk.size, float(bgc[0] * a)), Image.new('F', unk.size, float(bgc[1] * a)),
                Image.new('F', unk.size, float(bgc[2] * a)), Image.new('F', unk.size, float(bgc[3]))]
    d = None
    for c, b in zip(chans, bgch):
        di = ImageMath.lambda_eval(lambda e: abs(e['c'] - e['b']), c=c, b=b)
        d = di if d is None else ImageMath.lambda_eval(lambda e: e['max'](e['x'], e['y']), x=d, y=di)
    dl = ImageMath.lambda_eval(lambda e: e['convert'](e['min'](e['d'], 255.0), 'L'), d=d)
    dl = ImageChops.multiply(dl, unk)
    strong = dl.point(lambda v: 255 if v >= thr else 0)
    weak = dl.point(lambda v: 255 if v >= thr * 0.5 else 0)
    m = strong
    for _ in range(64):
        n = ImageChops.multiply(_dilate(m, 1), weak)
        if ImageChops.difference(n, m).getbbox() is None:
            break
        m = n
    return region, m, bgch


# ------------------------------------------------------------------------------------------- color analysis
def _top_half(cols, key):
    """Half of cols with the greatest key (at least 1)."""
    if not cols:
        return cols
    srt = sorted(cols, key=key, reverse=True)
    return srt[:max(1, (len(srt) + 1) // 2)]


def analyze(img, box, keep=None, thr=None, bg=None):
    """Analyzes the ORIGINAL text inside box. Returns a dict with: bg (background), fill, stroke (outline or
    None), stroke_w (estimated thickness), grad (vertical gradient stops of the fill or None), glyph_box [x,y,w,h]
    (box fitted to the strokes), glyph_h (height of the strokes without outline), n (stroke pixels).
    Method: stroke mask by difference from the diffused background; fill = eroded core (the pixels
    farthest from the background); outline = pixels of the mask border that are NOT a fill<->background blend."""
    rects = _rects(box)
    bgfix = _bg_param(img, rects, keep, bg)
    region, m, bgch = glyph_mask(img, rects, keep, thr, bg=bg)
    x0, y0, x1, y1 = region
    W = x1 - x0
    pix = _pixels(img.crop(region))
    mk = _pixels(m)
    upx = _pixels(_unknown_mask(region, rects, keep))
    ring = [pix[i] for i in range(len(pix)) if not upx[i]]
    if bgfix is not None:
        bgc = bgfix
    else:
        bgc = _median(ring) if ring else _median(_pixels(_fmerge_unpremul(bgch)))
    G = [i for i, v in enumerate(mk) if v]
    area = sum(1 for v in upx if v)
    res = {'bg': _to_hex(bgc), 'n': len(G), 'cover': round(len(G) / max(1, area), 2)}
    if len(G) < 4:
        res.update(fill=None, stroke=None, stroke_w=0, grad=None, glyph_box=None, glyph_h=0, palette=[])
        return res
    core = _pixels(m.filter(ImageFilter.MinFilter(3)))
    gx = [i % W for i in G]
    gy = [i // W for i in G]
    gb = [min(gx) + x0, min(gy) + y0, max(gx) - min(gx) + 1, max(gy) - min(gy) + 1]
    C_ = [i for i in G if core[i]]
    Bd = [i for i in G if not core[i]]
    transparent_bg = bgc[3] < 128

    def dist_bg(c):
        if transparent_bg:
            return c[3] + 0.25 * _lum(c)
        return _cdist(c, bgc) + abs(c[3] - bgc[3])

    fill_src = C_ if len(C_) >= max(3, len(G) // 10) else G
    fcols = [pix[i] for i in fill_src if pix[i][3] >= 128] or [pix[i] for i in fill_src]
    fill = _median(_top_half(fcols, dist_bg))
    # outline: mask pixels that are neither fill nor a fill<->background blend
    fb = [bgc[j] - fill[j] for j in range(3)]
    L2 = sum(v * v for v in fb)
    outl = []
    for i in G:
        c = pix[i]
        if c[3] < 96:
            continue
        df = _cdist(c, fill)
        if df < 45:
            continue
        if transparent_bg:
            outl.append(i)
            continue
        t = sum((c[j] - fill[j]) * fb[j] for j in range(3)) / L2 if L2 > 0 else 0.0
        resid = _cdist(c, [fill[j] + t * fb[j] for j in range(3)])
        if resid > 30 or t > 1.12 or t < -0.12:
            outl.append(i)
    stroke = None
    stroke_w = 0
    if len(outl) >= max(3, len(Bd) // 6):
        ocols = [pix[i] for i in outl]
        stroke = _median(_top_half(ocols, lambda c: _cdist(c, fill) + (0 if transparent_bg else _cdist(c, bgc))))
        # refine: the pure fill is what differs most from the outline (and vice versa)
        gcols = [pix[i] for i in G if pix[i][3] >= 128]
        if gcols:
            far = sorted(gcols, key=lambda c: _cdist(c, stroke), reverse=True)
            fill = _median(far[:max(1, len(far) // 3)])
            far_o = sorted(ocols, key=lambda c: _cdist(c, fill), reverse=True)
            stroke = _median(far_o[:max(1, len(far_o) // 2)])
        near = sum(1 for i in G if pix[i][3] >= 96 and _cdist(pix[i], stroke) < _cdist(pix[i], fill))
        stroke_w = round(min(4.0, max(0.5, near / max(1, len(Bd)))) * 2) / 2
    # vertical gradient of the fill (core)
    grad = None
    fsel = [i for i in fill_src if pix[i][3] >= 128
            and (stroke is None or _cdist(pix[i], fill) <= _cdist(pix[i], stroke))
            and (transparent_bg or _cdist(pix[i], fill) <= _cdist(pix[i], bgc))]
    ys = [i // W for i in fsel]
    if ys and max(ys) - min(ys) >= 4:
        ytop, ybot = min(ys), max(ys)
        bins = [[], [], []]
        for i in fsel:
            tt = (i // W - ytop) / (ybot - ytop)
            bins[min(2, int(tt * 3))].append(pix[i])
        if all(len(b) >= 2 for b in bins):
            meds = [_median(_top_half(b, dist_bg)) for b in bins]
            if max(_cdist(meds[a], meds[b]) for a in range(3) for b in range(3)) >= 30:
                grad = [[0, _to_hex(meds[0])], [0.5, _to_hex(meds[1])], [1, _to_hex(meds[2])]]
    gh = gb[3] - (2 * stroke_w if stroke else 0)
    # palette of the strokes (fill, outline, shadow...): frequent mask colors far from the background
    from collections import Counter
    qc = Counter()
    qacc = {}
    for i in G:
        c = pix[i]
        if c[3] < 96 or (not transparent_bg and _cdist(c, bgc) < 40):
            continue
        q = (c[0] >> 4, c[1] >> 4, c[2] >> 4)
        qc[q] += 1
        qacc.setdefault(q, []).append(c)
    palette = [_to_hex(_median(qacc[q])) for q, k in qc.most_common(6) if k >= max(3, len(G) // 30)]
    res['palette'] = palette
    res.update(fill=_to_hex(fill), stroke=_to_hex(stroke) if stroke else None, stroke_w=stroke_w, grad=grad,
               glyph_box=gb, glyph_h=round(gh, 1))
    return res


def sample_colors(img, box):
    """Compatibility: (fill, stroke) as RGBA tuples."""
    a = analyze(img, box)
    return (_hex(a['fill']) if a['fill'] else (255, 255, 255, 255)), (_hex(a['stroke']) if a['stroke'] else None)


# ------------------------------------------------------------------------------------------- erasing
def _ring(img, box):
    x, y, w, h = box
    W, H = img.size
    px = img.load()
    out = []
    for xx in range(x - 1, x + w + 1):
        for yy in (y - 1, y + h):
            if 0 <= xx < W and 0 <= yy < H:
                out.append(px[xx, yy])
    for yy in range(y, y + h):
        for xx in (x - 1, x + w):
            if 0 <= xx < W and 0 <= yy < H:
                out.append(px[xx, yy])
    return out


def erase(img, box, mode, keep=None, grow=1, thr=None, bg=None):
    """Erases the text of box (or list of boxes) according to mode. Returns (pixels touched, coverage)."""
    if mode in (None, 'none', ''):
        return 0, 0.0
    rects = _rects(box)
    W, H = img.size
    keep = _rects(keep)
    saved = [(r, img.crop((r[0], r[1], r[0] + r[2], r[1] + r[3]))) for r in keep]
    n = 0
    cover = 1.0
    if mode in ('inpaint', 'diffuse'):
        region = _region_for(img, rects)
        unk = _unknown_mask(region, rects, keep)
        inpaint(img, region, unk)
        n = sum(r[2] * r[3] for r in rects)
    elif mode.startswith('glyph'):
        bgc = _bg_param(img, rects, keep, bg)
        region, m, _bg = glyph_mask(img, rects, keep, thr, bg=bg)
        unk = _unknown_mask(region, rects, keep)
        area = sum(1 for v in _pixels(unk) if v)
        cover = sum(1 for v in _pixels(m) if v) / max(1, area)
        if grow:
            m = _dilate(m, grow)
            m = ImageChops.multiply(m, unk)
        m = m.point(lambda v: 255 if v else 0)
        n = sum(1 for v in _pixels(m) if v)
        if mode == 'glyph:transparent':
            img.paste(Image.new('RGBA', m.size, (0, 0, 0, 0)), region[:2], m)
        elif mode == 'glyph:bg':
            if bgc is None:
                bgc = mode_color(img, rects, keep)
            img.paste(Image.new('RGBA', m.size, bgc), region[:2], m)
        elif mode in ('glyph', 'glyph:inpaint'):
            inpaint(img, region, m)
        else:
            raise ValueError(f'unknown erase: {mode}')
    else:
        px = img.load()
        for r in rects:
            cr = _clip(r, W, H)
            if not cr:
                continue
            x, y = cr[0], cr[1]
            w, h = cr[2] - cr[0], cr[3] - cr[1]
            n += w * h
            if mode == 'transparent':
                img.paste(Image.new('RGBA', (w, h), (0, 0, 0, 0)), (x, y))
            elif mode == 'hfill':
                for yy in range(y, y + h):
                    a = px[x - 1, yy] if x - 1 >= 0 else px[min(W - 1, x + w), yy]
                    b = px[x + w, yy] if x + w < W else a
                    for i, xx in enumerate(range(x, x + w)):
                        t = (i + 0.5) / w
                        px[xx, yy] = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(4))
            elif mode == 'vfill':
                for xx in range(x, x + w):
                    a = px[xx, y - 1] if y - 1 >= 0 else px[xx, min(H - 1, y + h)]
                    b = px[xx, y + h] if y + h < H else a
                    for i, yy in enumerate(range(y, y + h)):
                        t = (i + 0.5) / h
                        px[xx, yy] = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(4))
            elif mode.startswith('solid:'):
                if mode == 'solid:auto':
                    c = _bg_param(img, [r], keep, bg) or _median(_ring(img, (x, y, w, h)))
                else:
                    c = _hex(mode[6:])
                img.paste(Image.new('RGBA', (w, h), c), (x, y))
            elif mode.startswith('copy:'):
                sx, sy = (int(v) for v in mode[5:].split(','))
                patch = img.crop((sx, sy, sx + w, sy + h)).copy()
                img.paste(patch, (x, y))
            else:
                raise ValueError(f'unknown erase: {mode}')
    for r, im in saved:
        img.paste(im, (r[0], r[1]))
    return n, cover


def cut_warnings(img, rects, keep=None, thr=None, bg=None, erased=None):
    """Warnings if an erase box CUTS strokes of the text (leftovers would remain outside the box): pixels of the
    outer ring with the color of the strokes detected inside (fill, outline or the mask palette:
    shadows), different from the rest of that side and from the background that continues 3-6 px further out
    (bands/gradients), and that continue a stroke (or a non-background blend) on the inner edge of the box.
    erased = all the erased boxes of the spec (a ring that falls inside another erased box does not count).
    Heuristic: confirm in the detail view."""
    out = []
    W, H = img.size
    keep = _rects(keep)
    skip = keep + _rects(erased)
    px = img.load()
    for r in _rects(rects):
        x, y, w, h = r
        try:
            an = analyze(img, [r], keep, thr, bg)
        except Exception:
            continue
        if an['n'] < 4 or not an['fill']:
            continue
        base_cols = [_hex(an['fill'])] + ([_hex(an['stroke'])] if an['stroke'] else [])
        pal = [_hex(c) for c in an.get('palette', [])]           # shadows/outlines of another color

        def glyphlike(c, tol, gcols):
            return c[3] >= 96 and min(_cdist(c, g) for g in gcols) < tol

        sides = {}
        for (side, pts, inn) in (('left', [(x - 1, yy) for yy in range(y, y + h)], (1, 0)),
                                 ('right', [(x + w, yy) for yy in range(y, y + h)], (-1, 0)),
                                 ('top', [(xx, y - 1) for xx in range(x, x + w)], (0, 1)),
                                 ('bottom', [(xx, y + h) for xx in range(x, x + w)], (0, -1))):
            pts = [p for p in pts if 0 <= p[0] < W and 0 <= p[1] < H
                   and not any(k[0] <= p[0] < k[0] + k[2] and k[1] <= p[1] < k[1] + k[3] for k in skip)]
            if not pts:
                continue
            med = _median([px[p] for p in pts])
            # stroke colors of this side: fill/outline + palette, except those similar to this side's background
            gcols = base_cols + [c for c in pal if _cdist(c, med) >= 40]

            def notbg(c):
                return _cdist(c, med) + abs(c[3] - med[3]) > 50

            cnt = 0
            for p in pts:
                c = px[p]
                ip = (p[0] + inn[0], p[1] + inn[1])
                if not (0 <= ip[0] < W and 0 <= ip[1] < H):
                    continue
                # the same color 3 and 6 px further out = band or gradient of the background (buttons), not a cut stroke
                q3 = (p[0] - 2 * inn[0], p[1] - 2 * inn[1])
                q6 = (p[0] - 5 * inn[0], p[1] - 5 * inn[1])
                if (0 <= q6[0] < W and 0 <= q6[1] < H and _cdist(px[q3], c) + abs(px[q3][3] - c[3]) < 24
                        and _cdist(px[q6], c) + abs(px[q6][3] - c[3]) < 24):
                    continue
                # outside: stroke color and not background; inside (inner edge): stroke or blend (not background)
                if glyphlike(c, 45, gcols) and notbg(c) and (glyphlike(px[ip], 60, gcols) or notbg(px[ip])):
                    cnt += 1
            if cnt >= 3:
                sides[side] = cnt
        if sides:
            out.append(f'box {list(r)} seems to cut strokes of the original text (shadow/outline included) '
                       f'({", ".join(f"{s}: {c} px" for s, c in sides.items())}): look at that side in the detail; '
                       f'if leftovers remain, widen erase_box 1-2 px towards that side; otherwise ignore the warning')
    return out


# ------------------------------------------------------------------------------------------- text
def _stops(spec):
    if isinstance(spec, dict):
        if 'stops' in spec:
            st = [(float(t), _hex(c)) for t, c in spec['stops']]
        else:
            st = [(0.0, _hex(spec['top'])), (1.0, _hex(spec['bottom']))]
            if 'mid' in spec:
                st.insert(1, (float(spec.get('mid_at', 0.5)), _hex(spec['mid'])))
        return sorted(st, key=lambda s: s[0])
    return [(0.0, spec), (1.0, spec)]


def _interp(stops, t):
    if t <= stops[0][0]:
        return stops[0][1]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return tuple(int(round(c0[k] + (c1[k] - c0[k]) * u)) for k in range(4))
    return stops[-1][1]


def _paint(spec, size, bands):
    """RGBA image of the given size painted with spec (color or per-line vertical gradient)."""
    W, H = size
    if not isinstance(spec, dict):
        return Image.new('RGBA', size, spec)
    st = _stops(spec)
    col = Image.new('RGBA', (1, H))
    cp = col.load()
    for y in range(H):
        yt, yb = min(bands, key=lambda b: abs((b[0] + b[1]) / 2 - y))
        t = min(1.0, max(0.0, (y - yt) / max(1.0, yb - yt)))
        cp[0, y] = _interp(st, t)
    return col.resize((W, H), Image.NEAREST)


def _resolve_color(v, auto):
    if v == 'auto':
        return auto
    if isinstance(v, dict):
        if 'stops' in v:
            return {'stops': [[t, _hex(c)] for t, c in v['stops']]}
        out = {k: (_hex(c) if k in ('top', 'bottom', 'mid') else c) for k, c in v.items()}
        return out
    return _hex(v) if v is not None else None


class Layout:
    """Measurements of the text block at a given em size (in SS pixels)."""

    def __init__(self, it, entry, size, lines):
        self.entry = entry
        self.size = size
        self.lines = lines
        self.font = get_font(entry, size * SS)
        self.track = float(it.get('tracking', 0) or 0) * SS
        lead = it.get('leading')
        self.pitch = (float(lead) if lead else 1.2) * size * SS + float(it.get('line_gap', 0) or 0) * SS
        self.cap = cap_ratio(entry) * size * SS
        self.align = it.get('align', 'center')
        self.info = []
        for ln in lines:
            pos = []
            if self.track and len(ln) > 1:
                for i, ch in enumerate(ln):
                    pos.append((self.font.getlength(ln[:i]) + i * self.track, ch))
            else:
                pos.append((0.0, ln))
            l = t = r = b = None
            for x, s in pos:
                if not s.strip():
                    continue
                bb = self.font.getbbox(s, anchor='ls')
                l = x + bb[0] if l is None else min(l, x + bb[0])
                t = bb[1] if t is None else min(t, bb[1])
                r = x + bb[2] if r is None else max(r, x + bb[2])
                b = bb[3] if b is None else max(b, bb[3])
            if l is None:
                l = t = r = b = 0
            self.info.append((pos, l, t, r, b))
        self.ink_w = max((i[3] - i[1]) for i in self.info) if self.info else 0
        n = len(lines)
        self.top = min(i[2] for i in self.info) if self.info else 0
        self.bottom = (n - 1) * self.pitch + (self.info[-1][4] if self.info else 0)
        self.ink_h = self.bottom - self.top

    def line_x(self, k):
        pos, l, t, r, b = self.info[k]
        w = r - l
        if self.align == 'left':
            return -l
        if self.align == 'right':
            return self.ink_w - r
        return (self.ink_w - w) / 2 - l


def _effects(it, strokes, shadows):
    outer = sum(s[1] for s in strokes) + float(it.get('embolden', 0) or 0) + 1.5 * float(it.get('blur', 0) or 0)
    sx = sy = 0.0
    ext = it.get('extrude')
    if ext:
        sx = max(sx, abs(float(ext.get('dx', 0))))
        sy = max(sy, abs(float(ext.get('dy', 2))))
    for sh in shadows:
        sx = max(sx, abs(sh.get('dx', 0)) + 2 * sh.get('blur', 0) + (abs(float(ext.get('dx', 0))) if ext else 0))
        sy = max(sy, abs(sh.get('dy', 0)) + 2 * sh.get('blur', 0) + (abs(float(ext.get('dy', 2))) if ext else 0))
    return outer, sx, sy


def _fit(it, entry, lines, aw, ah, strokes, shadows):
    """Em size (px) and condensing so that the block fits in aw x ah."""
    skew = abs(float(it.get('italic_skew', 0) or 0))
    outer, shx, shy = _effects(it, strokes, shadows)
    min_sx = float(it.get('min_scale_x', 0.85))
    fixed_sx = it.get('scale_x')

    def dims(s, sx=1.0):
        L = Layout(it, entry, s, lines)
        tw = L.ink_w / SS
        th = L.ink_h / SS
        W = tw * sx + skew * (th + 2 * outer) + 2 * outer + shx
        Hh = th + 2 * outer + shy
        return W, Hh, tw, th

    size = float(it.get('size') or 0)
    cap = it.get('cap')
    if not size and cap and cap != 'jp':
        size = float(cap) / cap_ratio(entry)
    if not size:
        lo, hi = 2.0, max(4.0, ah * 3.0)
        sx_try = float(fixed_sx) if fixed_sx else min_sx
        for _ in range(22):
            mid = (lo + hi) / 2
            W, Hh, _, _ = dims(mid, sx_try)
            if Hh <= ah + 0.01 and W <= aw + 0.01:
                lo = mid
            else:
                hi = mid
        size = lo
        if it.get('max_cap'):
            size = min(size, float(it['max_cap']) / cap_ratio(entry))
        if it.get('min_size'):
            size = max(size, float(it['min_size']))
    W1, Hh, tw, th = dims(size, 1.0)
    if fixed_sx:
        sx = float(fixed_sx)
    else:
        extra = W1 - tw
        sx = min(1.0, max(0.05, (aw - extra) / tw)) if tw > 0 else 1.0
    return size, sx


def _choose_lines(it, entry, text, aw, ah, strokes, shadows):
    lines = text.split('\n')
    if not it.get('wrap') or len(lines) > 1 or ' ' not in text:
        return lines
    words = text.split(' ')
    cands = [[text]]
    for i in range(1, len(words)):
        cands.append([' '.join(words[:i]), ' '.join(words[i:])])
    if len(words) >= 3:
        for i in range(1, len(words)):
            for j in range(i + 1, len(words)):
                cands.append([' '.join(words[:i]), ' '.join(words[i:j]), ' '.join(words[j:])])
    best = None
    for c in cands:
        s, sx = _fit(it, entry, c, aw, ah, strokes, shadows)
        lens = [len(x) for x in c]
        balance = (max(lens) - min(lens)) / max(1, sum(lens))      # 0 = equal lines
        score = s * min(1.0, sx / 0.9) - 0.25 * (len(c) - 1) - 0.3 * balance
        if best is None or score > best[0] + 1e-6:
            best = (score, c)
    return best[1]


def _norm_shadows(sh):
    if not sh:
        return []
    out = []
    for s in (sh if isinstance(sh, list) else [sh]):
        s = dict(s)
        s.setdefault('dx', 1)
        s.setdefault('dy', 1)
        s.setdefault('blur', 0)
        out.append(s)
    return out


def draw_text(img, it, box, fill, strokes, shadows, report):
    """Draws it['text'] in box with fill fill and outlines strokes [(color, w)], shadows shadows."""
    text = it.get('text', '')
    x, y, w, h = box
    pl, pt, pr, pb = _pads(it.get('pad', 1))
    aw, ah = max(1.0, w - pl - pr), max(1.0, h - pt - pb)
    entry = _font_entry(it)
    rot = int(it.get('rotate', 0) or 0) % 360
    if rot in (90, 270):                        # vertical text: the text width goes in the box height
        aw, ah = ah, aw
    lines = _choose_lines(it, entry, text, aw, ah, strokes, shadows)
    size, sx = _fit(it, entry, lines, aw, ah, strokes, shadows)
    if rot in (90, 270):
        aw, ah = ah, aw
    L = Layout(it, entry, size, lines)
    skew = float(it.get('italic_skew', 0) or 0)
    outer, shx, shy = _effects(it, strokes, shadows)
    emb = float(it.get('embolden', 0) or 0)
    # SS canvas with margins for outlines, shadows and slant
    M = int(math.ceil((outer + max(shx, shy) + 3) * SS + abs(skew) * (L.ink_h + 2 * outer * SS)))
    cw = int(math.ceil(L.ink_w + 2 * M))
    ch = int(math.ceil(L.ink_h + 2 * M))
    X0, Y0 = M, M - L.top                       # origin (ink x 0, baseline of the 1st line)
    fm = Image.new('L', (cw, ch), 0)
    d = ImageDraw.Draw(fm)
    for k, (pos, l, t, r, b) in enumerate(L.info):
        lx = X0 + L.line_x(k)
        by = Y0 + k * L.pitch
        for px_, s in pos:
            d.text((lx + px_, by), s, font=L.font, fill=255, anchor='ls')
    bands = [(Y0 + k * L.pitch - L.cap, Y0 + k * L.pitch) for k in range(len(lines))]
    # horizontal condensing (letters only; outlines are computed afterwards -> uniform thickness)
    if abs(sx - 1.0) > 1e-3:
        nw = max(1, int(round(cw * sx)))
        fm = fm.resize((nw, ch), Image.LANCZOS)
        X0 *= nw / cw
        cw = nw
    # slant (pivot: center of the capitals band)
    if skew:
        yc = (bands[0][0] + bands[-1][1]) / 2
        fm = fm.transform(fm.size, Image.AFFINE, (1, skew, -skew * yc, 0, 1, 0), Image.BICUBIC)
    if emb:
        fm = _dilate_frac(fm, emb * SS)
    # 3D extrusion: sweep of the fill mask up to (dx, dy); outlines surround face + depth
    ext = it.get('extrude')
    body = fm
    if ext:
        edx, edy = float(ext.get('dx', 0)) * SS, float(ext.get('dy', 2)) * SS
        n = max(1, int(round(max(abs(edx), abs(edy)))))
        body = fm
        for k in range(1, n + 1):
            body = ImageChops.lighter(body, ImageChops.offset(fm, int(round(edx * k / n)), int(round(edy * k / n))))
    # accumulated outline masks (from inside out)
    smasks = []
    cur = body
    acc = 0.0
    for col, sw in strokes:
        acc += sw
        cur = _dilate_frac(body, acc * SS)
        smasks.append((col, cur))
    sil = cur
    layer = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    for sh in shadows:
        sm = ImageChops.offset(sil, int(round(sh['dx'] * SS)), int(round(sh['dy'] * SS)))
        if sh.get('blur'):
            sm = sm.filter(ImageFilter.GaussianBlur(sh['blur'] * SS))
        op = float(sh.get('opacity', sh.get('alpha', 1.0)))
        if op < 1:
            sm = sm.point(lambda v, op=op: int(v * op))
        layer.alpha_composite(_masked(_paint(_resolve_color(sh.get('color', '#000000'), (0, 0, 0, 255)), (cw, ch), bands), sm))
    for col, msk in reversed(smasks):
        layer.alpha_composite(_masked(_paint(col, (cw, ch), bands), msk))
    if ext:
        layer.alpha_composite(_masked(_paint(_resolve_color(ext.get('color', '#000000'), None), (cw, ch), bands), body))
    layer.alpha_composite(_masked(_paint(fill, (cw, ch), bands), fm))
    if it.get('blur'):                          # blur of the whole label (glow/shine sprites)
        # in premultiplied RGBA ('RGBa'): otherwise the RGB mixes with the black of the transparent area and the glow
        # ends up
        # with dark edges (gray halo on light backgrounds)
        layer = layer.convert('RGBa').filter(ImageFilter.GaussianBlur(float(it['blur']) * SS)).convert('RGBA')
    op = float(it.get('opacity', 1.0))
    if op < 1:
        a = layer.getchannel('A').point(lambda v: int(v * op))
        layer.putalpha(a)
    if it.get('dark_edges'):                    # RGB x alpha: dark edges, like some original glows
        a = layer.getchannel('A')
        layer = Image.merge('RGBA', [ImageChops.multiply(c, a) for c in layer.split()[:3]] + [a])
    if rot:                                     # 90 = rotates left (reads bottom to top); 270 = right
        layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
        cw, ch = layer.size
    # ink box (without the diffuse tail of the shadows)
    ink = layer.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox() or layer.getchannel('A').getbbox()
    if not ink:
        report.append(f'WARNING: the text {text!r} produced no visible pixels (opacity/transparent colors?)')
        return
    il, itp, ir, ib = ink
    # position in SS px of the texture
    ax0, ay0 = (x + pl) * SS, (y + pt) * SS
    ax1, ay1 = (x + w - pr) * SS, (y + h - pb) * SS
    al, va = it.get('align', 'center'), it.get('valign', 'middle')
    if al == 'left':
        ox = ax0 - il
    elif al == 'right':
        ox = ax1 - ir
    else:
        ox = (ax0 + ax1) / 2 - (il + ir) / 2
    capc = (bands[0][0] + bands[-1][1]) / 2 if not rot else (itp + ib) / 2
    if it.get('baseline') is not None and not rot:
        oy = float(it['baseline']) * SS - Y0
    elif va == 'top':
        oy = ay0 - itp
    elif va == 'bottom':
        oy = ay1 - ib
    else:
        oy = (ay0 + ay1) / 2 - capc
        if oy + ib > ay1:                       # keep descenders from sticking out
            oy = max(ay1 - ib, ay0 - itp)
        if oy + itp < ay0:
            oy = min(ay0 - itp, ay1 - ib) if (ib - itp) <= (ay1 - ay0) else (ay0 + ay1) / 2 - (itp + ib) / 2
    ox += float(it.get('dx', 0)) * SS
    oy += float(it.get('dy', 0)) * SS
    if it.get('snap', True):
        ox = round((ox + il) / SS) * SS - il
        oy = (round((oy + Y0) / SS) * SS - Y0) if not rot else (round((oy + itp) / SS) * SS - itp)
    ox, oy = int(round(ox)), int(round(oy))
    # destination region (texture px), aligned to the SS grid
    W, H = img.size
    rx0 = max(0, (ox + il) // SS - 1)
    ry0 = max(0, (oy + itp) // SS - 1)
    rx1 = min(W, -(-(ox + ir) // SS) + 1)
    ry1 = min(H, -(-(oy + ib) // SS) + 1)
    # the diffuse shadow may extend a bit further
    rx0 = max(0, rx0 - int(shx) - 1); ry0 = max(0, ry0 - int(shy) - 1)
    rx1 = min(W, rx1 + int(shx) + 1); ry1 = min(H, ry1 + int(shy) + 1)
    if rx1 <= rx0 or ry1 <= ry0:
        report.append('WARNING: the text falls outside the texture')
        return
    canvas = Image.new('RGBA', ((rx1 - rx0) * SS, (ry1 - ry0) * SS), (0, 0, 0, 0))
    dx_, dy_ = ox - rx0 * SS, oy - ry0 * SS
    sx0, sy0 = max(0, -dx_), max(0, -dy_)
    sx1, sy1 = min(cw, canvas.size[0] - dx_), min(ch, canvas.size[1] - dy_)
    if sx1 > sx0 and sy1 > sy0:
        canvas.alpha_composite(layer.crop((sx0, sy0, sx1, sy1)), (dx_ + sx0, dy_ + sy0))
    small = canvas.resize((rx1 - rx0, ry1 - ry0), Image.BOX)
    crisp = float(it.get('crisp', 0) or 0)
    if crisp > 0:
        _crisp(small, crisp, [fill] + [c for c, _ in strokes])
    img.alpha_composite(small, (rx0, ry0))
    # report
    fin = ((ox + il) / SS, (oy + itp) / SS, (ox + ir) / SS, (oy + ib) / SS)
    capp = L.cap / SS
    report.append(f'text {lines!r}: font={it.get("font", "bold")} em={size:.1f}px caps={capp:.1f}px '
                  f'condensed={sx:.2f} ink=[{fin[0]:.1f},{fin[1]:.1f} -> {fin[2]:.1f},{fin[3]:.1f}]')
    over = []
    if fin[0] < x - 0.6: over.append('left')
    if fin[2] > x + w + 0.6: over.append('right')
    if fin[1] < y - 0.6: over.append('top')
    if fin[3] > y + h + 0.6: over.append('bottom')
    if over:
        report.append(f'WARNING: the text sticks out of the box on: {", ".join(over)}')
    if sx < 0.62:
        report.append(f'WARNING: excessive condensing ({sx:.2f}); shorten the text, use a narrow font or more lines')
    if _is_pixel_font(entry) and not it.get('scale_x') and abs(sx - 1.0) > 0.005:
        report.append(f'WARNING: condensed pixel font ({sx:.2f}): it breaks its grid and comes out blurry; '
                      f'widen the box '
                      f'(the outline counts too), shorten or set "scale_x": 1')
    if capp < 5.5 and text.strip():
        report.append(f'WARNING: very small letters (capitals {capp:.1f}px); may be unreadable')


def _crisp(im, k, paints):
    """Sharpness for small letters: sharper edge alpha and intermediate colors (fill/outline blend)
    pushed toward the nearest reference color. k in 0..1. Improves legibility and ETC1/RGBA4 compression."""
    refs = [c for c in paints if c is not None and not isinstance(c, dict)]
    gain = 1.0 + 3.0 * k
    px = im.load()
    W, H = im.size
    for yy in range(H):
        for xx in range(W):
            r, g, b, a = px[xx, yy]
            if a == 0:
                continue
            a2 = int(min(255, max(0, (a - 128) * gain + 128)))
            if refs:
                ref = min(refs, key=lambda c: (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2)
                r = int(round(r + k * (ref[0] - r)))
                g = int(round(g + k * (ref[1] - g)))
                b = int(round(b + k * (ref[2] - b)))
            px[xx, yy] = (r, g, b, a2)


def _masked(paint, mask):
    out = paint.copy()
    a = ImageChops.multiply(paint.getchannel('A'), mask)
    out.putalpha(a)
    return out


# ------------------------------------------------------------------------------------------- items
STYLES = {
    # Presets per family (see translation-work/tex/LECCIONES.md). An item uses them with "style": "name";
    # the item's keys take priority.
    'boton': {'erase': 'glyph', 'font': 'compact-rounded-heavy', 'fill': 'auto', 'stroke': 'auto', 'stroke_w': 1,
              'min_scale_x': 0.75},
    'menu': {'erase': 'glyph', 'font': 'sf-rounded-heavy', 'fill': 'auto', 'stroke': 'auto', 'stroke_w': 1.2,
             'min_scale_x': 0.75, 'align': 'left', 'pad': 0, 'crisp': 0.4},
    'hud': {'erase': 'glyph', 'font': 'din', 'fill': 'auto', 'stroke': 'auto', 'stroke_w': 1, 'pad': 0,
            'crisp': 0.4},
    'hud_mini': {'erase': 'glyph', 'font': 'tahoma', 'fill': 'auto', 'stroke': 'auto', 'stroke_w': 1, 'pad': 0,
                 'crisp': 0.4},
    'mapa': {'erase': 'glyph', 'font': 'hiragino-heavy', 'fill': '#FFFFFF', 'stroke': '#000000C0', 'stroke_w': 1.5,
             'pad': 0, 'crisp': 0.2},
    'cartel': {'erase': 'transparent', 'font': 'sf-black-italic', 'pad': 0, 'min_scale_x': 0.75},
    # Medaforce posters (battle/tex/mfNNN): like the Japanese, dark inner border, thin light line, outer gray
    # and 5 px depth (reviewed on 8-oct against the 60 posters; colors measured on the JP)
    'medafuerza': {
        'erase': 'transparent', 'font': 'sf-black-italic', 'italic_skew': 0.12, 'pad': 0, 'min_scale_x': 0.7,
        'fill': {'stops': [[0, '#1450C8'], [0.12, '#1C86F2'], [0.45, '#46C2FF'], [0.62, '#B8EEFF'], [1, '#EAFFFF']]},
        'extrude': {'dx': 1, 'dy': 5, 'color': '#020C2A'},
        'strokes': [{'color': '#0A2E86', 'w': 1.5}, {'color': '#DDE6F2', 'w': 1}, {'color': '#7C8898', 'w': 0.8}],
        'shadow': {'dx': 1, 'dy': 1, 'color': '#000000', 'opacity': 0.45, 'blur': 1}},
    'medafuerza_oro': {
        'erase': 'transparent', 'font': 'sf-black-italic', 'italic_skew': 0.12, 'pad': 0, 'min_scale_x': 0.7,
        'fill': {'stops': [[0, '#D86A00'], [0.15, '#F59A10'], [0.45, '#FFCB3A'], [0.7, '#FCDC58'], [1, '#F8EC96']]},
        'extrude': {'dx': 1, 'dy': 5, 'color': '#3A1A00'},
        'strokes': [{'color': '#7A3A00', 'w': 1.5}, {'color': '#F2ECDD', 'w': 1}, {'color': '#8A8070', 'w': 0.8}],
        'shadow': {'dx': 1, 'dy': 1, 'color': '#000000', 'opacity': 0.45, 'blur': 1}},
    'medafuerza_morado': {
        'erase': 'transparent', 'font': 'sf-black-italic', 'italic_skew': 0.12, 'pad': 0, 'min_scale_x': 0.7,
        'fill': {'stops': [[0, '#8E2AD0'], [0.15, '#9B54ED'], [0.3, '#AC68FB'], [0.42, '#B970F6'], [0.6, '#A75BE8'],
                           [0.75, '#9A3ADC'], [1, '#9838DA']]},
        'extrude': {'dx': 1, 'dy': 5, 'color': '#1E0636'},
        'strokes': [{'color': '#4A0C96', 'w': 1.5}, {'color': '#ECE2F4', 'w': 1}, {'color': '#84788E', 'w': 0.8}],
        'shadow': {'dx': 1, 'dy': 1, 'color': '#000000', 'opacity': 0.45, 'blur': 1}},
    'medafuerza_verde': {
        'erase': 'transparent', 'font': 'sf-black-italic', 'italic_skew': 0.12, 'pad': 0, 'min_scale_x': 0.7,
        'fill': {'stops': [[0, '#08A060'], [0.15, '#0ABF72'], [0.3, '#15D48B'], [0.5, '#2BDCA1'], [0.7, '#50EBBE'],
                           [1, '#9AF4D8']]},
        'extrude': {'dx': 1, 'dy': 5, 'color': '#002414'},
        'strokes': [{'color': '#005A2C', 'w': 1.5}, {'color': '#E2F2EA', 'w': 1}, {'color': '#7C8C84', 'w': 0.8}],
        'shadow': {'dx': 1, 'dy': 1, 'color': '#000000', 'opacity': 0.45, 'blur': 1}},
}


def expand_items(spec):
    """Applies defaults/styles and repeat -> list of concrete items."""
    styles = dict(STYLES)
    styles.update(spec.get('styles', {}))
    out = []
    for raw in spec.get('items', []):
        if 'copy' in raw:
            out.append(dict(raw))
            continue
        # priority: defaults < style(s) < item keys
        it = dict(spec.get('defaults', {}))
        st = raw.get('style', it.get('style'))
        for s in ([st] if isinstance(st, str) else (st or [])):
            if s not in styles:
                raise ValueError(f'unknown style: {s} (available: {", ".join(styles)})')
            it.update(styles[s])
        it.update(raw)
        offs = [[0, 0]] + [list(o) for o in it.get('repeat', [])]
        for dx, dy in offs:
            c = dict(it)
            for key in ('box', 'erase_box', 'sample_box', 'keep', 'segments'):
                if key == 'box' and c.get('segments'):     # with segments, box is in strip coordinates
                    continue
                if key in c and c[key]:
                    rs = _rects(c[key])
                    moved = [[r[0] + dx, r[1] + dy, *r[2:]] for r in rs]
                    c[key] = moved[0] if (key in ('box', 'sample_box') or (isinstance(c[key][0], (int, float)))) else moved
            if c.get('baseline') is not None:
                c['baseline'] = c['baseline'] + dy
            c.pop('repeat', None)
            out.append(c)
    return out


def _segments(it):
    """Segments of an item -> ([(x, y, w, h)] in the texture, [(px, py)] in the composed strip, width, height).
    Forms: [x, y, w, h] (in a row, same height) or [x, y, w, h, px, py] (explicit position in the strip, e.g. the one
    given by `sprites --compose`)."""
    segs = _rects(it.get('segments'))
    if not segs:
        return [], [], 0, 0
    if any(len(r) == 6 for r in segs):
        if not all(len(r) == 6 for r in segs):
            raise ValueError('"segments": either all with position [x, y, w, h, px, py] or none')
        pos = [(r[4], r[5]) for r in segs]
    else:
        if len({r[3] for r in segs}) != 1:
            raise ValueError('all "segments" in a row must have the same height (or give positions px, py)')
        pos, acc = [], 0
        for r in segs:
            pos.append((acc, 0))
            acc += r[2]
    rects = [tuple(r[:4]) for r in segs]
    SW = max(px + r[2] for r, (px, _py) in zip(rects, pos))
    SH = max(py + r[3] for r, (_px, py) in zip(rects, pos))
    return rects, pos, SW, SH


def _erase_rects(it):
    """Erase boxes of an item: erase_box, or the segments, or the box."""
    return _rects(it.get('erase_box')) or _segments(it)[0] or [tuple(it['box'])]


def _text_rects(it):
    """Boxes (texture coordinates) where an item's text goes: the segments or the box."""
    return _segments(it)[0] or ([tuple(it['box'])] if it.get('box') else [])


def draw_item(img, it, ctx=None):
    """Applies an item (erase + write). ctx: {'jp': JP image, 'base0': untouched base}. Returns a report."""
    ctx = ctx or {}
    report = []
    if 'copy' in it:
        sx, sy, w, h = it['copy']
        tx, ty = it['to']
        src = ctx.get('base0', img)
        patch = src.crop((sx, sy, sx + w, sy + h))
        if it.get('blend') == 'over':
            img.alpha_composite(patch, (tx, ty))
        else:
            img.paste(patch, (tx, ty))
        report.append(f'copy [{sx},{sy},{w},{h}] -> [{tx},{ty}]')
        return report
    segs, spos, SW, SH = _segments(it)
    if segs:
        # label split into several strips of the texture that the screen (or the model) composes: "box" is in
        # coordinates of the composed strip (by default, the whole strip)
        box = [int(round(v)) for v in it['box']] if it.get('box') else [0, 0, SW, SH]
    elif it.get('box'):
        box = [int(round(v)) for v in it['box']]
    elif _rects(it.get('erase_box')):              # item without "box": its (first) erase box
        box = list(_rects(it.get('erase_box'))[0])
    else:
        raise ValueError(f'item without "box", "erase_box" or "segments": {json.dumps(it, ensure_ascii=True)[:120]}')
    text = it.get('text', '') or ''
    if any(ord(ch) > 126 or (ord(ch) < 32 and ch != '\n') for ch in text):
        report.append(f'WARNING: text with non-ASCII characters: {text!r}')
    erase_rects = _rects(it.get('erase_box')) or segs or [tuple(box)]
    keep = _rects(it.get('keep'))
    fill = it.get('fill', 'auto')
    stroke = it.get('stroke', 'auto')
    strokes_spec = it.get('strokes')
    need_auto = text and (fill in ('auto', 'auto-grad') or (stroke == 'auto' and not strokes_spec)
                          or it.get('stroke_w') == 'auto'
                          or it.get('cap') == 'jp'
                          or any(s.get('color') == 'auto' for s in (strokes_spec or [])))
    an = None
    if need_auto:
        sbox = _rects(it.get('sample_box')) or erase_rects
        src_name = it.get('sample_from', 'jp')
        srcimg = ctx.get('jp') if (src_name == 'jp' and ctx.get('jp') is not None) else img
        an = analyze(srcimg, sbox, keep, it.get('thr'), it.get('bg'))
        if an['n'] < 4 and srcimg is not img:
            an = analyze(img, sbox, keep, it.get('thr'), it.get('bg'))
        if an['n'] < 4:
            report.append('WARNING: no original text detected in the sampling box; default colors')
        report.append(f'sampling ({src_name}): background={an["bg"]} fill={an["fill"]} outline={an["stroke"]} '
                      f'thickness={an["stroke_w"]} gradient={json.dumps(an["grad"]) if an["grad"] else "no"} '
                      f'strokes={an["glyph_box"]} height={an["glyph_h"]}')
    # colors
    if fill == 'auto':
        fill_c = _hex(an['fill']) if an and an['fill'] else (255, 255, 255, 255)
    elif fill == 'auto-grad':
        if an and an['grad']:
            fill_c = {'stops': [[t, _hex(c)] for t, c in an['grad']]}
        else:
            fill_c = _hex(an['fill']) if an and an['fill'] else (255, 255, 255, 255)
    else:
        fill_c = _resolve_color(fill, None)
    strokes = []
    if strokes_spec:
        for i, s in enumerate(strokes_spec):
            col = s.get('color', '#000000')
            if col == 'auto':
                col = an['stroke'] if an and an['stroke'] else '#000000'
            strokes.append((_resolve_color(col, None), float(s.get('w', 1))))
    else:
        if stroke == 'auto':
            sc = _hex(an['stroke']) if an and an['stroke'] else None
        else:
            sc = _resolve_color(stroke, None)
        sw = it.get('stroke_w', 1 if sc else 0)
        if sw == 'auto':
            sw = an['stroke_w'] if an and an['stroke_w'] else 1
        if sc is not None and float(sw) > 0:
            strokes.append((sc, float(sw)))
    shadows = _norm_shadows(it.get('shadow'))
    it2 = dict(it)
    if it.get('cap') == 'jp':
        it2['cap'] = round(0.8 * an['glyph_h'], 1) if an and an['glyph_h'] else None
        report.append(f'cap "jp" -> {it2["cap"]} px')
    # erase
    mode = it.get('erase', 'transparent')
    if mode not in (None, 'none', ''):
        n, cover = erase(img, erase_rects, mode, keep, int(it.get('grow', 1)), it.get('thr'), it.get('bg'))
        if mode.startswith('glyph') and cover > 0.75:
            report.append(f'WARNING: the "glyph" erase marked {int(cover * 100)}% of the box as stroke: perhaps the '
                          f'estimated background is not reliable (box stuck to lines/other things). Look at the detail; '
                          f'if leftovers remain, try "bg": "mode" or "bg": "#RRGGBBAA", or a somewhat looser box')
    if text and segs:
        strip = Image.new('RGBA', (SW, SH), (0, 0, 0, 0))
        for r, (px, py) in zip(segs, spos):
            strip.paste(img.crop((r[0], r[1], r[0] + r[2], r[1] + r[3])), (px, py))
        draw_text(strip, it2, box, fill_c, strokes, shadows, report)
        report.append(f'(segments: composed strip of {SW}x{SH}; each strip at '
                      f'{", ".join(f"({px},{py})" for px, py in spos)})')
        for r, (px, py) in zip(segs, spos):
            img.paste(strip.crop((px, py, px + r[2], py + r[3])), (r[0], r[1]))
    elif text:
        draw_text(img, it2, box, fill_c, strokes, shadows, report)
    return report


# ------------------------------------------------------------------------------------------- render
def _final_view(src_bytes, img):
    try:
        return C.roundtrip_image(src_bytes, img)
    except Exception:
        return img


def _zoom_rows(rel, items, jp, en, es, max_w=1500):
    """Detail rows (JP | EN | ES) around each label."""
    W, H = jp.size
    groups = []
    for it in items:
        rs = _rects(it.get('erase_box')) + _text_rects(it)
        if 'copy' in it:
            rs = [tuple(it['copy']), (it['to'][0], it['to'][1], it['copy'][2], it['copy'][3])]
        for r in rs:
            g = [r[0] - 4, r[1] - 4, r[0] + r[2] + 4, r[1] + r[3] + 4]
            groups.append(g)
    def area(r):
        return max(0, r[2] - r[0]) * max(0, r[3] - r[1])

    merged = True
    while merged:                      # merge only crops that overlap a lot (same label) and are still small
        merged = False
        out = []
        for g in groups:
            for o in out:
                inter = [max(o[0], g[0]), max(o[1], g[1]), min(o[2], g[2]), min(o[3], g[3])]
                u = [min(o[0], g[0]), min(o[1], g[1]), max(o[2], g[2]), max(o[3], g[3])]
                if (area(inter) >= 0.5 * min(area(o), area(g))
                        and (u[2] - u[0]) <= 220 and (u[3] - u[1]) <= 90):
                    o[:] = u
                    merged = True
                    break
            else:
                out.append(list(g))
        groups = out
    rows = []
    for g in sorted(groups, key=lambda g: (g[1], g[0])):
        x0, y0, x1, y1 = max(0, g[0]), max(0, g[1]), min(W, g[2]), min(H, g[3])
        if x1 <= x0 or y1 <= y0:
            continue
        cw, chh = x1 - x0, y1 - y0
        npan = 3 if en is not None else 2
        z = max(2, min(12, int(min((max_w - 30 * npan) / (cw * npan), 420 / chh))))
        if z * cw * npan > max_w:          # too wide: vertical
            z = max(2, min(12, int(min((max_w - 30) / cw, 600 / (chh * npan)))))
            vertical = True
        else:
            vertical = False
        pans = [_grid(jp.crop((x0, y0, x1, y1)), z, f'JP [{x0},{y0}]', (x0, y0))]
        if en is not None:
            pans.append(_grid(en.crop((x0, y0, x1, y1)), z, 'EN', (x0, y0)))
        pans.append(_grid(es.crop((x0, y0, x1, y1)), z, 'ES (final)', (x0, y0)))
        rows.append(_stack(pans, vertical))
    return rows


def _norm_targets(spec, rel, tex):
    """Additional copies of a CGFX texture ("also": list of "rel" | "rel:texture" | {"rel", "tex"} | "auto")."""
    also = spec.get('also') or []
    if also == 'auto':
        return find_copies(rel, tex)
    out = []
    for a in also:
        if isinstance(a, dict):
            r, t = a['rel'], a.get('tex', tex)
        else:
            r, t = split_rel(a, tex)
        if (r, t) != (rel, tex) and (r, t) not in out:
            out.append((r, t))
    return out


def find_copies(rel, tex):
    """Other textures with the SAME pixels (level 0) in the CGFX models of the same RomFS folder: the same
    sign appears on several maps. -> [(rel, tex)] (without itself). Stored in translation-work/tex/cgfx/
    copies_cache.json (the Japanese base does not change)."""
    cache_p = WORK / 'cgfx' / 'copies_cache.json'
    key = f'{rel}:{tex}'
    try:
        cache = json.loads(cache_p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        cache = {}
    if key in cache:
        return [tuple(x) for x in cache[key]]
    data = jp_bytes(rel)
    t0 = G.get(data, tex)
    raw0 = data[t0['off']:t0['off'] + G.level_size(t0['w'], t0['h'], t0['fmt'])]
    pix0 = None
    folder = rel.rsplit('/', 1)[0] + '/'
    try:
        cands = [r for r in romfs.listdir(folder) if '/' not in r[len(folder):] and is_cgfx(r)]
    except FileNotFoundError:          # no ROM: what is extracted in archive/
        cands = sorted({folder + p.name for b in (UPD_TEX, ROM_EXTRACT) if (b / folder).is_dir()
                        for p in (b / folder).iterdir() if is_cgfx(p.name)})
    out = []
    for r in cands:
        d = jp_bytes(r)
        for t in G.textures(d):
            if (r, t['name']) == (rel, tex) or (t['w'], t['h']) != (t0['w'], t0['h']):
                continue
            raw = d[t['off']:t['off'] + G.level_size(t['w'], t['h'], t['fmt'])]
            same = raw == raw0 and t['fmt'] == t0['fmt']
            if not same and (t['fmt'] != t0['fmt'] or t['fmt'] in (0xC, 0xD)):
                if pix0 is None:
                    pix0 = G.decode(data, t0).tobytes()
                same = G.decode(d, t).tobytes() == pix0
            if same:
                out.append((r, t['name']))
    cache[key] = out
    cache_p.parent.mkdir(parents=True, exist_ok=True)
    cache_p.write_text(json.dumps(cache, indent=0), encoding='utf-8')
    return out


def _write_cgfx(targets, img, base0, out_dir=None):
    """Writes img into each (rel, texture) of targets, ACCUMULATING over data/romfs_tex_es/<rel> if it already
    exists (other textures of the same model already translated). Verifies: same size and only that texture's
    bytes change."""
    written = []
    for r, t in targets:
        orig = jp_bytes(r)
        if G.decode(orig, G.get(orig, t)).tobytes() != base0.tobytes():
            raise ValueError(f'{r}:{t} does not have the same pixels as the spec texture; remove it from "also"')
        out = (Path(out_dir) if out_dir else OUT_TEX) / r
        cur = out.read_bytes() if out.exists() else orig
        if len(cur) != len(orig):
            raise ValueError(f'{out} is not the same size as the original ({len(cur)} != {len(orig)}): delete it and '
                             f're-render all the specs of that model')
        new = G.replace(cur, t, img, orig=orig)
        bad = G.changed_outside(cur, new, G.get(orig, t))
        if bad or len(new) != len(orig):
            raise ValueError(f'{r}:{t}: the write would change bytes outside the texture {bad[:3]}; not written')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(new)
        written.append(f'{out} ({t})')
    return written


def _prepare(spec):
    """Starting images of a spec: base (JP or EN), JP and EN, bytes of the base file."""
    rel = spec['rel']
    tex = spec.get('tex')
    cgfx = is_cgfx(rel)
    if cgfx:
        _need_tex(rel, tex)
    base = spec.get('base') or ('en' if en_path(rel) else 'jp')
    if base == 'en' and not en_path(rel):
        raise ValueError(f'{rel}: no English version exists; use "base": "jp"')
    src_bytes = jp_bytes(rel) if base == 'jp' else en_path(rel).read_bytes()
    return {'rel': rel, 'tex': tex, 'cgfx': cgfx, 'base': base, 'src_bytes': src_bytes,
            'base0': decode_bytes(src_bytes, rel, tex), 'jp': load(rel, 'jp', tex),
            'en': load(rel, 'en', tex) if en_path(rel) else None}


def _erased_rects(items):
    out = []
    for it in items:
        if 'copy' not in it and it.get('erase', 'transparent') not in (None, 'none', ''):
            out += _erase_rects(it)
    return out


def _apply_items(img, items, prep, erased, first=0):
    """Applies items[first:] over img (in place). Returns the report lines ('  item n: ...')."""
    ctx = {'jp': prep['jp'], 'base0': prep['base0']}
    log = []
    for n in range(first, len(items)):
        it = items[n]
        rep = draw_item(img, it, ctx)
        if 'copy' not in it and it.get('erase', 'transparent') not in (None, 'none', '') and it.get('check', True):
            rep += ['WARNING: ' + wmsg for wmsg in cut_warnings(prep['base0'], _erase_rects(it),
                                                             it.get('keep'), it.get('thr'), it.get('bg'), erased)]
        for r in rep:
            log.append(f'  item {n}: {r}')
    return log


def _finish(img, spec, prep):
    """Protect areas restored (in place) and final view after the codec."""
    base0 = prep['base0']
    for r in _rects(spec.get('protect')):
        img.paste(base0.crop((r[0], r[1], r[0] + r[2], r[1] + r[3])), (r[0], r[1]))
    return roundtrip(prep['src_bytes'], prep['rel'], img, prep['tex'])


def build(spec):
    """Applies the spec in memory (no writing or previews): dict with the images of _prepare + img (result
    before the codec), final (as it will look), items (expanded) and log."""
    prep = _prepare(spec)
    img = prep['base0'].copy()
    items = expand_items(spec)
    log = _apply_items(img, items, prep, _erased_rects(items))
    final = _finish(img, spec, prep)
    return dict(prep, img=img, final=final, items=items, log=log)


def _allowed_mask(items, spec, size):
    """'L' mask (255 = area the spec may change): erase boxes, text boxes, segments, copy destinations and
    protect."""
    m = Image.new('L', size, 0)
    d = ImageDraw.Draw(m)
    rs = list(_rects(spec.get('protect')))
    for it in items:
        if 'copy' in it:
            rs.append((it['to'][0], it['to'][1], it['copy'][2], it['copy'][3]))
            continue
        if it.get('erase', 'transparent') not in (None, 'none', ''):
            rs += _erase_rects(it)
        if it.get('text'):
            rs += _text_rects(it)
    for (x, y, w, h) in rs:
        if w > 0 and h > 0:
            d.rectangle((x, y, x + w - 1, y + h - 1), fill=255)
    return m


def outside_changes(base0, img, items, spec):
    """(n, [x, y, w, h]) pixels the spec changes OUTSIDE its boxes (ink, outline or shadow that sticks out of the
    text box,
    mostly) and their bounding box; (0, None) if none."""
    diff = ImageChops.difference(base0, img)
    rgb = diff.convert('RGB').point(lambda v: 255 if v else 0).convert('L').point(lambda v: 255 if v else 0)
    vis = ImageChops.lighter(base0.getchannel('A'), img.getchannel('A')).point(lambda v: 255 if v else 0)
    ch = ImageChops.lighter(ImageChops.multiply(rgb, vis), diff.getchannel('A').point(lambda v: 255 if v else 0))
    out = ImageChops.subtract(ch, _allowed_mask(items, spec, img.size))
    bb = out.getbbox()
    if not bb:
        return 0, None
    n = sum(1 for v in _pixels(out) if v)
    return n, [bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]]


def write_only(spec, out_dir):
    """Renders the spec and writes the texture file(s) into out_dir, without previews (used by the m9 build)."""
    b = build(spec)
    rel, tex, cgfx, src_bytes, img, base0 = b['rel'], b['tex'], b['cgfx'], b['src_bytes'], b['img'], b['base0']
    if cgfx:
        return _write_cgfx([(rel, tex)] + _norm_targets(spec, rel, tex), img, base0, out_dir)
    out = Path(out_dir) / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(C.replace(src_bytes, {0: img}))
    return [str(out)]


def render(spec, write=True, out_dir=None, scale=None, crop=None, quiet=False):
    b = build(spec)
    rel, tex, cgfx, base, src_bytes = b['rel'], b['tex'], b['cgfx'], b['base'], b['src_bytes']
    base0, img, final, jp, en, items, log = b['base0'], b['img'], b['final'], b['jp'], b['en'], b['items'], b['log']
    targets = [(rel, tex)] + (_norm_targets(spec, rel, tex) if cgfx else [])
    nout, bbout = outside_changes(base0, img, items, spec)
    if nout:
        log.append(f'  WARNING: {nout} px changed OUTSIDE the boxes (area {bbout}): ink, outline or shadow that '
                   f'sticks out of the text box; check that it does not cover anything (or widen the box / erase_box)')
    else:
        log.append('  outside the boxes: 0 px changed')
    # full preview
    rects = []
    for it in items:
        if 'copy' in it:
            rects.append((*it['copy'], (255, 200, 0, 255)))
            rects.append((it['to'][0], it['to'][1], it['copy'][2], it['copy'][3], (255, 200, 0, 255)))
            continue
        if it.get('erase', 'transparent') not in (None, 'none', ''):
            for r in _erase_rects(it):
                rects.append((*r, (255, 60, 60, 255)))
        if it.get('text'):
            for r in _text_rects(it):
                rects.append((*r, (0, 230, 255, 255)))
    panels_src = [('JP original (boxes: red = erase, cyan = text, yellow = copy)', jp, rects)]
    if en is not None:
        panels_src.append(('EN (Omnija)', en, None))
    panels_src.append(('ES (result exactly as it will look in the game)', final, None))
    origin = (0, 0)
    if crop:
        x, y, w, h = crop
        panels_src = [(t, im.crop((x, y, x + w, y + h)), r) for t, im, r in panels_src]
        origin = (x, y)
    pw, ph = panels_src[0][1].size
    s, vertical = _panel_layout(pw, ph, len(panels_src), scale)
    name = f'{rel}:{tex}' if tex else rel
    panels = [_grid(im, s, f'{t}  {name}' if i == 0 else t, origin, r) for i, (t, im, r) in enumerate(panels_src)]
    prev = _stack(panels, vertical)
    key = tex_key(rel, tex)
    pdir = WORK / ('preview_en' if out_dir and Path(out_dir).name.endswith('_en') else 'preview')   # previews per language
    pdir.mkdir(exist_ok=True)
    pv = pdir / (key + '.png')
    pv.parent.mkdir(parents=True, exist_ok=True)
    prev.convert('RGB').save(pv)
    zrows = _zoom_rows(rel, items, jp, en, final)
    zp = pdir / (key + '.zoom.png')
    for old in zp.parent.glob(key + '.zoom*.png'):   # old pages
        try:
            old.unlink()
        except OSError:
            pass
    if zrows:
        # paginate if too tall
        pages, cur, hh = [], [], 0
        for r in zrows:
            if cur and hh + r.size[1] > 1700:
                pages.append(cur); cur, hh = [], 0
            cur.append(r); hh += r.size[1] + 10
        pages.append(cur)
        for i, pg in enumerate(pages):
            p = zp if i == 0 else zp.with_name(zp.name.replace('.zoom.png', f'.zoom{i + 1}.png'))
            _stack(pg, True, 10).convert('RGB').save(p)
    written = []
    if write:
        if cgfx:
            written = _write_cgfx(targets, img, base0, out_dir)
        else:
            new = C.replace(src_bytes, {0: img})
            out = Path(out_dir) / rel if out_dir else OUT_TEX / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(new)
            written = [str(out)]
    if not quiet:
        print(f'{name} (base {base}, format {fmt_name(src_bytes, rel, tex)})')
        if len(targets) > 1:
            print(f'  copies with the same pixels ({len(targets) - 1}): '
                  + ', '.join(f'{r}:{t}' for r, t in targets[1:]))
        for line in log:
            print(line)
        print(f'preview: {pv}')
        if zrows:
            print(f'detail:  {zp}')
        for w in written:
            print(f'written: {w}')
    return pv


def _diff_outside(old, new, spans):
    """Bytes that differ between old and new OUTSIDE the ranges spans [(start, end)] (or None if their sizes differ)."""
    if len(old) != len(new):
        return None
    n = 0
    prev = 0
    for a, b in sorted(spans) + [(len(old), len(old))]:
        if a > prev:
            seg_o, seg_n = old[prev:a], new[prev:a]
            if seg_o != seg_n:
                n += sum(1 for x, y in zip(seg_o, seg_n) if x != y)
        prev = max(prev, b)
    return n


def verify_out(out_dir=None):
    """Checks each file of data/romfs_tex_es against its original (JP 1.3, or Omnija's EN if the spec started from
    it): same size and no byte changed outside the texture data (headers, meshes, materials).
    Returns the number of files with problems."""
    root = Path(out_dir) if out_dir else OUT_TEX
    bad = 0
    for f in sorted(q for q in root.rglob('*') if q.is_file()):
        rel = f.relative_to(root).as_posix()
        new = f.read_bytes()
        cands = []
        try:
            cands.append(('JP', jp_bytes(rel)))
        except (FileNotFoundError, KeyError):
            pass
        if en_path(rel):
            cands.append(('EN', en_path(rel).read_bytes()))
        if not cands:
            print(f'ERROR {rel}: original not found')
            bad += 1
            continue
        best = None
        for tag, orig in cands:
            try:
                ts = tex_list(orig, rel)
            except Exception:
                continue
            spans = [(t['off'], t['off'] + t['size']) for t in ts]
            out = _diff_outside(orig, new, spans)
            if out is None:
                continue
            changed = [t['name'] for t in ts if orig[t['off']:t['off'] + t['size']] != new[t['off']:t['off'] + t['size']]]
            if best is None or out < best[1]:
                best = (tag, out, changed)
        if best is None:
            print(f'ERROR {rel}: not the same size as the original')
            bad += 1
        elif best[1]:
            print(f'ERROR {rel}: {best[1]} bytes changed outside the textures (against {best[0]})')
            bad += 1
        else:
            print(f'OK    {rel} (against {best[0]}; changed textures: {", ".join(best[2]) or "none"})')
    print(f'{bad} files with problems')
    return bad


# ------------------------------------------------------------------------------------------- boxes
def _components(mask, w, h, gap=2):
    """Boxes of the connected components of a boolean mask (list of lists), joining gaps <= gap px."""
    seen = [[False] * w for _ in range(h)]
    boxes = []
    for y0 in range(h):
        for x0 in range(w):
            if not mask[y0][x0] or seen[y0][x0]:
                continue
            stack = [(x0, y0)]
            seen[y0][x0] = True
            x1 = x2 = x0; y1 = y2 = y0
            while stack:
                x, y = stack.pop()
                x1, x2, y1, y2 = min(x1, x), max(x2, x), min(y1, y), max(y2, y)
                for dy in range(-gap, gap + 1):
                    for dx in range(-gap, gap + 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True
                            stack.append((nx, ny))
            boxes.append([x1, y1, x2 - x1 + 1, y2 - y1 + 1])
    return boxes


def _merge_lines(boxes, hgap=6):
    """Joins boxes on the same line (they overlap vertically and are <= hgap px apart horizontally)."""
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    changed = True
    while changed:
        changed = False
        out = []
        for b in boxes:
            for o in out:
                vo = min(o[1] + o[3], b[1] + b[3]) - max(o[1], b[1])
                hg = max(o[0], b[0]) - min(o[0] + o[2], b[0] + b[2])
                if vo > 0.4 * min(o[3], b[3]) and hg <= hgap:
                    x1, y1 = min(o[0], b[0]), min(o[1], b[1])
                    x2, y2 = max(o[0] + o[2], b[0] + b[2]), max(o[1] + o[3], b[1] + b[3])
                    o[:] = [x1, y1, x2 - x1, y2 - y1]
                    changed = True
                    break
            else:
                out.append(list(b))
        boxes = out
    return boxes


def text_boxes(rel, tex=None):
    """Candidate text boxes. With Omnija's English version: areas where JP and EN differ (exact).
    Without it: components of opaque pixels (transparent background). For opaque textures (3D models) it gives one
    box:
    use inspect --crop and sample."""
    jp = load(rel, 'jp', tex)
    w, h = jp.size
    jpx = jp.load()
    if en_path(rel):
        en = load(rel, 'en', tex); epx = en.load()
        mask = [[sum(abs(jpx[x, y][k] - epx[x, y][k]) for k in range(4)) > 40 for x in range(w)] for y in range(h)]
        src = 'diff JP/EN'
    else:
        mask = [[jpx[x, y][3] > 60 for x in range(w)] for y in range(h)]
        src = 'opaque'
    boxes = [b for b in _merge_lines(_components(mask, w, h)) if b[2] >= 3 and b[3] >= 4]
    return src, boxes


# ------------------------------------------------------------------------------------------- fonts
def font_sheet(text='Volver Guardar Pieza 123', cap=9, out=None, only=None):
    rows = []
    lab = ImageFont.truetype(FONTS['regular'][0], 12)
    names = list(FONTS)
    if only:
        names = [n.strip() for n in (only.split(',') if isinstance(only, str) else only) if n.strip()]
    for name in names:
        try:
            entry = _font_entry(name)
            size = cap / cap_ratio(entry)
            f = get_font(entry, size * SS)
        except Exception as e:  # font missing on this machine
            rows.append((name, None, str(e)))
            continue
        bb = f.getbbox(text, anchor='ls')
        W = int((bb[2] - bb[0]) / SS) + 8
        Hh = int(cap * 2.2) + 4
        m = Image.new('L', (W * SS, Hh * SS), 0)
        ImageDraw.Draw(m).text((4 * SS - bb[0], int(cap * 1.5 * SS) + 2 * SS), text, font=f, fill=255, anchor='ls')
        layer = Image.new('RGBA', m.size, (255, 255, 255, 255))
        st = _dilate(m, SS)
        im = Image.new('RGBA', m.size, (90, 110, 140, 255))
        im.alpha_composite(_masked(Image.new('RGBA', m.size, (20, 20, 30, 255)), st))
        im.alpha_composite(_masked(layer, m))
        rows.append((name, im.resize((W, Hh), Image.BOX), ''))
    z = 3
    colw = max((r[1].size[0] * z if r[1] else 300) for r in rows) + 170
    half = (len(rows) + 1) // 2
    cols = [rows[:half], rows[half:]]
    colh = [sum((r[1].size[1] * z if r[1] else 20) + 6 for r in c) for c in cols]
    sheet = Image.new('RGB', (colw * 2 + 10, max(colh)), (28, 28, 30))
    d = ImageDraw.Draw(sheet)
    for ci, c in enumerate(cols):
        x0 = ci * (colw + 10)
        yy = 0
        for name, im, err in c:
            d.text((x0 + 4, yy + 4), name, fill=(255, 220, 0), font=lab)
            if im is None:
                d.text((x0 + 170, yy + 4), 'NOT AVAILABLE', fill=(255, 80, 80), font=lab)
                yy += 26
                continue
            sheet.paste(im.convert('RGB').resize((im.size[0] * z, im.size[1] * z), Image.NEAREST), (x0 + 170, yy))
            yy += im.size[1] * z + 6
    out = Path(out or (WORK / 'fuentes.png'))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


# ------------------------------------------------------------------------------------------- review sheets
_BGS = {'oscuro': (28, 28, 32), 'medio': (128, 128, 136), 'claro': (232, 232, 236), 'magenta': (255, 0, 255)}
_BG_ALIAS = {'dark': 'oscuro', 'mid': 'medio', 'gris': 'medio', 'light': 'claro'}


def _bg_list(arg, default='todos'):
    """--bg -> [(name, (r, g, b))]: 'todos' (oscuro, medio and claro), oscuro | medio | claro | magenta, or 'R,G,B'."""
    arg = arg or default
    arg = _BG_ALIAS.get(arg, arg)
    if arg in ('todos', 'all'):
        return [(k, _BGS[k]) for k in ('oscuro', 'medio', 'claro')]
    if arg in _BGS:
        return [(arg, _BGS[arg])]
    v = tuple(int(t) for t in arg.split(','))
    return [(arg, v[:3])]


def _over(img, rgb):
    bg = Image.new('RGBA', img.size, tuple(rgb) + (255,))
    bg.alpha_composite(img)
    return bg.convert('RGB')


def _label_img(text, width, size=12, color=(255, 220, 90)):
    """Dark strip with text (splits long lines; Hiragino: Japanese too)."""
    try:
        f = ImageFont.truetype(FONTS['hiragino'][0], size, index=FONTS['hiragino'][1])
    except OSError:
        f = ImageFont.truetype(FONTS['regular'][0], size)
    lines = []
    for raw in text.split('\n'):
        cur = ''
        for word in raw.split(' '):
            t = (cur + ' ' + word).strip()
            if cur and f.getlength(t) > width - 8:
                lines.append(cur)
                cur = word
            else:
                cur = t
        lines.append(cur)
    im = Image.new('RGB', (max(1, width), len(lines) * (size + 3) + 4), (24, 24, 30))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(lines):
        d.text((4, 2 + i * (size + 3)), ln, fill=color, font=f)
    return im


def _row_panels(img, bgs, scale, marks=None):
    """[enlarged image over each background] (marks: [(x, y, w, h)] in img px, green frame)."""
    out = []
    for _name, rgb in bgs:
        p = _over(img, rgb).resize((img.width * scale, img.height * scale), Image.NEAREST)
        if marks:
            d = ImageDraw.Draw(p)
            for (x, y, w, h) in marks:
                d.rectangle((x * scale, y * scale, (x + w) * scale - 1, (y + h) * scale - 1), outline=(60, 255, 90))
        out.append(p)
    return out


def _sheet_pages(blocks, out, max_h=1800, gap=8):
    """Stacks blocks (RGB images) into one or several pages: out, out.2.png... -> list of paths."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    for old in out.parent.glob(out.stem + '.*.png'):
        if old.name[len(out.stem) + 1:-4].isdigit():
            try:
                old.unlink()
            except OSError:
                pass
    pages, cur, hh = [], [], 0
    for b in blocks:
        if cur and hh + b.height > max_h:
            pages.append(cur)
            cur, hh = [], 0
        cur.append(b)
        hh += b.height + gap
    if cur:
        pages.append(cur)
    paths = []
    for i, pg in enumerate(pages):
        W = max(b.width for b in pg)
        H = sum(b.height for b in pg) + gap * (len(pg) - 1)
        sheet = Image.new('RGB', (W, H), (10, 10, 14))
        y = 0
        for b in pg:
            sheet.paste(b, (0, y))
            y += b.height + gap
        p = out if i == 0 else out.with_name(f'{out.stem}.{i + 1}.png')
        sheet.save(p)
        paths.append(p)
    return paths


def _hstack(ims, gap=6, bg=(10, 10, 14)):
    W = sum(i.width for i in ims) + gap * (len(ims) - 1)
    H = max(i.height for i in ims)
    c = Image.new('RGB', (W, H), bg)
    x = 0
    for i in ims:
        c.paste(i, (x, 0))
        x += i.width + gap
    return c


def _vstack(ims, gap=2, bg=(10, 10, 14)):
    W = max(i.width for i in ims)
    H = sum(i.height for i in ims) + gap * (len(ims) - 1)
    c = Image.new('RGB', (W, H), bg)
    y = 0
    for i in ims:
        c.paste(i, (0, y))
        y += i.height + gap
    return c


def _parse_val(v):
    """Value of --try/--var: JSON if it is JSON; otherwise text (with \\n -> line break, as in the specs)."""
    v = v.strip()
    try:
        return json.loads(v)
    except ValueError:
        return v.replace('\\n', '\n')


def _split_top(s, sep=','):
    """Splits s by sep outside brackets, braces and quotes."""
    out, cur, depth, q = [], '', 0, None
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
            continue
        if ch in '"\'':
            q = ch
        elif ch in '[{(':
            depth += 1
        elif ch in ']})':
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def variant_list(tries=(), vars_=()):
    """--try key=v1,v2 (Cartesian product across --try) and --var 'key=v;key=v' or --var '{json}'."""
    out = []
    if tries:
        combos = [{}]
        for t in tries:
            k, _, vals = t.partition('=')
            if not vals:
                raise ValueError(f'--try {t!r}: use key=value1,value2')
            combos = [dict(c, **{k.strip(): _parse_val(v)}) for c in combos for v in _split_top(vals)]
        out += combos
    for v in vars_:
        v = v.strip()
        if v.startswith('{'):
            out.append(json.loads(v))
        else:
            d = {}
            for kv in _split_top(v, ';'):
                k, _, val = kv.partition('=')
                d[k.strip()] = _parse_val(val)
            out.append(d)
    return out


def _fmt_variant(ov):
    return ' '.join(f'{k}={v}' if isinstance(v, str) else f'{k}={json.dumps(v, separators=(",", ":"))}'
                    for k, v in ov.items()) or '(no changes)'


def _summary(lines):
    """Summary of the report lines of an item: capitals, condensing, warnings."""
    import re
    out = []
    for ln in lines:
        m = re.search(r"text (\[.*?\]): font=(\S+) em=\S+ caps=(\S+) condensed=(\S+)", ln)
        if m:
            out.append(f'{m.group(2)} caps {m.group(3)} condensed {m.group(4)}')
        elif 'WARNING' in ln:
            out.append('WARNING ' + ln.split('WARNING:', 1)[1].strip()[:110])
    return '; '.join(out)


def _item_rects(it):
    rs = list(_text_rects(it))
    if 'copy' not in it and it.get('erase', 'transparent') not in (None, 'none', ''):
        rs += list(_erase_rects(it))
    return rs


def _view(img, it, region):
    """Crop shown for an item: the composed strip if it has segments; otherwise the region."""
    segs, spos, SW, SH = _segments(it)
    if segs:
        strip = Image.new('RGBA', (SW, SH), (0, 0, 0, 0))
        for r, (px, py) in zip(segs, spos):
            strip.paste(img.crop((r[0], r[1], r[0] + r[2], r[1] + r[3])), (px, py))
        return strip
    return img.crop(region)


def variants(spec, n=None, vlist=(), text=None, bg=None, scale=None, out=None, key_suffix=''):
    """Tries variants of an item (font, cap, colors, text...) WITHOUT touching the previews or writing: a sheet
    with the JP, the current spec and each variant, already passed through the codec, on plain backgrounds. n = index
    of the item in the spec's "items" (from 0; the "repeat" ones go with their item). Returns the sheet paths."""
    raws = spec.get('items', [])
    if n is None:
        n = next((i for i, r in enumerate(raws) if 'copy' not in r and r.get('text')), None)
        if n is None:
            raise ValueError('the spec has no item with text: give --item N')
    if not 0 <= n < len(raws) or 'copy' in raws[n]:
        raise ValueError(f'--item {n}: is not a text item (the spec has {len(raws)} items, counted from 0)')
    vlist = list(vlist)
    if text is not None and not vlist:
        vlist = [{}]
    prep = _prepare(spec)
    W, H = prep['base0'].size
    pre_items = expand_items(dict(spec, items=raws[:n]))
    k0 = len(pre_items)
    pre = prep['base0'].copy()
    _apply_items(pre, pre_items, prep, _erased_rects(pre_items))
    versions = [('current spec', {}, False)] + [(None, v, True) for v in vlist]
    res = []
    for label, ov, is_var in versions:
        raw = dict(raws[n])
        raw.update(ov)
        if is_var and text is not None and 'text' not in ov:
            raw['text'] = text
        sp = dict(spec, items=raws[:n] + [raw] + raws[n + 1:])
        items = expand_items(sp)
        k1 = k0 + len(expand_items(dict(sp, items=[raw])))
        img = pre.copy()
        log = _apply_items(img, items, prep, _erased_rects(items), first=k0)
        final = _finish(img, sp, prep)
        mine = [ln for ln in log if any(ln.startswith(f'  item {k}:') for k in range(k0, k1))]
        lab = label or _fmt_variant(dict(ov, **({'text': text} if (text is not None and 'text' not in ov) else {})))
        res.append((lab, items[k0], final, mine))
    rs = [r for _l, it, _f, _m in res for r in _item_rects(it)]
    m = 6
    region = (max(0, min(r[0] for r in rs) - m), max(0, min(r[1] for r in rs) - m),
              min(W, max(r[0] + r[2] for r in rs) + m), min(H, max(r[1] + r[3] for r in rs) + m))
    views = [('JP original', _view(prep['jp'], res[0][1], region), '')]
    views += [(f'{i}: {lab}' if i else lab, _view(fin, it, region), _summary(mine))
              for i, (lab, it, fin, mine) in enumerate(res)]
    transparent = any(v.getchannel('A').getextrema()[0] < 255 for _t, v, _s in views)
    bgs = _bg_list(bg, 'todos' if transparent else 'medio')
    vw, vh = views[0][1].size
    s = scale or max(2, min(8, int((1460 - 8 * len(bgs)) / (vw * len(bgs))), int(300 / max(1, vh)),
                            int((3400 - 44 * len(views)) / (len(views) * max(1, vh)))))
    blocks = []
    where = ('composed strip of its "segments"' if _segments(res[0][1])[0] else
            f'area [{region[0]}, {region[1]}, {region[2] - region[0]}, {region[3] - region[1]}]')
    head = (f'{spec["rel"]}  item {n}  (backgrounds: {", ".join(b[0] for b in bgs)}; result already passed through '
            f'the codec; '
            f'{where})')
    for title, v, summ in views:
        row = _hstack(_row_panels(v, bgs, s))
        lab = _label_img(title + (f'\n{summ}' if summ else ''), row.width)
        blocks.append(_vstack([lab, row]))
    blocks.insert(0, _label_img(head, blocks[0].width, 12, (150, 210, 255)))
    key = tex_key(spec['rel'], spec.get('tex'))
    out = out or (WORK / 'variantes' / f'{key}.item{n}{key_suffix}.png')
    paths = _sheet_pages(blocks, out)
    for title, _v, summ in views[1:]:
        print(f'  {title}\n      {summ or "-"}')
    return paths


def _acd_tex(rel, es, es_imgs, es_dir, cache):
    """Texture of a sprite: JP, or ES (the one in the in-memory spec, the one written in data/romfs_tex_es or
    --es-dir; otherwise
    the JP)."""
    key = (rel, es)
    if key not in cache:
        im = None
        try:
            if es:
                if rel in es_imgs:
                    im = es_imgs[rel]
                else:
                    p = (Path(es_dir) if es_dir else OUT_TEX) / rel
                    if p.exists():
                        im = decode_bytes(p.read_bytes(), rel)
            if im is None:
                im = load(rel, 'jp')
        except Exception:
            im = None
        cache[key] = im
    return cache[key]


def compose_frame(sprites, root, es, es_imgs, es_dir, cache, report, mark=None):
    """Composes a frame of an .acd (sprites from acd.layout) -> (RGBA image, origin (x0, y0), boxes of the
    sprites of the mark texture). Applies the sprite color (tint/alpha) and scale; sprites without a texture are
    color rectangles; the font labels (text) are not drawn."""
    import acd as A
    xs = [s['x'] for s in sprites] + [s['x'] + s['w'] for s in sprites]
    ys = [s['y'] for s in sprites] + [s['y'] + s['h'] for s in sprites]
    x0, y0 = math.floor(min(xs)), math.floor(min(ys))
    W, H = max(1, math.ceil(max(xs)) - x0), max(1, math.ceil(max(ys)) - y0)
    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    marks = []
    for s in sprites:
        w, h = int(round(abs(s['w']))), int(round(abs(s['h'])))
        if w <= 0 or h <= 0:
            continue
        col = tuple(max(0.0, min(1.0, c)) for c in s['color'])
        px, py = int(round(min(s['x'], s['x'] + s['w']))) - x0, int(round(min(s['y'], s['y'] + s['h']))) - y0
        if s['tex'] is None:
            if s['text']:
                continue
            patch = Image.new('RGBA', (w, h), tuple(int(round(c * 255)) for c in col))
        else:
            rel = A.tex_rel(root, s['tex'])
            src = _acd_tex(rel, es, es_imgs, es_dir, cache)
            if src is None:
                msg = f'cannot read texture {rel}'
                if msg not in report:
                    report.append(msg)
                continue
            r = A.uv_rect(s)
            patch = src.crop((r[0], r[1], r[0] + r[2], r[1] + r[3]))
            if patch.size != (w, h):
                patch = patch.resize((w, h), Image.BILINEAR)
            if col != (1.0, 1.0, 1.0, 1.0):
                patch = Image.merge('RGBA', [ch.point(lambda v, k=k: int(round(v * k)))
                                             for ch, k in zip(patch.split(), col)])
            if mark and rel == mark:
                marks.append((px, py, w, h))
        canvas.alpha_composite(patch, (px, py))
    return canvas, (x0, y0), marks


def screen(target, acd_filter=None, anim=None, frame='auto', bg=None, scale=None, es_dir=None, out=None, marks=True,
           max_rows=30):
    """Composes the screens (.acd) that use a texture with the JP and ES texture, side by side: the label on its
    real button or window. target = .json spec (ES = its in-memory render, not written), .ctpk texture (ES = the one
    written in data/romfs_tex_es) or an .acd. One row per distinct composition (animations normal, select, push,
    disable...; frame: 'auto' = all frames of animations of up to 4 and the first of the rest, N or
    'all'). Returns the sheet paths."""
    import acd as A
    es_imgs = {}
    rel = None
    if target.endswith('.json'):
        spec = json.loads(Path(target).read_text(encoding='utf-8'))
        if is_cgfx(spec['rel']):
            raise ValueError('screen: the .acd files only use CTPK textures')
        b = build(spec)
        rel = b['rel']
        es_imgs[rel] = b['final']
        acds = None
    elif target.endswith('.acd'):
        acds = [target]
    else:
        rel = target
        acds = None
    if acds is None:
        acds = sorted({e['acd'] for e in A.load_index().get(rel, [])})
        if acd_filter:
            acds = [a for a in acds if acd_filter in a]
        if not acds:
            print(f'{rel}: no .acd uses this texture' + (f' (filter {acd_filter!r})' if acd_filter else '') +
                  ': scripts or the code use it')
            return []
    texname = rel.rsplit('/', 1)[-1].rsplit('.', 1)[0] if rel else None
    rows, report = [], []
    for a in acds:
        try:
            lay = A.layout(jp_bytes(a))
        except Exception as e:
            report.append(f'{a}: cannot read ({e})')
            continue
        root = a.split('/')[0]
        seen = {}
        for an in lay['anims']:
            if anim and an['name'] not in anim.split(','):
                continue
            nf = len(an['frames'])
            if not nf:
                continue
            if frame in (None, 'auto'):
                fis = range(nf) if nf <= 4 else [0]
            elif frame == 'all':
                fis = range(nf)
            else:
                fis = [min(int(frame), nf - 1)]
            for fi in fis:
                sps = an['frames'][fi]['sprites']
                if not sps or (texname and not any(s['tex'] == texname and A.tex_rel(root, s['tex']) == rel
                                                   for s in sps)):
                    continue
                lab = an['name'] + (f'#{fi}' if nf > 1 else '')
                sig = json.dumps([(s['tex'], A.uv_rect(s), [round(v, 1) for v in (s['x'], s['y'], s['w'], s['h'])],
                                   [round(c, 2) for c in s['color']]) for s in sps])
                if sig in seen:
                    seen[sig].append(lab)
                    continue
                seen[sig] = [lab]
                rows.append((a, seen[sig], sps, root))
    if not rows:
        print('nothing to compose' + (f' (animation {anim!r})' if anim else ''))
        return []
    if len(rows) > max_rows:
        report.append(f'{len(rows) - max_rows} more compositions not drawn (use --acd, --anim or --frame)')
        rows = rows[:max_rows]
    rows = [(f'{a}  [{", ".join(labs[:6])}{" +" + str(len(labs) - 6) if len(labs) > 6 else ""}]', sps, root)
            for a, labs, sps, root in rows]
    bgs = _bg_list(bg, 'medio')
    cache = {}
    blocks = []
    for title, sps, root in rows:
        jp_c, org, mk = compose_frame(sps, root, False, es_imgs, es_dir, cache, report, rel if marks else None)
        es_c, _o, _m = compose_frame(sps, root, True, es_imgs, es_dir, cache, report)
        s = scale or max(1, min(6, int(1440 / (2 * jp_c.width)), int(520 / jp_c.height)))
        for bname, rgb in bgs:
            pj = _row_panels(jp_c, [(bname, rgb)], s, mk)[0]
            pe = _row_panels(es_c, [(bname, rgb)], s)[0]
            row = _hstack([pj, pe], 10)
            lab = _label_img(f'{title}  (origin of the .acd at ({org[0]}, {org[1]}); background {bname}; x{s})   '
                             f'JP | ES' + ('   [green = sprites of the texture]' if mk else ''), row.width)
            blocks.append(_vstack([lab, row]))
    if out is None:
        parts = [tex_key(rel) if rel else target.replace('/', '__')]
        if acd_filter:                          # one sheet per combination: another --acd does not overwrite
            parts.append(acd_filter.replace('/', '_'))
        if anim:
            parts.append(anim.replace(',', '+'))
        if frame not in (None, 'auto'):
            parts.append(f'f{frame}')
        out = WORK / 'pantallas' / ('.'.join(parts) + '.png')
    paths = _sheet_pages(blocks, out)
    for t, _s, _r in rows:
        print(f'  {t}')
    for r in report:
        print(f'  note: {r}')
    return paths


def tiles_report(only=None, out_dir=None):
    """Areas that the .acd files STRETCH (1 px UV or scale >= 1.9: frame strips, fills, lines; also glow sprites
    and zoomed labels) and that change between the JP and what is written: the erase or ink of a label has eaten
    a piece of frame that the game stretches across the whole width. Ignores codec noise (differences <= 32 per channel
    with no alpha change). Returns the number of changed strip/frame areas."""
    import acd as A
    root = Path(out_dir) if out_dir else OUT_TEX
    n_strips = 0
    for p in sorted(root.rglob('*.ctpk')):
        rel = p.relative_to(root).as_posix()
        if only and only not in rel:
            continue
        try:
            pl = A.placements(rel)
        except Exception:
            continue
        zones = {}
        for g in pl:
            sx, sy = g['scale']
            if sx is None or sy is None or abs(sx) >= 1.9 or abs(sy) >= 1.9:
                zones.setdefault(tuple(g['rect']), []).append(g)
        if not zones:
            continue
        try:
            jp = load(rel, 'jp')
            es = decode_bytes(p.read_bytes(), rel)
        except Exception:
            continue
        pj, pe = jp.load(), es.load()
        W, H = jp.size
        spec_p = WORK / 'specs' / (tex_key(rel) + '.json')
        items = []
        if spec_p.exists():
            try:
                items = expand_items(json.loads(spec_p.read_text(encoding='utf-8')))
            except Exception:
                items = []
        lines = []
        for r, gs in sorted(zones.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            x, y, w, h = r
            n = 0
            for yy in range(max(0, y), min(H, y + h)):
                for xx in range(max(0, x), min(W, x + w)):
                    a, b = pj[xx, yy], pe[xx, yy]
                    if a == b or (a[3] == 0 and b[3] == 0):
                        continue
                    if abs(a[3] - b[3]) > 16 or (max(a[3], b[3]) > 32 and max(abs(a[k] - b[k]) for k in range(3)) > 32):
                        n += 1
            if not n:
                continue
            g = gs[0]
            sx, sy = g['scale']
            strip_zone = min(w, h) <= 2 or (sx or 99) >= 4 or (sy or 99) >= 4
            if strip_zone:
                n_strips += 1
            hits = []
            for k, it in enumerate(items):
                if 'copy' in it:
                    continue
                rs = (_erase_rects(it) if it.get('erase', 'transparent') not in (None, 'none', '') else []) + \
                    (_text_rects(it) if it.get('text') else [])
                if any(q[0] < x + w and x < q[0] + q[2] and q[1] < y + h and y < q[1] + q[3] for q in rs):
                    hits.append(f'item {k} ({(it.get("text") or "erase")[:16]!r})')
            esc = '1 px UV' if (sx is None or sy is None) else f'scale {sx:g}x{sy:g}'
            lines.append(f'  {list(r)} {esc} ({g["acd"].rsplit("/", 1)[-1]}:{g["anims"][0]}): {n} px changed '
                         f'{"-> STRIP/FRAME: protect it with protect" if strip_zone else "(label or glow sprite: ok)"}'
                         + (f'; touched by {", ".join(hits[:3])}' if hits else ''))
        if lines:
            print(rel)
            for ln in lines:
                print(ln)
    print(f'{n_strips} stretched strips/frames changed')
    return n_strips


def verify_specs(spec_dir, out_dir=None):
    """Each spec of spec_dir against what is written in data/romfs_tex_es: the written file must be exactly the
    render of the spec (otherwise the spec changed after being written or it was written with another version of
    texlib).
    For 3D models it compares only the bytes of its texture. Returns the number of discrepancies."""
    root = Path(out_dir) if out_dir else OUT_TEX
    bad = 0
    for f in sorted(Path(spec_dir).glob('*.json')):
        try:
            spec = json.loads(f.read_text(encoding='utf-8'))
        except ValueError as e:
            print(f'ERROR        {f.name}: invalid JSON ({e})')
            bad += 1
            continue
        if 'rel' not in spec:
            continue
        try:
            b = build(spec)
        except Exception as e:  # report and continue
            print(f'ERROR        {f.name}: {type(e).__name__}: {e}')
            bad += 1
            continue
        rel, tex = b['rel'], b['tex']
        p = root / rel
        if not p.exists():
            print(f'NOT WRITTEN  {f.name}')
            bad += 1
            continue
        cur = p.read_bytes()
        if b['cgfx']:
            orig = jp_bytes(rel)
            new = G.replace(orig, tex, b['img'], orig=orig)
            t = G.get(orig, tex)
            same = len(cur) == len(new) and cur[t['off']:t['off'] + t['size']] == new[t['off']:t['off'] + t['size']]
        else:
            same = C.replace(b['src_bytes'], {0: b['img']}) == cur
        if same:
            print(f'OK           {f.name}')
        else:
            print(f'DIFFERENT    {f.name}: what is written is not the current render of the spec (render it again)')
            bad += 1
    print(f'{bad} specs with problems')
    return bad


# ------------------------------------------------------------------------------------------- CLI
def _arg(flag, default=None, cast=str):
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return cast(sys.argv[i + 1])
    return default


def _args(flag):
    """All the values of a flag that can be repeated (--try a --try b)."""
    return [sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == flag]


def _rect_arg(s):
    return [int(v) for v in s.replace(' ', '').split(',')]


def _rel_tex():
    """(rel, tex) of positional argument 2: 'rel', 'rel:texture' (CGFX) or 'rel' + --tex texture."""
    return split_rel(sys.argv[2], _arg('--tex'))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == 'list':
        rel = sys.argv[2]
        data = jp_bytes(rel)
        for t in tex_list(data, rel):
            lv = len(G.levels(t)) if is_cgfx(rel) else 1
            print(f"{t['name']:32} {t['w']:4}x{t['h']:<4} {C.FMT_NAMES.get(t['fmt'], t['fmt']):8} mipmaps {lv}")
    elif cmd == 'copies':
        rel, tex = _rel_tex()
        _need_tex(rel, tex)
        cp = find_copies(rel, tex)
        print(f'{rel}:{tex}: {len(cp)} copies with the same pixels in {rel.rsplit("/", 1)[0]}/')
        for r, t in cp:
            print(f'  {r}:{t}')
        print(json.dumps([f'{r}:{t}' for r, t in cp]))
    elif cmd == 'boxes':
        rel, tex = _rel_tex()
        src, bx = text_boxes(rel, tex)
        print(src, json.dumps(bx))
        if '--trazos' in sys.argv:
            # inside each component: box fitted to the strokes that deviate from the dominant color
            img = load(rel, 'jp', tex)
            print('strokes inside each box (background = dominant color of the box):')
            for b in bx:
                if b[2] * b[3] < 24:
                    continue
                try:
                    an = analyze(img, [b], bg='mode')
                except Exception:
                    continue
                if an['n'] >= 6 and an['cover'] <= 0.6 and an['glyph_box']:
                    print(f'  box {b} -> strokes {an["glyph_box"]} fill={an["fill"]} outline={an["stroke"]} '
                          f'background={an["bg"]}')
    elif cmd == 'inspect':
        rel, tex = _rel_tex()
        print(inspect(rel, scale=_arg('--scale', None, int), crop=_arg('--crop', None, _rect_arg), tex=tex,
                      sprites='--sprites' in sys.argv))
    elif cmd == 'uv':
        rel, tex = _rel_tex()
        if not is_cgfx(rel):
            print('uv: only for CGFX model textures (<rel>.bcmdl:<texture>); for CTPK use sprites / screen')
            return 1
        _need_tex(rel, tex)
        print(uv_report(rel, tex, box=_arg('--box', None, _rect_arg), scale=_arg('--scale', None, int),
                        out=_arg('--out'), es='--es' in sys.argv))
    elif cmd == 'sprites' and '--screen' in sys.argv:
        import acd
        rel, _tex = _rel_tex()
        pl = acd.placements(rel, _arg('--acd'))
        if '--escalados' in sys.argv:
            pl = [g for g in pl if None in g['scale'] or any(abs(v - 1) > 0.01 for v in g['scale'])]
        if not pl:
            print(f'{rel}: no .acd uses this texture (scripts or the code use it)')
            return 0
        print(f'{rel}: {len(pl)} uses on screen: texture area -> position (x, y) and size of the sprite in its .acd '
              f'(.acd coordinates; the screen places it whole somewhere else, e.g. centered)')
        for g in pl:
            r, s_ = g['rect'], g['screen']
            sx, sy = g['scale']
            notes = []
            if sx is None or sy is None:
                notes.append('STRETCHED 1 px UV')
            elif abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
                notes.append(f'SCALED to {abs(s_[2]):g}x{abs(s_[3]):g} ({sx:g}x{sy:g})')
            if g['alpha'][0] < 0.99:
                notes.append(f'alpha {g["alpha"][0]:.2f}-{g["alpha"][1]:.2f}')
            an = g['anims']
            more = f' +{len(an) - 4}' if len(an) > 4 else ''
            print(f'  {r} -> ({s_[0]:g}, {s_[1]:g}) {abs(s_[2]):g}x{abs(s_[3]):g}'
                  f'{"  " + "  ".join(notes) if notes else ""}   {g["acd"].rsplit("/", 1)[-1]}:{g["sprite"]} '
                  f'[{", ".join(an[:4])}{more}]')
    elif cmd == 'sprites' and '--compose' in sys.argv:
        import acd
        rel, _tex = _rel_tex()
        name = rel.rsplit('/', 1)[-1][:-5]
        users = sorted({e['acd'] for e in acd.load_index().get(rel, [])})
        for u in users:
            sp = sorted({tuple(round(v) for v in s_[1:9]) for s_ in acd.parse(jp_bytes(u)) if s_[-1] == name})
            if len(sp) < 2:
                continue
            x0, y0 = min(t_[0] for t_ in sp), min(t_[1] for t_ in sp)
            segs = [[t_[4], t_[5], t_[6] - t_[4], t_[7] - t_[5], t_[0] - x0, t_[1] - y0] for t_ in sp]
            print(f'{u}: {len(sp)} sprites -> "segments": {json.dumps(segs)}')
        if not users:
            print('no .acd uses this texture')
    elif cmd == 'sprites':
        rel, tex = _rel_tex()
        rs = sprite_rects(rel)
        print(f'{rel}: {len(rs)} areas used by .acd sprites' +
              ('' if rs else ' (none: the texture is used by scripts or the code; it is shown whole or unknown)'))
        for r, users, cut in rs:
            more = f' (+{len(users) - 3})' if len(users) > 3 else ''
            print(f'  {r}{"  [the sprite stretches/repeats the texture]" if cut else ""}  {", ".join(users[:3])}{more}')
    elif cmd == 'sample':
        rel, tex = _rel_tex()
        box = _rect_arg(sys.argv[3])
        which = _arg('--from', 'jp')
        img = load(rel, which, tex)
        if img is None:
            print(f'version {which} does not exist')
            return 1
        print(json.dumps(analyze(img, [box], bg=_arg('--bg')), ensure_ascii=True))
    elif cmd == 'fonts':
        custom = any(f in sys.argv for f in ('--text', '--cap', '--only'))
        out = _arg('--out')
        if out is None and custom:        # the reference sampler (fuentes.png) is only written with no arguments
            import re
            slug = re.sub(r'[^A-Za-z0-9]+', '_', f'{_arg("--text", "")}_{_arg("--cap", "")}_{_arg("--only", "")}')
            out = WORK / 'variantes' / f'fuentes.{slug.strip("_")[:60]}.png'
        print(font_sheet(_arg('--text', 'Volver Guardar Pieza 123'), _arg('--cap', 9, float), out, _arg('--only')))
    elif cmd == 'render':
        spec = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
        render(spec, write='--dry' not in sys.argv, out_dir=_arg('--out'), scale=_arg('--scale', None, int),
               crop=_arg('--crop', None, _rect_arg))
    elif cmd == 'variants':
        spec = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
        vl = variant_list(_args('--try'), _args('--var'))
        for p in variants(spec, _arg('--item', None, int), vl, _arg('--text'), _arg('--bg'),
                          _arg('--scale', None, int), _arg('--out')):
            print(f'sheet: {p}')
    elif cmd == 'screen':
        for p in screen(sys.argv[2], _arg('--acd'), _arg('--anim'), _arg('--frame', 'auto'), _arg('--bg'),
                        _arg('--scale', None, int), _arg('--es-dir'), _arg('--out'), '--sin-marcas' not in sys.argv):
            print(f'sheet: {p}')
    elif cmd == 'tiles':
        tiles_report(_arg('--only'), _arg('--out'))
    elif cmd == 'verify' and '--specs' in sys.argv:
        return 1 if verify_specs(_arg('--specs'), _arg('--out')) else 0
    elif cmd == 'verify':
        return 1 if verify_out(_arg('--out')) else 0
    elif cmd == 'render-all':
        d = Path(sys.argv[2])
        bad = 0
        for f in sorted(d.glob('*.json')):
            try:
                spec = json.loads(f.read_text(encoding='utf-8'))
                if 'rel' not in spec:
                    continue
                render(spec, write='--dry' not in sys.argv, out_dir=_arg('--out'), quiet=True)
                print(f'OK    {f.name}')
            except Exception as e:  # report and continue
                bad += 1
                print(f'ERROR {f.name}: {type(e).__name__}: {e}')
        print(f'{bad} errors')
        return 1 if bad else 0
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, FileNotFoundError) as e:   # usage errors: clear message, no traceback
        print(f'ERROR: {e}')
        sys.exit(1)
