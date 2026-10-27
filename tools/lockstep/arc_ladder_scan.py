"""arc_ladder_scan.py <state> <x lo> <x hi> [dir L/R]: for each target x, PRE (a route.py prefix) then walk to it, stand 10, hold up: where Arthur stood and his y and x after (port_ladder_scan.py: the same in the port)."""
import os, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, R + '/tools/arcade'); sys.path.insert(0, R + '/tools/lockstep')
from gng import GnG
from route import Route
D = sys.argv[4] if len(sys.argv) > 4 else 'L'
AMAP = {'R': 1, 'L': 2, 'D': 4, 'U': 8, 'F': 0x10, 'J': 0x20, 'RJ': 0x21, 'LJ': 0x22, '': 0}
for tx in range(int(sys.argv[2]), int(sys.argv[3]) + 1):
    g = GnG(R + '/rom'); g.load(sys.argv[1]); m = g.mem
    rt = Route(os.environ.get('PRE', '') + '%s%d,W10,U' % (D, tx)); sx = None
    X = lambda: m[0x506] << 8 | m[0x507]; Y = lambda: m[0x509] << 8 | m[0x50A]
    for fr in range(1200):
        k = rt.step(X(), Y()); m[0xAD] = 60
        if k == 'U' and sx is None: sx = '%d.%d' % (X(), m[0x508]); y0 = Y()
        g.set_inputs(0, AMAP[k], 0); g.run_frame()
        if sx is not None and rt.done(): break
    if sx is None: y0 = None
    print('target', tx, 'stood at', sx, 'y', y0, '->', Y(), 'x', X())
