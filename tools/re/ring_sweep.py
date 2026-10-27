"""ring_sweep.py: both games' terrain rings at the same cameras along a walk (Fixed 80).

  ring_sweep.py arc <arc state> <frames> <out.pkl>            the arcade (tools/arcade/gng.py)
  ring_sweep.py port <core> <rom> <frames> <out.pkl>         the port (LOAD=<port_start.py state>, lr.py harness)
  ring_sweep.py cmp <arc.pkl> <port.pkl> <port rom>           cells that differ, per camera both games reached

Both walk right, jumping right for 24 frames when Arthur's x has stood still for 10 (Arthur kept invincible), or
follow BOT=1 (tools/lockstep/bot.py, AJ=jump x list, CL=climb x list) or a ROUTE (route.py), and keep the ring (1,024 tiles + 1,024 attributes, the same cell layout in both games) the first frame
the camera is at each (x, y) with x and y multiples of STEP (default 16) after an update."""
import os, pickle, sys
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H + '/../lockstep'); sys.path.insert(0, H + '/../arcade')
from bot import Bot
from route import Route
STEP = int(os.environ.get('STEP', '16'))


class Walk:
    def __init__(self):
        self.lx = None; self.still = 0; self.j = 0

    def step(self, x, y):
        if self.j:
            self.j -= 1; return 'RJ'
        self.still = self.still + 1 if x == self.lx else 0
        self.lx = x
        if self.still >= 10:
            self.still = 0; self.j = 24; return 'RJ'
        return 'R'


def walker():
    if os.environ.get('ROUTE'):
        return Route(os.environ['ROUTE'])
    if not os.environ.get('BOT'):
        return Walk()
    return Bot([int(v) for v in os.environ.get('AJ', '').split(',') if v], [int(v) for v in os.environ.get('CL', '').split(',') if v])


mode = sys.argv[1]
if mode == 'arc':
    from gng import GnG
    g = GnG(H + '/../../rom'); g.load(sys.argv[2]); m = g.mem
    AMAP = {'R': 1, 'L': 2, 'D': 4, 'U': 8, 'F': 0x10, 'J': 0x20, 'RJ': 0x21, 'LJ': 0x22, '': 0}
    w = walker(); rings = {}
    for f in range(int(sys.argv[3])):
        k = w.step(m[0x506] << 8 | m[0x507], m[0x509] << 8 | m[0x50A]); m[0xAD] = 60
        g.set_inputs(0, AMAP[k], 0); g.run_frame()
        cx, cy = m[0x9C] << 8 | m[0x9D], m[0x9E] << 8 | m[0x9F]
        if cx % STEP == 0 and cy % STEP == 0 and (cx, cy) not in rings:
            rings[(cx, cy)] = bytes(m[0x2800:0x3000])
    pickle.dump(rings, open(sys.argv[4], 'wb')); print(len(rings), 'cameras')
elif mode == 'port':
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    import lrbase
    lrbase.setup(globals())
    PMAP = {'R': 0x80, 'L': 0x40, 'D': 0x20, 'U': 0x10, 'F': 1, 'J': 0x100, 'RJ': 0x180, 'LJ': 0x140, '': 0}
    w = walker(); rings = {}
    for f in range(1, int(frames) + 1):
        frame_no[0] = f
        r = ram()
        SCRIPT[:] = [(f, f, PMAP[w.step(rd(r, 0xFF9001, 2), rd(r, 0xFF9004, 2))])]
        lrbase.w8(globals(), 0xFFC309, 60)
        L.retro_run()
        r = ram(); cx, cy = rd(r, 0xFF9100, 2), rd(r, 0xFF9102, 2)
        if cx % STEP == 0 and cy % STEP == 0 and (cx, cy) not in rings:
            rings[(cx, cy)] = bytes(r[(k ^ 1)] for k in range(0x800))
    pickle.dump(rings, open(out, 'wb')); print(len(rings), 'cameras')
else:
    A = pickle.load(open(sys.argv[2], 'rb')); P = pickle.load(open(sys.argv[3], 'rb'))
    ROM = open(sys.argv[4], 'rb').read(); Ht = ROM[0x14A6E:0x14A6E + 256]
    fl = lambda t, a: (not (a & 0xC0) and Ht[t] != 0, Ht[t] if not (a & 0xC0) else 0)
    tot = tf = n = 0
    for key in sorted(set(A) & set(P)):
        a, p = A[key], P[key]
        d = [i for i in range(1024) if (a[i], a[1024 + i]) != (p[i], p[1024 + i])]
        df = [i for i in d if fl(a[i], a[1024 + i]) != fl(p[i], p[1024 + i])]
        n += 1; tot += len(d); tf += len(df)
        if d and os.environ.get('V'):
            print('camera %d,%d: %d cells differ, %d as a floor' % (key[0], key[1], len(d), len(df)))
    print('%d cameras in both: %d cell differences, %d as a floor' % (n, tot, tf))
