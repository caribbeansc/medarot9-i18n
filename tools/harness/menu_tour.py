#!/usr/bin/env python3
"""menu_tour.py - Walk through the Medawatch menus from the user's save (bench copy) and capture each one to
review texts and textures by eye (leftover Japanese/English, overflows). Never saves: on 'Save' it only opens the
dialog and cancels it with B.

  python tools/harness/menu_tour.py            # screenshots in experiments/harness/shots/tour/ + sheet tour.png
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from azahar_rpc import launch, shutdown, REPO, RPCError  # noqa: E402

OUT = REPO / 'experiments' / 'harness' / 'shots' / 'tour'
H = [sys.executable, str(HERE / 'h.py')]
ICONS = [('parts', 45, 50), ('areamap', 115, 55), ('album', 275, 50), ('save', 55, 125), ('medawatch', 160, 125),
         ('medadata', 265, 125), ('items', 125, 195), ('options', 195, 195), ('medadex', 270, 205)]


def main():
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
        emu.screenshot(OUT / '00_campo.png'); shots.append(OUT / '00_campo.png')
        for k, (name, x, y) in enumerate(ICONS, 1):
            emu.tap(x, y, hold=8, after=300)
            p = OUT / f'{k:02d}_{name}.png'
            emu.screenshot(p); shots.append(p)
            emu.press('A', hold=6, after=240) if name in ('medawatch', 'medadex', 'medadata', 'parts') else None
            p2 = OUT / f'{k:02d}_{name}_2.png'
            emu.screenshot(p2); shots.append(p2)
            for _ in range(4):
                emu.press('B', hold=6, after=120)
            emu.run(120)
    except RPCError as e:
        print('HANG:', e)
    finally:
        shutdown(emu)
    from PIL import Image, ImageDraw
    cols = 4
    sheet = Image.new('RGB', (cols * 200, ((len(shots) + cols - 1) // cols) * 254), 'white')
    d = ImageDraw.Draw(sheet)
    for i, p in enumerate(shots):
        if not p.exists():
            continue
        im = Image.open(p).convert('RGB').resize((200, 240))
        x, y = (i % cols) * 200, (i // cols) * 254
        sheet.paste(im, (x, y + 14)); d.text((x + 3, y + 1), p.stem, fill='black')
    sheet.save(OUT / 'tour.png')
    print('sheet:', OUT / 'tour.png')


if __name__ == '__main__':
    main()
