# Ghosts 'n Goblins Genesis Plus

A reworked version of the Ghosts 'n Goblins Mega Drive / Genesis port: fixed to run on real hardware and accurate emulators, faster, with 2-player co-op as Maximo and a one-player campaign as Firebrand, the Red Arremer.

The port has no source code, so everything here is a patcher plus freestanding 68000 C/asm linked into the padding above the original image. **Source only:** no ROMs, no SEGA/CAPCOM boot intros, and none of the ROM-derived art are in this repository.

- [build/COMPATIBILITY.md](build/COMPATIBILITY.md): the hardware-compatibility fixes and how they were verified.
- [src_patch/README.md](src_patch/README.md): every feature, engine hook and speed-up, with measurements.
- [build/release/README.txt](build/release/README.txt): the player readme (controls, modes, known issues).
- [docs/ITCH_POST.md](docs/ITCH_POST.md): the release post.

## Build

Requirements: Python 3, `m68k-elf-gcc` and `m68k-elf-objcopy`, and your own copy of the port, `Ghosts'n Goblins (SMD) (PD).bin` (3,473,408 bytes, SHA-1 `bfa7c9613a5ea03127e14479359d2dbeca1540b2`). The menu font and the Japanese title logo are read from the arcade ROM set at build time (`rom/gg1.bin`).

Compatibility-only ROM (no menus, no SRAM):

```bash
python3 tools/patch_gng.py "Ghosts'n Goblins (SMD) (PD).bin" build/GhostsNGoblins_fixed.bin
```

Features ROM (menus, SRAM saves, co-op, Firebrand, speed-ups):

```bash
make -C src_patch
python3 tools/patch_gng.py "Ghosts'n Goblins (SMD) (PD).bin" build/GhostsNGoblins_plus.bin --features src_patch/build
```

The features build also needs the Maximo and Firebrand sprite banks in `art/maximo/` and `art/firebrand/` (`maximo_bank*.bin`, `firebrand_*.bin`). They're derived from the game's own frames and from Demon's Crest, so they aren't included. The scripts that made them are in `art/*/src/`. They read local captures that aren't in the repository, so as written they won't run from a fresh clone.

### Optional boot intros

On a cold boot the release ROM plays the SEGA logo with the "SE-GA" chant, then the CAPCOM logo with its jingle (`src_patch/intro.c`). The logos, chant and jingle are Sega's and Capcom's, so they stay out of the repository. `src_patch/mkintro.py` reads them at build time from three local intro kits, set with `SEGA_KIT`, `CHANT_KIT` and `CAPCOM_KIT`. Without the kits, the build skips the intros and boots straight to the game.

## Testing

Everything was tested headlessly through libretro cores (Genesis Plus GX, PicoDrive): `tools/headless/lr.py` runs a ROM with scripted input and dumps RAM, PNGs, save states and audio, and `tools/re/` holds the equivalence and profiling scripts. Nothing has been tested on a real console yet.

## Pixel editors

`tools/maximo_editor/` and `tools/firebrand_editor/` are browser editors for redrawing Maximo's and Firebrand's frames inside the game's palette. Their frame data (`*_data.js`) comes from the ROMs and isn't included. `tools/firebrand_editor/make_data.py` rebuilds Firebrand's from your own ROM.
