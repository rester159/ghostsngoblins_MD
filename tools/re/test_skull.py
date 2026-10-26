"""Check src_patch/skull.c (stage 5's skulls, type 9) against the arcade itself.

Runs the arcade (tools/arcade/gng.py) from a stage 5 state with Arthur
invincible and a scripted mix of walking, jumping and crouching, and records
every call of the type-9 handler ($CC45) in states 0 and 1: the slot image and
the inputs at entry (<$A0/<$A2 Arthur, <$9C/<$9E camera), the results of the
floor probes it makes ($8CA7: carry and B) and the image at its return. The
same C code as the ROM's (compiled for the host with -DHOST) runs on each entry
image with those probe results; the whole slot image must match.

usage: test_skull.py <arcade state> <frames> [seed]
  TP=frame:x,...  teleports Arthur (x) at those frames, e.g. next to skulls.
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
long host_probe[16]; int host_np, host_ip;
long sk_floor(void *slot) { return host_ip < host_np ? host_probe[host_ip++] : -1; }
void sk_sound(int id) { }
'''


class Ctx(ctypes.Structure):
    _fields_ = [('camx', ctypes.c_uint16), ('camy', ctypes.c_uint16), ('ax', ctypes.c_uint16),
                ('ay', ctypes.c_uint16), ('frame', ctypes.c_uint8), ('slot', ctypes.c_uint8),
                ('rank', ctypes.c_uint8)]


def build():
    d = tempfile.mkdtemp()
    open(os.path.join(d, 'stub.c'), 'w').write(STUB)
    so = os.path.join(d, 'skull.so')
    subprocess.check_call(['cc', '-O1', '-shared', '-fPIC', '-DHOST', '-Wno-unused-function', '-I',
                           os.path.join(ROOT, 'src_patch'), os.path.join(ROOT, 'src_patch', 'skull.c'),
                           os.path.join(d, 'stub.c'), '-o', so])
    return ctypes.CDLL(so)


def record(state, frames, seed):
    g = GnG(os.path.join(ROOT, 'rom'))
    g.load(state)
    m = g.mem
    w = lambda a: m[a] << 8 | m[a + 1]
    calls, cur, ret = [], {}, []
    tp = [tuple(int(v) for v in t.split(':')) for t in os.environ.get('TP', '').split(',') if t]

    def hook(pc):
        x = g.cpu.x
        if pc == 0xCC45 and m[x + 5] == 9 and m[x - 0xD] < 2:
            cur[x] = dict(frame=f, x=x, pre=bytes(m[x - 0x10:x + 0x20]), probes=[],
                          inp=(w(0x9C), w(0x9E), w(0xA0), w(0xA2), m[0x21], m[0xE0], m[0x9A]))
        elif pc == 0x8CA7 and x in cur:
            ret.append((g.cpu.r16(g.cpu.s), x))
        elif ret and pc == ret[-1][0]:
            _, xx = ret.pop()
            if xx in cur:
                cur[xx]['probes'].append((0x10000 | g.cpu.b) if g.cpu.cc & 1 else 0)
        elif pc == 0xA0C9 and x in cur:                # back in the enemy loop
            c = cur.pop(x)
            c['post'] = bytes(m[x - 0x10:x + 0x20])
            calls.append(c)
    g.cpu.hook = hook
    rnd = random.Random(seed)
    pad = 0
    for f in range(frames):
        m[0xAD] = 0x60                                  # invincible
        for tf, tx in tp:
            if f == tf: m[0x506] = tx >> 8; m[0x507] = tx & 255
        if f % 20 == 0:
            pad = rnd.choice([0, 0, 0, 1, 2, 4, 5, 6, 0x21, 0x22, 0x20])
        g.set_inputs(0, pad, 0)
        g.run_frame()
    return calls


def main():
    args = sys.argv[1:]
    state, frames = args[0], int(args[1])
    seed = int(args[2]) if len(args) > 2 else 1
    lib = build()
    calls = record(state, frames, seed)
    probe = (ctypes.c_long * 16).in_dll(lib, 'host_probe')
    np_ = ctypes.c_int.in_dll(lib, 'host_np')
    ip = ctypes.c_int.in_dll(lib, 'host_ip')
    bad = 0
    states = {}
    for c in calls:
        buf = (ctypes.c_uint8 * 48)(*c['pre'])
        for k, v in enumerate(c['probes'][:16]): probe[k] = v
        np_.value = len(c['probes']); ip.value = 0
        lib.skull_host(buf, ctypes.byref(Ctx(*c['inp'])))
        got = bytes(buf)
        diff = [k for k in range(48) if got[k] != c['post'][k]]
        key = (c['pre'][3], c['pre'][4], c['pre'][5])
        states[key] = states.get(key, 0) + 1
        if diff or ip.value != np_.value:
            bad += 1
            if bad <= 10:
                print('frame %d slot %04x state %s: bytes %s probes %d/%d' % (
                    c['frame'], c['x'] - 0x10, key, ['+%02x %02x/%02x' % (k, got[k], c['post'][k]) for k in diff],
                    ip.value, np_.value))
    print('%d handler calls, states %s: %d mismatches' % (
        len(calls), ' '.join('%d/%d/%d:%d' % (k + (v,)) for k, v in sorted(states.items())), bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
