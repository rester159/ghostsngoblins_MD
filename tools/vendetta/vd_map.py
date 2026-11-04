"""Firebrand's Vendetta's stage map, mirrored: Satan's lair on the left, the
graveyard on the right, the boxes numbered 1 (the lair) to 6 (the graveyard)
in the order he plays them. Built from the game's own map data in the ROM;
tools/patch_gng.py install_vd_map places the results and vendetta.c /
vendetta_glue.s use them on the map screen ($113B70) in Vendetta.

The map is plane B ($C000), its table at $265D54 (64 x 32 entries, tiles
loaded raw from $2607B4 to VRAM 0, none flipped), 400 px wide (columns
0-49), panned 0 -> 143 px. The marker (a 16x16 sprite, screen x = $FFC596)
comes from the table at $267E2A: (y, x) per stage, 7 stages, a second set
after the checkpoint. Stages 0-3 are placed at pan 0 and follow the pan;
4-6 (`cmpi.b #4,$FFC512`, $113D32 / $113D74) are placed at the full pan and
hidden until it ends.

Mirrored: every column c of 0-49 shows column 49 - c, horizontally flipped.
Each numbered box's digit (a 7 x 6 glyph in the game's style: e stroke, 1
shadow, on the box's c) is redrawn in the original tiles as the mirror image
of digit 7 - n, so that, flipped with the map, box n reads 7 - n. A marker at
map x m goes to 384 - m; it follows the pan if it fits the first screen
(<= 240), else it is placed at the full pan."""
import sys

TILES, NT, MARK = 0x2607B4, 0x265D54, 0x267E2A
COLS, PAN = 50, 143

# the boxes' digit areas in map pixels (x, y, w, h), box n = 1-6 (game stage n)
BOXES = {1: (88, 193, 7, 6), 2: (160, 193, 7, 6), 3: (209, 193, 8, 7), 4: (280, 193, 7, 6),
         5: (316, 177, 7, 7), 6: (316, 158, 7, 7)}
K = {'c': 12, 'e': 14, '1': 1}
GLYPHS = {
    1: ["ccec1cc", "ceec1cc", "c1ec1cc", "ccec1cc", "ccec1cc", "ceeec1c"],
    2: ["ccee1cc", "ce11e1c", "c11ce1c", "ccce1cc", "cce1ccc", "ceeee1c"],
    3: ["ceeee1c", "c11e11c", "ccee1cc", "cc11e1c", "ceee11c", "c111ccc"],
    4: ["ccce1cc", "cce1ccc", "ce1e1cc", "ce1e1cc", "ceeee1c", "c11e1cc"],
    5: ["ceeee1c", "ce1111c", "ceee1cc", "c111e1c", "ceee1cc", "c111ccc"],
    6: ["c1ee1cc", "ce11ccc", "ceee1cc", "ce11e1c", "c1ee1cc", "cc11ccc"],
}


def build(rom):
    """-> (mirrored table 4096 bytes, tile patches [(tile, 32 bytes)], marker table 28 bytes,
    far flags 14 bytes: 4 = placed at the full pan, 0 = follows it)"""
    nt = [int.from_bytes(rom[NT + 2 * i:NT + 2 * i + 2], 'big') for i in range(2048)]
    assert not any(e & 0x1800 for e in nt), 'the map has flipped cells'
    out = list(nt)
    for y in range(32):
        for c in range(COLS):
            out[y * 64 + c] = nt[y * 64 + COLS - 1 - c] ^ 0x0800
    table = b''.join(e.to_bytes(2, 'big') for e in out)

    tiles = {}

    def tile(t):
        if t not in tiles:
            tiles[t] = bytearray(rom[TILES + t * 32:TILES + t * 32 + 32])
        return tiles[t]

    uses = {}
    for e in nt:
        uses[e & 0x7FF] = uses.get(e & 0x7FF, 0) + 1

    def setpx(x, y, v):
        t = nt[(y // 8) * 64 + x // 8] & 0x7FF
        assert uses[t] == 1, 'tile $%x is used %d times' % (t, uses[t])
        d = tile(t)
        i = (y % 8) * 4 + (x % 8) // 2
        d[i] = (d[i] & 0x0F) | v << 4 if x % 2 == 0 else (d[i] & 0xF0) | v

    for n, (x0, y0, w, h) in BOXES.items():
        g = GLYPHS[7 - n]
        for y in range(h):
            for x in range(w):
                # shown flipped: painted column x is shown at w - 1 - x
                gx = w - 1 - x
                ch = g[y][gx] if y < 6 and gx < 7 else 'c'
                setpx(x0 + x, y0 + y, K[ch])
    patches = sorted((t, bytes(d)) for t, d in tiles.items())

    mark, far = bytearray(), bytearray()
    for i in range(14):
        s = i % 7
        y, x = rom[MARK + 2 * i], rom[MARK + 2 * i + 1]
        m = x + (PAN if s >= 4 else 0)
        m2 = COLS * 8 - 16 - m
        if m2 <= 256 - 16:
            mark += bytes((y, m2)); far.append(0)
        else:
            mark += bytes((y, m2 - PAN)); far.append(4)
    return table, patches, bytes(mark), bytes(far)


if __name__ == '__main__':
    t, p, m, f = build(open(sys.argv[1], 'rb').read())
    print('tiles patched:', ' '.join('$%x' % a for a, _ in p))
    print('marker', m.hex(), 'far', f.hex())
