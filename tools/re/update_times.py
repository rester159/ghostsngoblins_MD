"""Per-update durations from a probe_rom.py ring in a RAM dump.

usage: update_times.py <ram dump> [lines per frame: 262 NTSC (default) / 313 PAL]
Each entry holds the V counter and frame counter at the start and the end of
one update; the frame counter steps at the start of VBlank (line 224).
"""
import sys

raw = open(sys.argv[1], 'rb').read()
R = bytes(raw[i ^ 1] for i in range(len(raw)))
LPF = int(sys.argv[2]) if len(sys.argv) > 2 else 262
w = lambda o: R[o] << 8 | R[o + 1]


def t(v, fc):                        # absolute line number
    return fc * LPF + ((v - 224) % LPF)


lines = []
for k in range(64):
    o = 0x2C00 + 8 * k
    vs, fs, ve, fe = w(o) >> 8, w(o + 2), w(o + 4) >> 8, w(o + 6)
    if not (fs or fe):
        continue
    d = t(ve, fe) - t(vs, fs)
    if 0 < d < 4 * LPF:
        lines.append(d)
lines.sort()
if not lines:
    sys.exit('no entries')
p = lambda q: lines[min(len(lines) - 1, int(q * len(lines)))]
print('%d updates (lines; one frame = %d): median %d, p90 %d, max %d; over one frame: %d%%'
      % (len(lines), LPF, p(0.5), p(0.9), lines[-1], 100 * sum(1 for x in lines if x > LPF) // len(lines)))
