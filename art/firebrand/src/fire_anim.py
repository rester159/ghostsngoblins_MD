"""Firebrand's flying fireball as Demon's Crest animates it: its four shapes
(dc/shot.json captures 22, 23, 26, 29; each shown 3 frames, then the next),
each in fire.py's shot layout (32x16, pointing left, two 16x16 pieces stored
mirrored), for firebrand.c to cycle; then its impact on a wall, three 16x16
pictures (captures 46, the burst; 67, the flame; 62, the sparks) for the
game's three hit-spark frames, each centred on the shot's line and stored
mirrored as a shot's first piece (0x100 bytes each, the rest blank).
Demon's Crest's colours mapped to sprite
palette line 0 (1 black, 2 dark red, 3 red, 5 dark orange, 7 orange, 10 tan,
12 cream); each shape kept at its captured height relative to the others.

usage: fire_anim.py <art dir>   (writes firebrand_fire_anim.bin, 7 x 0x100 bytes)"""
import json
import os
import sys

import fire

HERE = os.path.dirname(os.path.abspath(__file__))
SHAPES = (22, 23, 26, 29)
IMPACT = (46, 67, 62)
MID = 8                             # the shot's line: row 8 of its 16-row pieces
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


def impact(cap):
    """16x16, centred on the shot's line and across the piece"""
    rows = cap['rows']
    h, w = len(rows), len(rows[0])
    y0, x0 = MID - h // 2, (16 - w) // 2
    g = [[0] * 32 for _ in range(16)]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != '0':
                assert 0 <= y0 + y < 16 and 0 <= x0 + x < 16
                g[y0 + y][x0 + x] = COLOUR[int(ch, 16)]
    return g


def encode():
    caps = {c['first']: c for c in json.load(open(os.path.join(HERE, '..', 'dc', 'shot.json')))}
    out = b''
    for k in SHAPES:
        g = image(caps[k])
        out += fire.piece(g, 0) + fire.piece(g, 16)
    for k in IMPACT:
        out += fire.piece(impact(caps[k]), 0) + bytes(0x80)
    return out


if __name__ == '__main__':
    data = encode()
    assert len(data) == 0x700
    open(os.path.join(sys.argv[1], 'firebrand_fire_anim.bin'), 'wb').write(data)
    caps = {c['first']: c for c in json.load(open(os.path.join(HERE, '..', 'dc', 'shot.json')))}
    for g in [image(caps[k]) for k in SHAPES] + [impact(caps[k]) for k in IMPACT]:
        print('\n'.join(''.join('%x' % c if c else '.' for c in r) for r in g), '\n')
