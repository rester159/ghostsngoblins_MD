"""Firebrand's wing pickup: a 16x16 golden feathered wing, three rows of
feathers (sprite palette line 0: 1 black, 12 cream, 7 orange, 5 dark
orange; gold like the game's treasure, so it reads as a prize), drawn where
the game draws the torch pickup (item frames $0A-$0D, firebrand.c
fb_item_art). The item streamer uploads 256 bytes a frame; a single 16x16
piece uses the first 128, in sprite column order (top left, bottom left,
top right, bottom right).

usage: wing.py <art dir>   (writes firebrand_wing.bin, 0x100 bytes)"""
import os
import sys

K = {'.': 0, 'k': 1, 'l': 12, 'm': 7, 'd': 5}
WING = """
...........kkk..
.........kklllk.
.......kklllmmk.
.....kkllllmmmk.
...kklllllmmmdk.
..kllllllmmmmdk.
.kdddddkmmmmmdk.
..kklllllmmmddk.
...kdddddkmmmdk.
....kklllllmmdk.
.....kdddddkmdk.
......kklllllk..
.......kddddk...
........kkkk....
................
................"""


def encode():
    rows = WING.strip('\n').split('\n')
    assert len(rows) == 16 and all(len(r) == 16 for r in rows)
    out = b''
    for tx, ty in ((0, 0), (0, 1), (1, 0), (1, 1)):     # column order
        for y in range(8):
            r = rows[ty * 8 + y][tx * 8:tx * 8 + 8]
            out += bytes(K[r[i]] << 4 | K[r[i + 1]] for i in range(0, 8, 2))
    return out + bytes(0x80)


if __name__ == '__main__':
    data = encode()
    assert len(data) == 0x100
    open(os.path.join(sys.argv[1], 'firebrand_wing.bin'), 'wb').write(data)
