"""Firebrand's fireball for the shots: the user's reference fireball (21x8,
pointing left), taken pixel by pixel from their 2x capture and mapped to sprite
palette line 0 (2 dark red, 3 red, 5 dark orange, 7 orange, 10 tan, 12 cream).

A shot is two 16x16 pieces. Flying left the game shows [mirror(piece 0)]
[mirror(piece 1)]; flying right it shows [piece 0][piece 1], and firebrand.c
swaps the two pieces' positions for those, so the 32x16 image F (pointing left)
is stored as piece 0 = mirror(F[0:16]), piece 1 = mirror(F[16:32]).

usage: fire.py   (prints the 32x16 image)"""

FIREBALL = [
    '...257775.....722....',
    '.5aca77522.....5775..',
    'accccaaca752..7527a72',
    'acccccccca752.5..5a52',
    'acccccccc7752....5a52',
    '7ccc77aa72222...57772',
    '.5aca722.5255...25...',
    '..257a75.......552...',
]
X0, Y0 = 3, 0                       # at the mouth of his firing pose (row 10 of his frame)


def image():
    g = [[0] * 32 for _ in range(16)]
    for y, row in enumerate(FIREBALL):
        for x, ch in enumerate(row):
            if ch != '.':
                g[Y0 + y][X0 + x] = int(ch, 16)
    return g


def piece(g, x0):
    half = [row[x0:x0 + 16][::-1] for row in g]           # stored mirrored
    out = bytearray()
    for tx in range(2):
        for ty in range(2):
            for y in range(8):
                r = half[ty * 8 + y]
                for x in range(0, 8, 2):
                    out.append(r[tx * 8 + x] << 4 | r[tx * 8 + x + 1])
    return bytes(out)


def encode(rom=None):
    g = image()
    return piece(g, 0) + piece(g, 16)


if __name__ == '__main__':
    for row in image():
        print(''.join('%x' % c if c else '.' for c in row))
