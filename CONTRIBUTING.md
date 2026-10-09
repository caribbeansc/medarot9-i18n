# Contributing

Thanks for wanting to help. The short version: fix lines, keep the windows happy, never commit game data.

## Fixing a translation

1. `python m9.py game <your dump> --update <your update>` once.
2. `python m9.py extract es` writes `work/es/<path>.tsv` for every script: index, the Japanese line (read from YOUR
   dump), and the current text, side by side. Find the line.
3. Fix it in `langs/es/script/<path>.json` (the entry with that `i`), keeping:
   - codes exactly as they are: colour tags `<c:ff00ff>…<c>`, button icons `$*` `$ｸ`…, variables, `%d` `%s`;
   - term keys: write `{{robattle}}`, not the word, so the name stays changeable in one place;
   - the window: dialogue boxes show 2 lines of about 36 characters and do not scroll; a line break is `\n`.
4. `python m9.py build es` and try it in Azahar (the build refuses lines whose Japanese does not match your dump).
5. Commit `langs/` only. Pull requests that touch `build/`, `dist/`, `work/` or any game file will be asked to
   slim down.

## Changing a name or a term

`langs/<lang>/terms.csv`: change `text` (and `plural`). Every `{{id}}` in the language pack follows.

## Adding a language

Copy `langs/en/` to `langs/<code>/`, set `lang.json`, translate `terms.csv` and the `t` of every line (the
`work/` files show the Japanese). Texts must use characters the game's fonts have: ASCII, plus the Spanish letters
this project draws in (`á é í ó ú ü ñ ¿ ¡`). Other letters need new glyphs (see the fonts section of `docs/TECHNICAL.md` and `tools/font_es.py`).

## Textures

`langs/<lang>/textures/` holds the relabelled textures as patches. To change one, edit its spec in
`langs/<lang>/texture_specs/` and re-render it with `tools/tex/` (see `tools/tex/README.md`); the renderer uses
desktop fonts that are not part of this repository.

## What not to send

Game files, ROM excerpts, the Japanese script, or screenshots full of untranslated Japanese. Fingerprints and your
own words only.
