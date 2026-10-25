"""Game updates per video frame between two RAM dumps of a probe_rom.py build
(update counter $FF2BF4, frame counter $FF7DFC).

usage: update_rate.py <ram dump A> <ram dump B>"""
import sys


def rd(path, a, n=4):
    raw = open(path, 'rb').read()
    return int.from_bytes(bytes(raw[(a - 0xFF0000 + k) ^ 1] for k in range(n)), 'big')


u = rd(sys.argv[2], 0xFF2BF4) - rd(sys.argv[1], 0xFF2BF4)
f = rd(sys.argv[2], 0xFF7DFC) - rd(sys.argv[1], 0xFF7DFC)
print('%d updates in %d frames: %.3f per frame' % (u, f, u / f))
