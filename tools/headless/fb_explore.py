"""Firebrand's climbing stages (5, 6) explored headless, Go-Explore style (no
invincibility, no pokes): an archive keeps, for each 24 x 24 px cell he has
stood, climbed or hovered in, the shortest path there and its save state.
Each round picks a cell (the less tried, the higher and the more stage time
left there, the likelier), loads
it and plays random moves (fb_campaign's macro) until he dies or wanders
long enough; every new cell, or a known one reached sooner, goes into the
archive. fb_campaign's single best-progress search falls back down the
towers; this one keeps every floor it has reached to start from.

BOSS=1 keys the cells by the boss's damage, its death and the key too, ranks
them by height plus that progress, and runs until the stage is cleared.

usage: [SEED_MOVES=<file>] [BOSS=1] fb_explore.py <rom> <stage 5|6> <out prefix> [rounds] [stop y]
SEED_MOVES puts every cell along a known path into the archive first. P=0 plays Arthur (1P) instead.
STATS=<file> keeps each enemy type's steps per update (by 200 px band of his y) from all the play, written
every 2,000 rounds (comparing builds' enemy speeds where the paths differ).
Writes <out>.moves (the path to the highest cell, one input mask per frame
from the launch) whenever the top rises, and stops once he is at stop y
(world y, up; default: the boss floor, 1700 for stage 5, 2700 for stage 6)
or the stage is cleared. Then `RESUME=1 fb_campaign.py <rom> <stage> <out>`
replays that path straight from the launch (repairing it where a load
drifted) and plays on through the boss and the key, with the clear's
straight-replay proof."""
import os
import random
import sys
import time
import zlib
from array import array

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbh import Game, F, U, D, LT, RT, J     # noqa: E402

rom, stage, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 200000
stop_y = int(sys.argv[5]) if len(sys.argv) > 5 else {5: 1700, 6: 2700}[stage]
K = 8
random.seed(int(os.environ.get('SEED', '1')))
g = Game(rom, sysdir=os.path.dirname(os.path.abspath(out)),
         options={'genesis_plus_gx_overclock': os.environ.get('OC', '200%')})
g.launch(stage, int(os.environ.get('P', '2')))     # P=0: Arthur, 1P
g.want_video = False
stage0, idx0 = g.r8(0xFFF400), g.r8(0xFFC512)


def dead():
    return g.r8(0xFFC342) or g.r16(0xFFC570) == 1


def cleared():
    return g.r8(0xFFC512) != idx0 or g.r8(0xFFF400) != stage0


LADDER = range(0x74, 0x7A)


def ladder_dir():
    """towards the nearest ladder cell beside or under him, up on it (as fb_campaign)"""
    fx, fy = g.r16(0xFF9001), g.r16(0xFF9004)
    best = None
    for dy in (8, 24, 40, 56):
        y = fy + dy
        for dx in range(-384, 385, 16):
            x = fx + dx
            i = (x & 0x1F0) * 2 | (((y >> 4) ^ 15) & 31)
            if g.r8(0xFF0000 + i) in LADDER:
                cx = (x & ~15) + 8
                if best is None or abs(cx - fx) < abs(best - fx):
                    best = cx
    if best is None:
        return None
    return U if abs(best - fx) <= 6 else RT if best > fx else LT


def macro(last):
    if random.random() < 0.6:
        d, j = last
        j = 'hold' if j == 'press' else j
    else:
        d = random.choices([RT, 0, LT, U, D, 'lad'], [30, 10, 30, 14, 6, 20])[0]
        j = random.choices(['off', 'hold', 'press'], [45, 35, 20])[0]
    last[:] = [d, j]
    if d == 'lad':
        d = ladder_dir()
        if d is None:
            d = random.choice([RT, LT])
        else:
            j = 'off'
    fire = random.random() < 0.5
    ms = []
    for k in range(K):
        m = d
        if j == 'hold' or (j == 'press' and k > 0):
            m |= J
        if fire and k < 2:
            m |= F
        ms.append(m)
    return ms


BOSS = bool(os.environ.get('BOSS'))     # also the fight: the boss's damage, its death, the key


def boss_dmg():
    """hit points the boss enemies (type 6: stage 6's Satans, 10 each) have lost, 20 once dead"""
    if g.r8(0xFFC8D6) == 2:
        return 20
    hp = [g.r8(0xFFB800 + 48 * k + 11) for k in range(40)
          if g.r8(0xFFB800 + 48 * k + 4) and g.r8(0xFFB800 + 48 * k + 10) == 6]
    return 20 - sum(hp) if hp else 0


def progress():
    p = g.r16(0xFF9004)
    if BOSS:
        p += 60 * boss_dmg() + 1500 * (g.r8(0xFFC8D6) == 2) + 3000 * (g.r16(0xFFCD7A) != 0)
    return p


def key():
    k = (g.r16(0xFF9001) // 24, g.r16(0xFF9004) // 24, bool(g.r8(0xFF9459)))
    if BOSS:
        k += (boss_dmg() // 2, g.r8(0xFFC8D6) == 2, g.r16(0xFFCD7A) != 0)
    return k


archive = {}        # cell -> [state (compressed), moves (16-bit masks), tries, stage timer left (s)]
top = (-1, None)    # (y, cell)


def add(moves):
    global top
    k = key()
    e = archive.get(k)
    if e is None or len(moves) < len(e[1]):
        raw, f = g.save()
        archive[k] = [(zlib.compress(raw, 1), f), array('H', moves), e[2] if e else 0, g.r16(0xFFCD62), progress()]
        y = progress()
        if g.r16(0xFF9410) == 0 or g.r8(0xFF9459) or BOSS:     # standing or on a ladder: a floor reached
            if y > top[0]:
                top = (y, k)
                open(out + '.moves', 'w').write('\n'.join('%x' % m for m in moves) + '\n')
                return True
    return False


STATS = os.environ.get('STATS')        # a file: per 200 px band of his y and enemy type, each update's step
st, st_prev = {}, [None, {}]


def sample():
    """one update's enemy steps (max of |dx|, |dy| in px) into STATS, keyed by (y band, type)"""
    u = g.r32(0xFF7084)
    if u == st_prev[0]:
        return
    cur = {}
    band = g.r16(0xFF9004) // 200 * 200
    for i in range(40):
        a = 0xFFB800 + 48 * i
        if g.r8(a + 4):
            t, x, y = g.r8(a + 10), g.r16(a + 17), g.r16(a + 21)
            cur[i] = (t, x, y)
            p = st_prev[1].get(i)
            if p and p[0] == t and st_prev[0] is not None and u == st_prev[0] + 1:
                d = max(abs(x - p[1]), abs(y - p[2]))
                if 0 < d < 40:
                    st.setdefault((band, t), []).append(d)
    st_prev[:] = [u, cur]


def dump_stats():
    with open(STATS, 'w') as fo:
        for (b, t), v in sorted(st.items()):
            v = sorted(v)
            fo.write('y%-5d t%-2d n%-6d mean %.2f p95 %d max %d\n' % (b, t, len(v), sum(v) / len(v), v[int(len(v) * .95)], v[-1]))


add([])
if os.environ.get('SEED_MOVES'):        # a known path (e.g. fb_proofs/stage5_partial.moves): every cell along it
    path = []
    for i, m in enumerate(int(v, 16) for v in open(os.environ['SEED_MOVES']).read().split()):
        g.run(1, m)
        path.append(m)
        if dead() or cleared():
            break
        if i % K == K - 1:
            add(path)
    print('seeded: %d frames, %d cells, top y %d' % (len(path), len(archive), top[0]), flush=True)
t0 = time.time()
for rnd in range(rounds):
    cells = list(archive.items())
    ys = sorted({c[1][4] for c in cells})
    rank = {y: i / max(1, len(ys) - 1) for i, y in enumerate(ys)}
    w = [(1 + 3 * rank[e[4]] ** 2) / (1 + e[2]) ** 0.5 * (e[3] / 180) ** 2 for c in cells for e in [c[1]]]
    k, e = random.choices(cells, w)[0]
    e[2] += 1
    raw, f = e[0]
    g.load((zlib.decompress(raw), f))
    st_prev[0] = None
    moves = list(e[1])
    last = [0, 'off']
    for s in range(random.randint(4, 40)):
        for m in macro(last):
            g.run(1, m)
            if STATS:
                sample()
            moves.append(m)
            if dead() or cleared():
                break
        if dead():
            break
        if cleared():
            open(out + '.moves', 'w').write('\n'.join('%x' % m for m in moves) + '\n')
            print('CLEARED in exploration: %d frames' % len(moves), flush=True)
            sys.exit(0)
        if add(moves):
            print('top y %d at x %d, %d frames, %d cells, round %d, %.0fs' % (
                top[0], g.r16(0xFF9001), len(moves), len(archive), rnd, time.time() - t0), flush=True)
            if top[0] >= stop_y and not BOSS:
                print('STOP y reached', flush=True)
                sys.exit(0)
    if rnd % 2000 == 0:
        if STATS:
            dump_stats()
        print('round %d cells %d top %d %.0fs' % (rnd, len(archive), top[0], time.time() - t0), flush=True)
print('ROUNDS out: top y %d' % top[0])
sys.exit(2)
