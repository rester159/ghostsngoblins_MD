"""Capture a sprite's animation frames from a SNES game, headlessly (snes9x core).

Runs from a save state with a scripted pad, decodes VRAM/OAM/CGRAM from the
core's save state every frame, composes the OAM entries that match a filter
(palette + tile range) and keeps each new picture, in order of appearance.

usage: snes_capture.py <core> <rom> <state> <frames> <script> <out.json>
         [--pal P] [--tiles LO-HI] [--base HEX] [--lag N]

The JSON holds, per unique picture: first frame, the anchor (OAM entry 0 of the
group's screen position is not stable, so pictures are stored with absolute
screen coordinates plus the bounding box), and the pixels as palette indices,
with the 16-colour palette (BGR555) used.
"""
import ctypes as C
import json
import re
import sys

core, rom, state, frames, script, out = sys.argv[1:7]
frames = int(frames)
opts = dict(zip(sys.argv[7::2], sys.argv[8::2]))
PAL = int(opts.get('--pal', '7'))
LO, HI = (int(x, 16) for x in opts.get('--tiles', '0-3F').split('-'))
BASE = int(opts.get('--base', 'C000'), 16)
LAG = int(opts.get('--lag', '1'))      # OAM from LAG frames earlier (tiles are uploaded a frame later)
OAM_AT, CG_AT = 2003, 64            # inside the snes9x 1.6x PPU block (format 0012)

ev = []
for part in script.split(','):
    if part.strip():
        rng, m = part.split(':')
        a, b = rng.split('-')
        ev.append((int(a), int(b), int(m, 16)))

L = C.CDLL(core)
frame_no = [0]
ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VID = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AS = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
ASB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
IP = C.CFUNCTYPE(None)
IS = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


def env(cmd, data):
    cmd &= 0xFFFF
    if cmd == 10:
        return True
    if cmd in (9, 31):
        C.cast(data, C.POINTER(C.c_char_p))[0] = b'.'
        return True
    return False


def instate(port, dev, idx, id_):
    if port:
        return 0
    for a, b, m in ev:
        if a <= frame_no[0] <= b:
            return 1 if (m >> id_) & 1 else 0
    return 0


cbs = [ENV(env), VID(lambda *a: None), AS(lambda l, r: None), ASB(lambda d, n: n), IP(lambda: None), IS(instate)]
L.retro_set_environment(cbs[0]); L.retro_set_video_refresh(cbs[1]); L.retro_set_audio_sample(cbs[2])
L.retro_set_audio_sample_batch(cbs[3]); L.retro_set_input_poll(cbs[4]); L.retro_set_input_state(cbs[5])
L.retro_init()


class GI(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]


data = open(rom, 'rb').read()
buf = C.create_string_buffer(data, len(data))
assert L.retro_load_game(C.byref(GI(rom.encode(), C.cast(buf, C.c_void_p), len(data), None)))
L.retro_serialize_size.restype = C.c_size_t
st = open(state, 'rb').read()
L.retro_run()
assert L.retro_unserialize(C.create_string_buffer(st, len(st)), len(st))
n = L.retro_serialize_size()
sb = C.create_string_buffer(n)


def blocks(s):
    out = {}
    for m in re.finditer(rb'([A-Z]{3}):([0-9]{6}):', s[:0x20000]):
        out[m.group(1).decode()] = (m.end(), int(m.group(2)))
    return out


def tile4(vram, t):
    a = (BASE + t * 32) & 0xFFFF
    rows = []
    for y in range(8):
        p0, p1, p2, p3 = vram[a + 2 * y], vram[a + 2 * y + 1], vram[a + 16 + 2 * y], vram[a + 17 + 2 * y]
        rows.append([((p0 >> (7 - x)) & 1) | ((p1 >> (7 - x)) & 1) << 1 |
                     ((p2 >> (7 - x)) & 1) << 2 | ((p3 >> (7 - x)) & 1) << 3 for x in range(8)])
    return rows


seen = {}
order = []
oam_hist = []
for f in range(1, frames + 1):
    frame_no[0] = f
    L.retro_run()
    L.retro_serialize(sb, n)
    s = sb.raw
    bl = blocks(s)
    po, _ = bl['PPU']
    vo, _ = bl['VRA']
    ppu = s[po:po + 2652]
    vram = s[vo:vo + 65536]
    oam_hist.append(ppu[OAM_AT:OAM_AT + 544])
    if len(oam_hist) <= LAG:
        continue
    oam = oam_hist[-1 - LAG]
    oam_hist = oam_hist[-1 - LAG:]
    cg = [ppu[CG_AT + 2 * i] << 8 | ppu[CG_AT + 2 * i + 1] for i in range(256)]
    px = {}
    ents = []
    for i in range(128):
        x, y, t, a = oam[4 * i:4 * i + 4]
        hi = oam[512 + i // 4] >> (2 * (i % 4)) & 3
        x |= (hi & 1) << 8
        if x >= 256:
            x -= 512
        tile = t | (a & 1) << 8
        if (a >> 1 & 7) != PAL or not (LO <= tile <= HI) or y >= 224:
            continue
        ents.append((i, x, y, tile, a >> 6 & 1, a >> 7 & 1, hi >> 1 & 1))
    if ents:                                                # keep the cluster round the median
        mx = sorted(e[1] for e in ents)[len(ents) // 2]
        my = sorted(e[2] for e in ents)[len(ents) // 2]
        ents = [e for e in ents if abs(e[1] - mx) <= 40 and abs(e[2] - my) <= 40]
    for i, x, y, tile, hf, vf, big in reversed(ents):      # lower OAM index on top
        nt = 2 if big else 1
        for ty in range(nt):
            for tx in range(nt):
                rows = tile4(vram, (tile & 0x100) | ((tile & 0xF0) + ty * 16 & 0xF0) | ((tile + tx) & 0x0F))
                for yy in range(8):
                    for xx in range(8):
                        c = rows[yy][xx]
                        if c:
                            X = x + ((nt - 1 - tx) * 8 + 7 - xx if hf else tx * 8 + xx)
                            Y = y + ((nt - 1 - ty) * 8 + 7 - yy if vf else ty * 8 + yy)
                            px[(X, Y)] = c
    if not px:
        continue
    x0 = min(p[0] for p in px); y0 = min(p[1] for p in px)
    x1 = max(p[0] for p in px); y1 = max(p[1] for p in px)
    key = tuple(sorted(((x - x0, y - y0), c) for (x, y), c in px.items()))
    if key in seen:
        seen[key]['frames'].append(f)
        continue
    w, h = x1 - x0 + 1, y1 - y0 + 1
    grid = [[0] * w for _ in range(h)]
    for (x, y), c in px.items():
        grid[y - y0][x - x0] = c
    hf = sum(e[4] for e in ents) * 2 > len(ents)          # most entries flipped
    rec = dict(first=f, frames=[f], box=[x0, y0, w, h], hflip=int(hf),
               palette=cg[128 + PAL * 16:128 + PAL * 16 + 16],
               rows=[''.join('%x' % c for c in r) for r in grid])
    seen[key] = rec
    order.append(rec)

json.dump(order, open(out, 'w'), indent=0)
print('unique pictures:', len(order))
