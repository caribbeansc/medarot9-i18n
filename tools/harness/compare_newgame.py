#!/usr/bin/env python3
"""compare_newgame.py - Play the start of a NEW GAME twice with the same button presses: with the original
Japanese game (mods set aside) and with the patch, and save parallel screenshots to compare them (e.g. that the
first robattle uses the same Medabots: historical bug "the Medabot of the test battle changes").

  python tools/harness/compare_newgame.py [--presses 500] [--every 5] [--only es|jp]
Screenshots: experiments/harness/shots/cmp_<jp|es>/p<NNNN>.png. The bench mod is ALWAYS restored at the end.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from azahar_rpc import launch, shutdown, USER_DIR, REPO, RPCError  # noqa: E402

MODS = USER_DIR / 'load' / 'mods' / '0004000000174F00'
PARKED = USER_DIR / 'load' / 'mods_parked_0004000000174F00'
H = [sys.executable, str(HERE / 'h.py')]
REF_NAMING = REPO / 'experiments' / 'harness' / 'shots' / 'newgame' / 'g021.png'


def bottom_diff(png_a, png_b):
    from PIL import Image, ImageChops, ImageStat
    a = Image.open(png_a).convert('L').crop((40, 240, 360, 480)).resize((80, 60))
    b = Image.open(png_b).convert('L').crop((40, 240, 360, 480)).resize((80, 60))
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


def play(tag, presses, every):
    out = REPO / 'experiments' / 'harness' / 'shots' / f'cmp_{tag}'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    subprocess.run(H + ['testmod', 'debug_menu', 'off'], capture_output=True)
    emu = launch()
    emu.pause()
    log = []
    try:
        emu.run(900)
        emu.press('START', hold=6, after=240)
        emu.press('UP', hold=6, after=60)
        emu.press('A', hold=6, after=300)
        named = False
        for i in range(1, presses + 1):
            shot = out / f'p{i:04d}.png'
            emu.screenshot(shot)
            if not named and REF_NAMING.exists() and bottom_diff(shot, REF_NAMING) < 12:
                emu.tap(290, 210, hold=6, after=120)          # OK (default name)
                emu.press('A', hold=6, after=120)               # confirm
                named = True
                log.append(f'{i}: name accepted')
                continue
            emu.press('A', hold=6, after=75)
            if i % every and not (i < 40):
                shot.unlink()
    except RPCError as e:
        log.append(f'HANG: {e}')
    finally:
        shutdown(emu)
    (out / 'log.txt').write_text('\n'.join(log))
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--presses', type=int, default=500)
    ap.add_argument('--every', type=int, default=5)
    ap.add_argument('--only', choices=['es', 'jp'])
    a = ap.parse_args()
    if a.only != 'jp':
        print('ES:', play('es', a.presses, a.every))
    if a.only != 'es':
        if PARKED.exists():
            raise SystemExit(f'{PARKED} already exists: restore it by hand')
        MODS.rename(PARKED)
        try:
            print('JP:', play('jp', a.presses, a.every))
        finally:
            PARKED.rename(MODS)
    print('bench mod present:', MODS.exists())


if __name__ == '__main__':
    main()
