#!/usr/bin/env python3
"""h.py - CLI of the test bench (one command per word, chainable).

Examples:
  python tools/harness/h.py launch                 # start the game in the harness Azahar (paused at start)
  python tools/harness/h.py run 120 shot title    # 2 s of game time and a screenshot -> .../shots/title.png
  python tools/harness/h.py press START wait 90 shot menu
  python tools/harness/h.py hold A 30              # hold A for 30 frames
  python tools/harness/h.py stick 0 1 20           # Circle Pad up for 20 frames
  python tools/harness/h.py tap 160 120            # touch the bottom screen
  python tools/harness/h.py save 1 | load 1        # save states (slot)
  python tools/harness/h.py mash A 10 40           # press A 10 times, 40 frames between presses (skip dialogs)
  python tools/harness/h.py status | quit | dialogs   # error dialogs closed automatically
  python tools/harness/h.py testmod debug_boot on    # developer chapter selector (tests only)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from azahar_rpc import Azahar, launch, REPO  # noqa: E402

SHOTS = REPO / 'experiments' / 'harness' / 'shots'


def main(argv):
    emu = None
    i = 0
    while i < len(argv):
        cmd = argv[i].lower()
        i += 1
        if cmd == 'launch':
            emu = launch()
            emu.pause()
            print('launched', emu.status())
            continue
        if emu is None:
            emu = Azahar()
        if cmd == 'status':
            print(emu.status())
        elif cmd in ('run', 'wait'):
            n = int(argv[i]); i += 1
            emu.run(n)
        elif cmd == 'press':
            b = argv[i]; i += 1
            emu.press(*b.split('+'))
        elif cmd == 'hold':
            b, n = argv[i], int(argv[i + 1]); i += 2
            emu.set_input(b.split('+')); emu.run(n); emu.release(); emu.run(2)
        elif cmd == 'mash':
            b, n, gap = argv[i], int(argv[i + 1]), int(argv[i + 2]); i += 3
            for _ in range(n):
                emu.press(*b.split('+'), after=gap)
        elif cmd == 'stick':
            dx, dy, n = float(argv[i]), float(argv[i + 1]), int(argv[i + 2]); i += 3
            emu.stick(dx, dy, n)
        elif cmd == 'tap':
            x, y = int(argv[i]), int(argv[i + 1]); i += 2
            emu.tap(x, y)
        elif cmd == 'shot':
            name = argv[i]; i += 1
            p = emu.screenshot(SHOTS / f'{name}.png')
            print('screenshot', p)
        elif cmd == 'save':
            print('save', emu.save_state(int(argv[i]))); i += 1
        elif cmd == 'load':
            print('load', emu.load_state(int(argv[i]))); i += 1
        elif cmd == 'resume':
            emu.resume()
        elif cmd == 'pause':
            emu.pause()
        elif cmd == 'quit':
            from azahar_rpc import shutdown
            shutdown()
            print('closed')
        elif cmd == 'testmod':
            # test-ONLY overlay on the harness mod (e.g. debug_boot = chapter selector)
            import shutil
            name, state = argv[i], argv[i + 1]; i += 2
            src = Path(__file__).resolve().parent / 'testmods' / name
            live = REPO / 'experiments' / 'harness' / 'run' / 'user' / 'load' / 'mods' / '0004000000174F00'
            for f in src.rglob('*'):
                if f.is_file():
                    dst = live / f.relative_to(src)
                    bak = dst.with_name(dst.name + '.testmod_bak')
                    if state == 'on':
                        if dst.exists() and not bak.exists():
                            shutil.copy2(dst, bak)
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, dst)
                    else:
                        if bak.exists():
                            shutil.move(bak, dst)
                        elif dst.exists() and dst.read_bytes() == f.read_bytes():
                            # only removed if it is the overlay file; otherwise it is the DEPLOYED one (Oct 2026: 'off'
                            # deleted the patch's spt/bootKWG.spt and tests booted with the original script)
                            dst.unlink()
            print('testmod', name, state)
        elif cmd == 'dialogs':
            from azahar_rpc import new_dialogs
            print('\n'.join(new_dialogs()[-20:]) or '(no dialogs)')
        else:
            raise SystemExit(f'unknown command: {cmd}')


if __name__ == '__main__':
    main(sys.argv[1:])
