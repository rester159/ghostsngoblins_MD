"""arc_restart.py <entry hex 8> <out.state> [stage index, default 4]: arc_start.py for that stage index with its
checkpoint-0 restart entry (RAM $6CED + 4 x index, poked during the boot) replaced (restart_entry.py is the port's);
saves 30 frames after the restart."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'arcade'))
from gng import GnG
ent = bytes.fromhex(sys.argv[1]); outp = sys.argv[2]; st = int(sys.argv[3]) if len(sys.argv) > 3 else 4
g = GnG(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'rom')); m = g.mem
t = None
for f in range(1, 4000):
    if 820 <= f < 1320 and f % 10 == 0: m[0x72] = st; m[0x81] = 0
    if 820 <= f < 1320: m[0x6CED + 4 * st:0x6CED + 4 * st + 4] = ent
    g.set_inputs(0x40 if 700 <= f <= 710 else (1 if 800 <= f <= 805 else 0), 0, 0); g.run_frame()
    x = m[0x506] << 8 | m[0x507]; cam = m[0x9C] << 8 | m[0x9D]
    if t is None and f > 1320 and x > 200 and (cam or m[0x9E] or m[0x9F]):
        t = f + 30; print('restart at frame', f, 'x', x, 'y', m[0x509] << 8 | m[0x50A], 'cam', cam, m[0x9E] << 8 | m[0x9F])
    if t and f == t:
        g.save(outp); print('saved', f, 'x', x, 'y', m[0x509] << 8 | m[0x50A]); break
