"""Check src_patch/petite.c (the arcade's Petite Devils, type 2) against the arcade itself.

Runs the arcade (tools/arcade/gng.py) from a state, with Arthur invincible and
a scripted mix of walking, jumping, crouching and throwing, and records every
call of the type-2 handler ($A89C) in states 0 and 1: the slot image and the
inputs at entry (<$A0/<$A2 Arthur, <$9C/<$9E camera, <$21, <$E0, <$9A, the
free shot count <$A7, the rock-face globals $1574-$1579, the random state
$6E/$6F) and the image, globals, random state and shots at its return. The
same C code as the ROM's (compiled for the host with -DHOST) runs on each
entry image; the whole slot image (animation included), the globals, the
random state and the fireballs must match.

usage: test_petite.py <arcade state> <frames> [seed]
  SPAWN=slot:subtype:x:y,...  makes devils first (type 2, state 0) in the
  given arcade slots (0-39), x/y absolute, e.g. to exercise subtype 1, which
  the scripted runs don't reach in stage 4.
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
unsigned short host_rstate;
unsigned char arc_rand(void)
{
    unsigned short s = host_rstate;
    unsigned char b = ~(unsigned char)((s >> 8) ^ s);
    s = (unsigned short)(s << 1) | ((b >> 6) & 1);
    host_rstate = s;
    return (unsigned char)s;
}
int host_nsound;
void pd_sound(int id) { host_nsound++; }
'''


class Ctx(ctypes.Structure):
    _fields_ = [('camx', ctypes.c_uint16), ('camy', ctypes.c_uint16), ('ax', ctypes.c_uint16),
                ('ay', ctypes.c_uint16), ('frame', ctypes.c_uint8), ('slot', ctypes.c_uint8),
                ('rank', ctypes.c_uint8)]


class Glob(ctypes.Structure):
    _fields_ = [('last_y', ctypes.c_uint16), ('toggle', ctypes.c_uint8), ('pad', ctypes.c_uint8),
                ('last_x', ctypes.c_uint16)]


def build():
    d = tempfile.mkdtemp()
    open(os.path.join(d, 'stub.c'), 'w').write(STUB)
    so = os.path.join(d, 'petite.so')
    subprocess.check_call(['cc', '-O1', '-shared', '-fPIC', '-DHOST', '-Wno-unused-function', '-I',
                           os.path.join(ROOT, 'src_patch'), os.path.join(ROOT, 'src_patch', 'petite.c'),
                           os.path.join(d, 'stub.c'), '-o', so])
    return ctypes.CDLL(so)


def record(state, frames, seed):
    g = GnG(os.path.join(ROOT, 'rom'))
    g.load(state)
    m = g.mem
    for sp in os.environ.get('SPAWN', '').split(','):
        if sp:
            sl, sub, x, y = (int(v) for v in sp.split(':'))
            a = 0x880 + 48 * sl
            m[a:a + 48] = bytes(48)
            m[a] = 1; m[a + 2] = sub; m[a + 0x15] = 2
            m[a + 6] = x >> 8; m[a + 7] = x & 255; m[a + 9] = y >> 8; m[a + 10] = y & 255
    w = lambda a: m[a] << 8 | m[a + 1]
    calls, cur = [], {}

    def hook(pc):
        x = g.cpu.x
        if pc == 0xA89C and m[x + 5] == 2 and m[x - 0xD] < 2:
            cur[x] = dict(frame=f, x=x, pre=bytes(m[x - 0x10:x + 0x20]), rs=w(0x6E), free=m[0xA7],
                          glob=bytes(m[0x1574:0x157A]),
                          inp=(w(0x9C), w(0x9E), w(0xA0), w(0xA2), m[0x21], m[0xE0], m[0x9A]))
        elif pc == 0xA0C9 and x in cur:                # back in the enemy loop
            c = cur.pop(x)
            c['post'] = bytes(m[x - 0x10:x + 0x20]); c['rs2'] = w(0x6E)
            c['glob2'] = bytes(m[0x1574:0x157A]); c['free2'] = m[0xA7]
            calls.append(c)
    g.cpu.hook = hook
    rnd = random.Random(seed)
    pad = 0
    for f in range(frames):
        m[0xAD] = 0x60                                  # invincible
        if f % 20 == 0:
            pad = rnd.choice([0, 0, 1, 2, 4, 5, 6, 0x21, 0x22, 0x20, 0x11, 0x12, 0x10, 0x14])
        p = pad if f % 20 < 12 else (pad & 0x0F) | (0x10 if f & 2 else 0)
        g.set_inputs(0, p, 0)
        g.run_frame()
    return calls


def main():
    args = sys.argv[1:]
    state, frames = args[0], int(args[1])
    seed = int(args[2]) if len(args) > 2 else 1
    lib = build()
    calls = record(state, frames, seed)
    rs = ctypes.c_uint16.in_dll(lib, 'host_rstate')
    free = ctypes.c_int.in_dll(lib, 'host_free')
    nshot = ctypes.c_int.in_dll(lib, 'host_nshot')
    glob = Glob.in_dll(lib, 'pd_glob')
    bad = 0
    states = {}
    nshots = 0
    for c in calls:
        buf = (ctypes.c_uint8 * 48)(*c['pre'])
        i = Ctx(*c['inp'])
        rs.value = c['rs']
        free.value = c['free']
        nshot.value = 0
        g0 = c['glob']
        glob.last_y = g0[0] << 8 | g0[1]; glob.toggle = g0[3]; glob.last_x = g0[4] << 8 | g0[5]
        lib.petite_step(buf, ctypes.byref(i))
        got = bytes(buf)
        diff = [k for k in range(48) if got[k] != c['post'][k]]
        g1 = c['glob2']
        gok = (glob.last_y, glob.toggle, glob.last_x) == (g1[0] << 8 | g1[1], g1[3], g1[4] << 8 | g1[5])
        shots = c['free'] - c['free2']
        nshots += shots
        key = (c['pre'][2], c['pre'][3], c['pre'][4], c['pre'][5])
        states[key] = states.get(key, 0) + 1
        if diff or rs.value != c['rs2'] or not gok or nshot.value != shots:
            bad += 1
            if bad <= 10:
                print('frame %d slot %04x sub/state %s: bytes %s rand %04x/%04x glob %s shots %d/%d' % (
                    c['frame'], c['x'] - 0x10, key, ['+%02x %02x/%02x' % (k, got[k], c['post'][k]) for k in diff],
                    rs.value, c['rs2'], gok, nshot.value, shots))
    print('%d handler calls, %d fireballs, subtype/states %s: %d mismatches' % (
        len(calls), nshots, ' '.join('%d/%d/%d/%d:%d' % (k + (v,)) for k, v in sorted(states.items())), bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
