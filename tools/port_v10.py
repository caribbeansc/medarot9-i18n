#!/usr/bin/env python3
"""port_v10.py - Makes a language pack work on the game WITHOUT its 1.3.0 update (version 1.0) (Oct 2026).

The packs are made for 1.3.0. Most of the game is the same in 1.0 (3,828 of the 3,882 translated scripts, every
texture, most data tables); what the update changed gets a 1.0 variant next to the 1.3.0 file, named `<name>.v10.json`
in the same folder. The build picks, for every game file, the variant whose fingerprints / SHA-1 match the player's
file, so one pack serves both versions:

  - scripts the update changed: each line goes to the 1.0 field with the same Japanese (fields aligned with the
    commands as anchors); the fields the update rewrote get their 1.0 text from V10_TEXT below;
  - data tables: same-size runs where the 1.0 bytes are the same as 1.3.0's; PartsText.b record by record;
    AreaEnemyData.b name by name; name slots to the same Japanese name, in the same order;
  - code.bin, per edition: .rodata/.data/padding runs one page lower (the 1.0 code is 0x1000 shorter and those
    sections are otherwise identical), with the pointers in them moved the same way; the strings the translation
    moved to the free gap after .text go to the 1.0 gap; .text runs are found by their Japanese bytes.

Files that exist only in 1.3.0 (7 scripts, 4 data tables) are skipped by the build on a 1.0 game.

  python3 tools/port_v10.py es en --kuwagata <game> <update> --kabuto <game> <update>
"""
import argparse
import difflib
import json
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from m9 import patch, script, names  # noqa: E402
from m9.dump import Dump  # noqa: E402
import effect_pool_fix as epf  # noqa: E402  (tools/: the crash fix of long robattles, re-applied per program)

# Fields the 1.3.0 update rewrote, as the 1.0 game has them: {lang: {(file, Japanese 1.0 text): text}}.
# 'SAME' = the 1.3.0 translation says it as well (typo fixes, same meaning).
SAME = 'SAME'
HDR = '<c:00ff00>'
V10_TEXT = {
    'es': {
        ('mdr/spt/partshint_4_31.spt', 'ブリリアンス'): HDR + '{{leg_trait|cap}}:<c>Brillo\nAl completar la carga, te\naplica un {{effect}} igual al\nde\n"Súper Reparación".',
        ('mdr/spt/partshint_4_33.spt', 'イリュージョン'): HDR + '{{leg_trait|cap}}:<c>{{illusion}}\nAl completar la carga, te\naplica un {{effect}} igual al\nde\n"{{stealth}}".',
        ('mdr/spt/partshint_4_57.spt', 'アーティラリー'): HDR + '{{leg_trait|cap}}:<c>Artillería\nDurante la {{prep}} de un\nataque no puede evadir ni\ndefender.\n{{power|cap}} y {{success}} +10.',
        ('mdr/spt/partshint_4_66.spt', 'ノーガード'): HDR + '{{leg_trait|cap}}:<c>\nSin Guardia\nDurante la {{prep}} de un\nataque cuerpo a cuerpo\nno puede evadir ni\ndefender. {{prep|cap}} y {{success}}\n+10.',
        ('mdr/spt/partshint_A_27.spt', 'オーバードライブ'): HDR + '{{mf}}:<c>{{overdrive}}\nSube bastante la {{prep}} y\nrefrigeración de todo tu\nequipo.\n<c:00ffff>*{{required_parts|cap}}<c>\nNinguna',
        ('story/spt/npc_teach_fa_meda_000_s00_t001.spt', 'ムーンドラゴン'): '{{moon_dragon}}',
        ('story/spt/npc_teach_fa_meda_000_s01_t011.spt', 'ムーンドラゴン'): '{{moon_dragon}}',
        ('story/spt/npc_teach_fa_meda_000_s05_t011.spt', 'ムーンドラゴン'): '{{moon_dragon}}',
    },
    'en': {
        ('mdr/spt/partshint_4_31.spt', 'ブリリアンス'): HDR + 'Leg Trait:<c> {{brilliance}}\nWhen charging completes,\ngives you the same {{effect}}\nas\n"Super Repair".',
        ('mdr/spt/partshint_4_33.spt', 'イリュージョン'): HDR + 'Leg Trait:<c> {{illusion}}\nWhen charging completes,\ngives you the same {{effect}}\nas\n"{{stealth}}".',
        ('mdr/spt/partshint_4_57.spt', 'アーティラリー'): HDR + 'Leg Trait:<c> {{artillery}}\nWhile prepping an attack,\ncannot evade or defend.\n{{power}} and {{success}} {{stats}}\n+10.',
        ('mdr/spt/partshint_4_66.spt', 'ノーガード'): HDR + 'Leg Trait:<c> No Guard\nWhile prepping a melee\nattack, cannot evade or\ndefend.\n{{prep}} and {{success}} {{stats}}\n+10.',
        ('mdr/spt/partshint_A_27.spt', 'オーバードライブ'): HDR + '{{mf}}:<c> {{overdrive}}\nGreatly raises the {{prep}}\nand\n{{cooldown}} stats of your\nwhole team.\n<c:00ffff>{{required_parts}}<c>\nNone',
        ('story/spt/npc_m_2f_meda_000_s03_t011.spt', '左手'): "Its left hand's Criminal Eye sees\nthrough everything.",
        ('story/spt/npc_teach_fa_meda_000_s00_t001.spt', 'ムーンドラゴン'): '{{moon_dragon}}',
        ('story/spt/npc_teach_fa_meda_000_s01_t011.spt', 'ムーンドラゴン'): '{{moon_dragon}}',
        ('story/spt/npc_teach_fa_meda_000_s05_t011.spt', 'ムーンドラゴン'): '{{moon_dragon}}',
    },
}
# Fields the update rewrote whose 1.3.0 translation fits 1.0 too (typo fixes / same meaning): (file, field index in 1.0)
V10_SAME = {('mdr/spt/medahint_227.spt', 8), ('mdr/spt/partshint_4_24.spt', 8), ('mdr/spt/partshint_4_42.spt', 8),
            ('mdr/spt/partshint_4_43.spt', 8), ('mdr/spt/partshint_4_44.spt', 8),
            ('story/spt/npc_pc03_161_s03_t011.spt', 1038), ('story/spt/npc_m_2f_meda_000_s03_t011.spt', 1052)}


# Textures the update replaced with another poster: (spec of the 1.3.0 poster that looks like the 1.0 one, 1.0 text)
TEXTURES_V10 = {
    'battle/tex/mf045.ctpk': ('battle/tex/mf052.ctpk', None),            # 1.0: ブレイブ (gold), 1.3.0: a green one
    'battle/tex/mf059.ctpk': (None, {'es': 'Absorbedor MF', 'en': 'MF Absorber'}),   # 1.0: MFアブソーバー
}


def v10_name(path: Path) -> Path:
    n = path.name
    for ext in ('.json.gz', '.json'):
        if n.endswith(ext):
            return path.with_name(n[:-len(ext)] + '.v10' + ext)
    raise ValueError(path)


# --- scripts ------------------------------------------------------------------------------------------------------

def port_script(lang, rel, lines, jp13: bytes, jp10: bytes, report):
    f13, f10 = script.fields(jp13), script.fields(jp10)
    sm = difflib.SequenceMatcher(None, f13, f10, autojunk=False)
    where = {}                        # 1.3 index -> 1.0 index (same Japanese), or (1.0 index, 'rewritten')
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                where[i1 + k] = j1 + k
        elif tag == 'replace':
            for k in range(i1, i2):
                fp = script.fingerprint(f13[k])
                hits = [x for x in range(j1, j2) if script.fingerprint(f10[x]) == fp]
                if len(hits) == 1:
                    where[k] = hits[0]
                elif i2 - i1 == j2 - j1:
                    where[k] = (j1 + k - i1, 'rewritten')
    texts = V10_TEXT.get(lang, {})
    out = []
    for e in lines:
        w = where.get(e['i'])
        if isinstance(w, int):
            out.append(dict(e, i=w, src=script.fingerprint(f10[w])))
            continue
        if w is None:
            report.append(f'{lang} {rel}[{e["i"]}]: only in 1.3.0, not written on 1.0')
            continue
        i10 = w[0]
        jp = f10[i10].decode('cp932', 'replace')
        t = next((v for (f, key), v in texts.items() if f == rel and key in jp), None)
        if t is None and (rel, i10) in V10_SAME:
            t = SAME
        if t is None:
            raise SystemExit(f'{lang} {rel}[{i10}]: the update rewrote this field and V10_TEXT has no 1.0 text: {jp!r}')
        new = dict(e, i=i10, src=script.fingerprint(f10[i10]))
        if t != SAME:
            new.pop('hex', None)
            new['t'] = t
        out.append(new)
    return out


# --- data tables --------------------------------------------------------------------------------------------------

# Data-table names the update replaced, as 1.0 has them (the 1.3.0 entry is another part)
NAMES_V10 = {'es': {'チェアリー': 'Silla'}, 'en': {'チェアリー': 'Chairly'}}

# PartsText.b records the update rewrote, as 1.0 has them: {lang: {Japanese 1.0 record: text}} (same byte length as
# the Japanese record, padded with spaces; lines end in CR LF as in the game)
RECORDS_V10 = {
    'es': {'味方メダロット１体の\r\n１パーツのダメージを回復\r\n地形相性により回復量変化':
           'Un aliado recupera\r\ndaño de 1 pieza\r\nVaría según afinidad de terreno'},
    'en': {'味方メダロット１体の\r\n１パーツのダメージを回復\r\n地形相性により回復量変化':
           "1 of team's medalia\r\nHeals Dmg for 1 part\r\nRecover varies : Terrain"},
}


def records(b: bytes, count: int):
    """`count` [u16 LE length][text] records (PartsText.b) and the bytes after them (1.0 has 6 stray ones)."""
    out, i = [], 0
    for _ in range(count):
        n = struct.unpack_from('<H', b, i)[0]
        out.append(b[i + 2:i + 2 + n])
        i += 2 + n
    return out, b[i:]


def port_records(jp13, out13, jp10, lang):
    n = 0
    i = 0
    while i + 2 <= len(jp13):
        i += 2 + struct.unpack_from('<H', jp13, i)[0]
        n += 1
    (r13, t13), (o13, _), (r10, t10) = records(jp13, n), records(out13, n), records(jp10, n)
    if t13 or len(o13) != len(r13):
        raise SystemExit('PartsText.b: not a list of length-prefixed records')
    tr = {}
    for a, b in zip(r13, o13):
        tr.setdefault(a, b)
    for jp, t in RECORDS_V10.get(lang, {}).items():
        k = jp.encode('cp932')
        body = t.encode('sjis_es')
        if len(body) > len(k):
            raise SystemExit(f'PartsText.b 1.0 record too long: {t!r}')
        tr[k] = body + b' ' * (len(k) - len(body))
    left = [r for r in r10 if r not in tr]
    out = b''.join(struct.pack('<H', len(tr.get(r, r))) + tr.get(r, r) for r in r10) + t10
    return out, left


def _token(buf, s, e):
    def txt(i):
        return buf[i] >= 0x20 and buf[i] != 0x7F
    while s > 0 and txt(s - 1):
        s -= 1
    while e < len(buf) and txt(e):
        e += 1
    return s, e


def port_tokens(jp13, out13, jp10):
    """Same-length text tokens (AreaEnemyData.b names): learned from 1.3.0, written on the 1.0 file."""
    pairs, i = {}, 0
    while i < len(jp13):
        if jp13[i] == out13[i]:
            i += 1
            continue
        s, e = _token(jp13, i, i + 1)
        while e < len(jp13) and jp13[e] != out13[e]:
            e += 1
        s, e = _token(jp13, s, e)
        pairs.setdefault(jp13[s:e], out13[s:e])
        i = e
    out = bytearray(jp10)
    n = 0
    for k in sorted(pairs, key=len, reverse=True):
        pos = jp10.find(k)
        while pos != -1:
            if (pos == 0 or jp10[pos - 1] < 0x20) and (pos + len(k) >= len(jp10) or jp10[pos + len(k)] < 0x20):
                out[pos:pos + len(k)] = pairs[k]
                n += 1
            pos = jp10.find(k, pos + 1)
    missing = [k for k in pairs if k not in jp10]
    return bytes(out), (n, len(pairs), len(missing))


def port_runs(jp13, out13, jp10, lookup):
    """Same-size table with the same layout (parts tables), name by name: where 1.0 has the same Japanese as 1.3.0
    the translated name is copied; where the update renamed the entry, the 1.0 name is looked up (terms, part lists);
    a 1.0 typo of the same name gets the 1.3.0 translation. Returns (bytes, notes)."""
    out = bytearray(jp10)
    notes, i = [], 0
    while i < len(jp13):
        if jp13[i] == out13[i]:
            i += 1
            continue
        s, e = _token(jp13, i, i + 1)
        while e < len(jp13) and jp13[e] != out13[e]:
            e += 1
        s, e = _token(jp13, s, e)
        old13, new13, old10 = jp13[s:e], out13[s:e], jp10[s:e]
        if old10 == old13:
            out[s:e] = new13
        else:
            n10 = old10.decode('cp932', 'replace').strip(' \u3000\x00')
            n13 = old13.decode('cp932', 'replace').strip(' \u3000\x00')
            t = lookup(n10)
            if t is not None:
                body = t.encode('sjis_es')
                if len(body) > e - s:
                    raise SystemExit(f'{n10!r} -> {t!r} does not fit its {e - s} bytes')
                out[s:e] = body + b' ' * (e - s - len(body))
                notes.append(f'{n10} -> {t} (the update renamed it {n13})')
            elif difflib.SequenceMatcher(None, n10, n13).ratio() >= 0.8:
                out[s:e] = new13
                notes.append(f'{n10} (1.0 typo of {n13}) -> 1.3.0 translation')
            else:
                raise SystemExit(f'no translation for the 1.0 name {n10!r} (1.3.0: {n13!r})')
        i = e
    return bytes(out), notes


def port_names(slots, jp13, jp10):
    """Name slots to the 1.0 offsets: the n-th slot with a given Japanese name goes to its n-th place in 1.0."""
    if jp13 == jp10:
        return slots, 0
    by, index = {}, {}
    for s in slots:
        by.setdefault((s['size'], s['src']), []).append(s)
    for size in {k[0] for k in by}:
        idx = index[size] = {}
        for o in range(len(jp10) - size + 1):
            idx.setdefault(names.fingerprint(jp10[o:o + size]), []).append(o)
    out, lost = [], 0
    for (size, src), group in by.items():
        here = index[size].get(src, [])
        group.sort(key=lambda s: s['off'])
        if len(here) < len(group):
            lost += len(group) - len(here)
        for s, o in zip(group, here):
            out.append(dict(s, off=o))
    out.sort(key=lambda s: s['off'])
    return out, lost


# --- code.bin -----------------------------------------------------------------------------------------------------

def layout(src):
    e = src._ncch.exheader()
    t_addr, _, t_size = struct.unpack_from('<III', e, 0x10)
    r_addr, _, r_size = struct.unpack_from('<III', e, 0x20)
    d_addr, _, d_size = struct.unpack_from('<III', e, 0x30)
    base = t_addr
    return {'text_end': t_size, 'ro': r_addr - base, 'ro_end': r_addr - base + r_size, 'data': d_addr - base,
            'data_end': d_addr - base + d_size, 'base': base, 'ro_size': r_size, 'data_size': d_size}


def _agree(c13, a, b, c10, q):
    """How many of the 16 bytes before or after a run (the better side) are the same in 1.0 at q."""
    return max(sum(c13[a - k] == c10[q - k] for k in range(1, 17)),
               sum(c13[b + k] == c10[q + (b - a) + k] for k in range(16)))


def port_code(c13: bytes, out13: bytes, c10: bytes, L13, L10, report):
    """The 1.3.0 code patch moved to the 1.0 code (see the module docstring)."""
    if (L13['ro_size'], L13['data_size']) != (L10['ro_size'], L10['data_size']):
        raise SystemExit('code.bin: .rodata/.data sizes differ between 1.0 and 1.3.0')
    delta = L13['ro'] - L10['ro']
    if L13['data'] - L10['data'] != delta:
        raise SystemExit('code.bin: .rodata and .data do not move together')
    base = L13['base']
    gap13, gap10 = (L13['text_end'], L13['ro']), (L10['text_end'], L10['ro'])

    def va_map(v):
        o = v - base
        if gap13[0] <= o < gap13[1]:
            n = gap10[0] + (o - gap13[0])
            return base + n if n < gap10[1] else None
        if L13['ro'] <= o < L13['data_end'] + 0x100000:
            return v - delta
        return None

    def in_reloc(v):              # where the translation puts moved strings: the gap after .text, the .rodata padding
        o = v - base
        return gap13[0] <= o < gap13[1] or L13['ro_end'] <= o < L13['data']

    out = bytearray(c10)
    # 1) .rodata / padding / .data: word by word (1.0 = 1.3.0 except pointer words)
    lo, hi = L13['ro'], L13['data_end']
    changed = [i for i in range(lo, hi) if c13[i] != out13[i]]
    for w in sorted({i - i % 4 for i in changed}):
        o13, n13 = c13[w:w + 4], out13[w:w + 4]
        w10 = w - delta
        o10 = c10[w10:w10 + 4]
        if o10 == o13:
            # the same in both versions (not a pointer that moves): plain bytes, unless it is a pointer the
            # translation redirected to a moved string
            v_old, v_new = struct.unpack('<I', o13)[0], struct.unpack('<I', n13)[0]
            if in_reloc(v_new) and 0x100000 <= v_old < base + L13['data_end']:
                out[w10:w10 + 4] = struct.pack('<I', va_map(v_new))
            else:
                out[w10:w10 + 4] = n13
            continue
        v13, v10 = struct.unpack('<I', o13)[0], struct.unpack('<I', o10)[0]
        if va_map(v13) != v10:
            raise SystemExit(f'code.bin: word at {w:#x} differs between 1.0 and 1.3.0 and is not a moved pointer')
        nv = struct.unpack('<I', n13)[0]
        m = va_map(nv)
        if m is None:
            raise SystemExit(f'code.bin: pointer at {w:#x} redirected to {nv:#x}, which has no 1.0 place')
        out[w10:w10 + 4] = struct.pack('<I', m)
    # 2) the gap after .text (strings the translation moved there)
    g = [i for i in range(*gap13) if c13[i] != out13[i]]
    if g:
        a, b = min(g), max(g) + 1
        n = gap10[0] + (a - gap13[0])
        if n + (b - a) > gap10[1] or any(c10[n:n + (b - a)]):
            raise SystemExit('code.bin: the 1.0 gap after .text has no room')
        out[n:n + (b - a)] = out13[a:b]
    # 3) .text: each run found by its Japanese bytes (+ context), near the same place
    runs = []
    for i in (k for k in range(gap13[0]) if c13[k] != out13[k]):
        if runs and i - runs[-1][1] < 2:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    shift = L13['text_end'] - L10['text_end']
    placed = {}
    # (literal pools next to the strings hold pointers that differ between versions: contexts on one side too)
    for a, b in runs:                 # first pass: a unique place for the Japanese bytes (with some context)
        for before, after in ((32, 32), (16, 16), (0, 32), (32, 0), (0, 16), (16, 0), (8, 8), (0, 8), (8, 0), (0, 6), (6, 0), (0, 4), (4, 0), (0, 2), (2, 0), (0, 0)):
            needle = c13[a - before:b + after]
            lo10, hi10 = max(0, a - shift - 40000), min(gap10[0], b + 40000)
            hits, p = [], c10.find(needle, lo10, hi10)
            while p != -1 and len(hits) < 2:
                hits.append(p + before)
                p = c10.find(needle, p + 1, hi10)
            if len(hits) == 1:
                placed[a] = hits[0]
                break
    done = sorted(placed.items())
    for a, b in runs:                 # second pass: the exact bytes where the nearest placed runs predict them
        if a in placed:
            continue
        near = sorted(done, key=lambda t: abs(t[0] - a))[:4]
        exp = sorted(p2 - a2 for a2, p2 in near)[len(near) // 2] + a
        cand, p = [], c10.find(c13[a:b], exp - 4096, exp + 4096)
        while p != -1:
            cand.append(p)
            p = c10.find(c13[a:b], p + 1, exp + 4096)
        if not cand:
            raise SystemExit(f'code.bin: .text run at {a:#x} ({out13[a:b]!r}) not found in 1.0')
        # the candidate whose surroundings agree most with 1.3.0's (pointer words differ, the rest should not)
        best = max(cand, key=lambda q: (_agree(c13, a, b, c10, q), -abs(q - exp)))
        placed[a] = best
        report.append(f'code.bin .text {a:#x}: placed by its surroundings ({_agree(c13, a, b, c10, best)}/16 bytes agree)')
        if _agree(c13, a, b, c10, best) < 8:
            raise SystemExit(f'code.bin: .text run at {a:#x} placed where its surroundings do not agree')
    for a, b in runs:
        q = placed[a]
        out[q:q + (b - a)] = out13[a:b]
    report.append(f'code.bin: {len(runs)} .text runs placed')
    return bytes(out)


# --- driver -------------------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('langs', nargs='+')
    ap.add_argument('--kuwagata', nargs=2, required=True, metavar=('GAME', 'UPDATE'))
    ap.add_argument('--kabuto', nargs=2, metavar=('GAME', 'UPDATE'))
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    from m9.build import build
    eds = {'kuwagata': Dump(*a.kuwagata)}
    if a.kabuto:
        eds['kabuto'] = Dump(*a.kabuto)
    d = eds['kuwagata']
    tmp = REPO / 'work' / 'port_v10'
    for lang in a.langs:
        pack = REPO / 'langs' / lang
        report = []
        tdict = dict(NAMES_V10.get(lang, {}))
        import csv
        for r in csv.DictReader((pack / 'terms.csv').open(encoding='utf-8')):
            if r.get('jp'):
                tdict.setdefault(r['jp'], r['text'])

        def lookup(jp):
            return tdict.get(jp)
        # scripts
        n = 0
        for f in sorted((pack / 'script').rglob('*.json')):
            if f.name.endswith('.v10.json'):
                continue
            j = json.loads(f.read_text(encoding='utf-8'))
            rel = j['file']
            if not (d.game.has(rel) and d.update.has(rel)) or d.update.read(rel) == d.game.read(rel):
                continue
            lines = port_script(lang, rel, j['lines'], d.update.read(rel), d.game.read(rel), report)
            n += 1
            if not a.dry_run:
                v10_name(f).write_text(json.dumps(dict(j, game='1.0', lines=lines), ensure_ascii=False, indent=1) + '\n',
                                       encoding='utf-8')
        print(f'{lang}: {n} scripts with a 1.0 variant')
        # data tables and names: from the 1.3.0 build
        built = {}
        for ed, dump in eds.items():
            out = tmp / lang / ed
            build(dump, lang, out, log=lambda *x: None)
            built[ed] = out / dump.title
        mod = built['kuwagata']
        for f in sorted((pack / 'binary').rglob('*.json*')):
            if '.v10.' in f.name:
                continue
            p = patch.load(f)
            rel = p['file']
            if rel.startswith('exefs/'):
                ed = p.get('edition', 'kuwagata')
                if ed not in eds:
                    continue
                dd = eds[ed]
                c13, c10 = dd.update.code(), dd.game.code()
                e13, e10 = dd.update.exheader(), dd.game.exheader()
                # the effect-pool fix (tools/effect_pool_fix.py) has branches that depend on the addresses: it is
                # left out of the port and applied again to the 1.0 program
                out13 = epf.strip(c13, patch.apply(p, c13), e13)
                out10 = port_code(c13, out13, c10, layout(dd.update), layout(dd.game), report)
                out10 = epf.apply(c10, out10, e10)
                q = patch.make(rel, c10, out10)
                q['edition'] = ed
                q['game'] = '1.0'
                print(f'{lang}: code.bin {ed}: {len(p["ops"])} runs -> {len(q["ops"])} on 1.0')
                if not a.dry_run:
                    patch.save(q, v10_name(f))
                continue
            if not (d.game.has(rel) and d.update.has(rel)) or d.update.read(rel) == d.game.read(rel):
                continue
            jp13, jp10 = d.update.read(rel), d.game.read(rel)
            out13 = (mod / 'romfs' / rel).read_bytes()
            if rel.endswith('PartsText.b'):
                out10, left = port_records(jp13, out13, jp10, lang)
                what = f'{len(left)} records without a 1.3.0 twin (kept Japanese)'
            elif len(jp13) != len(jp10):
                out10, (k, npairs, missing) = port_tokens(jp13, out13, jp10)
                what = f'{k} names written from {npairs} pairs ({missing} only in 1.3.0)'
            else:
                out10, notes = port_runs(jp13, out13, jp10, lookup)
                what = 'names: ' + ('; '.join(notes) or 'all the same as 1.3.0')
            q = patch.make(rel, jp10, out10)
            q['game'] = '1.0'
            print(f'{lang}: {rel}: {what}')
            if not a.dry_run:
                gz = f.name.endswith('.gz')
                dst = v10_name(f)
                patch.save(q, dst.with_name(dst.name[:-3]) if gz else dst, compress=gz)
        # textures the update changed: the same spec rendered on the 1.0 texture (tools/tex)
        sys.path.insert(0, str(REPO / 'tools' / 'tex'))
        import tempfile
        import texlib
        base_only = Dump(a.kuwagata[0])
        for f in sorted((pack / 'textures').rglob('*.json.gz')):
            if '.v10.' in f.name:
                continue
            q = patch.load(f)
            rel = q['file']
            if not (d.game.has(rel) and d.update.has(rel)) or d.update.read(rel) == d.game.read(rel):
                continue
            spec = json.loads((pack / 'texture_specs' / (rel.replace('/', '__') + '.json')).read_text(encoding='utf-8'))
            if rel in TEXTURES_V10:                  # the update replaced the poster: the 1.0 poster's own label
                like, text = TEXTURES_V10[rel]
                if like:
                    spec = json.loads((pack / 'texture_specs' / (like.replace('/', '__') + '.json'))
                                      .read_text(encoding='utf-8'))
                    spec['rel'] = rel
                if text:
                    for it in spec['items']:
                        if it.get('text'):
                            it['text'] = text[lang]
            texlib.SOURCE = base_only
            with tempfile.TemporaryDirectory() as t:
                texlib.write_only(spec, t)
                out10 = (Path(t) / rel).read_bytes()
            texlib.SOURCE = None
            v = patch.make(rel, d.game.read(rel), out10, enc='b64')
            v['game'] = '1.0'
            print(f'{lang}: texture {rel}: rendered on the 1.0 texture')
            if not a.dry_run:
                dst = v10_name(f)
                patch.save(v, dst.with_name(dst.name[:-3]), compress=True)
        for f in sorted((pack / 'names').glob('*.json')) if (pack / 'names').is_dir() else []:
            if f.name.endswith('.v10.json'):
                continue
            j = json.loads(f.read_text(encoding='utf-8'))
            rel = j['file']
            if not (d.game.has(rel) and d.update.has(rel)) or d.update.read(rel) == d.game.read(rel):
                continue
            slots, lost = port_names(j['slots'], d.update.read(rel), d.game.read(rel))
            print(f'{lang}: names {rel}: {len(slots)} slots on 1.0, {lost} without a 1.0 place')
            if not a.dry_run:
                v10_name(f).write_text(json.dumps(dict(j, game='1.0', slots=slots), ensure_ascii=False, indent=1) + '\n',
                                       encoding='utf-8')
        for r in report:
            print('  ', r)


if __name__ == '__main__':
    main()
