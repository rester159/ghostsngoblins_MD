"""port_start.py <core> <rom> <frames> <out>: SCRIPT (a devscript.py launch) until Arthur x == TX and camera
x == TC (and y == TCY if given) in play; saves <out>_st.state 30 frames later."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lrbase
lrbase.setup(globals())
# mkstart: run SCRIPT (dev launch) until Arthur x == TX and camera x == TC with play live; save <out>_st.state 30 frames later
TX, TC = int(os.environ['TX']), int(os.environ['TC']); t = None
TCY = int(os.environ['TCY']) if os.environ.get('TCY') else None   # camera y too, when camera x alone is ambiguous (stage 3: 0)
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    L.retro_run()
    r = ram()
    if t is None and f > 1200 and rd(r, 0xFF9001, 2) == TX and rd(r, 0xFFA200, 2) == TC and (TCY is None or rd(r, 0xFFA202, 2) == TCY) and rd(r, 0xFF7FF0, 4) == 0x4C495645:
        t = f + 30
    if t and f == t:
        n = L.retro_serialize_size(); b = C.create_string_buffer(n); L.retro_serialize(b, n)
        open(out + '_st.state', 'wb').write(b.raw); print('saved', f); break
else:
    print('not reached')
