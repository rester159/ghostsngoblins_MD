"""Contact sheet of a snes_capture.py JSON: each picture with its first frame.

usage: capsheet.py <capture.json> <out.png> [zoom]"""
import json
import sys
from PIL import Image, ImageDraw

recs = json.load(open(sys.argv[1]))
Z = int(sys.argv[3]) if len(sys.argv) > 3 else 3
cw = max(r['box'][2] for r in recs) * Z + 10
ch = max(r['box'][3] for r in recs) * Z + 18
cols = 10
im = Image.new('RGB', (cols * cw, ((len(recs) + cols - 1) // cols) * ch), (40, 40, 60))
d = ImageDraw.Draw(im)
for k, r in enumerate(recs):
    ox, oy = (k % cols) * cw, (k // cols) * ch
    pal = [((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3) for c in r['palette']]
    for y, row in enumerate(r['rows']):
        for x, ch_ in enumerate(row):
            c = int(ch_, 16)
            if c:
                d.rectangle([ox + x * Z, oy + y * Z, ox + x * Z + Z - 1, oy + y * Z + Z - 1], fill=pal[c])
    d.text((ox + 2, oy + ch - 14), '%d f%d' % (k, r['first']), fill=(220, 220, 220))
im.save(sys.argv[2])
