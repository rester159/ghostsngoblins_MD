"""Build Firebrand's sprite bank from his Demon's Crest frames (art/firebrand/dc,
captured by tools/headless/snes_capture.py), scaled to 70% so he matches
Arthur's size, in the Genesis sprite palette (dc.py).

Every frame Arthur can show gets a Firebrand pose of the same meaning and facing;
walking and hovering play Firebrand's own 6-frame cycles (firebrand.c picks them).
A bank frame is 0x300 bytes:
  +0x000  512 bytes  32x32 in Arthur's layout (16 tiles, column-major) -> tile $300
  +0x200  128 bytes  8x32 column left of it  (x -24..-16)              -> tile $690
  +0x280  128 bytes  8x32 column right of it (x +16..+24)              -> tile $694
Bank order: Arthur's 84 frames, walk cycle facing right, then left (6 + 6),
flight cycle facing right, then left (6 + 6).
firebrand_flags.bin, one byte per frame: bit0 left column, bit1 right column,
bit2 palette line 2 (the burn-up flames), bit3 a walking frame of Arthur's (the
runtime shows the walk cycle instead), bit4 faces left.
firebrand_fire.bin is the shot art (fire.py); firebrand_mapicon.bin the stage-map marker (head.py).

usage: build.py <rom (fixed or plus build)> <out dir>
"""
import os
import sys
from collections import Counter
from arremer import frame as arremer_frame
import dc
import fire
import head

ARTHUR = [0x109E2 + i * 0x200 for i in range(11)] + \
         [0x40000 + i * 0x200 for i in range(73)]
SCALE = 0.7
W, H = 48, 32                      # Arthur's 32x32 slot plus the two 8-px columns
CX = 24                            # Arthur's x in the canvas; feet on the bottom row
FRAME = 0x300
BODY = set(range(1, 7))            # Firebrand's gold ramp (the wings are blues/greys)

# pose -> (dc set, index in the set, airborne?)
POSE = {
    'stand': ('stand', 0, False), 'fire': ('fire', 0, False),
    'crouch': ('jump', 0, False), 'jump': ('jump', 2, True), 'jump2': ('jump', 4, True),
    'hit': ('jump', 1, True), 'land': ('land', 1, False),
}
WALK = [('walk', i, False) for i in range(6)]
FLY = [('fly', i, True) for i in range(6)]
FLAMES = {35: 51, 36: 53, 37: 55, 38: 56, 39: 58, 40: 57, 41: 55, 42: 53, 43: 59, 44: 60}

R, L = 0, 1
RUN = 'run'
CLASS = {
    0: ('stand', R), 1: (RUN, R), 2: (RUN, R), 3: (RUN, R), 4: (RUN, R),
    5: (RUN, R), 6: (RUN, R), 7: ('jump', R), 8: ('jump2', R), 9: ('fire', R),
    10: ('crouch', R),
    11: ('stand', R), 12: (RUN, R), 13: (RUN, R), 14: (RUN, R), 15: (RUN, R),
    16: ('jump', R), 17: ('jump2', R), 18: ('fire', R), 19: ('crouch', R),
    20: ('crouch', R), 21: ('crouch', R), 22: ('crouch', R),
    23: ('stand', R), 24: ('land', R), 25: ('crouch', R), 26: ('crouch', R),
    27: ('stand', R), 28: ('stand', R), 29: ('stand', L), 30: ('crouch', R),
    31: ('crouch', R), 32: ('crouch', L), 33: ('hit', R), 34: ('hit', R),
    45: (None, R), 46: (None, R), 47: (None, R), 48: (None, R), 49: (None, R),
    50: ('fire', L), 51: ('stand', L), 52: ('stand', L), 53: (RUN, L), 54: ('jump', L),
    55: ('jump2', L), 56: ('fire', L), 57: (RUN, L), 58: ('crouch', L), 59: ('crouch', L),
    60: (RUN, R), 61: (RUN, R), 62: (RUN, R), 63: (RUN, R), 64: ('jump', R),
    65: ('jump2', R), 66: ('fire', R), 67: ('crouch', R), 68: ('crouch', R), 69: ('crouch', R),
    70: ('stand', R), 71: ('land', R), 72: ('crouch', R), 73: ('crouch', R),
    74: (RUN, L), 75: (RUN, L), 76: (RUN, L), 77: (RUN, L), 78: ('jump', L),
    79: ('jump2', L), 80: ('fire', L), 81: ('crouch', L), 82: ('crouch', L), 83: ('crouch', L),
}


def source(set_name, i):
    """DC picture facing right: rows of Genesis colour indices."""
    rws, box, pal, hflip = dc.frames(set_name)[i]
    m = dc.mapping(pal, set_name)
    g = [[m[int(c, 16)] if c != '0' else 0 for c in r] for r in rws]
    if not hflip:                  # captured facing left
        g = [r[::-1] for r in g]
    return g, [[int(c, 16) for c in (r if hflip else r[::-1])] for r in rws]


def downscale(g, s):
    """Palette-aware: each target pixel takes the most common colour under it,
    or stays clear when most of its footprint is clear."""
    h, w = len(g), len(g[0])
    th, tw = max(1, round(h * s)), max(1, round(w * s))
    out = [[0] * tw for _ in range(th)]
    for ty in range(th):
        y0, y1 = int(ty / s), max(int(ty / s) + 1, int((ty + 1) / s))
        for tx in range(tw):
            x0, x1 = int(tx / s), max(int(tx / s) + 1, int((tx + 1) / s))
            cnt = Counter(g[y][x] for y in range(y0, min(y1, h)) for x in range(x0, min(x1, w)))
            clear = cnt.pop(0, 0)
            if cnt and sum(cnt.values()) >= clear:
                out[ty][tx] = cnt.most_common(1)[0][0]
    return out


def anchor(idx_rows):
    """Body centre x, body centre y and the lowest pixel, in source pixels."""
    pts = [(x, y) for y, r in enumerate(idx_rows) for x, c in enumerate(r) if c in BODY]
    allpts = [(x, y) for y, r in enumerate(idx_rows) for x, c in enumerate(r) if c]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(p[1] for p in allpts)


def stand_body_y():
    g, idx = source('stand', 0)
    _, cy, bottom = anchor(idx)
    return (H - 1) - (bottom - cy) * SCALE


AIR_Y = None


def pose_image(set_name, i, air):
    g, idx = source(set_name, i)
    h, w = len(g), len(g[0])
    s = min(SCALE, H / h, W / w)
    small = downscale(g, s)
    cx, cy, bottom = anchor(idx)
    sh, sw = len(small), len(small[0])
    ox = round(CX - cx * s)
    oy = round(AIR_Y - cy * s) if air else (H - 1) - round(bottom * s)
    ox = max(0, min(W - sw, ox))           # keep the wings on the canvas
    oy = max(0, min(H - sh, oy))
    canvas = [[0] * W for _ in range(H)]
    for y in range(sh):
        for x in range(sw):
            if small[y][x]:
                canvas[oy + y][ox + x] = small[y][x]
    best = None
    st = head.stamp()
    if set_name == 'fire':
        x0, y0, x1, y1 = head.FIRE_BOX
        best = (0, x0, y0, x1 - x0, y1 - y0)
        st = head.stamp(head.FIRE_STAMP)
    else:
        for tpl, (bx, by, bw, bh) in head_templates():
            sc, hx, hy = head.find(tpl, idx)
            if sc <= head.MAX_MISMATCH and (best is None or sc < best[0]):
                best = (sc, hx, hy, bw, bh)
    if best:                                # the clean head over the scaled one
        _, hx, hy, bw, bh = best
        cxh = ox + (hx + bw / 2) * s
        sx = round(cxh - len(st[0]) / 2)
        sy = round(oy + (hy + bh) * s) - len(st)
        for y, r in enumerate(st):
            for x, c in enumerate(r):
                if c and 0 <= sy + y < H and 0 <= sx + x < W:
                    canvas[sy + y][sx + x] = c
    return canvas


_TEMPLATES = None


def head_templates():
    """[(template rows of DC colour indices, (x, y, w, h))] facing right."""
    global _TEMPLATES
    if _TEMPLATES is None:
        _TEMPLATES = []
        for set_name, i, x0, y0, x1, y1 in head.TEMPLATES:
            _, idx = source(set_name, i)
            _TEMPLATES.append(([r[x0:x1] for r in idx[y0:y1]], (x0, y0, x1 - x0, y1 - y0)))
    return _TEMPLATES


def mirror(g):
    return [r[::-1] for r in g]


def encode_tiles(g, x0, cols):
    out = bytearray()
    for tx in range(cols):
        for ty in range(4):
            for y in range(8):
                for x in range(0, 8, 2):
                    X = x0 + tx * 8 + x
                    out.append(g[ty * 8 + y][X] << 4 | g[ty * 8 + y][X + 1])
    return bytes(out)


def bank_frame(g):
    main = encode_tiles(g, 8, 4)
    left = encode_tiles(g, 0, 1)
    right = encode_tiles(g, 40, 1)
    flags = (1 if any(left) else 0) | (2 if any(right) else 0)
    return main + left + right, flags


def images(rom):
    global AIR_Y
    AIR_Y = stand_body_y()
    poses = {k: pose_image(*v) for k, v in POSE.items()}
    walk = [pose_image(*v) for v in WALK]
    fly = [pose_image(*v) for v in FLY]
    out = []
    for i in range(len(ARTHUR)):
        if i in FLAMES:
            out.append((arremer_frame(rom, FLAMES[i]), 4))
            continue
        pose, facing = CLASS[i]
        if pose is None:
            out.append(([[0] * W for _ in range(H)], 0))
            continue
        g = walk[0] if pose == RUN else poses[pose]
        extra = (8 if pose == RUN else 0) | (16 if facing == L else 0)
        out.append((mirror(g) if facing == L else g, extra))
    out += [(g, 0) for g in walk] + [(mirror(g), 16) for g in walk]
    out += [(g, 0) for g in fly] + [(mirror(g), 16) for g in fly]
    return out


def main(rom_path, dst):
    rom = open(rom_path, 'rb').read()
    bank, flags = bytearray(), bytearray()
    imgs = images(rom)
    for g, extra in imgs:
        data, f = bank_frame(g)
        bank += data
        flags.append(f | extra)
    open(os.path.join(dst, 'firebrand_bank.bin'), 'wb').write(bank)
    open(os.path.join(dst, 'firebrand_flags.bin'), 'wb').write(flags)
    open(os.path.join(dst, 'firebrand_fire.bin'), 'wb').write(fire.encode(rom))
    open(os.path.join(dst, 'firebrand_mapicon.bin'), 'wb').write(head.map_icon_tiles())
    preview(imgs, os.path.join(dst, 'firebrand_all_frames.png'))
    print('frames', len(imgs), 'bank', len(bank), 'wide', sum(1 for f in flags if f & 3))


def preview(imgs, path):
    import struct
    import zlib
    line0 = [(0, 0, 0)] + [dc.GEN[i] for i in range(1, 16)]
    line2 = [(0, 0, 0), (0, 0, 0), (52, 52, 0), (116, 52, 0), (0, 87, 0), (144, 87, 0), (52, 116, 0),
             (87, 116, 0), (144, 172, 0), (52, 52, 52), (144, 116, 52), (87, 144, 52), (116, 87, 87),
             (116, 116, 116), (144, 116, 116), (144, 0, 0)]
    S, cols = 3, 12
    cw, ch = W * S + 6, H * S + 6
    PW, PH = cols * cw, ((len(imgs) + cols - 1) // cols) * ch
    px = bytearray([44, 50, 66] * PW * PH)
    for i, (g, extra) in enumerate(imgs):
        line = line2 if extra & 4 else line0
        ox, oy = (i % cols) * cw, (i // cols) * ch
        for y in range(H):
            for x in range(W):
                c = g[y][x]
                col = bytes(line[c]) if c else (bytes((56, 62, 82)) if 8 <= x < 40 else None)
                if col is None:
                    continue
                for dy in range(S):
                    p = ((oy + y * S + dy) * PW + ox + x * S) * 3
                    px[p:p + S * 3] = col * S
    rows = b''.join(b'\0' + bytes(px[y * PW * 3:(y + 1) * PW * 3]) for y in range(PH))
    chunk = lambda t, b: struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b))
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', PW, PH, 8, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
