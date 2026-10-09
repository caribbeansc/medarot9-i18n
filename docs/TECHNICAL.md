# How Medarot 9 keeps its text, and how this project changes it

For contributors who know Python but have never modified a 3DS game. Everything here was learned the hard way
(and verified in the emulator); when this document and the code disagree, the code wins.

## The game and its update

- Two editions: Kuwagata Ver. (title `0004000000174F00`, update `0004000E00174F00`) and Kabuto Ver.
  (`0004000000174E00`, update `0004000E00174E00`). With the 1.3.0 update both have exactly the same RomFS files;
  only `code.bin` differs (`.text` is 8 bytes shorter in Kabuto, `.rodata`/`.data` at the same addresses), so a
  language pack has one code patch per edition and shares everything else.
- The update ships a **partial** RomFS (994 files against the base game's ~23,000): the game loads a file from the
  update when the update has it, and from the base game otherwise. `m9/dump.py` reproduces that rule.
- Azahar (and Luma3DS) apply the mod folder of the base title to the update too: for every path in the mod, the game
  sees OUR file. A file in the mod must therefore be built on the version the game would load (1.3 when the update
  has it), or it silently reverts the update's change.
- `code.bin` is stored compressed (BLZ, backward LZ77) in the ExeFS; mods may hold it decompressed.
- The game looks for EVERY file in the update first (checked in the emulator: a translated update whose RomFS also
  carries files the original update does not have shows them translated). That is why a translated copy of the
  update alone is enough to install with FBI (`m9/cia.py`).
- **Version 1.0** (no update): 3,828 of the 3,882 translated scripts and almost every other file are the same as in
  1.3.0. What the update changed has a 1.0 variant in the pack (`<name>.v10.json`, made by `tools/port_v10.py`); the
  build picks for each game file the variant whose fingerprints / SHA-1 match. `code.bin` 1.0: `.rodata` and `.data`
  are byte for byte those of 1.3.0 one page (0x1000) lower, except pointer words; the translated strings in `.text`
  are found by their Japanese bytes.

## Scripts (`.spt`)

A script is a list of fields separated by NUL bytes. A field starting with a lone CR (`0x0D`, never followed by
`0x0A`) is a **command**; the fields after it, up to the next command, are its arguments.

- Text is Shift-JIS (cp932). `\r\n` inside a text is a line break; a lone `\r` is a command separator: turning one
  into `\n` (or writing text over the next command) breaks the script (black screen, hang).
- **Never change the number or order of fields.** Jumps are relative and counted in commands (`\r{N` and `\r}M`
  point to the same target; `N - M` is the size of the block): inserting a field shifts every jump that crosses it.
  Text that does not fit is shortened, never paginated.
- `message mbox0 <arg> <arg>...`: the arguments are concatenated in the box; variables (`S8` = the player's name,
  `S9`/`S10` = Medabot names...) are separate arguments, so the text around them is split in pieces.
- Dialogue boxes show **2 lines and do not scroll**; consecutive messages without a `KEY_WAIT` stack in the same box.
  Width: about 356 px of the proportional dialogue font (`font16`), i.e. ~36-40 characters. The Medadex window shows
  9 lines (font14, scale ~1.06); the slanted help panel of the upper screen ~9 lines of ~238 px.
- `ifname S0 == <text>` compares the option the player chose, byte for byte: a menu option and its comparison must
  be the same text.
- Furigana is written `<kanji@NN reading>`; translations drop the wrapper. Colour: `<c:RRGGBB>…<c>`. Button icons:
  `$` followed by one byte (`$*` = A, `$ｸ`...).
- The name-entry keyboard needs a full-width default name (`テンマ`): those defaults stay Japanese.

## Data tables (`romfs/param/*.b`)

Fixed-size records (part names, Medabot data), length-prefixed strings (`<len><bytes>`) mixed with ids and values,
or sequences of records (`RotationText.b`, `ResultsData.b`, `MemoData.b`). Bytes ≥ 0x80 are often data, not text:
resizing a record that the game reads by offset corrupts the table (the game panics at boot). The language packs
store these as binary patches made against the Japanese file.

## The code (`code.bin`)

- Sections: `.text` (code with some strings merged in), `.rodata`, `.data`. Writing over a string that is really
  code crashes the game ("undefined instruction").
- The linker **merges string tails**: `"B"` can be the last byte of `ハイモビリティ`, and a pointer points into the
  middle of another string. A translation must keep those tails (`Hi-Mobility` is 11 bytes for that reason).
- A translation longer than its slot is moved to the free padding at the end of `.rodata` and its pointer is
  redirected (only for strings referenced by u32 pointers, never by `adr`).
- The text engine read single-byte characters as **signed** (`ldrsb`), so bytes ≥ 0x80 had no glyph; the patch
  changes the two reads (draw and measure) to `ldrb`. That is what lets the Spanish letters exist.

## Fonts and the Spanish letters

The fonts (`*.bcfnt`, CFNT/TGLP/CWDH/CMAP) have no `á é í ó ú ü ñ ¿ ¡`. Sixteen half-width katakana (`0xC0`-`0xCF`,
one byte each, never used by the game's text) are redrawn as those letters in the seven fonts that show text, with
the width of their base letter. Two-byte characters cannot be used: they always advance the font's fixed width. The
codec `sjis_es` (`m9/codec.py`) maps the letters to those bytes.

## Textures

Labels drawn in textures (`.ctpk`, and signs inside `.bcmdl` models, CGFX) are relabelled by `tools/tex/` from a
spec per texture (boxes to erase, text, font, size, outline); see `tools/tex/README.md`. The language packs ship the
result as patches.

## The language pack format

See `m9/script.py` (script lines with fingerprints), `m9/patch.py` (binary patches) and `m9/terms.py` (term keys).
1.0 variants: same formats with `"game": "1.0"`, next to the 1.3.0 file.

## Installable copies (`m9/cia.py`)

The RomFS is rebuilt from scratch (level 3 directory/file tables and data, then the IVFC SHA-256 tree over 4 KiB
blocks), the ExeFS gets the translated `.code` stored decompressed (extended header flag cleared), and the NCCH and
CIA headers get their new sizes and hashes; certificates, ticket, e-manual and meta block are copied from the player's
`.cia`. The copies are decrypted and not signed by Nintendo: a console with Luma3DS (or Azahar) installs them.
A `.3ds` input gives a `.3ds` (GodMode9 builds the `.cia` on the console with the console's own certificates).
