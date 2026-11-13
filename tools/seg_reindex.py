"""Stage 2's segment tile sets, re-indexed so a segment change needs no reload (src_patch/segswap.c).

Stage 2's street is drawn from segments (per section, the table at $2A2B42: section -> segment table, palette;
an entry is start column, end column, tile words - 1, tiles, map). The base port packed each segment's tiles on
their own, so moving into the next segment uploaded its whole set (652-672 tiles) with the display off: two black
frames. Two neighbouring segments overlap by 31 columns, and at the change every column in the plane's ring
(the column 15 left of the camera and the 31 right of it) lies in that overlap, where both maps draw the same
cells. Here each segment after the first is laid out on the one before it: a tile the next one shares by content
(or flipped) keeps its index, one it lacks goes into an index the plane can't be showing (one no overlap cell of
the previous segment uses, and not needed next), the rest keep the previous segment's tiles, and the map entries
are remapped. Then the overlap cells are equal word for word (checked), and a change is the new tiles' upload,
the same indices either way: going right the next segment's tiles there, going left the previous one's. Each
list is ordered by the first column that needs its tiles (going right the column entering at the plane's right
edge first, the only one that can show before the upload ends).

install(rom, sym): the maps rewritten in place, each segment's tiles written in place or, if the new layout is
longer, in free space, the tables repointed, and seg_xfer[section][change][direction] (src_patch/segswap.c)
pointed at run lists: u16 runs, then runs x (u16 first tile, u16 tiles, u32 source).
"""
import struct

SECTIONS = 0x2A2B42
LIMIT = 672                     # tiles $000-$29F: the segments' region in VRAM
FREE = ((0x3CB600, 0x3F0000), (0x3F0100, 0x400000))   # after Maximo's bank A; after the patch stubs
BUDGET = 96                     # tiles a vblank (segswap.c SEG_BUDGET)


def hf(t):
    return b''.join(bytes(((b & 15) << 4) | (b >> 4) for b in t[r * 4:r * 4 + 4][::-1]) for r in range(8))


def vf(t):
    return b''.join(t[r * 4:r * 4 + 4] for r in range(7, -1, -1))


VARIANTS = ((0, lambda t: t), (0x0800, hf), (0x1000, vf), (0x1800, lambda t: hf(vf(t))))


def r32(rom, a):
    return struct.unpack('>I', rom[a:a + 4])[0]


def segments(rom, table):
    out = []
    i = 0
    while True:
        a, b, n, src, mp = struct.unpack('>HHHxxII', rom[table + 16 * i:table + 16 * i + 16])
        if a == 0xFFFF:
            return out
        tiles = [bytes(rom[src + 32 * k:src + 32 * k + 32]) for k in range((n + 1) * 2 // 32)]
        words = list(struct.unpack('>%dH' % ((b - a) * 128), rom[mp:mp + (b - a) * 256]))
        out.append(dict(entry=table + 16 * i, a=a, b=b, src=src, size=(n + 1) * 2, map=mp, tiles=tiles, words=words))
        i += 1


def column(seg, words, c):
    o = (c - seg['a']) * 128
    return words[o:o + 128]


def layout(segs):
    """Each segment's VRAM picture (index -> tile or None), its remapped map, and the indices each change rewrites
    (in upload order)."""
    s0 = segs[0]
    vram = list(s0['tiles']) + [None] * (LIMIT - len(s0['tiles']))
    pics, maps, changes = [vram], [list(s0['words'])], []
    for k in range(1, len(segs)):
        prev, s = segs[k - 1], segs[k]
        pv, pw = pics[-1], maps[-1]
        keep = set()
        for c in range(s['a'], prev['b']):
            keep.update(w & 0x7FF for w in column(prev, pw, c))
        where = {}
        for i in sorted(range(LIMIT), key=lambda i: (i not in keep, i)):
            if pv[i] is not None:
                where.setdefault(pv[i], i)
        first = {}                                  # tile index of s -> first column that uses it
        for c in range(s['a'], s['b']):
            for w in column(s, s['words'], c):
                first.setdefault(w & 0x7FF, c)
        found, new = {}, []
        for t in sorted(first, key=lambda t: (first[t], t)):
            for flip, f in VARIANTS:
                if f(s['tiles'][t]) in where:
                    found[t] = (where[f(s['tiles'][t])], flip)
                    break
            else:
                new.append(t)
        taken = keep | {i for i, _ in found.values()} | {0}     # tile 0: the blank cell of plane A (the HUD's plane)
        free = [i for i in range(LIMIT) if i not in taken]
        content = {}
        order = []
        nv = list(pv)
        for t in new:
            c = s['tiles'][t]
            if c in content:
                found[t] = (content[c], 0)
                continue
            assert free, 'segment %d: no free tile' % k
            i = free.pop(0)
            nv[i] = c
            content[c] = i
            found[t] = (i, 0)
            order.append(i)
        words = [(w & 0xE000) | ((w & 0x1800) ^ found[w & 0x7FF][1]) | found[w & 0x7FF][0] for w in s['words']]
        for c in range(s['a'], prev['b']):
            assert column(s, words, c) == column(prev, pw, c), 'segment %d: overlap column %d differs' % (k, c)
        pics.append(nv)
        maps.append(words)
        changes.append(order)
    return pics, maps, changes


def runs(order, base, keep=None):
    """(first tile, tiles, source) runs over the indices in order, data at base + 32 * index, none across a
    128 KiB DMA boundary."""
    out = []
    for i in order:
        if keep is not None and i not in keep:
            continue
        src = base + 32 * i
        assert (src >> 17) == ((src + 31) >> 17), 'a tile across a DMA boundary'
        if out and out[-1][0] + out[-1][1] == i and (out[-1][2] >> 17) == ((src + 31) >> 17) \
                and out[-1][1] < 128:
            out[-1][1] += 1
        else:
            out.append([i, 1, src])
    return out


def install(rom, sym, put, be32):
    free = [list(r) for r in FREE]

    def alloc(data):
        for r in free:
            a = r[0]
            if a + len(data) <= r[1]:
                assert all(b == 0xFF for b in rom[a:a + len(data)]), 'free space in use'
                put(rom, a, data)
                r[0] = (a + len(data) + 1) & ~1
                return a
        raise AssertionError('segment data runs out of free space')

    xfer = sym['seg_xfer']
    table = []
    worst = 0
    for sec in range(3):
        segs = segments(rom, r32(rom, SECTIONS + 8 * sec))
        pics, maps, changes = layout(segs)
        base = []
        for k, s in enumerate(segs):
            used = {w & 0x7FF for w in maps[k]}
            n = max(used) + 1
            blob = b''.join(pics[k][i] or bytes(32) for i in range(n))
            if k == 0:
                at = s['src']                                   # the first segment as it was
                assert blob == bytes(rom[at:at + len(blob)])
            elif len(blob) <= s['size']:
                at = s['src']
                put(rom, at, blob)
            else:
                at = alloc(blob)
            put(rom, s['entry'] + 4, struct.pack('>H', len(blob) // 2 - 1))
            put(rom, s['entry'] + 8, be32(at))
            put(rom, s['map'], struct.pack('>%dH' % len(maps[k]), *maps[k]))
            base.append((at, used))
        for k, order in enumerate(changes):
            prev, nxt = segs[k], segs[k + 1]
            right = runs(order, base[k + 1][0])
            left = runs(sorted(order), base[k][0], base[k][1])
            need = {w & 0x7FF for w in column(nxt, maps[k + 1], prev['b'])} & set(order)
            first = sum(1 for i in order[:BUDGET] if i in need)
            assert first == len(need), 'section %d change %d: the first column needs more than a vblank' % (sec, k)
            worst = max(worst, len(order))
            for d, rl in ((0, right), (1, left)):
                data = struct.pack('>H', len(rl)) + b''.join(struct.pack('>HHI', i, n, s) for i, n, s in rl)
                table.append((sec, k, d, alloc(data)))
    for sec, k, d, at in table:
        put(rom, xfer + 4 * ((sec * 4 + k) * 2 + d), be32(at))
    return worst
