"""port_satan_death.py <core> <rom> <frames> <out>: stage 5 room life start (TX), walk right WALK frames, then fire every GAP
frames; Satan hit points (+11) held at 1; logs from the kill (+7 = 2): +4 +7 +9 +30 +36 per frame, and the sprite
table entries (VRAM via state) with tiles in the Satan's buffers (SPR=1)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'headless'))
import lrbase
lrbase.setup(globals())


def w8(a, v):
    p = L.retro_get_memory_data(2); C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v


TX = int(os.environ.get('TX', '7008')); WALK = int(os.environ.get('WALK', '200')); GAP = int(os.environ.get('GAP', '12'))
r0 = None; kill = None; slot = None
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    r = ram(); ax = rd(r, 0xFF9001, 2)
    if r0 is None and f > 1200 and rd(r, 0xFF7FF0, 4) == 0x4C495645 and ax == TX: r0 = f
    if r0 is not None:
        t = f - r0 - 36
        m = 0x80 if 0 < t <= WALK else (1 if t > WALK and t % GAP == 0 else 0)
        SCRIPT[:] = [(f, f, m)]
        for i in range(40):
            s = 0xFFB800 + 48 * i
            if rd(r, s + 4, 1) and rd(r, s + 10, 1) == 6:
                slot = s
                if rd(r, s + 11, 1) > 1 and rd(r, s + 7, 1) < 2: w8(s + 11, 1)
    w8(0xFFC309, 60)
    L.retro_run()
    if slot is None: continue
    r = ram(); s = slot
    if kill is None and rd(r, s + 7, 1) == 2: kill = f; print('kill at r%d upd%d' % (f - r0, rd(r, 0xFF7084, 4)))
    if kill is not None:
        line = 'k%d live %d st %d cnt %d frame %d cd %d upd %d' % (f - kill, rd(r, s + 4, 1), rd(r, s + 7, 1), rd(r, s + 9, 1),
                                                                 rd(r, s + 30, 2), rd(r, s + 36, 2), rd(r, 0xFF7084, 4))
        if os.environ.get('SPR'):
            import vdp
            n = L.retro_serialize_size(); b = C.create_string_buffer(n); L.retro_serialize(b, n)
            st = b.raw; vram = bytes(st[vdp.BASE + (i ^ 1)] for i in range(0x10000))
            sat = []
            k = 0
            for _ in range(80):
                sb = (st[vdp.BASE + 0x10100 + 5] & 0x7F) << 9; e = vram[sb + k * 8:sb + k * 8 + 8]
                y = (e[0] << 8 | e[1]) & 0x3FF; lk = e[3] & 0x7F; at = e[4] << 8 | e[5]; x = (e[6] << 8 | e[7]) & 0x1FF
                tile = at & 0x7FF
                if 0x500 <= tile < 0x548: sat.append('%03X@%d,%d' % (tile, x - 128, y - 128))
                k = lk
                if not k: break
            line += ' | ' + ' '.join(sat)
        print(line)
        if f - kill > 92: break
