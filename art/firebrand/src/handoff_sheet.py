"""Firebrand's art for an artist to touch up and complete: one sheet in three parts.

  WORKS    every picture the game shows that is right, once (frames the game shows
           in several places are one picture; facing left is the mirror image, made
           from the right-facing one), with what it is used for
  BROKEN   pictures that are there but wrong, as they look now, and what is wrong
  MISSING  empty boxes for pictures the game needs and has none of, with what to draw

Read from the art files tools/patch_gng.py puts in the ROM (firebrand_bank.bin and
the rest in art/firebrand), so it is the art as it plays.

The climbing boxes show Arthur's own ladder frames, dimmed, as a guide to the poses and
timing (read from the built ROM, default build/GhostsNGoblins_fixed.bin).

Also writes <out>_raw.png: the same grid at 1x, no text, every frame a 48x32 box at its
real pixels, transparent where the sprite is (colour 0), with 2 px gutters and a 2 px
bar in the section's colour above each part. The labelled sheet is its key.

usage: handoff_sheet.py <art dir> <out.png> [<rom>]
"""
import os
import sys
import textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcade_sheet as a                         # noqa: E402
import full_sheet as fs                          # noqa: E402
from PIL import Image, ImageDraw                 # noqa: E402

S = 4
BOX_W, BOX_H = 48 * S, 32 * S
CW, TEXT, COLS = BOX_W + 16, 64, 7
CH = BOX_H + TEXT + 16
GREEN, ORANGE, RED = (90, 190, 110), (235, 160, 60), (230, 80, 80)

DESC = {
    'stand': 'Standing still.',
    'jump': 'Jumping forward.', 'jump2': 'Jumping straight up.',
    'fire': 'Spitting a fireball, standing or in the air.',
    'windup': 'The moment before the spit.',
    'crouch': 'Crouching.', 'crouchfire': 'Spitting while crouched.',
    'land': 'Landing from a jump.', 'hit': 'Hit by an enemy: knocked back (facing right).',
}


def meaning(s):
    """what the game shows slot s for"""
    if s in a.FLAMES:
        return 'flames'
    if s < 84:
        t = a.BOOT[s] if s < 11 else s
        if t in a.RUN_R or t in a.RUN_L:
            return 'stand'
        return a.CLASS[t][0]
    if s < 96:
        return 'walk %d' % ((s - 84) % 6 + 1)
    if s < 108:
        return 'hover %d' % ((s - 96) % 6 + 1)
    return ('cling', 'cling', 'cling fire', 'cling fire')[s - 108]


NAME = {'stand': 'Stand', 'jump': 'Jump forward', 'jump2': 'Jump straight up', 'fire': 'Spit',
        'windup': 'Spit wind-up', 'crouch': 'Crouch', 'crouchfire': 'Crouching spit', 'land': 'Land',
        'hit': 'Hit', 'cling': 'Wall cling', 'cling fire': 'Wall cling spit'}


def describe(names):
    """(title, text) for the poses one picture is shown for"""
    poses = [n for n in names if not n.startswith(('walk', 'hover'))]
    walk = [n[5:] for n in names if n.startswith('walk')]
    hover = [n[6:] for n in names if n.startswith('hover')]
    parts, title = [], []
    for n in poses:
        title.append(NAME.get(n, n))
        if n in DESC:
            parts.append(DESC[n] if n != 'stand' else 'Standing still.')
        elif n == 'cling':
            parts.append('Holding on to a wall (wall on his left).')
        elif n == 'cling fire':
            parts.append('Spitting while holding on to a wall.')
    if walk:
        title.append('Walk ' + '/'.join(walk))
        parts.append('Walk cycle, step%s %s of 6.' % ('s' if len(walk) > 1 else '', ', '.join(walk)))
    if hover:
        title.append('Hover ' + '/'.join(hover))
        parts.append('Hovering (flying), wing beat%s %s of 6.' % ('s' if len(hover) > 1 else '', ', '.join(hover)))
    return ' + '.join(title), ' '.join(parts)


def arthur(rom, s):
    """Arthur's own picture for bank slot s (32x32 at $40000 + (s-11)*0x200)"""
    o = 0x40000 + (s - 11) * 0x200
    return fs.tiles(rom[o:o + 0x200], 4, 4)


def write_raw(parts, out):
    """the sheet at 1x: frames only, in the labelled sheet's order"""
    G = 2
    rows = [(len(items) + COLS - 1) // COLS for _, _, items in parts]
    w = G + COLS * (48 + G)
    h = sum(G + G + r * (32 + G) for r in rows)
    im = Image.new('RGBA', (w, h), a.BG + (255,))
    y = 0
    for (name, col, items), r in zip(parts, rows):
        im.paste(col + (255,), (0, y, w, y + G))
        y0 = y + G + G
        for i, (g, ln, _, _) in enumerate(items):
            ox, oy = G + (i % COLS) * (48 + G), y0 + (i // COLS) * (32 + G)
            im.paste((0, 0, 0, 0), (ox, oy, ox + 48, oy + 32))
            dim = isinstance(g, tuple)
            if dim:
                g = g[1]
            if g is None:
                continue
            pal = a.LINE2 if ln == 2 else a.LINE0
            gh, gw = len(g), len(g[0])
            x0, y1 = ox + (48 - gw) // 2, oy + 32 - gh
            for yy in range(gh):
                for xx in range(gw):
                    c = g[yy][xx]
                    if c:
                        rgb = pal[c]
                        if dim:
                            rgb = tuple((v + 2 * 52) // 3 for v in rgb)
                        im.putpixel((x0 + xx, y1 + yy), rgb + (255,))
        y = y0 + r * (32 + G)
    im.save(out)


def main(art, out, rom=None):
    rd = lambda n: open(os.path.join(art, n), 'rb').read()
    rom = open(rom or os.path.join(art, '..', '..', 'build', 'GhostsNGoblins_fixed.bin'), 'rb').read()
    bank, flags = rd('firebrand_bank.bin'), rd('firebrand_flags.bin')
    img = [fs.bank_image(bank[s * 0x300:(s + 1) * 0x300]) for s in range(a.COUNT)]
    line = [2 if flags[s] & 4 else 0 for s in range(a.COUNT)]
    shown = [s for s in range(a.COUNT)
             if not (s < 11 or s in a.EMPTY or (s < 84 and flags[s] & 8))]
    key = lambda g: tuple(map(tuple, g))
    groups = {}
    for s in shown:
        groups.setdefault(key(img[s]), []).append(s)
    ladder = (70, 71, 72, 73)

    works, broken = [], []
    flames = 0
    for k, slots in groups.items():
        if any(s in ladder for s in slots):
            continue
        left = all(flags[s] & 16 for s in slots)
        mirror = key(fs.mirror([list(r) for r in k]))
        if left and mirror in groups and mirror != k:
            continue                             # drawn from its right-facing twin
        names = sorted({meaning(s) for s in slots}, key=lambda n: (n not in DESC, n))
        if names == ['flames']:
            flames += 1
            title = 'Death %d' % flames
            text = ('Killed: the burst, then the game\'s own enemy flames (palette line 2).' if flames == 1
                    else 'Burning up when killed, picture %d. The game\'s own enemy flames (palette line 2).' % flames)
        else:
            title, text = describe(names)
            if 'hit' in names:
                text += ' Shown facing left too (no left picture: see MISSING).'
        works.append((img[slots[0]], line[slots[0]], title, text, min(slots)))
    works.sort(key=lambda w: (w[2].startswith('Death'), w[4]))

    # the ladder: all four slots hold the wall-cling picture
    cur = {s: img[s] for s in ladder}
    broken.append((cur[70], 0, 'Ladder (now)',
                   'The 4 ladder slots show the wall-cling pose (both ways). No climbing art yet.'))
    broken.append((cur[71], 0, 'Ladder (now, other way)',
                   'Same picture mirrored. Replace with the 4 ladder frames under MISSING.'))

    ref = ' Dimmed: Arthur\'s frame, as a guide.'
    missing = [
        (70, 'Climb A', 'On a ladder, from behind, one arm up. Alternates with B.' + ref),
        (71, 'Climb B', 'A\'s opposite: the other arm up (Arthur\'s is the mirror).' + ref),
        (72, 'Climb top A', 'Getting off at the top: one knee up on the ledge, from behind.' + ref),
        (73, 'Climb top B', 'Over the top: crouched on the ledge, from behind.' + ref),
        (None, 'Hit, facing left', 'Knocked back while facing left (the game now shows the right-facing '
                                   'one).'),
    ]

    extra = []
    anim = rd('firebrand_fire_anim.bin')
    for k in range(4):
        p = anim[k * 0x100:(k + 1) * 0x100]
        extra.append((fs.side(fs.mirror(fs.tiles(p[:0x80], 2, 2)), fs.mirror(fs.tiles(p[0x80:], 2, 2))), 0,
                      'Fireball %d' % (k + 1), 'His shot in flight, shape %d of 4.' % (k + 1)))
    for k, (n, t) in enumerate((('burst', 'first'), ('flame', 'second'), ('sparks', 'last'))):
        p = anim[(4 + k) * 0x100:(5 + k) * 0x100]
        extra.append((fs.mirror(fs.tiles(p[:0x80], 2, 2)), 0, 'Impact: ' + n,
                      'Fireball hitting something, %s picture.' % t))
    fire = rd('firebrand_fire.bin')
    extra.append((fs.side(fs.mirror(fs.tiles(fire[:0x80], 2, 2)), fs.mirror(fs.tiles(fire[0x80:], 2, 2))), 0,
                  'Weapon box', 'The fireball in the HUD weapon box.'))
    extra.append((fs.tiles(rd('firebrand_mapicon.bin'), 2, 2), 0, 'Map marker',
                  'His head on the stage map between lives.'))
    extra.append((fs.tiles(rd('firebrand_wing.bin')[:0x80], 2, 2), 0, 'Wing pickup',
                  'The item that gives him more flight.'))
    frog = rd('firebrand_frog.bin')
    for k in range(8):
        extra.append((fs.tiles(frog[k * 0x200:(k + 1) * 0x200], 4, 4), 0, 'Frog %d' % (k + 1),
                      'Turned into a frog by the magician, %d of 8.' % (k + 1)))

    works_all = [(g, l, t, d) for g, l, t, d, _ in works] + extra
    parts = [('WORKS', GREEN, works_all), ('BROKEN', ORANGE, broken),
             ('MISSING', RED, [(('ref', arthur(rom, k)) if k else None, 0, t, d) for k, t, d in missing])]

    write_raw(parts, os.path.splitext(out)[0] + '_raw.png')

    intro = [
        "FIREBRAND'S SPRITES: what to touch up and what to draw",
        'Each frame is a 48x32 box: a 32x32 body in the middle (the lighter box) with an 8 px column '
        'each side for wings; feet on the bottom row.',
        'Colours: only the 15 below (palette line 0); the death flames use their own line. One colour '
        'is transparent (the background).',
        'Draw everything facing right: facing left is made by mirroring. Frames the game shows several '
        'times are shown once.',
    ]
    pal_y = 16 + 18 * len(intro)
    y = pal_y + 40
    heights = [(len(items) + COLS - 1) // COLS * CH + 34 for _, _, items in parts]
    im = Image.new('RGB', (COLS * CW + 16, y + sum(heights) + 20), a.BG)
    d = ImageDraw.Draw(im)
    for i, t in enumerate(intro):
        d.text((12, 10 + 18 * i), t, fill=(255, 220, 120) if i == 0 else (225, 225, 225))
    for i in range(1, 16):
        d.rectangle([12 + (i - 1) * 34, pal_y, 12 + (i - 1) * 34 + 28, pal_y + 20], fill=a.LINE0[i])
        d.text((12 + (i - 1) * 34 + 2, pal_y + 22), str(i), fill=(200, 200, 200))

    for (name, col, items), h in zip(parts, heights):
        d.rectangle([8, y, COLS * CW + 8, y + 22], fill=col)
        d.text((14, y + 5), '%s  (%d)' % (name, len(items)), fill=(20, 20, 20))
        y0 = y + 30
        for i, (g, ln, title, text) in enumerate(items):
            ox, oy = 12 + (i % COLS) * CW, y0 + (i // COLS) * CH
            d.rectangle([ox - 2, oy - 2, ox + BOX_W + 1, oy + BOX_H + 1], outline=col, width=2)
            d.rectangle([ox, oy, ox + BOX_W - 1, oy + BOX_H - 1], fill=(48, 44, 56))
            d.rectangle([ox + 8 * S, oy, ox + 40 * S - 1, oy + BOX_H - 1], fill=(60, 56, 70))
            dim = isinstance(g, tuple)
            if dim:
                g = g[1]
            if g is None:
                d.text((ox + BOX_W // 2 - 24, oy + BOX_H // 2 - 6), 'to draw', fill=col)
            else:
                pal = a.LINE2 if ln == 2 else a.LINE0
                h_, w_ = len(g), len(g[0])
                x0, y1 = ox + (48 - w_) // 2 * S, oy + (32 - h_) * S
                for yy in range(h_):
                    for xx in range(w_):
                        c = g[yy][xx]
                        if c:
                            r = pal[c]
                            if dim:
                                r = tuple((v + 2 * 52) // 3 for v in r)
                            d.rectangle([x0 + xx * S, y1 + yy * S, x0 + xx * S + S - 1, y1 + yy * S + S - 1],
                                        fill=r)
                if dim:
                    d.text((ox + 4, oy + 4), 'Arthur (guide)', fill=col)
                    d.text((ox + BOX_W - 52, oy + 4), 'to draw', fill=col)
            d.text((ox, oy + BOX_H + 4), title, fill=col)
            for k, ln_ in enumerate(textwrap.wrap(text, 32)[:4]):
                d.text((ox, oy + BOX_H + 18 + 12 * k), ln_, fill=(215, 215, 215))
        y += h
    im.save(out)


if __name__ == '__main__':
    main(*sys.argv[1:4])
