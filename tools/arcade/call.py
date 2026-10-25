"""Call one arcade routine from a saved state, for black-box contracts.

    from call import Caller
    k = Caller('<state>')                 # a tools/arcade/gng.py state file
    k.mem[0x507] = 200                    # set up RAM (k.mem is reset from the state each call)
    carry, regs = k.call(0x8CA7, x=0x510, bank=4, setup=lambda m: ...)

Runs from `addr` with the given registers until it returns (a sentinel on the
stack), with interrupts off. Returns (carry flag, register dict); k.g.mem holds
the RAM afterwards.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gng import GnG                 # noqa: E402
from cpu6809 import C as CARRY      # noqa: E402

ROMS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'rom')


class Caller:
    def __init__(self, state, romdir=ROMS):
        self.g = GnG(romdir)
        self.g.load(state)
        self.base = bytes(self.g.mem)
        self.base_bank = self.g.bank

    def call(self, addr, setup=None, bank=None, limit=100000, **regs):
        g = self.g
        g.mem[:] = self.base
        g.set_bank(self.base_bank if bank is None else bank)
        if setup:
            setup(g.mem)
        c = g.cpu
        c.irq = c.waiting = c.cwai = False
        c.s = regs.pop('s', 0x1D00)
        for r, v in regs.items():
            setattr(c, r, v)
        c.push16s(0xFFF0)
        c.pc = addr
        n = 0
        while c.pc != 0xFFF0:
            op = g.mem[c.pc]
            c.pc = (c.pc + 1) & 0xFFFF
            c.ops[op]()
            n += 1
            if n > limit:
                raise RuntimeError('no return after %d instructions (pc %04X)' % (n, c.pc))
        return bool(c.cc & CARRY), dict(a=c.a, b=c.b, x=c.x, y=c.y, u=c.u, cc=c.cc)
