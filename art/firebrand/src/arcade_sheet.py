"""A Firebrand sheet for the pixel editor (tools/firebrand_editor): one
arcade-looking frame for each of the editor's 112 slots.

Each slot shows what it shows in the in-game sheet (build.py: Arthur's 84
frames given Firebrand's pose of the same meaning and facing, then his walk and
hover cycles and the wall cling). Its picture is the arcade Red Arremer's own
frame (arremer.py), 1:1, wherever the arcade has that pose; where it has none
(the wall cling, the ladder) it is the matching frame of Firebrand on the
Gargoyle's Quest II (NES) sheet ripped by Fret (FX by pixelated_pollywog),
repainted in the arcade style (paint): its pose and pixels kept 1:1, each body
part shaded as the arcade shades (orange core, red, dark-red rim, dark-red
creases), its wings and bands in the arcade's blues, the arcade's blue eye.

Output: the editor's "Export PNG sheet" layout (12 a row, 48x32 at 3x, 6 px
gaps, background rgb(44,40,50) = clear), so "Load PNG" takes it whole; and
beside it firebrand_arcade_bank.bin, the same frames in firebrand_bank.bin's
format (build.py), which the editor shows as its arcade reference (make_data.py)
and "Load .bin" takes. Every frame must fit its 48x32 box (place() refuses
otherwise).

usage: arcade_sheet.py <rom (fixed build)> <gq2 sheet png> <out.png> [<labelled preview.png>]
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arremer                                   # noqa: E402

W, H, COUNT = 48, 32, 112
S, COLS = 3, 12
CW, CH = W * S + 6, H * S + 6
BG = (44, 40, 50)
LINE0 = [(0, 0, 0), (0, 0, 0), (116, 0, 0), (206, 0, 0), (87, 52, 0), (144, 52, 0), (116, 87, 0),
         (206, 116, 0), (144, 144, 0), (52, 52, 116), (172, 144, 116), (116, 116, 144),
         (206, 172, 144), (0, 116, 172), (144, 144, 172), (172, 172, 206)]
LINE2 = [(0, 0, 0), (0, 0, 0), (52, 52, 0), (116, 52, 0), (0, 87, 0), (144, 87, 0), (52, 116, 0),
         (87, 116, 0), (144, 172, 0), (52, 52, 52), (144, 116, 52), (87, 144, 52), (116, 87, 87),
         (116, 116, 116), (144, 116, 116), (144, 0, 0)]
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

# ---------- the GQ2 sheet ----------

# frame boxes on the left half of the sheet (x0, y0, x1, y1), all facing right
GQ2 = {
    0: (13, 12, 36, 41),                         # stand
    1: (91, 16, 115, 41),                        # curled up
    3: (13, 50, 37, 78), 4: (42, 50, 64, 78), 5: (69, 49, 92, 78),     # walk
    6: (98, 50, 123, 78), 7: (128, 49, 151, 78),
    8: (12, 88, 39, 113), 9: (46, 88, 76, 113),                        # hover: mid, up,
    10: (84, 88, 111, 113), 11: (118, 88, 145, 113),                   # mid, down
    12: (152, 85, 174, 113), 13: (180, 85, 204, 113),                  # hop, landing
    14: (15, 124, 38, 152),                                            # spit
    17: (13, 162, 43, 189), 18: (50, 161, 76, 189),                    # jump
    19: (83, 161, 109, 189), 20: (117, 161, 143, 189),
    23: (14, 198, 44, 221), 24: (52, 198, 78, 221), 25: (85, 198, 111, 221),  # flying spit
    29: (15, 233, 39, 261), 30: (47, 233, 72, 261),                    # wall cling, cling spit
}
NES = {(0, 0, 0): 'k', (181, 49, 33): 'r', (255, 130, 115): 's',
       (66, 66, 255): 'B', (66, 65, 255): 'B', (148, 214, 255): 'L', (189, 223, 255): 'L'}


def grab(im, k):
    """GQ2 frame k as rows of k (black), r (dark red), s (salmon), B/L (blues), '.'."""
    x0, y0, x1, y1 = GQ2[k]
    return [[NES.get(im.getpixel((x, y)), '.') for x in range(x0, x1)] for y in range(y0, y1)]


# ---------- the arcade style ----------

def blank():
    return [[0] * W for _ in range(H)]


def mirror(g):
    return [r[::-1] for r in g]


def blobs(g, keys):
    """4-connected regions of the given GQ2 colours: [[(x, y)...]...]."""
    h, w = len(g), len(g[0])
    seen, out = set(), []
    for y in range(h):
        for x in range(w):
            if g[y][x] in keys and (x, y) not in seen:
                st, pts = [(x, y)], []
                seen.add((x, y))
                while st:
                    p = st.pop()
                    pts.append(p)
                    for i, j in N4:
                        q = (p[0] + i, p[1] + j)
                        if 0 <= q[0] < w and 0 <= q[1] < h and q not in seen and g[q[1]][q[0]] in keys:
                            seen.add(q)
                            st.append(q)
                out.append(pts)
    return out


def paint(g):
    """A GQ2 frame (grab) repainted in the arcade style, pixel for pixel."""
    h, w = len(g), len(g[0])
    at = lambda x, y: g[y][x] if 0 <= x < w and 0 <= y < h else '.'
    o = [[0] * w for _ in range(h)]
    wing = set()
    for pts in blobs(g, 'BL'):
        if len(pts) >= 18:                       # small blue bits are the wrist/ankle bands
            wing |= set(pts)
    wingk = {(x, y) for y in range(h) for x in range(w)
             if g[y][x] == 'k' and sum((x + i, y + j) in wing for i, j in N4) >= 2}
    part = {}
    parts = blobs(g, 'rs')                       # body parts: red areas between black lines
    for n, pts in enumerate(parts):
        for p in pts:
            part[p] = n
    for pts in parts:                            # a rounded form lit from the front-right
        rows = {}
        for x, y in pts:
            rows.setdefault(y, []).append(x)
        top, bot = min(rows), max(rows)
        for x, y in pts:
            x0, x1 = min(rows[y]), max(rows[y])
            wd = x1 - x0 + 1
            if len(pts) < 6 or wd <= 2:
                o[y][x] = 7 if g[y][x] == 's' else 3
                continue
            d = abs((x - x0 + .5) / wd - .58) + (.1 if y == top and bot - top > 3 else 0)
            c = 7 if d < .2 else 3 if d < .4 else 2
            if g[y][x] == 'r' and c == 7:         # GQ2's shadow stays out of the light
                c = 3
            if g[y][x] == 's' and c == 2:
                c = 3
            o[y][x] = c
    for y in range(h):
        for x in range(w):
            c = g[y][x]
            if c == 'k':
                if (x, y) in wingk:              # wing ribs, black at the wing's edge
                    o[y][x] = 1 if any(at(x + i, y + j) == '.' for i, j in N4) else 9
                else:                            # outline and joins black, creases dark red
                    edge = any(at(x + i, y + j) == '.' for i, j in N4)
                    joins = len({part.get((x + i, y + j)) for i, j in N4} - {None}) >= 2
                    blue = any(at(x + i, y + j) in 'BL' for i, j in N4)
                    line = sum(at(x + i, y + j) == 'k' for i, j in N4) >= 3
                    o[y][x] = 1 if edge or joins or blue or line else 2
            elif c in 'BL':
                if (x, y) in wing:
                    o[y][x] = 11 if c == 'B' else 15 if at(x, y - 1) == 'L' and at(x - 1, y) == 'L' else 14
                else:
                    o[y][x] = 11 if c == 'L' else 13
    return o


# where each master's eye is (the same head drawn in most of them)
EYE = {0: (13, 6), 1: (13, 6), 3: (13, 6), 4: (13, 6), 5: (13, 6), 6: (13, 6), 7: (13, 6),
       8: (14, 7), 9: (17, 7), 10: (14, 7), 11: (14, 7), 12: (13, 6), 13: (13, 6), 14: (16, 7),
       17: (16, 6), 18: (13, 6), 19: (13, 6), 20: (13, 6), 23: (19, 7), 24: (16, 7), 25: (16, 7),
       29: (14, 8), 30: (17, 8)}


def art(g, eye):
    o = paint(g)
    x, y = eye
    o[y][x], o[y][x + 1] = 13, 11                # the arcade's blue eye and its glint
    return o


def place(g, wall=False):
    """On the 48x32 canvas: feet on the bottom row, body centred on Arthur's x
    (24); on a wall (the wall at his left), his leftmost pixel on x 8."""
    h, w = len(g), len(g[0])
    assert h <= H and w <= W, 'frame %dx%d does not fit the box' % (w, h)
    red = [x for r in g for x, c in enumerate(r) if c in (2, 3, 7)]
    ox = 8 if wall else max(0, min(W - w, round(24 - (min(red) + max(red)) / 2)))
    out = blank()
    for y in range(h):
        for x in range(w):
            if g[y][x]:
                out[H - h + y][ox + x] = g[y][x]
    return out


# ---------- the editor's slots ----------

# What each slot shows, as in the in-game sheet (build.py CLASS: Arthur's 84
# frames, each given Firebrand's pose of the same meaning and facing), then the
# walk and hover cycles and the wall cling. A frame is the arcade Red Arremer's
# own ('a', k) wherever it has the pose, else the matching GQ2 frame repainted
# in the arcade style ('g', k).
R, L = False, True
POSE = {
    'stand': ('a', 4), 'crouch': ('a', 1), 'land': ('a', 2), 'hit': ('a', 61),
    'jump': ('a', 23), 'jump2': ('a', 25),       # jumping forward; straight up
    'fire': ('a', 36), 'windup': ('a', 35),      # the spit; the moment before it
    'crouchfire': ('a', 2),                      # rising out of the crouch, arm out
    'climb': ('g', 29),                          # the ladder: GQ2's wall grip (the arcade never climbs)
}
CLASS = {
    0: ('stand', R), 7: ('jump', R), 8: ('jump2', R), 9: ('fire', R), 10: ('crouch', R),
    11: ('stand', R), 16: ('jump', R), 17: ('jump2', R), 18: ('fire', R), 19: ('crouch', R),
    20: ('crouch', R), 21: ('crouch', R), 22: ('crouch', R), 23: ('stand', R), 24: ('land', R),
    25: ('crouch', R), 26: ('crouch', R), 27: ('stand', R), 28: ('stand', R), 29: ('stand', L),
    30: ('crouch', R), 31: ('crouch', R), 32: ('crouch', L), 33: ('hit', R), 34: ('hit', R),
    50: ('fire', L), 51: ('stand', L), 52: ('stand', L), 54: ('jump', L), 55: ('jump2', L),
    56: ('fire', L), 58: ('crouch', L), 59: ('crouch', L), 64: ('jump', R), 65: ('jump2', R),
    66: ('windup', R), 67: ('fire', R),          # the throw (also in the air): wind-up, spit
    68: ('crouch', R), 69: ('crouchfire', R),    # the crouching throw
    70: ('climb', R), 71: ('climb', L), 72: ('climb', R), 73: ('climb', L),   # hand over hand
    78: ('jump', L), 79: ('jump2', L), 80: ('windup', L), 81: ('fire', L), 82: ('crouch', L),
    83: ('crouchfire', L),
}
BOOT = [11, 12, 13, 14, 15, 14, 13, 16, 17, 18, 19]  # slots 0..10 are copies of these
RUN_R = [1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 60, 61, 62, 63]   # the game shows the walk cycle
RUN_L = [53, 57, 74, 75, 76, 77]
FLAMES = {35: 51, 36: 53, 37: 55, 38: 56, 39: 58, 40: 57, 41: 55, 42: 53, 43: 59, 44: 60}
EMPTY = range(45, 50)                            # Arthur's empty frame and armor pieces
WALK = [('a', k) for k in (4, 3, 6, 5, 8, 7)]    # the arcade's steps: planted, step, planted, step
HOVER = [('a', k) for k in (23, 24, 25, 26, 19, 20)]   # its flight cycle's wing beat
CLING = [('g', 29), ('g', 30)]                   # GQ2's wall cling and its spit (the arcade has none)


def frames(rom, gq2_png):
    """The images by key: ('a', k) arcade frame k as it is; ('g', k) GQ2 frame k
    repainted (the cling frames with the wall side at x 8)."""
    from PIL import Image
    im = Image.open(gq2_png).convert('RGB')
    F = {('a', k): arremer.frame(rom, k) for k in range(71)}
    for k in GQ2:
        F[('g', k)] = place(art(grab(im, k), EYE[k]))
        F[('g', k, 'wall')] = place(art(grab(im, k), EYE[k]), wall=True)
    return F


def label(key):
    return ('arcade %d' if key[0] == 'a' else 'GQ2 #%d') % key[1]


def slots(rom, gq2_png):
    """[(image, palette line, source label)] for the 112 slots."""
    F = frames(rom, gq2_png)
    pick = lambda key, left: (mirror(F[key]) if left else F[key], 0, label(key))
    out = []
    for s in range(84):
        t = BOOT[s] if s < 11 else s
        if s in FLAMES:
            out.append((F[('a', FLAMES[s])], 2, 'arcade %d (flames)' % FLAMES[s]))
        elif s in EMPTY:
            out.append((blank(), 0, 'unused'))
        elif t in RUN_R or t in RUN_L:
            out.append(pick(WALK[0], t in RUN_L))
        else:
            pose, left = CLASS[t]
            out.append(pick(POSE[pose], left))
    for left in (R, L):
        out += [pick(k, left) for k in WALK]
    for left in (R, L):
        out += [pick(k, left) for k in HOVER]
    for key in CLING:
        out += [(F[key + ('wall',)], 0, label(key)), (mirror(F[key + ('wall',)]), 0, label(key))]
    assert len(out) == COUNT
    return out


# ---------- the sheet ----------

SLOT_NAMES = (['boot A%d' % i for i in range(11)] +
              ['A0', 'A1', 'A2', 'A3', 'A4', 'A7', 'A8', 'A9', 'B0/A10'] +
              ['B%d' % k for k in range(1, 65)] +
              ['Walk > %d' % i for i in range(1, 7)] + ['Walk < %d' % i for i in range(1, 7)] +
              ['Hover > %d' % i for i in range(1, 7)] + ['Hover < %d' % i for i in range(1, 7)] +
              ['Cling >', 'Cling <', 'Cling fire >', 'Cling fire <'])
for _s, _n in ((70, 'Climb A'), (71, 'Climb B'), (72, 'Climb top A'), (73, 'Climb top B')):
    SLOT_NAMES[_s] = _n
CREDIT = ("Masters: Firebrand from Gargoyle's Quest II (NES), ripped by Fret (FX by pixelated_pollywog). "
          "Style and colours: the arcade Red Arremer (Capcom).")


def render(cells, path, labels=None):
    from PIL import Image, ImageDraw
    rows = (len(cells) + COLS - 1) // COLS
    lab = 12 if labels else 0
    foot = 16 if labels else 0
    im = Image.new('RGB', (COLS * CW, rows * (CH + lab) + foot), BG)
    d = ImageDraw.Draw(im)
    if labels:
        d.text((4, im.size[1] - 13), CREDIT, fill=(220, 220, 220))
    for i, (g, line) in enumerate(cells):
        pal = LINE2 if line == 2 else LINE0
        ox, oy = (i % COLS) * CW, (i // COLS) * (CH + lab) + lab
        if labels:
            d.text((ox + 2, oy - lab), labels[i], fill=(220, 220, 220))
            d.rectangle([ox + 8 * S, oy, ox + 40 * S - 1, oy + H * S - 1], fill=(56, 52, 64))
        for y in range(H):
            for x in range(W):
                c = g[y][x]
                if c:
                    d.rectangle([ox + x * S, oy + y * S, ox + x * S + S - 1, oy + y * S + S - 1], fill=pal[c])
    im.save(path)


def bank_frame(g):
    """0x300 bytes as in firebrand_bank.bin: the 32x32 body (16 tiles, column-major,
    canvas x 8..39), then the 8x32 columns at x 0..7 and x 40..47."""
    out = bytearray()
    for x0, cols in ((8, 4), (0, 1), (40, 1)):
        for tx in range(cols):
            for ty in range(4):
                for y in range(8):
                    r = g[ty * 8 + y]
                    for x in range(0, 8, 2):
                        out.append(r[x0 + tx * 8 + x] << 4 | r[x0 + tx * 8 + x + 1])
    return bytes(out)


def main(rom_path, gq2_png, out, preview=None):
    rom = open(rom_path, 'rb').read()
    sl = slots(rom, gq2_png)
    render([(g, line) for g, line, _ in sl], out)
    with open(os.path.join(os.path.dirname(os.path.abspath(out)), 'firebrand_arcade_bank.bin'), 'wb') as f:
        f.write(b''.join(bank_frame(g) for g, _, _ in sl))
    if preview:
        render([(g, line) for g, line, _ in sl], preview,
               ['%s  %s' % (SLOT_NAMES[s], sl[s][2]) for s in range(COUNT)])
    src = Counter(t.split(' (')[0] for _, _, t in sl)
    print('slots', COUNT, 'arcade', sum(n for t, n in src.items() if t.startswith('arcade')),
          'GQ2', sum(n for t, n in src.items() if t.startswith('GQ2')), 'unused', src['unused'])


if __name__ == '__main__':
    main(*sys.argv[1:])
