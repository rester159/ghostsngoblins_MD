# GnG features patch layer

The port has no source, so new features are freestanding 68000 C/asm linked at
`$380000` (the padding above the original 3.3 MiB image) and hooked into the engine
by `tools/patch_gng.py --features src_patch/build`.

```bash
make -C src_patch
python3 tools/patch_gng.py "Ghosts'n Goblins (SMD) (PD).bin" build/GhostsNGoblins_plus.bin --features src_patch/build
```

Without `--features` the patcher produces the compatibility-only ROM.

## Features so far

- Boot flow: on a cold boot the SEGA and CAPCOM intros, then **ARCADE / HOME**, with `rester159, 2026` at the bottom. The previous port's own splash ("ARCADE MACHINE" and "PROGRAMED BY FRANK", `$CA6`) is never shown.
- **Intros** (`intro.c`, as in the Black Tiger port): the Revenge of Shinobi SEGA logo with the Sonic 1 "SE-GA" chant, then the SF2' CAPCOM logo with its FM jingle, about 9.5 s; Start skips them. The chant is streamed to the YM2612 DAC at 16 kHz by a small Z80 loop from a 32 KiB ROM bank; the jingle is written by the 68k. Afterwards the game's Z80 program (136 bytes from `$202380`, normally loaded only at power-on) is reloaded and its sound init re-run. On PAL every fifth frame steps twice, so the timing stays at 60 Hz. The logo art, palettes, chant and jingle are Sega's and Capcom's and aren't in this repository: `mkintro.py` reads them from the local intro kits (`SEGA_KIT`, `CHANT_KIT`, `CAPCOM_KIT`) into `build/intro.inc`, and without the kits the build skips the intros.
- **ARCADE**: the original title and attract loop. C inserts coins, Start starts, A takes over C's old action.
- **HOME**: 1 PLAYER starts straight into the intro. Start pauses and resumes during play, and music keeps running.
- **ARCADE → DIP SWITCHES**:
  - Coinage: 1C/1P, 1C/2P, 1C/3P, 2C/1P, 3C/1P, free play.
  - Lives: 3, 4, 5, 7.
  - Bonus life: 20K 70K every 70K, 30K 80K every 80K, 20K 80K, 30K 80K.
  - Difficulty: the four enemy parameter sets selected by `$FFC501` bits 4–5 (the port shipped on set 0, "EASY").
  - Demo sound, continue.
- **HOME → OPTIONS**:
  - Lives 1–9; continues 0–9 or infinite (Start continues during the countdown).
  - Bonus life, including none; difficulty.
  - English / Japanese title (arcade Makaimura logo on the menus, title screen and attract overlay).
  - Sound test.
- **High scores**: separate top-10 tables for Arcade and Home. Initials entry at game over, and TOP SCORE starts from the saved best.
- **Developer** (Home screen: Up Down Up Down Left Right Left Right, until a hardware reset):
  - Stage 1–6, starting lives, infinite lives, difficulty, sound test.
  - Launched games are practice runs and aren't ranked.
- DIP switches, Home options, the title choice and both tables are saved to battery SRAM.
- **HOME → 2 PLAYERS**: Maximo on pad 2, running on Arthur's own player routines through a context swap (`p2.c`).
  - **Movement:** the same walking, jumping, landing (terrain and tombstones), animation timing and facing as Arthur.
  - **Weapons:** his lances spawn from his own position (`$80BA`) into the shared weapon slots. The game moves them and scores their hits; both players share the engine's few on-screen shots.
  - **Getting hit:** enemies hit him through the engine's own collision, with Arthur's knockback and armor shatter (`$55E0`, run for him), down to boxers, then death.
  - **Death and respawn:** after dying, a player respawns 3 s later next to their partner (if the partner is alive and on the ground), otherwise where they fell. They come back armored (`$7FA4`, `$6456`, `$6928`, armor set `$FFC328 = 0`) with 3 s of the game's own blink invincibility (`$FFC309`).
  - **Arthur in co-op:** while Maximo is in the game, Arthur's death doesn't restart the stage (hook at `$61DC`).
  - **Lives and credits:** each player has their own lives (the Lives option). An out-of-lives player uses a shared credit to rejoin; with none left they are out. If Maximo is out, Arthur follows the normal 1P rules. When both are out, the game's continue and game-over flow runs.
  - **Each other:** the players pass through each other, but a player falling onto the partner's head is set on it and bounces off automatically with a full jump, once per jump; a second landing on the head falls through, and touching the ground re-arms it (`head_bounce` in `p2.c`).
  - **HUD:** "PLAYER2" and Maximo's lives in the top-right, in the game's own HUD tiles.
  - **Developer menu:** PLAYERS 1/2 launches co-op into any stage. Stages 1–6 were each run for 3,000 frames of random co-op play with no faults.
  - **Score:** shared team score; Maximo's kills count towards the single score.
- **HOME → FIREBRAND'S QUEST**: a one-player campaign as the Red Arremer (`firebrand.c`).
  - **Art:** Firebrand's own frames from Demon's Crest (stand, 6-frame walk, fire, jump, 6-frame flight, landing), captured headlessly with `tools/headless/snes_capture.py` (snes9x core) into `art/firebrand/dc/`, mapped to sprite palette line 0 by hand (`art/firebrand/src/dc.py`) and scaled to 70% so he matches Arthur's size (`art/firebrand/src/build.py`: palette-aware downscale; feet or body centre as the anchor). His head is a hand-drawn stamp (`art/firebrand/src/head.py`) placed where template matching finds his head in each source frame, because the dithered original turns to noise at 70%; the firing pose keeps its own head. Every frame Arthur can show maps to a pose of the same meaning and facing; walking and hovering play Firebrand's 6-frame cycles instead of Arthur's (`firebrand.c`). Frames wider than 32 px add two 8×32 columns at tiles `$690`/`$694`. His death is the game's enemy burn-up flames (palette line 2). The bank (108 × `0x300`) is at `$3A0000`.
  - **Hover:** hold jump after the top of a jump to hold the altitude for up to 2 s (`$FF9404` zeroed before the engine's fall step); landing refills it. Left/right steers at walking speed through the engine's wall-checked walk moves (`$11469C`/`$1146CE`). His flight cycle plays while hovering.
  - **One attack:** the lance's mechanics, drawn as the fireball from `art/firebrand/src/fire.py` (uploaded in place of the lance art for each shot slot, `$11711E`; right-moving shots get their two pieces swapped so the picture faces forward, and left-moving ones are drawn 14 px ahead because the game starts them over his body; either way the fireball leaves the mouth of his firing pose). The HUD weapon box shows the game's own fire icon (`$1037D4`). Pickups never change it.
  - **One hit:** never armored (`$FFC328 = 1`), so the first hit kills.
  - **Boxes:** weapon and armor pickups give 1,000 points instead (the game's score message `$0C00|8` on the queue at `$FFB400`).
  - **Head:** a hand-drawn head is stamped on every frame where his head is in profile (see Art); the firing pose gets an open-mouth version with fire in the mouth.
  - **Stage map and stage end:** the map marker between lives is Firebrand's head (`hook_map_marker` at `$113DA2` points it at tiles `$69C-$69F`), and the stage-end sequence's frames (`$C0000-$C1600`, the `$8AAD4` table) map to his poses, the fist-raise to his wings-spread flight frame.
  - **Frog:** the frog frames are in the ROM, but no code path in this port that I could find selects them; a frog frame would be shown unchanged.
  - **Start:** skips the princess scene (`$E0C`) and goes straight into stage 1.
  - **Developer menu:** PLAYERS 1 / 2 / FIREBRAND.
- **Engine speed (all modes, features build only):**
  - Measured with `tools/re/probe_rom.py` (timestamps every stage-1 update and every DMA) and `tools/re/uc_profile.py` (Unicorn, estimated cycles per routine). In play, with deaths excluded, 1P runs at 0.97-1.0 updates per frame in every stage; the earlier ~0.69 figure counted death and map sequences.
  - The sound driver's request scan (`$11CAB8`) tested 512 bits one at a time every update; it now skips clear longs and bytes (`sound_scan`, checked against the original by `tools/re/test_sound_scan.py`: 300 random cases, identical Z80 commands).
  - The object/player pass (`$69A2`) mapped object types through a 14-compare chain; it is now a table (`src_patch/inplace/obj_type.s`, checked by `tools/re/test_inplace.py`: identical RAM and VDP writes over whole updates).
  - Firebrand's shot fix-up only scans the sprite table while shots are out.
  - The other per-slot type chains are tables too: the 40-slot passes at `$114704` (stages 2-6, `inplace/obj_sum.s`) and `$768A` (stage 1, `slot_dispatch`), and the handler pick at `$6A88` (`obj_dispatch`). Each target is entered with the same registers as before.
  - The stage-1 tombstone check (`$10442A`, run three times an update in co-op over 12 tombstones) hoists its loop-invariant tests and skips tombstones outside the player's X window with one compare (`tomb_check`; `tools/re/test_tomb.py`: 22,500 random placements, identical RAM and registers).
  - Co-op: Maximo's context swap is generated straight-line movem code over the ranges his update actually touches (`mkswap.py`, ranges traced by `tools/re/ctx_trace.py`), and his control block is one assembly sequence (`p2_control`) instead of one C call per routine.
  - The sprite buffer clear before every sprite build (128 single `clr.l`) is a movem clear (`clear_sat`).
  - **Render skip** (`src_patch/pace.c`, `hook_sat_dma`, `render_gate*`): the game logic runs every update; in busy stretches the sprite layer is drawn less often, like a frame skip.
    - At the start of each update (`$6938`), `pace_start` reads where in VBlank the update starts. From NTSC line 229, or when a whole frame was lost, it skips this update's sprite build (15-20% of an update in every stage).
    - From line 241 the uploads would run into the active display (DMA ~10x slower, CPU halted), so that frame uploads nothing for the sprites (sprite table, Arthur's and Maximo's frames). The screen keeps the previous sprites; a held Arthur frame goes up with the next upload.
    - At most 3 frames in a row are held (`FS_MAX` in pace.c), so sprites are drawn at least every fourth frame. The background keeps scrolling on held frames, so sprites can lag it by a pixel or two for those frames. PAL (longer VBlank) only skips after a lost frame.
    - Everything the builds write is render state (sprite buffer and counts, enemy/shot art requests, piece counts). `tools/re/test_ab.py` with a forced skip on every other update (`-pb <fs_force>=1`) gives identical game RAM over 150 updates from co-op snapshots of all six stages.
  - Every change is checked against the previous build by `tools/re/test_ab.py`: whole updates from co-op RAM snapshots of all six stages with random input on both pads give identical RAM and VDP writes (for the render skip: with skipping off; and with it forced, identical game RAM).
  - In-play rates now (mean of 3 input seeds, deaths excluded, NTSC):

    | Stage | 1 | 2 | 3 | 4 | 5 | 6 |
    |---|---|---|---|---|---|---|
    | 1P | 1.00 | 0.98 | 0.99 | 1.00 | 0.99 | 1.00 |
    | Co-op (before this work) | 0.54 | 0.60 | 0.62 | 0.81 | 0.61 | 0.80 |
    | Co-op | 0.93 | 0.86 | 0.97 | 0.98 | 0.89 | 0.98 |
    | Firebrand | 0.99 | 0.97 | 0.99 | 1.00 | 0.98 | 0.98 |

    PAL co-op (same method): 1.00, 0.99, 1.00, 1.00, 0.95, 1.00. Single seeds vary by about ±0.05.
  - Still slow: co-op in stages 2 and 5. Even with the build skipped, some updates there take more than a frame of game logic (the object passes, Maximo's duplicated player routines and context swap). In those moments sprites drop to 15 fps (every fourth frame); a 2-frame limit gave 0.84/0.86 there.
- Menu text uses the arcade font (ASCII `$20–$7F` from `rom/gg1.bin`).

## Engine hooks

| Address | Original | Hook |
|---|---|---|
| `$28E` | `lea $FF0000,a0` + RAM clear loop | `hook_ramclear`: clears RAM except `$FF5000–$FF50FF`, reads the VDP control port first |
| `$B7A` | title prologue (`movem` + `jsr $BF58`) | `hook_title` → `boot_flow` (intros, menus), then the title, or a Home start |
| `$BB8` | `lea $2045E8,a0` (title palette) | `hook_title_pal`: Japanese logo on the title screen |
| `$BF72` | pad routine | `hook_pad` → `pad_update`: same RAM outputs, per-mode mapping, pause |
| `$113A28`, `$11CFF0` | `jmp $200` soft restarts | `warm_restart`: marks the restart as warm so it isn't treated as a power-on |
| `$11CE80/86`, `$11CF0C/2C` | overlay `lea` sources | `ovl_*`: English or Japanese attract overlay |
| `$61A2` | `clr.l $FFC570` (player block init) | `hook_player_init`: lives, difficulty rank and its floor, debug stage |
| `$6348` | `move.b #3,$FFC500` (continue) | `hook_continue_lives` |
| `$7890` | `clr.l $FFC040` (score block init) | `hook_score_init`: TOP SCORE from the saved table, bonus thresholds |
| `$779A` | `move.l (a4),d1; cmp.l 4(a4),d1` (after the score add) | `hook_score_added`: bonus life (the port had none) |
| `$62FA` | `tst.w $FFC594` (continue countdown) | `hook_continue_tick`: continue DIP, Home continues, free play |
| `$639C` | game over → `jmp $200` | `hook_game_over`: initials entry, then the soft restart |
| `$89E4` | sound play `jmp $11C73E` | `hook_sound_play`: demo-sound DIP |
| `$644` + 9 more stage loops | sprite-table DMA `jsr $704BE` | `hook_sat_dma`: links Maximo's sprite after Arthur's, DMAs his frame to tiles `$690–$69F`, hides dead players |
| `$61DC` | `tst.w $FFC570` (start of death handling) | `hook_p1_death`: co-op respawn instead of a stage restart |
| `$690E` | Arthur's frame upload `jsr $704BE` | `hook_arthur_dma`: skipped in Firebrand mode (his frame goes up at the sprite DMA) |
| `$11711E` | shot-slot art upload `jsr $704BE` | `hook_shot_dma`: fireball instead of the lance in Firebrand mode |
| `$116472`, `$116884` | item code copying armor/weapon back from its context | `hook_item_copy`: Firebrand turns pickups into points |

Engine variables used: `$FFC000` score (BCD), `$FFC004` TOP SCORE, `$FFC500` lives,
`$FFC501` difficulty rank, `$FFC561` rank floor, `$FFC512` stage (0/1 = stage 1 … 6),
`$FFC570` play state (2 = continue countdown), `$FF7FE8` credits. A debug launch to a later
stage uses the game's own stage advance (`$FFC512 = n`, `jmp $113B70`) on the first frame of play.
Entering a stage's code directly from the start path crashes, because it expects that loader.

## Memory

- `$FF5000–$FF50FF`: `Persist` (`common.h`), which survives the game's soft restarts. Validated by the magic `MXMP`.
- `$FF5100–$FF5EFF`: C `.bss` (no `.data`; everything is cleared at boot).
- `$FF5F00`: the SRAM transfer routine, copied there at run time.
- `$FF2BE1–$FF6FFF` is never touched by the game. Checked over 24,000 frames of boot, attract and stage 1 play plus 6,000 frames of play in each of stages 2–6 (via the developer launch), and no instruction addresses it directly.

## SRAM

The header declares 8 KiB at `$200001–$203FFF` (odd bytes). Because the ROM is larger than
2 MiB, SRAM is switched in with `$A130F1 = 1` only for the length of a transfer. `sram_xfer`
copies itself to work RAM and runs there with interrupts off, so no code ever executes from
the switched window. The save format (`sram.c`) is magic `GNGS`, a version, the options and a checksum.
