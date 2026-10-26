"""arc_rand.py <state> <frames> "<script: python list of (from, to, mask)>": the arcade from a state, logging every
draw of the shared second random ($68F9, Fixed 31): frame, call site (the JSR), the slot in X and its type, and the
state before the draw; Arthur and the state every 100 frames. Arthur kept invincible ($AD). Pad bits as arc_walk.py
(1 right 2 left 4 down 8 up 10 fire 20 jump); ROUTE (route.py) instead of the script, PNG=<prefix>. Compare with port_rand.py (the port's draws per update)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'arcade'))
from gng import GnG
g = GnG(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'rom')); g.load(sys.argv[1]); m = g.mem
N = int(sys.argv[2]); ev = eval(sys.argv[3])
f = [0]


def hook(pc):
    if pc == 0x68F9:
        c = g.cpu; s = c.s; ret = m[s] << 8 | m[s + 1]
        x = c.x; slot = (x - 0x890) // 48 if 0x890 <= x < 0x890 + 48 * 40 and (x - 0x890) % 48 == 0 else -1
        print('f%d draw %04X slot%d type%d before %02X%02X ax%d' % (f[0], ret - 3, slot, m[x + 5] if slot >= 0 else -1,
                                                                 m[0x6E], m[0x6F], m[0x506] << 8 | m[0x507]))


g.cpu.hook = hook
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from route import Route
route = Route(os.environ['ROUTE']) if os.environ.get('ROUTE') else None
PNG = os.environ.get('PNG')
AMAP = {'R': 1, 'L': 2, 'D': 4, 'U': 8, 'F': 0x10, 'J': 0x20, 'RJ': 0x21, 'LJ': 0x22, '': 0}
for fr in range(1, N + 1):
    f[0] = fr; p = 0
    for a, b, k in ev:
        if a <= fr <= b: p |= k; break
    if route: p = AMAP[route.step(m[0x506] << 8 | m[0x507], m[0x509] << 8 | m[0x50A])]
    m[0xAD] = 60
    g.set_inputs(0, p, 0); g.run_frame()
    if fr % 100 == 0:
        print('f%d arthur x%d y%d cam%d,%d rand %02X%02X' % (fr, m[0x506] << 8 | m[0x507], m[0x509] << 8 | m[0x50A],
                                                         m[0x9C] << 8 | m[0x9D], m[0x9E] << 8 | m[0x9F], m[0x6E], m[0x6F]))
        if PNG: g.png('%s_%05d.png' % (PNG, fr))
