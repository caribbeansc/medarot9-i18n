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

    def test_code_patches_for_both_editions_and_versions(self):
        for lang in LANGS:
            d = ROOT / 'langs' / lang / 'binary' / 'exefs'
            got = {(patch.load(f).get('edition', 'kuwagata'), patch.load(f).get('game', '1.3')) for f in d.glob('code.bin*.json')}
            want = {(e, v) for e in ('kuwagata', 'kabuto') for v in ('1.3', '1.0')}
            self.assertEqual(got, want, f'{lang}: code.bin patches')

    def test_v10_variants(self):
        """Every 1.0 variant says so, and sits next to the 1.3.0 file of the same game file."""
        for lang in LANGS:
            pack = ROOT / 'langs' / lang
            for f in pack.rglob('*.v10.json*'):
                d = patch.load(f) if f.suffix == '.gz' or 'binary' in f.parts or 'textures' in f.parts \
                    else json.loads(f.read_text(encoding='utf-8'))
                self.assertEqual(d.get('game'), '1.0', f)
                twin = f.with_name(f.name.replace('.v10', ''))
                self.assertTrue(twin.exists(), f'{f}: no 1.3.0 file next to it')

    def test_binary_patches(self):
        for lang in LANGS:
            for f in list((ROOT / 'langs' / lang / 'binary').rglob('*.json')) + \
                     list((ROOT / 'langs' / lang / 'textures').rglob('*.json.gz')):
                p = patch.load(f)
                for k in ('file', 'src', 'out', 'size', 'ops'):
                    self.assertIn(k, p, f)


class Containers(unittest.TestCase):
    def test_romfs_round_trip(self):
        """A RomFS built by m9.cia reads back through m9.dump, file by file, with a valid hash tree."""
        import hashlib
        import io
        from m9 import cia
        from m9.dump import _RomFs
        files = {f'dir{i % 7}/sub{i % 3}/file{i}.bin': bytes([i % 251]) * (i * 37 % 9000) for i in range(300)}
        files['top.txt'] = b'hello'
        rf = cia.RomFS({k: len(v) for k, v in files.items()})
        buf = io.BytesIO()
        rf.write(buf, 0, files.__getitem__)
        buf.seek(0)
        r = _RomFs(buf, 0, 'test')
        self.assertEqual(set(r.files), set(files))
        for k, v in files.items():
            self.assertEqual(r.read(k), v, k)
        b = buf.getvalue()
        l3 = b[rf.l3_phys:rf.l3_phys + rf.l3_size]
        l2 = b[rf.l2_phys:rf.l2_phys + rf.l2_size]
        for i in range(len(l2) // 32):
            self.assertEqual(hashlib.sha256(l3[i * 4096:(i + 1) * 4096].ljust(4096, b'\0')).digest(), l2[i * 32:i * 32 + 32])
        l1 = b[rf.l1_phys:rf.l1_phys + rf.l1_size]
        self.assertEqual(b[0x60:0x80], hashlib.sha256(l1[:4096].ljust(4096, b'\0')).digest())


if __name__ == '__main__':
    unittest.main()
