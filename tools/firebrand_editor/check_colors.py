"""Check the Firebrand editor's colours against the game: the editor's palette
lines (make_data.py LINE0/LINE2) against CRAM, and the frame the game has in
VRAM (Arthur's sprite tiles at $6000, plus the wing columns at $D200) against
the editor's bank frame, both read from Genesis Plus GX save states taken in
Firebrand play (e.g. tools/headless/fb_wall_test.py's).

usage: check_colors.py <state> [<state> ...]
Prints per state: palette lines that differ, and which bank frame (if any) is
in VRAM; exits 1 on any colour mismatch."""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'headless'))
import make_data                                 # noqa: E402
import vdp                                       # noqa: E402

ROOT = os.path.join(HERE, '..', '..')
bank = open(os.path.join(ROOT, 'art', 'firebrand', 'firebrand_bank.bin'), 'rb').read()
bad = 0
for path in sys.argv[1:]:
    vram, _, _ = vdp.load(path)
    pal = [tuple(c) for c in vdp.palette(path)]
    msg = []
    for line, want in ((0, make_data.LINE0), (2, make_data.LINE2)):
        diff = [i for i in range(1, 16) if pal[line * 16 + i] != tuple(want[i])]
        if diff:
            bad = 1
            msg.append('line %d differs at %s' % (line, diff))
    body = bytes(vram[0x6000:0x6200])
    hits = [k for k in range(len(bank) // 0x300) if bank[k * 0x300:k * 0x300 + 0x200] == body]
    msg.append('VRAM frame = bank %s' % hits if hits else 'VRAM frame not in the bank (not Firebrand, or the frog)')
    print(os.path.basename(path) + ':', '; '.join(msg) if msg else 'ok')
sys.exit(bad)
