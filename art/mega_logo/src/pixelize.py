"""A gen.py draft -> the game's pixels: the art's bounding box cut to an h-pixel-tall
grid (width by its aspect), each cell the majority of its pixels in the logo's
4 colours (title palette line 0: 0 clear, 1 blue, 7 red, 9 light grey).
grid(path, h) -> rows of indices."""
from collections import Counter

from PIL import Image

PEN = {0: (0, 0, 0), 1: (0, 72, 180), 7: (216, 0, 0), 9: (216, 216, 216)}


def near(c):
    return min(PEN, key=lambda k: sum((a - b) ** 2 for a, b in zip(c, PEN[k])))


def grid(path, h):
    im = Image.open(path).convert('RGB')
    q = im.point(lambda v: v)          # copy
    W, H = im.size
    px = im.load()
    xs = [x for x in range(W) for y in range(0, H, 4) if max(px[x, y]) > 60]
    ys = [y for y in range(H) for x in range(0, W, 4) if max(px[x, y]) > 60]
    x0, x1, y0, y1 = min(xs), max(xs) + 1, min(ys), max(ys) + 1
    w = round(h * (x1 - x0) / (y1 - y0))
    out = []
    for gy in range(h):
        row = []
        for gx in range(w):
            ax, bx = x0 + (x1 - x0) * gx / w, x0 + (x1 - x0) * (gx + 1) / w
            ay, by = y0 + (y1 - y0) * gy / h, y0 + (y1 - y0) * (gy + 1) / h
            c = Counter()
            for y in range(int(ay + 0.2 * (by - ay)), int(by - 0.2 * (by - ay)) + 1):
                for x in range(int(ax + 0.2 * (bx - ax)), int(bx - 0.2 * (bx - ax)) + 1):
                    c[near(px[min(x, W - 1), min(y, H - 1)])] += 1
            row.append(c.most_common(1)[0][0])
        out.append(row)
    return out


def image(g, scale=1):
    im = Image.new('RGB', (len(g[0]), len(g)))
    for y, r in enumerate(g):
        for x, v in enumerate(r):
            im.putpixel((x, y), PEN[v])
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)
