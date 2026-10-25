"""Equivalence test for an in-place engine patch: whole game updates of the
stage-1 loop ($5CE-$95A) from real RAM snapshots, on the original ROM and on
a copy with only the patch applied; the resulting RAM must be identical
(stack scratch above $FFFC00 excluded), as must the VDP writes.

usage: test_inplace.py <rom> <patch.bin> <address hex> <ram dump>... [-n iterations]
"""
import struct
import sys
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_WRITE, UcError
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_SR, UC_M68K_REG_PC, UC_CPU_M68K_M68000

args = sys.argv[1:]
N = 1
if '-n' in args:
    i = args.index('-n'); N = int(args[i + 1]); del args[i:i + 2]
rom = open(args[0], 'rb').read()
patch = open(args[1], 'rb').read()
at = int(args[2], 16)
patched = bytearray(rom); patched[at:at + len(patch)] = patch


def run(code, ram_raw):
    ram = bytes(ram_raw[i ^ 1] for i in range(len(ram_raw)))
    uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
    uc.mem_map(0, 0x400000); uc.mem_write(0, bytes(code))
    uc.mem_map(0xFF0000, 0x10000); uc.mem_write(0xFF0000, ram)
    uc.mem_map(0xA00000, 0x20000); uc.mem_map(0xC00000, 0x10000)
    vdp, th, vb = [], {}, [8]

    def mem(uc, kind, addr, size, value, _):
        if kind == UC_MEM_WRITE:
            if 0xC00000 <= addr < 0xC00010:
                vdp.append((addr, size, value))
            if addr in (0xA10003, 0xA10005):
                th[addr] = value & 0x40
            return
        if 0xC00004 <= addr < 0xC00008:
            vb[0] ^= 8; uc.mem_write(0xC00004, bytes([0x34, vb[0]]))
        elif addr in (0xA11100, 0xA11101):
            uc.mem_write(0xA11100, b'\x00\x00')
        elif addr in (0xA10003, 0xA10005):
            uc.mem_write(addr, b'\x7f' if th.get(addr, 0x40) else b'\x33')
    uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, mem)
    for _ in range(N):
        uc.reg_write(UC_M68K_REG_SR, 0x2700); uc.reg_write(UC_M68K_REG_A7, 0xFFFE00)
        try:
            uc.emu_start(0x5CE, 0x95A, count=20_000_000)
        except UcError as e:
            return None, 'stopped %s at %X' % (e, uc.reg_read(UC_M68K_REG_PC))
    return bytes(uc.mem_read(0xFF0000, 0xFC00)), vdp


bad = 0
for path in args[3:]:
    raw = open(path, 'rb').read()
    a = run(rom, raw); b = run(patched, raw)
    same = a == b
    print('%s: %s' % (path.rsplit('/', 1)[-1], 'identical' if same else 'DIFFERENT'))
    bad += not same
sys.exit(1 if bad else 0)
