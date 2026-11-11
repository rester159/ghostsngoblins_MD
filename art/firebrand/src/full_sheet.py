"""Every picture of Firebrand the game has, read back from the files tools/patch_gng.py puts
in the ROM (so it is the art as it plays), on one labelled sheet:

  - the 112 frames of firebrand_bank.bin (48x32 each, palette line from firebrand_flags.bin),
    named as in the pixel editor; frames the game never shows are dimmed and say why
    (the boot copies, Arthur's walking frames, which play the walk cycle instead, and the
    empty armour slots). The ladder is slots 70-73 (B59-B62): Climb A/B while climbing,
    Climb top A/B getting on and off at the top.
  - the fireball's four flight shapes and its three impact pictures (firebrand_fire_anim.bin)
  - the weapon-box fireball (firebrand_fire.bin), the stage-map marker (firebrand_mapicon.bin),
    the wing pickup (firebrand_wing.bin) and his frog (firebrand_frog.bin, 8 frames)

Also writes the 112 frames alone in the editor's "Export PNG sheet" layout, which the
editor's "Load PNG" and sheet_to_bank.py take back.

usage: full_sheet.py <art dir> <full sheet.png> [<editor sheet.png>]
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcade_sheet as a                         # noqa: E402
from PIL import Image, ImageDraw                 # noqa: E402

S = 3                                            # display scale


def tiles(data, cols, rows):
    """cols x rows 8x8 tiles stored column-major (4 bpp) -> pixel rows"""
    g = [[0] * (cols * 8) for _ in range(rows * 8)]
    k = 0
    for tx in range(cols):
        for ty in range(rows):
            for y in range(8):
                for x in range(0, 8, 2):
                    b = data[k]; k += 1
                    g[ty * 8 + y][tx * 8 + x] = b >> 4
                    g[ty * 8 + y][tx * 8 + x + 1] = b & 15
    return g


def bank_image(f):
    """a firebrand_bank.bin frame -> 48x32 (a.bank_frame's inverse)"""
    body, left, right = tiles(f[:0x200], 4, 4), tiles(f[0x200:0x280], 1, 4), tiles(f[0x280:0x300], 1, 4)
    return [left[y] + body[y] + right[y] for y in range(32)]


def mirror(g):
    return [r[::-1] for r in g]


def side(p, q):
    return [p[y] + q[y] for y in range(len(p))]


def main(art, out, editor=None):
    rd = lambda n: open(os.path.join(art, n), 'rb').read()
    bank, flags = rd('firebrand_bank.bin'), rd('firebrand_flags.bin')
    frames = [bank_image(bank[s * 0x300:(s + 1) * 0x300]) for s in range(a.COUNT)]
    lines = [2 if flags[s] & 4 else 0 for s in range(a.COUNT)]
    if editor:
        a.render(list(zip(frames, lines)), editor)

    def hidden(s):
        if s < 11:
            return 'boot copy'
        if s in a.EMPTY:
            return 'unused'
        if s < 84 and flags[s] & 8:
            return 'walk: cycle shown'
        return None

    cells = [(frames[s], lines[s], a.SLOT_NAMES[s], hidden(s)) for s in range(a.COUNT)]
    anim = rd('firebrand_fire_anim.bin')
    extra = []
    for k in range(4):                           # flying left: [mirror(piece 0)][mirror(piece 1)]
        p = anim[k * 0x100:(k + 1) * 0x100]
        extra.append((side(mirror(tiles(p[:0x80], 2, 2)), mirror(tiles(p[0x80:], 2, 2))), 0, 'Fireball %d' % (k + 1)))
    for k, n in enumerate(('burst', 'flame', 'sparks')):
        p = anim[(4 + k) * 0x100:(5 + k) * 0x100]
        extra.append((mirror(tiles(p[:0x80], 2, 2)), 0, 'Impact: ' + n))
    fire = rd('firebrand_fire.bin')
    extra.append((side(mirror(tiles(fire[:0x80], 2, 2)), mirror(tiles(fire[0x80:], 2, 2))), 0, 'Weapon box'))
    extra.append((tiles(rd('firebrand_mapicon.bin'), 2, 2), 0, 'Map marker'))
    extra.append((tiles(rd('firebrand_wing.bin')[:0x80], 2, 2), 0, 'Wing pickup'))
    frog = rd('firebrand_frog.bin')
    for k in range(8):
        extra.append((tiles(frog[k * 0x200:(k + 1) * 0x200], 4, 4), 0, 'Frog %d' % (k + 1)))

    CW, CH, LAB, COLS = 48 * S + 8, 32 * S + 8, 12, 12
    rows1 = (len(cells) + COLS - 1) // COLS
    rows2 = (len(extra) + COLS - 1) // COLS
    head = 18
    im = Image.new('RGB', (COLS * CW, head + rows1 * (CH + LAB) + head + rows2 * (CH + LAB) + 16), a.BG)
    d = ImageDraw.Draw(im)

    def cell(i, y0, g, line, name, note):
        pal = a.LINE2 if line == 2 else a.LINE0
        ox, oy = (i % COLS) * CW, y0 + (i // COLS) * (CH + LAB) + LAB
        d.text((ox + 2, oy - LAB), name + (' (%s)' % note if note else ''),
               fill=(130, 126, 140) if note else (225, 225, 225))
        d.rectangle([ox, oy, ox + 48 * S - 1, oy + 32 * S - 1], fill=(36, 33, 41) if note else (56, 52, 64))
        h, w = len(g), len(g[0])
        x0, y1 = ox + (48 - w) // 2 * S, oy + (32 - h) * S      # small pictures: centred, on the floor
        for y in range(h):
            for x in range(w):
                c = g[y][x]
                if c:
                    r = pal[c]
                    if note:
                        r = tuple((v + 2 * 44) // 3 for v in r)
                    d.rectangle([x0 + x * S, y1 + y * S, x0 + x * S + S - 1, y1 + y * S + S - 1], fill=r)

    d.text((4, 3), "Firebrand: the 112 frames of firebrand_bank.bin as in the game (editor slot names)", fill=(255, 220, 120))
    for i, (g, line, name, note) in enumerate(cells):
        cell(i, head, g, line, name, note)
    y2 = head + rows1 * (CH + LAB)
    d.text((4, y2 + 3), "Fireball, impact, weapon box, map marker, wing pickup and frog", fill=(255, 220, 120))
    for i, (g, line, name) in enumerate(extra):
        cell(i, y2 + head, g, line, name, None)
    d.text((4, im.size[1] - 13), a.CREDIT, fill=(200, 200, 200))
    im.save(out)


if __name__ == '__main__':
    main(*sys.argv[1:4])
