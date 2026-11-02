"""Can Vendetta's bosses be beaten without invincibility? A search with
rewinds (as save states would allow a player): random 8-frame moves, a move
kept when the boss has taken more hits, a rewind to the last kept state on a
death. Prints the hits over time and the frames played.

usage: boss_search.py <harness dir> <rom> <elf> satan|arthur <arena.state for arthur> [seed]"""
import sys, os, pickle, random, subprocess
sys.path.insert(0, sys.argv[1])
from fbh import Game, LT, RT, J, F, D, U
rom, elf, boss = sys.argv[2], sys.argv[3], sys.argv[4]
arena = sys.argv[5] if len(sys.argv) > 5 else None
random.seed(int(sys.argv[6]) if len(sys.argv) > 6 else 1)
sym = {}
for l in subprocess.check_output(['m68k-elf-nm', elf]).decode().split('\n'):
    p = l.split()
    if len(p) == 3: sym.setdefault(p[2], int(p[0], 16))
g = Game(rom, sysdir=os.path.dirname(os.path.abspath(rom)), options={'genesis_plus_gx_overclock': '200%'})
if boss == 'arthur':
    g.load(pickle.load(open(arena, 'rb')))
else:
    g.launch(6, 4)

def satan_slot():
    for k in range(40):
        a = 0xFFB800 + 48 * k
        if g.r8(a + 4) and g.r8(a + 10) == 6: return a
    return None

def hits():
    if boss == 'satan':
        if g.r8(sym['vd_satan_done']): return 99
        a = satan_slot()
        return 0 if a is None or g.r8(a + 7) == 0 else 10 - g.r8(a + 11)
    st = g.r8(sym['st'])
    if st >= 4: return 99
    if st == 0: return -1
    return (14 - g.r8(sym['hp'])) if g.r8(sym['armor']) else 14 + (14 - g.r8(sym['hp']))

MOVES = [0, LT, RT, J, LT | J, RT | J, D, 0]
def segment():
    m = random.choice(MOVES)
    for i in range(8):
        f = F if i < 3 and random.random() < 0.8 else 0
        g.run(1, m | f if not (m & J and i > 4 and random.random() < 0.5) else (m & ~J) | f)
        if g.r8(0xFFC342): return False
    return True

# get into the fight (Arthur: walk left until he comes)
if boss == 'arthur':
    while hits() < 0:
        g.run(1, LT | (J if g.frame % 40 < 20 else 0))
        if g.r8(0xFFC342): print('died before the fight'); sys.exit(1)
best = hits(); hist = [(g.save(), best)]; rewinds = 0; fails = 0; backs = 0
t0 = hist[0][0][1]
while best < 99 and rewinds < 60000:
    ok = segment()
    if not ok:
        rewinds += 1; fails += 1
        if fails > 50 * (backs + 1) and len(hist) > 1:
            hist.pop(); backs += 1; fails = 0      # a dead end: back up, further each time
        g.load(hist[-1][0])
        continue
    h = hits()
    if h > best:
        print('hits', h, 'frame', g.frame - t0, 'rewinds', rewinds, flush=True)
        best = h; hist.append((g.save(), h)); fails = 0; backs = 0
    elif fails > 20 and random.random() < 0.25:
        hist.append((g.save(), h)); fails = 0     # drift on, to get out of a stalemate
    if len(hist) > 400: del hist[1:100]
print('RESULT', boss, 'beaten' if best >= 99 else 'not beaten (%d hits)' % best, 'frames', g.frame - t0, 'rewinds', rewinds)
