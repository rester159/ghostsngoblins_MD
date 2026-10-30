"""Tiles a stage never uses: VRAM never non-zero and never referenced by the planes (A, B; the window when it is on) or the sprite table,
sampled every N frames of a walk (Arthur invincible), for one mode. Prints the free runs of 16+ tiles.

usage: vram_free.py <rom> <stage> <players 0 1P / 1 co-op / 2 Firebrand> <frames> [every] [pickle out]"""
import os, pickle, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'headless'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lockstep'))
from fbh import Game, F, U, RT, J
from bot import Bot
import vdp

rom, stage, players, frames = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
every = int(sys.argv[5]) if len(sys.argv) > 5 else 10
g = Game(rom, sysdir='/tmp')
inv = lambda g: (g.w8(0xFFC309, 80), g.w8(0xFFC500, 5))
g.launch(stage, players, inv)
bot = Bot([])
M = {'R': RT, 'U': U, 'J': J, 'RJ': RT | J, '': 0}
used = set()
for f in range(frames):
    x, y = g.r16(0xFF9001), g.r16(0xFF9004)
    g.run(1, M[bot.step(x, y)] | (F if f % 16 < 2 else 0), inv)
    if f % every:
        continue
    raw = g.save()[0]
    v = bytes(raw[vdp.BASE + (i ^ 1)] for i in range(0x10000))
    r = raw[vdp.BASE + 0x10100:vdp.BASE + 0x10120]
    for t in range(0x800):
        if any(v[t * 32:t * 32 + 32]): used.add(t)
    win = r[17] & 0x1F or r[18] & 0x1F          # the window is on: its table and map count
    for base, n in (((r[2] & 0x38) << 10, 64 * 32), ((r[4] & 7) << 13, 64 * 32)) + ((((r[3] & 0x3E) << 10, 32 * 32),) if win else ()):
        for k in range(n):
            used.add((v[base + 2 * k] << 8 | v[base + 2 * k + 1]) & 0x7FF)
    sat = (r[5] & 0x7F) << 9
    for k in range(80):
        e = v[sat + 8 * k:sat + 8 * k + 8]
        nt = ((e[2] >> 2 & 3) + 1) * ((e[2] & 3) + 1)
        a = (e[4] << 8 | e[5]) & 0x7FF
        used.update(range(a, a + nt))
    # the tables themselves
    for base, size in (((r[2] & 0x38) << 10, 0x1000), ((r[4] & 7) << 13, 0x1000), (sat, 0x280), ((r[13] & 0x3F) << 10, 0x400)) + ((((r[3] & 0x3E) << 10, 0x800),) if win else ()):
        used.update(range(base // 32, (base + size + 31) // 32))
if len(sys.argv) > 6:
    pickle.dump(used, open(sys.argv[6], 'wb'))
run = []
for t in range(0x801):
    if t < 0x800 and t not in used: run.append(t); continue
    if len(run) >= 16: print('free $%03X-$%03X (%d tiles)' % (run[0], run[-1], len(run)))
    run = []
