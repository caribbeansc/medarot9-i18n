#!/usr/bin/env python3
"""
azahar_rpc.py - Client for the automated test bench (Azahar built with the extended RPC).

The local Azahar build (experiments/harness/azahar-src, patch in tools/harness/azahar-harness.patch)
extends the RPC server (UDP 45987) with: button/Circle Pad/touch injection, PNG screenshots,
frame-by-frame execution (deterministic pause), save states and speed control. Reading/writing
RAM was already part of Azahar.

ISOLATED environment: the build uses the portable folder experiments/harness/run/user (config, saves,
installed 1.3.0 update and its own mods). It never touches the user's Azahar.

Basic usage:
    from azahar_rpc import Azahar, launch
    emu = launch()                    # starts the game and waits for the RPC
    emu.run(600)                      # advances 600 frames (10 s of game time) at maximum speed
    emu.press('A')                    # presses A (4 frames) and releases (4 frames)
    emu.screenshot('shot.png')        # captures both screens
    emu.save_state(1); emu.load_state(1)
    emu.read(0x08000000, 16)          # RAM of the game process
"""
import os
import random
import socket
import struct
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / 'experiments' / 'harness'
AZAHAR_BIN = HARNESS / 'azahar-src' / 'build' / 'bin' / 'Release' / 'azahar.app' / 'Contents' / 'MacOS' / 'azahar'
USER_DIR = HARNESS / 'run' / 'user'
ROM = Path(os.environ['M9_BENCH_ROM']) if os.environ.get('M9_BENCH_ROM') else \
    REPO / 'roms' / 'Medarot 9 - Kuwagata Ver. (Japan).3ds'      # M9_BENCH_ROM: another copy (.3ds/.cxi) of the game
TITLE_ID = 0x0004000000174F00

PORT = 45987
VERSION = 1
MAX_DATA = 1024
PT = {'ReadMemory': 1, 'WriteMemory': 2, 'ProcessList': 3, 'SetGetProcess': 4,
      'SetInput': 100, 'Screenshot': 101, 'RunFrames': 102, 'Pause': 103, 'Resume': 104,
      'SaveState': 105, 'LoadState': 106, 'SetSpeed': 107, 'Status': 108}
BUTTONS = {'A': 0, 'B': 1, 'SELECT': 2, 'START': 3, 'RIGHT': 4, 'LEFT': 5, 'UP': 6, 'DOWN': 7,
           'R': 8, 'L': 9, 'X': 10, 'Y': 11}


class RPCError(RuntimeError):
    pass


class Azahar:
    def __init__(self, host='127.0.0.1', port=PORT, timeout=30.0):
        self.addr = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)
        self.pid = None

    # -- transport --------------------------------------------------------------------------
    def _req(self, ptype: str, data: bytes = b'', timeout: float = None) -> bytes:
        if len(data) < 8:
            data = data + b'\x00' * (8 - len(data))
        if len(data) > MAX_DATA:
            raise ValueError('packet too large')
        rid = random.getrandbits(32)
        self.sock.sendto(struct.pack('<IIII', VERSION, rid, PT[ptype], len(data)) + data, self.addr)
        old = self.sock.gettimeout()
        if timeout is not None:
            self.sock.settimeout(timeout)
        try:
            while True:
                resp, _ = self.sock.recvfrom(MAX_DATA + 64)
                ver, rid2, pt, size = struct.unpack_from('<IIII', resp)
                if rid2 == rid:
                    return resp[16:16 + size]
        except socket.timeout as e:
            raise RPCError(f'no response to {ptype}') from e
        finally:
            self.sock.settimeout(old)

    # -- state / time control -----------------------------------------------------------
    def status(self) -> dict:
        d = self._req('Status', timeout=5)
        frame, adv, powered = struct.unpack_from('<QII', d)
        return {'frame': frame, 'paused': bool(adv), 'powered': bool(powered)}

    def pause(self):
        return self._req('Pause')

    def resume(self):
        return self._req('Resume')

    def run(self, frames: int, timeout_ms: int = 5000) -> int:
        """Advance N frames (60 = 1 s of game time) with no limiter and leave the game paused."""
        done_total = 0
        while frames > 0:
            n = min(frames, 3600)
            d = self._req('RunFrames', struct.pack('<II', n, timeout_ms), timeout=n * timeout_ms / 1000 + 10)
            frame, done = struct.unpack_from('<QI', d)
            done_total += done
            if done < n:
                raise RPCError(f'run: only {done}/{n} frames advanced (game hung or loading)')
            frames -= n
        return done_total

    def set_speed(self, percent: int):
        """0 = unlimited (turbo), 100 = normal. Only affects free-running mode (resume)."""
        self._req('SetSpeed', struct.pack('<II', percent, 0))

    # -- input -------------------------------------------------------------------------------
    def set_input(self, buttons=(), circle=None, touch=None):
        mask = 0
        for b in buttons:
            mask |= 1 << BUTTONS[b.upper()]
        flags = 1 | (2 if circle is not None else 0) | (4 if touch is not None else 0)
        cx, cy = circle if circle is not None else (0, 0)
        tx, ty = touch if touch is not None else (0, 0)
        self._req('SetInput', struct.pack('<IIhhHH', mask, flags, int(cx), int(cy), int(tx), int(ty)))

    def release(self):
        self._req('SetInput', struct.pack('<IIhhHH', 0, 0, 0, 0, 0, 0))

    def press(self, *buttons, hold=4, after=4):
        """Press the buttons for `hold` frames, release and wait `after` frames."""
        self.set_input(buttons)
        self.run(hold)
        self.release()
        self.run(after)

    def tap(self, x, y, hold=4, after=4):
        """Touch the bottom screen at (x, y) pixels (0-319, 0-239)."""
        self.set_input(touch=(x, y))
        self.run(hold)
        self.release()
        self.run(after)

    def stick(self, dx, dy, frames):
        """Circle Pad in direction (dx, dy) in [-1,1] for N frames."""
        self.set_input(circle=(int(dx * 0x9A), int(dy * 0x9A)))
        self.run(frames)
        self.release()

    # -- screenshots / states --------------------------------------------------------------------
    def screenshot(self, path, scale: int = 1) -> Path:
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = str(path).encode('utf-8')
        d = self._req('Screenshot', struct.pack('<II', scale, len(raw)) + raw, timeout=20)
        if not d or struct.unpack_from('<I', d)[0] != 1:
            raise RPCError(f'screenshot failed: {path}')
        return path

    def save_state(self, slot: int):
        d = self._req('SaveState', struct.pack('<II', slot, 0), timeout=30)
        return bool(struct.unpack_from('<I', d)[0]) if d else False

    def load_state(self, slot: int):
        d = self._req('LoadState', struct.pack('<II', slot, 0), timeout=30)
        return bool(struct.unpack_from('<I', d)[0]) if d else False

    # -- memory ---------------------------------------------------------------------------
    def processes(self):
        d = self._req('ProcessList', struct.pack('<II', 0, 64))
        n = struct.unpack_from('<I', d)[0]
        out = []
        for i in range(n):
            pid, tid = struct.unpack_from('<IQ', d, 4 + i * 0x14)
            name = d[4 + i * 0x14 + 12: 4 + i * 0x14 + 20].rstrip(b'\x00').decode('ascii', 'replace')
            out.append((pid, tid, name))
        return out

    def select_game_process(self):
        for pid, tid, name in self.processes():
            if tid in (TITLE_ID, TITLE_ID | 0x0000000E00000000):
                self._req('SetGetProcess', struct.pack('<II', 1, pid))
                self.pid = pid
                return pid
        raise RPCError('game process not found')

    def read(self, addr: int, size: int) -> bytes:
        out = bytearray()
        while size > 0:
            n = min(size, MAX_DATA)
            out += self._req('ReadMemory', struct.pack('<II', addr, n))
            addr += n
            size -= n
        return bytes(out)

    def write(self, addr: int, data: bytes):
        step = MAX_DATA - 8
        for i in range(0, len(data), step):
            chunk = data[i:i + step]
            self._req('WriteMemory', struct.pack('<II', addr + i, len(chunk)) + chunk)

    def u32(self, addr):
        return struct.unpack('<I', self.read(addr, 4))[0]


DIALOG_LOG = USER_DIR / 'log' / 'harness_dialogs.txt'
APP_PLIST = AZAHAR_BIN.parent.parent / 'Info.plist'


def kill_all():
    """Kill ALL instances of the test Azahar (never the user's Azahar) and wait until the RPC port
    is free."""
    subprocess.run(['pkill', '-9', '-f', str(AZAHAR_BIN)], capture_output=True)
    for _ in range(40):
        r = subprocess.run(['lsof', '-nP', f'-iUDP:{PORT}'], capture_output=True, text=True)
        if not r.stdout.strip():
            return
        time.sleep(0.25)
    raise RPCError(f'UDP port {PORT} is still busy (is another app using the RPC?)')


def make_background_app():
    """No Dock icon or menu (LSUIElement) in the TEST .app (not the user's)."""
    r = subprocess.run(['/usr/libexec/PlistBuddy', '-c', 'Print :LSUIElement', str(APP_PLIST)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        subprocess.run(['/usr/libexec/PlistBuddy', '-c', 'Add :LSUIElement bool true', str(APP_PLIST)],
                       check=True, capture_output=True)


def new_dialogs(since: int = 0):
    """Dialog lines that harness mode closed automatically (emulator errors/warnings)."""
    if not DIALOG_LOG.exists():
        return []
    return DIALOG_LOG.read_text(encoding='utf-8', errors='replace').splitlines()[since:]


def launch(rom: Path = ROM, wait: float = 90.0, extra_args=()) -> Azahar:
    """Start (a single, invisible instance of) the harness Azahar and wait for the RPC."""
    if not AZAHAR_BIN.exists():
        raise FileNotFoundError(AZAHAR_BIN)
    kill_all()
    make_background_app()
    log = open(USER_DIR / 'log' / 'harness_stdout.txt', 'w')
    env = dict(os.environ, AZAHAR_HARNESS='1')
    proc = subprocess.Popen([str(AZAHAR_BIN), *extra_args, str(rom)], stdout=log, stderr=subprocess.STDOUT,
                            env=env)
    emu = Azahar(timeout=5)
    emu.proc = proc
    emu.dialogs_seen = len(new_dialogs())
    t0 = time.time()
    while time.time() - t0 < wait:
        if proc.poll() is not None:
            raise RPCError(f'Azahar exited with code {proc.returncode}')
        try:
            st = emu.status()
            if st['powered'] and st['frame'] > 0:
                emu.sock.settimeout(30)
                return emu
        except RPCError:
            pass
        time.sleep(0.5)
    kill_all()
    raise RPCError('the RPC did not respond in time. Dialogs: ' + ' || '.join(new_dialogs(emu.dialogs_seen)))


def shutdown(emu: Azahar = None):
    proc = getattr(emu, 'proc', None) if emu else None
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
    kill_all()
