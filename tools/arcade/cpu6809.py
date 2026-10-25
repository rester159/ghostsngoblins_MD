"""MC6809 interpreter for headless arcade reference runs.

The board supplies `mem` (a 64 KiB bytearray read directly) and `write(addr,
value)` (for stores, so it can trap I/O and ROM). Cycle counts follow the
Motorola datasheet, including indexed-mode and push/pull extras, so a frame's
cycle budget runs the same amount of code as the real CPU. IRQ/FIRQ/NMI are
levels the board raises; `irq_ack` (if set) is called when the CPU takes an
IRQ, for "hold until acknowledged" lines.
"""

E, F, H, I, N, Z, V, C = 0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01


class CPU6809:
    def __init__(self, mem, write):
        self.mem = mem
        self.wr = write
        self.a = self.b = self.dp = 0
        self.x = self.y = self.u = self.s = self.pc = 0
        self.cc = I | F
        self.cycles = 0
        self.irq = self.firq = self.nmi = False
        self.irq_ack = None
        self.waiting = False          # SYNC / CWAI
        self.cwai = False
        self.hook = None              # hook(pc) before each instruction, or None
        self._build()

    def reset(self):
        self.cc = I | F
        self.dp = 0
        self.pc = self.r16(0xFFFE)

    # ---- memory -------------------------------------------------------
    def r16(self, a):
        m = self.mem
        return (m[a & 0xFFFF] << 8) | m[(a + 1) & 0xFFFF]

    def w16(self, a, v):
        self.wr(a & 0xFFFF, (v >> 8) & 0xFF)
        self.wr((a + 1) & 0xFFFF, v & 0xFF)

    def fetch(self):
        v = self.mem[self.pc]
        self.pc = (self.pc + 1) & 0xFFFF
        return v

    def fetch16(self):
        v = self.r16(self.pc)
        self.pc = (self.pc + 2) & 0xFFFF
        return v

    def push8s(self, v):
        self.s = (self.s - 1) & 0xFFFF
        self.wr(self.s, v & 0xFF)

    def push16s(self, v):
        self.push8s(v)
        self.push8s(v >> 8)

    def pull8s(self):
        v = self.mem[self.s]
        self.s = (self.s + 1) & 0xFFFF
        return v

    def pull16s(self):
        return (self.pull8s() << 8) | self.pull8s()

    # ---- addressing -----------------------------------------------------
    def ea_dir(self):
        return (self.dp << 8) | self.fetch()

    def ea_ext(self):
        return self.fetch16()

    def _reg(self, r):
        return (self.x, self.y, self.u, self.s)[r]

    def _setreg(self, r, v):
        v &= 0xFFFF
        if r == 0: self.x = v
        elif r == 1: self.y = v
        elif r == 2: self.u = v
        else: self.s = v

    def ea_idx(self):
        pb = self.fetch()
        r = (pb >> 5) & 3
        if not pb & 0x80:                       # 5-bit offset
            off = pb & 0x1F
            if off & 0x10: off -= 0x20
            self.cycles += 1
            return (self._reg(r) + off) & 0xFFFF
        t = pb & 0x0F
        ind = pb & 0x10
        if t == 0:
            ea = self._reg(r); self._setreg(r, ea + 1); self.cycles += 2
        elif t == 1:
            ea = self._reg(r); self._setreg(r, ea + 2); self.cycles += 3
        elif t == 2:
            ea = (self._reg(r) - 1) & 0xFFFF; self._setreg(r, ea); self.cycles += 2
        elif t == 3:
            ea = (self._reg(r) - 2) & 0xFFFF; self._setreg(r, ea); self.cycles += 3
        elif t == 4:
            ea = self._reg(r)
        elif t == 5:
            b = self.b - 256 if self.b & 0x80 else self.b
            ea = (self._reg(r) + b) & 0xFFFF; self.cycles += 1
        elif t == 6:
            a = self.a - 256 if self.a & 0x80 else self.a
            ea = (self._reg(r) + a) & 0xFFFF; self.cycles += 1
        elif t == 8:
            o = self.fetch(); o = o - 256 if o & 0x80 else o
            ea = (self._reg(r) + o) & 0xFFFF; self.cycles += 1
        elif t == 9:
            ea = (self._reg(r) + self.fetch16()) & 0xFFFF; self.cycles += 4
        elif t == 11:
            ea = (self._reg(r) + ((self.a << 8) | self.b)) & 0xFFFF; self.cycles += 4
        elif t == 12:
            o = self.fetch(); o = o - 256 if o & 0x80 else o
            ea = (self.pc + o) & 0xFFFF; self.cycles += 1
        elif t == 13:
            o = self.fetch16()
            ea = (self.pc + o) & 0xFFFF; self.cycles += 5
        elif t == 15:
            ea = self.fetch16(); self.cycles += 2
        else:
            raise RuntimeError('illegal indexed postbyte %02X at %04X' % (pb, self.pc))
        if ind:
            ea = self.r16(ea); self.cycles += 3
        return ea

    # ---- flags ------------------------------------------------------------
    def nz8(self, v):
        self.cc = (self.cc & ~(N | Z)) | (N if v & 0x80 else 0) | (0 if v else Z)

    def nz16(self, v):
        self.cc = (self.cc & ~(N | Z)) | (N if v & 0x8000 else 0) | (0 if v else Z)

    def add8(self, a, b, c=0):
        r = a + b + c
        cc = self.cc & ~(H | N | Z | V | C)
        if (a ^ b ^ r) & 0x10: cc |= H
        if r & 0x100: cc |= C
        if (~(a ^ b) & (a ^ r)) & 0x80: cc |= V
        r &= 0xFF
        if r & 0x80: cc |= N
        if not r: cc |= Z
        self.cc = cc
        return r

    def sub8(self, a, b, c=0):
        r = a - b - c
        cc = self.cc & ~(N | Z | V | C)
        if r & 0x100: cc |= C
        if ((a ^ b) & (a ^ r)) & 0x80: cc |= V
        r &= 0xFF
        if r & 0x80: cc |= N
        if not r: cc |= Z
        self.cc = cc
        return r

    def add16(self, a, b):
        r = a + b
        cc = self.cc & ~(N | Z | V | C)
        if r & 0x10000: cc |= C
        if (~(a ^ b) & (a ^ r)) & 0x8000: cc |= V
        r &= 0xFFFF
        if r & 0x8000: cc |= N
        if not r: cc |= Z
        self.cc = cc
        return r

    def sub16(self, a, b):
        r = a - b
        cc = self.cc & ~(N | Z | V | C)
        if r & 0x10000: cc |= C
        if ((a ^ b) & (a ^ r)) & 0x8000: cc |= V
        r &= 0xFFFF
        if r & 0x8000: cc |= N
        if not r: cc |= Z
        self.cc = cc
        return r

    def logic8(self, v):
        self.cc &= ~V
        self.nz8(v)
        return v

    # ---- 8-bit read-modify-write ops (return result) ----------------------
    def op_neg(self, v):
        r = (-v) & 0xFF
        cc = self.cc & ~(N | Z | V | C)
        if r & 0x80: cc |= N
        if not r: cc |= Z
        if v == 0x80: cc |= V
        if v: cc |= C
        self.cc = cc
        return r

    def op_com(self, v):
        r = (~v) & 0xFF
        self.cc = (self.cc & ~(V)) | C
        self.nz8(r)
        return r

    def op_lsr(self, v):
        self.cc = (self.cc & ~(N | Z | C)) | (C if v & 1 else 0)
        r = v >> 1
        if not r: self.cc |= Z
        return r

    def op_ror(self, v):
        r = (v >> 1) | (0x80 if self.cc & C else 0)
        self.cc = (self.cc & ~C) | (C if v & 1 else 0)
        self.nz8(r)
        return r

    def op_asr(self, v):
        r = (v >> 1) | (v & 0x80)
        self.cc = (self.cc & ~C) | (C if v & 1 else 0)
        self.nz8(r)
        return r

    def op_asl(self, v):
        r = (v << 1) & 0xFF
        cc = self.cc & ~(V | C)
        if v & 0x80: cc |= C
        if (v ^ (v << 1)) & 0x80: cc |= V
        self.cc = cc
        self.nz8(r)
        return r

    def op_rol(self, v):
        r = ((v << 1) | (1 if self.cc & C else 0)) & 0xFF
        cc = self.cc & ~(V | C)
        if v & 0x80: cc |= C
        if (v ^ (v << 1)) & 0x80: cc |= V
        self.cc = cc
        self.nz8(r)
        return r

    def op_dec(self, v):
        r = (v - 1) & 0xFF
        self.cc = (self.cc & ~V) | (V if v == 0x80 else 0)
        self.nz8(r)
        return r

    def op_inc(self, v):
        r = (v + 1) & 0xFF
        self.cc = (self.cc & ~V) | (V if v == 0x7F else 0)
        self.nz8(r)
        return r

    def op_tst(self, v):
        self.cc &= ~V
        self.nz8(v)
        return None

    def op_clr(self, v):
        self.cc = (self.cc & ~(N | V | C)) | Z
        return 0

    # ---- registers by TFR/EXG code ----------------------------------------
    def getr(self, code):
        if code == 0: return (self.a << 8) | self.b
        if code == 1: return self.x
        if code == 2: return self.y
        if code == 3: return self.u
        if code == 4: return self.s
        if code == 5: return self.pc
        if code == 8: return self.a
        if code == 9: return self.b
        if code == 10: return self.cc
        if code == 11: return self.dp
        return 0xFF

    def setr(self, code, v):
        if code == 0: self.a = (v >> 8) & 0xFF; self.b = v & 0xFF
        elif code == 1: self.x = v & 0xFFFF
        elif code == 2: self.y = v & 0xFFFF
        elif code == 3: self.u = v & 0xFFFF
        elif code == 4: self.s = v & 0xFFFF
        elif code == 5: self.pc = v & 0xFFFF
        elif code == 8: self.a = v & 0xFF
        elif code == 9: self.b = v & 0xFF
        elif code == 10: self.cc = v & 0xFF
        elif code == 11: self.dp = v & 0xFF

    # ---- stacking ---------------------------------------------------------
    def _push_all(self):
        self.push16s(self.pc); self.push16s(self.u); self.push16s(self.y); self.push16s(self.x)
        self.push8s(self.dp); self.push8s(self.b); self.push8s(self.a); self.push8s(self.cc)

    def interrupt(self):
        """Take a pending interrupt if allowed. Returns cycles used or 0."""
        if self.nmi:
            self.nmi = False
            if not self.cwai:
                self.cc |= E; self._push_all()
            self.cc |= I | F
            self.pc = self.r16(0xFFFC); self.waiting = self.cwai = False
            return 19
        if self.firq and not self.cc & F:
            if self.cwai:
                pass
            else:
                self.cc &= ~E
                self.push16s(self.pc); self.push8s(self.cc)
            self.cc |= I | F
            self.pc = self.r16(0xFFF6); self.waiting = self.cwai = False
            return 10
        if self.irq and not self.cc & I:
            if not self.cwai:
                self.cc |= E; self._push_all()
            self.cc |= I
            self.pc = self.r16(0xFFF8); self.waiting = self.cwai = False
            if self.irq_ack: self.irq_ack()
            return 19
        if self.waiting and (self.irq or self.firq or self.nmi):
            self.waiting = False          # SYNC ends on any interrupt line, masked or not
        return 0

    # ---- run --------------------------------------------------------------
    def run(self, budget):
        """Run until `budget` more cycles have elapsed."""
        end = self.cycles + budget
        ops = self.ops
        while self.cycles < end:
            if self.irq or self.firq or self.nmi:
                c = self.interrupt()
                if c:
                    self.cycles += c
                    continue
            if self.waiting:
                self.cycles = end
                break
            if self.hook:
                self.hook(self.pc)
            op = self.mem[self.pc]
            self.pc = (self.pc + 1) & 0xFFFF
            ops[op]()

    # ---- opcode table -----------------------------------------------------
    def _build(self):
        ops = [None] * 256
        p2 = {}
        p3 = {}
        cpu = self

        def ill(op):
            def f():
                raise RuntimeError('illegal opcode %02X at %04X' % (op, (cpu.pc - 1) & 0xFFFF))
            return f
        for i in range(256):
            ops[i] = ill(i)

        # RMW group: 0x00 direct, 0x40 A, 0x50 B, 0x60 indexed, 0x70 extended
        rmw = {0x0: self.op_neg, 0x3: self.op_com, 0x4: self.op_lsr, 0x6: self.op_ror,
               0x7: self.op_asr, 0x8: self.op_asl, 0x9: self.op_rol, 0xA: self.op_dec,
               0xC: self.op_inc, 0xD: self.op_tst, 0xF: self.op_clr}
        for lo, fn in rmw.items():
            def mk_mem(fn, eaf, cyc):
                def f():
                    ea = eaf()
                    r = fn(cpu.mem[ea])
                    if r is not None: cpu.wr(ea, r)
                    cpu.cycles += cyc
                return f
            def mk_a(fn):
                def f():
                    r = fn(cpu.a)
                    if r is not None: cpu.a = r
                    cpu.cycles += 2
                return f
            def mk_b(fn):
                def f():
                    r = fn(cpu.b)
                    if r is not None: cpu.b = r
                    cpu.cycles += 2
                return f
            ops[0x00 | lo] = mk_mem(fn, self.ea_dir, 6)
            ops[0x40 | lo] = mk_a(fn)
            ops[0x50 | lo] = mk_b(fn)
            ops[0x60 | lo] = mk_mem(fn, self.ea_idx, 6)
            ops[0x70 | lo] = mk_mem(fn, self.ea_ext, 7)
        # TST/CLR memory cycle quirks are close enough; JMP:
        def jmp(eaf, cyc):
            def f():
                cpu.pc = eaf(); cpu.cycles += cyc
            return f
        ops[0x0E] = jmp(self.ea_dir, 3)
        ops[0x6E] = jmp(self.ea_idx, 3)
        ops[0x7E] = jmp(self.ea_ext, 4)

        # misc
        def nop(): cpu.cycles += 2
        ops[0x12] = nop
        def sync(): cpu.waiting = True; cpu.cycles += 4
        ops[0x13] = sync
        def lbra():
            o = cpu.fetch16(); cpu.pc = (cpu.pc + o) & 0xFFFF; cpu.cycles += 5
        ops[0x16] = lbra
        def lbsr():
            o = cpu.fetch16(); cpu.push16s(cpu.pc); cpu.pc = (cpu.pc + o) & 0xFFFF; cpu.cycles += 9
        ops[0x17] = lbsr
        def daa():
            a = cpu.a; cf = 0; lsn = a & 0x0F; msn = a & 0xF0
            if (cpu.cc & H) or lsn > 9: cf |= 0x06
            if (cpu.cc & C) or msn > 0x90 or (msn > 0x80 and lsn > 9): cf |= 0x60
            r = a + cf
            cpu.cc = (cpu.cc & ~(V)) | (C if r & 0x100 or cpu.cc & C else 0)
            cpu.a = r & 0xFF; cpu.nz8(cpu.a); cpu.cycles += 2
        ops[0x19] = daa
        def orcc(): cpu.cc |= cpu.fetch(); cpu.cycles += 3
        ops[0x1A] = orcc
        def andcc(): cpu.cc &= cpu.fetch(); cpu.cycles += 3
        ops[0x1C] = andcc
        def sex():
            cpu.a = 0xFF if cpu.b & 0x80 else 0
            cpu.cc &= ~V; cpu.nz16((cpu.a << 8) | cpu.b); cpu.cycles += 2
        ops[0x1D] = sex
        def exg():
            pb = cpu.fetch(); s, d = pb >> 4, pb & 15
            vs, vd = cpu.getr(s), cpu.getr(d)
            if (s < 8) != (d < 8):
                if s < 8: vs &= 0xFF; vd |= 0xFF00
                else: vd &= 0xFF; vs |= 0xFF00
            cpu.setr(s, vd); cpu.setr(d, vs); cpu.cycles += 8
        ops[0x1E] = exg
        def tfr():
            pb = cpu.fetch(); s, d = pb >> 4, pb & 15
            v = cpu.getr(s)
            if s < 8 and d >= 8: v &= 0xFF
            elif s >= 8 and d < 8: v |= 0xFF00
            cpu.setr(d, v); cpu.cycles += 6
        ops[0x1F] = tfr

        # branches
        conds = [
            lambda c: True, lambda c: False,
            lambda c: not (c & (C | Z)), lambda c: bool(c & (C | Z)),
            lambda c: not c & C, lambda c: bool(c & C),
            lambda c: not c & Z, lambda c: bool(c & Z),
            lambda c: not c & V, lambda c: bool(c & V),
            lambda c: not c & N, lambda c: bool(c & N),
            lambda c: bool(c & N) == bool(c & V), lambda c: bool(c & N) != bool(c & V),
            lambda c: not c & Z and bool(c & N) == bool(c & V),
            lambda c: bool(c & Z) or bool(c & N) != bool(c & V),
        ]
        for k in range(16):
            def mkb(cond):
                def f():
                    o = cpu.fetch()
                    if cond(cpu.cc):
                        cpu.pc = (cpu.pc + (o - 256 if o & 0x80 else o)) & 0xFFFF
                    cpu.cycles += 3
                return f
            def mklb(cond):
                def f():
                    o = cpu.fetch16()
                    if cond(cpu.cc):
                        cpu.pc = (cpu.pc + o) & 0xFFFF; cpu.cycles += 6
                    else:
                        cpu.cycles += 5
                return f
            ops[0x20 + k] = mkb(conds[k])
            if k: p2[0x20 + k] = mklb(conds[k])

        # LEA
        def leax(): cpu.x = cpu.ea_idx(); cpu.cc = (cpu.cc & ~Z) | (0 if cpu.x else Z); cpu.cycles += 4
        def leay(): cpu.y = cpu.ea_idx(); cpu.cc = (cpu.cc & ~Z) | (0 if cpu.y else Z); cpu.cycles += 4
        def leas(): cpu.s = cpu.ea_idx(); cpu.cycles += 4
        def leau(): cpu.u = cpu.ea_idx(); cpu.cycles += 4
        ops[0x30], ops[0x31], ops[0x32], ops[0x33] = leax, leay, leas, leau

        # push / pull
        def mkpsh(use_u):
            def f():
                pb = cpu.fetch(); n = 0
                def p8(v):
                    if use_u:
                        cpu.u = (cpu.u - 1) & 0xFFFF; cpu.wr(cpu.u, v & 0xFF)
                    else:
                        cpu.push8s(v)
                def p16(v): p8(v); p8(v >> 8)
                if pb & 0x80: p16(cpu.pc); n += 2
                if pb & 0x40: p16(cpu.s if use_u else cpu.u); n += 2
                if pb & 0x20: p16(cpu.y); n += 2
                if pb & 0x10: p16(cpu.x); n += 2
                if pb & 0x08: p8(cpu.dp); n += 1
                if pb & 0x04: p8(cpu.b); n += 1
                if pb & 0x02: p8(cpu.a); n += 1
                if pb & 0x01: p8(cpu.cc); n += 1
                cpu.cycles += 5 + n
            return f
        def mkpul(use_u):
            def f():
                pb = cpu.fetch(); n = 0
                def g8():
                    if use_u:
                        v = cpu.mem[cpu.u]; cpu.u = (cpu.u + 1) & 0xFFFF; return v
                    return cpu.pull8s()
                def g16(): return (g8() << 8) | g8()
                if pb & 0x01: cpu.cc = g8(); n += 1
                if pb & 0x02: cpu.a = g8(); n += 1
                if pb & 0x04: cpu.b = g8(); n += 1
                if pb & 0x08: cpu.dp = g8(); n += 1
                if pb & 0x10: cpu.x = g16(); n += 2
                if pb & 0x20: cpu.y = g16(); n += 2
                if pb & 0x40:
                    v = g16(); n += 2
                    if use_u: cpu.s = v
                    else: cpu.u = v
                if pb & 0x80: cpu.pc = g16(); n += 2
                cpu.cycles += 5 + n
            return f
        ops[0x34], ops[0x35], ops[0x36], ops[0x37] = mkpsh(False), mkpul(False), mkpsh(True), mkpul(True)

        def rts(): cpu.pc = cpu.pull16s(); cpu.cycles += 5
        ops[0x39] = rts
        def abx(): cpu.x = (cpu.x + cpu.b) & 0xFFFF; cpu.cycles += 3
        ops[0x3A] = abx
        def rti():
            cpu.cc = cpu.pull8s()
            if cpu.cc & E:
                cpu.a = cpu.pull8s(); cpu.b = cpu.pull8s(); cpu.dp = cpu.pull8s()
                cpu.x = cpu.pull16s(); cpu.y = cpu.pull16s(); cpu.u = cpu.pull16s()
                cpu.cycles += 15
            else:
                cpu.cycles += 6
            cpu.pc = cpu.pull16s()
        ops[0x3B] = rti
        def cwai():
            cpu.cc &= cpu.fetch(); cpu.cc |= E; cpu._push_all()
            cpu.cwai = True; cpu.waiting = True; cpu.cycles += 20
        ops[0x3C] = cwai
        def mul():
            r = cpu.a * cpu.b; cpu.a = r >> 8; cpu.b = r & 0xFF
            cpu.cc = (cpu.cc & ~(Z | C)) | (0 if r else Z) | (C if r & 0x80 else 0)
            cpu.cycles += 11
        ops[0x3D] = mul
        def swi_v(vec, mask):
            def f():
                cpu.cc |= E; cpu._push_all(); cpu.cc |= mask
                cpu.pc = cpu.r16(vec); cpu.cycles += 19
            return f
        ops[0x3F] = swi_v(0xFFFA, I | F)
        p2[0x3F] = swi_v(0xFFF4, 0)
        p3[0x3F] = swi_v(0xFFF2, 0)

        # ALU group, A (0x80-0xBF) and B (0xC0-0xFF)
        modes = ((0x00, None, 2), (0x10, self.ea_dir, 4), (0x20, self.ea_idx, 4), (0x30, self.ea_ext, 5))
        for regb, base in ((False, 0x80), (True, 0xC0)):
            for off, eaf, cyc in modes:
                def get8(eaf):
                    if eaf is None: return cpu.fetch
                    return lambda: cpu.mem[eaf()]
                g = get8(eaf)
                def alu(fn, regb, g, cyc, store=True):
                    def f():
                        v = g()
                        if regb:
                            r = fn(cpu.b, v)
                            if store: cpu.b = r
                        else:
                            r = fn(cpu.a, v)
                            if store: cpu.a = r
                        cpu.cycles += cyc
                    return f
                o = base + off
                ops[o + 0x0] = alu(lambda a, v: cpu.sub8(a, v), regb, g, cyc)
                ops[o + 0x1] = alu(lambda a, v: cpu.sub8(a, v), regb, g, cyc, False)
                ops[o + 0x2] = alu(lambda a, v: cpu.sub8(a, v, 1 if cpu.cc & C else 0), regb, g, cyc)
                ops[o + 0x4] = alu(lambda a, v: cpu.logic8(a & v), regb, g, cyc)
                ops[o + 0x5] = alu(lambda a, v: cpu.logic8(a & v), regb, g, cyc, False)
                ops[o + 0x6] = alu(lambda a, v: cpu.logic8(v), regb, g, cyc)
                ops[o + 0x8] = alu(lambda a, v: cpu.logic8(a ^ v), regb, g, cyc)
                ops[o + 0x9] = alu(lambda a, v: cpu.add8(a, v, 1 if cpu.cc & C else 0), regb, g, cyc)
                ops[o + 0xA] = alu(lambda a, v: cpu.logic8(a | v), regb, g, cyc)
                ops[o + 0xB] = alu(lambda a, v: cpu.add8(a, v), regb, g, cyc)
                if eaf is not None:
                    def st8(regb, eaf, cyc):
                        def f():
                            ea = eaf(); v = cpu.b if regb else cpu.a
                            cpu.logic8(v); cpu.wr(ea, v); cpu.cycles += cyc
                        return f
                    ops[o + 0x7] = st8(regb, eaf, cyc)

        # 16-bit ops
        def get16(eaf):
            if eaf is None: return cpu.fetch16
            return lambda: cpu.r16(eaf())
        modes16 = ((0x00, None, 4), (0x10, self.ea_dir, 6), (0x20, self.ea_idx, 6), (0x30, self.ea_ext, 7))
        D = lambda: (cpu.a << 8) | cpu.b
        def setD(v): cpu.a = (v >> 8) & 0xFF; cpu.b = v & 0xFF
        for off, eaf, cyc in modes16:
            g = get16(eaf)
            def mk(fn, g, cyc):
                def f():
                    fn(g()); cpu.cycles += cyc
                return f
            ops[0x83 + off] = mk(lambda v: setD(cpu.sub16(D(), v)), g, cyc)
            ops[0xC3 + off] = mk(lambda v: setD(cpu.add16(D(), v)), g, cyc)
            ops[0x8C + off] = mk(lambda v: cpu.sub16(cpu.x, v), g, cyc)
            p2[0x83 + off] = mk(lambda v: cpu.sub16(D(), v), g, cyc + 1)
            p2[0x8C + off] = mk(lambda v: cpu.sub16(cpu.y, v), g, cyc + 1)
            p3[0x83 + off] = mk(lambda v: cpu.sub16(cpu.u, v), g, cyc + 1)
            p3[0x8C + off] = mk(lambda v: cpu.sub16(cpu.s, v), g, cyc + 1)
            ld_c = cyc - 1                       # LD16 is one cycle faster than the ALU ops
            def ld(setter, g, cyc):
                def f():
                    v = g(); setter(v); cpu.cc &= ~V; cpu.nz16(v); cpu.cycles += cyc
                return f
            def sx(v): cpu.x = v
            def sy(v): cpu.y = v
            def su(v): cpu.u = v
            def ss(v): cpu.s = v
            ops[0x8E + off] = ld(sx, g, ld_c)
            ops[0xCC + off] = ld(setD, g, ld_c)
            ops[0xCE + off] = ld(su, g, ld_c)
            p2[0x8E + off] = ld(sy, g, ld_c + 1)
            p2[0xCE + off] = ld(ss, g, ld_c + 1)
            if eaf is not None:
                def st(getter, eaf, cyc):
                    def f():
                        ea = eaf(); v = getter(); cpu.cc &= ~V; cpu.nz16(v); cpu.w16(ea, v); cpu.cycles += cyc
                    return f
                st_c = cyc - 1
                ops[0x8F + off] = st(lambda: cpu.x, eaf, st_c)
                ops[0xCD + off] = st(D, eaf, st_c)
                ops[0xCF + off] = st(lambda: cpu.u, eaf, st_c)
                p2[0x8F + off] = st(lambda: cpu.y, eaf, st_c + 1)
                p2[0xCF + off] = st(lambda: cpu.s, eaf, st_c + 1)
        # JSR / BSR
        def bsr():
            o = cpu.fetch(); cpu.push16s(cpu.pc)
            cpu.pc = (cpu.pc + (o - 256 if o & 0x80 else o)) & 0xFFFF; cpu.cycles += 7
        ops[0x8D] = bsr
        def jsr(eaf, cyc):
            def f():
                ea = eaf(); cpu.push16s(cpu.pc); cpu.pc = ea; cpu.cycles += cyc
            return f
        ops[0x9D] = jsr(self.ea_dir, 7)
        ops[0xAD] = jsr(self.ea_idx, 7)
        ops[0xBD] = jsr(self.ea_ext, 8)

        def page(tbl, base):
            def f():
                op = cpu.fetch()
                h = tbl.get(op)
                if h is None:
                    raise RuntimeError('illegal opcode %02X %02X at %04X' % (base, op, (cpu.pc - 2) & 0xFFFF))
                h()                             # entries carry the full page-2/3 count
            return f
        ops[0x10] = page(p2, 0x10)
        ops[0x11] = page(p3, 0x11)
        self.ops = ops
