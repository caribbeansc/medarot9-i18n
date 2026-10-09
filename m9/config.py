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
        self.azahar = None      # Azahar's mods folder, when not the default one
        if CONFIG.exists():
            d = json.loads(CONFIG.read_text(encoding='utf-8'))
            self.game, self.update, self.azahar = d.get('game'), d.get('update'), d.get('azahar')

    def save(self):
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps({'game': self.game, 'update': self.update, 'azahar': self.azahar}, indent=1) + '\n',
                          encoding='utf-8')


def azahar_mods(override=None) -> Path:
    """Azahar's (and Citra's) mods folder on this computer."""
    if override:
        return Path(override).expanduser()
    home = Path.home()
    system = platform.system()
    if system == 'Darwin':
        return home / 'Library' / 'Application Support' / 'Azahar' / 'load' / 'mods'
    if system == 'Windows':
        return Path(os.environ.get('APPDATA', home / 'AppData' / 'Roaming')) / 'Azahar' / 'load' / 'mods'
    return Path(os.environ.get('XDG_DATA_HOME', home / '.local' / 'share')) / 'azahar-emu' / 'load' / 'mods'
