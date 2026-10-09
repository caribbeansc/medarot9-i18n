#!/usr/bin/env python3
"""test_tutorial_battle.py - Automatic test of the tutorial robattle (the one from the old crash #2).

Starts the game with the developer's debug menu (testmod debug_menu), enters
Robattle > Tutorial > Tuto 1 and advances the battle by pressing A (and sometimes UP/DOWN to pick
parts), watching for: game PANIC/exceptions, unmapped memory accesses (null-deref) and
freezes (frames not advancing). Saves periodic screenshots to experiments/harness/shots/tuto_*.png.

Usage: python tools/harness/test_tutorial_battle.py [--steps 120] [--tag base]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from azahar_rpc import launch, shutdown, USER_DIR, REPO, RPCError  # noqa: E402

LOG = USER_DIR / 'log' / 'azahar_log.txt'
SHOTS = REPO / 'experiments' / 'harness' / 'shots'
H = [sys.executable, str(Path(__file__).resolve().parent / 'h.py')]


def log_problems():
    t = LOG.read_text(errors='replace') if LOG.exists() else ''
    return {'panic': t.count('broke execution'), 'exception': t.count('Exception Type'),
            'unmapped': len(re.findall(r'[Uu]nmapped (Read|Write)', t))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--steps', type=int, default=120)
    ap.add_argument('--tag', default='base')
    a = ap.parse_args()
    subprocess.run(H + ['testmod', 'debug_menu', 'on'], check=True, capture_output=True)
    emu = launch()
    emu.pause()
    try:
        emu.run(600)
        emu.press('DOWN'); emu.press('A', after=240)                      # Robattle
        for _ in range(9):
            emu.press('DOWN', after=6)
        emu.press('A', after=600)                                        # Tutorial
        emu.press('A', after=900)                                        # Tuto 1
        emu.screenshot(SHOTS / f'tuto_{a.tag}_000.png')
        last = emu.status()['frame']
        cycle = ['RIGHT', 'A', 'A', 'A', 'LEFT', 'A', 'A', 'UP', 'A', 'A', 'DOWN', 'A', 'A', 'R', 'A', 'X', 'A', 'A']
        for step in range(1, a.steps + 1):
            btn = cycle[step % len(cycle)]
            try:
                emu.press(btn, hold=4, after=50)
            except RPCError as e:
                print(f'step {step}: FROZEN ({e})')
                break
            p = log_problems()
            if p['panic'] or p['unmapped']:
                print(f'step {step}: PROBLEM {p}')
                emu.screenshot(SHOTS / f'tuto_{a.tag}_fallo.png')
                break
            if step % 20 == 0:
                emu.screenshot(SHOTS / f'tuto_{a.tag}_{step:03d}.png')
                st = emu.status()
                print(f'step {step}: frame {st["frame"]} {p}')
                last = st['frame']
        else:
            print('completed without problems', log_problems())
        emu.screenshot(SHOTS / f'tuto_{a.tag}_fin.png')
    finally:
        shutdown(emu)
        subprocess.run(H + ['testmod', 'debug_menu', 'off'], capture_output=True)


if __name__ == '__main__':
    main()
