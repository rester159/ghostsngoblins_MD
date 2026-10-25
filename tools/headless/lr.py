"""Headless libretro runner (Genesis Plus GX) for scripted tests. No window.

usage: lr.py <core.dylib> <rom> <frames> <out prefix>

Environment:
  SCRIPT / SCRIPT2  pad 1 / pad 2 input, "a-b:mask,..." (frames a..b, libretro
                    joypad bits: B=1 Y=2 SELECT=4 START=8 UP=10 DOWN=20 LEFT=40
                    RIGHT=80 A=100; Genesis B=B, C=A, A=Y)
  POKE              "frame:addr:hex,..." writes to 68k RAM before that frame
  DUMP_AT           "f f ..." frames to save <out>_<f>.{state,ram,png}
  STEP              print WATCH every STEP frames (default 120)
  WATCH             "addr ..." 68k RAM to print (byte; prefix 1 for a long, e.g. 1FF9000)
  PNG=1             also save a PNG at every STEP
  REGION            genesis_plus_gx_region_detect value (e.g. pal, ntsc-u)
  LOAD              save state to start from (works with any core)
  WAV               write the audio to this .wav file
"""
import ctypes as C
import os
import struct
import sys
import zlib

core, rom, frames, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
L = C.CDLL(core)
fb = {'d': None, 'w': 0, 'h': 0, 'p': 0}
fmt = [1]
keep = []
frame_no = [0]


def parse(name):
    ev = []
    for part in os.environ.get(name, '').split(','):
        if part.strip():
            rng, m = part.split(':')
            a, b = rng.split('-')
            ev.append((int(a), int(b), int(m, 16)))
    return ev


SCRIPT, SCRIPT2 = parse('SCRIPT'), parse('SCRIPT2')


class Var(C.Structure):
    _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]


ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VID = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AS = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
ASB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
IP = C.CFUNCTYPE(None)
IS = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)
sysdir = C.c_char_p((os.path.dirname(out) or '.').encode())


def env(cmd, data):
    cmd &= 0xFFFF
    if cmd == 10:
        fmt[0] = C.cast(data, C.POINTER(C.c_int))[0]
        return True
    if cmd in (9, 31):
        C.cast(data, C.POINTER(C.c_char_p))[0] = sysdir.value
        return True
    if cmd == 15 and os.environ.get('REGION'):
        v = C.cast(data, C.POINTER(Var))[0]
        if v.key == b'genesis_plus_gx_region_detect':
            keep.append(C.c_char_p(os.environ['REGION'].encode()))
            C.cast(data, C.POINTER(Var))[0].value = keep[-1].value
            return True
    return False


def vid(d, w, h, p):
    if d:
        fb.update(d=bytes(C.string_at(d, p * h)), w=w, h=h, p=p)


def instate(port, dev, idx, id_):
    ev = SCRIPT if port == 0 else SCRIPT2 if port == 1 else []
    for a, b, m in ev:
        if a <= frame_no[0] <= b:
            return 1 if (m >> id_) & 1 else 0
    return 0


pcm = []


def audio(d, n):
    if os.environ.get('WAV'):
        pcm.append(C.string_at(d, n * 4))
    return n


cbs = [ENV(env), VID(vid), AS(lambda l, r: None), ASB(audio), IP(lambda: None), IS(instate)]
L.retro_set_environment(cbs[0]); L.retro_set_video_refresh(cbs[1]); L.retro_set_audio_sample(cbs[2])
L.retro_set_audio_sample_batch(cbs[3]); L.retro_set_input_poll(cbs[4]); L.retro_set_input_state(cbs[5])
L.retro_init()


class GI(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]


data = open(rom, 'rb').read()
buf = C.create_string_buffer(data, len(data))
assert L.retro_load_game(C.byref(GI(rom.encode(), C.cast(buf, C.c_void_p), len(data), None))), 'load failed'
if SCRIPT2:
    L.retro_set_controller_port_device(1, 1)
L.retro_get_memory_data.restype = C.c_void_p
L.retro_get_memory_size.restype = C.c_size_t
L.retro_serialize_size.restype = C.c_size_t


def ram():
    p = L.retro_get_memory_data(2)
    return C.string_at(p, L.retro_get_memory_size(2))


def rd(r, a, n):
    return int.from_bytes(bytes(r[(a - 0xFF0000 + k) ^ 1] for k in range(n)), 'big')


def png(path):
    w, h, p, d = fb['w'], fb['h'], fb['p'], fb['d']
    rows = b''
    for y in range(h):
        r = d[y * p:y * p + w * (4 if fmt[0] == 1 else 2)]
        rows += b'\0'
        if fmt[0] == 1:
            rows += b''.join(bytes((r[i + 2], r[i + 1], r[i])) for i in range(0, len(r), 4))
        else:
            for i in range(0, len(r), 2):
                v = r[i] | r[i + 1] << 8
                rows += bytes(((v >> 11 & 31) << 3, (v >> 5 & 63) << 2, (v & 31) << 3))
    ch = lambda t, b: struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b))
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                           + ch(b'IDAT', zlib.compress(rows)) + ch(b'IEND', b''))


if os.environ.get('LOAD'):                     # start from a save state (frame numbers continue from 1)
    st = open(os.environ['LOAD'], 'rb').read()
    L.retro_run()
    assert L.retro_unserialize(C.create_string_buffer(st, len(st)), len(st)), 'state load failed'

pokes = []
for pk in os.environ.get('POKE', '').split(','):
    if pk.strip():
        f, a, v = pk.split(':')
        pokes.append((int(f), int(a, 16), v))
dump_at = set(int(x) for x in os.environ.get('DUMP_AT', '').split())
step = int(os.environ.get('STEP', '120'))
watch = [int(x, 16) for x in os.environ.get('WATCH', '').split()]

for f in range(1, frames + 1):
    frame_no[0] = f
    for pf, pa, pv in pokes:
        if pf == f:
            p = L.retro_get_memory_data(2)
            n = (len(pv) + 1) // 2
            v = int(pv, 16)
            for k in range(n):
                C.c_uint8.from_address(p + ((pa - 0xFF0000 + k) ^ 1)).value = (v >> (8 * (n - 1 - k))) & 0xFF
    L.retro_run()
    if f in dump_at:
        n = L.retro_serialize_size()
        b = C.create_string_buffer(n)
        L.retro_serialize(b, n)
        open('%s_%05d.state' % (out, f), 'wb').write(b.raw)
        open('%s_%05d.ram' % (out, f), 'wb').write(ram())
        png('%s_%05d.png' % (out, f))
    if f % step == 0:
        r = ram()
        w = ' '.join('%X=%08X' % (a & 0xFFFFFF, rd(r, a & 0xFFFFFF, 4)) if a >> 24 else
                     '%X=%02X' % (a, rd(r, a, 1)) for a in watch)
        print('%s frame %d state %s' % (w, f, bytes(r[(0x7FF0 + k) ^ 1] for k in range(4))))
        if os.environ.get('PNG') == '1':
            png('%s_%05d.png' % (out, f))

if os.environ.get('WAV'):
    import wave
    av = C.create_string_buffer(64)            # retro_system_av_info: timing.sample_rate at +32
    L.retro_get_system_av_info(av)
    rate = int(C.c_double.from_buffer_copy(av.raw, 32).value)
    with wave.open(os.environ['WAV'], 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate); w.writeframes(b''.join(pcm))
