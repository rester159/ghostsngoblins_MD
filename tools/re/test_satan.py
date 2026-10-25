"""Check src_patch/satan.c (the arcade's Satan) against the arcade itself.

Runs the arcade (tools/arcade/gng.py) from a state with Satans in play, with
Arthur invincible and a scripted mix of walking, jumping, crouching and
throwing, and records every call of the Satan handler ($BED5): the slot
image and the inputs at entry (<$A0/<$A2 Arthur, <$9C/<$9E camera, <$21,
<$9A, $051F, the random state $6E/$6F) and the image, random state and shots
($C24C) at its return. The same C code as the ROM's (compiled for the host
with -DHOST) is then run on each entry image; the states, x/y, timers and
the whole of the slot's AI bytes, the random state and the shots must match.
Animation bytes (X+0..X+4) and the hit points (X+$14, the weapon code's) are
not compared.

usage: test_satan.py <arcade state> <frames> [seed]
       (POKE=addr:hex,... sets arcade RAM first, e.g. a Satan's y)
The state needs Satans in play: e.g. a stage 5 or 6 respawn state with the
restart table ($6CED/$6D09, 4 bytes per stage index: $4000 | screen y << 5 |
screen x, then x and y in the screen) pointed at the boss room (stage 5:
screen $1C,$06; stage 6: $1D,$0A) and a death to respawn there.
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
int nfire; unsigned char fire_dir[64];
void host_fire(const unsigned char *s, unsigned char d) { if (nfire < 64) fire_dir[nfire] = d; nfire++; }
'''


class In(ctypes.Structure):
    _fields_ = [('ax', ctypes.c_uint16), ('ay', ctypes.c_uint16), ('camx', ctypes.c_uint16),
                ('camy', ctypes.c_uint16), ('c21', ctypes.c_uint8), ('rank', ctypes.c_uint8),
                ('crouch', ctypes.c_uint8)]


def build():
    d = tempfile.mkdtemp()
    open(os.path.join(d, 'stub.c'), 'w').write(STUB)
    so = os.path.join(d, 'satan.so')
    subprocess.check_call(['cc', '-O1', '-shared', '-fPIC', '-DHOST', '-I', os.path.join(ROOT, 'src_patch'),
                           os.path.join(ROOT, 'src_patch', 'satan.c'), os.path.join(d, 'stub.c'), '-o', so])
    return ctypes.CDLL(so)


def record(state, frames, seed):
    g = GnG(os.path.join(ROOT, 'rom'))
    g.load(state)
    m = g.mem
    for pk in os.environ.get('POKE', '').split(','):   # addr:hex, e.g. d39:0620 (a Satan's y)
        if pk:
            a, v = pk.split(':')
            m[int(a, 16):int(a, 16) + len(v) // 2] = bytes.fromhex(v)
    w = lambda a: m[a] << 8 | m[a + 1]
    calls, cur = [], {}

    def hook(pc):
        x = g.cpu.x
        if pc == 0xBED5 and m[x + 5] == 6:
            cur[x] = dict(frame=f, x=x, pre=bytes(m[x - 0x10:x + 0x20]), rs=w(0x6E),
                          inp=(w(0xA0), w(0xA2), w(0x9C), w(0x9E), m[0x21], m[0x9A], m[0x51F]), shots=[])
        elif pc == 0xC256 and g.cpu.x in cur:          # STB -2,Y: a shot's direction
            cur[g.cpu.x]['shots'].append(g.cpu.b)
        elif pc == 0xA0C9 and x in cur:                # back in the enemy loop
            c = cur.pop(x)
            c['post'] = bytes(m[x - 0x10:x + 0x20]); c['rs2'] = w(0x6E)
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
    nfire = ctypes.c_int.in_dll(lib, 'nfire')
    fdir = (ctypes.c_uint8 * 64).in_dll(lib, 'fire_dir')
    skip = set(range(0x10, 0x15)) | {0x24, 0x02}       # anim bytes, hit points, hit flag
    bad = 0
    states = {}
    nshots = 0
    for c in calls:
        if c['pre'][3] >= 2:
            continue                                   # dying / removal: the port's own code
        buf = (ctypes.c_uint8 * 48)(*c['pre'])
        i = In(*c['inp'])
        rs.value = c['rs']
        nfire.value = 0
        lib.satan_step(buf, ctypes.byref(i))
        got = bytes(buf)
        diff = [k for k in range(48) if k not in skip and got[k] != c['post'][k]]
        shots = list(fdir[:nfire.value])
        nshots += len(c['shots'])
        key = (c['pre'][3], c['pre'][4], c['pre'][5])
        states[key] = states.get(key, 0) + 1
        if diff or rs.value != c['rs2'] or shots != c['shots']:
            bad += 1
            if bad <= 10:
                print('frame %d slot %04x state %s: bytes %s rand %04x/%04x shots %s/%s' % (
                    c['frame'], c['x'] - 0x10, key, ['+%02x %02x/%02x' % (k, got[k], c['post'][k]) for k in diff],
                    rs.value, c['rs2'], shots, c['shots']))
    print('%d handler calls, %d shots, states %s: %d mismatches' % (
        len(calls), nshots, ' '.join('%d/%d/%d:%d' % (k + (v,)) for k, v in sorted(states.items())), bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
