#!/usr/bin/env python3
"""Entry point: run ``python m9.py`` for the menu, or a subcommand directly (``python m9.py --help``)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == '__main__':
    if sys.version_info < (3, 10):
        print(f'Python 3.10 or newer is needed; this is {sys.version.split()[0]}')
        raise SystemExit(3)
    from m9.cli import main
    raise SystemExit(main())
