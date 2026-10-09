"""The game's text encoding: Shift-JIS (cp932) plus the 16 Spanish letters.

The game's fonts have no Spanish letters. Sixteen half-width katakana (one byte each, 0xC0-0xCF), which the game
never uses in its text, carry them: m9/fonts.py redraws those glyphs and the code patch makes the text engine read
the byte unsigned. The codec is registered on import:

  import m9.codec
  'Año'.encode('sjis_es')   # b'A\\xc6o'
"""
import codecs

CHARMAP = {'á': 0xC0, 'é': 0xC1, 'í': 0xC2, 'ó': 0xC3, 'ú': 0xC4, 'ü': 0xC5, 'ñ': 0xC6,
           'Á': 0xC7, 'É': 0xC8, 'Í': 0xC9, 'Ó': 0xCA, 'Ú': 0xCB, 'Ü': 0xCC, 'Ñ': 0xCD,
           '¿': 0xCE, '¡': 0xCF}
_ENC = {ch: bytes([code]) for ch, code in CHARMAP.items()}
_DEC = {ord(bytes([code]).decode('cp932')): ch for ch, code in CHARMAP.items()}
FOLD = str.maketrans('áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN', '¿¡')


def _encode(text, errors='strict'):
    out = bytearray()
    for ch in text:
        b = _ENC.get(ch)
        out += b if b is not None else ch.encode('cp932', errors)
    return bytes(out), len(text)


def _decode(data, errors='strict'):
    return bytes(data).decode('cp932', errors).translate(_DEC), len(data)


def _search(name):
    if name in ('sjis_es', 'sjis-es'):
        return codecs.CodecInfo(_encode, _decode, name='sjis_es')
    return None


codecs.register(_search)


def fold(text: str) -> str:
    """The text without accents, ñ or opening ¿ ¡."""
    return text.translate(FOLD)


def is_game_text(s: str, extra: str = '') -> bool:
    """Text the patched fonts can show: printable ASCII and the Spanish letters (plus `extra`, e.g. '\\n')."""
    return all(0x20 <= ord(c) < 0x7F or c in CHARMAP or c in extra for c in s)
