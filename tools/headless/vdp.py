"""VDP state from a Genesis Plus GX save state (VRAM, CRAM, registers), and a
sprite-table dump.

usage: vdp.py sat <state>     print the linked sprite list
"""
import sys

BASE = 0x12425          # VRAM offset in a GPGX 1.7.x state; CRAM and regs follow


def load(path):
    st = open(path, 'rb').read()
    vram = bytes(st[BASE + (i ^ 1)] for i in range(0x10000))
    cram = st[BASE + 0x10000:BASE + 0x10080]
    regs = st[BASE + 0x10100:BASE + 0x10120]
    return vram, cram, regs


def palette(path):
    """64 RGB colours from CRAM."""
    cram = load(path)[1]
    lv = [0, 52, 87, 116, 144, 172, 206, 255]
    out = []
    for i in range(64):
        w = cram[i * 2] | cram[i * 2 + 1] << 8
        out.append((lv[w & 7], lv[w >> 3 & 7], lv[w >> 6 & 7]))
    return out


def sprites(path):
    v, _, r = load(path)
    sat = (r[5] & 0x7F) << 9
    i, out = 0, []
    for _ in range(80):
        e = v[sat + i * 8:sat + i * 8 + 8]
        a = e[4] << 8 | e[5]
        out.append(dict(i=i, y=((e[0] << 8 | e[1]) & 0x3FF) - 128, x=((e[6] << 8 | e[7]) & 0x1FF) - 128,
                        w=(e[2] >> 2 & 3) + 1, h=(e[2] & 3) + 1, tile=a & 0x7FF, pal=a >> 13 & 3,
                        hf=a >> 11 & 1, vf=a >> 12 & 1, link=e[3] & 0x7F))
        i = e[3] & 0x7F
        if not i:
            break
    return out


if __name__ == '__main__' and sys.argv[1] == 'sat':
    for s in sprites(sys.argv[2]):
        print('%(i)2d y=%(y)4d x=%(x)4d %(w)dx%(h)d tile=%(tile)03X pal=%(pal)d hf=%(hf)d link=%(link)d' % s)
