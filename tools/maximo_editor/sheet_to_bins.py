"""Maximo's banks from the editor's PNG sheet ('PNG' button: 77 frames, 15 a row,
3x, 100 px cells from (4, 4), background rgb(44,50,66), palette index 1 = black).

Writes art/maximo/maximo_bank{A,B,C}.bin:
  A: A0-A10 (11 frames)
  B: the co-op layout from Arthur's $40000 (A0-A4, A7-A9, then B0-B64: 73 frames)
     src_patch/p2.c maps Arthur's frames onto it; patch_gng.py places it at $3C0000
  C: C0 (1 frame)
A5/A6/B0 are the game's copies of A3/A2/A10 and are written as those.

usage: sheet_to_bins.py <sheet.png> <art dir>"""
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FRAME, COUNT = 512, 77


def palette():
    js = open(os.path.join(HERE, 'maximo_data.js')).read()
    return json.loads(re.search(r'palette:(\[\[.*?\]\])', js).group(1))


def read(path):
    lut = {tuple(c): i for i, c in reversed(list(enumerate(palette()))) if i}
    lut[(44, 50, 66)] = 0
    im = Image.open(path).convert('RGB')
    assert im.size == (1504, 604), im.size
    px = im.load()
    out = []
    for i in range(COUNT):
        ox, oy = 4 + (i % 15) * 100, 4 + (i // 15) * 100
        g = []
        for y in range(32):
            for x in range(32):
                blk = {px[ox + x * 3 + dx, oy + y * 3 + dy] for dx in range(3) for dy in range(3)}
                assert len(blk) == 1 and next(iter(blk)) in lut, (i, x, y, blk)
                g.append(lut[blk.pop()])
        out.append(g)
    return out


def encode(g):
    out = bytearray()
    for tx in range(4):
        for ty in range(4):
            for y in range(8):
                for x in range(0, 8, 2):
                    r = (ty * 8 + y) * 32 + tx * 8 + x
                    out.append(g[r] << 4 | g[r + 1])
    return bytes(out)


def main(sheet, dst):
    f = read(sheet)
    for dup, src in ((5, 3), (6, 2), (11, 10)):
        if f[dup] != f[src]:
            print(f'note: frame {dup} differs from {src}; {src} is used')
        f[dup] = f[src]
    a = [encode(g) for g in f[:11]]
    b = [encode(g) for g in f[11:76]]
    bank_b = b''.join(a[k] for k in (0, 1, 2, 3, 4, 7, 8, 9)) + b''.join(b)
    open(os.path.join(dst, 'maximo_bankA.bin'), 'wb').write(b''.join(a))
    open(os.path.join(dst, 'maximo_bankB.bin'), 'wb').write(bank_b)
    open(os.path.join(dst, 'maximo_bankC.bin'), 'wb').write(encode(f[76]))
    print('A', len(a), 'B', len(bank_b) // FRAME, 'C 1')


if __name__ == '__main__':
    main(*sys.argv[1:3])
