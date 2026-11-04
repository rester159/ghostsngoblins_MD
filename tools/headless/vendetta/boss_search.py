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

def boss_xy():
    if boss == 'satan':
        a = satan_slot()
        return (g.r8(a + 17) << 8 | g.r8(a + 18), g.r8(a + 21) << 8 | g.r8(a + 22)) if a else (0, 0)
    sx = lambda v: v - (1 << 32) if v >= 1 << 31 else v
    return sx(g.r32(sym['ax'])) >> 8, sx(g.r32(sym['ay'])) >> 8

# moves, each 8 frames: plain ones, and ones aimed at the boss (turn to face
# him on the first frame, then fire)
KINDS = ['still', 'left', 'right', 'jump', 'jumpL', 'jumpR', 'face_fire', 'face_fire', 'hover_fire',
         'crouch_fire', 'away', 'away_jump', 'toward', 'flap']
def segment():
    kind = random.choice(KINDS)
    bx, by = boss_xy()
    fx, fy = g.r32(0xFF9000) >> 8 & 0xFFFF, g.r16(0xFF9004)
    tow = RT if bx > fx else LT
    away = LT if tow == RT else RT
    for i in range(8):
        m = {'still': 0, 'left': LT, 'right': RT, 'jump': J, 'jumpL': LT | J, 'jumpR': RT | J,
             'face_fire': tow if i == 0 else 0, 'hover_fire': J | (tow if i == 0 else 0),
             'crouch_fire': D | (tow if i == 0 else 0), 'away': away, 'away_jump': away | J,
             'toward': tow, 'flap': J if i in (0, 1, 4, 5) else 0}[kind]
        if kind in ('face_fire', 'hover_fire', 'crouch_fire'):
            m |= F if i in (1, 2, 5, 6) else 0
        elif i < 3 and random.random() < 0.6:
            m |= F
        g.run(1, m)
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
        if fails > 30 and len(hist) > 1:          # a dead end: back up 1, 2, 4 ... states
            del hist[max(1, len(hist) - (1 << backs)):]
            backs = min(backs + 1, 10); fails = 0
        g.load(hist[-1][0])
        continue
    h = hits()
    if h > best:
        print('hits', h, 'frame', g.frame - t0, 'rewinds', rewinds, flush=True)
        best = h; hist.append((g.save(), h)); fails = 0; backs = 0
    elif backs and random.random() < 0.05:
        hist.append((g.save(), h)); fails = 0; backs -= 1   # past the trouble: a little forward again
    elif not backs and fails > 20 and random.random() < 0.25:
        hist.append((g.save(), h)); fails = 0     # drift on, to get out of a stalemate
    if len(hist) > 400: del hist[1:100]
print('RESULT', boss, 'beaten' if best >= 99 else 'not beaten (%d hits)' % best, 'frames', g.frame - t0, 'rewinds', rewinds)
