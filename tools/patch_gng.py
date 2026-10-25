#!/usr/bin/env python3
"""Hardware-compatibility patcher for the Ghosts'n Goblins Genesis port.

Input : Ghosts'n Goblins (SMD) (PD).bin   (3,473,408 bytes, header checksum EE66)
Output: patched ROM, padded to a standard 4 MiB linear image.

Fixes (all verified against the disassembly of the input image):
  1. 16x `clr.w/clr.l $C00000` -> jsr to write-only stubs. A 68000 `clr` reads
     the destination before writing; reading the VDP data port while it is in
     a write mode is undefined on real hardware (lock-up / corruption) and is
     rejected by accuracy-focused emulators. Fusion/Gens ignore it.
  2. Boot: read the VDP control port before the first register write so a
     soft reset that interrupted a two-word command does not corrupt VDP init.
  3. Sound init: after releasing Z80 reset with BUSREQ held, wait for BUSACK
     again before touching Z80 RAM (the original wrote immediately).
  4. Attract mode: invalidate the logo/ranking overlay tile cache on the two
     `jmp $2CC` restart paths (taken when the demo player dies), which re-run
     VRAM init. Previously the logo was drawn with overwritten tiles until the
     ranking overlay took over.
  5. Blink + death: while Arthur blinks (post-hit invincibility, $FFC309), the
     blink routine at $5E4A copied the queued animation straight into the shown
     one. A death that starts during the blink (time-out, pit) queues the death
     sequence's terminator ($0B, no frame); the frame lookup then failed its
     range check and the game halted in the $B56 trap. The copy now skips
     animations without a frame.
  6. Header: blank (0x20) SRAM/modem/memo fields instead of 0xFF, real title,
     ROM end = 0x3FFFFF, correct checksum.

Optional: --features adds src_patch/ (menus, modes, SRAM); --maximo swaps Arthur's
sprite frames for Maximo's (art/maximo/).
"""
import os
import struct
import sys

SRC_SIZE = 0x350000
SRC_SUM = 0xEE66
OUT_SIZE = 0x400000
PATCH_BASE = 0x3F0000          # beyond the original image; padding region

CLR_W = [0x000DEA, 0x000E00, 0x113C26, 0x113C2C, 0x113D4C, 0x11D254, 0x11D25A]
CLR_L = [0x113C3C, 0x113C4C, 0x113C52, 0x119F7E, 0x119F84,
         0x11D1FC, 0x11D202, 0x11D212, 0x11D222]


def be16(v):
    return struct.pack('>H', v)


def be32(v):
    return struct.pack('>I', v)


def jsr(addr):
    return b'\x4e\xb9' + be32(addr)


def expect(rom, off, data, what):
    if bytes(rom[off:off + len(data)]) != data:
        sys.exit(f'unexpected bytes at {off:06X} ({what}); wrong input ROM?')


def put(rom, off, data):
    rom[off:off + len(data)] = data


FEATURE_BASE = 0x380000        # src_patch/link.ld


def load_symbols(path):
    syms = {}
    for line in open(path):
        parts = line.split()
        if len(parts) == 3:
            syms[parts[2]] = int(parts[0], 16)
    return syms


MUSIC_ATT = 8          # music volume: total-level steps of 0.75 dB (8 = -6 dB)
SOUND_TABLE = 0x14CBF8  # 12 bytes per sound id: type, slot, stream offset


def attenuate_music(rom, att):
    """Make the music quieter in the data itself. The music (stage tunes, map
    and intro themes, jingles) is the sequencer's register streams: per track,
    per tick a word count and that many (part, register, value) writes; the
    action sound effects are separate PCM clips. Each carrier operator's total
    level ($40-$4F; the operators that set the output for the channel's
    algorithm, $B0-$B2) gets `att` more attenuation. A stream sets its
    levels and algorithms together at its start, so a tick's algorithm writes
    count for that tick's level writes; with no algorithm yet, only S4 (a
    carrier in every algorithm) is changed. No code changes and no run-time
    cost: the driver's restore of cached registers sends the same values."""
    rd16 = lambda a: int.from_bytes(rom[a:a + 2], 'big')
    rd32 = lambda a: int.from_bytes(rom[a:a + 4], 'big')
    carriers = (8, 8, 8, 8, 0xC, 0xE, 0xE, 0xF)      # bit = $40 S1, $44 S3, $48 S2, $4C S4
    done = set()
    for sid in range(64):
        e = SOUND_TABLE + 12 * sid
        if rd16(e) not in (1, 2):
            continue
        base = SOUND_TABLE + rd32(e + 4)
        for t in range(rd16(base)):
            tr = base + 4 + 20 * t
            p = base + rd32(tr + 12)
            alg = [None] * 6
            for _ in range(rd32(tr + 4)):
                n = rd16(p); p += 2
                block = [(p + 3 * k, rom[p + 3 * k], rom[p + 3 * k + 1]) for k in range(n)]
                p += 3 * n
                for a, part, reg in block:
                    if 0xB0 <= reg <= 0xB2:
                        alg[part * 3 + reg - 0xB0] = rom[a + 2] & 7
                for a, part, reg in block:
                    if 0x40 <= reg <= 0x4F and reg & 3 != 3 and a not in done:
                        ch = part * 3 + (reg & 3)
                        mask = carriers[alg[ch]] if alg[ch] is not None else 8
                        if mask >> ((reg >> 2) & 3) & 1:
                            v = rom[a + 2]
                            rom[a + 2] = (v & 0x80) | min(0x7F, (v & 0x7F) + att)
                        done.add(a)
    return len(done)


def install_features(rom, build_dir):
    """Menus, modes and QoL code from src_patch/ (built with `make`)."""
    blob = open(build_dir + '/patch.bin', 'rb').read()
    sym = load_symbols(build_dir + '/patch.sym')
    assert FEATURE_BASE + len(blob) <= 0x3A0000, 'feature blob runs into the art banks'
    put(rom, FEATURE_BASE, blob)
    jmp = lambda a: b'\x4e\xf9' + be32(a)

    # RAM clear that keeps the persistent block (also does the VDP latch read)
    expect(rom, 0x28E, b'\x4e\xb9', 'boot jsr (fix stub)')
    put(rom, 0x28E, jsr(sym['hook_ramclear']))
    # boot menu before the title/attract: the title routine's prologue
    # (movem + jsr $BF58, 10 bytes; only caller is $2C8) jumps to hook_title,
    # which repeats that prologue
    expect(rom, 0xB7A, b'\x48\xe7\xff\xe0' + jsr(0xBF58), 'title prologue')
    put(rom, 0xB7A, jmp(sym['hook_title']) + b'\x4e\x71\x4e\x71')
    # pad routine (keeps outputs, adds per-mode mapping and pause)
    expect(rom, 0xBF72, b'\x13\xfc\x00\x40' + be32(0xA10003), 'pad routine')
    put(rom, 0xBF72, jmp(sym['hook_pad']) + b'\x4e\x71')
    # soft restarts: tell them apart from a real reset
    for a in (0x113A28, 0x11CFF0):
        expect(rom, a, jmp(0x200), 'jmp $200')
        put(rom, a, jmp(sym['warm_restart']))
    # continue countdown expired: high-score entry, then the soft restart
    expect(rom, 0x639C, b'\x2e\x7c' + be32(0xFFFFFC) + b'\x4e\xfa', 'movea + jmp $200')
    put(rom, 0x639C, jmp(sym['hook_game_over']))
    # DIP switches / Home options, bonus life, continues, demo sounds
    clr_l = lambda a: b'\x42\xb9' + be32(a)
    for site, orig, name in (
            (0x61A2, clr_l(0xFFC570), 'hook_player_init'),
            (0x7890, clr_l(0xFFC040), 'hook_score_init'),
            (0x779A, b'\x22\x14\xb2\xac\x00\x04', 'hook_score_added'),
            (0x62FA, b'\x4a\x79' + be32(0xFFC594), 'hook_continue_tick')):
        expect(rom, site, orig, name)
        put(rom, site, jsr(sym[name]))
    expect(rom, 0x6348, b'\x13\xfc\x00\x03' + be32(0xFFC500), 'continue lives')
    put(rom, 0x6348, jsr(sym['hook_continue_lives']) + b'\x4e\x71')
    expect(rom, 0x89E4, jmp(0x11C73E), 'sound play entry')
    put(rom, 0x89E4, jmp(sym['hook_sound_play']))
    # player 2: Maximo's frames (same layout as Arthur's banks) and the
    # sprite-table DMA in each stage loop
    art = os.path.join(os.path.dirname(build_dir.rstrip('/')), '..', 'art', 'maximo')
    for name, at in (('maximo_bankB.bin', 0x3C0000), ('maximo_bankA.bin', 0x3CA000)):
        data = open(os.path.join(art, name), 'rb').read()
        assert (at & 0x1FFFF) + len(data) <= 0x20000      # DMA source boundary
        put(rom, at, data)
    # Firebrand: his frames (with wing columns), flags and fireball, in the
    # 128 KiB DMA block at $3A0000
    fb = os.path.join(os.path.dirname(build_dir.rstrip('/')), '..', 'art', 'firebrand')
    for name, at, size in (('firebrand_bank.bin', 0x3A0000, 108 * 0x300),
                           ('firebrand_flags.bin', 0x3B6000, 108),
                           ('firebrand_fire.bin', 0x3B6100, 0x100),
                           ('firebrand_mapicon.bin', 0x3B6200, 0x80)):
        data = open(os.path.join(fb, name), 'rb').read()
        assert len(data) == size, name
        assert (at & 0x1FFFF) + len(data) <= 0x20000      # DMA source boundary
        put(rom, at, data)
    # Arthur's frame upload ($68F4): Firebrand uploads his own at the sprite DMA
    expect(rom, 0x690E, jsr(0x704BE), 'Arthur frame DMA')
    put(rom, 0x690E, jsr(sym['hook_arthur_dma']))
    # stage-map marker: Firebrand's head instead of Arthur's helmet
    expect(rom, 0x113DA2, bytes.fromhex('33fc02a900c00000'), 'map marker tile')
    put(rom, 0x113DA2, jsr(sym['hook_map_marker']) + b'\x4e\x71')
    # --- engine speed (all modes) ---
    # object/player pass ($69A2): the 14-compare type chain as a table
    # (src_patch/inplace/obj_type.s; tools/re/test_inplace.py checks it)
    expect(rom, 0x69DA, bytes.fromhex('78000c2c000b000a677e'), 'object type chain start')
    expect(rom, 0x6A5E, bytes.fromhex('66000236'), 'object type chain end')
    code = open(os.path.join(build_dir, '..', 'inplace', 'obj_type.bin'), 'rb').read()
    assert len(code) <= 0x6A62 - 0x69DA
    put(rom, 0x69DA, code + b'\x4e\x71' * ((0x6A62 - 0x69DA - len(code)) // 2))
    # 40-slot object pass ($114704): the 19-compare type chain as a table
    # (src_patch/inplace/obj_sum.s; tools/re/test_ab.py checks it)
    expect(rom, 0x114746, bytes.fromhex('0c2c0007000a6700016c'), 'slot type chain start')
    expect(rom, 0x1147EE, bytes.fromhex('0c2c000c000a660000a0'), 'slot type chain end')
    code = open(os.path.join(build_dir, '..', 'inplace', 'obj_sum.bin'), 'rb').read()
    assert len(code) <= 0x1147F8 - 0x114746
    put(rom, 0x114746, code + b'\x4e\x71' * ((0x1147F8 - 0x114746 - len(code)) // 2))
    # tombstone check ($10442A): the arcade's rules (glue.s tomb_check)
    expect(rom, 0x10442A, bytes.fromhex('4a3900ffc512670c'), 'tombstone check')
    put(rom, 0x10442A, jmp(sym['tomb_check']))
    # ... and its handler pick ($6A88, an 11-compare chain on d4) by table
    expect(rom, 0x6A88, bytes.fromhex('0c44000d67000516'), 'object handler chain')
    put(rom, 0x6A88, jmp(sym['obj_dispatch']))
    # stage 1's 40-slot pass ($768A): its 9-compare type chain by table
    expect(rom, 0x76A4, bytes.fromhex('0c2c0007000a670000b0'), 'stage-1 slot type chain')
    put(rom, 0x76A4, jmp(sym['slot_dispatch']))
    # sprite buffer clear before each sprite build (128 single clr.l): movem.
    # At the entry of each stage's build it is also the render-skip gate
    # (glue.s hook_sat_dma / render_gate); $1118BC is the stage-6 "no
    # sprites" path, not a build.
    for a in (0x9A0E, 0x105502, 0x106434, 0x10F3D2, 0x110368, 0x11130C, 0x1118BC, 0x111B1A):
        expect(rom, a, bytes.fromhex('43f900ffb500707f429951c8fffc'), 'sprite buffer clear')
        put(rom, a, jsr(sym['clear_sat' if a == 0x1118BC else 'render_gate']) + b'\x4e\x71' * 4)
    # render skip: decided at the start of every stage-loop update (pace.c)
    expect(rom, 0x6938, jmp(0x114F58), 'update start')
    put(rom, 0x6938, jmp(sym['pace_hook']))
    expect(rom, 0x92A0, bytes.fromhex('4ebac05633fc002f00ffb204'), 'stage-1 sprite build')
    put(rom, 0x92A0, jmp(sym['render_gate1']))
    expect(rom, 0x4CBE, bytes.fromhex('7000303900ffb20c'), 'stage-1 second sprite pass')
    put(rom, 0x4CBE, jmp(sym['render_gate2']) + b'\x4e\x71')
    # sound driver request scan: byte-wise instead of 512 single-bit tests
    expect(rom, 0x11CADC, bytes.fromhex('700072003600'), 'sound request scan')
    put(rom, 0x11CADC, jmp(sym['sound_scan']))
    attenuate_music(rom, MUSIC_ATT)
    # shot-slot art upload: the fireball instead of the lance
    expect(rom, 0x11711E, jsr(0x704BE), 'shot art DMA')
    put(rom, 0x11711E, jsr(sym['hook_shot_dma']))
    # item pickups: armor/weapon copied back from the item context
    for a in (0x116472, 0x116884):
        expect(rom, a, bytes.fromhex('13eb000900ffc32813eb001100ffa218'), 'item copy-back')
        put(rom, a, jsr(sym['hook_item_copy']) + b'\x4e\x71' * 5)
    # co-op death handling (Arthur respawns instead of restarting the stage)
    expect(rom, 0x61DC, b'\x4a\x79' + be32(0xFFC570), 'death handling tst')
    put(rom, 0x61DC, jsr(sym['hook_p1_death']))
    for a in (0x644, 0x104888, 0x10ECD0, 0x10FBA6, 0x110B7E,
              0x1115FA, 0x1177A6, 0x118816, 0x118D80, 0x119896):
        expect(rom, a, jsr(0x704BE), 'sprite table DMA')
        put(rom, a, jsr(sym['hook_sat_dma']))
    # English / Japanese logo: title palette source and attract overlay sources
    lea = lambda reg, a: bytes([0x41 | (reg << 1), 0xF9]) + be32(a)
    expect(rom, 0xBB8, lea(0, 0x2045E8), 'title palette lea')
    put(rom, 0xBB8, jsr(sym['hook_title_pal']))
    for a, reg, src, name in ((0x11CE80, 0, 0x320000, 'ovl_tiles1'),
                              (0x11CE86, 1, 0x320920, 'ovl_map'),
                              (0x11CF0C, 0, 0x320260, 'ovl_tiles2'),
                              (0x11CF2C, 0, 0x3206E0, 'ovl_tiles3')):
        expect(rom, a, lea(reg, src), 'overlay lea')
        put(rom, a, jsr(sym[name]))


FRAME = 0x200                  # 32x32 4bpp, 16 tiles column-major
MAXIMO_A = 0x109E2             # bank A: boot-time copy of A0..A10, loaded to VRAM $6000
MAXIMO_B = 0x41000             # bank B: B0..B64 = $41000..$491FF
# In play the frame for pose p is DMA'd to VRAM $6000 from the long at $2B234 + 8p
# ($68B2). Poses 0..82 read $40000..$49000: A0-A4, A7-A9 live at $40000..$40E00
# (A5/A6 are poses 5/6 = A3/A2 again) and A10 *is* $41000, i.e. B0's slot.
# Poses 83..96 ($49200..$4A000) are the frog. The intermission uses its own table
# at $8AAD4 -> $C0000.. with copies of the walks, plus $C0200 (fist raised, no
# helmet), which exists only there: bank C.
STREAM_A = {0: 0x40000, 1: 0x40200, 2: 0x40400, 3: 0x40600, 4: 0x40800,
            7: 0x40A00, 8: 0x40C00, 9: 0x40E00, 10: 0x41000}
INTERMISSION = [('A', 0, 0xC0400), ('A', 1, 0xC0600), ('A', 2, 0xC0800),
                ('A', 3, 0xC0A00), ('A', 4, 0xC0C00), ('B', 9, 0xC0E00),
                ('B', 41, 0xC1000), ('B', 42, 0xC1200), ('B', 43, 0xC1400),
                ('B', 44, 0xC1600)]
BANK_C = [0xC0200]


def install_maximo(rom, art_dir):
    """Replace Arthur's sprite frames with art/maximo/maximo_bank{A,B,C}.bin (same
    layout and palette; exported by art/maximo_options/src/export.py or the editor)
    everywhere the game reads them. Bank B is 65 frames (last = boxer-left
    crouch-throw at $49000); an older 64-frame file leaves that frame as Arthur's.
    Bank C (intermission-only frames) is optional."""
    a = open(art_dir + '/maximo_bankA.bin', 'rb').read()
    b = open(art_dir + '/maximo_bankB.bin', 'rb').read()
    try:
        c = open(art_dir + '/maximo_bankC.bin', 'rb').read()
    except FileNotFoundError:
        c = None
        print('no maximo_bankC.bin; the intermission fist-raised pose stays Arthur')
    if c is not None and len(c) != len(BANK_C) * FRAME:
        sys.exit(f'maximo_bankC.bin is {len(c)} bytes, expected {len(BANK_C) * FRAME}')
    if len(a) != 11 * FRAME:
        sys.exit(f'maximo_bankA.bin is {len(a)} bytes, expected {11 * FRAME}')
    if len(b) == 72 * FRAME:
        # the co-op layout (art/maximo_options/src/export.py): 72 frames from
        # $40000; the first 8 repeat bank A (A0-A4, A7-A9), so B0 is frame 8
        b = b[8 * FRAME:]
    if len(b) not in (64 * FRAME, 65 * FRAME):
        sys.exit(f'maximo_bankB.bin is {len(b)} bytes, expected {65 * FRAME} (or 72 frames from $40000)')
    if len(b) == 64 * FRAME:
        print('maximo_bankB.bin has 64 frames; B64 ($49000) stays Arthur')
    fa = lambda k: a[k * FRAME:(k + 1) * FRAME]
    fb = lambda k: b[k * FRAME:(k + 1) * FRAME]
    for dup, src in ((5, 3), (6, 2)):
        if fa(dup) != fa(src):
            print(f'warning: A{dup} differs from A{src}; the game only shows A{src}')
    if fb(0) != fa(10):
        print('warning: B0 differs from A10; they share $41000, A10 is used')
    put(rom, MAXIMO_A, a)
    put(rom, MAXIMO_B, b)
    for k, addr in STREAM_A.items():
        put(rom, addr, fa(k))
    for bank, k, addr in INTERMISSION:
        put(rom, addr, fa(k) if bank == 'A' else fb(k))
    if c is not None:
        for k, addr in enumerate(BANK_C):
            put(rom, addr, c[k * FRAME:(k + 1) * FRAME])


def main(src, dst, features=None, maximo=None):
    rom = bytearray(open(src, 'rb').read())
    if len(rom) != SRC_SIZE:
        sys.exit(f'input is {len(rom):#x} bytes, expected {SRC_SIZE:#x}')
    if struct.unpack('>H', rom[0x18E:0x190])[0] != SRC_SUM:
        sys.exit('input header checksum is not EE66; wrong input ROM?')
    rom += b'\xff' * (OUT_SIZE - len(rom))

    # --- stub area -------------------------------------------------------
    stubs = bytearray()

    def stub(code):
        addr = PATCH_BASE + len(stubs)
        stubs.extend(code)
        if len(stubs) & 1:
            stubs.append(0x4E)          # never executed, keeps alignment
            stubs.append(0x71)
        return addr

    # move.w #0,$C00000 ; rts   (write-only, same flags as clr.w)
    vdp_zero_w = stub(b'\x33\xfc' + be16(0) + be32(0xC00000) + b'\x4e\x75')
    # move.l #0,$C00000 ; rts
    vdp_zero_l = stub(b'\x23\xfc' + be32(0) + be32(0xC00000) + b'\x4e\x75')
    # tst.w $C00004 ; lea $FF0000,a0 ; rts
    boot_vdp = stub(b'\x4a\x79' + be32(0xC00004) +
                    b'\x41\xf9' + be32(0xFF0000) + b'\x4e\x75')
    # move.w #$100,$A11200 ; jmp z80_busreq_wait ($11CD24, preserves d0, rts)
    z80_unreset = stub(b'\x33\xfc' + be16(0x100) + be32(0xA11200) +
                       b'\x4e\xf9' + be32(0x11CD24))

    # --- 1. VDP data-port read-modify-write ------------------------------
    for a in CLR_W:
        expect(rom, a, b'\x42\x79' + be32(0xC00000), 'clr.w $C00000')
        put(rom, a, jsr(vdp_zero_w))
    for a in CLR_L:
        expect(rom, a, b'\x42\xb9' + be32(0xC00000), 'clr.l $C00000')
        put(rom, a, jsr(vdp_zero_l))

    # --- 2. clear VDP pending-command latch at boot -----------------------
    # (with --features, hook_ramclear takes this site over and does the same)
    expect(rom, 0x28E, b'\x41\xf9' + be32(0xFF0000), 'boot lea $FF0000,a0')
    put(rom, 0x28E, jsr(boot_vdp))

    # --- 3. re-wait for Z80 BUSACK after reset release --------------------
    expect(rom, 0x11C66E, b'\x33\xfc\x01\x00\x00\xa1\x12\x00', 'Z80 unreset')
    put(rom, 0x11C66E, jsr(z80_unreset) + b'\x4e\x71')

    # --- 4. attract overlay cache ------------------------------------------
    # The overlay code caches which overlay's tiles are in VRAM ($FF86A0 kind,
    # $FF86A2 segment). The demo-death restart paths `jmp $2CC` re-run VRAM init
    # (overwriting the logo tiles) but keep RAM, so the stale cache made the logo
    # draw with wrong tiles. Invalidate it first, as the $638C path already does.
    # move.w #-1,$FF86A0 ; jmp $2CC
    reinit = stub(b'\x33\xfc' + be16(0xFFFF) + be32(0xFF86A0) +
                  b'\x4e\xf9' + be32(0x2CC))
    for a in (0x113A06, 0x113E1E):
        expect(rom, a, b'\x4e\xf9' + be32(0x2CC), 'jmp $2CC')
        put(rom, a, b'\x4e\xf9' + be32(reinit))

    # --- 5. blink routine vs. death animation ------------------------------
    # replaces `move.w 12(a4),14(a4)`; copies only animations that have a
    # frame in the $4A77E table (terminators like $0B map to $FFFF)
    blink_copy = stub(bytes.fromhex(
        '48e78080'          # movem.l d0/a0,-(sp)
        '302c000c'          # move.w  12(a4),d0
        '0c400061'          # cmpi.w  #97,d0
        '6414'              # bcc.s   out
        'd040'              # add.w   d0,d0
        '41f90004a77e'      # lea     $4A77E,a0
        '4a700000'          # tst.w   0(a0,d0.w)
        '6b06'              # bmi.s   out
        '396c000c000e'      # move.w  12(a4),14(a4)
        '4cdf0101'          # out: movem.l (sp)+,d0/a0
        '4e75'))            # rts
    expect(rom, 0x5E4A, b'\x39\x6c\x00\x0c\x00\x0e', 'blink anim copy')
    put(rom, 0x5E4A, jsr(blink_copy))

    assert len(stubs) <= 0x100
    put(rom, PATCH_BASE, stubs)

    if features:
        install_features(rom, features)
    if maximo:
        install_maximo(rom, maximo)

    # --- 6. header ----------------------------------------------------------
    title = b"GHOSTS'N GOBLINS".ljust(48)
    put(rom, 0x120, title)
    put(rom, 0x150, title)
    put(rom, 0x1A0, be32(0) + be32(OUT_SIZE - 1))
    put(rom, 0x1B0, b' ' * 0x40)               # no SRAM, no modem, blank memo
    if features:
        # 8 KiB battery SRAM on odd bytes at $200001, switched in via $A130F1
        put(rom, 0x1B0, b'RA\xf8\x20' + be32(0x200001) + be32(0x203FFF))
    words = struct.unpack('>%dH' % ((OUT_SIZE - 0x200) // 2), rom[0x200:])
    put(rom, 0x18E, be16(sum(words) & 0xFFFF))

    open(dst, 'wb').write(rom)
    print(f'wrote {dst}: {len(rom):#x} bytes, checksum '
          f'{struct.unpack(">H", rom[0x18E:0x190])[0]:04X}')


if __name__ == '__main__':
    args = sys.argv[1:]
    opts = {}
    for flag in ('--features', '--maximo'):
        if flag in args:
            i = args.index(flag)
            opts[flag[2:]] = args[i + 1]
            del args[i:i + 2]
    if len(args) != 2:
        sys.exit('usage: patch_gng.py <input.bin> <output.bin> '
                 '[--features src_patch/build] [--maximo art/maximo]')
    main(args[0], args[1], **opts)
