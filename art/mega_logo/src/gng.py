"""The game's GHOSTS'N GOBLINS logo (title map rows 6-8, 22 x 3 tiles from column 6,
title tiles at $202408, palette line 0) as a 176 x 24 grid of pens, with its red
frame taken out: the red pixels 4-connected to the frame's outer edge, and its
top bar (rows 6-7, which runs behind the letters: red under a blank row 5)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TILES, MAP = 0x202408, 0x2035E8


def logo(rom):
    w = lambda a: int.from_bytes(rom[a:a + 2], 'big')
    g = [[0] * 176 for _ in range(24)]
    for ty in range(3):
        for tx in range(22):
            e = w(MAP + ((6 + ty) * 64 + 6 + tx) * 2)
            t, hf, vf = e & 0x7FF, e & 0x800, e & 0x1000
            for py in range(8):
                for px in range(8):
                    sx, sy = (7 - px if hf else px), (7 - py if vf else py)
                    b = rom[TILES + t * 32 + sy * 4 + sx // 2]
                    g[ty * 8 + py][tx * 8 + px] = b >> 4 if sx % 2 == 0 else b & 15
    return g


def frameless(g):
    h, w = len(g), len(g[0])
    seen, st = set(), []
    for y in range(h):
        for x in range(w):
            if g[y][x] == 7 and (y in (0, h - 1) or x in (0, w - 1) or
                                 not any(g[y][xx] for xx in range(x)) or
                                 (y in (6, 7) and g[5][x] == 0)):
                st.append((y, x))
    while st:
        y, x = st.pop()
        if (y, x) in seen or not (0 <= y < h and 0 <= x < w) or g[y][x] != 7:
            continue
        seen.add((y, x))
        st += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    out = [[0 if (y, x) in seen else g[y][x] for x in range(w)] for y in range(h)]
    for x in range(1, w - 1):           # the bar through the open G's: the shadow it covered
        if out[7][x] == 7 and out[7][x - 1] == 1 and out[7][x + 1] == 1:
            out[7][x] = 1
    return out
