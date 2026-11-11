MEGA GHOSTS'N GOBLINS  -  V0.8.4 ALPHA
rester159, 2026
==================================

A reworked version of the Ghosts 'n Goblins Mega Drive / Genesis port: fixed to
run on real hardware and accurate emulators, faster, with 2-player co-op as
Maximo and two campaigns as Firebrand, the Red Arremer. Formerly Ghosts'n
Goblins MD.

File: MegaGhosts'nGoblins_Alpha_0.8.4.bin  (4 MiB, regions J/U/E, NTSC and PAL)
SHA-1: c161ae325d2a89ca9c338b8312aff6745e50efd7


NEW IN V0.8.4
-------------
- Firebrand takes two hits: the first knocks him back and takes his
  flight, the second kills. A wing heals him and gives his flight back.
- New Firebrand art by Robot-Random and GoodLuckTrying: he climbs ladders
  seen from behind, and his wall cling is redrawn.
- The community credits have a title in the Ghosts'n Goblins lettering.


NEW AND FIXED IN V0.8.3
-----------------------
- The map theme at the start of each stage was about three times louder
  than the stage music. It now plays at the stage music's level, and 15
  other tunes were evened out to that level too.
- New Home option, WEAPON: KEEP AFTER DEATH (the default, as in the arcade
  and the sequel) keeps the weapon you were holding when you lose a life;
  LANCE AFTER DEATH gives you the lance again, as before.
- Arcade mode now keeps the weapon after a death, as the arcade does.


FIXED IN V0.8.2
---------------
- The second loop could not be finished: Arthur stood in Astaroth's room
  with no Astaroth and only the music. Firebrand's Quest Plus had the same
  problem.
- Astaroth faces Arthur, and throws the arcade's bolts.
- The room opens as in the arcade: "RESOLVE YOUR BATTLE !", Arthur walking
  in, and the princess beside Astaroth, who then waits at the right.
- Stage 6's skulls are all there after a real stage 5 clear (3 instead of 5
  at the start).
- The plants' eyeballs are drawn in the second loop.
- A blue raven stays blue when it follows you out of stage 2's building.


CHANGED IN V0.8.1
-----------------
- Home's parallax no longer reads the video chip while the game runs: a
  try at a reported freeze early in stage 1 on a Model 1 console. Reports
  from real hardware are very welcome.


NEW IN V0.8
-----------
- New name and logo: Home is Mega Ghosts'n Goblins. Arcade mode stays the
  original, and the Japanese Makaimura title is still in the options.
- FIREBRAND'S VENDETTA: a new campaign that runs the game backwards, from
  Satan's throne room to the graveyard.
- Firebrand flies: jump, then press jump again in the air to fly until the
  FLY gauge runs out. Red wing pickups raise his flight level.
- Parallax backgrounds in Home mode.
- Maximo's sprites redrawn (thanks to the community artists).


FIXED IN V0.7.1
---------------
- The tombstones (and every other sprite) no longer shiver against the
  background while the screen scrolls.
- Home mode's EASY is now really easier: the difficulty rank stays at its
  lowest all game. NORMAL, DIFFICULT and VERY DIFFICULT are as before, and
  Arcade mode keeps the board's four DIP settings as they are.
- Checked against the arcade and left as is: tombstones are solid about
  3 px wider than their stone on each side, as in the arcade.


FIXED IN V0.7
-------------
- Stage 5's Big Men are drawn from their own art (they showed as sprite
  garbage) and can be killed again: 10 hits, as in the arcade.
- Stage 2's buildings no longer flash light and dark.
- Stage 2's stepping stones over the water are the arcade's grey stone
  blocks (they looked like ice).


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
                      give points. Two hits: the first takes away his
                      flight, the second kills. A wing heals him and
                      gives his flight back; the next wing raises it.
                      In the air, push into a wall to cling to it; jump to
                      hop up it. Fire level with Astaroth to hurt him.
  FIREBRAND'S QUEST PLUS  appears once the quest is beaten: top difficulty
                      throughout, half the hover time.
  OPTIONS ........... lives, continues, bonus life, difficulty, weapon after
                      a death, English or Japanese (Makaimura) title,
                      sound test

ARCADE
  DIP SWITCHES ...... coinage (including free play), lives, bonus life,
                      difficulty, demo sound, continue

High scores (separate Arcade and Home top-10 tables) and all settings are
saved to SRAM. There's also a hidden developer menu.


KNOWN ISSUES
------------
- Co-op can still slow down a little when the screen is busy (stage 2
  most), as both players' routines run every frame.
- Maximo's and Firebrand's art is temporary.
- The high-score table is drawn over the live stage (same as the original).


Bug reports, slowdown spots and feedback: leave a comment on the itch.io page.
