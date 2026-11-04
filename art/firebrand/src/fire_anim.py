"""Firebrand's flying fireball as Demon's Crest animates it: its four shapes
(dc/shot.json captures 22, 23, 26, 29; each shown 3 frames, then the next),
each in fire.py's shot layout (32x16, pointing left, two 16x16 pieces stored
mirrored), for firebrand.c to cycle. Demon's Crest's colours mapped to sprite
palette line 0 (1 black, 2 dark red, 3 red, 5 dark orange, 7 orange, 10 tan,
12 cream); each shape kept at its captured height relative to the others.

usage: fire_anim.py <art dir>   (writes firebrand_fire_anim.bin, 4 x 0x100 bytes)"""
import json
import os
import sys

import fire

HERE = os.path.dirname(os.path.abspath(__file__))
SHAPES = (22, 23, 26, 29)
COLOUR = {0: 0, 1: 1, 2: 2, 3: 3, 4: 5, 5: 7, 6: 10, 7: 12}
X0, TOP = 3, 158                    # the ball's head at x 3; capture y 158 = row 0


def image(cap):
    g = [[0] * 32 for _ in range(16)]
    y0 = cap['box'][1] - TOP
    for y, row in enumerate(cap['rows']):
        for x, ch in enumerate(row):
            if ch != '0':
                assert 0 <= y0 + y < 16 and X0 + x < 32
                g[y0 + y][X0 + x] = COLOUR[int(ch, 16)]
    return g


def encode():
    caps = {c['first']: c for c in json.load(open(os.path.join(HERE, '..', 'dc', 'shot.json')))}
    out = b''
    for k in SHAPES:
        g = image(caps[k])
        out += fire.piece(g, 0) + fire.piece(g, 16)
    return out


if __name__ == '__main__':
    data = encode()
    assert len(data) == 0x400
    open(os.path.join(sys.argv[1], 'firebrand_fire_anim.bin'), 'wb').write(data)
    for k in SHAPES:
        caps = {c['first']: c for c in json.load(open(os.path.join(HERE, '..', 'dc', 'shot.json')))}
        print('\n'.join(''.join('%x' % c if c else '.' for c in r) for r in image(caps[k])), '\n')
