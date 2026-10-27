#!/usr/bin/env python3
"""The arcade's princess-scene sprites (rom/gg12-gg17, 16x16 4bpp, MAME gng
layout) -> Genesis 4bpp sprite tiles in the port's palette line 0 (ending.c).

Pieces (arcade sprite codes, from its sprite RAM during the scene; palette
row 2 the princess, 0 Arthur):
  walk0  566/574   walk1  567/575       (16x32, script $7C7C)
  hug_p  550 551 / 558 559              (32x32, the princess's embrace, $7C86)
  hug_a  629 630 / 637 638              (32x32, Arthur's embrace, $7F8D)
  heart  char $60 of gg1 (fg layer, attribute 5; $7F95)
and the ending's texts in their colours (build/endfont.h).
Arthur's pieces go to the port's palette line 0 (his colours, which are the
arcade's row 0: his art maps exactly). The princess's (row 2) go to line 2
with her own 15 colours (prin_line2, pen p -> entry p + 1; 4 bits a channel
halved to the Genesis' 3): in the final room no pixel of the planes on the
screen uses line 2 (counted per pixel from the room's VRAM during the scene:
its tiles use lines 1 and 3, the HUD and the texts lines 0 and 3), and no
sprite there but hers, so ending.c loads it at the scene's start.
The heart and the texts are the arcade's chars in the colours the port's HUD
font gives the same arcade colours."""
import os
import sys
rom, dst = sys.argv[1], sys.argv[2]
rd = lambda n: open('%s/%s' % (rom, n), 'rb').read()
ff = b'\xff' * 0x4000
SPR = b''.join((rd('gg17.bin'), rd('gg16.bin'), rd('gg15.bin'), ff, rd('gg14.bin'), rd('gg13.bin'), rd('gg12.bin'), ff))
CHR = rd('gg1.bin')
# the arcade's sprite palette rows 0 and 2 (R, G, B; 0-15) in the final room
ARC = {
    0: [(0, 6, 11), (0, 0, 0), (12, 10, 8), (10, 8, 6), (7, 5, 0), (5, 4, 0), (8, 8, 10), (6, 6, 8),
        (4, 4, 6), (9, 9, 0), (8, 4, 0), (6, 0, 0), (10, 10, 12), (12, 0, 0), (12, 7, 0), (0, 0, 0)],
    2: [(10, 7, 14), (0, 0, 0), (6, 0, 0), (8, 0, 0), (10, 0, 0), (10, 5, 0), (11, 9, 6), (9, 7, 5),
        (5, 5, 5), (7, 7, 7), (9, 9, 9), (11, 11, 11), (5, 0, 8), (6, 3, 9), (8, 5, 12), (0, 0, 0)],
}
# the port's palette line 0 in the final room (CRAM, BGR 3 bits each)
L0 = [0x000, 0x000, 0x003, 0x006, 0x00A, 0x00C, 0x013, 0x01E, 0x024, 0x0C9, 0x0E5, 0x11B, 0x12E, 0x158, 0x164, 0x1AD]
PORT = [(c & 7, c >> 3 & 7, c >> 6 & 7) for c in L0]


def nearest(rgb):
    return min(range(1, 16), key=lambda i: sum((a - b) ** 2 * w for a, b, w in zip(rgb, PORT[i], (3, 4, 2))))


def spr(code, px, py):
    o = code * 64 + py * 2 + (32 if px >= 8 else 0) + ((px & 7) >> 2)
    bit = 3 - (px & 3)
    lo, hi = SPR[o], SPR[0x10000 + o]
    return ((lo >> (bit + 4)) & 1) | (((lo >> bit) & 1) << 1) | (((hi >> (bit + 4)) & 1) << 2) | (((hi >> bit) & 1) << 3)


def image(pieces):
    w = max(dx for _, _, dx, _ in pieces) + 16
    h = max(dy for _, _, _, dy in pieces) + 16
    img = [[0] * w for _ in range(h)]
    for code, row, dx, dy in pieces:
        for py in range(16):
            for px in range(16):
                p = spr(code, px, py)
                if p != 15:
                    img[dy + py][dx + px] = p + 1 if row == 2 else nearest(tuple(v >> 1 for v in ARC[row][p]))
    return img


def chr_pen(code, px, py):
    b = CHR[code * 16 + py * 2 + px // 4]; bit = 3 - (px % 4)
    return ((b >> (bit + 4)) & 1) | (((b >> bit) & 1) << 1)


# The arcade's fg colours of the ending's texts and hearts (R, G, B; 0-15), drawn
# as the port's own HUD font draws the same colours (its PLAYER, TOP SCORE, TIME
# and score digits: arcade pens 1 and 2 -> these port indexes, read from its VRAM
# in the final room); pen 0 to the nearest colour of line 0, pen 3 transparent.
FG_ARC = {0: [(12, 12, 10), (14, 12, 0), (6, 5, 0)], 4: [(0, 0, 0), (14, 14, 13), (5, 5, 4)],
          5: [(15, 0, 6), (15, 8, 8), (4, 4, 4)], 8: [(15, 0, 6), (15, 0, 6), (4, 4, 4)],
          9: [(6, 6, 15), (9, 9, 15), (4, 4, 4)], 11: [(5, 15, 15), (8, 15, 15), (4, 4, 4)]}
FG_PORT = {0: (0, {1: 7, 2: 6}), 4: (0, {1: 15, 2: 9}), 5: (0, {1: 12, 2: 9}), 8: (0, {1: 3, 2: 9}),
           9: (0, {2: 9}), 11: (3, {1: 15, 2: 4})}


def fg_map(colour):
    """(line, {arcade pen: port index}) of an arcade fg colour"""
    line, m = FG_PORT[colour]
    m = dict(m)
    for pen in range(3):
        if pen not in m:                # (line 3: only its 15 and 4 are the HUD's)
            m[pen] = nearest(tuple(v >> 1 for v in FG_ARC[colour][pen])) if line == 0 else 15
    m[3] = 0
    return line, m


def heart():
    """the heart (char $60, colour 5), as the HUD draws colour 5"""
    line, m = fg_map(5)
    return [[m[chr_pen(0x60, px, py)] for px in range(8)] for py in range(8)]


def tiles(img):
    """Sprite tile order: columns of 8x8 tiles, top to bottom."""
    out = []
    for tx in range(len(img[0]) // 8):
        for ty in range(len(img) // 8):
            for y in range(8):
                r = img[ty * 8 + y][tx * 8:tx * 8 + 8]
                out.append(bytes((r[i] << 4) | r[i + 1] for i in range(0, 8, 2)))
    return b''.join(out)


FRAMES = [('walk0', [(566, 2, 0, 0), (574, 2, 0, 16)]),
          ('walk1', [(567, 2, 0, 0), (575, 2, 0, 16)]),
          ('hug_p', [(550, 2, 0, 0), (558, 2, 0, 16), (551, 2, 16, 0), (559, 2, 16, 16)]),
          ('hug_a', [(629, 0, 0, 0), (637, 0, 0, 16), (630, 0, 16, 0), (638, 0, 16, 16)])]
data = b''.join(tiles(image(p)) for _, p in FRAMES) + tiles(heart())

# The ending's texts in the arcade's colours (ending.c end_tupload): per colour,
# the arcade's chars (gg1, its fg font) of the letters its texts in that colour
# use, as Genesis tiles, uploaded to VRAM $AF00 (tiles $578-$5FD: Astaroth's
# art, unused after his removal; the port's one-colour font went to $6000, where
# Arthur's frame is uploaded too).
TEXTS = {8: ['THIS ROOM IS AN ILLUSION AND', 'IS A TRAP DEVISED BY SATAN.'], 9: ['GO AHEAD DAUNTLESSLY !'],
         4: ['MAKE RAPID PROGRES !', "FIREBRAND'S QUEST PLUS"], 0: ['CONGRATULATION'], 5: ['THIS STORY IS HAPPY END.', 'RETURN TO STARTING POINT'],
         11: ['BEING THE WISE AND COURAGEOUS', 'KNIGHT THAT YOU ARE, YOU', 'FEEL STRONGTH WELLING', 'IN YOUR BODY.',
              'CHALLENGE AGAIN !',
              'THE RED ARREMER HAS', 'DEFEATED ASTAROTH.']}       # these and the next: Firebrand's ending
TEXTS[9].append('A HARDER QUEST AWAITS !')
SLOTS = [0, 4, 5, 8, 9, 11]
font, glyph = [], []
for colour in SLOTS:
    line, m = fg_map(colour)
    g = [0] * 64
    for ch in sorted(set(''.join(TEXTS[colour])) - {' '}):
        img = [[m[chr_pen(ord(ch), px, py)] for px in range(8)] for py in range(8)]
        font.append(tiles(img))
        g[ord(ch) - 32] = len(font)
    glyph.append(g)
assert len(font) <= 0x5FE - 0x578
fdata = b''.join(font)
with open(os.path.join(os.path.dirname(dst), 'endfont.h'), 'w') as f:
    f.write("/* generated by mkprincess.py: the ending's texts in the arcade's colours (ending.c) */\n")
    f.write('#define END_FONT_TILES %d\n' % len(font))
    f.write('static const u16 end_font[%d] __attribute__((aligned(2))) = {\n' % (len(fdata) // 2))
    for i in range(0, len(fdata), 32):
        f.write('    ' + ', '.join('0x%04X' % (fdata[k] << 8 | fdata[k + 1]) for k in range(i, min(i + 32, len(fdata)), 2)) + ',\n')
    f.write('};\n')
    f.write('/* the arcade colours 0 4 5 8 9 11: the line, then per char 32-95 the tile (1-based, 0 none) */\n')
    f.write('static const u8 end_slot_line[6] = { %s };\n' % ', '.join(str(fg_map(c)[0]) for c in SLOTS))
    f.write('static const u8 end_glyph[6][64] = {\n%s\n};\n' % ',\n'.join('    { %s }' % ', '.join(map(str, g)) for g in glyph))
    f.write('/* the princess\'s colours (the arcade\'s sprite row 2), palette line 2 */\n')
    f.write('static const u16 prin_line2[16] = { 0, %s };\n' % ', '.join(
        '0x%03X' % ((b >> 1) << 9 | (g >> 1) << 5 | (r >> 1) << 1) for r, g, b in ARC[2][:15]))
with open(dst, 'w') as f:
    f.write('| generated by mkprincess.py from rom/gg12-gg17 and gg1 (%d tiles:\n' % (len(data) // 32))
    f.write('| walk0 0-7, walk1 8-15, hug_p 16-31, hug_a 32-47, heart 48)\n')
    for i in range(0, len(data), 16):
        f.write('    .byte ' + ','.join('0x%02x' % b for b in data[i:i + 16]) + '\n')
