"""terrain_probe.py <arc state> <port rom> <port ram>: Arthur's floor probe at every 16 px cell around the camera
(columns -24..+31, rows -12..+19), arcade $8CA7 (tools/arcade/call.py) against port $85D2 (Unicorn) on the given
states; prints the disagreements per row and the rows that have any (A = floor only in the arcade, P = only in
the port). Used for Fixed 37, 49 and 65 (docs/ACCURACY.md)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'arcade'))
from call import Caller
from unicorn import *
from unicorn.m68k_const import *
k = Caller(sys.argv[1]); am = k.base
acx, acy = am[0x9C] << 8 | am[0x9D], am[0x9E] << 8 | am[0x9F]
ROM = open(sys.argv[2], 'rb').read(); raw = open(sys.argv[3], 'rb').read()
RAM = bytes(raw[i ^ 1] for i in range(len(raw)))
pcx = RAM[0x9100] << 8 | RAM[0x9101]; pcy = RAM[0x9102] << 8 | RAM[0x9103]
print('camera arcade', acx, acy, 'port', pcx, pcy)
uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN); uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
uc.mem_map(0, 0x400000); uc.mem_write(0, ROM); uc.mem_map(0xFF0000, 0x10000)
def port_probe(x, y):
    uc.mem_write(0xFF0000, RAM)
    uc.reg_write(UC_M68K_REG_D0, x); uc.reg_write(UC_M68K_REG_D1, y)
    uc.reg_write(UC_M68K_REG_A0, 0xFF0000); uc.reg_write(UC_M68K_REG_A3, 0x14A6E); uc.reg_write(UC_M68K_REG_A4, 0x14B6E)
    uc.reg_write(UC_M68K_REG_A7, 0xFFFE00); uc.mem_write(0xFFFE00, b'\x00\x3f\xff\xf0')
    uc.emu_start(0x85D2, 0x3FFFF0, count=20000)
    return uc.reg_read(UC_M68K_REG_D0) != 0
def arc_probe(x, y):
    def setup(m):
        m[0x506] = x >> 8; m[0x507] = x & 255; m[0x508] = 0x80
        m[0x509] = y >> 8; m[0x50A] = y & 255; m[0x50B] = 0x80
    c, _ = k.call(0x8CA7, x=0x510, bank=4, setup=setup)
    return c
import collections
dis = collections.Counter(); tot = collections.Counter()
for dr in range(-12, 20):
    for dc in range(-24, 32):
        x = (acx // 16 + dc) * 16 + 8; y = (acy // 16 + dr) * 16 + 8
        if x < 0 or y < 0: continue
        a = arc_probe(x, y); p = port_probe(x, y)
        tot[dr] += 1
        if a != p: dis[dr] += 1
print('total disagreements %d of %d' % (sum(dis.values()), sum(tot.values())))
print('row offset: disagreements / cells')
for dr in sorted(tot): print('%+d: %d/%d' % (dr, dis[dr], tot[dr]), end='  ')
print()
for dr in [d for d in sorted(tot) if dis[d]]:
    row = ''
    for dc in range(-24, 32):
        x = (acx // 16 + dc) * 16 + 8; y = (acy // 16 + dr) * 16 + 8
        if x < 0 or y < 0: row += ' '; continue
        a = arc_probe(x, y); p = port_probe(x, y)
        row += '.' if not a and not p else ('#' if a and p else ('A' if a else 'P'))
    print('%+3d %s' % (dr, row))
