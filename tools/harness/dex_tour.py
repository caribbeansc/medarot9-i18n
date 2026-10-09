#!/usr/bin/env python3
"""dex_tour.py - Walk through the first N pages of the MEDADEX (the Medawatch encyclopedia) from the user's save
(bench copy) and capture the top screen of each one, to check by eye that the description fits its window
(9 lines, no scroll; Oct 2026). Never saves.

  python tools/harness/dex_tour.py [--n 24]     # screenshots in experiments/harness/shots/dex/ + sheet dex.png
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from azahar_rpc import launch, shutdown, REPO, RPCError  # noqa: E402

OUT = REPO / 'experiments' / 'harness' / 'shots' / 'dex'
H = [sys.executable, str(HERE / 'h.py')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=24)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(H + ['testmod', 'debug_menu', 'off'], capture_output=True)
    emu = launch()
    emu.pause()
    shots = []
    try:
        emu.run(900)
        emu.press('START', hold=6, after=240)
        emu.press('A', hold=6, after=600)          # Continue
        emu.press('A', hold=6, after=900)          # load the save
        emu.run(600)
        emu.tap(270, 205, hold=8, after=300)       # Medadex icon on the Medawatch
        emu.press('A', hold=6, after=240)
        for k in range(a.n):
            p = OUT / f'{k:03d}.png'
            emu.screenshot(p)
            shots.append(p)
            emu.press('DOWN', hold=6, after=90)
    except RPCError as e:
        print('HANG:', e)
    finally:
        shutdown(emu)
    from PIL import Image, ImageDraw
    cols = 4
    sheet = Image.new('RGB', (cols * 400, ((len(shots) + cols - 1) // cols) * 254), 'white')
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(shots):
        if not p.exists():
            continue
        im = Image.open(p).convert('RGB').crop((0, 0, 400, 240))   # top screen only
        x, y = (i % cols) * 400, (i // cols) * 254
        sheet.paste(im, (x, y + 14))
        d.text((x + 3, y + 1), p.stem, fill='black')
    sheet.save(OUT / 'dex.png')
    print('sheet:', OUT / 'dex.png')


if __name__ == '__main__':
    main()
