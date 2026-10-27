"""Firebrand's campaign played headless by a search bot (no invincibility, no
pokes): random moves in 8-frame segments, rewinding with save states on a
death or a stall, until the stage byte $FFF400 moves on.

usage: fb_campaign.py <rom> <stage 1-7> <out prefix> [max frames searched]
  stage 7 = the final room (stage 6 launch with $FFF400 poked to 6, as
  tools/lockstep/README.md describes; the poke is the launch, not play).
  START=<file.state> starts from a saved state instead (e.g. the previous
  stage's clear, to chain the campaign).

Writes <out>.moves (one input mask per played frame, hex, from the launch),
<out>_clear.state at the stage change and PNGs along the way. Replaying the
moves from the same launch with no rewinds plays the same game: `REPLAY=1`
does that and reports the clear (the proof that the stage was beaten).

Progress is camera x + 2 x camera y (the camera never scrolls back; the
climbs count double) plus a quarter of Firebrand's x and y, 10 per second
left on the stage timer ($FFCD62), plus, since the camera last moved (capped), points
scored and enemy hit points taken (slot +11, sampled every segment), so a
boss fight counts as progress while hits land; so does getting near the
dragon (type 12: it only wakes with Firebrand under it). In the climbing
stages (5, 6) his x doesn't count, and his y only where he stands or climbs
(the camera doesn't climb while he's in the air). Once the boss is dead
($FFC8D6 = 2) the key (the stage-end object in weapon slot 0, $FF9600) is
the goal: closing in on it is progress, taking it ($FFCD7A) more.

Every 250 segments <out>.moves holds the path so far; RESUME=1 replays it
and searches on from there (TRUNC=n frames dropped from its end first).
Repeated failures without a new best back up further each time (doubling).

A load of a save state taken mid-stage is not exact in this core (the next
frames can differ, by frame pacing), so a path found with rewinds may not
play the same straight. Loading the launch state is exact: at each clear the
path is replayed straight from it, and if that replay dies at frame t, the
search goes on from the straight replay's state 240 frames before t, until a
straight replay clears. The .moves file is then that straight path.

The core runs at OC (default 200%) CPU: no update is dropped, so the
updates (the game's logic) are the hardware's without its slowdown, and
loads change the game far less often (at 100% the frame pacing makes them
drift). OC=100% for the hardware's timing."""
import os
import random
import sys
import time
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fbh import Game, F, U, D, LT, RT, J     # noqa: E402

rom, stage, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
budget = int(sys.argv[4]) if len(sys.argv) > 4 else 400000
K = 8
g = Game(rom, sysdir=os.path.dirname(os.path.abspath(out)),
         options={'genesis_plus_gx_overclock': os.environ.get('OC', '200%')})
if os.environ.get('START'):
    g.run(1)
    g.load((open(os.environ['START'], 'rb').read(), 0))
else:
    if stage == 7:
        # the developer menu stops at stage 6: its stage index poked to 6 while it launches
        g.launch(6, poke=lambda gg: 880 <= gg.frame <= 1300 and gg.w8(0xFF500B, 7))
    else:
        g.launch(stage)
launch_frame = g.frame
stage0 = g.r8(0xFFF400)
idx0 = g.r8(0xFFC512)


def dead():
    """hit ($FFC342) or a death starting ($FFC570 = 1; it is 3 while the game
    goes to the next stage's map too)"""
    return g.r8(0xFFC342) or g.r16(0xFFC570) == 1


def cleared():
    """the stage index ($FFC512) moved on: the stage end (or the ending) is
    taking the game to the next map; $FFF400 follows ~300 frames later"""
    return g.r8(0xFFC512) != idx0 or g.r8(0xFFF400) != stage0


def score():
    s = 0
    for a in range(0xFFC000, 0xFFC004):           # BCD
        s = s * 100 + (g.r8(a) >> 4) * 10 + (g.r8(a) & 15)
    return s


if os.environ.get('REPLAY'):
    moves = [int(v, 16) for v in open(out + '.moves').read().split()]
    for i, m in enumerate(moves):
        g.run(1, m)
        if cleared():
            print('REPLAY: stage index %d -> %d after %d frames, no death' % (idx0, g.r8(0xFFC512), i + 1))
            g.want_video = True
            g.run(1)
            g.png(out + '_replay_clear.png')
            sys.exit(0)
        if dead():
            print('REPLAY: died at move', i)
            sys.exit(1)
    print('REPLAY: ended without a clear')
    sys.exit(1)


last_dj = [RT, 'off']
LADDERS = {4: range(0x74, 0x7A), 5: range(0x74, 0x7A)}    # stages 5 and 6 (by stage index)


def ladder_dir():
    """towards the nearest ladder cell beside or under him (the terrain ring), up on it"""
    tiles = LADDERS.get(g.r8(0xFFC512))
    if not tiles:
        return None
    fx, fy = g.r16(0xFF9001), g.r16(0xFF9004)
    best = None
    for dy in (8, 24):
        y = fy + dy
        for dx in range(-192, 193, 16):
            x = fx + dx
            i = (x & 0x1F0) * 2 | (((y >> 4) ^ 15) & 31)
            if g.r8(0xFF0000 + i) in tiles:
                cx = (x & ~15) + 8
                if best is None or abs(cx - fx) < abs(best - fx):
                    best = cx
    if best is None:
        return None
    return U if abs(best - fx) <= 6 else RT if best > fx else LT


def macro(prev):
    """(direction, jump, fire) -> 8 masks; the direction and jump carry on
    from the last segment 60% of the time (ladders, long walks, hovers)"""
    if random.random() < 0.6:
        d, j = last_dj
        j = 'hold' if j == 'press' else j
    else:
        d = random.choices([RT, 0, LT, U, D, 'lad'], [50, 10, 16, 14, 10, 15])[0]
        j = random.choices(['off', 'hold', 'press'], [50, 32, 18])[0]
    last_dj[:] = [d, j]
    if d == 'lad':                      # to the nearest ladder and up it
        d = ladder_dir()
        if d is None:
            d = RT
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


def hp_map():
    m = {}
    for k in range(40):
        a = 0xFFB800 + 48 * k
        if g.r8(a + 4):
            m[k] = (g.r8(a + 10), g.r8(a + 11))
    return m


def hits(old, new):
    return sum(o[1] - n[1] for k, o in old.items() for n in [new.get(k)] if n and n[0] == o[0] and n[1] < o[1])


def save_moves(shot=False):
    open(out + '.moves', 'w').write('\n'.join('%x' % m for m in moves) + '\n')
    if shot:                        # a picture of where the path is, without moving the game on
        st = g.save()
        g.want_video = True
        g.run(1, 0)
        g.png(out + '_now.png')
        g.want_video = False
        g.load(st)


st0 = g.save()      # the launch: its loads are exact


def snap():         # a rewind point, compressed (a state is ~1 MB, mostly zeros)
    raw, f = g.save()
    return zlib.compress(raw, 1), f


def restore(st):
    g.load((zlib.decompress(st[0]), st[1]))


def straight(n, rec=None):
    """moves[:n] from the launch, no rewinds: ('clear' | 'dead' | 'ok', frames played);
    rec: a list given the state every 8 frames (rewind points for the search)"""
    g.load(st0)
    for i, m in enumerate(moves[:n]):
        if rec is not None and i % K == 0:
            rec.append((snap(), i, -1, -1, 0, 0, 0, {}, 0))
        g.run(1, m)
        if cleared():
            return 'clear', i + 1
        if dead():
            return 'dead', i + 1
    return 'ok', n


def place(n, rec=None):
    """the game at moves[:n] played straight (back from a death if there is one)"""
    global moves
    r, t = straight(n)
    if r == 'dead':
        moves = moves[:max(0, t - 240)]
    if r == 'dead' or rec is not None:
        straight(len(moves), rec)
    return r, t


hist = []           # (state, moves played, best, best_cam, cam_score, cam_dmg, dmg, hp map, gy)
moves = []
if os.environ.get('RESUME') and os.path.exists(out + '.moves'):
    moves = [int(v, 16) for v in open(out + '.moves').read().split()]
    moves = moves[:max(0, len(moves) - int(os.environ.get('TRUNC', '0')))]
    print('resume:', place(len(moves), hist), 'path', len(moves), flush=True)
best = -1
best_cam = -1
cam_score = 0
cam_dmg = dmg = 0
gy = 0              # the highest y he has stood or climbed at
hpm = hp_map()
fails = {}
since_best = 0
streak = 0          # failures since the last new best
searched = 0
t0 = time.time()
g.want_video = False
seg = 0
while searched < budget:
    st = snap()
    camx, camy = g.r16(0xFFA200), g.r16(0xFFA202)
    cam = camx + 2 * camy
    if g.r16(0xFF9410) == 0 or g.r8(0xFF9459):     # standing or on a ladder
        gy = max(gy, g.r16(0xFF9004))
    new = hp_map()
    dmg += hits(hpm, new)
    hpm = new
    if cam > best_cam:
        best_cam = cam
        cam_score = score()
        cam_dmg = dmg
    if g.r8(0xFFC512) in (4, 5):        # the climbs
        here = gy / 2
    else:
        here = (g.r16(0xFF9001) + g.r16(0xFF9004)) / 4
    prog = cam + here + 10 * g.r16(0xFFCD62) + min((score() - cam_score) / 100, 40) + min(25 * (dmg - cam_dmg), 600)
    if g.r8(0xFFC8D6) != 2:             # near a boss
        fx, fy, near = g.r16(0xFF9001), g.r16(0xFF9004), 300
        for k in range(40):
            a = 0xFFB800 + 48 * k
            if g.r8(a + 4) and g.r8(a + 10) == 12 and g.r8(a + 11) >= 5:
                near = min(near, abs(g.r16(a) - fx) + abs(g.r16(a + 2) - fy))
        prog += 300 - near
    if g.r8(0xFFC8D6) == 2:             # the boss is dead: get the key
        kx, ky = (g.r32(0xFF9600) >> 8) & 0xFFFF, (g.r32(0xFF9604) >> 8) & 0xFFFF
        prog += 1000 - min(abs(kx - g.r16(0xFF9001)) + abs(ky - g.r16(0xFF9004)), 900) + (1000 if g.r16(0xFFCD7A) else 0)
    if prog > best:
        best = prog
        since_best = 0
        streak = 0
    hist.append((st, len(moves), best, best_cam, cam_score, cam_dmg, dmg, hpm, gy))
    ms = macro(moves[-1] if moves else 0)
    died = False
    for m in ms:
        g.run(1, m)
        searched += 1
        moves.append(m)
        if cleared():
            break
        if dead():
            died = True
            break
    if cleared() and not died:
        r, t = place(len(moves))
        if r != 'clear':
            print('REPAIR: the straight replay %s at frame %d; searching on from frame %d' % (
                r, t, len(moves)), flush=True)
            hist, fails, best, best_cam, since_best = [], {}, -1, -1, 0
            cam_dmg = dmg = gy = 0
            hpm = hp_map()
            continue
        moves = moves[:t]
        save_moves()
        g.want_video = True
        g.run(1)
        g.png(out + '_clear.png')
        open(out + '_clear.state', 'wb').write(g.save()[0])
        print('CLEAR stage index %d -> %d: %d frames played, %d searched, %.0f s' % (
            idx0, g.r8(0xFFC512), len(moves), searched, time.time() - t0), flush=True)
        sys.exit(0)
    since_best += 1
    if died or since_best > 200:
        i = len(hist) - 1
        fails[i] = fails.get(i, 0) + 1
        streak += 1
        back = 1 + fails[i] // 2 + (8 if not died else 0)
        if streak > 40:                 # stuck: back up much further, doubling
            back = max(back, 2 ** min((streak - 40) // 10 + 3, 10))
        back = min(back, len(hist) - 1)
        tgt = len(hist) - 1 - back
        st, nm, best, best_cam, cam_score, cam_dmg, dmg, hpm, gy = hist[tgt]
        hist = hist[:tgt]
        restore(st)
        moves = moves[:nm]
        since_best = 0
    seg += 1
    if seg % 250 == 0:
        save_moves(True)
        print('searched %d played %d x %d y %d cam %d,%d best %.0f hits %d lives %d score %d %.0fs' % (
            searched, len(moves), g.r16(0xFF9001), g.r16(0xFF9004), g.r16(0xFFA200), g.r16(0xFFA202),
            best, dmg, g.r8(0xFFC500), score(), time.time() - t0), flush=True)
save_moves()
open(out + '_last.state', 'wb').write(g.save()[0])
print('BUDGET out: played %d, best %.0f' % (len(moves), best))
sys.exit(2)
