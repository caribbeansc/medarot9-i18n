"""The command line, and the menu that stands in front of it."""
import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

from m9.config import HOME, ROOT, Config, azahar_mods
from m9.dump import Dump, DumpError

BUILD = HOME / 'build'
DIST = HOME / 'dist'


def languages():
    out = []
    for d in sorted((ROOT / 'langs').iterdir()):
        if (d / 'lang.json').exists():
            out.append(json.loads((d / 'lang.json').read_text(encoding='utf-8')))
    return out


def _dump(cfg: Config, no_update=False) -> Dump:
    if not cfg.game:
        raise DumpError('point me at your game first: python m9.py game <your .3ds/.cia or RomFS folder> '
                        '[--update <your 1.3.0 update .cia or folder>]')
    return Dump(cfg.game, None if no_update else cfg.update)


def version_note(d: Dump) -> str:
    """What the player has to do on their console/emulator for this version."""
    if d.version == '1.0':
        return ('Made for the game WITHOUT its update (1.0): do not install the 1.3.0 update (uninstall it if it is '
                'installed), or the game will not match these files.')
    return 'Made for the game WITH its 1.3.0 update: install the update too.'


def cmd_game(a, cfg):
    if a.path:
        cfg.game = str(Path(a.path).expanduser().resolve())
    if a.update:
        cfg.update = str(Path(a.update).expanduser().resolve())
    d = _dump(cfg)
    cfg.save()
    print(f'game:   {cfg.game}')
    print(f'update: {cfg.update or "(none: the translation is made for the game alone, version 1.0)"}')
    print(f'Medarot 9 {d.edition.title()} ({d.title}), version {d.version}; {len(d.files())} files')
    return 0


def _build(a, cfg, d=None):
    from m9.build import build
    d = d or _dump(cfg, getattr(a, 'no_update', False))
    out = BUILD / a.language
    print(f'Building {a.language} for Medarot 9 {d.edition.title()} {d.version} into {out} ...')
    problems = build(d, a.language, out)
    for p in problems[:20]:
        print('  problem:', p)
    if problems:
        print(f'{len(problems)} lines were not written (see above).')
    print(version_note(d))
    return out / d.title


def cmd_build(a, cfg):
    _build(a, cfg)
    return 0


def cmd_install(a, cfg):
    mod = _build(a, cfg)
    dst = azahar_mods(a.azahar or cfg.azahar) / mod.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(mod, dst)
    print(f'Installed into {dst}. Restart the game in Azahar.')
    return 0


def _luma_path(mod, f):
    """Path inside the SD card for Luma3DS game patching: romfs/ as it is, and code.bin at the title folder's root
    (Luma3DS reads /luma/titles/<title>/code.bin, not exefs/code.bin as Azahar does)."""
    rel = f.relative_to(mod).as_posix()
    if rel.startswith('exefs/'):
        rel = rel[len('exefs/'):]
    return f'luma/titles/{mod.name}/{rel}'


def cmd_zip(a, cfg):
    d = _dump(cfg, a.no_update)
    mod = _build(a, cfg, d)
    DIST.mkdir(exist_ok=True)
    z = DIST / f'medarot9-{d.edition}-{d.version}-{a.language}-sdcard.zip'
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(mod.rglob('*')):
            if f.is_file():
                zf.write(f, _luma_path(mod, f))
    print(f'{z}: unzip it at the root of your SD card (Luma3DS: enable "game patching").')
    return 0


def output_name(d: Dump, lang: str) -> str:
    name = next((l['name'] for l in languages() if l['code'] == lang), lang)
    return f'Medarot 9 {d.edition.title()} ({name})'


def cmd_cia(a, cfg):
    from m9 import cia
    d = _dump(cfg, a.no_update)
    mod = _build(a, cfg, d)
    out = cia.make(d, mod, DIST, output_name(d, a.language))
    if d.version == '1.3':
        print(f'{out}\nInstall your ORIGINAL game, then this translated update, with FBI (Luma3DS). In Azahar: '
              f'File > Install CIA. It replaces the 1.3.0 update; nothing else is needed (no game patching).')
    elif str(out).endswith('.3ds'):
        print(f'{out}\nA translated .3ds of the game (1.0). Azahar opens it directly. For a console, copy it to the '
              f'SD card and in GodMode9 choose it > NCSD image options > Build CIA from file, then install that '
              f'.cia with FBI. Do not install the 1.3.0 update.')
    else:
        print(f'{out}\nInstall it with FBI instead of the original game (1.0). Do not install the 1.3.0 update.')
    return 0


def cmd_files(a, cfg):
    from m9 import cia
    d = _dump(cfg, a.no_update)
    mod = _build(a, cfg, d)
    out = cia.split_files(d, mod, DIST / f'{d.edition}-{d.version}-{a.language}-files')
    print(f'{out}: exefs/code.bin and romfs/ to drop into the {"update" if d.version == "1.3" else "game"}\'s '
          f'extracted ExtractedExeFS / ExtractedRomFS (PackHack / HackingToolkit3DS), then rebuild it.')
    return 0


def cmd_extract(a, cfg):
    """work/<lang>/<path>.tsv: every translated line next to the Japanese of YOUR dump, for reference."""
    from m9 import script
    d = _dump(cfg)
    pack = ROOT / 'langs' / a.language / 'script'
    out = HOME / 'work' / a.language
    n = 0
    for f in sorted(pack.rglob('*.json')):
        if f.name.endswith('.v10.json') != (d.version == '1.0') and f.with_name(f.name.replace('.v10', '')) != f:
            continue
        e = json.loads(f.read_text(encoding='utf-8'))
        if not d.has(e['file']):
            continue
        jp = script.fields(d.read(e['file']))
        rows = ['index\tjapanese\ttext']
        for line in e['lines']:
            j = jp[line['i']].decode('cp932', 'replace') if line['i'] < len(jp) else ''
            esc = lambda t: t.replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n').replace('\r', '\\r')
            rows.append(f"{line['i']}\t{esc(j)}\t{esc(line.get('t', '<' + line.get('hex', '') + '>'))}")
        dst = out / (e['file'][:-4] + '.tsv')
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text('\n'.join(rows) + '\n', encoding='utf-8')
        n += 1
    print(f'{n} files in {out} (Japanese from your dump: keep them out of the repository)')
    return 0


def cmd_languages(a, cfg):
    for l in languages():
        print(f"  {l['code']:4} {l['name']}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='m9.py', description='Medarot 9 (Kabuto / Kuwagata) translation toolkit')
    sub = ap.add_subparsers(dest='cmd')
    s = sub.add_parser('game', help='point me at your game (and its 1.3.0 update)')
    s.add_argument('path', nargs='?')
    s.add_argument('--update')
    s.set_defaults(fn=cmd_game)
    for name, fn, h in (('build', cmd_build, 'build the translated files into build/<language>/'),
                        ('install', cmd_install, 'build and install into Azahar'),
                        ('zip', cmd_zip, 'build a ZIP for the SD card of a real console (Luma3DS)'),
                        ('cia', cmd_cia, 'build an installable translated .cia (FBI) into dist/'),
                        ('files', cmd_files, 'build the files to rebuild the game yourself (PackHack) into dist/')):
        s = sub.add_parser(name, help=h)
        s.add_argument('language')
        s.add_argument('--no-update', action='store_true',
                       help='for the game WITHOUT its 1.3.0 update (version 1.0), even if an update is set')
        if name == 'install':
            s.add_argument('--azahar', help="Azahar's mods folder, if not the default one")
        s.set_defaults(fn=fn)
    s = sub.add_parser('extract', help='write work/<language>/: each line next to the Japanese of your dump')
    s.add_argument('language')
    s.set_defaults(fn=cmd_extract)
    s = sub.add_parser('languages', help='list the languages')
    s.set_defaults(fn=cmd_languages)
    a = ap.parse_args(argv)
    cfg = Config()
    if not getattr(a, 'fn', None):
        return menu(cfg)
    try:
        return a.fn(a, cfg)
    except Exception as e:                  # DumpError, BuildError, PatchError: a message, not a traceback
        if not isinstance(e, (DumpError,)) and type(e).__name__ not in ('BuildError', 'PatchError', 'CiaError'):
            raise
        print(f'error: {e}')
        return 2


def menu(cfg):
    langs = [l['code'] for l in languages()]
    print('Medarot 9 (Kabuto / Kuwagata) — translation toolkit\n')
    print(f'  game:   {cfg.game or "(not set)"}')
    print(f'  update: {cfg.update or "(not set)"}\n')
    print('  1  Point me at the game')
    print('  2  Install a language into Azahar')
    print('  3  Make a ZIP for a real console (Luma3DS game patching)')
    print('  4  Make an installable .cia (real console, FBI)')
    print('  5  Make the files to rebuild the game yourself (PackHack)')
    print('  6  Build only (into build/)')
    print('  q  Quit')
    c = input('\n> ').strip().lower()
    if c == '1':
        g = input('Your game (.3ds / .cia / RomFS folder): ').strip().strip('"')
        u = input('Its 1.3.0 update (.cia / folder; Enter for the game alone, version 1.0): ').strip().strip('"')
        return main(['game', g] + (['--update', u] if u else []))
    if c in ('2', '3', '4', '5', '6'):
        lang = input(f'Language ({", ".join(langs)}): ').strip() or langs[0]
        extra = []
        if cfg.update and input('With the 1.3.0 update? [Y/n] ').strip().lower().startswith('n'):
            extra = ['--no-update']
        return main([{'2': 'install', '3': 'zip', '4': 'cia', '5': 'files', '6': 'build'}[c], lang] + extra)
    return 0


if __name__ == '__main__':
    sys.exit(main())
