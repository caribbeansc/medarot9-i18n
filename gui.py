#!/usr/bin/env python3
"""The patcher: a small window that builds the translation from your own copy of the game.

  python gui.py          (the release also ships it as a double-clickable app for Windows and macOS)
"""
import queue
import sys
import threading
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tkinter as tk  # noqa: E402
from tkinter import filedialog, ttk  # noqa: E402

from m9.cli import BUILD, DIST, languages, output_name, version_note  # noqa: E402
from m9.config import Config, azahar_mods  # noqa: E402

GAME_TYPES = [('3DS game', '*.3ds *.cci *.cia *.cxi'), ('All files', '*')]

VERSIONS = [('13', 'With the 1.3.0 update (recommended)'),
            ('10', 'Without the update (version 1.0)')]
OUTPUTS = [('azahar', 'Install into Azahar (emulator)'),
           ('zip', 'SD card ZIP for a real 3DS (Luma3DS game patching)'),
           ('cia', 'Installable .cia for a real 3DS (FBI)'),
           ('files', 'Files only (to rebuild the game yourself: PackHack / HackingToolkit3DS)')]
HINTS = {
    ('azahar', '13'): 'Install the game and its 1.3.0 update in Azahar as usual; the translation goes into its mods '
                      'folder.',
    ('azahar', '10'): 'The game must NOT have the 1.3.0 update installed in Azahar (uninstall it).',
    ('zip', '13'): 'Unzip at the root of the SD card. Install the game and its 1.3.0 update as usual. Hold SELECT '
                   'while turning the 3DS on and enable "Enable game patching".',
    ('zip', '10'): 'Unzip at the root of the SD card. Install the game only, NOT the 1.3.0 update. Hold SELECT '
                   'while turning the 3DS on and enable "Enable game patching".',
    ('cia', '13'): 'You get a translated copy of the UPDATE. Install your original game, then this .cia with FBI. '
                   'No game patching needed. (Needs the update as a .cia file.)',
    ('cia', '10'): 'You get a translated copy of the GAME (.cia from a .cia, .3ds from a .3ds). Install it with FBI '
                   'instead of the original; do NOT install the 1.3.0 update.',
    ('files', '13'): 'An "update" folder (exefs/code.bin, romfs/): drop them into the extracted UPDATE '
                     '(ExtractedExeFS / ExtractedRomFS) and rebuild it. The game stays original.',
    ('files', '10'): 'A "game" folder (exefs/code.bin, romfs/): drop them into the extracted GAME '
                     '(ExtractedExeFS / ExtractedRomFS) and rebuild it. Do NOT install the update.',
}


def _luma_path(mod, f):
    """Path inside the SD card for Luma3DS game patching: romfs/ as it is, and code.bin at the title folder's root
    (Luma3DS reads /luma/titles/<title>/code.bin, not exefs/code.bin as Azahar does)."""
    rel = f.relative_to(mod).as_posix()
    if rel.startswith('exefs/'):
        rel = rel[len('exefs/'):]
    return f'luma/titles/{mod.name}/{rel}'


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Medarot 9 — translation patcher (Kabuto / Kuwagata)')
        self.resizable(False, False)
        self.cfg = Config()
        self.langs = languages()
        self.q = queue.Queue()
        pad = {'padx': 8, 'pady': 3}
        f = ttk.Frame(self, padding=12)
        f.grid()
        r = 0
        ttk.Label(f, text='Your game (decrypted .3ds / .cci / .cia, or a dumped RomFS folder):').grid(
            row=r, column=0, columnspan=3, sticky='w')
        r += 1
        self.game = tk.StringVar(value=self.cfg.game or '')
        ttk.Entry(f, textvariable=self.game, width=64).grid(row=r, column=0, columnspan=2, **pad)
        ttk.Button(f, text='File…', command=lambda: self._pick(self.game)).grid(row=r, column=2, **pad)
        r += 1
        ttk.Label(f, text='Its 1.3.0 update (decrypted .cia or folder; not needed for version 1.0):').grid(
            row=r, column=0, columnspan=3, sticky='w')
        r += 1
        self.update_ = tk.StringVar(value=self.cfg.update or '')
        ttk.Entry(f, textvariable=self.update_, width=64).grid(row=r, column=0, columnspan=2, **pad)
        ttk.Button(f, text='File…', command=lambda: self._pick(self.update_)).grid(row=r, column=2, **pad)
        r += 1
        opts = ttk.Frame(f)
        opts.grid(row=r, column=0, columnspan=3, sticky='we', pady=6)
        ver = ttk.LabelFrame(opts, text='Version', padding=6)
        ver.grid(row=0, column=0, sticky='nw', padx=(0, 8))
        self.version = tk.StringVar(value='13' if (self.cfg.update or not self.cfg.game) else '10')
        for i, (k, label) in enumerate(VERSIONS):
            ttk.Radiobutton(ver, text=label, value=k, variable=self.version, command=self._hint).grid(
                row=i, column=0, sticky='w')
        ttk.Label(ver, text='Language:').grid(row=3, column=0, sticky='w', pady=(8, 0))
        self.lang = tk.StringVar(value=self.langs[0]['name'] if self.langs else '')
        ttk.Combobox(ver, textvariable=self.lang, values=[l['name'] for l in self.langs], state='readonly',
                     width=22).grid(row=4, column=0, sticky='w')
        outp = ttk.LabelFrame(opts, text='What to make', padding=6)
        outp.grid(row=0, column=1, sticky='nw')
        self.output = tk.StringVar(value='azahar')
        for i, (k, label) in enumerate(OUTPUTS):
            ttk.Radiobutton(outp, text=label, value=k, variable=self.output, command=self._hint).grid(
                row=i, column=0, sticky='w')
        r += 1
        self.hint = ttk.Label(f, wraplength=640, foreground='#555')
        self.hint.grid(row=r, column=0, columnspan=3, sticky='w', pady=(0, 6))
        r += 1
        self.make = ttk.Button(f, text='Make', command=self._run)
        self.make.grid(row=r, column=0, columnspan=3, pady=4)
        r += 1
        self.log = tk.Text(f, width=86, height=12, state='disabled')
        self.log.grid(row=r, column=0, columnspan=3)
        self._hint()
        self.after(100, self._poll)

    def _hint(self):
        self.hint.configure(text=HINTS[(self.output.get(), self.version.get())])

    def _pick(self, var):
        p = filedialog.askopenfilename(filetypes=GAME_TYPES) or filedialog.askdirectory()
        if p:
            var.set(p)

    def _say(self, msg):
        self.q.put(str(msg))

    def _poll(self):
        while not self.q.empty():
            self.log.configure(state='normal')
            self.log.insert('end', self.q.get() + '\n')
            self.log.see('end')
            self.log.configure(state='disabled')
        self.after(100, self._poll)

    def _run(self):
        code = next((l['code'] for l in self.langs if l['name'] == self.lang.get()), None)
        if not code or not self.game.get():
            self._say('Choose your game and a language first.')
            return
        if self.version.get() == '13' and not self.update_.get():
            self._say('Version 1.3.0 needs the update too (or choose "Without the update (version 1.0)").')
            return
        self.cfg.game, self.cfg.update = self.game.get(), self.update_.get() or None
        self.cfg.save()
        self.make.state(['disabled'])
        threading.Thread(target=self._work, args=(self.output.get(), self.version.get(), code), daemon=True).start()

    def _work(self, what, version, code):
        import shutil
        import zipfile
        from m9 import cia
        from m9.build import build
        from m9.dump import Dump
        try:
            d = Dump(self.cfg.game, self.cfg.update if version == '13' else None)
            self._say(f'Medarot 9 {d.edition.title()}, version {d.version}. Building {code}…')
            out = BUILD / code
            problems = build(d, code, out, log=self._say)
            mod = out / d.title
            if problems:
                self._say(f'{len(problems)} lines were not written (your dump differs?).')
            if what == 'azahar':
                dst = azahar_mods(self.cfg.azahar) / mod.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(mod, dst)
                self._say(f'Done: installed into {dst}. Start (or restart) the game in Azahar.')
            elif what == 'zip':
                DIST.mkdir(exist_ok=True)
                z = DIST / f'medarot9-{d.edition}-{d.version}-{code}-sdcard.zip'
                with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for f in sorted(mod.rglob('*')):
                        if f.is_file():
                            zf.write(f, _luma_path(mod, f))
                self._say(f'Done: {z}.')
            elif what == 'cia':
                self._say('Making the installable copy (a few seconds; the whole game takes longer)…')
                p = cia.make(d, mod, DIST, output_name(d, code), log=self._say)
                self._say(f'Done: {p}')
            else:
                p = cia.split_files(d, mod, DIST / f'{d.edition}-{d.version}-{code}-files')
                self._say(f'Done: {p}')
            self._say(HINTS[(what, version)])
            self._say(version_note(d))
        except Exception as e:  # shown to the player, not raised
            self._say(f'Error: {e}')
            if type(e).__name__ not in ('DumpError', 'BuildError', 'PatchError', 'CiaError'):   # a bug: details help
                self._say(traceback.format_exc(limit=2))
        finally:
            self.after(0, lambda: self.make.state(['!disabled']))


if __name__ == '__main__':
    App().mainloop()
