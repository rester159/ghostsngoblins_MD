"""Summarise the DMA ring of a probe_rom.py build: bytes moved during the active
display (lines 0-223, where a VRAM DMA runs at ~16 bytes/line in H32 and halts
the CPU) versus during VBlank, per destination.

usage: dma_log.py <ram dump>"""
import collections
import sys

raw = open(sys.argv[1], 'rb').read()
R = bytes(raw[i ^ 1] for i in range(len(raw)))
w = lambda o: R[o] << 8 | R[o + 1]
ents = []
for k in range(256):
    o = 0x3000 + 8 * k
    v, n, dst, fr = w(o) >> 8, w(o + 2), w(o + 4), w(o + 6)
    if n:
        ents.append((fr, v, n, dst))
if not ents:
    sys.exit('no entries')
frames = max(e[0] for e in ents) - min(e[0] for e in ents) + 1
act = collections.Counter()
vbl = collections.Counter()
for fr, v, n, dst in ents:
    (act if v < 224 else vbl)[dst & 0xFE00] += n
ta, tv = sum(act.values()), sum(vbl.values())
print('%d DMAs over %d frames: active display %d bytes/frame (~%.1f stalled lines/frame), VBlank %d bytes/frame'
      % (len(ents), frames, ta // frames, ta / frames / 16, tv // frames))
for dst, n in act.most_common(8):
    print('  active  VRAM %04X: %5d bytes/frame' % (dst, n // frames))
for dst, n in vbl.most_common(4):
    print('  vblank  VRAM %04X: %5d bytes/frame' % (dst, n // frames))
