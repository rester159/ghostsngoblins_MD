"""Firebrand's wall cling, headless: launch stage 5 in Firebrand mode from the
developer menu, put him on the middle floor next to the rock pillar (its right
side is a wall cell column, tiles $82-$85, wall edge x 6718), then jump into
it, hold, fire, leap up and re-grab, push away and fall, then hover into it
and grab it from the hover.

usage: [SIDE=right] fb_wall_test.py <core> <rom> <out prefix>
Waits until he is controllable ($FFC305 = 1, invincible throughout), then
runs PLAN (frames from that moment). Prints one line per frame (x, y, jump
phase, cling side, facing, shots out) and saves <out>_<frame>.png at the
frames in PNGS (with a save state, <out>_<frame>.state)."""
import os
import subprocess
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'lockstep'))
core, rom, out = sys.argv[1:4]
sys.argv = [sys.argv[0], core, rom, '4000', out]
dev = subprocess.check_output([sys.executable, os.path.join(HERE, '..', 'lockstep', 'devscript.py'), '5', '2']).decode().strip()
J, F, LT, RT = 0x100, 0x1, 0x40, 0x80          # libretro: A = Genesis C (jump), B = fire
PLAN = [(70, 89, LT), (90, 93, J | LT), (94, 149, LT),
        (190, 193, F), (230, 233, J | LT), (234, 309, LT),
        (330, 335, RT),
        # back on the floor, a step out: jump, hover (jump held) and steer into the pillar
        (360, 365, RT), (380, 383, J), (384, 405, J), (406, 440, J | LT)]
END = 470
START = (6740, 655)
if os.environ.get('SIDE') == 'right':           # the wall on his right: the next rock face up, edge x ~6740
    START = (6712, 740)
    PLAN = [(60, 100, RT), (110, 113, J | RT), (114, 160, RT), (190, 193, F), (230, 233, J | RT), (234, 309, RT), (330, 335, LT)]
    END = 380
os.environ['SCRIPT'] = dev
import lrbase                                   # noqa: E402
lrbase.setup(globals())
SYM = {l.split()[2]: int(l.split()[0], 16) for l in
       open(os.path.join(HERE, '..', '..', 'src_patch', 'build', 'patch.sym')) if len(l.split()) == 3}
PNGS = {60, 130, 191, 193, 220, 290, 360, 400}


def w(a, v, n):
    p = L.retro_get_memory_data(2)
    for k in range(n):
        C.c_uint8.from_address(p + ((a - 0xFF0000 + k) ^ 1)).value = (v >> (8 * (n - 1 - k))) & 0xFF


t0 = None
for f in range(1, 4001):
    frame_no[0] = f
    if f > 1300 and f % 20 == 0:
        w(0xFFC309, 80, 1)                      # no hits
    if t0 is None and f > 1300 and rd(ram(), 0xFFC305, 1) == 1:
        t0 = f
        SCRIPT[:] = [(t0 + a, t0 + b, m) for a, b, m in PLAN]
    if t0 is not None and f == t0 + 36:         # after the stage start has placed him and he has landed
        w(0xFF9000, START[0] << 8, 4)
        w(0xFF9400, START[1] << 8, 4)          # y (16.8; $FF9004 is its copy)
        w(0xFF9004, START[1], 2)
    L.retro_run()
    if t0 is not None:
        r = ram()
        print(f - t0, 'x %.2f' % ((rd(r, 0xFF9000, 4) & 0xFFFFFF) / 256), 'y', rd(r, 0xFF9004, 2),
              'ph', rd(r, 0xFF9410, 2), 'cling', rd(r, SYM['cling'], 1), 'wj', rd(r, SYM['wall_jump'], 1),
              'face', rd(r, 0xFF920A, 2), 'shots', sum(rd(r, 0xFF9608 + 32 * k, 1) != 0 for k in range(3)),
              'pose', hex(rd(r, 0xFFC380, 4)))
        if f - t0 in PNGS:
            png('%s_%d.png' % (out, f - t0))
            n = L.retro_serialize_size(); b = C.create_string_buffer(n); L.retro_serialize(b, n)
            open('%s_%d.state' % (out, f - t0), 'wb').write(b.raw)
        if f - t0 == END:
            break
