"""Contact sheet of PNG frames: sheet.py <out.png> <cols> <scale> <files...>"""
import sys
from PIL import Image, ImageDraw
out, cols, sc = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
fs = sys.argv[4:]
ims = [Image.open(f) for f in fs]
w, h = int(ims[0].width * sc), int(ims[0].height * sc)
S = Image.new('RGB', (cols * w, ((len(ims) + cols - 1) // cols) * (h + 12)), (0, 0, 0))
d = ImageDraw.Draw(S)
for k, (f, im) in enumerate(zip(fs, ims)):
    x, y = (k % cols) * w, (k // cols) * (h + 12)
    S.paste(im.resize((w, h)), (x, y + 12))
    d.text((x + 2, y), f.split('/')[-1], fill=(255, 255, 0))
S.save(out)
