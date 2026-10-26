"""Test of the sound driver's restore scan ($11CAB8) in the original ROM vs the
patched one (byte-wise scan, glue.s sound_scan), from the same RAM with random
request/enable bitmaps. Both runs' YM2612 writes (the (part, register, value)
triples queued for the Z80) are checked against a model of the scan: the
original's in ascending register order, the patched one's the same except
that each requested $A0+c or $A4+c is sent as the pair $A4+c, $A0+c (the
chip's single $A4-$A6 latch). The final 68000 RAM must match apart from the
queue pointers.

usage: test_sound_scan.py <original-layout rom> <patched rom> <ram dump> [cases]
"""
import random
import struct
import sys
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_WRITE
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_SR, UC_CPU_M68K_M68000

raw = open(sys.argv[3], 'rb').read()
RAM0 = bytearray(raw[i ^ 1] for i in range(len(raw)))
CASES = int(sys.argv[4]) if len(sys.argv) > 4 else 200


def run(rom, ram):
    uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
    uc.mem_map(0, 0x400000); uc.mem_write(0, rom)
    uc.mem_map(0xFF0000, 0x10000); uc.mem_write(0xFF0000, bytes(ram))
    uc.mem_map(0xA00000, 0x20000)
    uc.mem_map(0xC00000, 0x10000)
    z80 = []

    def mem(uc, kind, addr, size, value, _):
        if kind == UC_MEM_WRITE:
            if 0xA00000 <= addr < 0xA02000:
                z80.append((addr, value & 0xFF))
            return
        if addr in (0xA11100, 0xA11101):
            uc.mem_write(0xA11100, b'\x00\x00')
    uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, mem)
    # the routine's caller is a bsr: run it as a subroutine with a sentinel return
    uc.reg_write(UC_M68K_REG_SR, 0x2700)
    sp = 0xFFFE00
    uc.mem_write(sp, struct.pack('>I', 0x3FFFF0))
    uc.reg_write(UC_M68K_REG_A7, sp)
    uc.emu_start(0x11CAB8, 0x3FFFF0, count=5_000_000)
    return z80, bytes(uc.mem_read(0xFF0000, 0x10000))


def triples(z80):
    d = [v for a, v in z80 if 0xA01200 <= a < 0xA01500]
    return [tuple(d[i:i + 3]) for i in range(0, len(d), 3)]


def model(ram, pair):
    req = bytearray(ram[0x8650:0x8690])
    out = []

    def send(i, b):
        if ram[0x8610 + i] >> b & 1:
            r = i * 8 + b
            out.append((r >> 8, r & 0xFF, ram[0x8410 + r]))
    for i in range(64):
        if pair and i & 0x1F == 0x14:
            for c in range(3):
                if req[i] >> c & 0x11:
                    req[i] &= 0xFF & ~(0x11 << c)
                    send(i, c + 4)
                    send(i, c)
        for b in range(8):
            if req[i] >> b & 1:
                req[i] &= 0xFF & ~(1 << b)
                send(i, b)
    for c in range(6):
        if ram[0x8698 + c]:
            out.append((0, 0x28, ram[0x8690 + c]))
    return out


orig = open(sys.argv[1], 'rb').read()
new = open(sys.argv[2], 'rb').read()
rng = random.Random(1)
bad = 0
calls = 0
for case in range(CASES):
    ram = bytearray(RAM0)
    ram[0x8000] = 1                      # the scan runs only with sound on ...
    for k in range(3):
        ram[0x80C0 + k * 0xC0] = 0       # ... and no channel busy
    density = rng.choice([0, 1, 2, 8, 64])
    for i in range(64):
        ram[0x8650 + i] = rng.getrandbits(8) if rng.randrange(64) < density else 0
        ram[0x8610 + i] = rng.getrandbits(8)
    for i in range(512):
        ram[0x8410 + i] = rng.getrandbits(8)
    for i in range(8):
        ram[0x8690 + i] = rng.getrandbits(8)
        ram[0x8698 + i] = rng.getrandbits(8) & 1
    za, ra = run(orig, ram)
    zb, rb = run(new, ram)
    ta, tb = triples(za), triples(zb)
    calls += len(tb)
    keep = lambda r: r[:0x8400] + r[0x840C:0xFC00]   # minus the queue pointers; $FFFC00 up: stack scratch
    if ta != model(ram, False) or tb != model(ram, True) or keep(ra) != keep(rb):
        bad += 1
        if bad <= 3:
            print('case', case, 'differs: writes', len(ta), len(tb))
print('%d cases, %d YM2612 writes in total, %d mismatches' % (CASES, calls, bad))
sys.exit(1 if bad else 0)
