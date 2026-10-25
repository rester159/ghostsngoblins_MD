"""Profile game-update iterations of the GnG engine in Unicorn (68000) from a
real RAM snapshot: instructions and bus accesses per routine.

usage: uc_profile.py <rom> <ram dump from tools/headless/lr.py> [iterations] [start] [end]
       (TOP=n in the environment for a longer hottest-routine list)

Runs from `start` (default $5CE, after the stage-1 loop's VBlank wait) to `end`
(default $95A, the loop's branch back), `iterations` times, then prints:
  - per top-level call of the loop: instructions and bus accesses (inclusive)
  - the hottest routines by exclusive instructions, with their callers
Cycles are estimated: 4 per instruction word fetched plus a little internal
time, 4 per data access (8 for a long), and the internal time of multiply,
divide and shifts. VDP stalls and DMA time are not modelled. The VDP is a write sink with a toggling status, the Z80 bus is
always granted and the pads read as idle 3-button pads.
"""
import collections
import struct
import sys
from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_READ, \
    UC_HOOK_MEM_WRITE, UC_MEM_WRITE, UcError
from unicorn.m68k_const import UC_M68K_REG_PC, UC_M68K_REG_A7, UC_M68K_REG_SR, UC_CPU_M68K_M68000

import os
TOP = int(os.environ.get('TOP', '30'))          # rows of the hottest-routine list
ROM = open(sys.argv[1], 'rb').read()
raw = open(sys.argv[2], 'rb').read()
RAM = bytes(raw[i ^ 1] for i in range(len(raw)))
N = int(sys.argv[3]) if len(sys.argv) > 3 else 1
START = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0x5CE
END = int(sys.argv[5], 16) if len(sys.argv) > 5 else 0x95A

uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
uc.mem_map(0, 0x400000)
uc.mem_write(0, ROM)
uc.mem_map(0xFF0000, 0x10000)
uc.mem_write(0xFF0000, RAM)
uc.mem_map(0xA00000, 0x20000)
uc.mem_map(0xC00000, 0x10000)

vb = [8]
th = {}                                  # pad port -> TH level last written


def on_mem(uc, kind, addr, size, value, _):
    c = 8 if size == 4 else 4
    stats['bus'] += 1
    stats['cyc'] += c
    if stack:
        stack[-1][2]['bus'] += 1
        stack[-1][2]['cyc'] += c
        top[stack[0][0]]['bus'] += 1
        top[stack[0][0]]['cyc'] += c
    if kind == UC_MEM_WRITE:
        if addr in (0xA10003, 0xA10005):
            th[addr] = value & 0x40
        if 0xC00000 <= addr < 0xC00004:          # VDP data port: words written
            n = 2 if size == 4 else 1
            stats['vdp'] += n
            if stack:
                stack[-1][2]['vdp'] += n
                top[stack[0][0]]['vdp'] += n
        return
    if 0xC00004 <= addr < 0xC00008:
        vb[0] ^= 8
        uc.mem_write(0xC00004, bytes([0x34, vb[0]]))
    elif addr in (0xA11100, 0xA11101):
        uc.mem_write(0xA11100, b'\x00\x00')
    elif addr in (0xA10003, 0xA10005):     # idle 3-button pad
        uc.mem_write(addr, b'\x7f' if th.get(addr, 0x40) else b'\x33')


CALLS = (0x4EB9, 0x4EBA)
stats = collections.Counter()
excl = collections.defaultdict(collections.Counter)      # routine -> insn/bus
callers = collections.defaultdict(collections.Counter)
incl = collections.Counter()                             # routine -> inclusive cycles
INCL = os.environ.get('INCL')                            # set: also print inclusive costs
top = collections.defaultdict(collections.Counter)       # top-level call -> inclusive
stack = []                                               # [entry, sp at entry, counter]
pending = [None]


def is_call(op, word2):
    return op in CALLS or (op & 0xFF00) == 0x6100 or (op & 0xFFF8) in (0x4E90, 0x4EA8, 0x4EB0)


def extra_cycles(op):
    """Internal cycles of the slow instructions (68000 timing, typical cases)."""
    if (op & 0xF1C0) in (0xC0C0, 0xC1C0):        # mulu / muls
        return 54
    if (op & 0xF1C0) in (0x80C0, 0x81C0):        # divu / divs
        return 130
    if (op & 0xF000) == 0xE000:                  # shifts and rotates: ~2 per bit, assume 4 bits
        return 8
    if (op & 0xFF00) == 0x5100 and (op & 0x00F8) == 0x00C8:   # dbra
        return 2
    return 0


def on_code(uc, addr, size, _):
    sp = uc.reg_read(UC_M68K_REG_A7)
    while stack and sp > stack[-1][1]:
        stack.pop()
    if pending[0] is not None:
        caller = stack[-1][0] if stack else 'loop'
        stack.append([addr, sp, excl[addr]])
        callers[addr][caller] += 1
        pending[0] = None
    if addr == END:
        uc.emu_stop()
        return
    op = struct.unpack('>H', uc.mem_read(addr, 2))[0]
    cyc = 2 * size + 2 + extra_cycles(op)     # fetch 4 per word, a little internal time
    stats['insn'] += 1
    stats['cyc'] += cyc
    if stack:
        stack[-1][2]['insn'] += 1
        stack[-1][2]['cyc'] += cyc
        if INCL:
            for fr in {f[0] for f in stack}:
                incl[fr] += cyc
        top[stack[0][0]]['insn'] += 1
        top[stack[0][0]]['cyc'] += cyc
    if is_call(op, 0):
        pending[0] = addr


uc.hook_add(UC_HOOK_CODE, on_code)
uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, on_mem)
for it in range(N):
    uc.reg_write(UC_M68K_REG_SR, 0x2700)
    uc.reg_write(UC_M68K_REG_A7, 0xFFFE00)
    c = struct.unpack('>I', uc.mem_read(0xFF7DFC, 4))[0]
    uc.mem_write(0xFF7DFC, struct.pack('>I', c + 1))
    stack.clear()
    try:
        uc.emu_start(START, 0x400000, count=20_000_000)
    except UcError as e:
        print('stopped:', e, 'pc=%X' % uc.reg_read(UC_M68K_REG_PC))
        break

LINE = 488                                               # 68000 cycles per NTSC scanline
print('iterations %d: %d insns, ~%d cycles = ~%d scanlines per iteration (a frame is 262); '
      '%d VDP data words written (~%d lines of slot waits if done during the picture, at ~16 per line)'
      % (N, stats['insn'] // N, stats['cyc'] // N, stats['cyc'] // N // LINE, stats['vdp'] // N, stats['vdp'] // N // 16))
print('\ntop-level calls of the loop (inclusive, per iteration):')
for a, c in sorted(top.items(), key=lambda t: -t[1]['cyc'])[:25]:
    print('  %06X  insn %7d  lines %5.1f  %5.1f%%  vdp words %d' % (a, c['insn'] // N, c['cyc'] / N / LINE, 100 * c['cyc'] / stats['cyc'], c['vdp'] // N))
print('\nhottest routines (exclusive, per iteration):')
for a, c in sorted(excl.items(), key=lambda t: -t[1]['cyc'])[:TOP]:
    cs = ', '.join('%s x%d' % (('%06X' % k) if isinstance(k, int) else k, v // N) for k, v in callers[a].most_common(3))
    print('  %06X  insn %7d  lines %5.1f  %5.1f%%   from %s' % (a, c['insn'] // N, c['cyc'] / N / LINE,
                                                         100 * c['cyc'] / stats['cyc'], cs))

if INCL:
    print('\ninclusive (per iteration):')
    for a, c in incl.most_common(TOP):
        cs = ', '.join('%s x%d' % (('%06X' % k) if isinstance(k, int) else k, v // N) for k, v in callers[a].most_common(2))
        print('  %06X  lines %5.1f   from %s' % (a, c / N / LINE, cs))
