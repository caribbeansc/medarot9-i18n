#!/usr/bin/env python3
"""test_codebin_variant.py - Test code.bin 1.3 variants on the bench by playing the tutorial robattle
(the battle of the old crash #2: medaforce ハイモビリティ).

  --mode none   normal build (no effect names)                          = reference
  --mode raw    effect names translated IN PLACE without protecting tails = reproduces crash #2
  --mode all    effect names translated + fix_interior (tails)          = candidate
  --text-clean  also the 75 "clean" .text strings

Restores the deployed code.bin when done. Requires the mod deployed on the bench.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'python'))
import codebin13 as CB  # noqa: E402
import apply_m13 as M13  # noqa: E402

EXE = REPO / 'experiments' / 'harness' / 'run' / 'user' / 'load' / 'mods' / '0004000000174F00' / 'exefs' / 'code.bin'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='all', choices=['none', 'raw', 'all'])
    ap.add_argument('--text-clean', action='store_true')
    ap.add_argument('--steps', type=int, default=300)
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    code, rep = CB.build(fps60=True, formal_only=not a.text_clean, overrides=M13.codebin_overrides(),
                         allow_unsafe=None if a.mode == 'none' else 'all', fix_merged=a.mode != 'raw')
    print(f"variant {a.mode}: es={rep['es']} restored={rep.get('interior_restored')} "
          f"relocated={rep.get('interior_relocated')} errors={rep['errors']}")
    bak = EXE.with_suffix('.bin.bak')
    shutil.copy2(EXE, bak)
    try:
        EXE.write_bytes(code)
        r = subprocess.run([sys.executable, str(REPO / 'tools' / 'harness' / 'test_tutorial_battle.py'),
                            '--steps', str(a.steps), '--tag', a.tag or a.mode], capture_output=True, text=True)
        print(r.stdout[-1500:], r.stderr[-800:])
    finally:
        shutil.move(bak, EXE)


if __name__ == '__main__':
    main()
