"""port_checkpoint.py <core> <rom> <frames> <out>: stage 2 via SCRIPT (devscript.py 2 0): walk to x > 4900, die,
save <out>_cp.state 30 frames after the respawn at the checkpoint (x 4736, camera 4608)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lrbase
lrbase.setup(globals())
# mkcp2: dev-launch stage 2 (SCRIPT from devscript, players), walk right with jumps + invincibility until x > 4900,
# then boxers, no invincibility, stand; save <out>_cp.state 30 frames after the respawn at x 4736.
def w8(a, v):
    p = L.retro_get_memory_data(2); C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v
phase = 0; t = 0; deaths = 0; was_dying = 0
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    r = ram(); x = rd(r, 0xFF9001, 2); dying = rd(r, 0xFFC571, 1)
    if os.environ.get("V") and f % 500 == 0: print(f, phase, x, dying, rd(r, 0xFF7FF0, 4))
    if dying and not was_dying: deaths += 1
    was_dying = dying
    if f > 1500 and phase == 0:
        w8(0xFFC309, 60)
        # each life shifts the jump phase by 7 frames, so a gap one timing falls into is cleared on a later life
        SCRIPT[:] = [(f, f, 0x180 if (f + 7 * deaths) % 40 < 5 else 0x80)]
        if x > 4900: phase = 1; w8(0xFFC328, 1); w8(0xFFC309, 0)
    elif phase == 1:
        SCRIPT[:] = [(f, f, 0)]
        if dying: phase = 2
    elif phase == 2:
        SCRIPT[:] = [(f, f, 0)]
        if not dying and x == 4736 and rd(r, 0xFFA200, 2) == 4608: phase = 3; t = f + 30
    elif phase == 3 and f >= t:
        n = L.retro_serialize_size(); b = C.create_string_buffer(n); L.retro_serialize(b, n)
        open(out + '_cp.state', 'wb').write(b.raw); print('saved at frame', f); break
    L.retro_run()
else:
    print('no checkpoint, phase', phase)
