"""Firebrand frames captured from Demon's Crest (tools/headless/snes_capture.py,
saved in art/firebrand/dc/*.json) and their mapping to the Genesis sprite
palette line 0 that every sprite in this port shares.

usage: dc.py <state for the Genesis palette> <out.png>   (preview sheet)"""
import json
import os
import sys

DC = os.path.join(os.path.dirname(__file__), '..', 'dc')

# animation sets: (capture file, picture indices in capture order)
SETS = {                           # facing comes from each picture's hflip
    'stand': ('walk', [8]),
    'walk': ('walk', [2, 3, 4, 5, 6, 7]),
    'fire': ('fire', [2]),
    'jump': ('fly', [2, 3, 4, 5, 6, 7]),
    'fly': ('fly', [8, 9, 10, 11, 12, 13]),
    'land': ('fly', [14, 15]),
    'shot': ('shot', [12, 13, 14]),
    'burst': ('shot', [15, 16, 17]),
}

# Genesis line 0 in play (index: RGB)
GEN = {1: (0, 0, 0), 2: (116, 0, 0), 3: (206, 0, 0), 4: (87, 52, 0), 5: (144, 52, 0),
       6: (116, 87, 0), 7: (206, 116, 0), 8: (144, 144, 0), 9: (52, 52, 116), 10: (172, 144, 116),
       11: (116, 116, 144), 12: (206, 172, 144), 13: (0, 116, 172), 14: (144, 144, 172),
       15: (172, 172, 206)}


def bgr555(c):
    return ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)


def nearest(rgb):
    r, g, b = rgb

    def dist(k):
        R, G, B = GEN[k]
        rm = (r + R) / 2
        return (2 + rm / 256) * (r - R) ** 2 + 4 * (g - G) ** 2 + (2 + (255 - rm) / 256) * (b - B) ** 2
    return min(GEN, key=dist)


def load(name):
    return json.load(open(os.path.join(DC, name + '.json')))


def frames(set_name):
    """[(rows of DC colour indices, box, DC palette, hflip)] for an animation
    set; hflip 1 = facing right as captured."""
    f, idx = SETS[set_name]
    recs = load(f)
    return [(recs[i]['rows'], recs[i]['box'], recs[i]['palette'], recs[i].get('hflip', 1)) for i in idx]


# Firebrand's palette (Demon's Crest sprite palette 7) by hand, keeping each step
# of his gold ramp distinct (nearest-colour matching merges 3/4 and 5/6):
#   1 (48,0,0)    -> 2 dark red      2 (80,16,0)   -> 4 brown
#   3 (128,40,0)  -> 5 rust          4 (168,80,0)  -> 6 ochre
#   5 (184,128,8) -> 7 orange        6 (232,184,40) -> 12 cream
#   7 (8,16,56)   -> 1 black         8 (24,56,120) -> 9 dark blue
#   9 (40,88,168) -> 11 slate        10 (48,144,224) -> 13 blue
#   11 white      -> 15              12 (128,128,168) -> 14 grey
#   13 (72,80,120) -> 11 slate       14 (40,48,80) -> 9 dark blue    15 black -> 1
FIREBRAND = {1: 2, 2: 4, 3: 5, 4: 6, 5: 7, 6: 12, 7: 1, 8: 9, 9: 11, 10: 13,
             11: 15, 12: 14, 13: 11, 14: 9, 15: 1}


def mapping(palette, set_name=None):
    """Firebrand's frames always use FIREBRAND (his firing pose flashes its
    palette, but the indices mean the same); shots use the nearest colours."""
    if set_name not in ('shot', 'burst'):
        return FIREBRAND
    return {i: nearest(bgr555(c)) for i, c in enumerate(palette) if i}


if __name__ == '__main__':
    from PIL import Image, ImageDraw
    Z = 3
    names = list(SETS)
    rows = []
    for n in names:
        rows.append((n, frames(n)))
    W = max(sum(f[1][2] + 6 for f in fr) for _, fr in rows) * Z + 80
    H = sum(max(f[1][3] for f in fr) + 8 for _, fr in rows) * Z * 2 + 20
    im = Image.new('RGB', (W, H), (36, 36, 52))
    d = ImageDraw.Draw(im)
    y = 4
    for n, fr in rows:
        h = max(f[1][3] for f in fr)
        for line, use_gen in ((0, False), (1, True)):
            x = 80
            d.text((4, y + 4), n + (' (genesis)' if use_gen else ' (snes)'), fill=(220, 220, 220))
            for rws, box, pal, _ in fr:
                m = mapping(pal, n)
                for yy, r in enumerate(rws):
                    for xx, ch in enumerate(r):
                        c = int(ch, 16)
                        if c:
                            col = GEN[m[c]] if use_gen else bgr555(pal[c])
                            d.rectangle([x + xx * Z, y + yy * Z, x + xx * Z + Z - 1, y + yy * Z + Z - 1], fill=col)
                x += (box[2] + 6) * Z
            y += (h + 8) * Z
    im.save(sys.argv[2])
    pal = load('walk')[0]['palette']
    print({i: (bgr555(c), nearest(bgr555(c))) for i, c in enumerate(pal) if i})
