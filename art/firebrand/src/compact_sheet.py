"""The compact Firebrand sheet (art/firebrand/sheets/firebrand_compact.png): every distinct picture
once, 48x32 at 1x in 50x34 cells, 7 to a row, on (44, 40, 50) with transparent (or white) cells,
in handoff_sheet.py's three sections (its _raw.png) under coloured lines:
  green   WORKS: the bank's distinct frames (a mirrored pair once), then the 18 pictures full_sheet.py lists
          after them: fireball shapes 1-4, impacts (burst, flame, sparks), weapon box, map marker,
          wing pickup, frog 1-8 (the order of full_sheet.py's extras; the frog isn't imported: it is in its own colours; small ones centred, on the cell's floor; the fireballs and
          impacts as they fly left, i.e. their pieces mirrored)
  orange  BROKEN: the ladder as it was (a reference: not imported)
  red     MISSING: Climb A, Climb B, Climb top A, Climb top B (slots 70-73), then "hit, facing left",
          which has no slot of its own (not imported)
Which cell each of the 112 slots takes (and mirrored or not) is in compact_sheet_map.json,
made once with `map` from the art in place when the sheet was drawn (every unchanged cell equals
its slots' frames; a changed one goes to the slots it is nearest).

usage: compact_sheet.py map <sheet.png> <art dir>      writes compact_sheet_map.json
       compact_sheet.py import <sheet.png> <art dir>   writes the bank, flags and extras' bins"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcade_sheet as a                                       # noqa: E402
from PIL import Image                                          # noqa: E402


def tiles(data, cols, rows):
    """cols x rows 8x8 tiles stored column-major (4 bpp) -> pixel rows"""
    g = [[0] * (cols * 8) for _ in range(rows * 8)]
    k = 0
    for tx in range(cols):
        for ty in range(rows):
            for y in range(8):
                for x in range(0, 8, 2):
                    b = data[k]
                    k += 1
                    g[ty * 8 + y][tx * 8 + x] = b >> 4
                    g[ty * 8 + y][tx * 8 + x + 1] = b & 15
    return g


def bank_image(f):
    """a firebrand_bank.bin frame -> 48x32 (arcade_sheet.bank_frame's inverse)"""
    body, left, right = tiles(f[:0x200], 4, 4), tiles(f[0x200:0x280], 1, 4), tiles(f[0x280:0x300], 1, 4)
    return [left[y] + body[y] + right[y] for y in range(32)]


def mirror(g):
    return [r[::-1] for r in g]

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = os.path.join(HERE, '..', 'sheets', 'compact_sheet_map.json')
BG = (44, 40, 50)
LADDER = [70, 71, 72, 73]                         # Climb A, Climb B, Climb top A, Climb top B
L0 = [tuple(c) for c in a.LINE0]
L2 = [tuple(c) for c in a.LINE2]


def cells(png):
    im = Image.open(png).convert('RGBA')
    W, H = im.size
    px = im.load()
    bgrow = [sum(1 for x in range(W) if px[x, y][:3] != BG or not px[x, y][3]) < 10 for y in range(H)]
    out, y, sec = [], 0, -1
    while y < H:
        if bgrow[y]:
            y += 1
            continue
        y0 = y
        while y < H and not bgrow[y]:
            y += 1
        if y - y0 < 32:                          # a section line: green, orange, red
            sec += 1
            continue
        x = 0
        nb = [any(px[x, yy][:3] != BG or not px[x, yy][3] for yy in range(y0, y)) for x in range(W)]
        while x < W:
            if not nb[x]:
                x += 1
                continue
            x0 = x
            while x < W and nb[x]:
                x += 1
            g = [[None if (px[x0 + i, y0 + j][3] == 0 or px[x0 + i, y0 + j][:3] == (255, 255, 255))
                  else px[x0 + i, y0 + j][:3] for i in range(48)] for j in range(32)]
            out.append((sec, g))
    return out


def rgb(g, line):
    pal = L2 if line == 2 else L0
    return [[pal[v] if v else None for v in r] for r in g]


def place(g):
    """a small picture in a 48x32 cell as full_sheet draws it: centred, on the floor"""
    h, w = len(g), len(g[0])
    c = [[None] * 48 for _ in range(32)]
    for y in range(h):
        for x in range(w):
            c[32 - h + y][(48 - w) // 2 + x] = g[y][x]
    return c, (48 - w) // 2, 32 - h


def extras(art):
    """[(name, file, offset, kind, pixels in pens)] in the sheet's order"""
    rd = lambda n: open(os.path.join(art, n), 'rb').read()
    side = lambda p, q: [p[y] + q[y] for y in range(len(p))]
    out = []
    anim = rd('firebrand_fire_anim.bin')
    for k in range(4):
        p = anim[k * 0x100:(k + 1) * 0x100]
        out.append(('fireball %d' % (k + 1), 'firebrand_fire_anim.bin', k * 0x100, 'pair',
                    side(mirror(tiles(p[:0x80], 2, 2)), mirror(tiles(p[0x80:], 2, 2)))))
    for k in range(3):
        p = anim[(4 + k) * 0x100:(5 + k) * 0x100]
        out.append(('impact %d' % (k + 1), 'firebrand_fire_anim.bin', (4 + k) * 0x100, 'one', mirror(tiles(p[:0x80], 2, 2))))
    f = rd('firebrand_fire.bin')
    out.append(('weapon box', 'firebrand_fire.bin', 0, 'pair', side(mirror(tiles(f[:0x80], 2, 2)), mirror(tiles(f[0x80:], 2, 2)))))
    out.append(('map marker', 'firebrand_mapicon.bin', 0, 'plain', tiles(rd('firebrand_mapicon.bin'), 2, 2)))
    out.append(('wing pickup', 'firebrand_wing.bin', 0, 'plain', tiles(rd('firebrand_wing.bin')[:0x80], 2, 2)))
    fr = rd('firebrand_frog.bin')
    for k in range(8):
        out.append(('frog %d' % (k + 1), 'firebrand_frog.bin', k * 0x200, 'frog', tiles(fr[k * 0x200:(k + 1) * 0x200], 4, 4)))
    return out


def enc(g, cols, rows):
    """pixel rows -> cols x rows 8x8 tiles, column-major 4 bpp (tiles' inverse)"""
    b = bytearray()
    for tx in range(cols):
        for ty in range(rows):
            for y in range(8):
                r = g[ty * 8 + y][tx * 8:tx * 8 + 8]
                b += bytes(r[i] << 4 | r[i + 1] for i in range(0, 8, 2))
    return bytes(b)


def same(p, q):
    return sum(1 for y in range(32) for x in range(48) if p[y][x] == q[y][x])


def do_map(png, art):
    sec = [k for k, _ in cells(png)]
    cs = [g for _, g in cells(png)]
    bank, flags = open(os.path.join(art, 'firebrand_bank.bin'), 'rb').read(), open(os.path.join(art, 'firebrand_flags.bin'), 'rb').read()
    fr = [rgb(bank_image(bank[s * 0x300:(s + 1) * 0x300]), 2 if flags[s] & 4 else 0) for s in range(a.COUNT)]
    ex = extras(art)
    n_ex = len(ex)
    # the green section's frames end where the extras begin: the first cell equal to the first extra
    first_ex = rgb(place(ex[0][4])[0], 0)
    k0 = max(range(len(cs)), key=lambda i: same(cs[i], first_ex))
    slots = {}
    frame_cells = list(range(k0)) + list(range(k0 + n_ex, len(cs)))
    red = [c for c in frame_cells if sec[c] == 2]
    for s in range(a.COUNT):
        if s in a.EMPTY:                                    # never shown, not on the sheet: kept
            slots[s] = (-1, 0, 1536)
            continue
        if s in LADDER and LADDER.index(s) < len(red):     # MISSING: the ladder frames, in order
            slots[s] = (red[LADDER.index(s)], 0, 1536)
            continue
        cand = [(same(cs[c], fr[s]), 1, -c, c, 0) for c in frame_cells if sec[c] == 0]
        cand += [(same(cs[c], mirror(fr[s])), 0, -c, c, 1) for c in frame_cells if sec[c] == 0]
        n, _, _, c, mi = max(cand)                          # ties: unmirrored, the first cell
        slots[s] = (c, mi, n)
    m = {'frames': {str(s): [c, mi] for s, (c, mi, _) in slots.items()},
         'extras': list(range(k0, k0 + n_ex)), 'cells': len(cs)}
    json.dump(m, open(MAP, 'w'), indent=0)
    low = sorted((v[2], s, v[0]) for s, v in slots.items() if v[2] < 1536)
    print('cells', len(cs), 'extras from cell', k0, '; slots not equal to a cell (changed art):',
          [(s, a.SLOT_NAMES[s], c, n) for n, s, c in low])


# colours the Genesis palette lacks, to the nearest one it has (reported)
ALIAS = {(34, 34, 34): (0, 0, 0)}
aliased = []


def pens(g, line_hint):
    """RGB cell pixels -> pens of line 0 or 2 (the hint first)"""
    n = sum(1 for r in g for c in r if c in ALIAS)
    if n:
        aliased.append(n)
        g = [[ALIAS.get(c, c) for c in r] for r in g]
    used = {c for r in g for c in r if c}
    for line in (line_hint, 2 - line_hint):
        pal = L2 if line == 2 else L0
        inv = {}
        for i in range(len(pal) - 1, 0, -1):
            inv[pal[i]] = i
        if used <= set(inv):
            return line, [[inv[c] if c else 0 for c in r] for r in g]
    raise SystemExit('colours not in palette lines 0 or 2: %s' % sorted(used - set(inv)))


def do_import(png, art):
    m = json.load(open(MAP))
    cs = [g for _, g in cells(png)]
    if len(cs) != m['cells']:
        raise SystemExit('the sheet has %d cells, the map %d' % (len(cs), m['cells']))
    flags_old = open(os.path.join(art, 'firebrand_flags.bin'), 'rb').read()
    bank, flags = bytearray(), bytearray()
    bank_old = open(os.path.join(art, 'firebrand_bank.bin'), 'rb').read()
    for s in range(a.COUNT):
        c, mi = m['frames'][str(s)]
        if c < 0:                               # not on the sheet: as it is
            bank += bank_old[s * 0x300:(s + 1) * 0x300]
            flags.append(flags_old[s])
            continue
        g = mirror(cs[c]) if mi else cs[c]
        line, p = pens(g, 2 if flags_old[s] & 4 else 0)
        bank += a.bank_frame(p)
        lw = any(p[y][x] for y in range(32) for x in range(8))
        rw = any(p[y][x] for y in range(32) for x in range(40, 48))
        flags.append((flags_old[s] & ~7) | lw | rw << 1 | (4 if line == 2 else 0))
    open(os.path.join(art, 'firebrand_bank.bin'), 'wb').write(bank)
    open(os.path.join(art, 'firebrand_flags.bin'), 'wb').write(flags)
    files = {}
    changed = []
    for (name, fn, off, kind, old), c in zip(extras(art), m['extras']):
        if kind == 'frog':              # in the frog's own colours, not line 0's; no code shows it
            continue
        h, w = len(old), len(old[0])
        _, x0, y0 = place(old)
        cut = [r[x0:x0 + w] for r in cs[c][y0:y0 + h]]
        outside = sum(1 for y in range(32) for x in range(48) if cs[c][y][x] and not (y0 <= y < y0 + h and x0 <= x < x0 + w))
        if outside:                     # bigger than the game's picture: needs code, left as it is
            print('NOT IMPORTED: %s is bigger than its %dx%d picture (%d pixels outside)' % (name, w, h, outside))
            continue
        # drawn in other colours than line 0 (the frog, in its own): unchanged when every pen of the
        # old picture is one colour in the cell and back
        fwd, bwd, ok = {}, {}, True
        for y in range(h):
            for x in range(w):
                o, c = old[y][x], cut[y][x]
                if fwd.setdefault(o, c) != c or bwd.setdefault(c, o) != o:
                    ok = False
        if ok:
            continue
        _, p = pens(cut, 0)
        if p == old:
            continue
        changed.append(name)
        buf = files.setdefault(fn, bytearray(open(os.path.join(art, fn), 'rb').read()))
        if kind == 'pair':
            data = enc(mirror([r[:16] for r in p]), 2, 2) + enc(mirror([r[16:] for r in p]), 2, 2)
        elif kind == 'one':
            data = enc(mirror(p), 2, 2)
        elif kind == 'plain':
            data = enc(p, 2, 2)
        else:
            data = enc(p, 4, 4)
        buf[off:off + len(data)] = data
    for fn, buf in files.items():
        open(os.path.join(art, fn), 'wb').write(buf)
    print('bank', len(bank), 'flags changed', sum(1 for i in range(a.COUNT) if flags[i] != flags_old[i]),
          'extras changed', changed or 'none', 'pixels moved to the nearest colour', sum(aliased))


if __name__ == '__main__':
    {'map': do_map, 'import': do_import}[sys.argv[1]](*sys.argv[2:4])
