"""port_score.py <core> <rom> <frames> <out>: from FROM (1400), each score change and enemy slot state change
(with the update counter)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lrbase
lrbase.setup(globals())
def w8(a, v):
    p = L.retro_get_memory_data(2); C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v
prev = {}; sc0 = None
FROM = int(os.environ.get('FROM', '1400'))
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    if f > FROM: w8(0xFFC309, 60)
    L.retro_run()
    if f < FROM: continue
    r = ram(); sc = rd(r, 0xFFC000, 4); u = rd(r, 0xFF7084, 4)
    if sc0 is not None and sc != sc0: print(f, 'upd', u, 'SCORE %08x' % sc)
    sc0 = sc
    for i in range(40):
        a = 0xFFB800 + 48 * i
        cur = (rd(r, a + 10, 1), rd(r, a + 7, 1)) if rd(r, a + 4, 1) else None
        if cur != prev.get(i):
            if prev.get(i) or cur and cur[1]: print(f, 'upd', u, 'slot%d %s->%s' % (i, prev.get(i), cur))
            prev[i] = cur
