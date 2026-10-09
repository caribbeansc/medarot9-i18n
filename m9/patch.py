"""Binary patches for the game files the translation changes (.b data tables, map .gdn files, code.bin...).

A patch is JSON, made against the player's own Japanese file, and holds only what the translation writes:

  {"file": "param/ItemData.b", "src": "<sha1 of the Japanese file>", "out": "<sha1 of the result>", "size": N,
   "ops": [...]}

- Same size as the Japanese file: ops = [[offset, "bytes"], ...] (runs of changed bytes).
- Different size: ops = [["=", src_offset, length] | ["+", "bytes"], ...] in output order: copy a span of the
  Japanese file, or insert new bytes.
Bytes are hex, or base64 when the patch says "enc": "b64" (textures). Large patches are stored gzip-compressed
(<name>.json.gz); `load`/`save` handle both.

Nothing of the game is stored: copies point into the player's file.
"""
import base64
import difflib
import gzip
import hashlib
import json
from pathlib import Path


def sha1(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


class PatchError(Exception):
    pass


def _enc(b: bytes, enc: str) -> str:
    return base64.b64encode(b).decode('ascii') if enc == 'b64' else b.hex()


def _dec(s: str, enc: str) -> bytes:
    return base64.b64decode(s) if enc == 'b64' else bytes.fromhex(s)


def make(rel: str, src: bytes, out: bytes, gap: int = 8, enc: str = 'hex') -> dict:
    p = {'file': rel, 'src': sha1(src), 'out': sha1(out), 'size': len(out)}
    if enc != 'hex':
        p['enc'] = enc
    if len(src) == len(out):
        runs, i, n = [], 0, len(out)
        while i < n:
            if src[i:i + 256] == out[i:i + 256]:      # skip identical stretches fast
                i += 256
                continue
            if src[i] == out[i]:
                i += 1
                continue
            j = i
            while j < n:
                if src[j] != out[j]:
                    j += 1
                    continue
                k = j
                while k < n and k - j < gap and src[k] == out[k]:
                    k += 1
                if k < n and k - j < gap and src[k] != out[k]:
                    j = k
                    continue
                break
            runs.append([i, _enc(out[i:j], enc)])
            i = j
        p['ops'] = runs
    else:
        sm = difflib.SequenceMatcher(None, src, out, autojunk=False)
        ops = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                ops.append(['=', i1, i2 - i1])
            elif j2 > j1:
                ops.append(['+', _enc(out[j1:j2], enc)])
        p['ops'] = ops
    return p


def apply(p: dict, src: bytes) -> bytes:
    enc = p.get('enc', 'hex')
    if sha1(src) != p['src']:
        raise PatchError(f"{p['file']}: your file is not the expected Japanese version (different dump or update?)")
    ops = p['ops']
    if p['size'] == len(src) and (not ops or isinstance(ops[0][0], int)):
        out = bytearray(src)
        for off, hx in ops:
            b = _dec(hx, enc)
            out[off:off + len(b)] = b
        out = bytes(out)
    else:
        parts = []
        for op in ops:
            if op[0] == '=':
                parts.append(src[op[1]:op[1] + op[2]])
            else:
                parts.append(_dec(op[1], enc))
        out = b''.join(parts)
    if sha1(out) != p['out']:
        raise PatchError(f"{p['file']}: the patched file does not match (corrupt patch?)")
    return out


def save(p: dict, path: Path, compress: bool = False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(p, ensure_ascii=False, indent=None if compress else 1) + '\n').encode('utf-8')
    if compress:
        path.with_name(path.name + '.gz').write_bytes(gzip.compress(raw, 9, mtime=0))
    else:
        path.write_bytes(raw)


def load(path: Path) -> dict:
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.name.endswith('.gz') else raw)
