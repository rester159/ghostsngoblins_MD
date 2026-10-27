"""A/B equivalence of two ROM builds over whole game updates: from each RAM
snapshot, run `iterations` updates of a stage loop in Unicorn on build A and
on build B with the same seeded random input on both pads; the RAM (stack
scratch above $FFFC00 excluded) and the VDP writes must match after every
update. Use it to check that an optimisation changes nothing but speed.

usage: test_ab.py <rom A> <rom B> <loop start hex> <loop end hex> <ram dump>... [-n iterations]
         [-pa ADDR=VAL] [-pb ADDR=VAL]   poke a word into A's / B's RAM first (VAL hex, or @ADDR to
                                         copy that word of the snapshot); repeatable
         [-x START-END]                  RAM range (hex, end exclusive) left out of the comparison
         [--novdp]                       don't compare VDP writes
         [--vbl]                         advance the VBlank counter ($FF7DFC) by one before each
                                         update (the passes that alternate by frame take both halves)
"""
import random
import sys
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_WRITE, UcError
from unicorn.m68k_const import UC_M68K_REG_A7, UC_M68K_REG_SR, UC_M68K_REG_PC, UC_CPU_M68K_M68000

args = sys.argv[1:]
N = 20
if '-n' in args:
    i = args.index('-n'); N = int(args[i + 1]); del args[i:i + 2]
POKES = {'-pa': [], '-pb': []}
EXCL = []
NOVDP = '--novdp' in args
if NOVDP:
    args.remove('--novdp')
VBL = '--vbl' in args
if VBL:
    args.remove('--vbl')
for flag in ('-pa', '-pb', '-x'):
    while flag in args:
        i = args.index(flag); v = args[i + 1]; del args[i:i + 2]
        if flag == '-x':
            a, b = v.split('-'); EXCL.append((int(a, 16) - 0xFF0000, int(b, 16) - 0xFF0000))
        else:
            a, b = v.split('='); POKES[flag].append((int(a, 16) - 0xFF0000, b))
rom_a, rom_b = open(args[0], 'rb').read(), open(args[1], 'rb').read()
START, END = int(args[2], 16), int(args[3], 16)


class Machine:
    def __init__(self, rom, ram):
        self.uc = uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        uc.mem_map(0, 0x400000); uc.mem_write(0, rom)
        uc.mem_map(0xFF0000, 0x10000); uc.mem_write(0xFF0000, ram)
        uc.mem_map(0xA00000, 0x20000); uc.mem_map(0xC00000, 0x10000)
        self.vdp, self.th, self.vb, self.pads = [], {}, [8], {}
        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.mem)

    def mem(self, uc, kind, addr, size, value, _):
        if kind == UC_MEM_WRITE:
            if 0xC00000 <= addr < 0xC00010:
                self.vdp.append((addr, size, value))
            if addr in (0xA10003, 0xA10005):
                self.th[addr] = value & 0x40
            return
        if 0xC00004 <= addr < 0xC00008:
            self.vb[0] ^= 8; uc.mem_write(0xC00004, bytes([0x34, self.vb[0]]))
        elif addr in (0xA11100, 0xA11101):
            uc.mem_write(0xA11100, b'\x00\x00')
        elif addr in (0xA10003, 0xA10005):
            hi, lo = self.pads.get(addr, (0x7F, 0x33))
            uc.mem_write(addr, bytes([hi if self.th.get(addr, 0x40) else lo]))

    def update(self):
        uc = self.uc
        if VBL:
            c = int.from_bytes(uc.mem_read(0xFF7DFC, 4), 'big')
            uc.mem_write(0xFF7DFC, ((c + 1) & 0xFFFFFFFF).to_bytes(4, 'big'))
        uc.reg_write(UC_M68K_REG_SR, 0x2700); uc.reg_write(UC_M68K_REG_A7, 0xFFFE00)
        try:
            uc.emu_start(START, END, count=20_000_000)
        except UcError as e:
            return 'stopped %s at %X' % (e, uc.reg_read(UC_M68K_REG_PC))
        return None

    def state(self):
        m = bytearray(self.uc.mem_read(0xFF0000, 0xFC00))
        for a, b in EXCL:
            m[a:b] = bytes(b - a)
        return bytes(m)


bad = 0
for path in args[4:]:
    raw = open(path, 'rb').read()
    ram = bytes(raw[i ^ 1] for i in range(len(raw)))
    def poked(which):
        m = bytearray(ram)
        for o, v in POKES[which]:
            w = m[int(v[1:], 16) - 0xFF0000:][:2] if v.startswith('@') else int(v, 16).to_bytes(2, 'big')
            m[o:o + 2] = w
        return bytes(m)
    a, b = Machine(rom_a, poked('-pa')), Machine(rom_b, poked('-pb'))
    rng = random.Random(path)
    result = 'identical'
    for it in range(N):
        if it % 8 == 0:
            pads = {}
            for port in (0xA10003, 0xA10005):
                bits = rng.getrandbits(6)
                if bits & 3 == 3: bits &= ~2
                if bits & 12 == 12: bits &= ~8
                pads[port] = (0x7F & ~bits, 0x33 & ~(0x10 if rng.random() < 0.2 else 0) & ~(bits & 3))
            a.pads = b.pads = pads
        ea, eb = a.update(), b.update()
        if ea or eb:
            result = 'A %s / B %s at update %d' % (ea, eb, it) if ea != eb else 'both stopped (%s)' % ea
            bad += ea != eb
            break
        if a.state() != b.state() or (a.vdp != b.vdp and not NOVDP):
            diff = [i for i, (x, y) in enumerate(zip(a.state(), b.state())) if x != y]
            result = 'DIFFERENT at update %d: RAM %s, VDP writes %s' % (
                it, ' '.join('%X' % (0xFF0000 + i) for i in diff[:8]), 'same' if a.vdp == b.vdp else 'differ')
            bad += 1
            break
        a.vdp.clear(); b.vdp.clear()
    print('%s: %s' % (path.rsplit('/', 1)[-1], result))
print('%d snapshot(s) differ' % bad)
sys.exit(1 if bad else 0)
