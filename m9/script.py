"""The game's scripts (.spt) and the language packs' line files.

A .spt file is a list of fields separated by NUL bytes. A field starting with a lone CR (0x0D) is a command; the
fields after it, up to the next command, are its arguments (text the player reads, names, ids...). A translation
never changes the list of fields: it replaces the content of some of them.

A pack's line file (langs/<lang>/script/<path>.json) lists those fields:

  {"file": "story/spt/f01_000_110_00_t002.spt",
   "lines": [{"i": 1107, "src": "3f9a0c1b2d4e", "t": "Welcome to our {{academy}}, "}, ...]}

- i   : field index in the file.
- src : fingerprint of the Japanese field it replaces (first 12 hex digits of its SHA-1). The build refuses to
        write a line whose Japanese field is not the expected one.
- t   : the text, in the game's encoding once {{term}} keys are expanded (see m9/terms.py). A line whose bytes are
        not text is stored as "hex" instead of "t".
"""
import hashlib

import m9.codec  # noqa: F401  (registers the 'sjis_es' codec)


def fingerprint(field: bytes) -> str:
    return hashlib.sha1(field).hexdigest()[:12]


def fields(data: bytes):
    return data.split(b'\x00')


def join(fields_) -> bytes:
    return b'\x00'.join(fields_)


def is_command(field: bytes) -> bool:
    return field[:1] == b'\r'


def decode(field: bytes):
    """(text, None) or (None, hex) when the bytes are not valid game text."""
    try:
        t = field.decode('sjis_es')
        if t.encode('sjis_es') == field:          # only when it gives the very same bytes back
            return t, None
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return None, field.hex()


def encode(text: str) -> bytes:
    return text.encode('sjis_es')


def diff(jp: bytes, out: bytes):
    """Line entries for every field of `out` that differs from `jp` (same number of fields required)."""
    fj, fo = fields(jp), fields(out)
    if len(fj) != len(fo):
        raise ValueError('a translated script must keep the Japanese fields')
    lines = []
    for i, (a, b) in enumerate(zip(fj, fo)):
        if a == b:
            continue
        t, hx = decode(b)
        e = {'i': i, 'src': fingerprint(a)}
        if t is not None:
            e['t'] = t
        else:
            e['hex'] = hx
        lines.append(e)
    return lines


def apply(jp: bytes, lines, expand=None):
    """Writes the lines into the Japanese script. Returns (bytes, problems)."""
    f = fields(jp)
    problems = []
    for e in lines:
        i = e['i']
        if not (0 <= i < len(f)):
            problems.append((i, 'no such field'))
            continue
        if fingerprint(f[i]) != e['src']:
            problems.append((i, 'the Japanese field is not the expected one'))
            continue
        if 'hex' in e:
            f[i] = bytes.fromhex(e['hex'])
        else:
            t = expand(e['t']) if expand else e['t']
            f[i] = encode(t)
    return join(f), problems
