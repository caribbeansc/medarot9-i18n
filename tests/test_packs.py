"""Checks the language packs without the game: well-formed files, known term keys, no Japanese text."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from m9 import patch, terms  # noqa: E402
import m9.codec  # noqa: E402,F401

JP = re.compile(r'[぀-ヿ一-鿿]')
LANGS = sorted(d.name for d in (ROOT / 'langs').iterdir() if (d / 'lang.json').exists())


class Packs(unittest.TestCase):
    def test_lang_json(self):
        for lang in LANGS:
            meta = json.loads((ROOT / 'langs' / lang / 'lang.json').read_text(encoding='utf-8'))
            self.assertEqual(meta['code'], lang)

    def test_script_lines(self):
        for lang in LANGS:
            table = terms.load(lang)
            for f in (ROOT / 'langs' / lang / 'script').rglob('*.json'):
                d = json.loads(f.read_text(encoding='utf-8'))
                self.assertTrue(d['file'].endswith('.spt'), f)
                for line in d['lines']:
                    self.assertRegex(line['src'], r'^[0-9a-f]{12}$', f)
                    self.assertTrue(('t' in line) != ('hex' in line), f)
                    if 't' in line:
                        errors = []
                        text = terms.expand(line['t'], table, errors)
                        self.assertEqual(errors, [], f'{f}: unknown term keys')
                        text.encode('sjis_es')        # every character must exist in the game's encoding

    def test_name_slots(self):
        for lang in LANGS:
            table = terms.load(lang)
            for f in (ROOT / 'langs' / lang / 'names').glob('*.json'):
                d = json.loads(f.read_text(encoding='utf-8'))
                for s in d['slots']:
                    errors = []
                    body = terms.expand(s['t'], table, errors).encode('sjis_es')
                    self.assertEqual(errors, [], f)
                    room = s['size'] - s.get('head', 0) - s.get('tail', 0) - (1 if s.get('fill', 'nul') == 'nul' else 0)
                    self.assertLessEqual(len(body), room, f'{f}: {s["t"]} does not fit its slot')

    def test_binary_patches(self):
        for lang in LANGS:
            for f in list((ROOT / 'langs' / lang / 'binary').rglob('*.json')) + \
                     list((ROOT / 'langs' / lang / 'textures').rglob('*.json.gz')):
                p = patch.load(f)
                for k in ('file', 'src', 'out', 'size', 'ops'):
                    self.assertIn(k, p, f)


if __name__ == '__main__':
    unittest.main()
