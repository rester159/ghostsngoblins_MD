"""The port's music streams against the arcade's sound program, note for note.

Runs the arcade's sound CPU headlessly (Z80 at 3 MHz from `gg2.bin`, IRQ 4 per
frame held until taken, sound latch `$C800`, two YM2203s at `$E000-$E003`) for
each sound code and logs its YM2203 writes per IRQ. The port's music is the
sequencer's register streams (`SOUND_TABLE` in tools/patch_gng.py): per track,
per tick a word count and that many (part, register, value) writes; port id N
is arcade code N-1 and one tick is one arcade IRQ. For every tick it compares
the pitches written (`$A0-$A2` with their `$A4-$A6`, YM2203 at 1.5 MHz vs
YM2612 at 7.67 MHz, to 0.1 semitone) and the key-ons, per channel.

Needs the `z80` package (pip install z80; Ivan Kosarev's emulator).
usage: music_cmp.py <rom dir> <port rom> [sound id (hex) to list]
"""
import collections
import math
import sys

import z80

FM_ARC = 1500000 / 72                  # YM2203 at 1.5 MHz: fnum * rate * 2^block / 2^21
FM_MD = 53693175 / 7 / 144             # YM2612
SOUND_TABLE = 0x14CBF8


def streams(rom):
    rd16 = lambda a: int.from_bytes(rom[a:a + 2], 'big')
    rd32 = lambda a: int.from_bytes(rom[a:a + 4], 'big')
    out = {}
    for sid in range(64):
        e = SOUND_TABLE + 12 * sid
        if rd16(e) not in (1, 2):
            continue
        base = SOUND_TABLE + rd32(e + 4)
        trs = []
        for t in range(rd16(base)):
            tr = base + 4 + 20 * t
            p = base + rd32(tr + 12)
            ticks = []
            for _ in range(rd32(tr + 4)):
                n = rd16(p); p += 2
                ticks.append([tuple(rom[p + 3 * k:p + 3 * k + 3]) for k in range(n)])
                p += 3 * n
            trs.append(ticks)
        out[sid] = trs
    return out


class ArcadeSound:
    def __init__(self, romdir):
        m = self.m = z80.Z80Machine()
        m.set_memory_block(0, open(romdir + '/gg2.bin', 'rb').read())
        self.latch, self.addr, self.irq, self.log = 0xFF, [0, 0], 0, []
        m.mark_addrs(0xC800, 1, m.READ_MARK)
        m.mark_addrs(0xE000, 4, m.READ_MARK | m.WRITE_MARK)
        m.set_read_callback(lambda a: self.latch if a == 0xC800 else 0)
        m.set_write_callback(self.wr)
        self.run(60)

    def wr(self, a, v):
        chip = (a - 0xE000) >> 1
        if a & 1 == 0:
            self.addr[chip] = v
        else:
            self.log.append((self.irq, chip, self.addr[chip], v))

    def run(self, n):
        m = self.m
        for _ in range(n):
            m.ticks_to_stop = 3000000 // 240
            while not m.run() & m._TICKS_LIMIT_HIT:
                pass
            while not m.iff1 or m.int_disabled:          # line held until taken
                m.ticks_to_stop = 50
                while not m.run() & m._TICKS_LIMIT_HIT:
                    pass
            m.on_handle_active_int()
            self.irq += 1

    def play(self, code, n):
        self.latch, self.log, t0 = code, [], self.irq
        self.run(n)
        return [(i - t0, c, r, v) for i, c, r, v in self.log]


def events(seq, rate, keych):
    """(tick, chip/part, reg, val) -> {tick: [('f', ch, semitone), ('k', ch, slots)]}"""
    hi, ev = {}, collections.defaultdict(list)
    for i, c, r, v in seq:
        if 0xA4 <= r <= 0xA6:
            hi[(c, r - 0xA4)] = v
        elif 0xA0 <= r <= 0xA2:
            h = hi.get((c, r - 0xA0), 0)
            f = (h & 7) << 8 | v
            m = 69 + 12 * math.log2(f * rate * (1 << (h >> 3 & 7)) / (1 << 21) / 440) if f else -99
            ev[i].append(('f', c * 3 + r - 0xA0, round(m, 1)))
        elif r == 0x28 and v & 3 != 3:
            ev[i].append(('k', keych(c, v), v >> 4))
    return ev


def main():
    romdir, port = sys.argv[1], open(sys.argv[2], 'rb').read()
    only = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    total = 0
    for sid, trs in sorted(streams(port).items()):
        if only is not None and sid != only:
            continue
        n = min(len(t) for t in trs)
        arc = ArcadeSound(romdir).play(sid - 1, max(len(t) for t in trs) + 8)
        a = events(arc, FM_ARC, lambda c, v: c * 3 + (v & 3))
        seq = sorted(((i, p, r, v) for t in trs for i, tk in enumerate(t) for p, r, v in tk), key=lambda x: x[0])
        b = events(seq, FM_MD, lambda c, v: (v & 3) + (3 if v & 4 else 0))
        bad = [(i, sorted((collections.Counter(a.get(i, [])) - collections.Counter(b.get(i, []))).elements()),
                sorted((collections.Counter(b.get(i, [])) - collections.Counter(a.get(i, []))).elements()))
               for i in range(n) if collections.Counter(a.get(i, [])) != collections.Counter(b.get(i, []))]
        # a write that spilled into the arcade's next IRQ shows as the same events one tick apart
        moved = sum(1 for k in range(len(bad) - 1)
                    if bad[k][0] + 1 == bad[k + 1][0] and bad[k][1] == bad[k + 1][2] and not bad[k][2] and not bad[k + 1][1])
        real = len(bad) - 2 * moved
        total += real
        keyons = sum(1 for i in b for e in b[i] if e[0] == 'k' and e[2])
        print('sound %02X (arcade %02X): %d ticks, %d key-ons, %d ticks differ (%d one-tick shifts)'
              % (sid, sid - 1, n, keyons, real, moved))
        if only is not None:
            for i, x, y in bad:
                print('   ', i, 'arcade', x, 'port', y)
    print('ticks with a different pitch or key-on:', total)


if __name__ == '__main__':
    main()
