"""Run one main-loop iteration of the GnG engine in Unicorn and attribute RAM
accesses to the top-level routine called from the loop."""
import sys, struct, collections
from unicorn import *
from unicorn.m68k_const import *
ROM = open(sys.argv[1], 'rb').read()
raw = open(sys.argv[2], 'rb').read()
RAM = bytes(raw[i ^ 1] for i in range(len(raw)))
START, STOP = int(sys.argv[3], 16), int(sys.argv[4], 16)
LOOP_LO, LOOP_HI = int(sys.argv[5], 16), int(sys.argv[6], 16)

uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
uc.mem_map(0, 0x400000, UC_PROT_ALL)
uc.mem_write(0, ROM)
uc.mem_map(0xFF0000, 0x10000)
uc.mem_write(0xFF0000, RAM)
uc.mem_map(0xA00000, 0x20000)          # Z80 RAM + I/O
uc.mem_map(0xC00000, 0x10000)          # VDP
uc.mem_write(0xA11100, b'\x00\x00')     # Z80 bus granted
uc.mem_write(0xA10003, b'\x7f')
uc.reg_write(UC_M68K_REG_SR, 0x2700)
uc.reg_write(UC_M68K_REG_A7, 0xFFFE00)
def on_bad(uc, kind, addr, size, value, _):
    print('unmapped %s %X size %d pc=%X a7=%X' % ('W' if kind in (UC_MEM_WRITE_UNMAPPED,) else 'R', addr, size, uc.reg_read(UC_M68K_REG_PC), uc.reg_read(UC_M68K_REG_A7)))
    return False
uc.hook_add(UC_HOOK_MEM_UNMAPPED, on_bad)

cur = ['loop']
access = collections.defaultdict(lambda: collections.defaultdict(set))
order = []
def on_code(uc, addr, size, _):
    if LOOP_LO <= addr < LOOP_HI:
        cur[0] = 'loop@%X' % addr
        insn = uc.mem_read(addr, 6)
        op = struct.unpack('>H', insn[:2])[0]
        if op == 0x4EB9:
            t = struct.unpack('>I', insn[2:6])[0]; cur[0] = 'jsr %X' % t
        elif op == 0x4EBA:
            t = addr + 2 + struct.unpack('>h', insn[2:4])[0]; cur[0] = 'jsr %X' % t
        if not order or order[-1] != cur[0]: order.append(cur[0])
    if addr == STOP:
        uc.emu_stop()
vb=[8]
th={}
def on_mem(uc, kind, addr, size, value, _):
    if 0xFF0000 <= addr <= 0xFFFFFF:
        access[cur[0]]['W' if kind == UC_MEM_WRITE else 'R'].update(range(addr, addr + size))
    elif 0xC00000 <= addr < 0xC00010 and kind == UC_MEM_READ:
        vb[0] ^= 8
        uc.mem_write(0xC00004, bytes([0x34, vb[0]]))   # status: FIFO empty, vblank toggles
    elif addr in (0xA10003, 0xA10005):
        if kind == UC_MEM_WRITE: th[addr] = value & 0x40
        else: uc.mem_write(addr, b'\x7f' if th.get(addr, 0x40) else b'\x33')
    elif 0xA11100 <= addr < 0xA11102 and kind == UC_MEM_READ:
        uc.mem_write(0xA11100, b'\x00\x00')     # Z80 bus always granted
uc.hook_add(UC_HOOK_CODE, on_code)
uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, on_mem)
count=[0]
last=[0]*12
def on_intr(uc, intno, _):
    print('EXCEPTION intno', intno, 'pc=%X' % uc.reg_read(UC_M68K_REG_PC), 'prev pcs', ['%X'%x for x in last])
    uc.emu_stop()
uc.hook_add(UC_HOOK_INTR, on_intr)
def on_any(uc,a,s,_):
    count[0]+=1
    if a==0xB56:
        print('ASSERT -> B56 from', ['%X'%x for x in last], 'code', uc.mem_read(0xFFC9DC,4).hex()); uc.emu_stop()
    last.pop(0); last.append(a)
uc.hook_add(UC_HOOK_CODE, on_any)
try:
    uc.emu_start(START, 0x400000, count=3_000_000)
except UcError as e:
    print('stopped:', e, 'pc=%X' % uc.reg_read(UC_M68K_REG_PC))
print('end pc=%X insns=%d' % (uc.reg_read(UC_M68K_REG_PC), count[0]))

def ranges(s):
    s = sorted(s); out = []; a = b = None
    for x in s:
        if a is None: a = b = x
        elif x == b + 1: b = x
        else: out.append((a, b)); a = b = x
    if a is not None: out.append((a, b))
    return ', '.join('%X' % a if a == b else '%X-%X' % (a, b) for a, b in out)
for name in dict.fromkeys(order):
    d = access.get(name)
    if not d: continue
    print('== %s\n  W: %s\n  R: %s' % (name, ranges(d['W'])[:600], ranges(d['R'])[:400]))
