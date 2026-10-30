"""Walk Arthur (invincible, 1P) through a stage headless and save a frame every N frames, with the live enemy slots.

usage: stage_walk_caps.py <rom> <stage> <outdir> [frames] [every] [start_x]
start_x pokes Arthur's x ($FF9000 long, pixel << 8) once play starts."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'headless'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lockstep'))
from fbh import Game, F, U, RT, J
from bot import Bot

rom, stage, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
frames = int(sys.argv[4]) if len(sys.argv) > 4 else 6000
every = int(sys.argv[5]) if len(sys.argv) > 5 else 8
os.makedirs(out, exist_ok=True)
g = Game(rom, sysdir=out); g.want_video = True
inv = lambda g: g.w8(0xFFC309, 80)
g.launch(stage, 0, inv)
if len(sys.argv) > 6:
    v = int(sys.argv[6]) << 8
    for i in range(4): g.w8(0xFF9000 + i, v >> (24 - 8 * i))
bot = Bot([])
log = open(os.path.join(out, 'log.txt'), 'w')
M = {'R': RT, 'U': U, 'J': J, 'RJ': RT | J, '': 0}
for f in range(frames):
    x, y = g.r16(0xFF9001), g.r16(0xFF9004)
    m = M[bot.step(x, y)] | (F if f % 16 < 2 else 0)
    g.run(1, m, inv)
    if f % every == 0:
        g.png(os.path.join(out, 'f%05d.png' % f))
        sl = []
        for s in range(40):
            b = 0xFFB800 + 48 * s
            if g.r8(b + 4):
                sl.append('%d:t%d:x%d,y%d' % (s, g.r8(b + 10), g.r16(b + 17), g.r16(b + 21)))
        log.write('%d ax %d ay %d st %d %s\n' % (f, x, y, g.r8(0xFFC512), ' '.join(sl)))
