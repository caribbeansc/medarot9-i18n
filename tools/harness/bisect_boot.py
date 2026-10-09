#!/usr/bin/env python3
"""bisect_boot.py - Boot the game with a VARIANT of the mod and count PANICs/exceptions.

The variant is built by copying a subset of the deployed mod (FULL) to the harness mods folder.
Usage from code: boot_check(lambda rel: <bool include>, frames=420)."""
import shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from azahar_rpc import launch, shutdown, USER_DIR

MODS = USER_DIR / 'load' / 'mods'
LIVE = MODS / '0004000000174F00'
FULL = MODS / '_full_0004000000174F00'


def stage(include):
    """Copy to LIVE only the files of FULL for which include(rel) is True."""
    if LIVE.exists():
        shutil.rmtree(LIVE)
    n = 0
    for p in FULL.rglob('*'):
        if p.is_file():
            rel = p.relative_to(FULL).as_posix()
            if include(rel):
                dst = LIVE / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                n += 1
    return n


def boot_check(include, frames=420, shot=None):
    n = stage(include)
    log = USER_DIR / 'log' / 'azahar_log.txt'
    emu = launch()
    emu.pause()
    try:
        emu.run(frames)
        ok = True
    except Exception:
        ok = False
    if shot:
        try:
            emu.screenshot(shot)
        except Exception:
            pass
    shutdown(emu)
    time.sleep(0.5)
    txt = log.read_text(errors='replace') if log.exists() else ''
    return {'files': n, 'panics': txt.count('broke execution'), 'exceptions': txt.count('Exception Type'),
            'ran': ok}


def restore():
    if LIVE.exists():
        shutil.rmtree(LIVE)
    shutil.copytree(FULL, LIVE)
