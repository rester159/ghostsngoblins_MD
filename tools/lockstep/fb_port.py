"""port_frames.py <core> <rom> <frames> <out>: lr harness; FR="a b" dumps raw framebuffers (RGB 3 bytes, 256x224
cropped) of frames a..b into <out>.fb, and prints the G_STATE / frame counter at each frame with a change."""
import os, sys
sys.path.insert(0, os.path.join(os.environ['W'], 'tools', 'lockstep'))
import lrbase
lrbase.setup(globals())
a, b = map(int, os.environ['FR'].split())
pokes = []
for pk in os.environ.get('POKE', '').split(','):
    if pk.strip():
        f, ad, v = pk.split(':'); pokes.append((int(f), int(ad, 16), int(v, 16)))
fo = open(out + '.fb', 'wb')
info = open(out + '.txt', 'w')
dump_at = set(int(x) for x in os.environ.get('DUMP_AT', '').split())
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    for pf, pa, pv in pokes:
        if pf == f: lrbase.w8(globals(), pa, pv)
    L.retro_run()
    if f in dump_at:
        n = L.retro_serialize_size(); bb = C.create_string_buffer(n); L.retro_serialize(bb, n)
        open('%s_%05d.state' % (out, f), 'wb').write(bb.raw); open('%s_%05d.ram' % (out, f), 'wb').write(ram())
    if a <= f <= b:
        w, h, p, d = fb['w'], fb['h'], fb['p'], fb['d']
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
        if f == a: info.write('fb %d %d\n' % (w, h))
        fo.write(b''.join(rows))
        r = ram()
        info.write('%d %s %d\n' % (f, bytes(r[(0x7FF0 + k) ^ 1] for k in range(4)), rd(r, 0xFF7DFC, 4)))
