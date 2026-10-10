"""Where the player's copy of the game is (m9.config.json, personal: never shared) and where emulators keep mods."""
import json
import os
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # the repository (or the patcher's bundled files): read-only
# where to write: the repository when run from source; the user's home folder for the frozen patcher app
HOME = Path.home() / 'Medarot9-Patcher' if getattr(__import__('sys'), 'frozen', False) else ROOT
CONFIG = HOME / 'm9.config.json'


class Config:
    def __init__(self):
        self.game = None        # base game: decrypted .3ds/.cci/.cia, or a dumped RomFS folder
        self.update = None      # 1.3.0 update: decrypted .cia, or a dumped folder (optional but recommended)
        self.azahar = None      # the emulator's mods folder (load/mods), when not the one found by itself
        if CONFIG.exists():
            d = json.loads(CONFIG.read_text(encoding='utf-8'))
            self.game, self.update, self.azahar = d.get('game'), d.get('update'), d.get('azahar')

    def save(self):
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({'game': self.game, 'update': self.update, 'azahar': self.azahar}, indent=1) + '\n',
                          encoding='utf-8')


# 3DS emulators that load LayeredFS mods from "<user folder>/load/mods/<title id>/" (Citra and its forks):
# (name, folder name on Windows/macOS, folder name on Linux)
EMULATORS = [('Azahar', 'Azahar', 'azahar-emu'), ('AzaharPlus', 'AzaharPlus', 'azaharplus-emu'),
             ('Lime3DS', 'Lime3DS', 'lime3ds-emu'), ('Citra', 'Citra', 'citra-emu'),
             ('Mandarine', 'Mandarine', 'mandarine-emu')]


def _user_dir(win_mac: str, linux: str) -> Path:
    home = Path.home()
    system = platform.system()
    if system == 'Darwin':
        return home / 'Library' / 'Application Support' / win_mac
    if system == 'Windows':
        return Path(os.environ.get('APPDATA', home / 'AppData' / 'Roaming')) / win_mac
    return Path(os.environ.get('XDG_DATA_HOME', home / '.local' / 'share')) / linux


def emulator_mods():
    """[(emulator name, its mods folder)] of the emulators installed (used) on this computer, Azahar first. In the
    emulator, right click the game > Open Mods Location shows the folder (it is <user folder>/load/mods/<title id>)."""
    return [(name, _user_dir(a, b) / 'load' / 'mods') for name, a, b in EMULATORS if _user_dir(a, b).is_dir()]


def azahar_mods(override=None) -> Path:
    """The mods folder to install into: `override` (any emulator's load/mods folder), else the first emulator found
    on this computer, else Azahar's."""
    if override:
        return Path(override).expanduser()
    found = emulator_mods()
    return found[0][1] if found else _user_dir('Azahar', 'azahar-emu') / 'load' / 'mods'
