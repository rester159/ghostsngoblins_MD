"""port_rand.py <core> <rom> <frames> <out>: the port from a dev launch (SCRIPT) or LOAD state, logging every change of
the shared second random ($FFC62C, Fixed 31) with the number of draws it took (the state stepped as $68F9 does),
the update counter ($FF7084) and Arthur; Arthur and the state every 100 frames. Once Arthur is in play (the 'LIVE'
mark and x == TX if given) it follows ROUTE (route.py) and logs frames from there as r<n> (r1 = the first frame
after the restart was seen), so they line up with arc_rand.py runs from a state saved at the restart. INV=1 keeps
Arthur invincible; RPOKE="<r>:<addr>:<byte>,..." writes a byte on frame r (e.g. rng_lag, to line the frame counter
$FFA206 up with the arcade's <$21); XLOG=1 logs Arthur and the camera every frame from the restart."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lrbase
lrbase.setup(globals())
from route import Route


def w8(a, v):
    p = L.retro_get_memory_data(2); C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v


def step(s):
    b = ~((s >> 8) ^ s) & 0xFF
    return ((s << 1) & 0xFFFF) | ((b >> 6) & 1)


route = Route(os.environ.get('ROUTE', ''))
TX = int(os.environ['TX']) if os.environ.get('TX') else None
PMAP = {'R': 0x80, 'L': 0x40, 'D': 0x20, 'U': 0x10, 'F': 1, 'J': 0x100, 'RJ': 0x180, 'LJ': 0x140, '': 0}
RPOKE = [(int(a), int(b, 16), int(c, 16)) for a, b, c in (x.split(':') for x in os.environ.get('RPOKE', '').split(',') if x)]
r0 = None; prev = None
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    r = ram(); ax = rd(r, 0xFF9001, 2); ay = rd(r, 0xFF9004, 2)
    if r0 is None and f > 1200 and rd(r, 0xFF7FF0, 4) == 0x4C495645 and (TX is None or ax == TX):
        r0 = f; print('restart seen at frame', f, 'x', ax, 'y', ay, 'c21 %02X' % rd(r, 0xFFA206, 1))
    if r0 is not None:
        for rf, ra, rv in RPOKE:
            if f - r0 == rf: w8(ra, rv)
        SCRIPT[:] = [(f, f, PMAP[route.step(ax, ay)])]
    if os.environ.get('INV'): w8(0xFFC309, 60)
    L.retro_run()
    r = ram(); s = rd(r, 0xFFC62C, 2); tag = 'r%d' % (f - r0) if r0 is not None else 'f%d' % f
    if prev is not None and s != prev:
        n, t = 0, prev
        while t != s and n < 200: t = step(t); n += 1
        print('%s draws %s before %04X after %04X upd%d c21 %02X ax%d' % (tag, n if n < 200 else '?', prev, s, rd(r, 0xFF7084, 4), rd(r, 0xFFA206, 1), rd(r, 0xFF9001, 2)))
    prev = s
    if os.environ.get('XLOG') and r0 is not None:
        print('%s x %d.%d y %d cam %d,%d c21 %02X' % (tag, rd(r, 0xFF9001, 2), rd(r, 0xFF9003, 1), rd(r, 0xFF9004, 2), rd(r, 0xFFA200, 2), rd(r, 0xFFA202, 2), rd(r, 0xFFA206, 1)))
    if f % 100 == 0:
        print('%s arthur x%d y%d cam%d,%d rand %04X upd%d' % (tag, rd(r, 0xFF9001, 2), rd(r, 0xFF9004, 2), rd(r, 0xFFA200, 2), rd(r, 0xFFA202, 2), s, rd(r, 0xFF7084, 4)))
