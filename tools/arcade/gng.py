"""Headless arcade Ghosts'n Goblins (Capcom, MAME set `gng`) for reference runs.

Main CPU only: MC6809 at 1.5 MHz (12 MHz / 2 / 4), one VBlank IRQ per frame
held until taken, memory map and ROM layout as MAME's gng driver:
  $0000-$1DFF RAM, $1E00-$1FFF sprite RAM, $2000-$27FF fg video RAM,
  $2800-$2FFF bg video RAM, $3000-$3004 SYSTEM/P1/P2/DSW1/DSW2 (active low),
  $3800/$3900 palette (RRRRGGGG / BBBBxxxx), $3A00 sound latch, $3B08-$3B0B
  bg scroll, $3D00-$3D07 latch, $3E00 bank (4 = gg4 $4000, else gg5 page),
  $4000-$5FFF banked ROM, $6000-$FFFF fixed ROM (gg4 upper half, gg3).
The sound CPU isn't emulated: it only receives the latch and doesn't feed
back into the game logic. The renderer (chars, bg tiles, sprites) is for
checking runs by eye.

usage: gng.py <rom dir> <frames> <out prefix>
Environment (same conventions as tools/headless/lr.py):
  SCRIPT / SCRIPT2  pad input "a-b:mask,...": bits are the arcade's own,
                    1 right 2 left 4 down 8 up 10 fire 20 jump;
                    SYS "a-b:mask" 1 start1 2 start2 40 coin1 80 coin2
  POKE              "frame:addr:hex,..." RAM writes before that frame
  DUMP_AT           "f f ..." frames to save <out>_<f>.{ram,png,state}
  STEP / WATCH      print RAM bytes (prefix 1 for a 16-bit word) every STEP frames
  PNG=1             also save a PNG at every STEP
  LOAD              state file to start from
  DSW1 / DSW2       DIP switch bytes (default ff / ff)
"""
import os
import pickle
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpu6809 import CPU6809  # noqa: E402

CYCLES_PER_FRAME = 1500000 // 60            # 25,000 (the board runs at 59.59 Hz; close enough)


class GnG:
    def __init__(self, romdir):
        rd = lambda n: open(os.path.join(romdir, n), 'rb').read()
        self.rom = bytearray(0x18000)
        self.rom[0x4000:0x8000] = rd('gg4.bin')
        self.rom[0x8000:0x10000] = rd('gg3.bin')
        self.rom[0x10000:0x18000] = rd('gg5.bin')
        self.chars = rd('gg1.bin')
        self.tiles = b''.join(rd(n) for n in ('gg11.bin', 'gg10.bin', 'gg9.bin', 'gg8.bin', 'gg7.bin', 'gg6.bin'))
        ff = b'\xff' * 0x4000
        self.sprites = b''.join((rd('gg17.bin'), rd('gg16.bin'), rd('gg15.bin'), ff,
                                 rd('gg14.bin'), rd('gg13.bin'), rd('gg12.bin'), ff))
        self.mem = bytearray(0x10000)
        self.mem[0x6000:0x10000] = self.rom[0x6000:0x10000]
        self.bank = 0
        self.set_bank(0)
        self.io = {0x3000: 0xFF, 0x3001: 0xFF, 0x3002: 0xFF, 0x3003: 0xFF, 0x3004: 0xFF}
        for a, v in self.io.items():
            self.mem[a] = v
        self.scroll = [0, 0, 0, 0]
        self.latch = [0] * 8
        self.sound = []                       # (frame, value) written to the sound latch
        self.frame = 0
        self.spritebuf = bytes(0x200)
        self.cpu = CPU6809(self.mem, self.write)
        self.cpu.irq_ack = self._ack
        self.cpu.reset()
        self.watch_w = None                   # watch_w(addr, value, pc) on RAM writes, or None

    def _ack(self):
        self.cpu.irq = False

    def set_bank(self, v):
        self.bank = v
        src = 0x4000 if v == 4 else 0x10000 + (v & 3) * 0x2000
        self.mem[0x4000:0x6000] = self.rom[src:src + 0x2000]

    def write(self, a, v):
        if a < 0x3000:
            if self.watch_w and a < 0x2000:
                self.watch_w(a, v, self.cpu.pc)
            self.mem[a] = v
        elif a < 0x4000:
            if 0x3800 <= a < 0x3A00:
                self.mem[a] = v
            elif a == 0x3A00:
                self.sound.append((self.frame, v))
            elif 0x3B08 <= a <= 0x3B0B:
                self.scroll[a - 0x3B08] = v
            elif 0x3D00 <= a <= 0x3D07:
                self.latch[a - 0x3D00] = v & 1
            elif a == 0x3E00:
                self.set_bank(v)
        # ROM: ignored

    def set_inputs(self, sys_, p1, p2, dsw1=0xFF, dsw2=0xFF):
        m = self.mem
        m[0x3000] = (~sys_) & 0xFF
        m[0x3001] = (~p1) & 0xFF
        m[0x3002] = (~p2) & 0xFF
        m[0x3003] = dsw1
        m[0x3004] = dsw2

    def run_frame(self):
        self.cpu.irq = True                     # VBlank
        self.spritebuf = bytes(self.mem[0x1E00:0x2000])   # sprite DMA at VBlank
        self.cpu.run(CYCLES_PER_FRAME)
        self.frame += 1

    # ---- state ------------------------------------------------------------
    def save(self, path):
        c = self.cpu
        st = dict(mem=bytes(self.mem), bank=self.bank, scroll=self.scroll, latch=self.latch,
                  frame=self.frame, spritebuf=self.spritebuf,
                  cpu=(c.a, c.b, c.dp, c.x, c.y, c.u, c.s, c.pc, c.cc, c.cycles, c.irq, c.waiting, c.cwai))
        open(path, 'wb').write(pickle.dumps(st))

    def load(self, path):
        st = pickle.loads(open(path, 'rb').read())
        self.mem[:] = st['mem']
        self.set_bank(st['bank'])
        self.scroll, self.latch, self.frame, self.spritebuf = st['scroll'], st['latch'], st['frame'], st['spritebuf']
        c = self.cpu
        (c.a, c.b, c.dp, c.x, c.y, c.u, c.s, c.pc, c.cc, c.cycles, c.irq, c.waiting, c.cwai) = st['cpu']

    # ---- rendering ----------------------------------------------------------
    def palette(self):
        m = self.mem
        out = []
        for i in range(256):
            rg, bx = m[0x3800 + i], m[0x3900 + i]
            out.append(((rg >> 4) * 17, (rg & 15) * 17, (bx >> 4) * 17))
        return out

    def _char(self, code, px, py):
        b = self.chars[code * 16 + py * 2 + (px >> 2)]
        bit = 3 - (px & 3)
        return ((b >> (bit + 4)) & 1) | (((b >> bit) & 1) << 1)

    def _tile(self, code, px, py):
        o = code * 32 + py + (16 if px >= 8 else 0)
        bit = 7 - (px & 7)
        t = self.tiles
        return (((t[o] >> bit) & 1) | (((t[0x8000 + o] >> bit) & 1) << 1)
                | (((t[0x10000 + o] >> bit) & 1) << 2))

    def _sprite(self, code, px, py):
        o = code * 64 + py * 2 + (32 if px >= 8 else 0) + ((px & 7) >> 2)
        bit = 3 - (px & 3)
        s = self.sprites
        lo, hi = s[o], s[0x10000 + o]
        return ((lo >> (bit + 4)) & 1) | (((lo >> bit) & 1) << 1) | \
               (((hi >> (bit + 4)) & 1) << 2) | (((hi >> bit) & 1) << 3)

    def render(self):
        """256x224 RGB rows (visible lines 16-239)."""
        pal = self.palette()
        m = self.mem
        W, H = 256, 256
        img = [[(0, 0, 0)] * W for _ in range(H)]
        sx = self.scroll[0] | (self.scroll[1] << 8)
        sy = self.scroll[2] | (self.scroll[3] << 8)
        # bg: 32x32 16x16 tiles, column-major
        for y in range(16, 240):
            yy = (y + sy) & 0x1FF
            for x in range(W):
                xx = (x + sx) & 0x1FF
                i = (xx >> 4) * 32 + (yy >> 4)
                code = m[0x2800 + i]; attr = m[0x2C00 + i]
                code |= (attr & 0xC0) << 2
                px, py = xx & 15, yy & 15
                if attr & 0x10: px = 15 - px
                if attr & 0x20: py = 15 - py
                img[y][x] = pal[(attr & 7) * 8 + self._tile(code, px, py)]
        # sprites, back to front
        b = self.spritebuf
        for offs in range(0x200 - 4, -1, -4):
            attr = b[offs + 1]
            sxp = b[offs + 3] - (0x100 if attr & 1 else 0)
            syp = b[offs + 2]
            code = b[offs] + ((attr << 2) & 0x300)
            col = (attr >> 4) & 3
            for py in range(16):
                y = syp + py
                if not 16 <= y < 240: continue
                for px in range(16):
                    x = sxp + px
                    if not 0 <= x < W: continue
                    c = self._sprite(code, 15 - px if attr & 4 else px, 15 - py if attr & 8 else py)
                    if c != 15:
                        img[y][x] = pal[0x40 + col * 16 + c]
        # fg chars: 32x32 8x8, row-major, pen 3 transparent
        for ty in range(2, 30):
            for tx in range(32):
                i = ty * 32 + tx
                code = m[0x2000 + i]; attr = m[0x2400 + i]
                code |= (attr & 0xC0) << 2
                for py in range(8):
                    for px in range(8):
                        c = self._char(code, 7 - px if attr & 0x10 else px, 7 - py if attr & 0x20 else py)
                        if c != 3:
                            img[ty * 8 + py][tx * 8 + px] = pal[0x80 + (attr & 15) * 4 + c]
        return img[16:240]

    def png(self, path):
        rows = self.render()
        raw = b''.join(b'\0' + bytes(v for p in r for v in p) for r in rows)
        ch = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
        open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', 256, len(rows), 8, 2, 0, 0, 0))
                               + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))


def parse(name):
    ev = []
    for part in os.environ.get(name, '').split(','):
        if part.strip():
            rng, msk = part.split(':')
            a, b = rng.split('-')
            ev.append((int(a), int(b), int(msk, 16)))
    return ev


def held(ev, f):
    v = 0
    for a, b, msk in ev:
        if a <= f <= b:
            v |= msk
    return v


def main():
    romdir, frames, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    g = GnG(romdir)
    if os.environ.get('LOAD'):
        g.load(os.environ['LOAD'])
    s1, s2, ss = parse('SCRIPT'), parse('SCRIPT2'), parse('SYS')
    pokes = []
    for pk in os.environ.get('POKE', '').split(','):
        if pk.strip():
            f, a, v = pk.split(':')
            pokes.append((int(f), int(a, 16), v))
    dump_at = set(int(x) for x in os.environ.get('DUMP_AT', '').split())
    step = int(os.environ.get('STEP', '120'))
    watch = os.environ.get('WATCH', '').split()
    d1, d2 = int(os.environ.get('DSW1', 'ff'), 16), int(os.environ.get('DSW2', 'ff'), 16)
    start = g.frame
    for k in range(1, frames + 1):
        f = start + k
        for pf, pa, pv in pokes:
            if pf == f:
                n = (len(pv) + 1) // 2
                for i in range(n):
                    g.mem[pa + i] = (int(pv, 16) >> (8 * (n - 1 - i))) & 0xFF
        g.set_inputs(held(ss, f), held(s1, f), held(s2, f), d1, d2)
        g.run_frame()
        if f in dump_at:
            open('%s_%05d.ram' % (out, f), 'wb').write(bytes(g.mem[0:0x2000]))
            g.save('%s_%05d.state' % (out, f))
            g.png('%s_%05d.png' % (out, f))
        if f % step == 0:
            ws = []
            for w in watch:
                if w.startswith('1') and len(w) == 5:
                    a = int(w[1:], 16); ws.append('%04X=%04X' % (a, (g.mem[a] << 8) | g.mem[a + 1]))
                else:
                    a = int(w, 16); ws.append('%04X=%02X' % (a, g.mem[a]))
            print(' '.join(ws), 'frame', f, 'pc %04X' % g.cpu.pc, flush=True)
            if os.environ.get('PNG') == '1':
                g.png('%s_%05d.png' % (out, f))


if __name__ == '__main__':
    main()
