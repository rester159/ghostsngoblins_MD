"""In-process handle on the port in Genesis Plus GX (headless), for bots that
search with save states: Game(rom).launch(stage, players) boots it from the
developer menu (tools/lockstep/devscript.py), then step(mask, n), save(),
load(), r8/r16/r32, w8, png(). Masks are libretro pad bits: B = 1 (fire),
UP 0x10, DOWN 0x20, LEFT 0x40, RIGHT 0x80, A = 0x100 (jump).
options: core variables, e.g. {'genesis_plus_gx_overclock': '200%'}."""
import ctypes as C
import os
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.expanduser('~/Library/Application Support/RetroArch/cores/genesis_plus_gx_libretro.dylib')
F, U, D, LT, RT, J = 0x1, 0x10, 0x20, 0x40, 0x80, 0x100


class _Var(C.Structure):
    _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]


class _GI(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]


class Game:
    def __init__(self, rom, core=CORE, sysdir='.', options=None):
        self.L = L = C.CDLL(core)
        self._opts = {k.encode(): C.c_char_p(v.encode()) for k, v in (options or {}).items()}
        self.mask = 0
        self.script = []                        # (a, b, mask) by frame, for the launch
        self.frame = 0
        self.fb = None
        self._fmt = 1
        self._sys = C.c_char_p(sysdir.encode())
        ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
        VID = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
        AS = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
        ASB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
        IP = C.CFUNCTYPE(None)
        IS = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

        def env(cmd, data):
            cmd &= 0xFFFF
            if cmd == 10:
                self._fmt = C.cast(data, C.POINTER(C.c_int))[0]
                return True
            if cmd in (9, 31):
                C.cast(data, C.POINTER(C.c_char_p))[0] = self._sys.value
                return True
            if cmd == 15:                       # GET_VARIABLE
                v = C.cast(data, C.POINTER(_Var))[0]
                if v.key in self._opts:
                    C.cast(data, C.POINTER(_Var))[0].value = self._opts[v.key].value
                    return True
            return False

        def vid(d, w, h, p):
            if d and self.want_video:
                self.fb = (bytes(C.string_at(d, p * h)), w, h, p)

        def inp(port, dev, idx, id_):
            if port:
                return 0
            m = self.mask
            for a, b, sm in self.script:
                if a <= self.frame <= b:
                    m = sm
                    break
            return (m >> id_) & 1

        self.want_video = False
        self._cbs = [ENV(env), VID(vid), AS(lambda l, r: None), ASB(lambda d, n: n), IP(lambda: None), IS(inp)]
        L.retro_set_environment(self._cbs[0]); L.retro_set_video_refresh(self._cbs[1])
        L.retro_set_audio_sample(self._cbs[2]); L.retro_set_audio_sample_batch(self._cbs[3])
        L.retro_set_input_poll(self._cbs[4]); L.retro_set_input_state(self._cbs[5])
        L.retro_init()
        data = open(rom, 'rb').read()
        self._rom = C.create_string_buffer(data, len(data))
        assert L.retro_load_game(C.byref(_GI(rom.encode(), C.cast(self._rom, C.c_void_p), len(data), None)))
        L.retro_get_memory_data.restype = C.c_void_p
        L.retro_get_memory_size.restype = C.c_size_t
        L.retro_serialize_size.restype = C.c_size_t
        self._ram = L.retro_get_memory_data(2)
        self._ssize = L.retro_serialize_size()

    # memory (68k work RAM, byte-swapped in the core)
    def r8(self, a):
        return C.c_uint8.from_address(self._ram + ((a - 0xFF0000) ^ 1)).value

    def r16(self, a):
        return self.r8(a) << 8 | self.r8(a + 1)

    def r32(self, a):
        return self.r16(a) << 16 | self.r16(a + 2)

    def w8(self, a, v):
        C.c_uint8.from_address(self._ram + ((a - 0xFF0000) ^ 1)).value = v & 0xFF

    def run(self, n=1, mask=None, each=None):
        if mask is not None:
            self.mask = mask
        for _ in range(n):
            self.frame += 1
            self.L.retro_run()
            if each:
                each(self)

    def save(self):
        b = C.create_string_buffer(self._ssize)
        self.L.retro_serialize(b, self._ssize)
        return (b.raw, self.frame)

    def load(self, st):
        raw, self.frame = st
        assert self.L.retro_unserialize(C.create_string_buffer(raw, len(raw)), len(raw))

    def launch(self, stage, players=2, poke=None):
        """Developer-menu launch; returns once play has started ($FFC305 = 1).
        poke(game) runs after every frame of it."""
        ev = subprocess.check_output([sys.executable, os.path.join(HERE, '..', 'lockstep', 'devscript.py'),
                                      str(stage), str(players)]).decode().strip()
        self.script = []
        for part in ev.split(','):
            rng, m = part.split(':')
            a, b = rng.split('-')
            self.script.append((int(a), int(b), int(m, 16)))
        self.mask = 0
        while not (self.frame > 1320 and self.r8(0xFFC305) == 1):
            self.run(1, None, poke)
        self.script = []

    def png(self, path):
        if not self.fb:
            return
        d, w, h, p = self.fb
        rows = bytearray()
        for y in range(h):
            r = d[y * p:y * p + w * (4 if self._fmt == 1 else 2)]
            rows += b'\0'
            if self._fmt == 1:
                for i in range(0, len(r), 4):
                    rows += bytes((r[i + 2], r[i + 1], r[i]))
            else:
                for i in range(0, len(r), 2):
                    v = r[i] | r[i + 1] << 8
                    rows += bytes(((v >> 11 & 31) << 3, (v >> 5 & 63) << 2, (v & 31) << 3))
        ch = lambda t, b: struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b))
        open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                               + ch(b'IDAT', zlib.compress(bytes(rows))) + ch(b'IEND', b''))
