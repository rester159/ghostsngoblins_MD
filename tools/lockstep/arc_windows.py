"""arc_windows.py <state> <frames>: stage 2, ROUTE walk; window devils (type 4 subtype 1): states and their window's
bg tile codes every frame they change. KILL=<n>: the n-th window devil to reach its closing (ST1 4 ST2 4) is
removed (live 0) on that frame. INV."""
import os, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, R + '/tools/arcade'); sys.path.insert(0, R + '/tools/lockstep')
from gng import GnG
from route import Route
g = GnG(R + '/rom'); g.load(sys.argv[1]); m = g.mem
route = Route(os.environ.get('ROUTE', 'R9000'))
AMAP = {'R': 1, 'L': 2, 'D': 4, 'U': 8, 'F': 0x10, 'J': 0x20, 'RJ': 0x21, 'LJ': 0x22, '': 0}
KILL = int(os.environ.get('KILL', '0')); nclose = 0
wins = {}      # (col,row) -> last codes
seen = {}
for fr in range(1, int(sys.argv[2]) + 1):
    k = route.step(m[0x506] << 8 | m[0x507], m[0x509] << 8 | m[0x50A]); m[0xAD] = 60
    g.set_inputs(0, AMAP[k], 0); g.run_frame()
    for i in range(40):
        X = 0x890 + 48 * i
        if not m[X - 0x10] and i in seen: del seen[i]
        if m[X - 0x10] and m[X + 5] == 4 and m[X - 0xE] == 1:
            x = m[X - 0xA] << 8 | m[X - 9]; y = m[X - 7] << 8 | m[X - 6]
            st = (m[X - 0xD], m[X - 0xC], m[X - 0xB])
            key = i
            if st[:2] == (1, 4) and st[2] >= 1 and key not in seen:
                seen[key] = 1; wins[((x >> 4) - 1, y >> 4)] = None; print('f%d devil slot %d opens at %d,%d' % (fr, i, x, y))
            if st == (1, 4, 4) and seen.get(key) == 1:
                seen[key] = 2; nclose += 1
                if nclose == KILL: m[X - 0x10] = 0; print('f%d removed slot %d (closing)' % (fr, i))
    for (c, r), last in list(wins.items()):
        codes = []
        for rr in (r + 1, r):
            for cc in (c, c + 1):
                codes.append(m[0x2800 + ((cc & 31) << 5 | ((rr ^ 15) & 31))])
        codes = tuple(codes)
        if codes != last:
            wins[(c, r)] = codes; print('f%d window %d,%d %s ax %d cam %d' % (fr, c, r, ' '.join('%02X' % v for v in codes), m[0x506] << 8 | m[0x507], m[0x9C] << 8 | m[0x9D]))
