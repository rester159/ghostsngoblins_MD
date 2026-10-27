"""arc_frames.py <W> <state> <first frame of state+1> <last> <out.fb>: render arcade frames to raw RGB 256x224.
SYS env: frames with Start (unused here). Starts from a saved state."""
import sys, os, time
W, st, last, outp = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
sys.path.insert(0, os.path.join(W, 'tools', 'arcade'))
from gng import GnG
g = GnG(os.path.join(W, 'rom'))
g.load(st)
fo = open(outp, 'wb')
t = time.time()
f0 = g.frame + 1
while g.frame < last:
    g.set_inputs(0, 0, 0)
    g.run_frame()
    img = g.render()
    fo.write(b''.join(bytes(v for p in r for v in p) for r in img))
print('frames', f0, g.frame, 't', time.time() - t)
