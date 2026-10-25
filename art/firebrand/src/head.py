"""A clean, hand-drawn head for the 70% Firebrand. Demon's Crest shades his head
with fine dithering that turns to noise when scaled down, so build.py finds the
head in each source frame (template match against the standing frame's head) and
stamps this one over it after scaling. Facing right; Genesis palette line 0:
1 black, 4 brown, 5 rust, 6 ochre, 7 orange, 12 cream, 15 white."""

STAMP = [                  # horn sweeping back, brow over a glowing eye, snout, fangs
    '1.......',
    '.1......',
    '.171....',
    '..1761..',
    '.177761.',
    '17611c71',
    '15767771',
    '154f1f1.',
    '.15551..',
]

# the firing pose: the same head with the jaw dropped and fire glowing in the mouth
FIRE_STAMP = [
    '1.......',
    '.1......',
    '.171....',
    '..1761..',
    '.177761.',
    '17611c71',
    '15767771',
    '15f137c1',
    '151f3c71',
    '.15551..',
]
FIRE_BOX = (21, 3, 29, 13)          # its head in the firing pose (source pixels, facing right)

# his two head drawings (source pixels, facing right): (dc set, picture, box x0, y0, x1, y1).
# Standing/jumping/flying share one; the walk nods with the other. The firing pose
# (head thrown back, mouth open) matches neither; it gets FIRE_STAMP at FIRE_BOX.
TEMPLATES = [('stand', 0, 19, 4, 27, 14), ('walk', 0, 16, 4, 23, 15)]
MAX_MISMATCH = 30          # template score above this: no head found, no stamp


def stamp(rows=STAMP):
    return [[int(c, 16) if c != '.' else 0 for c in r] for r in rows]


def find(tpl, g):
    """Best (score, x, y) of the template (DC colour indices) inside g, comparing
    only his body colours (1-6): the wing behind the head changes per pose."""
    th, tw = len(tpl), len(tpl[0])
    h, w = len(g), len(g[0])
    best = (1 << 30, 0, 0)
    for oy in range(0, h - th + 1):
        for ox in range(0, w - tw + 1):
            sc = 0
            for y in range(th):
                gy, ty = g[oy + y], tpl[y]
                for x in range(tw):
                    a = ty[x]
                    if 1 <= a <= 6 and a != gy[ox + x]:
                        sc += 1 if gy[ox + x] else 2
                if sc >= best[0]:
                    break
            if sc < best[0]:
                best = (sc, ox, oy)
    return best


# the stage-map marker (16x16, replaces Arthur's helmet icon at tiles $2A9-$2AC):
MAP_ICON = [                       # front view: wing tips, pale horns, glowing eyes, fangs
    'e..............e',
    'ee............ee',
    '.ee..a....a..ee.',
    '.eee.aa..aa.eee.',
    '..ee.1a77a1.ee..',
    '..e.17777771.e..',
    '...1777777771...',
    '...1767777671...',
    '...17c3773c71...',
    '...1777777771...',
    '...1677117761...',
    '....171ff171....',
    '....16f11f61....',
    '.....166661.....',
    '......1111......',
    '................',
]


def map_icon_tiles():
    """128 bytes: the 2x2 sprite's tiles in column order (TL, BL, TR, BR)."""
    g = stamp(MAP_ICON)
    out = bytearray()
    for tx in range(2):
        for ty in range(2):
            for y in range(8):
                r = g[ty * 8 + y]
                for x in range(0, 8, 2):
                    out.append(r[tx * 8 + x] << 4 | r[tx * 8 + x + 1])
    return bytes(out)
