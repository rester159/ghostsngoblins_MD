"""port_ladder_scan.py <core> <rom> <frames> <out>: SCRIPT dev launch, TX restart; at r40 save; then per target in XLO..XHI
(env, DIR L/R, PRE a route.py prefix) walk to it, W10, hold up: the port's ladder range. INV on."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lrbase
lrbase.setup(globals())
from route import Route


def w8(a, v):
    p = L.retro_get_memory_data(2); C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v


TX = int(os.environ['TX']); D = os.environ.get('DIR', 'L')
PMAP = {'R': 0x80, 'L': 0x40, 'D': 0x20, 'U': 0x10, 'F': 1, 'J': 0x100, 'RJ': 0x180, 'LJ': 0x140, '': 0}
r0 = None; snap = None
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    r = ram(); ax = rd(r, 0xFF9001, 2)
    if r0 is None and f > 1200 and rd(r, 0xFF7FF0, 4) == 0x4C495645 and ax == TX: r0 = f
    w8(0xFFC309, 60)
    L.retro_run()
    if r0 is not None and f - r0 == 40:
        n = L.retro_serialize_size(); snap = C.create_string_buffer(n); L.retro_serialize(snap, n); break
for tx in range(int(os.environ['XLO']), int(os.environ['XHI']) + 1):
    L.retro_unserialize(snap, len(snap.raw))
    rt = Route(os.environ.get('PRE', '') + '%s%d,W10,U' % (D, tx)); sx = None
    for k in range(1200):
        frame_no[0] += 1
        r = ram(); ax = rd(r, 0xFF9001, 2); ay = rd(r, 0xFF9004, 2)
        s = rt.step(ax, ay)
        if s == 'U' and sx is None: sx = '%d.%d' % (ax, rd(r, 0xFF9003, 1)); y0 = ay
        SCRIPT[:] = [(frame_no[0], frame_no[0], PMAP[s])]
        w8(0xFFC309, 60)
        L.retro_run()
        if sx is not None and rt.done(): break
    r = ram()
    if sx is None: y0 = None
    print('target', tx, 'stood at', sx, 'y', y0, '->', rd(r, 0xFF9004, 2), 'x', rd(r, 0xFF9001, 2))
