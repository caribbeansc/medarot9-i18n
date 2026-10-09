#!/usr/bin/env python3
"""sweep_maps.py - Load ALL the game's maps (map viewer of the debug menu) with the mod deployed on the
harness and detect PANIC / unmapped accesses / hangs. Captures every map.

Requires the debug_menu test overlay (it turns it on and off by itself). Uses a save state at the map
selector so the emulator is not restarted for every map.

Usage: python tools/harness/sweep_maps.py [--ids 101,150] [--frames 420]
Output: experiments/harness/shots/maps/m<ID>.png and experiments/harness/sweep_maps.json
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from azahar_rpc import launch, shutdown, USER_DIR, REPO, RPCError  # noqa: E402

LOG = USER_DIR / 'log' / 'azahar_log.txt'
OUT = REPO / 'experiments' / 'harness' / 'shots' / 'maps'
H = [sys.executable, str(Path(__file__).resolve().parent / 'h.py')]
SLOT = 9


def map_ids():
    ids = set()
    for root in (REPO / 'archive' / 'rom_extract' / 'story' / 'spt', REPO / 'archive' / 'update_extract' / 'romfs' / 'story' / 'spt'):
        for p in root.glob('m[0-9][0-9][0-9]_*.spt'):
            ids.add(int(p.name[1:4]))
    return sorted(ids)


def problems():
    t = LOG.read_text(errors='replace') if LOG.exists() else ''
    return t.count('broke execution'), len(re.findall(r'[Uu]nmapped (Read|Write)', t))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', default='')
    ap.add_argument('--frames', type=int, default=420)
    a = ap.parse_args()
    ids = [int(x) for x in a.ids.split(',')] if a.ids else map_ids()
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(H + ['testmod', 'debug_menu', 'on'], check=True, capture_output=True)
    results = []
    emu = launch()
    emu.pause()
    try:
        emu.run(600)
        emu.press('DOWN'); emu.press('DOWN')
        emu.press('A', after=600)                     # map viewer (selector at 000)
        emu.save_state(SLOT)
        for mid in ids:
            p0 = problems()
            emu.load_state(SLOT)
            emu.run(20)
            h, t, u = mid // 100, (mid // 10) % 10, mid % 10
            for _ in range(u):
                emu.press('UP', hold=3, after=3)
            emu.press('RIGHT', hold=3, after=3)        # cursor: units -> hundreds
            for _ in range(h):
                emu.press('UP', hold=3, after=3)
            emu.press('RIGHT', hold=3, after=3)        # hundreds -> tens
            for _ in range(t):
                emu.press('UP', hold=3, after=3)
            emu.press('A', after=10)
            status = 'ok'
            try:
                emu.run(a.frames)
            except RPCError:
                status = 'HUNG'
            p1 = problems()
            if p1[0] > p0[0]:
                status = 'PANIC'
            elif p1[1] > p0[1]:
                status = 'UNMAPPED_MEMORY'
            try:
                emu.screenshot(OUT / f'm{mid:03d}.png')
            except RPCError:
                pass
            results.append({'map': mid, 'status': status})
            print(f'm{mid:03d}: {status}', flush=True)
            if status == 'HUNG':
                shutdown(emu)
                emu = launch(); emu.pause(); emu.run(600)
                emu.press('DOWN'); emu.press('DOWN'); emu.press('A', after=600)
                emu.save_state(SLOT)
    finally:
        shutdown(emu)
        subprocess.run(H + ['testmod', 'debug_menu', 'off'], capture_output=True)
        (REPO / 'experiments' / 'harness' / 'sweep_maps.json').write_text(json.dumps(results, indent=1))
    bad = [r for r in results if r['status'] != 'ok']
    print(f'{len(results)} maps; problems: {bad}')


if __name__ == '__main__':
    main()
