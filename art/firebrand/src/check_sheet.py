"""Check a Firebrand editor sheet PNG (arcade_sheet.py's output, or the editor's
"Export PNG sheet"): every pixel inside its frame's 48x32 box (none in the gaps
between cells or past the last frame), every editor pixel a whole 3x3 block of
one colour, and every colour from the frame's palette line. Given the ROM and
the GQ2 sheet, also that each frame is exactly arcade_sheet.py's build of it
(place() refuses a frame that does not fit), so nothing was cut off on the way.

usage: check_sheet.py <sheet.png> [<rom (fixed build)> <gq2 sheet png>]     exits 1 on any problem
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arcade_sheet as a                         # noqa: E402


def main(path, rom_path=None, gq2_png=None):
    from PIL import Image
    im = Image.open(path).convert('RGB')
    iw, ih = im.size
    px = im.load()
    bad = []
    rows = ih // a.CH
    if iw != a.COLS * a.CW or ih % a.CH or rows * a.COLS < a.COUNT:
        bad.append('sheet is %dx%d, not %d rows of %d cells of %dx%d' % (iw, ih, rows, a.COLS, a.CW, a.CH))
    outside = {}
    for y in range(ih):
        for x in range(iw):
            if px[x, y] == a.BG:
                continue
            col, row, cx, cy = x // a.CW, y // a.CH, x % a.CW, y % a.CH
            s = row * a.COLS + col
            if cx >= a.W * a.S or cy >= a.H * a.S or s >= a.COUNT:
                outside[s] = outside.get(s, 0) + 1
    for s, n in sorted(outside.items()):
        bad.append('frame %d: %d pixels outside its box' % (s, n))
    for s in range(min(a.COUNT, rows * a.COLS)):
        ox, oy = (s % a.COLS) * a.CW, (s // a.COLS) * a.CH
        pal = set(a.LINE2[1:] if s in a.FLAMES else a.LINE0[1:])   # the flames are line 2
        for y in range(a.H):
            for x in range(a.W):
                block = {px[ox + x * a.S + i, oy + y * a.S + j] for i in range(a.S) for j in range(a.S)}
                if len(block) > 1:
                    bad.append('frame %d pixel (%d,%d): not one colour (%d)' % (s, x, y, len(block)))
                c = block.pop()
                if c != a.BG and c not in pal:
                    bad.append('frame %d pixel (%d,%d): %s is not in its palette line' % (s, x, y, c))
    if rom_path:                                 # the generator's frames, pixel for pixel
        for s, (g, line, _) in enumerate(a.slots(open(rom_path, 'rb').read(), gq2_png)):
            pal = a.LINE2 if line == 2 else a.LINE0
            ox, oy = (s % a.COLS) * a.CW, (s // a.COLS) * a.CH
            diff = sum(1 for y in range(a.H) for x in range(a.W)
                       if px[ox + x * a.S, oy + y * a.S] != (tuple(pal[g[y][x]]) if g[y][x] else a.BG))
            if diff:
                bad.append('frame %d: %d pixels differ from its build' % (s, diff))
    print('\n'.join(bad) if bad else
          'ok: %d frames, every pixel inside its 48x32 box, whole 3x3 pixels, palette colours only%s'
          % (a.COUNT, ', every frame exactly its arcade build' if rom_path else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
