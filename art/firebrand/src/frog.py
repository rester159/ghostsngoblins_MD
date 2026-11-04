"""Firebrand's frog: the game's frog frames ($49200-$4A000, 8 frames of 0x200)
recoloured red like him, for firebrand.c to show in their place. The frog's
blue-grey body takes his reds (9 -> 2 dark red, 11 -> 3 red, 14 -> 7 orange)
and its red belly his warm lights (2 -> 4, 3 -> 7, 4 -> 5, 5 -> 10, 7 -> 12).

usage: frog.py <rom (fixed build)> <art dir>   (writes firebrand_frog.bin, 0x1000 bytes)"""
import os
import sys

FROG, COUNT = 0x49200, 8
MAP = {9: 2, 11: 3, 14: 7, 2: 4, 3: 7, 4: 5, 5: 10, 7: 12}


def recolour(data):
    m = lambda c: MAP.get(c, c)
    return bytes(m(b >> 4) << 4 | m(b & 15) for b in data)


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    out = recolour(rom[FROG:FROG + COUNT * 0x200])
    open(os.path.join(sys.argv[2], 'firebrand_frog.bin'), 'wb').write(out)
