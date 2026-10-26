"""arc_walk.py <state> <frames> <script: python list of (from, to, mask)> [png prefix]: the arcade (tools/arcade)
from a state; logs enemy slot events (TYPES=4,5 | all; slots $0880, 40 x 48, type +$15) and Arthur every 100
frames. Arthur kept invincible ($AD). BOT=1 with AJ/CL (bot.py), TP=frame:x teleports. Pad bits: 1 right 2
left 4 down 8 up 10 fire 20 jump."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'arcade'))
from gng import GnG
g = GnG(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'rom')); g.load(sys.argv[1])
N = int(sys.argv[2]); ev = eval(sys.argv[3]); pngp = sys.argv[4] if len(sys.argv) > 4 else None
m = g.mem; prev = {}
TY = None if os.environ.get('TYPES', '4,5') == 'all' else [int(v) for v in os.environ.get('TYPES', '4,5').split(',')]
AJ = [int(v) for v in os.environ.get('AJ', '').split(',') if v]; jt = 0
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bot import Bot
bot = Bot(AJ, [int(v) for v in os.environ.get('CL', '').split(',') if v]) if os.environ.get('BOT') else None
for f in range(1, N + 1):
    p = 0
    for a, b, k in ev:
        if a <= f <= b: p |= k; break
    ax0 = m[0x506] << 8 | m[0x507]
    if bot:
        p = {'R': 1, 'U': 8, 'J': 0x20, 'RJ': 0x21}[bot.step(ax0, m[0x509] << 8 | m[0x50A])]
    else:
        if any(abs(ax0 - j) <= 1 for j in AJ) and jt == 0: jt = 6
        if jt: p = 0x21; jt -= 1
    TP = os.environ.get('TP')
    if TP:
        tf, tx = map(int, TP.split(':'))
        if tf <= f < tf + 3: m[0x506] = tx >> 8; m[0x507] = tx & 255
    m[0xAD] = 60
    g.set_inputs(0, p, 0); g.run_frame()
    ax = m[0x506] << 8 | m[0x507]; cam = m[0x9C] << 8 | m[0x9D]
    if f % 100 == 0: print('f%d arthur x%d y%d cam%d' % (f, ax, m[0x509] << 8 | m[0x50A], cam))
    if pngp and f % 100 == 0: g.png('%s_%05d.png' % (pngp, f))
    for i in range(40):
        a = 0x880 + 48 * i; t = m[a + 0x15]
        cur = (t, m[a + 3]) if m[a] and (TY is None or t in TY) else None
        if cur != prev.get(i):
            print('f%d ax%d cam%d slot%d %s -> %s x%d y%d ons%d sub%d,%d' % (f, ax, cam, i, prev.get(i), cur, m[a + 6] << 8 | m[a + 7], m[a + 9] << 8 | m[a + 10], m[a + 1], m[a + 4], m[a + 5]))
            prev[i] = cur
