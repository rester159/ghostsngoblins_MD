"""port_walk.py <core> <rom> <frames> <out>: per-frame log of enemy slot events (TYPES=4,5 | all), Arthur
every 100 frames; LOAD state, POKE, BOTF (first bot frame, so a SCRIPT launch can run first), INV=1 (blink invincibility), BOT=1 with AJ (jump x list) / CL (climb x list),
DUMP_AT, PNGS=1. Port slots: $FFB800, 40 x 48 bytes."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lrbase
lrbase.setup(globals())
# port_walk: per-frame log of type-4/5 slot events (env TYPES, default 4,5); ARMOR/INV handled by POKE
pokes = []
for pk in os.environ.get('POKE', '').split(','):
    if pk.strip():
        f, a, v = pk.split(':'); pokes.append((int(f), int(a, 16), v))
types = None if os.environ.get('TYPES', '4,5') == 'all' else [int(t) for t in os.environ.get('TYPES', '4,5').split(',')]
dump_at = set(int(x) for x in os.environ.get('DUMP_AT', '').split())
prev = {}
from bot import Bot
bot = Bot([int(v) for v in os.environ.get('AJ','').split(',') if v], [int(v) for v in os.environ.get('CL','').split(',') if v]) if os.environ.get('BOT') else None
def w8(a, v):
    p = L.retro_get_memory_data(2); C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    for pf, pa, pv in pokes:
        if pf == f:
            n = (len(pv) + 1) // 2; v = int(pv, 16)
            for k in range(n): w8(pa + k, (v >> (8 * (n - 1 - k))) & 0xFF)
    botf = int(os.environ.get('BOTF', '0'))
    if os.environ.get('INV') and f >= botf: w8(0xFFC309, 60)
    if bot and f >= botf:
        r0 = ram(); SCRIPT[:] = [(f, f, {'R': 0x80, 'U': 0x10, 'J': 0x100, 'RJ': 0x180}[bot.step(rd(r0, 0xFF9001, 2), rd(r0, 0xFF9004, 2))])]
    L.retro_run()
    if f in dump_at:
        n = L.retro_serialize_size(); b = C.create_string_buffer(n); L.retro_serialize(b, n)
        open('%s_%05d.state' % (out, f), 'wb').write(b.raw); png('%s_%05d.png' % (out, f))
    r = ram(); ax = rd(r, 0xFF9001, 2); cam = rd(r, 0xFFA200, 2)
    if f % 100 == 0:
        print('f%d arthur x%d y%d cam%d dying%d' % (f, ax, rd(r, 0xFF9004, 2), cam, rd(r, 0xFFC571, 1)))
        if os.environ.get('PNGS'): png('%s_%05d.png' % (out, f))
    for i in range(40):
        a = 0xFFB800 + 48 * i; t = rd(r, a + 10, 1)
        cur = (t, rd(r, a + 7, 1)) if rd(r, a + 4, 1) and (types is None or t in types) else None
        if cur != prev.get(i):
            print('f%d ax%d cam%d slot%d %s -> %s x%d y%d ons%d var%d sub%d,%d life%d upd%d' % (f, ax, cam, i, prev.get(i), cur, rd(r, a + 17, 2), rd(r, a + 21, 2), rd(r, a + 5, 1), rd(r, a + 6, 1), rd(r, a + 8, 1), rd(r, a + 9, 1), rd(r, a + 42, 2), rd(r, 0xFF7084, 4)))
            prev[i] = cur
