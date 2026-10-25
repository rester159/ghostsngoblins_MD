GHOSTS 'N GOBLINS GENESIS PLUS
rester159, 2026
==============================

A reworked version of the Ghosts 'n Goblins Mega Drive / Genesis port: fixed to
run on real hardware and accurate emulators, faster, with 2-player co-op as
Maximo and a campaign as Firebrand, the Red Arremer.

File: Ghosts'nGoblinsMD_Alpha_0.5.bin  (4 MiB, regions J/U/E, NTSC and PAL)
SHA-1: 9e853ce5a0b13adbed2c651d919c23c01594258e


WHERE IT RUNS
-------------
- Emulators: tested in Genesis Plus GX and PicoDrive. Any emulator with
  battery-save (SRAM) support should work.
- Flashcarts / real hardware: the ROM uses 8 KiB of battery SRAM on a 4 MiB
  cartridge, so your cart has to support SRAM at that size. Most EverDrive
  models do. Not yet tested on a real console: reports are very welcome.


CONTROLS
--------
At power-on the SEGA and CAPCOM intros play (Start skips them), then pick
ARCADE or HOME.

HOME
  B ............ throw
  A or C ....... jump
  Start ........ pause / resume during play

ARCADE (plays like the cabinet)
  C ............ insert coin
  Start ........ start
  B ............ throw
  A ............ jump

2 PLAYERS (Home menu): player 2 plays Maximo on controller 2.


MODES
-----
HOME
  1 PLAYER .......... straight into the game
  2 PLAYERS ......... co-op with Maximo. Each player has their own lives; a
                      fallen player respawns next to their partner. Jump on
                      your partner's head to bounce off it. Shared score.
  FIREBRAND'S QUEST . play as the Red Arremer. Hold jump at the top of a jump
                      to hover for up to 2 seconds. Fireballs only; pickups
                      give points. No armor: one hit and you're dead.
  OPTIONS ........... lives, continues, bonus life, difficulty, English or
                      Japanese (Makaimura) title, sound test

ARCADE
  DIP SWITCHES ...... coinage (including free play), lives, bonus life,
                      difficulty, demo sound, continue

High scores (separate Arcade and Home top-10 tables) and all settings are
saved to SRAM. There's also a hidden developer menu.


KNOWN ISSUES
------------
- Co-op in stages 2 and 5 can still slow down when the screen is busy. In
  those moments sprites may update only every fourth frame.
- Maximo's and Firebrand's art is temporary.
- The high-score table is drawn over the live stage (same as the original).


Bug reports, slowdown spots and feedback: leave a comment on the itch.io page.
