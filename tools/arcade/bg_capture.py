"""Capture the arcade's stage 1 background as one picture (headless, tools/arcade/gng.py).

Boots the arcade (coin, start), then moves Arthur right 2 px a frame (teleports, his
height held, invincible) to world x XEND, recording the bg video RAM of every 16 px
column on screen and the BG palette (entries 0-63). Writes <out>.pkl with
  cols: world column -> (codes[32], attrs[32])    pal: 64 (r, g, b) of the first frame
  idx:  256 rows of per-pixel BG palette indices (world x)
and <out>.png. Slow (Python 6809): a few minutes.

usage: bg_capture.py <rom dir> <out prefix> [xend=3700]
"""
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gng import GnG  # noqa: E402

romdir, out = sys.argv[1], sys.argv[2]
xend = int(sys.argv[3]) if len(sys.argv) > 3 else 3700
g = GnG(romdir); m = g.mem
for f in range(1, 1501):                           # in play by ~frame 900 (Arthur at x 96)
    g.set_inputs(0x40 if 700 <= f <= 710 else (1 if 800 <= f <= 805 else 0), 0, 0)
    g.run_frame()
cols, pals = {}, []
y0 = m[0x509] << 8 | m[0x50A]
x = m[0x506] << 8 | m[0x507]
while x < xend:
    x += 2
    m[0x506], m[0x507], m[0x509], m[0x50A], m[0xAD] = x >> 8, x & 255, y0 >> 8, y0 & 255, 60
    g.set_inputs(0, 0, 0); g.run_frame()
    cam = m[0x9C] << 8 | m[0x9D]
    for c in range(cam // 16, cam // 16 + 17):
        i = (c & 31) * 32
        cols[c] = (bytes(m[0x2800 + i:0x2800 + i + 32]), bytes(m[0x2C00 + i:0x2C00 + i + 32]))
    if not pals:
        pals = [((m[0x3800 + i] >> 4) * 17, (m[0x3800 + i] & 15) * 17, (m[0x3900 + i] >> 4) * 17) for i in range(64)]
W = (max(cols) + 1) * 16
idx = [[0] * W for _ in range(256)]
for c, (codes, attrs) in cols.items():
    for r in range(16):
        code, attr = codes[r] | (attrs[r] & 0xC0) << 2, attrs[r]
        for py in range(16):
            for px in range(16):
                v = g._tile(code, 15 - px if attr & 0x10 else px, 15 - py if attr & 0x20 else py)
                idx[r * 16 + py][c * 16 + px] = (attr & 7) * 8 + v
pickle.dump(dict(cols=cols, pal=pals, idx=idx), open(out + '.pkl', 'wb'))
try:
    from PIL import Image
    im = Image.new('RGB', (W, 256))
    im.putdata([pals[v] for row in idx for v in row])
    im.save(out + '.png')
except ImportError:
    pass
print('columns 0-%d captured' % max(cols))
