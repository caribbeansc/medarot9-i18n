# Medarot 9, in your language

[![Download the patcher](https://img.shields.io/badge/Download-patcher%20for%20Windows%20%C2%B7%20macOS-2ea44f?style=for-the-badge&logo=github)](../../releases/latest)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/caribbeansc)

**メダロット９ カブトVer. / クワガタVer.** (Nintendo 3DS, 2015) never left Japan, so it only speaks Japanese.

**Just want to play?** Grab the ready-to-run patcher for Windows or macOS from the
[**latest release**](../../releases/latest). No Python, no terminal. See
[Play it](#play-it--the-easy-way-no-python-no-terminal) below.

**What this repository is for:** translating the game without reverse-engineering anything. Point it at your own
dump and it builds the translated files for the Azahar emulator or for a real console running Luma3DS; a language
is a folder (`langs/<code>/`), and every name and game term lives in one table you can change.

It ships two translations, both covering the game's full text:

| Language | Text | Artwork | State |
|---|---:|---:|---|
| Español (Latinoamérica) | 100% | 413 textures | playable, played in Azahar (PC and Android) |
| English | 100% | 347 textures | playable, tested in Azahar |

Both editions are supported, **Kabuto Ver.** and **Kuwagata Ver.**, with their **1.3.0 update**: you need the game
and its update (install the update in your emulator or console too). The patcher tells the editions apart on its own.

> **You need your own copy of the game.** These tools read the files from your own decrypted dump. They do not
> contain the game and cannot get it for you.

---

## Play it — the easy way (no Python, no terminal)

Download the patcher from the [**latest release**](../../releases/latest). It is built automatically from this
repository and contains nothing from the game.

### Windows

1. Download **`Medarot9-Patcher-Windows.exe`** and double-click it.
2. The first time, Windows may warn that it doesn't recognise the app (free software without a paid publisher
   certificate). Click **More info**, then **Run anyway**.

### macOS

1. Download **`Medarot9-Patcher-macOS.zip`**, double-click it to unpack the app, then **right-click it and choose
   Open** the first time (macOS asks once; click **Open**).

### Then, on either system

1. Point the patcher at your own copy of the game (Kabuto or Kuwagata), **decrypted** (GodMode9 on your console
   does it; files named `*.piratelegit.cia` and other encrypted dumps are refused):
   - the game: a `.3ds`/`.cci` cartridge dump or a `.cia`; or a RomFS folder dumped with Azahar
     (right click the game → *Dump RomFS*);
   - its **1.3.0 update** (`.cia`, or a dumped folder): required, the translation is made for it.
2. Pick a language and click **Install into Azahar** (it writes the mod into Azahar's `load/mods/` folder), or
   **ZIP for SD card** for a real 3DS with Luma3DS:
   - **unzip** it at the root of the SD card (it creates `luma/titles/<title>/` with `romfs/` and `code.bin`);
   - hold **SELECT** while turning the console on and enable **"Enable game patching"** (once);
   - the game and its 1.3.0 update are installed on the console as usual (FBI installs `.cia` files; a `.3ds`/`.cci`
     is a cartridge dump, not something to install). The decrypted copy is only what the patcher reads on your
     computer.
3. Start the game. Nothing else changes: your saves stay the same, and removing the mod folder gives you the
   Japanese game back.

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
python m9.py game <your game .3ds/.cia/folder> --update <your update .cia/folder>
python m9.py install es        # build and install into Azahar
python m9.py zip en            # build a ZIP for a real console
python m9.py build es          # just build, into build/es/
```

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
