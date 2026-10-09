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


def _dump(cfg: Config) -> Dump:
    if not cfg.game:
        raise DumpError('point me at your game first: python m9.py game <your .3ds/.cia or RomFS folder> '
                        '[--update <your 1.3.0 update .cia or folder>]')
    return Dump(cfg.game, cfg.update)


def cmd_game(a, cfg):
    if a.path:
        cfg.game = str(Path(a.path).expanduser().resolve())
    if a.update:
        cfg.update = str(Path(a.update).expanduser().resolve())
    d = _dump(cfg)
    cfg.save()
    print(f'game:   {cfg.game}')
    print(f'update: {cfg.update or "(none yet: the translation needs the 1.3.0 update too)"}')
    print(f'Medarot 9 {d.edition.title()} ({d.title}), version {d.version}; {len(d.files())} files')
    return 0


def _build(a, cfg):
    from m9.build import build
    d = _dump(cfg)
    out = BUILD / a.language
    print(f'Building {a.language} for Medarot 9 {d.edition.title()} {d.version} into {out} ...')
    problems = build(d, a.language, out)
    for p in problems[:20]:
        print('  problem:', p)
    if problems:
        print(f'{len(problems)} lines were not written (see above).')
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


def cmd_zip(a, cfg):
    mod = _build(a, cfg)
    DIST.mkdir(exist_ok=True)
    z = DIST / f'medarot9-{a.language}-sdcard.zip'
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(mod.rglob('*')):
            if f.is_file():
                zf.write(f, f'luma/titles/{mod.name}/' + f.relative_to(mod).as_posix())
    print(f'{z}: unzip it at the root of your SD card (Luma3DS: enable "game patching").')
    return 0


def cmd_extract(a, cfg):
    """work/<lang>/<path>.tsv: every translated line next to the Japanese of YOUR dump, for reference."""
    from m9 import script
    d = _dump(cfg)
    pack = ROOT / 'langs' / a.language / 'script'
    out = HOME / 'work' / a.language
    n = 0
    for f in sorted(pack.rglob('*.json')):
        e = json.loads(f.read_text(encoding='utf-8'))
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
                        ('zip', cmd_zip, 'build a ZIP for the SD card of a real console (Luma3DS)')):
        s = sub.add_parser(name, help=h)
        s.add_argument('language')
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
        if not isinstance(e, (DumpError,)) and type(e).__name__ not in ('BuildError', 'PatchError'):
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
    print('  3  Make a ZIP for a real console (Luma3DS)')
    print('  4  Build only (into build/)')
    print('  q  Quit')
    c = input('\n> ').strip().lower()
    if c == '1':
        g = input('Your game (.3ds / .cia / RomFS folder): ').strip().strip('"')
        u = input('Its 1.3.0 update (.cia / folder; Enter to skip): ').strip().strip('"')
        return main(['game', g] + (['--update', u] if u else []))
    if c in ('2', '3', '4'):
        lang = input(f'Language ({", ".join(langs)}): ').strip() or langs[0]
        return main([{'2': 'install', '3': 'zip', '4': 'build'}[c], lang])
    return 0


if __name__ == '__main__':
    sys.exit(main())
