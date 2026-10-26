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
    # intro.c's logos, chant and jingle, linked at $350000 (src_patch/link.ld)
    intro = os.path.join(build_dir, 'intro.bin')
    if os.path.exists(intro):
        data = open(intro, 'rb').read()
        assert 0x350000 + len(data) <= FEATURE_BASE, 'intro data runs into the code blob'
        put(rom, 0x350000, data)
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
    # standing up after a crouch: no walk on the stand-up frame, as the
    # arcade's $9A6C (arthur.s stand_up, walk_gate)
    expect(rom, 0x7F98, bytes.fromhex('197c0007000c422c000b4e75'), 'crouch stand-up')
    put(rom, 0x7F98, jmp(sym['stand_up']) + b'\x4e\x71' * 3)
    expect(rom, 0x8114, bytes.fromhex('4a3900ff94596618'), 'walk gate')
    put(rom, 0x8114, jmp(sym['walk_gate']))
    # ... and the crouch-entry frame still walks, as the arcade's ($9305, $940E)
    expect(rom, 0x7E56, bytes.fromhex('197c0001000b'), 'crouch entry')
    put(rom, 0x7E56, jsr(sym['crouch_in']))
    # ladder bottom: off the ladder above the floor he falls the next frame,
    # as the arcade's, instead of snapping down (arthur.s lad_exit, ground_snap)
    expect(rom, 0x7E42, bytes.fromhex('422c00080c2c00040009'), 'ladder end')
    put(rom, 0x7E42, jsr(sym['lad_exit']) + b'\x4e\x71' * 2)
    expect(rom, 0x8698, bytes.fromhex('610000aa4a80'), 'ground floor snap')
    put(rom, 0x8698, jsr(sym['ground_snap']))
    # armor lost on the hit frame (arcade $0158), not at the knockback's
    # landing; the knockback keeps its own marker (arthur.s kb_*)
    expect(rom, 0x5FA4, bytes.fromhex('197c00780009'), 'armored hit')
    put(rom, 0x5FA4, jsr(sym['kb_hit']))
    expect(rom, 0x5AAE, bytes.fromhex('4a2c00286614'), 'hit dispatch')
    put(rom, 0x5AAE, jmp(sym['kb_dispatch']))
    expect(rom, 0x5ADC, bytes.fromhex('4a2c002866000370'), 'knockback armor check')
    put(rom, 0x5ADC, bytes.fromhex('4a2c004367000370'))     # tst.b 67(a4); beq: the marker
    expect(rom, 0x5B44, bytes.fromhex('4a2c002867025c40'), 'knockback animation')
    put(rom, 0x5B44, jsr(sym['kb_anim']) + b'\x4e\x71')
    expect(rom, 0x5CD4, bytes.fromhex('197c00010028'), 'knockback landing armor')
    put(rom, 0x5CD4, jsr(sym['kb_land']))
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
    # boss hit points as the arcade's: Astaroth 10 ($DB1B; port 6), the Satans 10
    # ($BEF1; port 4); the dragon's head 6 ($D596; port 10) is set by dragon.c
    for a, old, new in ((0x111C00, '197c0006000b', '197c000a000b'), (0x110586, '197c0004000b', '197c000a000b')):
        expect(rom, a, bytes.fromhex(old), 'boss hit points')
        put(rom, a, bytes.fromhex(new))
    # Unicorn (stage 1 boss, handler $706FA): its walk ($70A44) doesn't follow the floor.
    # The arcade's walk only moves it ($A435-$A449, no floor check); the port
    # snapped it to the floor within 8 px ($70AE2), so walking off the raised
    # ground (y 78.6) dropped it to 70.6 just before a jump, and the jump ran
    # 8 px low.
    expect(rom, 0x70A70, bytes.fromhex('610000706016'), 'unicorn walk floor snap')
    put(rom, 0x70A70, b'\x4e\x71\x4e\x71')
    # stage 1's terrain map window as the arcade's (cam/16 - 15 .. + 16, not
    # - 8 .. + 23), so the columns past the screen hold what the arcade's do
    # (arthur.s map_start_*): the unicorn's landing probe at the arena's end
    for a, reg in ((0x93E0, 'd6'), (0x9454, 'd0')):
        n = {'d6': 6, 'd0': 0}[reg]
        expect(rom, a, bytes([0xE8, 0x48 | n, 0x51, 0x40 | n, 0x6A, 0x02, 0x70 | (n << 1), 0x00]), 'stage-1 map window')
        put(rom, a, jsr(sym['map_start_' + reg]) + b'\x4e\x71')
    # the Satans (stages 5 and 6): the arcade's handler (satan.c) for the port's
    # states 0 and 1; its death (state 2) and removal/key (state 3) stay
    for a, old in ((0x110578, '4a2c0005670002c8'), (0x1105C6, '4a2c0005670002' + '7a')):
        expect(rom, a, bytes.fromhex(old), 'Satan state entry')
        put(rom, a, jsr(sym['hook_satan']) + b'\x60\x00' + be16(0x110846 - (a + 8)))
    # ... and the arcade's 22-frame burst before its death's score phase
    expect(rom, 0x11080E, bytes.fromhex('4a2c00086620'), 'Satan death entry')
    put(rom, 0x11080E, jsr(sym['hook_satan_die']))
    expect(rom, 0x11082C, jsr(0xB7F2), 'Satan death sound')
    put(rom, 0x11082C, b'\x4e\x71' * 3)
    # the arcade's second random ($68F9, $6E/$6F = $FFC62C, arcrand.c) is seeded
    # at power-on and game start only: the ten stage inits reloaded $87CD
    for a in (0x9C0, 0x104728, 0x10EB60, 0x10FA2A, 0x1109D0, 0x111450, 0x11761C,
              0x118688, 0x118BEC, 0x1196C8):
        expect(rom, a, bytes.fromhex('42b900ffc62c'), 'random state clear')
        put(rom, a, bytes.fromhex('423900ffc62f'))         # clr.b $FFC62F (unused) instead
        expect(rom, a + 14, bytes.fromhex('33fc87cd00ffc62c'), 'random seed')
        put(rom, a + 14, b'\x4e\x71' * 4)
        if a == 0x9C0:
            expect(rom, a + 22, bytes.fromhex('13fc000000ffc62e'), 'random last')
            put(rom, a + 22, b'\x4e\x71' * 4)
        else:
            expect(rom, a + 22, bytes.fromhex('423900ffc62e'), 'random last')
            put(rom, a + 22, b'\x4e\x71' * 3)
    # a new game starts with 0 points, as the arcade's: the port's start block
    # ($28EEE, copied to $FFC000 by $7874) gave 600
    expect(rom, 0x28EEE, bytes.fromhex('0000060000010000'), 'start score')
    put(rom, 0x28EEE, bytes(4))
    # weapons against enemy shots on odd frames (shots.c, arcade $F3CE)
    expect(rom, 0x5930, bytes.fromhex('082c000000106600007e'), 'odd-frame shot check')
    put(rom, 0x5930, jsr(sym['shot_check']))
    # man-eater plant (arcade type 17, port index 2) hit box as the arcade's
    # ($EF62 / $F040: +-12 x, +-16 y): no weapon shift of 18 px along its
    # flight and no 5 px y offset ($6C0E), y range 32 instead of 37
    expect(rom, 0x6BB8, bytes.fromhex('6606'), 'plant box shift')
    put(rom, 0x6BB8, bytes.fromhex('6006'))
    for w in range(5):                  # $2AC94: 5 weapons x 18 kinds x 16 bytes
        r = 0x2AC94 + (w * 18 + 2) * 16
        expect(rom, r, bytes.fromhex('000c0018001000'), 'plant box')
        expect(rom, r + 7, b'\x25', 'plant box y range')
        put(rom, r + 7, b'\x20')
    # the dragon (stages 3, 4, 6) as the arcade's (dragon.c, dragon_glue.s):
    # its type-12 handler, the spawn position (stage 6: the absolute record in
    # the tower), every segment open to weapons, the arcade's weapon box, score
    # index and weapon-2 pass-through, and its fire flying straight along its side
    expect(rom, 0x106F80, bytes.fromhex('48e70ffe0c2c000c000a'), 'dragon handler')
    put(rom, 0x106F80, jmp(sym['dragon_entry']))
    expect(rom, 0x106F10, bytes.fromhex('301306400180348002800000ffffe18825400010'
                                        '322b000e064100403541000202810000ffffe18925410014'), 'dragon spawn position')
    put(rom, 0x106F10, jsr(sym['dragon_spawn_pos']) + b'\x60\x24' + b'\x4e\x71' * 18)
    # the object pass skipped the weapon test for every dragon node but the head
    expect(rom, 0x105798, bytes.fromhex('4a2c00066600009e'), 'dragon body weapon test')
    put(rom, 0x105798, b'\x4e\x71' * 4)
    # speed: the weapon test's set-up and call are skipped for every slot that
    # isn't live and on screen, all types but 8 (dragon_glue.s dragon_wtest:
    # the same RAM and registers as the test, which finds nothing for them)
    expect(rom, 0x114D58, bytes.fromhex('0c2c000c000a') + jmp(0x105796), 'weapon test entry')
    put(rom, 0x114D58, jmp(sym['dragon_wtest']) + b'\x4e\x71' * 3)
    # weapon-hit table ($2AC94: 5 weapons x 18 kinds x 16 bytes; kind 11 = type 12):
    # box x +-12, y +-10 (arcade $F0A0; port +-16, +-16), score index 4 (200,
    # $F0E4; port 9 = 1,000), and weapon 2 passes through (the arcade's $F0EB
    # is per weapon, 0 for weapon 2 against every enemy; the port stopped it here)
    for w in range(5):
        a = 0x2AC94 + (w * 18 + 11) * 16
        expect(rom, a, bytes.fromhex('0010002000100020f8010901'), 'dragon weapon box')
        put(rom, a, bytes.fromhex('000c0018000a0014f80104') + (b'\x00' if w == 2 else b'\x01'))
    # its fire (type 9): no aim at Arthur ($107510 `jsr $7442`, the direction
    # stays the side set by dragon.c), and 3.125 px/frame straight ahead
    expect(rom, 0x107510, bytes.fromhex('4eb90000744219400018'), 'dragon fire aim')
    put(rom, 0x107510, b'\x4e\x71' * 5)
    expect(rom, 0x107540, bytes.fromhex('43f90005052a'), 'dragon fire speed table')
    put(rom, 0x107540, b'\x43\xf9' + be32(sym['dragon_fire_vel']))
    # stage 4 type-14 enemy: any size-class change moves it by the arcade's
    # anchor difference (glue.s size_shift); the port trapped on 10 -> 1
    expect(rom, 0x10F816, bytes.fromhex('7000102c0019'), 'type-14 size class change')
    put(rom, 0x10F816, jmp(sym['size_shift']))
    # the arcade's stage-draw wait before play (pad.c stage_hold), at the entry
    # of each stage loop (all ten set the sr and 'LIVE' the same way)
    for a in (0x5A8, 0x1046E4, 0x10EB26, 0x10F9F0, 0x110994, 0x111414, 0x1175BA,
              0x11864C, 0x118BB0, 0x11968C):
        expect(rom, a, bytes.fromhex('46fc230023fc4c49564500ff7ff0'), 'stage loop entry')
        put(rom, a, jsr(sym['stage_hold_entry']) + b'\x4e\x71' * 4)
    # Arthur's weapons drawn 8 px low: their builder used y = 360 + camera - y,
    # every other builder 352 (all five weapons and their burst frames)
    expect(rom, 0x115994, bytes.fromhex('06410168'), 'weapon sprite y')
    put(rom, 0x115994, bytes.fromhex('06410160'))
    # final-room flames (type 10, builder $AF4A): frames 1-30 had their left and
    # right 16 px halves swapped (records at $125620 via $123B3E)
    for f in range(1, 31):
        a = 0x125620 + struct.unpack('>h', rom[0x123B3E + 2 * f:0x123B40 + 2 * f])[0]
        expect(rom, a, b'\x00\x04', 'flame pieces')
        for i in range(4):
            r = a + 2 + 6 * i
            dx = rom[r:r + 2]
            expect(rom, r, dx if dx in (b'\xff\xf0', b'\x00\x00') else b'?', 'flame piece x')
            put(rom, r, b'\x00\x00' if dx == b'\xff\xf0' else b'\xff\xf0')
    # zombies coming out of the ground or sinking: the arcade's 1- and 2-piece
    # frames 8 px higher (glue.s zombie_y)
    expect(rom, 0x7CF8, bytes.fromhex('3a873b7c0f000002'), 'zombie sprite y')
    put(rom, 0x7CF8, jsr(sym['zombie_y']) + b'\x4e\x71')
    # after the second loop's ending: play on from stage 1 (glue.s loop_again)
    expect(rom, 0x113A1C, bytes.fromhex('527900ff7fd0'), 'second-loop ending')
    put(rom, 0x113A1C, jmp(sym['loop_again']))
    # continue countdown: 640 frames shown as frames / 64 (the arcade's BCD
    # counter from 10, a step every 64 frames: $785D, $78A6), and Start with
    # fire or jump in Arcade mode (glue.s cont_start)
    expect(rom, 0x62C2, bytes.fromhex('33fc025800ffc594'), 'continue countdown length')
    put(rom, 0x62C2, bytes.fromhex('33fc028000ffc594'))
    expect(rom, 0x6312, bytes.fromhex('80fc003c'), 'continue countdown digit')
    put(rom, 0x6312, bytes.fromhex('80fc0040'))
    expect(rom, 0x6328, bytes.fromhex('0839000000ff70006600ffc6'), 'continue start test')
    put(rom, 0x6328, jsr(sym['cont_start']) + bytes.fromhex('6600ffc8') + b'\x4e\x71')
    # checkpoint: the arcade only refills the timer ($ED73); the port also
    # stopped the hurry tune and restarted the stage music with <= 15 s left
    expect(rom, 0x103CBE, b'\x62\x12', 'checkpoint music restart')
    put(rom, 0x103CBE, b'\x60\x12')
    # the random source runs on like the arcade's frame counter (glue.s rng_*),
    # and the item cycle carries over (item_init)
    for a in (0x927C, 0x99EC, 0x104F7E, 0x1054E2, 0x10F2D4, 0x11026A, 0x111226, 0x111AF2):
        expect(rom, a, bytes.fromhex('522b000649f900ffb800'), 'random counter step')
        put(rom, a, jsr(sym['rng_tick']) + b'\x4e\x71\x4e\x71')
    # moving platforms stand still a frame at each segment change (glue.s mover_load)
    expect(rom, 0x106B24, bytes.fromhex('3958001c195800181950001a'), 'platform mover load')
    put(rom, 0x106B24, jsr(sym['mover_load']) + b'\x4e\x75' + b'\x4e\x71' * 2)
    for a in (0x10F59C, 0x11A3CC, 0x11A5EA):
        expect(rom, a, bytes.fromhex('650272003941001c'), 'platform mover load')
        put(rom, a, jsr(sym['mover_load2']) + b'\x4e\x75')
    # ... and the rank creeps up with play time (glue.s rank_creep, arcade
    # $EEB9); a stage clear adds 4 to the base rank ($FFC501, arcade <$61 at
    # $6C58), not to the crept working rank $FFA208 the stage-end blocks load
    for a in (0x8A802, 0x117CEC, 0x118272, 0x11929E):
        expect(rom, a, bytes.fromhex('177900ffa208000e'), 'stage-end rank load')
        put(rom, a, bytes.fromhex('177900ffc501000e'))
    for a in (0x91D4, 0x9952, 0x104EE6):
        expect(rom, a, bytes.fromhex('41f900014f60'), 'random counter init')
        put(rom, a, jsr(sym['rng_init']))
    expect(rom, 0x25A8, bytes.fromhex('41f900ffc700'), 'item cycle save')
    put(rom, 0x25A8, jsr(sym['item_save']))
    expect(rom, 0x25DA, bytes.fromhex('41f90006ea6a'), 'item cycle init')
    put(rom, 0x25DA, jsr(sym['item_init']))
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
    install_stage_end(rom, sym)
    install_crow_tdevil(rom, sym)
    install_hud(rom, sym)
    install_petite(rom, sym)


RENDER_GATES = (0x9A0E, 0x105502, 0x106434, 0x10F3D2, 0x110368, 0x11130C, 0x111B1A)


def install_stage_end(rom, sym):
    """After a boss dies, the arcade's stage-end freeze (src_patch/stageend.s)."""
    jmp = lambda a: b'\x4e\xf9' + be32(a)
    # the enemy pass cores (enemies, shots, their hits)
    for a, core, name in ((0x6974, 0x69A2, 'se_objpass'), (0x1055A4, 0x1055D4, 'se_objpass2')):
        expect(rom, a, b'\x4e\xba' + struct.pack('>h', core - a - 2) + bytes.fromhex('48e7009c'), 'enemy pass core')
        put(rom, a, jmp(sym[name]) + b'\x4e\x71')
    # the weapon pass, the item objects and their draw
    for a, old, name in ((0xBC26, 0x1158D0, 'se_wmove'), (0xC348C, 0x11677A, 'se_items'),
                         (0xC35E8, 0x11693E, 'se_items_draw')):
        expect(rom, a, jmp(old), name)
        put(rom, a, jmp(sym[name]))
    # weapons are drawn by their on-screen flag +9 (se_wmove sets it), not +8
    expect(rom, 0x115960, bytes.fromhex('4a2c0008673c'), 'weapon draw test')
    put(rom, 0x115960, bytes.fromhex('4a2c0009673c'))
    # the spawner runs after the scroll in every loop, as the arcade's $E950
    expect(rom, 0x91E, jsr(0xA460), 'stage-1 spawner call')
    put(rom, 0x91E, jsr(sym['se_spawn']))
    for a in (0x104AD2, 0x10EF2E, 0x10FDDE, 0x110DDC, 0x1179FC, 0x118A80, 0x118FBE, 0x119B08):
        expect(rom, a, jsr(0x26DA), 'early spawner call')
        put(rom, a, b'\x4e\x71' * 3)
    expect(rom, 0x104AF0, bytes.fromhex('4ebaf890'), 'scroll call')
    expect(rom, 0x104B0C, jsr(0x525E), 'call after the scroll')
    put(rom, 0x104B0C, jsr(sym['se_525e_spawn']))
    for a in (0x10EF44, 0x10FDF4, 0x110DF2, 0x117A20, 0x118A98, 0x118FD6, 0x119B20):
        expect(rom, a, jsr(0x104382), 'scroll call')
        put(rom, a, jsr(sym['se_scroll_spawn']))
    # terrain map windows of stages 2-5: the arcade's cam/16 - 15 (src_patch/mapwin.s)
    for a, name, y_part, old in ((0x11A986, 'mw_stage2', 0x11A9B0, '3c3900ff9100e84e0c4600e8'),
                                 (0x104D16, 'mw_stage3', 0x104D34, '3c3900ff9100e84e0c460008'),
                                 (0x10F124, 'mw_stage4', None, '3c3900ff9100e84e0c4600e8'),
                                 (0x11001C, 'mw_stage5', 0x11003C, '3c3900ff9100e84e0c4601a8')):
        expect(rom, a, bytes.fromhex(old), 'map window ' + name)
        if y_part is None:
            put(rom, a, jmp(sym[name]))
        else:
            put(rom, a, jsr(sym[name]) + b'\x60' + bytes([y_part - (a + 8)]))
    # stage 1's weapons against the tombstones
    expect(rom, 0x102C56, bytes.fromhex('4eba18ee33fc004700ffcfb0'), 'weapon tombstone check')
    put(rom, 0x102C56, jsr(sym['se_wtomb']) + b'\x4e\x71' * 3)
    # the sprite builds hide the frozen enemies, shots and weapons; the
    # update start puts them back and takes weapon slot 0 for the key
    for a in RENDER_GATES:
        expect(rom, a, jsr(sym['render_gate']), 'render gate')
        put(rom, a, jsr(sym['se_rg']))
    expect(rom, 0x92A0, jmp(sym['render_gate1']), 'stage-1 render gate')
    put(rom, 0x92A0, jmp(sym['se_rg1']))
    expect(rom, 0x6938, jmp(sym['pace_hook']), 'update start')
    put(rom, 0x6938, jmp(sym['se_pace']))


def install_crow_tdevil(rom, sym):
    """Crows (type 1), stage 2 window/tower devils (type 4), the stage 3 Red Arremers (crow.c, tdevil.c)."""
    jmp = lambda a: b'\x4e\xf9' + be32(a)
    # crows, subtypes 3-5 ($44FE, stages 1 and 2): subtype 3 perches on random
    # timers before flying at Arthur, as the arcade's ($A725: $A755, then $A7DE);
    # only subtype 4 flies in from off the screen ($A812: $A72F). The port gave
    # subtype 3 the off-screen entry.
    expect(rom, 0x47FA, bytes.fromhex('0c2c000300066700'), 'crow subtype 3 entry')
    put(rom, 0x47FA, bytes.fromhex('0c2c000400066700'))
    # ... and its stage 2 hold-back (subtype 3 not set up while more than 512 px
    # right of the camera, $452C) goes: the arcade sets them up at once and they
    # wait for the on-screen flag
    expect(rom, 0x452C, bytes.fromhex('0c39000100ffc512661c'), 'stage 2 crow hold-back')
    put(rom, 0x452C, b'\x60\x24')
    # stage 2's type-4 devils: states 0 and 1 as the arcade's ($B146; tdevil.c)
    expect(rom, 0x107A5E, bytes.fromhex('7000102c00076700003c'), 'type 4 state dispatch')
    put(rom, 0x107A5E, jmp(sym['tdevil_entry']) + b'\x4e\x71\x4e\x71')
    # Red Arremers (type 5): the first state by subtype as the arcade's ($B66C:
    # subtype & 3, 0 -> 3), so subtype 0 (stage 3's after the checkpoint, which
    # follows Arthur into the dragon fight) starts at once ($B734) instead of
    # sleeping like subtype 1 until Arthur is within 48 px of its height
    expect(rom, 0x4278, bytes.fromhex('0c2c00020006670a197c0001000860000236197c000200086000022c'), 'Red Arremer first state')
    put(rom, 0x4278, bytes.fromhex('102c000602000003660270031940000860000234') + b'\x4e\x71' * 2)


def install_petite(rom, sym):
    """The Petite Devils (type 2, petite.c) and their fireball (the port's shot type 6)."""
    # states 0 and 1 of the type-2 handler as the arcade's ($A89C); 2 and 3 the port's
    expect(rom, 0x10C99A, bytes.fromhex('4ef90011c5c24e71'), 'type 2 handler')
    put(rom, 0x10C99A, b'\x4e\xf9' + be32(sym['petite_entry']) + b'\x4e\x71')
    # the shot type 6 set-up keeps a devil's fireball direction (no aim at Arthur)
    expect(rom, 0x72B6, bytes.fromhex('4eba018a19400018'), 'type 6 shot aim')
    put(rom, 0x72B6, jsr(sym['petite_shot_aim']) + b'\x4e\x71')
    # ... and moves it at the arcade's shot-8 speeds
    expect(rom, 0x72F2, bytes.fromhex('43f900029238'), 'type 6 shot speeds')
    put(rom, 0x72F2, jsr(sym['petite_shot_vel_sel']))
    # its death in stages 4 and 5 ($11AFEA): the arcade's sound $14 ($79B5 = $B7B2,
    # as stage 2's death $11BC0A has it) and 21 frames before the removal (port 36)
    expect(rom, 0x11AFF0, bytes.fromhex('4eb90000b7f2397c00240024'), 'type 2 death')
    put(rom, 0x11AFF0, bytes.fromhex('4eb90000b7b2397c00150024'))
    # stage 5's skulls (type 9): the arcade's ($CC45, skull.c) in states 0 and 1
    expect(rom, 0x110452, bytes.fromhex('4a2c00046748'), 'type 9 entry')
    put(rom, 0x110452, b'\x4e\xf9' + be32(sym['skull_entry']))


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



def install_hud(rom, sym):
    """The continue countdown as the arcade's: 10 to 01 on its own line (src_patch/hud.s)."""
    expect(rom, 0x62CA, bytes.fromhex('33fc003900ffc596'), 'continue count start')
    put(rom, 0x62CA, bytes.fromhex('33fc003a00ffc596'))
    expect(rom, 0x630A, bytes.fromhex('70003039 00ffc594 80fc0040 0c400009 63027009 06400030'.replace(' ', '')), 'continue digit')
    put(rom, 0x630A, jsr(sym['cont_digit']) + b'\x60' + bytes([0x6322 - 0x6312]) + b'\x4e\x71' * 8)
    expect(rom, 0x11D260, bytes.fromhex('7000303900ffc596044000300640825032003 3c100c000004cdf010f'.replace(' ', '')), 'continue digit draw')
    put(rom, 0x11D260, jsr(sym['cont_draw']) + b'\x4e\x71' * 9)

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
