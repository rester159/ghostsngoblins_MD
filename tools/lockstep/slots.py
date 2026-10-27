"""slots.py arc <state> <frames> | port <core> <rom> <frames> <out>: per frame, the enemy slots of TYPES (all slots
when unset) as 'slot:type:states:x,y' + the frame counter; arcade PAD/POKE (f:addr:hex), port PAD/POKE (lr form);
Arthur invincible in both; HOLDX=x Arthur's x held (both); SHOTS=1 also the 6 enemy shots (as slots 100-105:
the arcade's projectiles $13D0, the port's shot pool $FFC100, which is the arcade's <$A7/<$A8 pool). The port's
lines end with its update count and rng_lag (POKE it on frame 1 to line $FFA206 up with <$21, as in Fixed 51);
cmp_slots.py compares two logs update for update."""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
types = [int(t) for t in os.environ.get('TYPES', '').split(',') if t]
shots = os.environ.get('SHOTS')
holdx = int(os.environ['HOLDX']) if os.environ.get('HOLDX') else None
pad = int(os.environ.get('PAD', '0'), 16)       # the game's own pad bits
pk = [(int(a), int(b, 16), c) for a, b, c in (x.split(':') for x in os.environ.get('POKE', '').split(',') if x)]


def lag_addr():
    """rng_lag (hud.s) from the build's symbols (its address moves with the build)"""
    try:
        for l in open(os.path.join(ROOT, 'src_patch', 'build', 'patch.sym')):
            if l.split()[-1] == 'rng_lag': return int(l.split()[0], 16)
    except OSError:
        pass
    return 0xFF5608


def line(f, fc, sl):
    return '%d fc %02x %s' % (f, fc, ' '.join(sl))


if sys.argv[1] == 'arc':
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'arcade'))
    from gng import GnG
    g = GnG(os.path.join(ROOT, 'rom')); g.load(sys.argv[2]); m = g.mem
    w = lambda a: m[a] << 8 | m[a + 1]
    for f in range(1, int(sys.argv[3]) + 1):
        for a, b, c in pk:
            if a == f: m[b] = int(c, 16)
        m[0xAD] = 60; m[0x60] = 3
        if holdx is not None: m[0x506] = holdx >> 8; m[0x507] = holdx & 255
        g.set_inputs(0, pad, 0); g.run_frame()
        sl = []
        for i in range(40):
            x = 0x880 + 48 * i + 0x10
            if m[x - 16] and (not types or m[x + 5] in types):
                sl.append('%d:%d:%d%d%d:%d,%d' % (i, m[x + 5], m[x - 13], m[x - 12], m[x - 11], w(x - 10), w(x - 7)))
        if shots:
            for k in range(6):                  # projectiles $13D0 (32 bytes, X): slot 100 + k, type +5
                x = 0x13D0 + 32 * k
                if m[x - 16]:
                    sl.append('%d:%d:%d%d%d:%d,%d' % (100 + k, m[x + 5], m[x - 13], m[x - 12], m[x - 11], w(x - 10), w(x - 7)))
        print(line(f, m[0x21], sl))
else:
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'lockstep'))
    import lrbase
    G = {'__file__': os.path.join(ROOT, 'tools', 'lockstep', 'lrbase.py')}
    lrbase.setup(G)
    L, C, ram, rd, SCRIPT = G['L'], G['C'], G['ram'], G['rd'], G['SCRIPT']
    p = L.retro_get_memory_data(2)
    LAG = lag_addr()

    def w8(a, v):
        C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v & 255
    for f in range(1, int(G['frames']) + 1):
        G['frame_no'][0] = f
        for a, b, c in pk:
            if a == f:
                n = (len(c) + 1) // 2; v = int(c, 16)
                for k in range(n): w8(b + k, v >> (8 * (n - 1 - k)))
        w8(0xFFC309, 60); w8(0xFFC500, 3)
        if holdx is not None: w8(0xFF9001, holdx >> 8); w8(0xFF9002, holdx)
        SCRIPT[:] = [(f, f, pad)]
        L.retro_run()
        r = ram()
        sl = []
        for i in range(40):
            a = 0xFFB800 + 48 * i
            if rd(r, a + 4, 1) and (not types or rd(r, a + 10, 1) in types):
                sl.append('%d:%d:%d%d%d:%d,%d' % (i, rd(r, a + 10, 1), rd(r, a + 7, 1), rd(r, a + 8, 1), rd(r, a + 9, 1),
                                                rd(r, a + 17, 2), rd(r, a + 21, 2)))
        if shots:
            for k in range(6):                  # the shot pool $FFC100 (48 bytes; x/y words at +0/+2)
                a = 0xFFC100 + 48 * k
                if rd(r, a + 4, 1):
                    sl.append('%d:%d:%d%d%d:%d,%d' % (100 + k, rd(r, a + 10, 1), rd(r, a + 7, 1), rd(r, a + 8, 1),
                                                    rd(r, a + 9, 1), rd(r, a, 2), rd(r, a + 2, 2)))
        print(line(f, rd(r, 0xFFA206, 1), sl) + ' upd %d lag %02x' % (rd(r, 0xFF7084, 4), rd(r, LAG, 1)))
