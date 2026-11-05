"""Mega Ghosts'n Goblins' logo for the Home screens, from a gen.py demon draft:
the draft is cut to the screen's pixels at F times the scale where its GHOSTS'N
GOBLINS lettering is the game's own size (166 px of ink), so the demon and MEGA
fit the menu; colours quantized to the Genesis'. Then the game's own frameless
lettering (gng.py), at its own size and centred on the draft's, is put over a
black band (which hides the draft's smaller lettering) with a black outline.

Pens (palette line 1, beside the menu font's 1-3 and the Makaimura logo's 4-6,
which are also GHOSTS'N GOBLINS' red, grey and blue): 7 black, 8-15 the draft's.

build(rom, draft, f) -> (grid W x H of pens, colours {pen: 0x0BGR}, sub row)
usage: logo.py <rom> <draft> [f]   writes src_patch/mega_logo.h, art/mega_logo/mega_logo.png"""
from collections import Counter

from PIL import Image

import gng

W = 256
F = 1.0                          # the demon and MEGA at the draft's size (85% for the first round's)
INK = 166                        # the lettering's ink width in the game (columns 5-170)
GNG_PEN = {1: 6, 7: 4, 9: 5}     # the title's pens -> line 1's
FREE = list(range(8, 16))


def genesis(c):
    q = [min(7, round(v / 36)) for v in c]
    if c[2] > 1.3 * c[1] and q[2] and q[2] <= q[1]:     # navy stays blue, not teal
        q[2] = q[1] + 1
    return tuple(q)


def rgb(g):
    return tuple(v * 36 for v in g)


def word(g):
    return g[2] << 9 | g[1] << 5 | g[0] << 1


def letters_box(im):
    """the draft's GHOSTS'N GOBLINS: its red and light grey pixels"""
    px = im.load()
    w, h = im.size
    pts = [(x, y) for y in range(0, h, 2) for x in range(0, w, 2)
           if (lambda r, g, b: (r > 170 and g < 60 and b < 60) or (r > 180 and g > 180 and b > 180))(*px[x, y])]
    ys = Counter(y for _, y in pts)
    band = [y for y, n in ys.items() if n > 20]
    y0, y1 = min(band), max(band)
    xs = [x for x, y in pts if y0 <= y <= y1]
    return min(xs), y0, max(xs), y1


def extent(im):
    px = im.load()
    w, h = im.size
    pts = [(x, y) for y in range(0, h, 2) for x in range(0, w, 2) if sum(px[x, y]) > 40]
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def build(rom, draft, f=F):
    """-> (grid, colours, sub): the logo as tall as the draft's art needs (whole
    tile rows), and sub, the first of the 10 rows shown above a screen title"""
    im = Image.open(draft).convert('RGB')
    lx0, ly0, lx1, ly1 = letters_box(im)
    s = (lx1 - lx0) / INK / f                   # draft pixels per game pixel
    X0, Y0, X1, Y1 = extent(im)
    above, below = (ly0 - Y0) / s, (Y1 - ly1) / s
    title = gng.frameless(gng.logo(rom))
    # the title's ink rows in its grid
    rows = [y for y in range(24) if any(title[y])]
    cols = [x for x in range(176) if any(title[y][x] for y in range(24))]
    tw = cols[-1] - cols[0] + 1
    # game canvas: title ink starts at screen x (256 - tw)//2 and y = H - 1 - (last ink row) - 3
    th = rows[-1] - rows[0] + 1
    spill = (th - (ly1 - ly0) / s) / 2          # the game's title is taller than the draft's
    up, down = max(0, round(above - spill)), max(0, round(below - spill))
    H = (up + th + down + 2 + 7) // 8 * 8
    gx = (W - tw) // 2 - cols[0]
    gy = H - 1 - down - rows[-1]
    # the draft's lettering centre on the game title's ink centre
    cx, cy = gx + cols[0] + tw / 2, gy + (rows[0] + rows[-1]) / 2
    ox = (lx0 + lx1) / 2 - cx * s                # draft x of canvas x 0
    oy = (ly0 + ly1) / 2 - cy * s
    px = im.load()
    iw, ih = im.size
    cells = []
    for y in range(H):
        row = []
        for x in range(W):
            c = Counter()
            for yy in range(3):
                for xx in range(3):
                    sx = int(ox + (x + (xx + 0.5) / 3) * s)
                    sy = int(oy + (y + (yy + 0.5) / 3) * s)
                    c[genesis(px[sx, sy]) if 0 <= sx < iw and 0 <= sy < ih else (0, 0, 0)] += 1
            row.append(c.most_common(1)[0][0])
        cells.append(row)
    # the title area is redrawn from the game: leave it out of the colour count
    t_area = {(gy + y, gx + x) for y in range(24) for x in range(176)
              if any(title[yy][xx] for yy in range(max(0, y - 1), min(24, y + 2))
                     for xx in range(max(0, x - 1), min(176, x + 2)))}
    cnt = Counter(cells[y][x] for y in range(H) for x in range(W)
                  if (y, x) not in t_area and cells[y][x] != (0, 0, 0))
    # 8 colours: the most used, each further one the most used not within 1 step of those taken
    keep = []
    for c, _ in cnt.most_common():
        if all(max(abs(a - b) for a, b in zip(c, k)) > 1 for k in keep):
            keep.append(c)
        if len(keep) == len(FREE):
            break
    pens = dict(zip(FREE, keep))

    def pen(c):
        if c == (0, 0, 0):
            return 0
        k = min(pens, key=lambda p: sum((a - b) ** 2 for a, b in zip(c, pens[p])))
        return k

    grid = [[pen(cells[y][x]) for x in range(W)] for y in range(H)]
    # a black band behind the title (its ink box, 1 px out), then the title
    for y in range(gy + rows[0] - 1, gy + rows[-1] + 2):
        for x in range(gx + cols[0] - 1, gx + cols[-1] + 2):
            grid[y][x] = 7
    for y in range(24):
        for x in range(176):
            if title[y][x]:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = gy + y + dy, gx + x + dx
                        if 0 <= yy < H and 0 <= xx < W and not (0 <= y + dy < 24 and 0 <= x + dx < 176 and title[y + dy][x + dx]):
                            grid[yy][xx] = 7
    for y in range(24):
        for x in range(176):
            if title[y][x]:
                grid[gy + y][gx + x] = GNG_PEN[title[y][x]]
    colours = {7: 0}
    colours.update({p: word(c) for p, c in pens.items()})
    last = min(H // 8 - 1, (gy + rows[-1]) // 8 + 1)
    return grid, colours, max(0, last - 9)


LINE1 = {1: 0x0EEE, 2: 0x0E86, 3: 0x0222, 4: 0x000C, 5: 0x0CCC, 6: 0x0A40}


def image(grid, colours, scale=1):
    pal = dict(LINE1)
    pal.update(colours)
    im = Image.new('RGB', (len(grid[0]), len(grid)))
    for y, r in enumerate(grid):
        for x, v in enumerate(r):
            c = pal.get(v, 0) if v else 0
            im.putpixel((x, y), (((c >> 1) & 7) * 36, ((c >> 5) & 7) * 36, ((c >> 9) & 7) * 36))
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def tiles(grid):
    """-> (unique 8x8 tiles as 8 rows of 8 pens, map entries: 0 = blank, else
    tile number + 1 | $800 h-flip | $1000 v-flip), row major, W/8 x H/8"""
    uniq, index, nt = [], {}, []
    for ty in range(len(grid) // 8):
        for tx in range(len(grid[0]) // 8):
            t = tuple(tuple(grid[ty * 8 + y][tx * 8:tx * 8 + 8]) for y in range(8))
            if not any(any(r) for r in t):
                nt.append(0)
                continue
            for flip, f in ((0, t), (0x800, tuple(r[::-1] for r in t)),
                            (0x1000, t[::-1]), (0x1800, tuple(r[::-1] for r in t[::-1]))):
                if f in index:
                    nt.append((index[f] + 1) | flip)
                    break
            else:
                index[t] = len(uniq)
                uniq.append(t)
                nt.append(len(uniq))
    return uniq, nt


def header(grid, colours, sub, draft):
    uniq, nt = tiles(grid)
    out = ['/* Mega Ghosts\'n Goblins\' logo for the Home screens: generated by',
           ' * art/mega_logo/src/logo.py from %s; do not edit. */' % draft,
           '#define MEGA_W %d' % (len(grid[0]) // 8), '#define MEGA_H %d' % (len(grid) // 8),
           '#define MEGA_NT %d' % len(uniq),
           '#define MEGA_SUB %d     /* the first of the 10 rows above a screen title */' % sub,
           '/* palette line 1, pens 7-15 */',
           'static const u16 mega_colours[9] = { %s };' % ', '.join('0x%04X' % colours.get(p, 0) for p in range(7, 16)),
           'static const u32 mega_tiles[%d] = {' % (len(uniq) * 8)]
    for t in uniq:
        out.append('    ' + ', '.join('0x%08X' % int(''.join('%x' % v for v in r), 16) for r in t) + ',')
    out.append('};')
    out.append('static const u16 mega_map[%d] = {' % len(nt))
    for y in range(len(grid) // 8):
        w = len(grid[0]) // 8
        out.append('    ' + ', '.join('0x%04X' % e for e in nt[y * w:(y + 1) * w]) + ',')
    out.append('};')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    import os
    import sys
    rom_path, draft = sys.argv[1], sys.argv[2]
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(here, '..', '..', '..')
    f = float(sys.argv[3]) if len(sys.argv) > 3 else F
    g, c, sub = build(open(rom_path, 'rb').read(), draft, f)
    rel = os.path.relpath(draft, root)
    open(os.path.join(root, 'src_patch', 'mega_logo.h'), 'w').write(header(g, c, sub, rel))
    image(g, c).save(os.path.join(here, '..', 'mega_logo.png'))
    print('tiles', len(tiles(g)[0]), 'rows', len(g) // 8, 'sub', sub)
