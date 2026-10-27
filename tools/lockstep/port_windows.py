"""port_windows.py <core> <rom> <frames> <out>: stage 2 life start (TX), ROUTE, INV; the window devils (type 4 subtype 1):
when one opens (+7 +8 = 1 4, +9 >= 1) its window's plane B cells (4 x 4) are followed; on each change prints the
cells' look (a label per distinct set of tile pixels, first seen first) and whether they point at the slot tiles.
KILL=n removes the n-th window devil to reach its closing (+9 = 4) on that frame (+4 = 0), KILL=-1 every one; KDELAY=d
removes it d frames into its closing instead. With LOAD (a port_start.py
state, e.g. TX=4736 TC=4608 on a restart_entry.py copy whose stage 2 entry is 00128050) frames count from the state,
in phase with arc_windows.py on an arc_start.py 1 1 state."""
import os, sys
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, W + '/tools/lockstep'); sys.path.insert(0, W + '/tools/headless')
import lrbase
lrbase.setup(globals())
from route import Route
import vdp


def w8(a, v):
    p = L.retro_get_memory_data(2); C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v


TX = int(os.environ.get('TX', '4736')); KILL = int(os.environ.get('KILL', '0')); KD = int(os.environ.get('KDELAY', '0')); kat = {}
route = Route(os.environ.get('ROUTE', 'R9000'))
PMAP = {'R': 0x80, 'L': 0x40, 'D': 0x20, 'U': 0x10, 'F': 1, 'J': 0x100, 'RJ': 0x180, 'LJ': 0x140, '': 0}
r0 = 0 if os.environ.get('LOAD') else None; seen = {}; wins = {}; looks = {}; nclose = 0
SLOT = set(range(0x6AC, 0x6C8)) | set(range(0x5F4, 0x5FC)) | set(range(0x6D0, 0x6DC))   # the poses' tiles (Fixed 79)
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    r = ram(); ax = rd(r, 0xFF9001, 2); ay = rd(r, 0xFF9004, 2)
    if r0 is None and f > 1200 and rd(r, 0xFF7FF0, 4) == 0x4C495645 and ax == TX: r0 = f; print('restart at', f)
    if r0 is not None:
        SCRIPT[:] = [(f, f, PMAP[route.step(ax, ay)])]
    w8(0xFFC309, 60)
    L.retro_run()
    if r0 is None: continue
    r = ram(); t = f - r0
    for i in range(40):
        s = 0xFFB800 + 48 * i
        if not rd(r, s + 4, 1):
            seen.pop(i, None); continue
        if rd(r, s + 10, 1) != 4 or rd(r, s + 6, 1) != 1: continue
        st = (rd(r, s + 7, 1), rd(r, s + 8, 1), rd(r, s + 9, 1))
        if st[:2] == (1, 4) and st[2] >= 1 and i not in seen:
            x = rd(r, s + 17, 2); y = rd(r, s + 21, 2)
            seen[i] = 1; key = ((((x >> 4) - 1) * 2) & 63, (30 - 2 * (y >> 4)) & 31)
            wins[key] = None; print('r%d devil slot %d opens at %d,%d window %s' % (t, i, x, y, key))
        if st == (1, 4, 4) and seen.get(i) == 1:
            seen[i] = 2; nclose += 1
            if nclose == KILL or KILL < 0: kat[i] = t + KD
        if kat.get(i) == t: w8(s + 4, 0); del kat[i]; print('r%d removed slot %d (closing + %d)' % (t, i, KD))
    if not wins: continue
    n = L.retro_serialize_size(); b = C.create_string_buffer(n); L.retro_serialize(b, n)
    st = b.raw; vram = bytes(st[vdp.BASE + (k ^ 1)] for k in range(0x10000))
    for (c, rw), last in list(wins.items()):
        cells = []; pix = b''
        for rr in range(4):
            for cc in range(4):
                a = 0xC000 + ((rw + rr) & 31) * 128 + ((c + cc) & 63) * 2
                w = vram[a] << 8 | vram[a + 1]; cells.append(w)
                tl = w & 0x7FF; pix += vram[tl * 32:tl * 32 + 32] + bytes([w >> 11 & 3])
        lk = looks.setdefault(pix, 'L%d' % len(looks))
        inslot = sum(1 for w in cells if (w & 0x7FF) in SLOT)
        cur = (lk, inslot)
        if cur != last:
            wins[(c, rw)] = cur
            print('r%d window %s look %s slot-cells %d cam %d' % (t, (c, rw), lk, inslot, rd(r, 0xFFA200, 2)))
