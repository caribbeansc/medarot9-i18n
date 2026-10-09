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

from m9.cli import BUILD, DIST, languages  # noqa: E402
from m9.config import Config, azahar_mods  # noqa: E402

GAME_TYPES = [('3DS game', '*.3ds *.cci *.cia *.cxi'), ('All files', '*')]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Medarot 9 — translation patcher (Kabuto / Kuwagata)')
        self.resizable(False, False)
        self.cfg = Config()
        self.langs = languages()
        self.q = queue.Queue()
        pad = {'padx': 8, 'pady': 4}
        f = ttk.Frame(self, padding=12)
        f.grid()
        ttk.Label(f, text='Your game (decrypted .3ds / .cia, or a dumped RomFS folder):').grid(row=0, column=0, columnspan=3, sticky='w')
        self.game = tk.StringVar(value=self.cfg.game or '')
        ttk.Entry(f, textvariable=self.game, width=60).grid(row=1, column=0, columnspan=2, **pad)
        ttk.Button(f, text='File…', command=lambda: self._pick(self.game)).grid(row=1, column=2, **pad)
        ttk.Label(f, text='Its 1.3.0 update (decrypted .cia or folder; required):').grid(row=2, column=0, columnspan=3, sticky='w')
        self.update_ = tk.StringVar(value=self.cfg.update or '')
        ttk.Entry(f, textvariable=self.update_, width=60).grid(row=3, column=0, columnspan=2, **pad)
        ttk.Button(f, text='File…', command=lambda: self._pick(self.update_)).grid(row=3, column=2, **pad)
        ttk.Label(f, text='Language:').grid(row=4, column=0, sticky='w')
        self.lang = tk.StringVar(value=self.langs[0]['name'] if self.langs else '')
        ttk.Combobox(f, textvariable=self.lang, values=[l['name'] for l in self.langs], state='readonly',
                     width=20).grid(row=4, column=1, sticky='w', **pad)
        b = ttk.Frame(f)
        b.grid(row=5, column=0, columnspan=3, pady=8)
        self.buttons = [ttk.Button(b, text='Install into Azahar', command=lambda: self._run('install')),
                        ttk.Button(b, text='ZIP for SD card (real 3DS)', command=lambda: self._run('zip')),
                        ttk.Button(b, text='Build files only', command=lambda: self._run('build'))]
        for i, w in enumerate(self.buttons):
            w.grid(row=0, column=i, padx=4)
        self.log = tk.Text(f, width=80, height=14, state='disabled')
        self.log.grid(row=6, column=0, columnspan=3)
        self.after(100, self._poll)

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

    def _run(self, what):
        code = next((l['code'] for l in self.langs if l['name'] == self.lang.get()), None)
        if not code or not self.game.get():
            self._say('Choose your game and a language first.')
            return
        self.cfg.game, self.cfg.update = self.game.get(), self.update_.get() or None
        self.cfg.save()
        for w in self.buttons:
            w.state(['disabled'])
        threading.Thread(target=self._work, args=(what, code), daemon=True).start()

    def _work(self, what, code):
        import shutil
        import zipfile
        from m9.build import build
        from m9.dump import Dump
        try:
            d = Dump(self.cfg.game, self.cfg.update)
            self._say(f'Medarot 9 {d.edition.title()}, version {d.version}. Building {code}…')
            out = BUILD / code
            problems = build(d, code, out, log=self._say)
            mod = out / d.title
            if problems:
                self._say(f'{len(problems)} lines were not written (your dump differs?).')
            if what == 'install':
                dst = azahar_mods(self.cfg.azahar) / mod.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(mod, dst)
                self._say(f'Done: installed into {dst}. Start (or restart) the game in Azahar.')
            elif what == 'zip':
                DIST.mkdir(exist_ok=True)
                z = DIST / f'medarot9-{code}-sdcard.zip'
                with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for f in sorted(mod.rglob('*')):
                        if f.is_file():
                            zf.write(f, f'luma/titles/{mod.name}/' + f.relative_to(mod).as_posix())
                self._say(f'Done: {z}. Unzip it at the root of your SD card and enable game patching in Luma3DS.')
            else:
                self._say(f'Done: {mod}')
        except Exception as e:  # shown to the player, not raised
            self._say(f'Error: {e}')
            if type(e).__name__ not in ('DumpError', 'BuildError', 'PatchError'):     # a bug: details help to report it
                self._say(traceback.format_exc(limit=2))
        finally:
            for w in self.buttons:
                self.after(0, lambda w=w: w.state(['!disabled']))


if __name__ == '__main__':
    App().mainloop()
