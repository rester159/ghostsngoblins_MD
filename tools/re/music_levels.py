"""Loudness of every sound id, played from the developer menu's sound test.

usage: music_levels.py <rom> [secs] [ids]   (ids: "25,47" or "25-63"; default 25-63)

Boots to the developer menu (as tools/lockstep/devscript.py), selects SOUND
TEST, then for each id sets the persistent sound-test id ($FF5009), presses A,
records `secs` of audio and prints its loudness in dBFS: the RMS over the
windows (100 ms) where it plays (within 30 dB of its loudest), the loudest
window, the peak and the clipped samples, and how long it plays. Emulators clip
the summed YM2612 output where a console mixes its channels in analog, so the
FM preamp is set to PREAMP percent (default 25: nothing clips; +12 dB gives the
level at the core's default 100). WAV=<dir> also writes <dir>/snd_<id>.wav."""
import array
import ctypes as C
import math
import os
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'headless'))
import fbh  # noqa: E402

rom = sys.argv[1]
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
spec = sys.argv[3] if len(sys.argv) > 3 else '25-63'
ids = []
for part in spec.split(','):
    a, _, b = part.partition('-')
    ids += range(int(a, 0), int(b or a, 0) + 1)

pre = int(os.environ.get('PREAMP', '25'))
g = fbh.Game(rom, options={'genesis_plus_gx_fm_preamp': str(pre)})
boost = 20 * math.log10(100 / pre)
buf = array.array('h')
rec = [False]


def audio(d, n):
    if rec[0]:
        buf.frombytes(C.string_at(d, n * 4))
    return n


g._cbs[3] = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)(audio)
g.L.retro_set_audio_sample_batch(g._cbs[3])

# boot menu -> HOME, the developer code, A opens the developer menu
D = 40
script = [(580 + D, 583 + D, 0x20), (600 + D, 605 + D, 0x100)]
f = 640 + D
for b in (0x10, 0x20, 0x10, 0x20, 0x40, 0x80, 0x40, 0x80):
    script.append((f, f + 3, b)); f += 10
script.append((740 + D, 745 + D, 0x100)); f = 780 + D
for _ in range(5):                       # down to SOUND TEST
    script.append((f, f + 3, 0x20)); f += 10
g.script = script
g.mask = 0
g.run(f + 30)
g.script = []
fps = 60
res = []
for sid in ids:
    g.w8(0xFF5009, sid)
    g.run(10, 0)
    g.run(4, 0x100)
    g.run(1, 0)
    del buf[:]
    rec[0] = True
    g.run(int(secs * fps), 0)
    rec[0] = False
    s = buf
    if not len(s):
        continue
    win = 4410 * 2
    w = []
    for i in range(0, len(s) - win + 1, win):
        c = s[i:i + win]
        w.append(sum(v * v for v in c) / win)
    top = max(w)
    act = [x for x in w if x > top / 1000] or [0]
    db = lambda x: 10 * math.log10(x / 32768 ** 2) + boost if x else -999
    pk = max(abs(min(s)), max(s))
    clip = sum(1 for v in s if abs(v) >= 32767)
    res.append((sid, db(sum(act) / len(act)), db(top)))
    print('%3d $%02X  rms %6.1f  loudest %6.1f  peak %6.1f dBFS  clipped %d  plays %4.1f s' %
          (sid, sid, res[-1][1], res[-1][2], 20 * math.log10(max(pk, 1) / 32768) + boost, clip,
           len(act) * 0.1), flush=True)
    if os.environ.get('WAV'):
        with wave.open(os.path.join(os.environ['WAV'], 'snd_%02d.wav' % sid), 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100); w.writeframes(s.tobytes())
