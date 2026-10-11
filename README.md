# Medarot 9, in your language

[![Download the patcher](https://img.shields.io/badge/Download-patcher%20for%20Windows%20%C2%B7%20macOS-2ea44f?style=for-the-badge&logo=github)](../../releases/latest)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/caribbeansc)

**メダロット９ カブトVer. / クワガタVer.** (Nintendo 3DS, 2015) never left Japan, so it only speaks Japanese.

**Just want to play?** Grab the ready-to-run patcher for Windows or macOS from the
[**latest release**](../../releases/latest). No Python, no terminal. See
[Play it](#play-it--the-easy-way-no-python-no-terminal) below.

**What this repository is for:** translating the game without reverse-engineering anything. Point it at your own
dump and it builds the translated files for a 3DS emulator (Azahar, Citra, Lime3DS…), a real console running
Luma3DS, or an installable .cia; a language
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
2. **Have your own decrypted copy** of the game (GodMode9 on your console makes it; encrypted dumps are refused):
   - the game: a `.3ds` / `.cci` cartridge dump or a `.cia` (or a RomFS folder dumped with an emulator);
   - its **1.3.0 update** `.cia`, if you want to play with the update (recommended: it fixes and adds things).
3. **Follow the steps for where you play** (click to open). In the patcher you always fill in *Your game*, *Its
   1.3.0 update* (leave it empty for version 1.0), *Version*, *Language* and *What to make*, then click **Make**.
   What it makes goes to the **`Medarot9-Patcher/dist`** folder in your user folder (`dist/` when run from source).

<details>
<summary><b>An emulator on this computer</b> (Azahar, Citra, Lime3DS, AzaharPlus…)</summary>

**With the 1.3.0 update** (recommended)

1. In the emulator, add your game as usual and install its original 1.3.0 update (*File → Install CIA…*).
2. In the patcher: *Your game* = your game; *Its 1.3.0 update* = the update `.cia`.
3. *Version*: **With the 1.3.0 update** · *Language*: yours · *What to make*: **Install into an emulator on this
   computer**.
4. *Emulator*: the patcher lists the emulators it finds. If yours is missing, choose **Other folder…** and pick its
   `load/mods` folder (in the emulator, right-click the game → *Open Mods Location* opens `load/mods/<title id>`: pick
   the `mods` folder one level up).
5. Click **Make**, then start (or restart) the game.

**Without the update (version 1.0)**

1. In the emulator, if the 1.3.0 update is installed, remove it (right-click the game → *Remove* → *Remove
   Installed Update*).
2. In the patcher: only *Your game*; *Version*: **Without the update (version 1.0)**; then steps 3-5 above.

**Back to Japanese:** delete the game's folder inside `load/mods`.

</details>

<details>
<summary><b>An emulator on Android</b> (Azahar, Lime3DS…)</summary>

The patcher runs on a computer; you copy what it makes to the phone.

**With the 1.3.0 update** (recommended)

1. In the patcher: *Your game* = your game; *Its 1.3.0 update* = the update `.cia` (a `.cia` file, not a folder).
2. *Version*: **With the 1.3.0 update** · *Language*: yours · *What to make*: **Installable .cia for a real 3DS
   (FBI)** (it works in emulators too). Click **Make**.
3. You get **`Medarot 9 <edition> (<language>) (update 1.3.0).cia`**: a translated copy of the update. Copy it to
   the phone.
4. In the emulator, add your original game as usual, then install the translated update with its **Install CIA**
   option. If the original update was installed, this one replaces it.

**Without the update (version 1.0)**

1. In the patcher: only *Your game*; *Version*: **Without the update (version 1.0)**; *What to make*: **Installable
   .cia for a real 3DS (FBI)**. Click **Make**.
2. You get a translated copy of the **game**: a `.cia` if your game was a `.cia`, a `.3ds` if it was a `.3ds`/`.cci`.
   Copy it to the phone.
3. A `.3ds`: put it in your games folder and open it. A `.cia`: install it with **Install CIA** instead of the
   original game.
4. The 1.3.0 update must not be installed in the emulator.

**Back to Japanese:** reinstall your original update `.cia` (or your original game, for 1.0).

</details>

<details>
<summary><b>A real 3DS with Luma3DS: game patching</b> (easiest on a console)</summary>

1. In the patcher: *Your game*, and *Its 1.3.0 update* if you play with it; *Version*; *Language*; *What to make*:
   **SD card ZIP for a real 3DS (Luma3DS game patching)**. Click **Make**.
2. You get **`medarot9-<edition>-<version>-<language>-sdcard.zip`**.
3. Turn the 3DS off, put its SD card in the computer and unzip the ZIP at the **root** of the card. It creates
   `luma/titles/<title id>/` with `code.bin` and `romfs/`.
4. Install your original game as usual (unchanged).
   - **With the update:** install your original 1.3.0 update too.
   - **Without it (1.0):** the update must not be installed (to remove it: FBI → *Titles* → the update → *Delete
     Title*).
5. Hold **SELECT** while turning the 3DS on, enable **"Enable game patching"** in the Luma3DS menu and press
   **START** to save. Only the first time.
6. Start the game.

**Back to Japanese:** delete `luma/titles/<title id>/` from the SD card.

</details>

<details>
<summary><b>A real 3DS, installing a .cia with FBI</b> (no game patching)</summary>

**With the 1.3.0 update** (recommended)

1. In the patcher: *Your game* = your game **and** *Its 1.3.0 update* = the update `.cia`. It needs both: the
   update only contains the files that the update changed, and the translated update has to carry every translated
   file.
2. *Version*: **With the 1.3.0 update** · *Language*: yours · *What to make*: **Installable .cia for a real 3DS
   (FBI)**. Click **Make**.
3. You get **`Medarot 9 <edition> (<language>) (update 1.3.0).cia`**: a translated copy of the update. Copy it to
   the SD card.
4. On the 3DS, install your **original** Japanese game as usual (don't patch it).
5. In FBI: *SD* → the folder where you copied it → the `.cia` → **Install CIA**. If the original update was
   installed, this one replaces it.
6. Start the game. You don't need Luma's game patching; don't also put the SD card ZIP on the card.

**Without the update (version 1.0)**

1. In the patcher: only *Your game*; *Version*: **Without the update (version 1.0)**; *What to make*: **Installable
   .cia for a real 3DS (FBI)**. Click **Make**.
2. You get a translated copy of the **game**: **`Medarot 9 <edition> (<language>).cia`** if your game was a `.cia`,
   or a `.3ds` if it was a `.3ds`/`.cci`.
3. From a `.3ds`: copy it to the SD card; in GodMode9 select it → *NCSD image options* → *Build CIA from file*
   (the `.cia` goes to `gm9/out/`).
4. In FBI, install the translated `.cia` **instead of** the original game (if the original is installed, this one
   replaces it).
5. Don't install the 1.3.0 update (to remove it: FBI → *Titles* → the update → *Delete Title*).

**Back to Japanese:** reinstall your original update `.cia` (or your original game, for 1.0).

</details>

<details>
<summary><b>Rebuilding the game yourself</b> (PackHack / HackingToolkit3DS)</summary>

1. In the patcher: *Your game*, and *Its 1.3.0 update* if you play with it; *Version*; *Language*; *What to make*:
   **Files only**. Click **Make**.
2. You get a folder with **`update/`** (with the update) or **`game/`** (without it), each with `exefs/code.bin` and
   `romfs/`.
3. With your tool, extract your original **update** `.cia` (with the update) or your original **game** (without it).
4. Replace `code.bin` in *ExtractedExeFS* with `exefs/code.bin`, and copy everything in `romfs/` into
   *ExtractedRomFS*, overwriting.
5. Rebuild it and install it:
   - **with the update:** your original game, then this rebuilt update;
   - **without it:** this rebuilt game instead of the original, and no 1.3.0 update.

</details>

Nothing else changes: your saves stay the same, and removing the translation gives you the Japanese game back.

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
python m9.py install es        # build and install into an emulator (the first found; --mods <its load/mods>)
python m9.py zip en            # build a ZIP for a real console (Luma3DS game patching)
python m9.py cia es            # an installable translated .cia (the update's, or the game's for 1.0)
python m9.py files es          # exefs/ + romfs/ to rebuild the game yourself (PackHack)
python m9.py build es          # just build, into build/es/
```

Add `--no-update` to make it for the game without its update (version 1.0) when an update is set.

**A save started with an older version** keeps the party Medabots' default names in Japanese, or the earlier
"Coral" instead of "Sango" (the game stores them in the save). With the game closed,
`python tools/save_names.py <save folder> --lang es --write` (or `--lang en`)
puts the translated names in and backs the save up first; the save folder is the one with `user1.b` (Azahar:
`sdmc/Nintendo 3DS/<id>/<id>/title/00040000/00174f00/data/00000001`, Kabuto `00174e00`; or a Checkpoint backup).

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
