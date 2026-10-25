"""Which bytes of the co-op context ranges does Maximo's update touch?

Runs game updates in Unicorn from co-op RAM snapshots, with random input on
both pads (held for 8 updates at a time), and records every RAM
access made while Maximo's state is swapped in (between the two swap calls
of p2_frame), excluding the swap's own accesses. Prints, per context
range, the bytes read and written, so ranges can be cut to what is used.

usage: ctx_trace.py <rom> <patch.sym> <loop start> <loop end> <ram dump>... [-n iterations]
"""
import collections
import random
import struct
import sys
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, \
    UC_MEM_WRITE, UcError
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_SR, UC_M68K_REG_PC, UC_CPU_M68K_M68000

def ranges_from_p2(path):
    """ctx_ranges as defined in src_patch/p2.c"""
    src = open(path).read()
    body = src[src.index('ctx_ranges[] = {'):src.index('};', src.index('ctx_ranges[] = {'))]
    import re
    return [(int(a, 16), int(n, 16)) for a, n in re.findall(r'\{ 0x([0-9A-Fa-f]+), 0x([0-9A-Fa-f]+) \}', body)]


import os
RANGES = ranges_from_p2(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src_patch', 'p2.c'))

args = sys.argv[1:]
N = 2
if '-n' in args:
    i = args.index('-n'); N = int(args[i + 1]); del args[i:i + 2]
rom = open(args[0], 'rb').read()
sym = {l.split()[2]: int(l.split()[0], 16) for l in open(args[1]) if len(l.split()) == 3}
SWAP = sym.get('swap_ctx', sym.get('swap_fields'))
SWAP_END = min(v for v in sym.values() if v > SWAP)
START, END = int(args[2], 16), int(args[3], 16)
rng = random.Random(7)
rd = collections.defaultdict(int)
wr = collections.defaultdict(int)
in_ctx = [False]
swaps = [0]


def code(uc, addr, size, _):
    if addr == SWAP:
        swaps[0] += 1
        in_ctx[0] = swaps[0] % 2 == 1


def mem(uc, kind, addr, size, value, _):
    pc = uc.reg_read(UC_M68K_REG_PC)
    if kind == UC_MEM_WRITE:
        if addr in (0xA10003, 0xA10005):
            th[addr] = value & 0x40
    else:
        if 0xC00004 <= addr < 0xC00008:
            vb[0] ^= 8; uc.mem_write(0xC00004, bytes([0x34, vb[0]]))
        elif addr in (0xA11100, 0xA11101):
            uc.mem_write(0xA11100, b'\x00\x00')
        elif addr in (0xA10003, 0xA10005):         # random play on both pads
            hi, lo = pads[addr]
            uc.mem_write(addr, bytes([hi if th.get(addr, 0x40) else lo]))
    if not in_ctx[0] or SWAP <= pc < SWAP_END or not (0xFF0000 <= addr < 0x1000000):
        return
    for k in range(size):
        o = addr + k - 0xFF0000
        (wr if kind == UC_MEM_WRITE else rd)[o] += 1


for path in args[4:]:
    raw = open(path, 'rb').read()
    ram = bytes(raw[i ^ 1] for i in range(len(raw)))
    uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
    uc.mem_map(0, 0x400000); uc.mem_write(0, rom)
    uc.mem_map(0xFF0000, 0x10000); uc.mem_write(0xFF0000, ram)
    uc.mem_map(0xA00000, 0x20000); uc.mem_map(0xC00000, 0x10000)
    th, vb = {}, [8]
    uc.hook_add(UC_HOOK_CODE, code, begin=SWAP, end=SWAP)
    uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, mem)
    for it in range(N):
        if it % 8 == 0:                           # hold a random input for 8 updates
            pads = {}
            for port in (0xA10003, 0xA10005):
                b = rng.getrandbits(6)            # U D L R B C, 1 = pressed
                if b & 3 == 3: b &= ~2            # not up and down together
                if b & 12 == 12: b &= ~8
                a = rng.random() < 0.2
                pads[port] = (0x7F & ~b, 0x33 & ~(0x10 if a else 0) & ~(b & 3))
        uc.reg_write(UC_M68K_REG_SR, 0x2700); uc.reg_write(UC_M68K_REG_A7, 0xFFFE00)
        try:
            uc.emu_start(START, END, count=20_000_000)
        except UcError as e:
            print(path, 'stopped', e, hex(uc.reg_read(UC_M68K_REG_PC)))
            break

print('swaps seen: %d (should be 2 per update)' % swaps[0])
total = used = 0
for base, n in RANGES:
    marks = ''.join('W' if wr.get(base + k) else 'r' if rd.get(base + k) else '.' for k in range(n))
    u = sum(1 for c in marks if c != '.')
    total += n; used += u
    print('$FF%04X +%02X  %s  (%d of %d used)' % (base, n, marks, u, n))
print('used %d of %d bytes' % (used, total))
# accesses to Arthur-adjacent RAM outside the ranges (possible missing fields)
near = sorted(o for o in set(rd) | set(wr) if 0x9000 <= o < 0x9800 or 0xC300 <= o < 0xC400 or 0xB100 <= o < 0xB140)
outside = [o for o in near if not any(b <= o < b + n for b, n in RANGES)]
print('player-area bytes touched outside the ranges:', ' '.join('%04X%s' % (o, 'W' if wr.get(o) else '') for o in outside[:80]))
