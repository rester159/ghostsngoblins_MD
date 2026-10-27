"""port_end_fb.py <core> <rom> <frames> <out>: port_end.py's forced second clear, framebuffers of e<E0>..e<E1>
(ENV E="e0 e1") to <out>.fb, e = frames from the forced end (e1 the first after it)."""
import os, sys
sys.path.insert(0, os.path.join(os.environ['W'], 'tools', 'lockstep'))
import lrbase
lrbase.setup(globals())
def w8(a, v):
    p = L.retro_get_memory_data(2); C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v
e0, e1 = map(int, os.environ['E'].split())
live_seen = False
START = None; LOOP = int(os.environ.get('LOOPED', '1'))
fo = open(out + '.fb', 'wb'); info = open(out + '.txt', 'w')
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    if f >= 1000 and not live_seen:
        rm0 = ram()
        if bytes(rm0[(0x7FF0 + k) ^ 1] for k in range(4)) == b'LIVE': live_seen = True; w8(0xFF500B, 1)
        else: w8(0xFF500B, 7)
    w8(0xFFC309, 60)
    if START is None and f > 1310:
        r = ram()
        if rd(r, 0xFF9001, 2) == 8024 and rd(r, 0xFF7084, 4) > 330: START = f + 30
    if f == START:
        w8(0xFFDB08, 1); w8(0xFFDB0A, 0); w8(0xFFDB0B, 0); w8(0xFF7FC0, LOOP)
    L.retro_run()
    if START is None: continue
    e = f - START + 1
    if e0 <= e <= e1:
        d, p = fb['d'], fb['p']
        rows = []
        for y in range(224):
            r = d[y * p:y * p + 256 * (4 if fmt[0] == 1 else 2)]
            if fmt[0] == 1:
                rows.append(b''.join(bytes((r[i + 2], r[i + 1], r[i])) for i in range(0, len(r), 4)))
            else:
                rr = bytearray()
                for i in range(0, len(r), 2):
                    v = r[i] | r[i + 1] << 8
                    rr += bytes(((v >> 11 & 31) << 3, (v >> 5 & 63) << 2, (v & 31) << 3))
                rows.append(bytes(rr))
        fo.write(b''.join(rows))
        rm = ram()
        info.write('e%d f%d %s cnt %d gf %d\n' % (e, f, bytes(rm[(0x7FF0 + k) ^ 1] for k in range(4)), rd(rm, 0xFF7DFC, 4), rd(rm, 0xFF7084, 4)))
    if str(e) in os.environ.get('DUMP_E', '').split():
        open('%s_e%d.ram' % (out, e), 'wb').write(ram())
        n = L.retro_serialize_size(); bb = C.create_string_buffer(n); L.retro_serialize(bb, n); open('%s_e%d.state' % (out, e), 'wb').write(bb.raw)
    if e > e1: break
