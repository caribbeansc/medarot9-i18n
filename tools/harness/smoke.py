#!/usr/bin/env python3
"""smoke.py - Smoke-test suite for the patch deployed on the bench (final check before delivery).

1. NORMAL boot (no test overlays): title -> Continue with the copy of the user's save -> field ->
   Medawatch menu. Captures every step (experiments/harness/shots/smoke_*.png).
2. Tutorial robattle (debug menu): test_tutorial_battle.py.
3. Subset of maps with the map viewer: sweep_maps.py --ids ...
Fails on PANIC, unmapped memory or a hang in any step. The screenshots are reviewed BY EYE.

  python tools/harness/smoke.py [--skip-boot] [--skip-battle] [--skip-maps]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from azahar_rpc import launch, shutdown, USER_DIR, REPO, RPCError  # noqa: E402

LOG = USER_DIR / 'log' / 'azahar_log.txt'
SHOTS = REPO / 'experiments' / 'harness' / 'shots'
H = [sys.executable, str(HERE / 'h.py')]
MAPS = '101,110,116,130,150,153,160,165,200,220,233,310,330,342,400,452,453,456,500,600'


def problems():
    t = LOG.read_text(errors='replace') if LOG.exists() else ''
    return {'panic': t.count('broke execution'), 'unmapped': len(re.findall(r'[Uu]nmapped (Read|Write)', t))}


def boot_flow():
    subprocess.run(H + ['testmod', 'debug_menu', 'off'], capture_output=True)
    subprocess.run(H + ['testmod', 'debug_boot', 'off'], capture_output=True)
    emu = launch()
    emu.pause()
    ok = True
    try:
        steps = [('title', None, 900), ('press_start', 'START', 240), ('title_menu', 'A', 240),
                 ('continue', 'A', 600), ('loading', 'A', 900), ('field', None, 600), ('menu_x', 'X', 240),
                 ('close', 'B', 240)]
        for name, btn, frames in steps:
            if btn:
                emu.press(btn, hold=6, after=frames)
            else:
                emu.run(frames)
            emu.screenshot(SHOTS / f'smoke_{name}.png')
            p = problems()
            print(f'  {name}: {p}')
            if p['panic'] or p['unmapped']:
                ok = False
                break
    except RPCError as e:
        print('  HANG:', e)
        ok = False
    finally:
        shutdown(emu)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-boot', action='store_true')
    ap.add_argument('--skip-battle', action='store_true')
    ap.add_argument('--skip-maps', action='store_true')
    ap.add_argument('--maps', default=MAPS)
    a = ap.parse_args()
    res = {}
    if not a.skip_boot:
        print('[1] normal boot + user save')
        res['boot'] = boot_flow()
    if not a.skip_battle:
        print('[2] tutorial robattle')
        r = subprocess.run([sys.executable, str(HERE / 'test_tutorial_battle.py'), '--steps', '400', '--tag', 'smoke'],
                           capture_output=True, text=True)
        print('  ' + r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-400:])
        res['battle'] = 'completed without problems' in r.stdout
    if not a.skip_maps:
        print('[3] maps')
        r = subprocess.run([sys.executable, str(HERE / 'sweep_maps.py'), '--ids', a.maps], capture_output=True, text=True)
        last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-400:]
        print('  ' + last)
        res['maps'] = 'problems: []' in last
    print('RESULT:', res, '->', 'OK' if all(res.values()) else 'FAILURES')
    return 0 if all(res.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
