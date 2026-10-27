"""cmp.py <arc.fb> <arc first frame> <port.fb> <port first frame> <offset port-arc> <a0> <a1>
Per arcade frame f in a0..a1: IoU of the non-black pixel masks (port frame f+offset), the share of pixels whose
colour agrees (each channel within 40), and whether each picture changed from the previous frame."""
import sys
af, a_first, pf, p_first, off, a0, a1 = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])
SZ = 256 * 224 * 3
A = open(af, 'rb'); P = open(pf, 'rb')
def get(fh, i):
    fh.seek(i * SZ); return fh.read(SZ)
Y0, Y1 = int(__import__('os').environ.get('Y0', '0')), int(__import__('os').environ.get('Y1', '224'))
pa = pp = None
tot_iou = 0; n = 0; chg_a = set(); chg_p = set(); same = 0; rows = []
for f in range(a0, a1 + 1):
    a = get(A, f - a_first); p = get(P, f + off - p_first)
    if len(a) < SZ or len(p) < SZ: break
    inter = uni = agree = 0
    for y in range(Y0, Y1):
        for x in range(0, 256):
            i = (y * 256 + x) * 3
            an = a[i] > 24 or a[i + 1] > 24 or a[i + 2] > 24
            pn = p[i] > 24 or p[i + 1] > 24 or p[i + 2] > 24
            if an or pn:
                uni += 1
                if an and pn: inter += 1
            if abs(a[i] - p[i]) < 40 and abs(a[i + 1] - p[i + 1]) < 40 and abs(a[i + 2] - p[i + 2]) < 40: agree += 1
    iou = inter / uni if uni else 1.0
    ag = agree / ((Y1 - Y0) * 256)
    ca = pa is not None and a != pa; cp = pp is not None and p != pp
    if ca: chg_a.add(f)
    if cp: chg_p.add(f)
    rows.append((f, iou, ag, ca, cp))
    pa, pp = a, p
for r in rows:
    if '-v' in sys.argv: print('%d iou %.3f agree %.4f %s%s' % (r[0], r[1], r[2], 'A' if r[3] else '.', 'P' if r[4] else '.'))
N = len(rows)
print('frames %d..%d: mean IoU %.3f, IoU>=0.9 on %d, mean agree %.4f, agree>=0.995 on %d' % (
    a0, rows[-1][0], sum(r[1] for r in rows) / N, sum(1 for r in rows if r[1] >= 0.9), sum(r[2] for r in rows) / N, sum(1 for r in rows if r[2] >= 0.995)))
print('arcade changes %d, port changes %d, on the same frames %d, port-only %d, arcade-only %d' % (
    len(chg_a), len(chg_p), len(chg_a & chg_p), len(chg_p - chg_a), len(chg_a - chg_p)))
