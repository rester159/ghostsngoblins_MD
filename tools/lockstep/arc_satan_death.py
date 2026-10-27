"""arc_satan_death.py <state> <frames>: Arthur invincible, throwing (F1,W<gap>) from where he stands; the Satan's hit points
held at 1 once it is awake (HP1=1); logs from the kill: the slot's bytes and the sprite list entries near it."""
import os, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, R + '/tools/arcade')
from gng import GnG
g = GnG(R + '/rom'); g.load(sys.argv[1]); m = g.mem
GAP = int(os.environ.get('GAP', '12')); FACE = int(os.environ.get('FACE', '0'))
kill = None; pcs = []
def hook(pc):
    if pc in (0xC368, 0xC375, 0xE8A7, 0xE85B): pcs.append(pc)
g.cpu.hook = hook
def satan():
    for i in range(40):
        X = 0x890 + 48 * i
        if m[X - 0x10] and m[X + 5] == 6: return X
    return None
X0 = None
for fr in range(1, int(sys.argv[2]) + 1):
    m[0xAD] = 60
    X = satan()
    if X is not None: X0 = X
    if X is not None and os.environ.get('HP1') and m[X + 0x14] > 1: m[X + 0x14] = 1
    WK = int(os.environ.get('WALK', '0')); p = (1 if fr <= WK else (0x10 if fr % GAP == 0 else 0)) | FACE
    pcs.clear()
    g.set_inputs(0, p, 0); g.run_frame()
    if fr % 500 == 0 and X0: print('f', fr, 'st', m[X0 - 0xD], m[X0 - 0xC], 'hp', m[X0 + 0x14], 'x', m[X0 - 0xA] << 8 | m[X0 - 9], 'y', m[X0 - 7] << 8 | m[X0 - 6], file=sys.stderr)
    if X0 is None: continue
    X = X0
    if kill is None and pcs and 0xC368 in pcs: kill = fr; print('kill frame', fr)
    if kill is not None:
        sx = m[X - 0xA] << 8 | m[X - 9]; sy = m[X - 7] << 8 | m[X - 6]
        cx = m[0x9C] << 8 | m[0x9D]; cy = m[0x9E] << 8 | m[0x9F]
        spr = []
        sb = g.spritebuf
        for k in range(0, 0x200, 4):
            code, attr, y, x = sb[k], sb[k + 1], sb[k + 2], sb[k + 3]
            if y and y != 0xF8:
                spr.append('%02X%02X@%d,%d' % (attr, code, x | ((attr & 1) << 8), y))
        print('k%d live %d st %02X %02X %02X anim %s x %d y %d cam %d,%d pcs %s' % (fr - kill, m[X - 0x10], m[X - 0xD], m[X - 0xC], m[X - 0xB],
              bytes(m[X:X + 5]).hex(), sx, sy, cx, cy, ','.join('%X' % c for c in pcs)))
        if os.environ.get('SPR'): print('   ', ' '.join(spr))
        if fr - kill > 95: break
