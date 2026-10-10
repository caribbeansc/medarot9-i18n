#!/usr/bin/env python3
"""effect_pool_fix.py - code.bin fix for the crash in LONG robattles (Oct 2026; docs/encargos/crash-batalla-larga.md).

The game keeps the battle effects in a pool of 35 slots of 0xF0 bytes that sits right after the table of scheduled
battle sounds (Kuwagata 1.3.0: sounds 0x4CB0E4, effects 0x4CB344). When the pool is full, "create effect" returns -1
and the helpers that take an effect index do not check it: slot -1 is the last 0xF0 bytes of the sound table. So, in
a long fight that has filled the pool, effects stop appearing ("missing projectiles") and the effect code overwrites
the sound slots (an effect's anchor name lands on the elapsed counter of sound slot 17); the per-frame sound update
then "stops" a sound that never started, on channel 0xFF = a garbage pointer -> jump to address 0 (the reported
Undefined Instruction, PC 0, LR 0x199BC0). The 1.3.0 update already added a range check to the free function; the
rest of the helpers have none.

The fix (it only acts in that pathological case; a normal fight never fills the pool):
  1. create effect (FUN_002b1e0c): every allocation stamps the slot (its unused padding u16 at +0xEE = 1 + the
     newest stamp in use); when no slot is free, the OLDEST slot is reclaimed with the game's own free function -
     self-releasing kinds first (a leaked effect is old, the ones of the action in progress are new; persistent
     auras last) - and allocated: it never returns -1 any more;
  2. the helpers that take an effect index return at once for an index outside 0..34: actor of an effect
     (FUN_002b1df0, returns -1), actor flags (FUN_002b1c18), play / visibility (FUN_002b1c94), attach to a Medabot
     (FUN_002b1a80), and on 1.0 also the free function (FUN_002ab160, unchecked before the update).
New code: a small cave in the zero padding between .text and .rodata (the same, executable, page as the end of
.text), right after the strings the packs move there (1.3.0: 0x44BE10..0x44BF00; 1.0: 0x44AE10..0x44AF00); it refuses
to write if the cave is not empty. Every site is found by its Japanese bytes (the same in the four programs:
Kuwagata/Kabuto, 1.0/1.3.0); none of them is the target of another branch (the instruction after the pool loop is
the function's shared epilogue, so the "full" site is the loop's back edge). Evidence, bench runs and the
disassembly checks: experiments/crash_batalla/INFORME.md.

  python3 tools/effect_pool_fix.py es en --kuwagata <kwg update .cia | code.bin> --kuwagata10 <kwg game .3ds/.cia>
          --kabuto <kbt update .cia> --kabuto10 <kbt game .cci/.cia>        # rewrites langs/<lang>/binary/exefs/*
  (idempotent: the fix is stripped and applied again). tools/port_code.py and tools/port_v10.py strip it before
  porting and apply it to their output (its branches depend on the addresses).
"""
import argparse
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = 0x100000
CAVE_FROM_RO = 0x1F0        # the cave starts this far below the start of .rodata (1.3.0: 0x44BE10)
CAVE_LEN = 0xF0

COND = {'al': 0xE, 'eq': 0x0, 'ne': 0x1, 'hs': 0x2, 'lo': 0x3, 'hi': 0x8, 'ls': 0x9, 'ge': 0xA, 'lt': 0xB,
        'gt': 0xC, 'le': 0xD}


class FixError(Exception):
    pass


# --- a few ARM encodings --------------------------------------------------------------------------------------------

def _b(src, dst, cond='al', link=False):
    off = (dst - (src + 8)) >> 2
    if not -(1 << 23) <= off < (1 << 23):
        raise FixError('branch out of range')
    return (COND[cond] << 28) | (0x0B000000 if link else 0x0A000000) | (off & 0xFFFFFF)


def _imm(v):
    for rot in range(16):
        x = (((v << (2 * rot)) | (v >> (32 - 2 * rot))) & 0xFFFFFFFF) if rot else v
        if x < 256:
            return (rot << 8) | x
    raise FixError(f'immediate {v:#x}')


def _dpi(op, rd, rn, v, cond='al', s=0):
    return (COND[cond] << 28) | (1 << 25) | (op << 21) | (s << 20) | (rn << 16) | (rd << 12) | _imm(v)


def _cmp(rn, v):
    return _dpi(0b1010, 0, rn, v, s=1)


def _mov(rd, v):
    return _dpi(0b1101, rd, 0, v)


def _add(rd, rn, v):
    return _dpi(0b0100, rd, rn, v)


def _lsl(op, rd, rn, rm, sh):
    return 0xE0000000 | (op << 21) | (rn << 16) | (rd << 12) | (sh << 7) | rm


def _rsb4(rd, rn):                  # rd = rn*15  (rsb rd, rn, rn, lsl #4)
    return _lsl(0b0011, rd, rn, rn, 4)


def _add4(rd, rn, rm):              # rd = rn + (rm << 4)
    return _lsl(0b0100, rd, rn, rm, 4)


def _movr(rd, rm):
    return _lsl(0b1101, rd, 0, rm, 0)


def _ldr(rd, rn, off, byte=False):
    return 0xE5900000 | ((1 if byte else 0) << 22) | (rn << 16) | (rd << 12) | off


def _dpr(op, rd, rn, rm, cond='al', s=0):
    return (COND[cond] << 28) | (op << 21) | (s << 20) | (rn << 16) | (rd << 12) | rm


def _ldrh(rt, rn, off, cond='al', store=False):
    return (COND[cond] << 28) | (0x01C000B0 if store else 0x01D000B0) | (rn << 16) | (rt << 12) | \
        ((off >> 4) << 8) | (off & 0xF)


def _word(c, va):
    return struct.unpack_from('<I', c, va - BASE)[0]


def _target(c, va):
    """Destination of the B/BL instruction at va."""
    w = _word(c, va)
    if (w >> 25) & 0b111 != 0b101:
        raise FixError(f'no branch at {va:#x}')
    off = w & 0xFFFFFF
    if off & 0x800000:
        off -= 1 << 24
    return va + 8 + off * 4


# --- the sites, by their Japanese bytes (Kuwagata 1.3.0 reference; the four programs share them) -------------------

SIG = {
    # pool loop of FUN_002b1e0c: mvn r1,#0 ... blt loop; add sp,#0xdc; mov r0,r1; pop; rsb r1,r6,r6,lsl#4
    'pool': bytes.fromhex('0010e0e30060a0e3060266e0005288e00000d5e5000050e30500000a016086e2230056e3f7ffffba'
                          'dcd08de20100a0e1f08fbde8061266e0'),
    'df0': bytes.fromhex('011261e00112f0e7000051e30c00901582008012' '0000e003' '1eff2fe1'),
    'c18': bytes.fromhex('903080e2050265e0002286e00000d2e5000050e30000a0130d00000a'),
    'c94': bytes.fromhex('906080e2040264e000a0a0e3004285e00000d4e5000050e3'),
    'a80': bytes.fromhex('011261e0f0472de9015280e00000d5e520909de5000050e3'),
    'free13': bytes.fromhex('f0472de90060a0e10140a0e1'),
    'free13b': bytes.fromhex('001090e5401091e531ff2fe1000054e30090a0e3908080e2'),
    'free10b': bytes.fromhex('001090e5401091e531ff2fe1908080e2040264e00090a0e3004286e00000d4e5000050e3'),
}


def _find1(c, key, lo=0, hi=None):
    s = SIG[key]
    i = c.find(s, lo, hi)
    if i < 0 or c.find(s, i + 1, hi) >= 0:
        raise FixError(f'{key}: {"not found" if i < 0 else "not unique"}')
    return i + BASE


def layout(code: bytes, exh: bytes = None):
    """Addresses of the sites in this program (Japanese or translated: the sites are never translated)."""
    L = {}
    p = _find1(code, 'pool')
    # 'full' = the loop's back edge (blt loop): falling through it means no free slot. NOT the instruction after it:
    # that is the function's shared epilogue (the normal return jumps there too, from its end)
    L['loop'], L['full'], L['alloc'] = p + 8, p + 0x24, p + 0x34
    d = _find1(code, 'df0')
    L['df0'] = d
    c18 = _find1(code, 'c18')
    L['c18'], L['c18_ret'] = c18 + 4, _target(code, c18 + 0x18)
    c94 = _find1(code, 'c94')
    L['c94'] = c94 + 4
    L['c94_ret'] = _target(code, c94 + 0x18)
    a80 = _find1(code, 'a80')
    L['a80'], L['a80_ret'] = a80 + 0xC, _target(code, a80 + 0x18)
    # the free function: 1.3.0 has a range check; 1.0 does not (it gets one too)
    i = code.find(SIG['free13b'])
    if i >= 0 and code[i - 0x10:i - 4] == SIG['free13'] and code.find(SIG['free13b'], i + 1) < 0:
        L['free'], L['free_guard'] = i - 0x10 + BASE, None
    else:
        j = code.find(SIG['free10b'])
        if j < 0 or code[j - 0x10:j - 4] != SIG['free13'] or code.find(SIG['free10b'], j + 1) >= 0:
            raise FixError('free function not found')
        f = j - 0x10 + BASE
        L['free'], L['free_guard'], L['free_ret'] = f, f + 0x20, _target(code, f + 0x34)
    # the cave: below .rodata, in the zero padding after .text
    if exh is not None:
        t_addr, _, t_size = struct.unpack_from('<III', exh, 0x10)
        r_addr = struct.unpack_from('<I', exh, 0x20)[0]
        text_end = t_addr + t_size
    else:                           # no extended header (a dumped folder): the two known layouts
        r_addr = 0x44B000 if L['free_guard'] else 0x44C000
        text_end = r_addr - 0x200
    L['text_end'], L['cave'], L['cave_end'] = text_end, r_addr - CAVE_FROM_RO, r_addr - CAVE_FROM_RO + CAVE_LEN
    if L['cave'] < L['text_end']:
        raise FixError('no room for the cave')
    return L


def build(code: bytes, L) -> list:
    """[(va, bytes)] of the fix for the program whose layout is L."""
    words, pc = [], L['cave']

    def emit(w):
        nonlocal pc
        words.append(w)
        pc += 4
        return pc - 4

    # 1. allocation stamp (every allocation passes the instruction at L['alloc']; r8 = pool, r5 = the new slot,
    #    not marked used yet, r6 = its index): the slot's padding u16 at +0xEE = 1 + the newest stamp in use
    stamp = emit(_mov(0, 0))                        # r0 = newest stamp
    emit(_movr(1, 8))                               # r1 = slot 0
    emit(_add(2, 8, 0x2000))
    emit(_add(2, 2, 0xD0))                          # r2 = pool end (35 * 0xF0)
    loop1 = emit(_ldr(3, 1, 0, byte=True))          # used?
    emit(_cmp(3, 0))
    emit(_ldrh(3, 1, 0xEE, 'ne'))
    emit(_dpr(0b1010, 0, 3, 0, 'ne', s=1))          # cmpne r3, r0
    emit(_dpr(0b1101, 0, 0, 3, 'hi'))               # movhi r0, r3
    emit(_add(1, 1, 0xF0))
    emit(_dpr(0b1010, 0, 1, 2, s=1))                # cmp r1, r2
    emit(_b(pc, loop1, 'lo'))
    emit(_add(0, 0, 1))
    emit(_ldrh(0, 5, 0xEE, store=True))             # strh r0, [r5, #0xEE]
    emit(_rsb4(1, 6))                               # the replaced instruction
    emit(_b(pc, L['alloc'] + 4))
    # 2. pool full (L['full']; r8 = pool): reclaim the OLDEST slot, self-releasing kinds first (a leaked effect is
    #    old; the effects of the action in progress are new; persistent auras last), free it, allocate it
    reclaim = emit(_b(pc, L['loop'], 'lt'))         # the replaced back edge: a slot left to look at
    emit(_mov(6, 34))
    emit(_dpi(0b1111, 2, 0, 0))                     # r2 = best key (mvn r2, #0)
    emit(_mov(0, 0))                                # r0 = index
    emit(_movr(1, 8))                               # r1 = slot
    loop2 = emit(_ldrh(3, 1, 0xEE))                 # key = stamp
    emit(_ldr(12, 1, 8))
    emit(_cmp(12, 0))
    emit(_dpi(0b1100, 3, 3, 0x10000, 'le'))         # orrle r3, r3, #0x10000 (persistent kind)
    emit(_dpr(0b1010, 0, 3, 2, s=1))                # cmp r3, r2
    emit(_dpr(0b1101, 2, 0, 3, 'lo'))               # movlo r2, r3
    emit(_dpr(0b1101, 6, 0, 0, 'lo'))               # movlo r6, r0
    emit(_add(0, 0, 1))
    emit(_add(1, 1, 0xF0))
    emit(_cmp(0, 35))
    emit(_b(pc, loop2, 'lt'))
    emit(_rsb4(0, 6))
    emit(_add4(5, 8, 0))                            # r5 = victim slot
    emit(_movr(0, 8))
    emit(_movr(1, 6))
    emit(_b(pc, L['free'], link=True))              # free(pool, r6)
    emit(_b(pc, L['alloc']))                        # allocate it (through the stamp)
    # 3. guards: an index outside 0..34 returns at once
    g_df0 = emit(_cmp(1, 35))                       # FUN_002b1df0(pool, r1 = index)
    emit(0x23E00000)                                #   mvnhs r0, #0
    emit(0x212FFF1E)                                #   bxhs lr
    emit(_rsb4(1, 1))
    emit(_b(pc, L['df0'] + 4))
    g_c18 = emit(_cmp(5, 35))                       # FUN_002b1c18 (r5 = index)
    emit(_b(pc, L['c18_ret'], 'hs'))
    emit(_rsb4(0, 5))
    emit(_b(pc, L['c18'] + 4))
    g_c94 = emit(_cmp(4, 35))                       # FUN_002b1c94 (r4 = index)
    emit(_b(pc, L['c94_ret'], 'hs'))
    emit(_rsb4(0, 4))
    emit(_b(pc, L['c94'] + 4))
    g_a80 = emit(_cmp(1, 0x200))                    # FUN_002b1a80 (r1 = index*15: < 512 <=> 0..34)
    emit(_b(pc, L['a80_ret'], 'hs'))
    emit(_ldr(0, 5, 0, byte=True))
    emit(_b(pc, L['a80'] + 4))
    sites = [(L['alloc'], stamp), (L['full'], reclaim), (L['df0'], g_df0), (L['c18'], g_c18), (L['c94'], g_c94),
             (L['a80'], g_a80)]
    if L.get('free_guard'):
        g_free = emit(_cmp(4, 35))                  # 1.0 free function (r4 = index)
        emit(_b(pc, L['free_ret'], 'hs'))
        emit(_rsb4(0, 4))
        emit(_b(pc, L['free_guard'] + 4))
        sites.append((L['free_guard'], g_free))
    if pc > L['cave_end']:
        raise FixError(f'cave overflow ({pc - L["cave"]} bytes)')
    out = [(L['cave'], b''.join(struct.pack('<I', w) for w in words))]
    out += [(va, struct.pack('<I', _b(va, dst))) for va, dst in sites]
    return out


def has_fix(out: bytes, L) -> bool:
    return any(out[L['cave'] - BASE:L['cave_end'] - BASE])


def strip(jp: bytes, out: bytes, exh: bytes) -> bytes:
    """The translated program without the fix (Japanese bytes back at the sites, the cave zeroed)."""
    L = layout(jp, exh)
    o = bytearray(out)
    sites = [L['alloc'], L['full'], L['df0'], L['c18'], L['c94'], L['a80']] + \
        ([L['free_guard']] if L.get('free_guard') else [])
    for va in sites:
        o[va - BASE:va - BASE + 4] = jp[va - BASE:va - BASE + 4]
    o[L['cave'] - BASE:L['cave_end'] - BASE] = jp[L['cave'] - BASE:L['cave_end'] - BASE]
    return bytes(o)


def apply(jp: bytes, out: bytes, exh: bytes) -> bytes:
    """out (the translated program, without the fix) + the fix. Checks the sites still hold the Japanese bytes and
    that the cave is empty."""
    L = layout(jp, exh)
    if layout(out, exh) != L:
        raise FixError('the translated program moved the sites')
    if any(jp[L['cave'] - BASE:L['cave_end'] - BASE]) or has_fix(out, L):
        raise FixError('the cave is not empty (fix already applied, or strings there)')
    o = bytearray(out)
    for va, data in build(jp, L):
        o[va - BASE:va - BASE + len(data)] = data
    return bytes(o)


# --- driver: rewrite the language packs ---------------------------------------------------------------------------

def main():
    sys.path.insert(0, str(REPO))
    from m9 import patch
    from m9.dump import Source
    ap = argparse.ArgumentParser()
    ap.add_argument('langs', nargs='+')
    ap.add_argument('--kuwagata', required=True, help='Kuwagata 1.3.0 update (.cia) or its code.bin')
    ap.add_argument('--kuwagata-exh', help='with a bare code.bin: its exheader.bin')
    ap.add_argument('--kuwagata10', help='Kuwagata game (.3ds / .cia)')
    ap.add_argument('--kabuto', help='Kabuto 1.3.0 update (.cia)')
    ap.add_argument('--kabuto10', help='Kabuto game (.cci / .cia)')
    a = ap.parse_args()

    def program(path, exh=None):
        if path.endswith('.bin'):           # a bare decompressed code.bin (+ its exheader: <name>.exh or exheader.bin)
            e = Path(exh) if exh else next((q for q in (Path(path).with_suffix('.exh'),
                                                        Path(path).with_name('exheader.bin')) if q.is_file()), None)
            return Path(path).read_bytes(), (e.read_bytes() if e else None)
        s = Source(path)
        return s.code(), s.exheader()

    progs = {'code.bin.json': program(a.kuwagata, a.kuwagata_exh)}
    if a.kuwagata10:
        progs['code.bin.v10.json'] = program(a.kuwagata10)
    if a.kabuto:
        progs['code.bin.kabuto.json'] = program(a.kabuto)
    if a.kabuto10:
        progs['code.bin.kabuto.v10.json'] = program(a.kabuto10)
    for lang in a.langs:
        for name, (jp, exh) in progs.items():
            f = REPO / 'langs' / lang / 'binary' / 'exefs' / name
            p = patch.load(f)
            if p['src'] != patch.sha1(jp):
                raise SystemExit(f'{f}: made for another code.bin')
            out = patch.apply(p, jp)
            new = apply(jp, strip(jp, out, exh), exh)
            q = patch.make('exefs/code.bin', jp, new)
            q = {k: q.get(k, p[k]) for k in p}           # the pack's keys (edition, game), in its order
            patch.save(q, f)
            L = layout(jp, exh)
            print(f'{lang} {name}: fix at cave {L["cave"]:#x}, sites ' +
                  ', '.join(f'{L[k]:#x}' for k in ('full', 'df0', 'c18', 'c94', 'a80')) +
                  (f', free guard {L["free_guard"]:#x}' if L.get('free_guard') else ''))


if __name__ == '__main__':
    main()
