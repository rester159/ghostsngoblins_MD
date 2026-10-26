"""dual_updates.py <arc state> <port state> <port rom> <updates> "<plan>": each game run on its own with the same
x-triggered plan, Arthur logged once per game update (port: when $FF7084 steps; arcade: every frame), then
compared update by update. plan: "keys" default, then ";x>=N:keys:n" / ";x<=N:keys:n" / ";u=N:keys:n" entries
(each fires once, for n updates). keys from R L U D J F ('-' none). FRAC0=1 zeroes the fractions first.
OBJ=k,... also logs platform objects. Prints only differing updates (ALL=1: every update)."""
import os, sys
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, T + '/tools/arcade'); sys.path.insert(0, T + '/tools/lockstep')
from gng import GnG
arcst, portst, rom, N, plan = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
parts = plan.split(';'); default = parts[0]
ents = []
for p in parts[1:]:
    c, k, n = p.split(':'); ents.append([c, k, int(n)])
AK = dict(R=1, L=2, D=4, U=8, F=0x10, J=0x20); PK = dict(R=0x80, L=0x40, D=0x20, U=0x10, F=1, J=0x100)
OB = [int(v) for v in os.environ.get('OBJ', '').split(',') if v]
class Planner:
    def __init__(self): self.e = [list(x) + [0] for x in ents]; self.cur = None; self.left = 0
    def keys(self, u, x):
        for e in self.e:                 # u= entries take over at their update
            if not e[3] and e[0].startswith('u=') and u >= int(e[0][2:]):
                e[3] = 1; self.cur = e[1]; self.left = e[2] - 1; return e[1]
        if self.left:
            self.left -= 1; return self.cur
        for e in self.e:
            c, k, n, done = e
            if done: continue
            hit = (c.startswith('x>=') and x >= int(c[3:])) or (c.startswith('x<=') and x <= int(c[3:])) or \
                  (c.startswith('u=') and u >= int(c[2:]))
            if hit:
                e[3] = 1; self.cur = k; self.left = n - 1; return k
        return default
def tomask(k, tab):
    return sum(tab[c] for c in k if c in tab)
# arcade
g = GnG(T + '/rom'); g.load(arcst); m = g.mem
if os.environ.get('FRAC0'): m[0x508] = 0; m[0x50B] = 0
pl = Planner(); A = []
for u in range(N):
    x = m[0x506] << 8 | m[0x507]
    k = pl.keys(u, x)
    m[0xAD] = 60
    g.set_inputs(0, tomask(k, AK), 0); g.run_frame()
    ob = tuple((m[0x1010+32*j-0xA] << 8 | m[0x1010+32*j-9], m[0x1010+32*j-7] << 8 | m[0x1010+32*j-6]) for j in OB)
    if os.environ.get('ASAVE') and u == int(os.environ['ASAVE']):
        g.save('asave_%d.state' % u); sys.exit(0)
    if os.environ.get('AX'):
        a0, a1 = [int(v, 16) for v in os.environ['AX'].split('-')]
        ob = ob + (bytes(m[a0:a1]).hex(),)
    A.append((m[0x506] << 16 | m[0x507] << 8 | m[0x508], m[0x509] << 16 | m[0x50A] << 8 | m[0x50B], k, ob))
# port
sys.argv = ['x', os.path.expanduser('~/Library/Application Support/RetroArch/cores/genesis_plus_gx_libretro.dylib'), rom, str(N), '/tmp/x']
os.environ['LOAD'] = portst
import lrbase
G = {}
lrbase.setup(G)
L, Cc, ram, rd, frame_no = G['L'], G['C'], G['ram'], G['rd'], G['frame_no']
def pw(a, v, n):
    p = L.retro_get_memory_data(2)
    for kk in range(n):
        Cc.c_uint8.from_address(p + ((a - 0xFF0000 + kk) ^ 1)).value = (v >> (8 * (n - 1 - kk))) & 0xFF
if os.environ.get('FRAC0'): pw(0xFF9003, 0, 1); pw(0xFF9403, 0, 1)
pl = Planner(); P = []; r = ram(); u0 = rd(r, 0xFF7084, 4); f = 0
k = pl.keys(0, rd(r, 0xFF9001, 2)); prevu = 0; last = None
while len(P) < N and f < 4 * N:
    f += 1; frame_no[0] = f
    G['SCRIPT'][:] = [(f, f, tomask(k, PK))]
    pw(0xFFC309, 60, 1)
    L.retro_run(); r = ram()
    u = rd(r, 0xFF7084, 4) - u0
    # the counter steps at an update's start: the reading of the frame before is the previous update's end
    if u > prevu and last is not None:
        P.append(last)
        if os.environ.get('DUMPU') and len(P) == int(os.environ['DUMPU']):
            open('dump_u%d.ram' % len(P), 'wb').write(lastr)
    stepped = u > prevu
    prevu = u
    ob = tuple((rd(r, 0xFFE000 + 48 * j, 2), rd(r, 0xFFE002 + 48 * j, 2)) for j in OB)
    if os.environ.get('PX'):
        ob = ob + tuple('%X' % rd(r, int(a, 16), 2) for a in os.environ['PX'].split(','))
    last = (rd(r, 0xFF9000, 4) & 0xFFFFFF, rd(r, 0xFF9400, 4) & 0xFFFFFF, k, ob); lastr = r
    if stepped:                 # the next update's keys from this update's result, as in the arcade
        k = pl.keys(u, last[0] >> 16 if False else (last[0] >> 8))
nd = 0
for i in range(min(len(A), len(P))):
    a, p = A[i], P[i]
    same = a[:2] == p[:2]
    nd += not same
    if os.environ.get('ALL') or not same:
        print('%4d %-3s arc %5d.%02X %4d.%02X | port %5d.%02X %4d.%02X %-3s %s %s' % (i, a[2], a[0] >> 8, a[0] & 255, a[1] >> 8, a[1] & 255,
              p[0] >> 8, p[0] & 255, p[1] >> 8, p[1] & 255, p[2], '' if same else 'dx%+d dy%+d' % ((p[0] >> 8) - (a[0] >> 8), (p[1] >> 8) - (a[1] >> 8)),
              ' '.join('%s/%s' % (oa, op) for oa, op in zip(a[3], p[3])) + (' A:' + a[3][-1] if os.environ.get('AX') else '') + (' ' + ' '.join(p[3][len(a[3]):]) if os.environ.get('PX') else '')))
print('updates %d, differing %d' % (min(len(A), len(P)), nd))
