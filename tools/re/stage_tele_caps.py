"""Teleport Arthur (invincible, 1P) along a stage and save frames at each stop, with the live enemy slots.

usage: stage_tele_caps.py <rom> <stage> <outdir> <x0> <x1> <step> [hold frames] [every]
Each stop pokes Arthur's x ($FF9000 long = pixel << 8), lets him land, then stands firing for hold frames."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'headless'))
from fbh import Game, F

rom, stage, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
x0, x1, step = int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6])
hold = int(sys.argv[7]) if len(sys.argv) > 7 else 120
every = int(sys.argv[8]) if len(sys.argv) > 8 else 10
os.makedirs(out, exist_ok=True)
g = Game(rom, sysdir=out); g.want_video = True
inv = lambda g: g.w8(0xFFC309, 80)
g.launch(stage, 0, inv)
log = open(os.path.join(out, 'log.txt'), 'w')
n = 0
for tx in range(x0, x1, step):
    v = tx << 8
    for i in range(4): g.w8(0xFF9000 + i, v >> (24 - 8 * i))
    for f in range(hold):
        g.run(1, F if f % 16 < 2 else 0, inv)
        if f % every == every - 1:
            g.png(os.path.join(out, 'c%05d.png' % n))
            sl = []
            for s in range(40):
                b = 0xFFB800 + 48 * s
                if g.r8(b + 4):
                    sl.append('%d:t%d:x%d,y%d' % (s, g.r8(b + 10), g.r16(b + 17), g.r16(b + 21)))
            log.write('c%05d tx %d ax %d ay %d cam %d,%d st %d die %d %s\n' % (n, tx, g.r16(0xFF9001), g.r16(0xFF9004),
                      g.r16(0xFFA200), g.r16(0xFFA202), g.r8(0xFFC512), g.r8(0xFFC570), ' '.join(sl)))
            n += 1
