# Medarot 9, in your language

[![Download the patcher](https://img.shields.io/badge/Download-patcher%20for%20Windows%20%C2%B7%20macOS-2ea44f?style=for-the-badge&logo=github)](../../releases/latest)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/caribbeansc)

**メダロット９ カブトVer. / クワガタVer.** (Nintendo 3DS, 2015) never left Japan, so it only speaks Japanese.

**Just want to play?** Grab the ready-to-run patcher for Windows or macOS from the
[**latest release**](../../releases/latest). No Python, no terminal. See
[Play it](#play-it--the-easy-way-no-python-no-terminal) below.

**What this repository is for:** translating the game without reverse-engineering anything. Point it at your own
dump and it builds the translated files for the Azahar emulator, a real console running Luma3DS, or an installable
.cia; a language
is a folder (`langs/<code>/`), and every name and game term lives in one table you can change.

It ships two translations, both covering the game's full text:

| Language | Text | Artwork | State |
|---|---:|---:|---|
| Español (Latinoamérica) | 100% | 413 textures | playable, played in Azahar (PC and Android) |
| English | 100% | 347 textures | playable, tested in Azahar |

Both editions are supported, **Kabuto Ver.** and **Kuwagata Ver.**, with or without their **1.3.0 update**. The
patcher tells the editions and versions apart on its own.

> **You need your own copy of the game.** These tools read the files from your own decrypted dump. They do not
> contain the game and cannot get it for you.

---

## Play it — the easy way (no Python, no terminal)

1. **Get the patcher** from the [**latest release**](../../releases/latest) (it contains nothing from the game):
   - Windows: **`Medarot9-Patcher-Windows.exe`**, double-click it. The first time Windows may say it doesn't
     recognise the app (free software without a paid certificate): **More info** → **Run anyway**.
   - macOS: **`Medarot9-Patcher-macOS.zip`**, double-click it, then **right-click the app → Open** the first time.
2. **Have your own decrypted copy** of the game (GodMode9 on your console makes it; encrypted dumps such as
   `*.piratelegit.cia` are refused):
   - the game: a `.3ds` / `.cci` cartridge dump or a `.cia` (or a RomFS folder dumped with Azahar);
   - its **1.3.0 update** `.cia`, if you want to play with the update (recommended: it fixes and adds things).
3. **In the patcher**, choose the game (and the update), then:
   - **Version**: *With the 1.3.0 update* or *Without the update (1.0)*;
   - **Language**;
   - **What to make**, from the table below; then click **Make**.

| You play on | Choose | Then |
|---|---|---|
| **Azahar** on this computer | *Install into Azahar* | Start the game. Version 1.0: uninstall the 1.3.0 update in Azahar. |
| **Azahar on Android** | *Installable .cia* | Copy the .cia to the phone and install it in Azahar (*Install CIA*). |
| **A real 3DS** with Luma3DS — **easiest** | *SD card ZIP* | Unzip it at the **root** of the SD card. Install the game as usual (and the 1.3.0 update, if you chose it). Hold **SELECT** while turning the 3DS on and enable **"Enable game patching"** (once). |
| **A real 3DS**, installing with **FBI** | *Installable .cia* | **With the update**: install your **original** game, then the translated **update** `.cia`. **Without it**: install the translated game `.cia` instead of the original (from a `.3ds` you get a `.3ds`: in GodMode9 choose it → *NCSD image options* → *Build CIA from file*), and don't install the update. No game patching needed. |
| Rebuilding the game yourself (**PackHack** / HackingToolkit3DS) | *Files only* | You get `update/` (with the update) or `game/` (without it), each with `exefs/code.bin` and `romfs/`: drop them into the extracted **update** or **game** (*ExtractedExeFS* / *ExtractedRomFS*), rebuild it, and install it. |

Nothing else changes: your saves stay the same, and removing the translation (the mod folder, the SD card folder, or
reinstalling the original `.cia`) gives you the Japanese game back.

## About the translations

- **Español**: translated directly from the Japanese with an LLM, then checked against the Japanese line by line,
  played and corrected in the emulator. The terms follow the Latin American dub of the anime (*robobatalla*,
  *Medafuerza*, *medaguerrero*...). The game's fonts had no `á é í ó ú ü ñ ¿ ¡`: this patch draws them in.
- **English**: based on the fan translation by **Omnija & Sotaeko** (menus, battle, items), kept as they wrote it
  except for serious errors; everything they had not translated (most of the story, help texts, the 1.3.0 update)
  was translated from the Japanese with an LLM. Names follow the official English localisations.

LLM translations are **a starting point, not a finished localisation**: 100% means every line is translated, not
that every line is right. Fixing a line takes a minute and every correction reaches everyone; see
[Fix a line](#fix-a-line-or-add-a-language).

## Use it — from source

You need Python 3.10+ and nothing else:

```
git clone <this repo>
cd medarot9-i18n
python m9.py
```

The menu walks you through it; or directly:

```
python m9.py game <your game .3ds/.cia/folder> --update <your update .cia/folder>   # --update is optional
python m9.py install es        # build and install into Azahar
python m9.py zip en            # build a ZIP for a real console (Luma3DS game patching)
python m9.py cia es            # an installable translated .cia (the update's, or the game's for 1.0)
python m9.py files es          # exefs/ + romfs/ to rebuild the game yourself (PackHack)
python m9.py build es          # just build, into build/es/
```

Add `--no-update` to make it for the game without its update (version 1.0) when an update is set.

`python gui.py` opens the same patcher as the release.

## Change a name or a term everywhere

Every character, Medabot, part, attack, place and game term is written once in `langs/<lang>/terms.csv`; the texts
refer to it as `{{id}}` (`{{id|pl}}` plural, `{{id|cap}}` capitalised, `{{id|up}}` in capitals). Change the `text`
column, rebuild, and the new name is everywhere in the game: dialogue, menus, and the names inside the game's data
tables (Medadex, parts, Medals, Medaforces, enemies).

## Fix a line, or add a language

Each language is a folder:

```
langs/<lang>/
  lang.json            name and settings
  terms.csv            names and terms (see above)
  script/<path>.json   the game's text, one file per game script: index, fingerprint of the Japanese line, text
  binary/<path>.json   patches for the data tables (descriptions, achievements...) and the game's code
  names/<table>.json   the names inside the data tables (Medabots, Medaforces, Medals, parts, enemies), from terms
  textures/<path>.json.gz  the relabelled textures, as patches (only the changed bytes)
  texture_specs/       how each texture was relabelled (tools/tex)
```

The repository never stores the Japanese: each line carries a fingerprint of the Japanese line it replaces, and the
build checks it against your dump. To see the Japanese next to a line, see [CONTRIBUTING.md](CONTRIBUTING.md).
Technical notes on the game's formats: [docs/](docs/).

## Credits

See [NOTICE](NOTICE). Code: MIT ([LICENSE](LICENSE)). Translations: CC BY-SA 4.0
([LICENSE-TRANSLATIONS](LICENSE-TRANSLATIONS)).
