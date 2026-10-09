"""Names inside the game's data tables, written from the language's terms.

Medabot, Medaforce, Medal, part and enemy names live in fixed-size slots of the data tables (romfs/param/*.b). The
binary patches already write them; this layer writes them again from langs/<lang>/names/<table>.json so that a
term changed in terms.csv reaches the data tables too:

  {"file": "param/MedaData.b",
   "slots": [{"off": 742, "size": 20, "src": "<fingerprint of the Japanese slot>", "t": "{{noctobat}}",
              "fill": "nul" | "space", "head": 0, "tail": 0}, ...]}

The slot keeps its first `head` bytes and its last `tail` bytes as the patched file has them (a record prefix, the
Japanese suffix of an enemy name); the name goes in between, padded with NULs (the last byte always NUL) or spaces.
A name that does not fit its slot is not written and is reported.
"""
import hashlib

import m9.codec  # noqa: F401


def fingerprint(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()[:12]


def apply(data: bytes, jp: bytes, slots, expand):
    out = bytearray(data)
    problems = []
    for s in slots:
        off, size = s['off'], s['size']
        if fingerprint(jp[off:off + size]) != s['src']:
            problems.append((off, 'the Japanese slot is not the expected one'))
            continue
        head, tail = s.get('head', 0), s.get('tail', 0)
        cur = bytes(out[off:off + size])
        body = expand(s['t']).encode('sjis_es')
        nul = s.get('fill', 'nul') == 'nul'
        room = size - head - tail - (1 if nul else 0)
        if len(body) > room:
            problems.append((off, f'{expand(s["t"])!r} does not fit ({len(body)} > {room} bytes)'))
            continue
        pad = (b'\x00' if nul else b' ') * (size - head - tail - len(body))
        out[off:off + size] = cur[:head] + body + pad + (cur[size - tail:] if tail else b'')
    return bytes(out), problems
