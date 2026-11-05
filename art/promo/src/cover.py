"""itch.io cover for Mega Ghosts'n Goblins: an illustration drafted with OpenAI's
image API in the manner of the 1985 arcade flyer (refs/arcade_flyer.png), with
Maximo and Firebrand from their sprite sheets (refs/characters.png); then the
game's own Mega logo (art/mega_logo/mega_logo.png) and the tagline in the game's
menu font are laid over it here, so neither is redrawn by the model.

usage: cover.py draft <out dir> [n] [flyer]   writes cover_<k>.png (1536x1024); flyer:
                                              in the flyer's own cel style
       cover.py flyer <out dir> [n]            the flyer itself edited (Maximo and Arthur,
                                              Firebrand in front, the Mega title, the tagline)
       cover.py widen <flyer_k.png> <out dir>  that to itch.io's sizes, the API painting the sides
       cover.py wide <flyer_k.png> <out dir> [n]  the whole scene repainted wide in one piece
       cover.py simple <out dir> [n] [size]    simpler, Firebrand once, from the flyer
                                              (size 1280x1024 is itch.io's shape)
       cover.py featuring <wide.png> x0,y0,x1,y1 <out dir>  FEATURING repainted in the box
       cover.py title <art.png> <out dir> [n]  the logo and tagline painted on in the flyer's
                                              style; writes titled_<k>.png
       cover.py extend <titled.png> <out dir>  itch.io's sizes, the whole picture kept, the
                                              API painting the sky and grass it needs
       cover.py fit <titled.png> <out dir>     the same with mirrored edges (no API)
       cover.py compose <draft.png> <out dir>  (first round) the pixel logo and the font
                                              tagline laid on; writes cover_630x500.png, cover_1260x1000.png"""
import base64
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'art', 'mega_logo', 'src'))
import gen                      # noqa: E402

PROMPT = (
    "A new painted illustration in the manner of the 1985 arcade flyer in the first image: "
    "the same airbrushed 1980s Japanese arcade-poster painting style, saturated colours, dramatic "
    "dark graveyard at night, a crowd of monsters behind the heroes (a giant blue ogre, a cyclops "
    "giant, a dragon, zombies rising from graves, crows, tombstones, dead trees). A wide landscape "
    "composition, not a copy of the flyer's layout. Heroes, from the pixel sprites in the second "
    "image, painted as full illustrated characters: on the left MAXIMO, a young knight with auburn "
    "hair and blue eyes in gunmetal-blue plate armour, a red plumed helmet and a red scarf, "
    "charging forward with a lance; on the right FIREBRAND, a fierce red gargoyle demon with an "
    "orange belly, blue-grey claws and big grey bat wings spread, flying and spitting a fireball. "
    "Keep the top third of the picture as dark night sky with a pale moon and no figures, and keep "
    "a thin dark strip along the bottom edge empty. Absolutely no text, letters, logos or "
    "signatures anywhere in the picture."
)

# the second round: the flyer's own look, not a new painting
PROMPT_FLYER = (
    "Redraw the first image, the 1985 arcade flyer, in exactly its own art style: the same flat "
    "cel-shaded 1980s Japanese anime illustration, bold black ink outlines, bright flat saturated "
    "colours with simple airbrushed gradients, the same pink-and-grey stormy sky, the same "
    "chunky cartoon monsters (the big blue ogre, the green-skinned giant in the red studded coat, "
    "the orange flying demon, the purple dragon, zombies, a tombstone), the same busy crowded "
    "composition with the knight in the centre front leaping forward with a lance and the "
    "monsters packed around and behind him. Make it a wide landscape picture with the same "
    "characters spread out. Change only these: the knight is MAXIMO from the second image, a "
    "young auburn-haired, blue-eyed knight in gunmetal-blue armour with a red plumed helmet and a "
    "red scarf, drawn in the flyer's cartoon style; and the red winged demon top right is "
    "FIREBRAND from the second image, a red gargoyle with an orange belly, blue-grey claws and big "
    "grey bat wings, swooping and spitting a fireball, drawn in the flyer's cartoon style. Leave "
    "the top quarter of the picture as plain stormy sky with no characters. No text, no title, no "
    "logo, no letters, no white border anywhere: only the illustration, filling the whole image."
)

# the third round: the flyer itself edited, so its own painting style stays
PROMPT_EDIT = (
    "This is the 1987 Ghosts'n Goblins arcade flyer. Keep it as it is: the same hand-painted "
    "1980s airbrush and gouache poster painting, the same soft painted shading and colours, the "
    "same monsters in the same places and poses, the same grey castle and sky, the same "
    "composition, and keep ARTHUR, the silver-armoured knight leaping with a lance in the front. "
    "Do not make it look like anime, cel shading or a modern digital painting. Change only these, "
    "painted in exactly the flyer's own style: "
    "1. Beside Arthur in the front, add MAXIMO from the second image: a young knight with auburn "
    "hair, gunmetal-blue armour, a red plumed helmet and a red scarf, fighting next to Arthur. "
    "2. Bring FIREBRAND, the red winged gargoyle from the second image (red body, orange belly, "
    "grey bat wings), to the front right, big and close, spitting a fireball, not in the "
    "background. "
    "3. The title: replace GHOST'N GOBLINS with MEGA GHOSTS'N GOBLINS, lettered the same way as "
    "the flyer's title (blue-to-white gradient capitals in a red-outlined box), with the small "
    "word MEGA above it, and a dark navy horned winged demon silhouette spreading behind the "
    "title box, an idea taken from the third image. "
    "4. At the bottom, instead of the CAPCOM logo and address, the line FEATURING MAXIMO AND "
    "FIREBRAND'S VENDETTA! in 1980s arcade flyer lettering: chunky bold capitals with a hard drop "
    "shadow, like the title's, nothing modern. "
    "5. Remove the small (C) CAPCOM and DISTRIBUTED BY texts and the white border: the painting "
    "fills the whole image. Spell exactly: MEGA, GHOSTS'N GOBLINS, FEATURING MAXIMO AND "
    "FIREBRAND'S VENDETTA!"
)

PROMPT_SIDES = (
    "Extend this 1980s hand-painted arcade flyer painting into its transparent areas on the left "
    "and right: continue the same grey castle wall, stormy sky, graveyard grass and tombstones, "
    "and a few more monsters at the edges, in exactly the same airbrush and gouache painting "
    "style, seamlessly. Keep the existing picture, its title and its bottom line unchanged. Add "
    "no new text or logos."
)

# the fourth round: the whole scene painted again, wide, in one piece
PROMPT_WIDE = (
    "Paint this whole poster again from scratch as ONE single wide landscape painting, every part "
    "of it painted together in one consistent style, nothing pasted or extended. The style must "
    "be identical to the original 1987 Ghosts'n Goblins arcade flyer in the second image: the "
    "same hand-painted airbrush and gouache poster art, the same soft rounded shading, the same "
    "bright saturated colours, the same fiery orange-red background behind a grey castle tower, "
    "the same cartoonish monster designs. The content is the first image's: the big blue furry "
    "ogre in the middle behind, the orange fist holding the princess, the pink flying devil, the "
    "purple dragon, the green-faced giant in the red studded coat, the orange cyclops creatures, "
    "zombies; in the front, ARTHUR (bearded silver knight with a lance) leaping forward between "
    "MAXIMO (young auburn-haired knight in blue armour, red plume and red scarf) and FIREBRAND "
    "(the big red winged gargoyle spitting a fireball), all three large in the foreground on "
    "green grass. Spread the scene across the wide format so it fills it edge to edge. At the top "
    "the title lettered as in the first image: the small word MEGA over GHOSTS'N GOBLINS in "
    "blue-to-white gradient capitals in a red-outlined box, a dark navy horned winged demon "
    "silhouette spreading behind it. At the bottom, in the same 1980s arcade lettering as in the "
    "first image, FEATURING MAXIMO AND FIREBRAND'S VENDETTA! No other text, no logos, no border. "
    "Spell exactly: MEGA, GHOSTS'N GOBLINS, FEATURING MAXIMO AND FIREBRAND'S VENDETTA!"
)

PROMPT_FEATURING = (
    "In the transparent area, repaint the single word FEATURING in exactly the same 1980s arcade "
    "lettering as the big words MAXIMO AND FIREBRAND'S VENDETTA! under it: chunky condensed "
    "capitals, white at the top fading to red at the bottom, a dark outline and a blue drop "
    "shadow, smaller than that line and centred above it, on the same painted grass and "
    "background. Spell it exactly FEATURING. Change nothing else."
)

# the fifth round: simpler, Firebrand once (where the flyer's red devil flies)
PROMPT_SIMPLE = (
    "Paint a wide landscape poster in the simple style of the 1987 Ghosts'n Goblins arcade flyer "
    "in the first image, as one single painting. Keep the style simple, like that flyer: smooth "
    "flat airbrushed colour areas, soft simple gradients, clean rounded shapes, bold simple "
    "outlines, very little texture or fine detail, no hair-by-hair or scale-by-scale rendering, no "
    "grain. A simple composition with few elements and clear shapes: a plain fiery orange-red "
    "sky with a grey castle tower in the middle; the big blue furry ogre behind the tower; a "
    "purple dragon curling on the left; on the right, FIREBRAND, the red winged gargoyle from the "
    "second image (red body, orange belly, grey bat wings), flying in the upper right where the "
    "flyer's red devil is, spitting a fireball; a green-faced giant in a red studded coat at the "
    "left; two zombies. In the front, on green grass, only two heroes: ARTHUR, the bearded silver "
    "knight leaping forward with a lance, and MAXIMO beside him, the young auburn-haired knight "
    "in gunmetal-blue armour with a red plumed helmet and a red scarf (second image). Firebrand "
    "appears only once, in the upper right, not in the front. At the top the title as in the "
    "third image's idea, lettered like the flyer's title: the small word MEGA over GHOSTS'N "
    "GOBLINS in blue-to-white gradient capitals in a red-outlined box, a dark navy horned winged "
    "demon silhouette behind it. At the bottom, all in the same lettering as the title, one line "
    "or two: FEATURING MAXIMO AND FIREBRAND'S VENDETTA! No other text, no logos, no border. "
    "Spell exactly: MEGA, GHOSTS'N GOBLINS, FEATURING MAXIMO AND FIREBRAND'S VENDETTA!"
)

# the second pass: the title and tagline painted on a chosen illustration
PROMPT_TITLE = (
    "Keep the first image, the illustration, exactly as it is, and paint a title logo across its "
    "top and a tagline along its bottom, both in the style of the title lettering on the original "
    "1985 arcade flyer in the second image: smooth hand-painted 1980s arcade poster lettering with "
    "bold black outlines, bright flat colours, a red outlined banner shape. The logo is a painted "
    "reinterpretation of the game's pixel logo in the third image, not a copy of its pixels: the "
    "word MEGA, small, in bright blue gothic capitals with sharp serifs, above the words "
    "GHOSTS'N GOBLINS in big white-and-silver capitals with red blood dripping from their tops "
    "and a blue drop shadow, with a dark navy horned demon silhouette behind the whole title, its "
    "bat wings spread wide and its claws closing under the title. Along the bottom edge, in bold "
    "yellow capitals with a red outline, the tagline FEATURING MAXIMO AND FIREBRAND'S VENDETTA! "
    "Spell every word exactly as given: MEGA, GHOSTS'N GOBLINS, FEATURING MAXIMO AND FIREBRAND'S "
    "VENDETTA! No other text and no other logos."
)

FONT = os.path.join(ROOT, 'src_patch', 'build', 'font.inc')


def font():
    """the menu font (src_patch/build/font.inc: 8x8 tiles from ' ', 4bpp words)"""
    import re
    ws = [int(w, 16) for w in re.findall(r'0x([0-9A-Fa-f]{4})', open(FONT).read())]
    tiles = []
    for t in range(len(ws) // 16):
        g = []
        for y in range(8):
            a, b = ws[t * 16 + y * 2], ws[t * 16 + y * 2 + 1]
            v = a << 16 | b
            g.append([(v >> (28 - 4 * x)) & 15 for x in range(8)])
        tiles.append(g)
    return tiles


def text(s, colours):
    """s in the menu font, 8 px a character; pens 1-3 -> colours"""
    f = font()
    im = Image.new('RGBA', (8 * len(s), 8), (0, 0, 0, 0))
    for i, ch in enumerate(s):
        g = f[ord(ch) - 0x20] if 0x20 <= ord(ch) < 0x20 + len(f) else f[0]
        for y in range(8):
            for x in range(8):
                if g[y][x]:
                    im.putpixel((i * 8 + x, y), colours.get(g[y][x], (255, 255, 255)) + (255,))
    return im


def compose(draft, out):
    art = Image.open(draft).convert('RGB')
    # itch.io's cover: 630 x 500 (and twice that); the draft cropped to 1.26:1
    w, h = art.size
    cw = round(h * 630 / 500)
    art = art.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h)).resize((1260, 1000), Image.LANCZOS)
    logo = Image.open(os.path.join(ROOT, 'art', 'mega_logo', 'mega_logo.png')).convert('RGB')
    mask = Image.new('L', logo.size)
    mask.putdata([255 if p != (0, 0, 0) else 0 for p in logo.get_flattened_data()])
    k = 4                                        # 256 x 104 -> 1024 x 416
    big, bm = logo.resize((logo.width * k, logo.height * k), Image.NEAREST), mask.resize(
        (logo.width * k, logo.height * k), Image.NEAREST)
    art.paste(big, ((1260 - big.width) // 2, 14), bm)
    # the tagline on a dark band at the bottom
    line = "FEATURING MAXIMO AND FIREBRAND'S VENDETTA!"
    t = text(line, {1: (238, 238, 238), 2: (238, 136, 68), 3: (34, 34, 34)})
    s = 3
    t = t.resize((t.width * s, t.height * s), Image.NEAREST)
    band_h = t.height + 28
    d = ImageDraw.Draw(art, 'RGBA')
    d.rectangle((0, 1000 - band_h, 1260, 1000), fill=(0, 0, 0, 200))
    art.paste(t, ((1260 - t.width) // 2, 1000 - band_h + 14), t)
    os.makedirs(out, exist_ok=True)
    art.save(os.path.join(out, 'cover_1260x1000.png'))
    art.resize((630, 500), Image.LANCZOS).save(os.path.join(out, 'cover_630x500.png'))


PROMPT_EXTEND = (
    "Extend this painting into its transparent areas: continue the stormy pink, purple and "
    "dark sky upward above the picture and the green grass and dark ground downward below it, in "
    "exactly the same painted style, seamlessly. Keep the existing picture, its logo and its "
    "tagline unchanged. Add no new text, characters or logos."
)


def extend(path, out):
    """itch.io's 1.26:1 from a 3:2 picture, all of it kept: the picture shrunk into
    the middle of a 1536 x 1024 canvas and the API paints the sky above and the grass
    below; then the middle 1290 x 1024 is cut and sized to 1260 x 1000 and 630 x 500"""
    import tempfile
    im = Image.open(path).convert('RGB')
    w = 1290
    h = round(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    x0, y0 = (1536 - w) // 2, (1024 - h) // 2
    canvas = Image.new('RGBA', (1536, 1024), (0, 0, 0, 0))
    canvas.paste(im, (x0, y0))
    tmp = tempfile.mkdtemp()
    cp = os.path.join(tmp, 'canvas.png')
    canvas.save(cp)
    r = gen.edit(cp, 1, PROMPT_EXTEND, (), cp)
    big = Image.open(__import__('io').BytesIO(base64.b64decode(r['data'][0]['b64_json']))).convert('RGB')
    os.makedirs(out, exist_ok=True)
    big.save(os.path.join(out, 'api.png'))
    # the picture itself back over the API's copy of it, faded in over FEATHER px
    # from its top and bottom edges so the new sky and grass join without a line
    FEATHER = 48
    m = Image.new('L', im.size, 255)
    for y in range(FEATHER):
        v = round(255 * y / FEATHER)
        for yy in (y, h - 1 - y):
            m.paste(v, (0, yy, w, yy + 1))
    big.paste(im, (x0, y0), m)
    c = big.crop((x0, 0, x0 + w, 1024)).resize((1260, 1000), Image.LANCZOS)
    big.save(os.path.join(out, 'extended.png'))
    c.save(os.path.join(out, 'cover_1260x1000.png'))
    c.resize((630, 500), Image.LANCZOS).save(os.path.join(out, 'cover_630x500.png'))


def flyer(out, n):
    """the third round: the flyer edited (1024 x 1536), writes flyer_<k>.png"""
    os.makedirs(out, exist_ok=True)
    r = gen.edit(os.path.join(HERE, '..', 'refs', 'arcade_flyer_1024.png'), n, PROMPT_EDIT,
                 (os.path.join(HERE, '..', 'refs', 'characters.png'),
                  os.path.join(HERE, '..', 'refs', 'mega_logo_x5.png')), size='1024x1536')
    for i, d in enumerate(r['data']):
        p = os.path.join(out, f'flyer_{i}.png')
        open(p, 'wb').write(base64.b64decode(d['b64_json']))
        print(p)


def wide(content, out, n):
    """the fourth round: from a flyer edit (content) and the flyer (style), one wide
    painting; writes wide_<k>.png and, cut to 1.26:1, cover_<k>_630x500/1260x1000"""
    os.makedirs(out, exist_ok=True)
    r = gen.edit(content, n, PROMPT_WIDE, (os.path.join(HERE, '..', 'refs', 'arcade_flyer_1024.png'),))
    for i, d in enumerate(r['data']):
        p = os.path.join(out, f'wide_{i}.png')
        open(p, 'wb').write(base64.b64decode(d['b64_json']))
        im = Image.open(p).convert('RGB')
        cx = (im.width - 1290) // 2
        c = im.crop((cx, 0, cx + 1290, im.height)).resize((1260, 1000), Image.LANCZOS)
        c.save(os.path.join(out, f'cover_{i}_1260x1000.png'))
        c.resize((630, 500), Image.LANCZOS).save(os.path.join(out, f'cover_{i}_630x500.png'))
        print(p)


def simple(out, n, size='1536x1024'):
    """the fifth round: writes simple_<k>.png and its covers (cut to 1.26:1 if wider)"""
    os.makedirs(out, exist_ok=True)
    r = gen.edit(os.path.join(HERE, '..', 'refs', 'arcade_flyer_1024.png'), n, PROMPT_SIMPLE + (
                 " Keep the whole bottom line well inside the picture, with margins at both ends."),
                 (os.path.join(HERE, '..', 'refs', 'characters.png'),
                  os.path.join(HERE, '..', 'refs', 'mega_logo_x5.png')), size=size)
    for i, d in enumerate(r['data']):
        p = os.path.join(out, f'simple_{i}.png')
        open(p, 'wb').write(base64.b64decode(d['b64_json']))
        im = Image.open(p).convert('RGB')
        cw = round(im.height * 1.26)
        cx = max(0, (im.width - cw) // 2)
        c = im.crop((cx, 0, cx + min(cw, im.width), im.height)).resize((1260, 1000), Image.LANCZOS)
        c.save(os.path.join(out, f'cover_{i}_1260x1000.png'))
        c.resize((630, 500), Image.LANCZOS).save(os.path.join(out, f'cover_{i}_630x500.png'))
        print(p)


def featuring(path, box, out):
    """the word FEATURING repainted in the tagline's lettering: box (x0, y0, x1, y1) in
    the 1536 x 1024 picture is opened to the API, the rest kept; writes fixed.png and
    its covers"""
    import io
    import tempfile
    im = Image.open(path).convert('RGBA')
    m = im.copy()
    m.paste((0, 0, 0, 0), box)
    mp = os.path.join(tempfile.mkdtemp(), 'mask.png')
    m.save(mp)
    ip = os.path.join(os.path.dirname(mp), 'img.png')
    im.save(ip)
    r = gen.edit(ip, 1, PROMPT_FEATURING, (), mp)
    new = Image.open(io.BytesIO(base64.b64decode(r['data'][0]['b64_json']))).convert('RGB')
    out_im = im.convert('RGB')
    out_im.paste(new.crop(box), box[:2])           # only the opened box changes
    os.makedirs(out, exist_ok=True)
    out_im.save(os.path.join(out, 'fixed.png'))
    cx = (out_im.width - 1290) // 2
    c = out_im.crop((cx, 0, cx + 1290, out_im.height)).resize((1260, 1000), Image.LANCZOS)
    c.save(os.path.join(out, 'cover_1260x1000.png'))
    c.resize((630, 500), Image.LANCZOS).save(os.path.join(out, 'cover_630x500.png'))


def widen(path, out):
    """a portrait flyer to itch.io's 1.26:1: it fills the height in the middle of a
    1536 x 1024 canvas, the API paints the sides; the middle 1290 x 1024 is cut"""
    import io
    import tempfile
    im = Image.open(path).convert('RGB')
    h = 1024
    w = round(im.width * h / im.height)
    im = im.resize((w, h), Image.LANCZOS)
    x0 = (1536 - w) // 2
    canvas = Image.new('RGBA', (1536, 1024), (0, 0, 0, 0))
    canvas.paste(im, (x0, 0))
    cp = os.path.join(tempfile.mkdtemp(), 'canvas.png')
    canvas.save(cp)
    r = gen.edit(cp, 1, PROMPT_SIDES, (), cp)
    big = Image.open(io.BytesIO(base64.b64decode(r['data'][0]['b64_json']))).convert('RGB')
    os.makedirs(out, exist_ok=True)
    big.save(os.path.join(out, 'api.png'))
    FEATHER = 48
    m = Image.new('L', im.size, 255)
    for x in range(FEATHER):
        v = round(255 * x / FEATHER)
        for xx in (x, w - 1 - x):
            m.paste(v, (xx, 0, xx + 1, h))
    big.paste(im, (x0, 0), m)
    big.save(os.path.join(out, 'extended.png'))
    cx = (1536 - 1290) // 2
    c = big.crop((cx, 0, cx + 1290, 1024)).resize((1260, 1000), Image.LANCZOS)
    c.save(os.path.join(out, 'cover_1260x1000.png'))
    c.resize((630, 500), Image.LANCZOS).save(os.path.join(out, 'cover_630x500.png'))


def fit(path, out):
    """itch.io's 630 x 500 (and 1260 x 1000) from a 3:2 picture, all of it kept: the
    picture 1260 wide, its top and bottom edges mirrored out to fill the height,
    softened toward the outside"""
    from PIL import ImageFilter
    im = Image.open(path).convert('RGB')
    im = im.resize((1260, round(im.height * 1260 / im.width)), Image.LANCZOS)
    pad = 1000 - im.height
    top, bot = pad // 2, pad - pad // 2
    c = Image.new('RGB', (1260, 1000))
    c.paste(im, (0, top))
    for y0, band, flip in ((0, im.crop((0, 0, 1260, top)), True),
                           (top + im.height, im.crop((0, im.height - bot, 1260, im.height)), True)):
        b = band.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(6))
        dark = Image.new('RGB', b.size)
        m = Image.linear_gradient('L').resize(b.size)          # 0 at its top, 255 at its bottom
        if y0 == 0:
            m = m.transpose(Image.FLIP_TOP_BOTTOM)             # darkest at the picture's edge
        b = Image.composite(dark, b, m.point(lambda v: v * 0.6))
        c.paste(b, (0, y0))
    os.makedirs(out, exist_ok=True)
    c.save(os.path.join(out, 'cover_1260x1000.png'))
    c.resize((630, 500), Image.LANCZOS).save(os.path.join(out, 'cover_630x500.png'))


if __name__ == '__main__':
    if sys.argv[1] == 'draft':
        out, n = sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4
        os.makedirs(out, exist_ok=True)
        r = gen.edit(os.path.join(HERE, '..', 'refs', 'arcade_flyer.png'), n,
                     PROMPT_FLYER if len(sys.argv) > 4 and sys.argv[4] == 'flyer' else PROMPT,
                     (os.path.join(HERE, '..', 'refs', 'characters.png'),))
        for i, d in enumerate(r['data']):
            p = os.path.join(out, f'cover_{i}.png')
            open(p, 'wb').write(base64.b64decode(d['b64_json']))
            print(p)
    elif sys.argv[1] == 'title':
        art, out, n = sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 4
        os.makedirs(out, exist_ok=True)
        r = gen.edit(art, n, PROMPT_TITLE, (os.path.join(HERE, '..', 'refs', 'arcade_flyer.png'),
                                             os.path.join(HERE, '..', 'refs', 'mega_logo_x5.png')))
        for i, d in enumerate(r['data']):
            p = os.path.join(out, f'titled_{i}.png')
            open(p, 'wb').write(base64.b64decode(d['b64_json']))
            print(p)
    elif sys.argv[1] == 'flyer':
        flyer(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4)
    elif sys.argv[1] == 'wide':
        wide(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 4)
    elif sys.argv[1] == 'simple':
        simple(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 4,
               sys.argv[4] if len(sys.argv) > 4 else '1536x1024')
    elif sys.argv[1] == 'featuring':
        featuring(sys.argv[2], tuple(int(v) for v in sys.argv[3].split(',')), sys.argv[4])
    elif sys.argv[1] == 'widen':
        widen(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'extend':
        extend(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'fit':
        fit(sys.argv[2], sys.argv[3])
    else:
        compose(sys.argv[2], sys.argv[3])
