"""firebrand_arcade_sheet.png (the pixel editor's sheet layout) -> the game's Firebrand art:
firebrand_bank.bin and firebrand_flags.bin, which tools/patch_gng.py places at $3A0000 and $3B6000.
The flags keep their walk and facing bits (3, 4); the wing-column bits (0, 1) and the palette line
(bit 2) come from the frame.

usage: sheet_to_bank.py <sheet.png> <art dir (firebrand_flags.bin read and both written there)>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcade_sheet as a
from PIL import Image
png, out_dir = sys.argv[1:3]
old_flags = os.path.join(out_dir, 'firebrand_flags.bin')
im = Image.open(png).convert('RGB')
oldf = open(old_flags, 'rb').read()
bank, flags = bytearray(), bytearray()
for s in range(a.COUNT):
    ox, oy = (s % a.COLS) * a.CW, (s // a.COLS) * a.CH
    px = [[im.getpixel((ox + x * a.S, oy + y * a.S)) for x in range(a.W)] for y in range(a.H)]
    used = {c for r in px for c in r} - {a.BG}
    for line, pal in ((0, a.LINE0), (2, a.LINE2)):
        inv = {}
        for i in range(len(pal) - 1, 0, -1):
            inv[tuple(pal[i])] = i
        if used <= set(inv):
            break
    else:
        sys.exit('slot %d: colours not in either palette line: %s' % (s, used - set(inv)))
    g = [[0 if c == a.BG else inv[c] for c in r] for r in px]
    bank += a.bank_frame(g)
    lw = any(g[y][x] for y in range(a.H) for x in range(8))
    rw = any(g[y][x] for y in range(a.H) for x in range(40, 48))
    flags.append((oldf[s] & ~7) | lw | rw << 1 | (4 if line == 2 else 0))
open(os.path.join(out_dir, 'firebrand_bank.bin'), 'wb').write(bank)
open(os.path.join(out_dir, 'firebrand_flags.bin'), 'wb').write(flags)
print('bank', len(bank), 'line2', sum(1 for f in flags if f & 4), 'wide', sum(1 for f in flags if f & 3),
      'flags changed', sum(1 for i in range(a.COUNT) if flags[i] != oldf[i]))
