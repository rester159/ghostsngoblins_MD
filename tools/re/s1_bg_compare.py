"""Stage 1's background in the port against the arcade's.

The port draws stage 1 on plane B from one tile set loaded at the stage start
(VRAM tiles 1-588 from $C062) and one 64-colour palette ($13FE2, lines 1-3 for
the background; line 0 and part of line 2 are the sprites'). The map is one
256-byte record per 16 px column at $19E64 (two 8 px tile columns of 32 rows,
each followed by 64 unused bytes), streamed a column at a time by $944A/$94D8;
every entry already holds its palette line.

This renders that map from the ROM, lines it up with the arcade's (captured by
tools/arcade/bg_capture.py; same world coordinates, port plane row = arcade
pixel row), and prints:
  - per section (graveyard < 1700, forest < 2816, after the last puddle) and
    palette line: pixels and mean RGB error (linear 3-bit levels k*255/7);
  - line-1 tiles by the sections that use them;
  - for every background CRAM entry: the arcade colour its pixels show, the
    port's 3-bit colour and the nearest 3-bit colour.

usage: s1_bg_compare.py <port rom .bin> <arcade capture .pkl> [out.png]
(out.png: the whole stage, arcade above, port below)
"""
import pickle
import sys
from collections import Counter, defaultdict

rom = open(sys.argv[1], 'rb').read()
A = pickle.load(open(sys.argv[2], 'rb'))
aidx, apal = A['idx'], A['pal']
MAP, NCOL, TILES, PAL = 0x19E64, 224, 0xC062, 0x13FE2
B1, B2 = 1700, 2816
sec = lambda x: 0 if x < B1 else (1 if x < B2 else 2)
lv = lambda k: round(k * 255 / 7)
rgb3 = []
for i in range(64):
    w = rom[PAL + 2 * i] << 8 | rom[PAL + 2 * i + 1]
    rgb3.append((w >> 1 & 7, w >> 5 & 7, w >> 9 & 7))
tile = lambda t: rom[TILES + (t - 1) * 32:TILES + t * 32] if 1 <= t <= 588 else bytes(32)

err = defaultdict(float); cnt = Counter()
src = defaultdict(Counter)                     # CRAM entry -> arcade colours of its pixels
users = defaultdict(set)                       # line-1 tile -> sections
port = {}
for c in range(NCOL):
    rec = rom[MAP + c * 256:MAP + c * 256 + 256]
    for half in (0, 1):
        for row in range(32):
            o = half * 128 + row * 2
            e = rec[o] << 8 | rec[o + 1]
            t, p, hf, vf = e & 0x7FF, e >> 13 & 3, e >> 11 & 1, e >> 12 & 1
            if p == 1:
                users[t].add(sec(c * 16))
            d = tile(t)
            for y in range(8):
                Y = row * 8 + y
                for x in range(8):
                    xx, yy = (7 - x if hf else x), (7 - y if vf else y)
                    b = d[yy * 4 + xx // 2]; v = b >> 4 if xx % 2 == 0 else b & 15
                    X = c * 16 + half * 8 + x
                    pc = tuple(lv(k) for k in rgb3[p * 16 + v]) if v else (0, 0, 0)
                    port[X, Y] = pc
                    if not 16 <= Y < 240:
                        continue
                    ac = apal[aidx[Y][X]]
                    err[sec(X), p] += sum((a - b) ** 2 for a, b in zip(ac, pc)) ** 0.5
                    cnt[sec(X), p] += 1
                    if v:
                        src[p * 16 + v][ac] += 1
for k in sorted(cnt):
    print('section %s line %d: %6d px, mean error %.1f' % ('ABC'[k[0]], k[1], cnt[k], err[k] / cnt[k]))
print('line-1 tiles by sections using them:',
      dict(Counter(''.join('ABC'[s] for s in sorted(v)) for v in users.values())))
near = lambda c8: min(range(8), key=lambda k: abs(k * 255 / 7 - c8))
diff = 0
for i in sorted(src):
    ac, n = src[i].most_common(1)[0]
    want = tuple(near(v) for v in ac)
    diff += want != rgb3[i]
    print('line %d idx %2d: port %s, arcade %s (%d px%s), nearest %s%s' % (
        i // 16, i % 16, rgb3[i], tuple(v // 17 for v in ac), n,
        ', +%d more colours' % (len(src[i]) - 1) if len(src[i]) > 1 else '', want,
        '' if want == rgb3[i] else '  <-'))
print('%d of %d background entries are not the nearest 3-bit colour' % (diff, len(src)))
if len(sys.argv) > 3:
    from PIL import Image
    im = Image.new('RGB', (NCOL * 16, 448))
    for (X, Y), pc in port.items():
        if 16 <= Y < 240:
            im.putpixel((X, Y + 208), pc)
            if X < len(aidx[0]):
                im.putpixel((X, Y - 16), apal[aidx[Y][X]])
    im.save(sys.argv[3])
