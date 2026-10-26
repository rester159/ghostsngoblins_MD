"""arc_start.py <stage index 0-6> <checkpoint 0/1> <out.state>: boots the arcade (coin, start), pokes the stage
index $72 and checkpoint $81 during the boot, and saves a state 30 frames after the camera reaches the restart
point (Arthur in play). Matches port_start.py's 30 frames, so spawn timers start in the same phase."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'arcade'))
from gng import GnG
st, cp, outp = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
g = GnG(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'rom')); m = g.mem
t = None; x0 = None
for f in range(1, 4000):
    if 820 <= f < 1320 and f % 10 == 0: m[0x72] = st; m[0x81] = cp
    g.set_inputs(0x40 if 700 <= f <= 710 else (1 if 800 <= f <= 805 else 0), 0, 0); g.run_frame()
    x = m[0x506] << 8 | m[0x507]; cam = m[0x9C] << 8 | m[0x9D]
    if t is None and f > 1320 and x > 200 and cam != 0: t = f + 30; print('restart at frame', f, 'x', x, 'cam', cam)
    if t and f == t: g.save(outp); print('saved', f); break
