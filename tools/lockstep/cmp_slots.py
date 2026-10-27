"""cmp_slots.py <arc log> <port log> <offset>: slots.py logs; port updates (from its first = 1) = arcade frame + offset;
compares each slot's presence and x,y (STATES=1: and the state bytes); prints spawn/removal frames per slot."""
import os, sys
off = int(sys.argv[3]); st = os.environ.get('STATES')


def parse(fn, port):
    out = {}; seen = set(); base = None
    for l in open(fn):
        w = l.split()
        f = int(w[0])
        if port:
            u = int(w[w.index('upd') + 1])
            if u in seen: continue
            seen.add(u)
            if base is None: base = u - 1
            f = u - base
            w = w[:w.index('upd')]
        d = {}
        for e in w[3:]:
            s, t, ss, xy = e.split(':')
            d[int(s)] = (t, ss, xy) if st else (t, xy)
        out[f] = d
    return out


a = parse(sys.argv[1], False); p = parse(sys.argv[2], True)
bad = 0; n = 0
for f in sorted(a):
    if f + off not in p: continue
    n += 1
    if a[f] != p[f + off]:
        bad += 1
        if bad <= int(os.environ.get('SHOW', '10')): print('arc %d %s\nport %d %s' % (f, a[f], f + off, p[f + off]))
print('%d frames compared, %d differ' % (n, bad))


def events(d, o):
    ev = []; prev = {}
    for f in sorted(d):
        cur = d[f]
        for s in cur:
            if s not in prev: ev.append((f - o, 'spawn', s, cur[s][-1]))
        for s in prev:
            if s not in cur: ev.append((f - o, 'gone', s, prev[s][-1]))
        prev = cur
    return ev


print('arcade:', events(a, 0))
print('port  :', events(p, off))
