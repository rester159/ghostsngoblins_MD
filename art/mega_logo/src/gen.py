"""The MEGA part of Mega Ghosts'n Goblins' logo, drafted with OpenAI's image API
(gpt-image-2 or $IMAGE_MODEL, images/edits) from the game's own logo (art/mega_logo/logo_ref.png,
its 3 rows of the title map at 4x), then cut to tiles by tiles.py.

The key is read from OPENAI_API_KEY or ~/.config/openai/api_key (never printed).
usage: gen.py <out dir> [n]                     writes mega_<k>.png
       gen.py <out dir> n demon <canvas.png>     MEGA + a demon silhouette around the
           title on <canvas.png> (frameless title at 6x, tools: gng.py), styled on
           dc_style_ref.png; writes demon_<k>.png
       gen.py <out dir> n demon2 <canvas.png>    the same with MEGA small and the demon
           closing under the title; writes demon2_<k>.png"""
import base64
import json
import os
import sys
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPT = (
    "Pixel art for a 1988 Sega Mega Drive / Genesis game title screen, in the exact style of the "
    "attached arcade logo: blocky 16-bit lettering, light grey and white letter faces with dark red "
    "blood drips running down from the top of each letter, a solid royal blue drop shadow down and "
    "to the right, hard black outline, no anti-aliasing, flat colours only. "
    "Draw ONLY the single word MEGA in capital letters in that same lettering, slightly bolder, "
    "inside a thin red rounded-rectangle frame like the attached logo's. "
    "Centred on a pure black background, wide and short, nothing else in the image, no other text."
)


def key():
    k = os.environ.get('OPENAI_API_KEY')
    if not k:
        p = os.path.expanduser('~/.config/openai/api_key')
        if os.path.exists(p):
            k = open(p).read().strip()
    if not k:
        sys.exit('no key: set OPENAI_API_KEY or write it to ~/.config/openai/api_key')
    return k


PROMPT_DEMON = (
    "16-bit Super Nintendo / Mega Drive era pixel art title logo, flat colours, hard pixel edges, "
    "no anti-aliasing, pure black background. The first image already contains the title "
    "GHOSTS'N GOBLINS in pixel lettering: keep that lettering exactly as it is, same size and same "
    "place, untouched. Behind it, add one large dark navy-blue silhouette of a horned winged "
    "gargoyle demon facing the viewer, its huge bat wings spread wide to both sides so that the "
    "silhouette frames the whole title like the monster silhouette behind the Demon's Crest logo "
    "in the second image: a solid dark navy shape with a few lighter blue rim highlights and two "
    "small glowing eyes, ragged wing edges, the title sitting across its lower body and wings. "
    "Above the title, inside the silhouette's chest and head area, write the single word MEGA in "
    "the exact lettering style of the word Crest in the second image: bold hand-drawn gothic "
    "capitals with sharp serifs and flared tips, bright sky-blue to cyan fill, a dark navy outline. "
    "MEGA about as tall as the title's letters times one and a half, centred. Nothing else, no "
    "other words, keep everything inside the image with black margins."
)

# the second round: MEGA half as big, the demon lower so that it closes under the title
PROMPT_DEMON2 = (
    "16-bit Super Nintendo / Mega Drive era pixel art title logo, flat colours, hard pixel edges, "
    "no anti-aliasing, pure black background. The first image already contains the title "
    "GHOSTS'N GOBLINS in pixel lettering: keep that lettering exactly as it is, same size and same "
    "place, untouched. Behind it, add one dark navy-blue silhouette of a horned winged gargoyle "
    "demon facing the viewer, like the monster silhouette behind the Demon's Crest logo in the "
    "second image: solid dark navy with a few lighter blue rim highlights, two small glowing eyes, "
    "ragged wing edges. The demon sits LOW: the title runs across the middle of its body, its head "
    "and horns just above the title, and its clawed hands, lower body and the bottom edges of both "
    "wings wrap around and close underneath the title, so the title is enclosed by the silhouette "
    "on all sides. Wings spread wide and flat to both sides: the whole silhouette is short and "
    "wide, about two and a half times wider than tall. Between the demon's head and the title, "
    "write the single word MEGA, small: its letters only about as tall as the title's letters, in "
    "the exact lettering style of the word Crest in the second image: bold hand-drawn gothic "
    "capitals with sharp serifs and flared tips, bright sky-blue to cyan fill, a dark navy outline. "
    "Nothing else, no other words, keep everything inside the image with black margins."
)


def edit(ref, n, prompt=PROMPT, extra=()):
    b = uuid.uuid4().hex
    parts = []
    for name, val in (('model', os.environ.get('IMAGE_MODEL', 'gpt-image-2')), ('prompt', prompt), ('n', str(n)),
                      ('size', '1536x1024'), ('quality', 'high'), ('background', 'opaque')):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'.encode())
    for k, path in enumerate((ref,) + tuple(extra)):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="image[]"; filename="ref{k}.png"\r\n'
                     'Content-Type: image/png\r\n\r\n'.encode() + open(path, 'rb').read() + b'\r\n')
    body = b''.join(parts) + f'--{b}--\r\n'.encode()
    rq = urllib.request.Request('https://api.openai.com/v1/images/edits', body, {
        'Authorization': 'Bearer ' + key(), 'Content-Type': 'multipart/form-data; boundary=' + b})
    try:
        return json.load(urllib.request.urlopen(rq, timeout=300))
    except urllib.error.HTTPError as e:
        sys.exit(f'HTTP {e.code}: {e.read().decode()[:500]}')


if __name__ == '__main__':
    out, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 4 and sys.argv[3] in ('demon', 'demon2'):
        r = edit(sys.argv[4], n, PROMPT_DEMON if sys.argv[3] == 'demon' else PROMPT_DEMON2,
                 (os.path.join(HERE, '..', 'dc_style_ref.png'),))
        stem = sys.argv[3]
    else:
        r = edit(os.path.join(HERE, '..', 'logo_ref.png'), n)
        stem = 'mega'
    for k, d in enumerate(r['data']):
        open(os.path.join(out, f'{stem}_{k}.png'), 'wb').write(base64.b64decode(d['b64_json']))
        print(os.path.join(out, f'{stem}_{k}.png'))
