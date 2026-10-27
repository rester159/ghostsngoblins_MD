"""sprite_audit.py: where each game draws an object's sprites relative to the object (headless).

Records, frame by frame, the sprites on the screen as pixel masks and the objects (Arthur and the 40 enemy
slots) in either game, then pairs the arcade's 16x16 pieces with the identical pixels in the port's picture
and compares where each is drawn relative to its object.

  sprite_audit.py arc  <arcade state> <frames> <out.pkl>      the arcade (tools/arcade/gng.py) from a state
  sprite_audit.py port <core> <rom> <frames> <out.pkl>         the port (Genesis Plus GX); LOAD = state to start
                                                               from, or SCRIPT = a devscript.py launch
  sprite_audit.py cmp  <arc.pkl>... -- <port.pkl>...           the report
  sprite_audit.py box  <arc.pkl>... -- <port.pkl>... <type>    bounding boxes of one type's pixels (art that
                                                               isn't the arcade's, e.g. Astaroth)

Capture options (environment): SEED (random input with fire; 0 = none), INV=0 (Arthur not kept invincible
and his lives not kept at 3),
FROM (first frame recorded), TP=frame:x,... (Arthur put at x), WALK=1 (the random input goes right), POKE (port, lr.py's form), PIN=y (Arthur's y
held), PAD (a fixed pad mask, the game's own bits).

What is compared. Displayed on frame N+1 in both games: the arcade's sprite list as its VBlank copies it
(sprite RAM at the end of frame N, gng.py's spritebuf) and the port's sprite table and tiles in VRAM after
frame N+1 (the update of frame N, DMA'd in the VBlank of N+1, with the art streamed in the same VBlank);
each against the objects in RAM at the end of frame N. Positions relative to an object are screen offsets
from (x - camera x, 240 - (y - camera y)) (y points up in both games; the camera is the one the
background is drawn with: the arcade's <$9C/<$9E (its scroll registers), the port's $FF9100/2 (its plane B
scroll; $FFA200/2, the copy its game logic reads, is a frame behind it while scrolling); Arthur's
32x32 is then at (-16, -16) in both); the two games' screens differ by a constant,
the most common difference over all pairs (printed), and a placement is right when a pair differs by it.

The arcade's pieces (16x16, pen 15 transparent) are put to the nearest object of a type (Arthur = -1) within
40 px of its anchor; a piece of at least MINPX opaque pixels is a key (type, pixel mask). In the port's
picture (the union of all sprites' opaque pixels, pen 0 transparent) every 16x16 window on the 8 px grid of
any sprite within 48 px of an object is looked up by its pixels among the same type's keys. The port's pose
(slot +30, the builders' frame number) is kept with each pair, so a frame drawn in the wrong place, or with
the art of another pose (streamed art arriving late), is listed by it; a window that is an arcade piece
mirrored is counted as mirrored.
"""
import collections
import os
import pickle
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
MINPX = int(os.environ.get('MINPX', '24'))
M = 64                                   # margin around the 256-wide screen in the port's union mask


def rand_pad(seed, n, bits):
    """random input as bench.sh's (a choice every 8-40 frames)"""
    rnd = random.Random(seed); out = []; f = 0
    while f < n:
        m = rnd.choice(bits); k = rnd.randint(8, 40); out += [m] * (k + 1); f += k + 1
    return out


def _tps():
    """TP=frame:x,frame:x,...: Arthur put at x for 3 frames from each frame"""
    return [tuple(map(int, t.split(':'))) for t in os.environ.get('TP', '').split(',') if t]


def _objs(raw, cam, prev):
    """objects as (slot, type, screen x, screen y, pose, still, screen x/y a frame earlier, x, y, camera, camera a
    frame earlier, x/y a frame earlier): screen = (x - camera x, 240 - (y - camera y)); still = neither it nor the
    camera moved since the frame before"""
    cx, cy = cam; out = []
    pv = {} if prev is None else {(o[0], o[1]): o for o in prev[0]}
    for sl, t, x, y, pose in raw:
        q = pv.get((sl, t))
        still = q is not None and (q[2], q[3]) == (x, y) and prev[1] == cam
        px, py = (q[2] - prev[1][0], 240 - (q[3] - prev[1][1])) if q else (None, None)
        out.append((sl, t, x - cx, 240 - (y - cy), pose, still, px, py, x, y, cam, prev[1] if prev else None,
                    (q[2], q[3]) if q else None))
    return out, (raw, cam)


# ---------------------------------------------------------------- arcade capture
def cap_arc(state, frames, outp):
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'arcade'))
    from gng import GnG
    g = GnG(os.path.join(ROOT, 'rom')); g.load(state); m = g.mem
    seed = int(os.environ.get('SEED', '1'))
    # arcade pad: 1 right 2 left 4 down 8 up 10 fire 20 jump
    bits = [1, 0x11, 0x21, 1, 0x10, 0x31, 1] if os.environ.get('WALK') else [1, 0x11, 0x10, 0x21, 2, 0x12, 0, 0x14, 1]
    pads = rand_pad(seed, frames + 50, bits) if seed else None
    fixed = int(os.environ.get('PAD', '0'), 16)
    tps = _tps(); pin = os.environ.get('PIN'); first = int(os.environ.get('FROM', '1'))
    inv = os.environ.get('INV', '1') != '0'
    recs = []; prev_objs = None; prev_raw = None
    for f in range(1, frames + 1):
        if inv: m[0xAD] = 60; m[0x60] = 3           # invincible, lives kept
        for tf, tx in tps:
            if tf <= f < tf + 3: m[0x506] = tx >> 8; m[0x507] = tx & 255
        if pin: y = int(pin); m[0x509] = y >> 8; m[0x50A] = y & 255
        g.set_inputs(0, pads[f] if pads else fixed, 0); g.run_frame()
        # displayed now: spritebuf (sprite RAM at the end of the previous frame) against prev_objs
        if prev_objs is not None and f >= first:
            b = g.spritebuf; pcs = []
            for o in range(0, 0x200, 4):
                at = b[o + 1]; code = b[o] + ((at << 2) & 0x300)
                x = b[o + 3] - (0x100 if at & 1 else 0); y = b[o + 2] - 16
                if b[o + 2] == 0 or y >= 224 or y <= -16: continue
                pcs.append((x, y, code, bool(at & 4), bool(at & 8)))
            recs.append((f, prev_objs, pcs, tuple(g.scroll)))
        raw = [(-1, -1, m[0x506] << 8 | m[0x507], m[0x509] << 8 | m[0x50A], 0)]
        for i in range(40):
            a = 0x880 + 48 * i
            if m[a]:
                raw.append((i, m[a + 0x15], m[a + 6] << 8 | m[a + 7], m[a + 9] << 8 | m[a + 10], m[a + 3]))
        prev_objs, prev_raw = _objs(raw, (m[0x9C] << 8 | m[0x9D], m[0x9E] << 8 | m[0x9F]), prev_raw)
    pickle.dump(dict(game='arc', recs=recs), open(outp, 'wb'))
    print('arcade: %d frames recorded' % len(recs))


_arc_cache = {}


def arc_piece(g, code, hf, vf):
    """the 16 rows of a 16x16 arcade piece as ints (bit x = pixel x), opaque = pen != 15"""
    k = (code, hf, vf)
    if k not in _arc_cache:
        rows = []
        for py in range(16):
            r = 0
            for px in range(16):
                if g._sprite(code, 15 - px if hf else px, 15 - py if vf else py) != 15:
                    r |= 1 << px
            rows.append(r)
        _arc_cache[k] = tuple(rows)
    return _arc_cache[k]


# ---------------------------------------------------------------- port capture
def cap_port(core, rom, frames, outp):
    sys.argv = [sys.argv[0], core, rom, str(frames), outp + '_lr']
    G = {'__file__': os.path.join(ROOT, 'tools', 'lockstep', 'lrbase.py')}
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'lockstep'))
    import lrbase
    lrbase.setup(G)
    L, C, ram, rd, SCRIPT = G['L'], G['C'], G['ram'], G['rd'], G['SCRIPT']
    seed = int(os.environ.get('SEED', '1'))
    # port pad: B=1 fire, A=0x100 jump, UP 10 DOWN 20 LEFT 40 RIGHT 80
    bits = [0x80, 0x81, 0x180, 0x80, 1, 0x181, 0x80] if os.environ.get('WALK') else [0x80, 0x81, 1, 0x101, 0x40, 0x41, 0, 0x21, 0x80]
    pads = rand_pad(seed, frames + 50, bits) if seed else None
    fixed = int(os.environ.get('PAD', '0'), 16)
    pokes = []
    for pk in os.environ.get('POKE', '').split(','):
        if pk.strip():
            pf, pa, pv = pk.split(':'); pokes.append((int(pf), int(pa, 16), pv))
    first = int(os.environ.get('FROM', '1')); inv = os.environ.get('INV', '1') != '0'
    pin = os.environ.get('PIN'); tps = _tps()
    p = L.retro_get_memory_data(2)

    def w8(a, v):
        C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v & 255
    n = L.retro_serialize_size(); sbuf = C.create_string_buffer(n)
    BASE = 0x12425
    recs = []; prev_objs = None; prev_raw = None; prev_upd = None
    for f in range(1, frames + 1):
        G['frame_no'][0] = f
        for pf, pa, pv in pokes:
            if pf == f:
                k = (len(pv) + 1) // 2; v = int(pv, 16)
                for j in range(k): w8(pa + j, v >> (8 * (k - 1 - j)))
        r0 = ram()
        live = rd(r0, 0xFF7FF0, 4) == 0x4C495645
        if live and f >= first:
            if inv: w8(0xFFC309, 60); w8(0xFFC500, 3)    # invincible, lives kept
            if pin: y = int(pin); w8(0xFF9004, y >> 8); w8(0xFF9005, y)
            for tf, tx in tps:
                if tf <= f < tf + 3: w8(0xFF9001, tx >> 8); w8(0xFF9002, tx)
            SCRIPT[:] = [(f, f, pads[f] if pads else fixed)]
        L.retro_run()
        r = ram()
        if prev_objs is not None and f >= first:
            L.retro_serialize(sbuf, n); st = sbuf.raw
            vram = bytes(st[BASE + (i ^ 1)] for i in range(0x10000))
            regs = st[BASE + 0x10100:BASE + 0x10120]
            sat = (regs[5] & 0x7F) << 9
            sprs = []; i = 0; tcache = {}
            for _ in range(80):
                e = vram[sat + i * 8:sat + i * 8 + 8]
                a = e[4] << 8 | e[5]
                y = ((e[0] << 8 | e[1]) & 0x3FF) - 128; x = ((e[6] << 8 | e[7]) & 0x1FF) - 128
                w = (e[2] >> 2 & 3) + 1; h = (e[2] & 3) + 1
                t0 = a & 0x7FF; hf = a >> 11 & 1; vf = a >> 12 & 1
                if -32 < y < 224 and -32 < x < 256:
                    rows = [0] * (h * 8)
                    for tx in range(w):
                        for ty in range(h):
                            t = (t0 + tx * h + ty) & 0x7FF
                            if t not in tcache:
                                tr = []
                                for ry in range(8):
                                    bb = vram[t * 32 + ry * 4:t * 32 + ry * 4 + 4]; rr = 0
                                    for q in range(4):
                                        if bb[q] >> 4: rr |= 1 << (2 * q)
                                        if bb[q] & 15: rr |= 1 << (2 * q + 1)
                                    tr.append(rr)
                                tcache[t] = tr
                            for ry in range(8):
                                rr = tcache[t][ry]
                                rows[ty * 8 + ry] |= rr << (tx * 8)
                    W = w * 8
                    if hf: rows = [_rev(rr, W) for rr in rows]
                    if vf: rows = rows[::-1]
                    sprs.append((x, y, W, h * 8, tuple(rows), a))
                i = e[3] & 0x7F
                if not i: break
            upd = rd(r, 0xFF7084, 4)
            # the scroll shown at line 120: hscroll table (reg 13; reg 11 mode: full, per 8 lines, per line)
            hs = (regs[13] & 0x3F) << 10; md = regs[11] & 3
            hs += 0 if md == 0 else (120 & ~7) * 4 if md == 2 else 120 * 4
            vs = st[BASE + 0x10080:BASE + 0x10088]
            scr = (vram[hs] << 8 | vram[hs + 1], vram[hs + 2] << 8 | vram[hs + 3],
                   vs[1] << 8 | vs[0], vs[3] << 8 | vs[2], regs[11])          # plane A/B h, plane A/B v
            recs.append((f, prev_objs, sprs, upd - (prev_upd or upd), scr))
        raw = [(-1, -1, rd(r, 0xFF9001, 2), rd(r, 0xFF9004, 2), 0)]
        for i in range(40):
            a = 0xFFB800 + 48 * i
            if rd(r, a + 4, 1):
                raw.append((i, rd(r, a + 10, 1), rd(r, a + 17, 2), rd(r, a + 21, 2), rd(r, a + 30, 2)))
        prev_objs, prev_raw = _objs(raw, (rd(r, 0xFF9100, 2), rd(r, 0xFF9102, 2)), prev_raw)
        prev_upd = rd(r, 0xFF7084, 4)
    pickle.dump(dict(game='port', recs=recs), open(outp, 'wb'))
    print('port: %d frames recorded' % len(recs))


def _rev(v, n):
    r = 0
    for k in range(n):
        if v >> k & 1: r |= 1 << (n - 1 - k)
    return r


# ---------------------------------------------------------------- comparison
def nearest(objs, cx, cy, lim=40):
    best = None
    for o in objs:
        d = max(abs(cx - o[2]), abs(cy - o[3]))
        if d <= lim and (best is None or d < best[0]):
            best = (d, o)
    return best[1] if best else None


def arc_index(paths):
    """(type, rows) -> Counter of offsets from still objects, and the moving samples (key, offset against the
    object at the end of frame N, against it at N-1)"""
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'arcade'))
    from gng import GnG
    g = GnG(os.path.join(ROOT, 'rom'))
    idx = collections.defaultdict(collections.Counter); moving = []
    for pth in paths:
        for f, objs, pcs, *_ in pickle.load(open(pth, 'rb'))['recs']:
            for x, y, code, hf, vf in pcs:
                rows = arc_piece(g, code, hf, vf)
                if sum(bin(v).count('1') for v in rows) < MINPX: continue
                o = nearest(objs, x + 8, y + 8)
                if o is None: continue
                if o[5]: idx[(o[1], rows)][(x - o[2], y - o[3])] += 1
                elif o[6] is not None: moving.append(((o[1], rows), (x - o[2], y - o[3]), (x - o[6], y - o[7])))
    return idx, moving


def _grid(n):
    """window origins along a sprite of n px: its 16 px grid (and its last 16 px); an 8 px sprite as either
    half of a 16 px piece"""
    if n == 8: return (-8, 0)
    return sorted(set(list(range(0, n - 15, 16)) + [n - 16]))


def keep_keys(idx):
    """drop pieces not attached to their object in the arcade (shots and others put to the nearest object
    show up at many offsets): keep the offsets seen at least max(2, 5%) of the time, and keys with at most 4"""
    out = {}
    for k, c in idx.items():
        tot = sum(c.values())
        kept = collections.Counter({o: v for o, v in c.items() if v >= max(2, tot // 20)})
        if kept and len(kept) <= 4: out[k] = kept
    return out


MIRRORED = []


def port_pairs(paths, idx):
    """(type, rows, offset, pose, frame, slot, still, offset against the object a frame earlier)"""
    keys = {}
    for (t, rows) in idx: keys.setdefault(rows, set()).add(t)
    out = []
    for pth in paths:
        for f, objs, sprs, du, *_ in pickle.load(open(pth, 'rb'))['recs']:
            canvas = collections.defaultdict(int)             # screen y -> row bits (x + M)
            for x, y, W, H, rows, a in sprs:
                for k, rr in enumerate(rows):
                    if rr: canvas[y + k] |= rr << (x + M)
            cands = set()
            for x, y, W, H, rows, a in sprs:
                for gx in _grid(W):
                    for gy in _grid(H):
                        cands.add((x + gx, y + gy))
            for (wx, wy) in cands:
                rows = tuple((canvas.get(wy + k, 0) >> (wx + M)) & 0xFFFF for k in range(16))
                ts = keys.get(rows)
                if not ts:
                    # the arcade's piece drawn mirrored: counted as such (type, pose, frame, slot)
                    mr = tuple(_rev(v, 16) for v in rows)
                    ts = keys.get(mr) if mr != rows else None
                    if ts:
                        o = nearest([ob for ob in objs if ob[1] in ts], wx + 8, wy + 8, 48)
                        if o is not None: MIRRORED.append((o[1], o[4], f, o[0], mr, (wx - o[2], wy - o[3])))
                    continue
                o = nearest([ob for ob in objs if ob[1] in ts], wx + 8, wy + 8, 48)
                if o is None: continue
                pv = (wx - o[6], wy - o[7]) if o[6] is not None else None
                out.append((o[1], rows, (wx - o[2], wy - o[3]), o[4], f, o[0], o[5], pv))
    return out


def report(arcp, portp):
    raw, amov = arc_index(arcp)
    idx = keep_keys(raw)                          # still objects
    allr = collections.defaultdict(collections.Counter, {k: collections.Counter(v) for k, v in raw.items()})
    for k, dn, dp in amov: allr[k][dn] += 1
    idx_all = keep_keys(allr)                     # every frame, against the object at N (the arcade draws at N)
    for k in idx:
        idx_all.setdefault(k, idx[k])
    pairs = port_pairs(portp, idx_all)
    still = [p for p in pairs if p[6] and (p[0], p[1]) in idx]
    # the screens' constant: the most common difference over the still pairs (each against the arcade's
    # commonest offset of its key)
    diff = collections.Counter()
    for p in still:
        a = idx[(p[0], p[1])].most_common(1)[0][0]
        diff[(p[2][0] - a[0], p[2][1] - a[1])] += 1
    K = diff.most_common(1)[0][0]
    print('pairs %d (%d with the object and the camera still); screen constant (port - arcade) %s (%d of them; next %s)'
          % (len(pairs), len(still), K, diff[K], diff.most_common(4)[1:]))
    # arcade timing: moving objects drawn at their position at N or N-1 (against the still placements)
    tim = collections.defaultdict(collections.Counter)
    for k, dn, dp in amov:
        if k in idx: tim[k[0]]['N' if dn in idx[k] else ('N-1' if dp in idx[k] else '-')] += 1
    per = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for t, rows, d, pose, f, sl, st, pv in pairs:
        dd = (d[0] - K[0], d[1] - K[1]); k = (t, rows)
        if st and k in idx:
            if dd in idx[k]: per[t][pose]['still ok'] += 1
            else:
                best = min(idx[k], key=lambda a: abs(a[0] - dd[0]) + abs(a[1] - dd[1]))
                per[t][pose][('still', dd[0] - best[0], dd[1] - best[1])] += 1
        elif not st:
            if dd in idx_all[k]: per[t][pose]['moving ok'] += 1
            elif pv is not None and (pv[0] - K[0], pv[1] - K[1]) in idx_all[k]: per[t][pose]['moving N-1'] += 1
            else:
                best = min(idx_all[k], key=lambda a: abs(a[0] - dd[0]) + abs(a[1] - dd[1]))
                per[t][pose][('moving', dd[0] - best[0], dd[1] - best[1])] += 1
    for t, pose, f, sl, mr, d in MIRRORED: per[t][pose]['mirrored'] += 1
    seen = collections.Counter(t for t, _ in idx_all)
    for t in sorted(set(list(seen) + list(per))):
        c = tim[t]
        print('type %d: %d arcade piece masks (arcade, moving: drawn at N %d, N-1 %d, neither %d)' % (t, seen[t], c['N'], c['N-1'], c['-']))
        for pose in sorted(per[t]):
            c = per[t][pose]
            so, mo, m1, mi = c.pop('still ok', 0), c.pop('moving ok', 0), c.pop('moving N-1', 0), c.pop('mirrored', 0)
            bad = ', '.join('%s %+d,%+d x%d' % (k[0], k[1], k[2], v) for k, v in c.most_common(3))
            print('   pose %3d: still %5d at the arcade place, moving %5d (%d at N-1)%s%s'
                  % (pose, so, mo, m1, ('; mirrored %d' % mi) if mi else '', ('; off: ' + bad) if bad else ''))
    ex = os.environ.get('SHOW')                   # SHOW=type:pose prints that pose's still pairs
    if ex:
        t0, p0 = map(int, ex.split(':')); seen_k = set()
        for t, rows, d, pose, f, sl, st, pv in pairs:
            if t != t0 or pose != p0: continue
            dd = (d[0] - K[0], d[1] - K[1])
            if (rows, dd) in seen_k: continue
            seen_k.add((rows, dd))
            print('frame %d slot %d port at %s, arcade at %s' % (f, sl, dd, dict(idx_all[(t, rows)])))
            for r in rows: print('      ' + ''.join('#' if r >> k & 1 else '.' for k in range(16)))
    ex = os.environ.get('SHOWMI')                 # SHOWMI=type:pose: the mirrored windows
    if ex:
        t0, p0 = map(int, ex.split(':'))
        for t, pose, f, sl, mr, d in MIRRORED:
            if t == t0 and pose == p0:
                print('frame %d slot %d: port window at %s is the arcade piece seen at %s, mirrored'
                      % (f, sl, (d[0] - K[0], d[1] - K[1]), dict(idx_all[(t, mr)])))
    ex = os.environ.get('SHOWM')                  # SHOWM=type:pose: the moving pairs' offsets from the nearest arcade one
    if ex:
        t0, p0 = map(int, ex.split(':')); c = collections.Counter(); cp = collections.Counter()
        for t, rows, d, pose, f, sl, st, pv in pairs:
            if t != t0 or pose != p0 or st or pv is None: continue
            for dd, cc in (((d[0] - K[0], d[1] - K[1]), c), ((pv[0] - K[0], pv[1] - K[1]), cp)):
                best = min(idx_all[(t, rows)], key=lambda a: abs(a[0] - dd[0]) + abs(a[1] - dd[1]))
                cc[(dd[0] - best[0], dd[1] - best[1])] += 1
        print('moving, against N:', c.most_common(8)); print('moving, against N-1:', cp.most_common(8))
    return idx, pairs, K


def boxes(arcp, portp, ty):
    """bounding box of the pixels within 64 px of each object of type ty (no other object nearer), per pose:
    left/right/top/bottom relative to the object, the arcade's by state, the port's by pose"""
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'arcade'))
    from gng import GnG
    g = GnG(os.path.join(ROOT, 'rom'))
    ab = collections.defaultdict(collections.Counter)
    for pth in arcp:
        for f, objs, pcs, *_ in pickle.load(open(pth, 'rb'))['recs']:
            for o in [ob for ob in objs if ob[1] == ty]:
                x0 = y0 = 999; x1 = y1 = -999
                for x, y, code, hf, vf in pcs:
                    if nearest(objs, x + 8, y + 8, 64) is not o: continue
                    rows = arc_piece(g, code, hf, vf)
                    for k, rr in enumerate(rows):
                        if rr:
                            y0 = min(y0, y + k); y1 = max(y1, y + k)
                            x0 = min(x0, x + (rr & -rr).bit_length() - 1); x1 = max(x1, x + rr.bit_length() - 1)
                if x1 >= x0: ab[o[4]][(x0 - o[2], x1 - o[2], y0 - o[3], y1 - o[3])] += 1
    pb = collections.defaultdict(collections.Counter)
    for pth in portp:
        for f, objs, sprs, du, *_ in pickle.load(open(pth, 'rb'))['recs']:
            for o in [ob for ob in objs if ob[1] == ty]:
                x0 = y0 = 999; x1 = y1 = -999
                for x, y, W, H, rows, a in sprs:
                    if nearest(objs, x + W // 2, y + H // 2, 64) is not o: continue
                    for k, rr in enumerate(rows):
                        if rr:
                            y0 = min(y0, y + k); y1 = max(y1, y + k)
                            x0 = min(x0, x + (rr & -rr).bit_length() - 1); x1 = max(x1, x + rr.bit_length() - 1)
                if x1 >= x0: pb[o[4]][(x0 - o[2], x1 - o[2], y0 - o[3], y1 - o[3])] += 1
    print('arcade, by state: (left, right, top, bottom) x count')
    for s in sorted(ab): print('  ', s, ab[s].most_common(6))
    print('port, by pose:')
    for s in sorted(pb): print('  ', s, pb[s].most_common(6))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'arc':
        cap_arc(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif cmd == 'port':
        cap_port(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5])
    elif cmd in ('cmp', 'box'):
        a = sys.argv[2:]; k = a.index('--')
        if cmd == 'cmp': report(a[:k], a[k + 1:])
        else: boxes(a[:k], a[k + 1:-1], int(a[-1]))
