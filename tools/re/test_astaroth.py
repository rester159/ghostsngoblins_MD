"""Check src_patch/astaroth.c (the arcade's Astaroth) against the arcade itself.

Runs the arcade (tools/arcade/gng.py) from a final-room state with Arthur
invincible and a scripted mix of walking, jumping and crouching, and records
every call of Astaroth's handler ($DAD9, type 13): the slot image and the
inputs at entry (<$A0 Arthur's x, <$9C/<$9E camera, <$21, <$9A, <$E0, <$A7,
the random state $6E/$6F) and the image, random state and shots ($DD12) at
its return. The same C code as the ROM's (compiled for the host with -DHOST)
is then run on each entry image; the states, x/y, timers and the whole of
the slot's AI bytes, the random state and the shots must match. Animation
bytes (X+0..X+4) and the hit points (X+$16, the weapon code's) are not
compared.

usage: test_astaroth.py <arcade state> <frames> [seed]
       DIE=n kills Arthur on frame n (a respawn re-creates Astaroth, so its init
       and wake-up are covered; the default is frame 1).
The state needs the final room: e.g. arc_stage_states/rs_6_0.state.
"""
import ctypes
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'arcade'))
from gng import GnG  # noqa: E402

STUB = r'''
unsigned short host_rstate; unsigned char host_rlast;
unsigned char arc_rand(void)
{
    unsigned short s = host_rstate;
    unsigned char b = ~(unsigned char)((s >> 8) ^ s);
    s = (unsigned short)(s << 1) | ((b >> 6) & 1);
    host_rstate = s; host_rlast = (unsigned char)s;
    return (unsigned char)s;
}
'''


class In(ctypes.Structure):
    _fields_ = [('ax', ctypes.c_uint16), ('camx', ctypes.c_uint16), ('camy', ctypes.c_uint16),
                ('c21', ctypes.c_uint8), ('rank', ctypes.c_uint8), ('e0', ctypes.c_uint8),
                ('free_shots', ctypes.c_uint8)]


def build():
    d = tempfile.mkdtemp()
    open(os.path.join(d, 'stub.c'), 'w').write(STUB)
    so = os.path.join(d, 'astaroth.so')
    subprocess.check_call(['cc', '-O1', '-shared', '-fPIC', '-DHOST', '-I', os.path.join(ROOT, 'src_patch'),
                           os.path.join(ROOT, 'src_patch', 'astaroth.c'), os.path.join(d, 'stub.c'), '-o', so])
    return ctypes.CDLL(so)


def record(state, frames, seed):
    g = GnG(os.path.join(ROOT, 'rom'))
    g.load(state)
    m = g.mem
    w = lambda a: m[a] << 8 | m[a + 1]
    calls, cur = [], {}
    die = int(os.environ.get('DIE', '1'))

    def hook(pc):
        x = g.cpu.x
        if pc == 0xDAD9 and m[x + 5] == 13:
            cur[x] = dict(frame=f, x=x, pre=bytes(m[x - 0x10:x + 0x20]), rs=w(0x6E),
                          inp=(w(0xA0), w(0x9C), w(0x9E), m[0x21], m[0x9A], m[0xE0], m[0xA7]), shots=[])
        elif pc == 0xDD49 and x in cur:                # the shot's x/y are set
            y = g.cpu.y
            cur[x]['shots'].append((w(y - 0xA), w(y - 7), m[y - 2], m[y + 6]))
        elif pc == 0xDD66 and x in cur and cur[x]['shots'] and m[x + 0x12]:
            y = g.cpu.y                                # high shot: moved
            cur[x]['shots'][-1] = (w(y - 0xA), w(y - 7), m[y - 2], m[y + 6])
        elif pc == 0xA0C9 and x in cur:                # back in the enemy loop
            c = cur.pop(x)
            c['post'] = bytes(m[x - 0x10:x + 0x20]); c['rs2'] = w(0x6E)
            calls.append(c)
    g.cpu.hook = hook
    rnd = random.Random(seed)
    pad = 0
    for f in range(frames):
        if f == die:
            m[0x60] = max(m[0x60], 3)
            m[0x90] = 1
        elif f > die + 30:
            m[0xAD] = 0x60                              # invincible
        if f % 20 == 0:
            pad = rnd.choice([0, 0, 1, 2, 4, 5, 6, 0x21, 0x22, 0x20, 1, 1, 2, 2, 0, 0])
        g.set_inputs(0, pad, 0)
        g.run_frame()
    return calls


def main():
    args = sys.argv[1:]
    state, frames = args[0], int(args[1])
    seed = int(args[2]) if len(args) > 2 else 1
    lib = build()
    calls = record(state, frames, seed)
    rs = ctypes.c_uint16.in_dll(lib, 'host_rstate')
    lib.ast_step.restype = ctypes.c_int
    sx = ctypes.c_uint16.in_dll(lib, 'ast_shot_x')
    sy = ctypes.c_uint16.in_dll(lib, 'ast_shot_y')
    skip = set(range(0x10, 0x15)) | {0x26}             # anim bytes, hit points
    bad = 0
    states = {}
    nshots = 0
    for c in calls:
        if c['pre'][3] >= 2:
            continue                                   # dying / removal: the port's own code
        buf = (ctypes.c_uint8 * 48)(*c['pre'])
        i = In(*c['inp'])
        rs.value = c['rs']
        r = lib.ast_step(buf, ctypes.byref(i))
        got = bytes(buf)
        diff = [k for k in range(48) if k not in skip and got[k] != c['post'][k]]
        shots = []
        if r & 3:
            shots = [(sx.value, sy.value, got[0x28], got[0x2A] >> 1)]
        nshots += len(c['shots'])
        key = (c['pre'][3], c['pre'][4])
        states[key] = states.get(key, 0) + 1
        if diff or rs.value != c['rs2'] or shots != c['shots']:
            bad += 1
            if bad <= 10:
                print('frame %d slot %04x state %s: bytes %s rand %04x/%04x shots %s/%s' % (
                    c['frame'], c['x'] - 0x10, key, ['+%02x %02x/%02x' % (k, got[k], c['post'][k]) for k in diff],
                    rs.value, c['rs2'], shots, c['shots']))
    rapid = sum(1 for c in calls if c['post'][0x1D])
    high = sum(1 for c in calls if c['shots'] and c['post'][0x22])
    print('%d handler calls (%d in rapid fire), %d shots (%d high), states %s: %d mismatches' % (
        len(calls), rapid, nshots, high, ' '.join('%d/%d:%d' % (k + (v,)) for k, v in sorted(states.items())), bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
