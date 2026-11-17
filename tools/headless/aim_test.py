"""Home's ATTACK 4-WAY (src_patch/aim.c), headless: launch stage 1 (1 player)
from the developer menu with OPTIONS ATTACK = 4-WAY, then throw: Up + fire
standing, Down + fire in a jump, fire alone, and Down + fire crouched (a
normal low throw). ATTACK=0 runs the same plan with NORMAL.

usage: [ATTACK=0] [COOP=1] [KILL=1 [RAVEN=1]] aim_test.py <core> <rom> <out prefix>
Prints, per frame, Arthur's x/y and jump phase and each live weapon slot
(x, y, state, aim), and saves <out>_<frame>.png at the frames in PNGS."""
import os
import subprocess
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'lockstep'))
core, rom, out = sys.argv[1:4]
sys.argv = [sys.argv[0], core, rom, '4000', out]
COOP = os.environ.get('COOP') == '1'       # 2 players: Maximo (pad 2) plays the same plan, never aimed
dev = subprocess.check_output([sys.executable, os.path.join(HERE, '..', 'lockstep', 'devscript.py'), '1',
                               '1' if COOP else '0']).decode().strip()
J, F, UP, DN, RT = 0x100, 0x1, 0x10, 0x20, 0x80     # libretro: A = Genesis C (jump), B = fire
# the first range holding a frame wins (lr.py), so a press goes before its hold
PLAN = [(44, 47, UP | F), (40, 60, UP),               # up, standing
        (110, 113, J), (118, 121, DN | F), (114, 140, DN),   # down, in a jump
        (190, 193, F),                                # straight
        (250, 253, DN | F), (240, 270, DN),           # crouched: low and straight
        (300, 330, RT), (334, 337, UP | F), (330, 345, UP)]  # up after a walk
END = 400
PNGS = {48, 52, 60, 70, 122, 126, 132, 140, 196, 256, 340}
os.environ['SCRIPT'] = dev
import lrbase                                   # noqa: E402
lrbase.setup(globals())
ATTACK = int(os.environ.get('ATTACK', '1'))


def w(a, v, n):
    p = L.retro_get_memory_data(2)
    for k in range(n):
        C.c_uint8.from_address(p + ((a - 0xFF0000 + k) ^ 1)).value = (v >> (8 * (n - 1 - k))) & 0xFF


KILL = os.environ.get('KILL') == '1'
RAVEN = os.environ.get('RAVEN') == '1'     # KILL: walk straight to the ravens (x 816, 1104)
if KILL:
    END = 2500
    PNGS = {int(p) for p in os.environ.get('PNGS', '').split()}


def enemies(r):
    for i in range(40):
        a = 0xFFB800 + 48 * i
        if rd(r, a + 4, 1):
            yield i, rd(r, a + 10, 1), rd(r, a + 17, 2), rd(r, a + 21, 2), rd(r, a + 7, 1)


def kill_input(r, t):
    """Jump over the first zombie (type 11) and throw down, then walk right
    and throw up whenever a raven (type 17) is over Arthur."""
    ax, ay = (rd(r, 0xFF9000, 4) >> 8) & 0xFFFF, rd(r, 0xFF9004, 2)
    ph = rd(r, 0xFF9410, 2)
    if RAVEN and kill_input.jumped is None:
        kill_input.jumped = t - 81              # straight to the ravens
    if kill_input.jumped is None:
        for i, ty, x, y, st in enemies(r):
            if ty == 11 and st == 1 and 0 < x - ax < 22 and ph == 0:
                kill_input.jumped = t
                print('jump over zombie slot', i, 'at', x)
                return J
        return 0
    d = t - kill_input.jumped
    if d < 4:
        return J
    if d < 40:
        return DN | (F if 8 <= d < 12 else 0)
    if d < 80:
        return 0
    m = RT if t % 64 > 6 else J | RT
    if t % 128 > 90:
        m = 0                                   # stand and wait for a raven too
    for i, ty, x, y, st in enemies(r):
        if ty == 17 and abs(x - ax) < 24 and y > ay + 24 and t % 16 < 4:
            m = UP | F
    return m


kill_input.jumped = None
t0 = None
for f in range(1, 4001):
    frame_no[0] = f
    if f > 1300 and f % 20 == 0:
        w(0xFFC309, 80, 1)                      # no hits
    w(0xFF501D, ATTACK, 1)                      # PERSIST->home[HOP_ATTACK]
    if t0 is None and f > 1300 and rd(ram(), 0xFFC305, 1) == 1:
        t0 = f
        SCRIPT[:] = [(t0 + a, t0 + b, m) for a, b, m in PLAN]
        if COOP:
            SCRIPT2[:] = [(t0 + 6 + a, t0 + 6 + b, m) for a, b, m in PLAN]
    if KILL and t0 is not None:
        SCRIPT[:] = [(f, f, kill_input(ram(), f - t0))]
    L.retro_run()
    if t0 is not None:
        r = ram()
        sl = []
        for k in range(3):
            a = 0xFF9600 + 32 * k
            if rd(r, a + 8, 1):
                sl.append('[%d x%d y%d st%d.%d on%d aim%d]' % (k, (rd(r, a, 4) >> 8) & 0xFFFF, (rd(r, a + 4, 4) >> 8) & 0xFFFF,
                                                         rd(r, a + 12, 1), rd(r, a + 13, 1), rd(r, a + 9, 1), rd(r, 0xFF4602 + k, 1)))
        for i in range(64):
            e = [rd(r, 0xFFB500 + 8 * i + 2 * j, 2) for j in range(4)]
            if (e[2] & 0x7FB) in (0x2A0, 0x2B0, 0x790) or i == 0:
                sl.append('<sat%d y%d t%x x%d>' % (i, e[0] - 128, e[2], e[3] - 128))
        if KILL:
            sl.append('score %x' % rd(r, 0xFFC040, 4))
            sl += ['{%d t%d x%d y%d st%d}' % e for e in enemies(r) if e[1] in (11, 17) and abs(e[2] - ((rd(r, 0xFF9000, 4) >> 8) & 0xFFFF)) < 60]
        print(f - t0, 'x', (rd(r, 0xFF9000, 4) >> 8) & 0xFFFF, 'y', rd(r, 0xFF9004, 2), 'ph', rd(r, 0xFF9410, 2),
              'cam', rd(r, 0xFF9100, 2), rd(r, 0xFF9102, 2), ' '.join(sl))
        if f - t0 in PNGS:
            png('%s_%d.png' % (out, f - t0))
        if f - t0 == END:
            break
