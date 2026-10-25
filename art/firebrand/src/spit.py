"""Firebrand's side-facing spit: three frames drawn over his right-facing stand
pose (Arremer frame 4): mouth opening, spitting (mouth wide, a flash in front
of it), closing. Coordinates are in the 48x32 frame (Arthur's slot is x 8-39).

usage: spit.py <rom>   (prints the head of each frame)"""
import sys
from arremer import frame

BASE = 4                            # right-facing stand
# palette line 0: 1 black, 2 dark red, 3 red, 7 orange, 12 cream
MOUTH = {                           # the mouth sits under the eye slits (rows 7-8)
    'open': {(26, 9): 1, (27, 9): 1, (28, 9): 1, (27, 10): 2},
    'spit': {(25, 9): 1, (26, 9): 7, (27, 9): 12, (28, 9): 7, (29, 9): 1,
             (26, 10): 1, (27, 10): 1, (28, 10): 1,
             (30, 9): 7, (31, 9): 12, (32, 9): 7, (31, 8): 7, (33, 9): 3, (32, 8): 3},
    'close': {(27, 9): 1, (28, 9): 1},
}
ORDER = ['open', 'spit', 'close']


def frames(rom):
    out = []
    for name in ORDER:
        g = [row[:] for row in frame(rom, BASE)]
        for (x, y), c in MOUTH[name].items():
            g[y][x] = c
        out.append(g)
    return out


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    for name, g in zip(ORDER, frames(rom)):
        print(name)
        for row in g[:14]:
            print(''.join('%x' % c if c else '.' for c in row[16:36]))
