"""Fuzz the stage-1 tombstone check ($10442A) of two builds against each other:
from real stage-1 RAM snapshots, place the player (X $FF9000, old X $FF9220,
Y $FF9004, $FF922A, $FF9410, $FFC512) at random around a random live tombstone
and call the routine once; RAM and d2-d7/a0-a6 must match afterwards.

usage: test_tomb.py <rom A> <rom B> <ram dump>... [-n cases per dump]
"""
import random
import struct
import sys
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN
from unicorn.m68k_const import *

args = sys.argv[1:]
N = 2000
if '-n' in args:
    i = args.index('-n'); N = int(args[i + 1]); del args[i:i + 2]
roms = [open(args[0], 'rb').read(), open(args[1], 'rb').read()]
REGS = [UC_M68K_REG_D2, UC_M68K_REG_D3, UC_M68K_REG_D4, UC_M68K_REG_D5, UC_M68K_REG_D6, UC_M68K_REG_D7] + \
       [getattr(sys.modules['unicorn.m68k_const'], 'UC_M68K_REG_A%d' % k) for k in range(7)]
RET = 0x3FFFF0                                   # a stop address: `nop`


def run(rom, ram, regs):
    uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
    uc.mem_map(0, 0x400000); uc.mem_write(0, rom); uc.mem_write(RET, b'\x4e\x71')
    uc.mem_map(0xFF0000, 0x10000); uc.mem_write(0xFF0000, bytes(ram))
    for r, v in zip(REGS, regs):
        uc.reg_write(r, v)
    uc.reg_write(UC_M68K_REG_A7, 0xFFFE00); uc.mem_write(0xFFFE00, struct.pack('>I', RET))
    uc.emu_start(0x10442A, RET, count=100000)
    return bytes(uc.mem_read(0xFF0000, 0xFC00)), [uc.reg_read(r) for r in REGS[:-1]]


bad = cases = 0
rng = random.Random(1)
for path in args[2:]:
    raw = open(path, 'rb').read()
    base = bytearray(raw[i ^ 1] for i in range(len(raw)))
    tombs = [0xE000 + 48 * k for k in range(30) if base[0xE000 + 48 * k + 4] and base[0xE000 + 48 * k + 10] == 1]
    for _ in range(N):
        ram = bytearray(base)
        t = rng.choice(tombs)
        tx, ty = struct.unpack('>hh', ram[t:t + 4])
        x = tx + rng.randint(-40, 40); ox = x + rng.randint(-4, 4)
        y = ty + rng.randint(-8, 40)
        ram[0x9000:0x9004] = struct.pack('>I', (x & 0xFFFF) << 8 | rng.getrandbits(8))
        ram[0x9220:0x9224] = struct.pack('>I', (ox & 0xFFFF) << 8 | rng.getrandbits(8))
        ram[0x9004:0x9006] = struct.pack('>H', y & 0xFFFF)
        ram[0x922A:0x922E] = struct.pack('>I', ((y + rng.randint(-10, 30)) & 0xFFFF) << 8)
        ram[0x9410:0x9412] = struct.pack('>H', rng.choice((0, 1, 2)))
        ram[0xC512] = rng.choice((0, 0, 0, 2, 3))
        if rng.random() < 0.2:
            ram[t + 6] = rng.choice((3, 0))
        regs = [rng.getrandbits(32) & ~1 if k >= 6 else rng.getrandbits(32) for k in range(len(REGS))]
        regs[-1] = 0xFFFE00
        a, b = run(roms[0], ram, regs), run(roms[1], ram, regs)
        cases += 1
        if a != b:
            bad += 1
            if bad <= 5:
                d = [hex(0xFF0000 + i) for i, (p, q) in enumerate(zip(a[0], b[0])) if p != q][:6]
                print('%s: differ (x %d ox %d y %d tomb %d,%d): RAM %s regs %s' % (path.rsplit('/', 1)[-1], x, ox, y, tx, ty, d, a[1] != b[1]))
print('%d of %d cases differ' % (bad, cases))
sys.exit(1 if bad else 0)
