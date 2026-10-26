"""Row streaming equivalence (src_patch/rowfast.s, docs/ACCURACY.md Fixed 60): call each stage's row
routine (the collision ring row fill $938E, then the row's plane entries) in Unicorn on build A and
build B from the same RAM, for every window column start and row in a range, and compare all of RAM.

usage: test_rowfast.py <rom A> <rom B> <ram dump> [<ram dump> ...]
Every one of the six row routines is called on every dump (the stage's own and the others: the same
code on other data). Entry d1 = row, $FFB000 = first column; d1's upper word is set to a few
patterns (the original's tile loop adds d1.l).
"""
import sys
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN
from unicorn import m68k_const
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_D1, UC_M68K_REG_PC, UC_CPU_M68K_M68000

ROUTINES = (0x984C, 0x104DD4, 0x1100E0, 0x111098, 0x1156EC, 0x11AAE0)
SENTINEL = 0x3FFFF0


MACHINES = {}
REGS = [getattr(m68k_const, 'UC_M68K_REG_D%d' % i) for i in range(8)] + \
       [getattr(m68k_const, 'UC_M68K_REG_A%d' % i) for i in range(7)]


def machine(rom):
    if id(rom) not in MACHINES:
        uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        uc.mem_map(0, 0x400000); uc.mem_write(0, rom)
        uc.mem_write(SENTINEL, b'\x4e\x71\x4e\x71')
        uc.mem_map(0xFF0000, 0x10000)
        MACHINES[id(rom)] = uc
    return MACHINES[id(rom)]


def run(rom, ram, entry, d1, b000):
    uc = machine(rom)
    uc.mem_write(0xFF0000, ram)
    uc.mem_write(0xFFB000, bytes([b000 >> 8, b000 & 255]))
    sp = 0xFFFE00
    uc.mem_write(sp, SENTINEL.to_bytes(4, 'big'))
    for r in REGS:
        uc.reg_write(r, 0)
    uc.reg_write(UC_M68K_REG_A7, sp)
    uc.reg_write(UC_M68K_REG_D1, d1)
    try:
        uc.emu_start(entry, SENTINEL, count=200000)
    except Exception:                   # an unmapped read (another stage's routine on this RAM)
        return 'error'
    return bytes(uc.mem_read(0xFF0000, 0xFC00))     # stack scratch above $FFFC00 left out


def main():
    rom_a, rom_b = open(sys.argv[1], 'rb').read(), open(sys.argv[2], 'rb').read()
    rom_b = rom_b[:0x18E] + rom_a[0x18E:0x190] + rom_b[0x190:]     # the header checksum (a routine run on
                                                                   # another stage's RAM can read it)
    bad = 0
    for path in sys.argv[3:]:
        raw = open(path, 'rb').read()
        ram = bytes(raw[i ^ 1] for i in range(len(raw)))
        stage = ram[0xC512]
        b000 = ram[0xB000] << 8 | ram[0xB001]
        b00e = ram[0xB00E] << 8 | ram[0xB00F]
        for entry in ROUTINES:
          n = nerr = 0
          for col in range(max(0, b000 - 40), b000 + 41, 3):
            for row in range(max(0, b00e - 40), b00e + 56, 1 if col == b000 else 7):
                for hi in (0, 0x12340000, 0xFFFF0000):
                    a = run(rom_a, ram, entry, hi | row, col)
                    b = run(rom_b, ram, entry, hi | row, col)
                    n += 1
                    nerr += a == b == 'error'
                    if a != b:
                        bad += 1
                        if bad < 5:
                            if isinstance(a, str) or isinstance(b, str):
                                print('%s: $%X col %d row %d d1 %08X: %s / %s' % (path, entry, col, row, hi | row,
                                      a if isinstance(a, str) else 'ok', b if isinstance(b, str) else 'ok'))
                                continue
                            d = [i for i in range(len(a)) if a[i] != b[i]]
                            print('%s: $%X col %d row %d d1 %08X: %d bytes differ from $%06X'
                                  % (path, entry, col, row, hi | row, len(d), 0xFF0000 + d[0]))
          print('%s: stage index %d, routine $%X, %d calls compared (%d failing in both)' % (path, stage, entry, n, nerr))
    print('%d differ' % bad)
    sys.exit(1 if bad else 0)


main()
