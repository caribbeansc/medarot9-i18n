#!/usr/bin/env python3
"""test_scene.py - Jumps to a story event with the developer's chapter selector and plays it (Oct 2026).

A cutscene cannot be started on its own (it needs its map, characters and story state: started from boot it crashes
even in the Japanese game). This uses the developer's chapter selector (`story/spt/dbg_st.spt`, the debug_boot
testmod) with its "chapter 2" branch rewritten for the run, test-only and in the harness mod only:

  original: CLOSE_MESS, CLOSE_MESSWIN, WAIT_FADEOUT, scriptcall dbg02st, scriptcall fadein2, PORTAL <room>
  rewritten: CLOSE_MESS, nameset S9 <Medal name>, scriptcall dbg02st, valueset I33 <story step>, PORTAL <map>,
             scriptcall <event>

dbg02st sets up the chapter 2 party; I33 is the story step the map and the event check; PORTAL is the game's own warp
(area, arrival point, map boot script); the event script is the map's trigger that plays the cutscene(s). The number
of instructions stays the same (the header counts them and jumps are measured in instructions).

Then A is pressed every `--every` frames with a screenshot each time. Failure: PANIC / unmapped memory in the log, or
frames not advancing (RPC error). The mod is always restored.

  python tools/harness/test_scene.py tracks            # preset (see PRESETS)
  python tools/harness/test_scene.py tracks --jp       # the same on the original Japanese game (mod set aside)
  python tools/harness/test_scene.py tracks --mod-romfs data/romfs   # another patch's RomFS (e.g. the previous one)
  python tools/harness/test_scene.py tracks --mod-romfs data/romfs --mod-exefs data/exefs/KWG --no-update
      # the previous patch as its players ran it: its code.bin, on the game WITHOUT the 1.3.0 update (the update is
      # set aside in the harness for the run and put back)
Screenshots: experiments/harness/shots/scene_<preset>_<tag>/.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
from azahar_rpc import launch, shutdown, USER_DIR, REPO, RPCError  # noqa: E402
from m9.dump import Dump  # noqa: E402

LOG = USER_DIR / 'log' / 'azahar_log.txt'
MODS = USER_DIR / 'load' / 'mods'
# edition: (game, update, base title, boot script tag, update title folder)
GAMES = {
    'kuwagata': (REPO / 'roms' / 'Medarot 9 - Kuwagata Ver. (Japan).3ds',
                 REPO / '0004000E00174F00 メダロット９ - クワガタVer. (CTR-U-BB9J) (v1.3.0) (J)(Patch)-decrypted.cia',
                 '0004000000174F00', 'KWG', '00174f00'),
    'kabuto': (REPO / '0004000000174E00 メダロット９ - カブトVer. (CTR-P-BA9J) (v0.2.0) (J)-decrypted.cci',
               REPO / '0004000E00174E00 メダロット９ - カブトVer. (CTR-U-BA9J) (v1.3.0) (J) (Patch)-decrypted.cia',
               '0004000000174E00', 'KBT', '00174e00'),
}

# preset: (story step I33 that the event checks, PORTAL area/point/boot, event script)
PRESETS = {
    'tracks': ('69', '72', 'ダクト前', 'm212_boot', 'f03_025_212_10'),
    'interview': ('101', '107', '扉4前', 'm115_boot', 'f05_180_115_20'),
    'after_tracks': ('70', '52', '倉庫前', 'm230_boot', 'f03_030_230_10'),   # 1.0 script has \rスマホ操作 (removed by 1.3.0)
    'final': ('201', '101', '体育館前', 'm160_boot', 'f11_110_000_00'),     # likewise (last chapter)
}


# The developer's selector itself makes 3 accesses (read, read, write 0x40) to 0x4838xxxx from 0x2D6xxx when an option
# is chosen: the same with the Japanese game and with the patch, also with the selector untouched (1.3.0: 0x4838B3DB
# at 0x2D6A60; 1.0: 0x4838815B at 0x2D62F4). Not counted.
SELECTOR_QUIRK = re.compile(r'@ 0x4838[0-9A-F]{4} at PC 0x002D6[0-9A-F]{3}')


def problems():
    t = LOG.read_text(errors='replace') if LOG.exists() else ''
    bad = [l for l in t.splitlines() if re.search(r'[Uu]nmapped (Read|Write)', l) and not SELECTOR_QUIRK.search(l)]
    return {'panic': t.count('broke execution'), 'unmapped': len(bad)}


def boot_overlay(base: bytes) -> bytes:
    """The debug_boot testmod for any edition: boot sets B16 and its debug branch calls /story/dbg_st."""
    f = base.split(b'\x00')
    want = {819: b'\rflagclear', 831: b'B17', 836: b'/', 838: b'rom_debug_menu'}
    if any(f[i] != v for i, v in want.items()):
        raise SystemExit('boot script layout is not as expected')
    f[819], f[831], f[836], f[838] = b'\rflagset', b'B16', b'/story/', b'dbg_st'
    return b'\x00'.join(f)


def selector(base: bytes, step: str, area: str, point: str, boot: str, event: str, medal: str) -> bytes:
    f = base.split(b'\x00')
    i = f.index(b'dbg02st')
    a, b = i - 5, i + 7                    # \rgosub CLOSE_MESSWIN ... m007_boot
    want = [b'\rgosub', b'CLOSE_MESSWIN', b'\rgosub', b'WAIT_FADEOUT', b'\rscriptcall', b'dbg02st', b'\rscriptcall',
            b'fadein2', b'\rgosub', b'PORTAL']
    if f[a:a + 10] != want or f[b] != b'm007_boot':
        raise SystemExit(f'dbg_st chapter 2 branch is not as expected: {f[a:b + 1]}')
    # S9 = the player's Medal name (the partner's name label); 1st_set.spt sets it at the start of a real game
    new = [b'\rnameset', b'S9', medal.encode('cp932'), b'\rscriptcall', b'dbg02st', b'\rvalueset', b'I33', step.encode(),
           b'\rgosub', b'PORTAL', area.encode('cp932'), point.encode('cp932'), boot.encode(),
           b'\rscriptcall', event.encode()]
    out = f[:a] + new + f[b + 1:]
    if sum(p.startswith(b'\r') for p in out) != sum(p.startswith(b'\r') for p in f):
        raise SystemExit('instruction count changed')
    return b'\x00'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('preset', choices=sorted(PRESETS))
    ap.add_argument('--kabuto', action='store_true', help='Kabuto edition (default Kuwagata)')
    ap.add_argument('--jp', action='store_true', help='original Japanese game (mod set aside)')
    ap.add_argument('--mod-romfs', help='use this RomFS folder as the mod (e.g. data/romfs = the previous patch)')
    ap.add_argument('--mod-exefs', help='folder with a code.bin for the mod (with --mod-romfs)')
    ap.add_argument('--no-update', action='store_true', help='set the 1.3.0 update aside for the run')
    ap.add_argument('--medal', help="the player's Medal name (S9); default: the edition's default name, in "
                    "Japanese with --jp, as the patches' 1st_set.spt writes it otherwise")
    ap.add_argument('--rom', help='start this game file instead (e.g. a translated .3ds made by the patcher)')
    ap.add_argument('--tag')
    ap.add_argument('--presses', type=int, default=220)
    ap.add_argument('--every', type=int, default=40)
    a = ap.parse_args()
    step, area, point, boot, event = PRESETS[a.preset]
    ROM, UPDATE, TID, ED, UPD_DIR = GAMES['kabuto' if a.kabuto else 'kuwagata']
    tag = a.tag or ('jp' if a.jp else 'other' if a.mod_romfs else 'patch')
    if a.kabuto:
        tag += '_kabuto'
    out = REPO / 'experiments' / 'harness' / 'shots' / f'scene_{a.preset}_{tag}'
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    d = Dump(ROM, UPDATE)
    mod = MODS / TID
    parked = MODS.parent / f'mods_parked_{TID}'
    if parked.exists():
        raise SystemExit(f'{parked} exists: a previous run did not restore the mod; restore it first')
    sel_rel = Path('romfs/story/spt/dbg_st.spt')
    # both boot scripts: the code.bin picks one by its edition (another edition's code.bin, e.g. the previous patch's
    # Kuwagata code on Kabuto, loads the other one)
    boots = {Path(f'romfs/spt/boot{e}.spt'): boot_overlay(d.read(f'spt/boot{e}.spt')) for e in ('KWG', 'KBT')
             if d.has(f'spt/boot{e}.spt')}
    swap = a.jp or a.mod_romfs
    other = (REPO / a.mod_romfs / 'story/spt/dbg_st.spt') if a.mod_romfs else None
    if other and other.exists():
        base_sel = other.read_bytes()
    elif not swap and (mod / sel_rel).exists():
        base_sel = (mod / sel_rel).read_bytes()
    else:
        base_sel = d.read('story/spt/dbg_st.spt')
    medal = a.medal or {(True, True): 'ジッパー', (True, False): 'Zipper', (False, True): 'ソウエン',
                        (False, False): 'Souen'}[(a.kabuto, a.jp)]
    sel = selector(base_sel, step, area, point, boot, event, medal)          # checked before anything is touched
    saved = {}
    upd = USER_DIR / 'sdmc' / 'Nintendo 3DS' / ('0' * 32) / ('0' * 32) / 'title' / '0004000e' / UPD_DIR
    upd_parked = upd.with_name(UPD_DIR + '_parked')
    if upd_parked.exists():
        raise SystemExit(f'{upd_parked} exists: a previous run did not put the update back; restore it first')
    if a.no_update:
        upd.rename(upd_parked)
    if swap:
        if mod.exists():
            mod.rename(parked)
    else:
        saved = {r: ((mod / r).read_bytes() if (mod / r).exists() else None) for r in (sel_rel, *boots)}
    verdict, emu = 'played to the end of the presses without problems', None
    try:
        if swap:
            (mod / 'romfs').mkdir(parents=True)
            if a.mod_romfs:
                shutil.copytree(REPO / a.mod_romfs, mod / 'romfs', dirs_exist_ok=True)
            if a.mod_exefs:
                shutil.copytree(REPO / a.mod_exefs, mod / 'exefs', dirs_exist_ok=True)
        (mod / sel_rel).parent.mkdir(parents=True, exist_ok=True)
        (mod / sel_rel).write_bytes(sel)
        for r, v in boots.items():
            (mod / r).parent.mkdir(parents=True, exist_ok=True)
            (mod / r).write_bytes(v)
        emu = launch(Path(a.rom).resolve() if a.rom else ROM)
        emu.pause()
        emu.run(900)
        emu.screenshot(out / 'menu.png')
        emu.press('DOWN', after=20)
        emu.press('A', after=20)
        for i in range(a.presses):
            emu.screenshot(out / f'p{i:04d}.png')
            p = problems()
            if p['panic'] or p['unmapped']:
                verdict = f'PROBLEM after {i} presses: {p}'
                break
            emu.press('A', hold=6, after=a.every)
    except RPCError as e:
        verdict = f'HANG (frames stopped advancing): {e}'
    finally:
        try:
            if emu:
                emu.screenshot(out / 'last.png')
        except Exception:
            pass
        shutdown(emu)
        if a.no_update and upd_parked.exists():
            upd_parked.rename(upd)
        if swap:
            shutil.rmtree(mod, ignore_errors=True)
            if parked.exists():
                parked.rename(mod)
        else:
            for r, v in saved.items():
                if v is None:
                    (mod / r).unlink(missing_ok=True)
                else:
                    (mod / r).write_bytes(v)
    print(f'{a.preset} [{tag}]: {verdict}; log {problems()}; shots in {out}')


if __name__ == '__main__':
    main()
