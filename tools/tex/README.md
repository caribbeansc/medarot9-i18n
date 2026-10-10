# Translated textures (`.ctpk` and 3D models `.bcmdl`)

The interface images (buttons, menus, battle HUD, posters, Medaforce banners) are CTPK textures (PICA200). The
signs of the world (buildings, street signs, floating labels and 3D battle labels) are textures embedded in CGFX
models (`.bcmdl`). The patch re-letters them in the target language **from the Japanese**, keeping format, size and
style. The deploy overlays `data/romfs_tex_es/` (CTPK and models) on the mod (`data/romfs_tex_<lang>` for each
language).

## Tools
- `tools/ctpk_tool.py`: decodes/encodes CTPK (RGBA8, RGB8, RGBA5551, RGB565, RGBA4, LA8, L8, A8, LA4, L4, A4, ETC1,
  ETC1A4). `replace()` re-encodes in the SAME format and size; the header does not change. Exact round trip in
  lossless formats; in ETC1 the 4x4 blocks that do not change are copied byte for byte and those that change are
  compressed with `etcpak` or with our own ETC1 encoder (the one with the lower error).
  `python tools/ctpk_tool.py roundtrip <ctpk>` to check.
- `tools/tex/cgfx_tex.py`: textures inside CGFX models (`list`/`dump`/`replace`). Same format, size and offsets;
  with the original as reference, the ETC1 blocks and the mipmap areas that do not change stay byte for byte
  identical (the mipmaps of the edited area are regenerated). Byte-for-byte round trip in the 7 formats present in
  the models (RGBA8, RGB8, RGB565, RGBA4, LA8, ETC1, ETC1A4), with and without mipmaps.
- `tools/tex/romfs.py`: reads RomFS files directly from the Japanese ROM (the models that are not in `archive/`,
  e.g. `battle/mdl/`, `mdr/mdl/`, `story/mdl/e_f_*`).
- `tools/tex/texlib.py` (full guide in `translation-work/tex/INSTRUCCIONES_TEX.md`; run it with `python3` =
  `/opt/homebrew/bin/python3`, which has `etcpak`: with `/usr/local/bin/python3` the views come out without the ETC1
  codec and what is written does not match the specs):
  - `list <rel>`, `inspect <rel>`, `boxes <rel>`, `sample <rel> x,y,w,h`: study the original (JP 1.3 and Omnija's
    English version as a layout reference, if it exists).
  - `render <spec.json> [--dry]`: applies the specification (erase the old text + draw the new one) and writes
    `data/romfs_tex_es/<rel>` + previews in `translation-work/tex/preview/` (what will be seen in the game, already
    passed through the codec).
  - `render-all <folder>` (regression), `verify` (every file of `data/romfs_tex_es` has the same size as the original
    and only texture bytes change) and `verify --specs <folder>` (what is written is exactly the current render of
    each spec: detects specs changed after being written).
  - Review and tests (without writing or touching the previews): `variants <spec> --item N --try key=v1,v2` (sheet
    with variants of font, size, box or text of an item, already passed through the codec, on plain backgrounds →
    `translation-work/tex/variantes/`) and `screen <spec | ctpk | acd>` (composes the `.acd` screens with the JP and
    the target-language texture side by side, per state: the label on its real button →
    `translation-work/tex/pantallas/`). `render` warns about the pixels that the spec changes OUTSIDE its boxes.
  - 3D models: `<rel>:<texture>` in the commands; in the spec, `"tex"` and `"also": "auto"` (the same texture in
    several maps: all the copies are written, accumulating on what is already translated in each model); `copies`
    lists the copies; `"segments"` draws a label that the model composes from several strips of the texture;
    `uv <rel:tex>` tells which part of the texture each mesh shows and with what stretching
    (`tools/tex/cgfx_uv.py`, below).
  - `tiles [--only X]`: areas that the `.acd` files stretch (9-slice frames, fills, 1-2 px lines) and that change
    between the JP and what is written: an erasure that eats a piece of a frame changes a whole line of the window,
    and `render` does not warn about it (it is inside the boxes). Fixed with `"protect"` in the spec.
  - Effects: an item's `blur` blurs in premultiplied RGBA (the RGB of a glow stays light even if the alpha drops, as
    in the originals; until 8 Oct 2026 it darkened at the edges) and `"dark_edges": true` stores RGB × alpha for the
    glows and halos that the original stores premultiplied (dark edges: `loading`, `cp1_txt_b9/c9`). Medaforce
    poster styles: `medafuerza`, `medafuerza_oro`, `medafuerza_morado`, `medafuerza_verde`.
- `tools/tex/cgfx_uv.py`: CGFX mesh reader without numpy (meshes → shape → triangles; material → textures) for
  `texlib.py uv`: UV windows of each mesh in texture px (inverted V: y = (1 − v) · height; UVs outside [0, 1]
  wrapped), UV → 3D Jacobian (3D length per texel in x/y, their ratio, and whether the texture axes look rotated) and
  a PNG with the triangles. Only UV set 0 of the interleaved buffers; it applies neither the matrix nor the UV
  animations of the material (monitors, `mdr/mdl/panel.bcmdl`). Based on the readers of the wave-8 labelers.
- `tools/tex/cgfx_inventory.py`: inventory of the textures of the 573 map models (`scan` → index with groups of
  identical pixels; `sheets` → contact sheets to review by eye; `show`/`where`).
- `tools/tex/ctpk_inventory.py`: inventory of ALL the CTPK files (`scan` → `translation-work/tex/ctpk_inv/index.json`
  with group: oleadas, candidata, retrato, medabot, piloto, prueba; `sheets --grupo G` → contact sheets; `show`).
- `tools/tex/pack_texture.py <spec name>...`: after editing a spec of `translation-work/tex/specs/`, renders it
  (`data/romfs_tex_<lang>`), writes its language-pack patch (`langs/<lang>/textures/<rel>.json.gz`, against the
  Japanese texture) and the published spec (`langs/<lang>/texture_specs/`, without the `_` working notes). This is the
  way to change a texture now that `langs/` is the source of truth (Oct 2026).
- `tools/tex/acd.py`: reads the 2D screens (`*.acd`) structurally: animations (`normal`, `select`, `push`,
  `disable`...) → frames → sprites (rectangle on screen, rectangle in the texture, color that multiplies it, `u8`
  texture index and, if present, an SJIS label that the game draws with the font; format in its docstring, checked
  on the 3,060 `.acd` files: the read ends right at the texture table). Index →
  `translation-work/tex/ctpk_inv/sprites.json` (120,670 sprites of 2,947 `.acd` files, 2,128 textures; the earlier
  heuristic reader lost ~12,600 sprites whose texture index it read as `u16`, among them windows and HUD).
  `acd.py dump <acd>` lists a screen. In texlib: `sprites <rel>` (areas of the texture that are visible),
  `inspect <rel> --sprites` (draws them in green), `sprites <rel> --compose` (segments of a label that the screen
  composes from several strips), `sprites <rel> --screen` (position, size, scale and alpha of each area on screen)
  and `screen` (the composed screen).
- `tools/font_es.py`: adds the Spanish letters to the BCFNT fonts (see its docstring).
- Japanese base: `archive/rom_tex/` (CTPK of the ROM), `archive/rom_extract/story/mdl/` (map models),
  `archive/update_extract/romfs/` (what the update changed) and, for the rest, the ROM itself. English base (layout):
  `data/romfs/**.ctpk` (125 by Omnija). The 1.3 update does not change any model with signs.

## Specifications
`translation-work/tex/specs/<key>.json`, with `<key>` = `rel` with `__` (+ `__<texture>` in models). Format in
`translation-work/tex/INSTRUCCIONES_TEX.md`, recipes per family and mistakes to avoid in
`translation-work/tex/LECCIONES.md`, tested templates in `translation-work/tex/specs_ejemplos/` (one or more per
family, 15 in total, 4 of them for 3D models).

## CTPK inventory (Oct 2026)
The 3,725 CTPK files of the ROM (+4 of the update) were reviewed by eye with contact sheets: 306 were already in
the waves and 41 with visible text were added (`translation-work/tex/inventario_ctpk.json`: text, wave and notes of
each one; waves 1–6 and a "pending" 9). The rest: 1,356 Medabot textures and 235 pilot faces of `battle/tex`, 1,440
portraits (`bu*`, `bbu*`, `mup*`; they only carry letters painted on clothes or Medabots), 35 `test*` mock-ups with
placeholder text (unused), 10 `icon*.ctpk` that are not CTPK and ~290 without text. The message
「名前を入力してください。」 of the name screen is in `mdr/tex/bt_title_m8.ctpk` (wave 1), visible strip
[0, 196, 156, 14].

## 3D signs (wave 8)
Inventory in `translation-work/tex/lots_cgfx.json`: 60 signs with text (priority, what they say, proposal, copies)
plus the list of what is NOT translated (logos, emblems painted on Medabots, decorative calligraphy, illegible
text). It was made with contact sheets reviewed by eye: the 573 map models (4,083 textures in 2,076 groups of
identical pixels) and the rest of the RomFS models (battle, effects, menus, gacha, Medabots and characters: 13,628
textures). Examples already written in `data/romfs_tex_es/`: the 学院正門 plaque (`m101_name`, 5 maps), the
グラウンド/部室棟/体育館/武道場 post (`m160_sign`, 3 maps), the battle objective labels «〜狙い»
(`battle/mdl/TGT_N_*`, 4 models) and the floating label «エリアから出る» (`story/mdl/e_f_out`: one line split into two
strips of the texture; the UVs were read from the model).

The black floating labels over the doors (校舎, 男子寮, 女子寮, 部室棟, コンビニ) are NOT textures: they do not
appear in any texture of any `.bcmdl` model of the RomFS, and `mdr/tex/ivt_spot_name.ctpk` is just an empty black
256x32 bar (the label background). The text is drawn with the font at run time: it is the name of the markers of
`story/gdn_kwg|gdn_kbt/*.gdn` (confirmed on the test bench; translated by `python/translate_gdn_labels.py`, see
`CLAUDE.md`).

## Maintenance after the waves (8 Oct 2026, tex-mant-2)
- Premultiplied `blur` and `dark_edges` (above); the 70 specs with `blur` were re-rendered (only `loading` and
  `cp1_load` change, whose JP glow is premultiplied) and the RGB of each glow was measured by alpha ranges against
  the JP: the halo of the main text of `cp1_txt_b9/c9/stop` (battle and mdr) now has dark edges like the original.
- Medaforce posters unified: 56 normal posters with the same scheme (erase `[96,56,320,60]`, box `[106,58,300,54]`,
  cap 24, baseline 94) and styles measured on the JP (thin outline + 5 px depth; new green); `cp1_mf_txt` uses the
  chrome design of its original (like mf050/mf053).
- Stretched strips protected (`set_win_00`, `cp2_state9_b`, `m9_chr_sel05`), codec in `cp1_hantei`, background of
  the logo screen (`mk_logo_comp`, animation `bg`), SAFE DUEL banner (`event11_04`), unified terms (回避 = Eva.,
  わざ = Tec., メダチェンジにきりかえ = Switch to MedaChange). Wave 8: all the specs match what is written and were
  reviewed with their UV windows. The 4 pilot model specs (TGT_N_F, e_f_out, m101_name, m160_sign) are now also in
  `specs/`. Lessons from all the waves integrated in `translation-work/tex/LECCIONES.md`.

## How it was done (Oct 2026)
Workflow by **waves** (user request): a tools agent tries one texture of each family and hardens `texlib.py`; then 9
waves (buttons → menus → HUD → maps → logos → posters → Medaforce → 3D signs → pending) with a labeler + visual
reviewer (Sonnet 5.5); between waves, a maintenance agent integrates the lessons.
`assets/` (147 PNGs to move to English) is an earlier attempt, superseded by this pipeline.
