"""Firebrand's wing pickup: a pair of small wings spread from a brown centre,
16x16, in Red Arremer's colours: red wings (sprite palette line 0: 3 red,
2 dark red) with orange leading edges (7), a dark orange centre (5) and a
black outline (1), drawn
where the game draws the torch pickup (item frames $0A-$0D, firebrand.c
fb_item_art). The item streamer uploads 256 bytes a frame; a single 16x16
piece uses the first 128, in sprite column order (top left, bottom left,
top right, bottom right).

usage: wing.py <art dir>   (writes firebrand_wing.bin, 0x100 bytes)"""
import os
import sys

K = {'.': 0, 'H': 7, 'L': 3, 'M': 2, 'D': 1, 'B': 5, 'b': 2}
WING = """
................
................
................
D..............D
DD............DD
DHD..........DHD
DHLD........DLHD
DHLLD..bb..DLLHD
.DHLLDbBBbDLLHD.
.DHLLLbBBbLLLHD.
..DLMLDbbDLMLD..
..DMDMD..DMDMD..
...D.D....D.D...
................
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
