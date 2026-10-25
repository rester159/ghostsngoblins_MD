# Ghosts'n Goblins (Genesis port) — compatibility build

| | Input | Output |
|---|---|---|
| File | `Ghosts'n Goblins (SMD) (PD).bin` | `build/GhostsNGoblins_fixed.bin` |
| Size | 0x350000 (3.3 MiB) | 0x400000 (4 MiB, linear, no mapper, no SRAM) |
| Header checksum | EE66 | 8F3C (verified) |
| SHA-1 | bfa7c9613a5ea03127e14479359d2dbeca1540b2 | b2ec75ef4f1ab9ce1eec38eb423d9c112f78ade3 |

Rebuild: `python3 tools/patch_gng.py "<input.bin>" build/GhostsNGoblins_fixed.bin`

**Features build:** `build/GhostsNGoblins_plus.bin` (SHA-1 `cef3ca0ced89d29f2b24c07986ae188d32df006d`,
checksum see header) contains all of the fixes below, plus the SEGA/CAPCOM boot intros, the menus and QoL code from `src_patch/` (see
`src_patch/README.md`). It declares 8 KiB of battery SRAM at `$200001`, switched in through
`$A130F1`, so on hardware it needs a cartridge or flashcart that supports SRAM on a 4 MiB ROM.
Rebuild it with `make -C src_patch` and `--features src_patch/build`.

**Maximo side build:** `build/GhostsNGoblins_maximo.bin` (SHA-1 `ad435ce06934e035269fe819d672763b422d7de2`) is the
compatibility build with Arthur's frames swapped for Maximo's (`--maximo art/maximo`), no menus or SRAM.

## Changes

1. **VDP data-port read-modify-write (the "Fusion/Gens only" bug).** 16 `clr.w`/`clr.l $C00000`
   (0x0DEA, 0x0E00, 0x113C26–0x113D4C, 0x119F7E/84, 0x11D1FC–0x11D25A). The 68000 `clr` reads the
   destination before writing it. Reading the VDP data port while it is in a write mode is invalid on
   real hardware and in accuracy-focused emulators. Each site now calls a write-only stub at 0x3F0000.
   1,104 of these reads ran during boot alone.
2. **Boot VDP latch.** Reads the VDP control port before VDP init, so a soft reset (console reset button,
   EverDrive in-game reset, or the game's own `jmp $200` after the attract demo) that interrupted a
   two-word command can't corrupt the register setup. Defensive hardening.
3. **Z80 reset/bus handshake.** In sound init, the code now waits for BUSACK again after releasing
   Z80 reset, before writing Z80 RAM. Defensive hardening, following SGDK practice.
4. **Garbled attract-demo logo.** When the attract demo is on screen, the overlay code shows the logo
   for 570 of every 690 frames and caches which overlay's tiles are loaded (`$FF86A0` kind,
   `$FF86A2` segment). When the demo player dies, the game restarts through `jmp $2CC` (at `$113A06`
   and `$113E1E`), which re-runs VRAM init and overwrites the logo tiles (`$2B8–$2CA`). RAM is kept,
   so the stale cache skipped the re-upload and the logo drew with the wrong tiles until the ranking
   overlay took over. Both jumps now invalidate the cache first, as the existing `$638C` path does.
   Verified with an automated check: the logo map was on screen in 367 samples across 8000 frames
   (NTSC and PAL). Tiles not matching ROM: 4 samples before the fix, 0 after.
5. **Death while blinking froze the game.** After a hit, Arthur blinks (`$FFC309`), and on blink frames the
   routine at `$5E4A` copied the queued animation straight into the shown one. A death that starts during
   the blink (time running out, a pit) queues the death sequence's terminator (`$0B`, which has no frame).
   The frame lookup then failed its range check and the game stopped in the `$B56` trap (logic halted,
   music and VBlank still running). The copy now skips animations without a frame. Reproduced headlessly
   by forcing the blink timer through a time-out death: halted at frame 8740 before the fix, and it
   continues after (one life lost, play resumes). The co-op respawn blink made this much more likely.
6. **Header.** 0x1B0–0x1EF were 0xFF. They are now spaces (explicitly no SRAM, modem or memo).
   Title is now `GHOSTS'N GOBLINS` instead of the dev string `GNG STAGE3 ENEMY BOSS M126`. ROM end
   is 0x3FFFFF and the checksum is recalculated.

The vector table was already valid: SSP=$FFFF00, reset=$200, VBlank=$113E56, HBlank=$8DF8,
exceptions=$0B56. TMSS, the Z80 bus protocol, the pad reader (TH delays) and the Z80 driver were also
audited and left unchanged. Correction to an earlier version of this note: the game *does* use DMA (sprite table, Arthur's frames, and tile uploads), always through one helper at `$704BE`. That helper rejects any transfer that would cross a 128 KiB source boundary, is longer than 4 KiB or is odd-aligned (it stops at an error code rather than corrupting VRAM), and it requires the Z80 bus to be held. The features build's extra DMA (Maximo's frames) goes through the same helper, and its source banks are placed inside a single 128 KiB block.

## Evidence (headless libretro harness, scripted coin/start/run/jump input)

| Configuration | Original | Fixed |
|---|---|---|
| Genesis Plus GX, NTSC-U, lock-up + address-error emulation on | boots, title, gameplay | same, frame-identical state |
| Genesis Plus GX, PAL | — | boots, title, gameplay |
| Genesis Plus GX, NTSC-J | — | boots, title, gameplay |
| Genesis Plus GX, 6-button pad | — | boots, title, gameplay |
| Genesis Plus GX, soft reset during gameplay | — | returns to boot, then title, then gameplay |
| PicoDrive, auto / Europe / Japan NTSC | boots, title, gameplay | same |

None of these emulators reproduces the VDP-read fault itself, so they prove only that the fix causes
no regression. BlastEm was not run. **Physical status: pending.** No Model 1/2/3 console or EverDrive
has run this build yet. Suggested checks: cold boot, about 5 minutes of play, the reset button during
gameplay, and attract-demo loops on a Model 1 (VA6 or older) plus a Model 2, from both an older
EverDrive and an X-series/Pro.

## Known issues not changed (same in the original)

- The high-score table is drawn over the live stage instead of a cleared screen.
