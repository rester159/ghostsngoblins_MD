"""Boot Demon's Crest headlessly (snes9x libretro core, in-process) with a
scripted pad and save a state, e.g. for tools/headless/snes_capture.py.

usage: dc_boot.py <core> <rom> <script> <out.state> [--shots PNG] [--every N]
                  [--from STATE] [--poke OFF=VAL[,OFF=VAL]]

script: comma-separated 'a-b:mask' events like snes_capture.py (frames a..b
inclusive, mask = hex bits of libretro joypad ids: B=0 Y=1 SELECT=2 START=3
UP=4 DOWN=5 LEFT=6 RIGHT=7 A=8 X=9 L=10 R=11). The state is saved after the
last frame of the script (the largest b, or 'end:N' to run N frames).
--shots PNG writes a contact sheet of the picture every N frames (default 30),
four per row, to see where he is.
--poke writes WRAM bytes (hex offsets into $7E0000) every frame, e.g.
$7E000D=0C keeps Firebrand's health full.

DC controls: B jump (B again in the air flies), Y fire. Jumping into a wall
makes Firebrand cling to it; Y with the pad held towards the wall fires from it.

usage: dc_boot.py <core> <rom> --recipe cling <out.state>
replays the whole route to a wall (RECIPES below, about 13,000 frames): boot
and START, Somulo's arena (health $7E1062 held at 4; the boss's hit counter
$7E1336 set to 1 so the next hit ends phase 1), his head in the graveyard
(shot down normally), the pickup, then right to the gargoyle pillar, where
the last step jumps into it: the saved state has Firebrand clinging to its
left side, facing right. Run tools/headless/snes_capture.py from it, e.g.
script "1-20:80,21-23:82,24-50:80" (cling, fire from the wall, cling).
"""
import ctypes as C
import os
import struct
import sys
import zlib


class Snes:
    def __init__(self, core, rom):
        self.L = L = C.CDLL(core)
        self.frame = 0
        self.ev = []
        self.fmt = 0
        self.pic = None
        ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
        VID = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
        AS = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
        ASB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
        IP = C.CFUNCTYPE(None)
        IS = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

        def env(cmd, data):
            cmd &= 0xFFFF
            if cmd == 10:
                self.fmt = C.cast(data, C.POINTER(C.c_int))[0]
                return True
            if cmd in (9, 31):
                C.cast(data, C.POINTER(C.c_char_p))[0] = b'.'
                return True
            return False

        def vid(data, w, h, pitch):
            if data:
                self.pic = (C.string_at(data, pitch * h), w, h, pitch)

        def instate(port, dev, idx, id_):
            if port:
                return 0
            for a, b, m in self.ev:
                if a <= self.frame <= b:
                    if (m >> id_) & 1:
                        return 1
            return 0

        self.cbs = [ENV(env), VID(vid), AS(lambda l, r: None), ASB(lambda d, n: n),
                    IP(lambda: None), IS(instate)]
        L.retro_set_environment(self.cbs[0]); L.retro_set_video_refresh(self.cbs[1])
        L.retro_set_audio_sample(self.cbs[2]); L.retro_set_audio_sample_batch(self.cbs[3])
        L.retro_set_input_poll(self.cbs[4]); L.retro_set_input_state(self.cbs[5])
        L.retro_init()

        class GI(C.Structure):
            _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]

        data = open(rom, 'rb').read()
        self.buf = C.create_string_buffer(data, len(data))
        assert L.retro_load_game(C.byref(GI(rom.encode(), C.cast(self.buf, C.c_void_p), len(data), None)))
        L.retro_serialize_size.restype = C.c_size_t

    def load(self, path):
        st = open(path, 'rb').read()
        self.L.retro_run()
        assert self.L.retro_unserialize(C.create_string_buffer(st, len(st)), len(st))

    def save(self, path):
        n = self.L.retro_serialize_size()
        sb = C.create_string_buffer(n)
        assert self.L.retro_serialize(sb, n)
        open(path, 'wb').write(sb.raw)

    def wram(self):
        self.L.retro_get_memory_data.restype = C.c_void_p
        return self.L.retro_get_memory_data(2)        # RETRO_MEMORY_SYSTEM_RAM

    def poke(self, pokes):
        p = self.wram()
        for a, v in pokes:
            C.c_uint8.from_address(p + a).value = v

    def run(self):
        self.frame += 1
        self.L.retro_run()

    def rgb(self):
        """(w, h, bytes RGB) of the last picture"""
        data, w, h, pitch = self.pic
        out = bytearray()
        for y in range(h):
            for x in range(w):
                if self.fmt == 1:                       # XRGB8888
                    b, g, r, _ = data[y * pitch + 4 * x:y * pitch + 4 * x + 4]
                else:                                   # RGB565 (2) / 0RGB1555 (0)
                    v = data[y * pitch + 2 * x] | data[y * pitch + 2 * x + 1] << 8
                    if self.fmt == 2:
                        r, g, b = (v >> 11) << 3, (v >> 5 & 63) << 2, (v & 31) << 3
                    else:
                        r, g, b = (v >> 10 & 31) << 3, (v >> 5 & 31) << 3, (v & 31) << 3
                out += bytes((r, g, b))
        return w, h, bytes(out)

    def png(self, path):
        write_png(path, *self.rgb())


def write_png(path, w, h, px):
    rows = b''.join(b'\0' + px[y * w * 3:(y + 1) * w * 3] for y in range(h))
    chunk = lambda t, b: struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b))
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def sheet(path, pics, cols=4):
    """pics: [(w, h, px)] of one size -> one PNG grid"""
    w, h = pics[0][0], pics[0][1]
    rows = (len(pics) + cols - 1) // cols
    W = w * cols
    out = bytearray(W * h * rows * 3)
    for i, (_, _, px) in enumerate(pics):
        ox, oy = (i % cols) * w, (i // cols) * h
        for y in range(h):
            p = ((oy + y) * W + ox) * 3
            out[p:p + w * 3] = px[y * w * 3:(y + 1) * w * 3]
    write_png(path, W, h * rows, bytes(out))


def parse(script):
    ev, end = [], 0
    for part in script.split(','):
        part = part.strip()
        if not part:
            continue
        rng, m = part.split(':')
        if rng == 'end':
            end = max(end, int(m))
            continue
        a, b = rng.split('-')
        ev.append((int(a), int(b), int(m, 16)))
        end = max(end, int(b))
    return ev, end


def loop(period, parts, until):
    """the same events every `period` frames up to `until`"""
    ev, f = [], 1
    while f < until:
        ev += ['%d-%d:%s' % (f + a, f + b, m) for a, b, m in parts]
        f += period
    return ','.join(ev)


# jump and fire facing left: Somulo and his head
FIGHT = loop(110, [(0, 1, '40'), (3, 16, '1'), (22, 85, '1')] +
             [(k, k + 2, '2') for k in range(26, 86, 8)], 4000)
HP = (0x1062, 4)
# (script, frames, pokes once at the start, pokes every frame)
RECIPES = {
    'cling': [
        ('600-605:8,700-705:8,800-805:8,900-905:8,1000-1005:8', 2500, [], []),
        ('', 900, [], [HP]),                         # Somulo walks through the arena
        ('1-800:80', 800, [], [HP]),                 # to the right wall
        (FIGHT, 1499, [(0x1336, 1)], [HP]),          # phase 1 ends on the next hit
        ('1-800:80', 800, [], [HP]),                 # graveyard: up to the head
        ('1-4:80,5-20:81,21-150:80', 150, [], [HP]),
        (FIGHT, 3599, [], [HP]),                     # the head, shot down
        ('1-1000:80', 1000, [], [HP]),
        ('1-400:40', 1600, [], [HP]),                # the pickup; next area
        (loop(80, [(0, 39, '80'), (40, 55, '83'), (56, 79, '80')], 1500), 1520, [], [HP]),
        ('1-4:80,5-20:81,21-40:80', 40, [], [HP]),   # into the pillar: cling
    ],
}


def recipe(core, rom, name, out):
    s = Snes(core, rom)
    for script, frames, once, every in RECIPES[name]:
        s.ev, _ = parse(script)
        s.frame = 0
        s.poke(once)
        while s.frame < frames:
            s.poke(every)
            s.run()
    s.save(out)
    print('saved', out)


def main():
    if sys.argv[3] == '--recipe':
        recipe(sys.argv[1], sys.argv[2], sys.argv[4], sys.argv[5])
        return
    core, rom, script, out = sys.argv[1:5]
    opts = dict(zip(sys.argv[5::2], sys.argv[6::2]))
    s = Snes(core, rom)
    if '--from' in opts:
        s.load(opts['--from'])
    s.ev, end = parse(script)
    shots, every = opts.get('--shots'), int(opts.get('--every', '30'))
    pics = []
    pokes = [tuple(int(x, 16) for x in kv.split('=')) for kv in opts.get('--poke', '').split(',') if kv]
    while s.frame < end:
        s.poke(pokes)
        s.run()
        if shots and s.frame % every == 0 and s.pic:
            pics.append(s.rgb())
    s.save(out)
    if shots and pics:
        sheet(shots, pics)
    print('saved', out, 'after', s.frame, 'frames')


if __name__ == '__main__':
    main()
