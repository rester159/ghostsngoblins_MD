"""Dump a stage's terrain map (the port's map descriptors, src_patch/terrain.c)
as text: one cell per 3 chars, `#` wall (right/left probe table $1486E/$1496E,
no attribute bits $C0), `:` attribute bits $C0, then the tile byte in hex.

usage: fb_mapdump.py <rom> <stage 1-7> [x0 x1 y0 y1 in pixels]   (rows top first)"""
import struct
import sys

MAPS = (0x18254, 0x125A70, 0x211B20, 0x23CCC4, 0x249644, 0x255C74, 0x25E994)


def load(rom, stage):
    x0, y0, w, h, t, a = struct.unpack('>HHHHII', rom[MAPS[stage - 1]:MAPS[stage - 1] + 16])
    def cell(cx, cy):                   # world cell column / row (rows up from the bottom)
        i, j = cx - x0, cy - y0
        if not (0 <= i < w and 0 <= j < h):
            return None
        return rom[t + i * h + j], rom[a + i * h + j]
    return (x0, y0, w, h), cell


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    (x0, y0, w, h), cell = load(rom, int(sys.argv[2]))
    R, L = rom[0x1486E:0x1496E], rom[0x1496E:0x14A6E]
    if len(sys.argv) > 6:
        c0, c1, r0, r1 = (int(v) // 16 for v in sys.argv[3:7])
    else:
        c0, c1, r0, r1 = x0, x0 + w - 1, y0, y0 + h - 1
    print('stage map: columns %d-%d rows %d-%d' % (x0, x0 + w - 1, y0, y0 + h - 1))
    print('      ' + ''.join('%-3d' % (c % 1000) if c % 4 == 0 else '   ' for c in range(c0, c1 + 1)))
    for r in range(r1, r0 - 1, -1):
        row = ''
        for c in range(c0, c1 + 1):
            v = cell(c, r)
            if v is None:
                row += '   '
                continue
            tt, aa = v
            k = '#' if (R[tt] or L[tt]) and not aa & 0xC0 else ':' if aa & 0xC0 else ' '
            row += k + ('%02x' % tt if tt else '..')
        print('%5d ' % (r * 16) + row)
