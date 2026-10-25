"""Decode the game's Red Arremer frames (71 x 0x300 at $60000, layout table at
$506AE/$5073C) into 48x32 colour-index images on Arthur's anchor (x -24..24)."""
import struct

FRAMES = 0x60000
LAYOUT_IDX, LAYOUT = 0x506AE, 0x5073C
W, H = 48, 32


def layout(rom, k):
    w = lambda a: struct.unpack('>h', rom[a:a + 2])[0]
    a = LAYOUT + w(LAYOUT_IDX + 2 * k)
    return [(w(a + 2 + 6 * i), w(a + 4 + 6 * i), w(a + 6 + 6 * i) & 0xFFFF)
            for i in range(w(a))]


def tile(rom, a):
    return [[(rom[a + y * 4 + x // 2] >> (4 if x % 2 == 0 else 0)) & 15
             for x in range(8)] for y in range(8)]


def frame(rom, k):
    """48x32 image, x = dx + 24 (so Arthur's 32x32 slot is columns 8..39)."""
    g = [[0] * W for _ in range(H)]
    for dx, dy, attr in layout(rom, k):
        piece = (attr & 0x7FF) - 0x398           # tiles from the frame's start
        hf = attr >> 11 & 1
        src = FRAMES + k * 0x300 + piece * 32
        for tx in range(2):
            for ty in range(2):
                t = tile(rom, src + (tx * 2 + ty) * 32)
                for y in range(8):
                    for x in range(8):
                        c = t[y][x]
                        if not c:
                            continue
                        px = (1 - tx if hf else tx) * 8 + (7 - x if hf else x)
                        X, Y = dx + 24 + px, dy + ty * 8 + y
                        if 0 <= X < W and 0 <= Y < H:
                            g[Y][X] = c
    return g


def mirror(g):
    return [row[::-1] for row in g]
