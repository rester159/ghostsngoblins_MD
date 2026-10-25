# Arcade accuracy log

The Genesis port keeps the arcade's coordinates, physics and many tables (it's a translation, not a remake),
but some systems were reimplemented. This log compares it against the arcade, finding by finding.

**Reference:** the arcade set in `rom/` is MAME `gng` (World, gg3 `9e01c65e`, gg4 `66606beb`, gg5 `d6397b2b`).
`tools/arcade/gng.py` runs it headless (MC6809 interpreter `cpu6809.py`, main board only, MAME `gng` memory
map). Disassembly: `unidasm -arch m6809` on a 64 KiB image with gg4 at `$4000` and gg3 at `$8000`.
Addresses below are main-CPU addresses; `$4000-$5FFF` is bank 4 (gg4) unless stated.

**Method:** run both games from the first frame Arthur moves with the same input and compare positions
frame by frame; where they part, find the routine in both and compare.

## RAM map (arcade)

| Address | Meaning |
|---|---|
| `$0500` | Arthur's block (X = `$0510` in his routines) |
| `$0506-$0508` | x, 16.8 (high, pixel, fraction) |
| `$0509-$050B` | y, 16.8 (ground is 62) |
| `$050F` | size class (index into the probe tables, 3 for Arthur) |
| `$0510-$0512` | animation script pointer and frame timer (`$9074`) |
| `$1010` | 30 platform/tombstone objects, 32 bytes: `-$F` live, `-$A..-$8` x, `-$7..-$5` y, `+5` type |

Port equivalents: `$FF9000` x (16.8 in a long), `$FF9004` y (word), `$FF9400` y 16.8, `$FF9404` vertical
speed, `$FF9408` on the ground, `$FF9410` jump phase (1 rising, 2 falling), `$FF9220`/`$FF922A` previous
x/y, `$FFE000` the 30 objects (48 bytes: x, y, +4 live, +10 type).

## Matching (verified)

- Walk speed `$0120` per frame (1.125 px).
- Jump: initial speed `$44000`, same per-frame speed steps, peak 39 px, ~37 px of travel.
- The first zombie of stage 1 hits Arthur at the same moment with the same input.

## Fixed

1. **Tombstones** (`glue.s` `tomb_check`; arcade `$9FAE`, walk `$940E`/`$9435`, fall `$9638`, table `$A052`).
   Arcade: box x ±12 / y ±19, top y + 19; blocks walking only; while falling, inside the box lands you on
   top. Port had: top +20, landing ±20 by crossing the top, side stop ±13 in all states (so no jump cleared one).
   Same runs now agree: side stop 244 (arcade 244.01), top y 81 (81), a jump from against it clears it.

2. **Input timing** (`pad.c` `arcade_input`, used for Arthur and Maximo). The arcade reads left/right as
   (this frame AND last frame) (`$93D0`, inputs `$4B`/`$4C` from `$6920`/`$6930`), and a jump press on the
   ground takes off two frames later: the press frame still walks, the next stands still (`$9218` latches,
   `$9542` sets up), the one after moves (`$95C8`), along the walk direction latched at the press (`$9567`
   reads `$050E`). The port reacted on the press frame and took the jump direction from that frame's stick.
   Now: running jump walk / stand / take-off with `$80` and `$440` steps on the same frames as the arcade;
   the five direction cases (standing Right+Jump, reversing on the jump frame, ...) give the arcade's
   result (three were wrong before). Up/down already used the two-frame rule in the port (`$7D4C`).

3. **Random source** (`glue.s` `rng_*`). The arcade's is its frame counter (`$20-21`, `INC` in the interrupt
   at `$65CA`, read as `<$21`: zombie underground waits `$D336` with table `$D347`, rise/walk timers
   `$D406`/`$D457`); it runs from power-on through title, attract, deaths and the map. The port's (`$FFA206`)
   stepped once an update, froze while Arthur was dead and was reset to `$96` at every stage and life start
   (`$91D4`, `$9952`, `$104EE6` copy `$14F60`), so each life replayed the same zombie pattern. Now it follows
   the VBlank count plus the boot-menu frames. With the counter matched, all 13 stage-1 enemy slots agree
   with the arcade for 1,460 updates (zombies, crows, slot 6).
4. **Item-drop cycle** (`item_save`/`item_init`). Every 6th spawn makes an item whose type comes from a
   7-step cycle, an accumulator and a 5-byte generator (arcade `$7D`, `$7E`, `$78-$7C`, `$EBA4-$EC33`;
   port `$FFC890` +7..+13). The arcade clears them only at power-on; the port reloaded them every start.
5. **Difficulty** (`settings.c`): the arcade's four DSW2 settings in its order, NORMAL/EASY/DIFFICULT/VERY
   DIFFICULT = starting rank `$06/$00/$18/$20` (`$629A`, table `$6228`). The plus build had `$06/$16/$26/$36`.
6. **Continue** (`continue_lives`, `cont_start`): the score goes back to 0 and the bonus thresholds restart
   (`$7882` -> `$6C33`); the countdown is 640 frames (BCD from 10, a step per 64 frames, `$785D`); in Arcade
   mode it takes Start with fire or jump (`$786C`), measured in the arcade. Home keeps Start alone.
7. **Bonus lives stop at 1,000,000** (`$ED95`: never once the score's top byte is set).
8. **Checkpoint** (`$103CBE`): the arcade only refills the timer (`$ED73`); the port also stopped the hurry
   tune and restarted the stage music.
9. **After the second loop's ending** (`loop_again` at `$113A1C`): the arcade plays on from stage 1 with score
   and lives (`$73F3`, `$7446`); the port went to the title. Read in code; the ending wasn't reached in a run.

10. **Zombies coming out of the ground were drawn 8 px low** (`zombie_y` at `$7CF8`). The port draws each
    enemy frame as one 32x32 image placed at y = 352 + camera - object y, with no per-frame offset; the
    arcade's frames carry their own. During the rise the zombie's y is 54 (8 below the ground) in both, and
    the arcade draws the mound and head-and-shoulders frames 8 higher, bottom row on the ground line; the
    port's images for those frames (13-17) sat in the grass. Drawn rows compared frame by frame over the
    whole rise (arcade: sprite pieces owned by the slot, `X` at the builder `$F89E`-`$F91D`; port: the
    frame drawn with and without its sprite-table entry): 189-193, 186-193, 185-193, 182-193, 178-193,
    then 178-201 and 171-201, now identical. Other enemies may have the same converted-image offset errors;
    see Open.

11. **Stage-start wait** (`stage_hold` at the ten stage-loop entries, `$5A8` etc.). The arcade draws the stage
    over the map for ~37 frames with the game held (`$726E` calling `$80A0`) before play; Genesis draws it at
    once. From the end of the map to Arthur's first step: arcade 41 frames, port 15, now 41 (the hold keeps
    the music and the frame counter running). Death to first step: arcade 524, port now 527 (was 494). The
    death animation (60), death sequence (121) and map (302) already matched phase for phase.

12. **Random counter in every stage loop:** the seven other stage loops (`$99EC`, `$104F7E`, `$1054E2`,
    `$10F2D4`, `$11026A`, `$111226`, `$111AF2`) step it through `rng_tick` too (only stage 1's did).
13. **Moving platforms stand still a frame at each segment change** (`mover_load`, `mover_load2`). The
    arcade's mover (`$E482`) returns after loading the next entry; the port's four movers (`$106B0E`,
    `$10F560`, `$11A390`, `$11A5AE`) loaded and moved in the same frame, so platforms drifted out of phase
    (~25 frames in 1,200). Now the load frame holds still, as in the arcade.
14. **Stage start times:** every stage loop entry sets the time from the stage's table (`$103D10`); the
    stage inits copy a HUD block with the timer at `$74` and only stage 1's then set it, so stages 3, 4 and 6
    started at 1:56 instead of 2:30, 2:30 and 3:00 (index 2, 3, 5). All seven indexes now start at the
    table's value (120/90/150/150/180/180/120, checkpoint table after the checkpoint).
15. **Tombstone rules in every stage:** the stage 3 rocks (type 1) kept the port's old box; the arcade's
    check has no stage test. Now a jump from against a rock clears it, as in the arcade.
16. **Boss hit points:** Astaroth 10 (port 6), the Satans 10 (port 4), the dragon's head 6
    (port 10; now set by `dragon.c`, item 18), from the arcade's inits (`$DB1B`, `$BEF1`, `$D596`).
17. **Stage numbers:** the stage index `$FFC512` is the arcade's `$72` (0-5 = stages 1-6, 6 = the final
    room). The developer menu's STAGE n launched index n (so stage 2 was unreachable) and high scores
    recorded the index; both now use index + 1.

18. **The dragon** (stages 3, 4, 6; `dragon.c`, hooks `$106F80`, `$106F10`, `$105798`, `$107510`, `$107540`, table
    `$2AC94`). The port's type-12 handler homed on Arthur, its re-aim timer byte `+$23` overlapped a counter word at `+$22`
    (`$107318`/`$107346` add 1 to the word, `$10718A` subtracts 1 from the byte) so it never re-aimed and flew off, and
    the body replayed the head's position history at 1.13 px/frame. Now the arcade's (`$D518`, `$D6D6`-`$DAD8`):
    - nine nodes, one slot each (head in the spawner's slot, segments in the next eight free ones, as the arcade's
      allocation: slots 20, 19..12 in stage 3); segments at +20, +14 each, tail +12 (`$D5A9`); each moves 2 px/frame
      in 16 directions (`$A427`, `$51B6`); a direction reaches segment 1 after 10 frames, the next after 7, the tail
      after 6 (`$D955`); one pending direction per node, a newer one replaces it;
    - the head: uncoiling script `$D789` (six (10, dir) pairs, the head moving only on the step frames), then all nine
      frozen until on screen, Arthur within 32 px below (`$D7C0`) and 2-5 ticks of 16 frames (`$D7B1`/`$D7B5` by
      `($21 + slot counter) & 3`); main loop `$D7EE`: mouth and roar every 128 frames (`$5186`, sound `$21`), steering
      `$D818` at each step's end (random & 15 <= the rank threshold `$D5A5[rank >> 4]` and Arthur 24 px ahead: aim
      `$8FE4` (8-bit divide `$FED8`, low bytes only), 18 or 40 frames; past Arthur: turn round at `$5A` + 256 (the
      stage table `$1043E6`) or 94 px past him into `$52C2`/`$52E0` by height; else up/down 36-frame steps `$D943`/`$D947`
      or on with the script; stage 6 by the start height `$19`, `$D90A`), fire `$D981`;
    - fire: |dy| <= 72, `($21 + 1) & 31 == 0`, random & 3 == 0, a free projectile slot; 10-frame mouth, a type-9
      fireball at (x ± 10, y - 5) flying straight along the head's side at 3.125 px/frame (`$FCA8`/`$FEBE`, speed
      `$5E07`); the port's aimed at Arthur at 2.26 px/frame;
    - hits (`$EF4A`, `$DA15`): every node is a target (the port tested the head only, `$105798`); box ±12 x ±10 (`$F0A0`;
      port ±16 x ±16); score index 4 = 200 (`$F0E4`; port 9 = 1,000); weapon 2 passes through (`$F0EB` is per weapon:
      0 for weapon 2; the port stopped it on the dragon only); a hit segment survives and the tail is lost instead;
      6 hits on the head kill it and all segments (`$DA54`); head: sound `$0F`, 3 + 18 frames burning, "1000" for 63
      frames, then `$0C09` (1,000 points) and the removal that starts the stage end (`$DAB7` → `$E844`; port boss count
      `$10EA0C`, nothing in stage 6); segments: sound `$1B`, 36 frames burning, "200" for 63;
    - lost when more than 384 px off screen (`$D6DE`), except in stage 3;
    - spawn: stages 3/4 at camera + (`$180`, `$40`) of the spawn frame, set up the next frame; stage 6 at the absolute
      (7824, 2016) (`$EB4B`, absolute branch `$EB5B`); the port used the camera offsets in stage 6 too (7808, 1600 at the stage start).
    Lockstep with the arcade (Arthur's position, `$FFA206`/`<$21` and the shift register `$6E/$6F` copied from the
    arcade every frame, the stage 3 Red Arremers parked off screen, the emulated 68000 overclocked so the port never
    lags): stage 3, 3,000 frames of shooting it down segment by segment: every node's x/y (16.8), direction, state and
    HP, the fireballs and the score identical, the stage-end flag on the same frame (1604), 2,800 points both; stage 4,
    4,000 frames: the same (stage end frame 1572); stage 6, 4,000 frames of it waking in the tower and flying round
    Arthur, and a forced head kill: identical, +1,000, no stage end. Left different: the head's position on its spawn
    frame (set up a frame later in both), fireballs leaving the screen a frame apart (the arcade's fireball fraction is
    leftover RAM), and the burn-up flames (not in the type-12 sprite set; nothing is drawn for those frames). The old
    build over the same stage 3 run: 2,785 of 3,000 frames different, no points, no stage end.

## Matching (audited)

- **Weapons** (all five): speed tables (`$9E0D`/port `$293D9C`), ranges (`$9DEB`/`$293DC4`), throw spawn
  offsets, shots on screen 2/3/2/3/3, throw timer 15 with re-throw at <= 5, cancel by a new direction, shots vs
  tombstones (`$F6A2`/`$104546`: |dx| <= 14, dy -8..+4, 15 hits spawn the tombstone's object).
- **Game rules:** stage timer values (`$6EAD`/`$6EBB` = port `$103E28`/`$103E36`), 64-frame tick, hurry at
  15 s, time-out death; restart points per stage and checkpoint (`$6CED`/`$6D09` = `$1040CC`); the score
  table (`$5457` bank 3 = `$28F32`); stage end (key, 1,000 points, waits, rank +4 capped `$3F`); rank -1 per
  death to the starting floor; final-stage weapon gate; DIP lives and bonus tables.
- **Stage 1 enemies:** zombie spawn, rise (~91 frames), walk 0.8125 px, direction choice, sinking, despawn;
  crow wake-up and flights; the item tables (except mask-table bytes past index 4, unused in stage 1).
- **Arthur:** knockback arc (identical frame by frame), 120-frame invincibility (`$00AD`/`$FFC309`), death in
  boxers, ladders (grab zone, 1.375 px/frame, top/bottom sequences), ledge falls, throw lock 14 frames,
  crouch entry, landing keeps the y fraction in both.

## Open

- **Sprite placement of every other enemy, item, weapon and boss frame** (the converted 32x32 images can
  carry the wrong offset, as the zombie's rise did). A per-frame comparison of drawn pixels against the
  arcade, as for the zombie. Also a 1 px x difference on the zombie's rise frames relative to its walk
  (port +1) that needs an absolute reference.

- **AI rewritten in the port (to port from the arcade):** the Satans (`$1105C6`: choices from the rank byte `$FFA208` instead of a random),
  Astaroth (`$DAD9`: walk/pause, rapid-fire mode, high shots; shot motion), the Petite Devils (rise from
  the lava, hover, dive: `$A89C`/`$A8F9`/`$AB4B`), the stage 5 skulls (sleep/wake/hop, `$CC70`/`$CD08`; the
  port fires them as aimed projectiles). The arcade has a second random source, a shift register at
  `$68F9` (`$6E`/`$6F`), used from 34 places in enemy code; the port had no equivalent (`dragon.c` has
  one now, stepped by the dragon only).
- **Spawn and activation rules:** stage 2 window devils are never rejected off-screen (arcade `$B25E`,
  on-screen test `$B193`); stage 2 crows start 56-64 frames before they're visible (port `$450A` uses
  512 px; arcade `$A72F` waits until on screen, then perches on random timers); stage 2 tower devils
  (16 spawns, 218-frame life vs the arcade's 9 and 579); the stage 3 dragon fight has one Red Arremer
  instead of two.
- **Ending:** the port walks Arthur 240 frames before the text and has no princess scene (arcade: text 1
  frame after Astaroth dies; 131-frame princess scene on the second clear); +1,000 points at the room's
  end that the arcade doesn't give; "Return to starting point" drawn over the room instead of on black.
- **Smaller:** stage 4 fire pillars one frame early; a stage 5 flying knight drifts after ~600 frames; Astaroth's shot parks on a blinking Arthur; the stage 2
  stone-block edge and elevator walk-step quirks; Big Men 1 px; stage 2 water death y.
- **Rank over time:** the arcade adds `$6B` to its rank word `$9A` every 256 frames (`$EEB9`, capped at `$3F`):
  6 -> 10 over the 3,000 frames of the stage 3 dragon run; the port's `$FFC501` stayed at 6. The dragon reads it once,
  at its start (aim threshold `$D5A5[rank >> 4]`), so it only matters there after long stages; other enemies may
  read it more.
- **Seen while checking the dragon (not traced further):** the port's object pass sees the camera from before the
  frame's scroll (the arcade's after it), so camera-relative spawns land a scroll step behind (handled for the
  dragon); the port's lance starts at Arthur's x with its fraction (the arcade drops it); lances live on further
  past the screen edge in the port; a kill's score is added a frame later in the port.
- **Bonus lives:** the plus build caps lives at 9 (the arcade doesn't).
- **Continue digit:** the port shows one digit, so the arcade's "10" step shows as 9.

- **Stage start:** the arcade spends a frame landing (y 64.28 -> 62.03) without moving; the port lands and
  moves in one frame. Start x fraction `$60F5` (arcade) vs `$609C` (port); start y 64.28 vs 64.00.
- **Intro:** the arcade's opening shows Arthur and the princess in the graveyard (stage background) for
  ~200 frames before the black-background kidnapping scene; the port's intro starts at the kidnapping.
  Start to play is 557 frames in the arcade, ~335 in the port.
- **Standing up** after a crouch: the arcade's stand-up frame doesn't walk (counter back to 7, no move); the
  port walks on it (`$7F98` then its walk in the same update). One frame.
- **Ladder bottom:** the arcade spends one frame at y 64.90 before 62.65; the port drops straight to 62.
- **Armor flag** (`$0158` arcade, set on the hit frame) vs the port's `$FFC328` (set on landing, +33 frames).
- **Weapons vs enemy projectiles:** the arcade cancels enemy shots with weapons (`$F3CE`, tables `$F452`,
  `$F498`; the shield/cross cancels types 0-9, others only type 5). Not found in the port yet.
- **Dropped fire presses:** about every 23 updates the port advances its update counter without moving the
  weapons; a one-frame fire press there is lost (frame pacing, not weapon logic).
- **Enemies:** with the same input the port's Arthur is hit again ~130 frames after the first tombstone
  while the arcade's isn't hit for another ~340. Not yet traced (enemy tables to be mapped).
