"""Equivalence test: the sound driver's request scan ($11CAB8) in the original
ROM vs the patched one (byte-wise scan, glue.s sound_scan), from the same RAM
with random request/enable bitmaps. Compares the Z80 command bytes written,
in order, and the final 68000 RAM.

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
    calls += len(za)
    if za != zb or ra[:0xFC00] != rb[:0xFC00]:      # $FFFC00 up: stack scratch
        bad += 1
        if bad <= 3:
            print('case', case, 'differs: z80 writes', len(za), len(zb))
print('%d cases, %d Z80 bytes written in total, %d mismatches' % (CASES, calls, bad))
sys.exit(1 if bad else 0)
