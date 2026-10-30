"""Is every live, on-screen enemy drawn? Walk Arthur (invincible, 1P) and, each frame, match each enemy slot with its
on-screen flag to the sprite table entries near it (non-blank tiles, gpgx state). Prints the misses.

usage: stage_vis.py <rom> <stage> <frames> [png dir]
Screen: sx = x - cam x, sy = 224 - (y - cam y) (y up). Dying frames ($FFC570) are skipped."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'headless'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lockstep'))
from fbh import Game, F, U, RT, J
from bot import Bot
import vdp

rom, stage, frames = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
pdir = sys.argv[4] if len(sys.argv) > 4 else None
g = Game(rom, sysdir='/tmp' if not pdir else pdir)
g.want_video = bool(pdir)
if pdir: os.makedirs(pdir, exist_ok=True)
inv = lambda g: g.w8(0xFFC309, 80)
g.launch(stage, 0, inv)
bot = Bot([], [int(c) for c in os.environ.get('CL', '').split(',') if c])
M = {'R': RT, 'U': U, 'J': J, 'RJ': RT | J, '': 0}
seen, miss = {}, {}


def sat(raw):
    vram = bytes(raw[vdp.BASE + (i ^ 1)] for i in range(0x10000))
    regs = raw[vdp.BASE + 0x10100:vdp.BASE + 0x10120]
    base = (regs[5] & 0x7F) << 9
    i, out = 0, []
    for _ in range(80):
        e = vram[base + i * 8:base + i * 8 + 8]
        a = e[4] << 8 | e[5]
        w, h = (e[2] >> 2 & 3) + 1, (e[2] & 3) + 1
        t = (a & 0x7FF) * 32
        if any(vram[t:t + w * h * 32]):
            out.append((((e[6] << 8 | e[7]) & 0x1FF) - 128, ((e[0] << 8 | e[1]) & 0x3FF) - 128, w * 8, h * 8, a & 0x7FF))
        i = e[3] & 0x7F
        if not i:
            break
    return out


for f in range(frames):
    x, y = g.r16(0xFF9001), g.r16(0xFF9004)
    g.run(1, M[bot.step(x, y)] | (F if f % 16 < 2 else 0), inv)
    if g.r8(0xFFC570) or g.r8(0xFFC571) or g.r8(0xFFC305) != 1:
        continue
    cx, cy = g.r16(0xFFA200), g.r16(0xFFA202)
    sl = [(s, g.r8(0xFFB800 + 48 * s + 10), g.r16(0xFFB800 + 48 * s + 17), g.r16(0xFFB800 + 48 * s + 21))
          for s in range(40) if g.r8(0xFFB800 + 48 * s + 4) and g.r8(0xFFB800 + 48 * s + 5)]
    if not sl:
        continue
    spr = sat(g.save()[0])
    for s, t, ex, ey in sl:
        sx, sy = ex - cx, 224 - (ey - cy)
        if not (-16 < sx < 272 and -16 < sy < 240):
            continue
        k = (t, s)
        seen[k] = seen.get(k, 0) + 1
        if not any(px - 24 <= sx <= px + pw + 24 and py - 24 <= sy <= py + ph + 24 for px, py, pw, ph, _ in spr):
            miss.setdefault(k, []).append((f, ex, ey, sx, sy))
            if pdir and len(miss[k]) % 20 == 1:
                g.png(os.path.join(pdir, 'miss_t%d_s%d_f%05d.png' % (t, s, f)))
for k in sorted(seen):
    m = miss.get(k, [])
    mid = [e for e in m if 16 <= e[3] <= 240 and 16 <= e[4] <= 208]
    print('type %2d slot %2d: on screen %4d, not drawn %4d (mid-screen %4d) %s' % (k[0], k[1], seen[k], len(m), len(mid), mid[:4]))
