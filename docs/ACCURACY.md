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
16. **Boss hit points:** Astaroth 10 (port 6), the Satans 10 (port 4), the stage 6 dragon's head 6
    (port 10), from the arcade's inits (`$DB1B`, `$BEF1`, `$D596`).
17. **Stage numbers:** the stage index `$FFC512` is the arcade's `$72` (0-5 = stages 1-6, 6 = the final
    room). The developer menu's STAGE n launched index n (so stage 2 was unreachable) and high scores
    recorded the index; both now use index + 1.
18. **Weapons against enemy shots** (`shots.c`, `shot_check` at `$5930`): the port had no such check. The
    arcade's `$F3CE` runs on odd frames before Arthur's shot check: per weapon and shot type a count
    (`$F452`: the cross takes out both itself and shot types 1-9 and 11; the other weapons are used up on
    type 5 and pass everything else) and a box per shot type (`$F498`). Copied with its tables; measured:
    the cross and a man-eater plant's spit both go on the first odd frame, as in the arcade; the lance
    passes through it in both.
19. **Man-eater plant hit box** (`$6BB8`, record 2 at `$2AC94`): the port moved every weapon 18 px along its
    flight and the plant 5 px down before testing (`$6C0E`), with a y range of 37; a lance from the left
    killed it 18 px early and missed its far side. Now the arcade's +-12 x / +-16 y (`$EF62`, `$F040`):
    a grid of weapon positions around the plant gives the same kills in both.
20. **Starting score:** a new game started with 600 points (the start block at `$28EEE`); the arcade's
    starts at 0.
21. **Sprite placement** (audit of every frame drawn in all stages against the arcade, pixel masks relative
    to the object's position, ~30,000 matched frames). The arcade places each frame by the object's shape
    code (+$0F; anchors `$F864`: 0 = one 16x16 piece at (-8,-8), 2 = two at (-16,-8), 3 = 2x2 at
    (-16,-16)); the port's 32x32 images assume shape 3. Fixed: Arthur's weapons (all five, flight and
    burst frames) were drawn 8 px low (builder `$115994` used y = 360 + camera - y; every other builder
    352); the zombie's other shape-0/2 frames (0-4, 8-12, 21-25: the second rise set and the sinking
    sets) were 8 px low like the rise frames 13-17 were (`zombie_y`); the final-room flames (type 10,
    builder `$AF4A`, frames 1-30 of `$123B3E`/`$125620`) had their 16 px halves swapped (read from the
    data and the arcade's art; the arcade wasn't recorded in that room). After the fix both builders
    pair at offset 0 in a re-run. Everything else matched (the zombie's 1 px rise/walk step is the
    arcade's own). Firebrand's fireball goes through the weapon builder, so it is also 8 px higher.
22. **Walking off a tombstone:** the arcade sets the fall speed to the jump's 4.25 on every landing (`$51B`),
    so stepping off a tombstone drops at once (-4.25, -4.49, ... ; down in 5 frames from the top). The
    port's tombstone landing (`tomb_check`) stored one gravity step instead, so he eased off (14 frames).
    Now 4.25 as the port's own ground landing; frame for frame the same as the arcade.
23. **Crouching** (`arthur.s` `stand_up`, `crouch_in`, `walk_gate`; walk gate `$8114`). The arcade's crouch
    handler (`$91B4`) never walks: on the frame the stand-up countdown runs out (`$0520` 9..0, then back to 7
    and the crouch flag `$050F` cleared at `$9A6C`) Arthur doesn't move, and he walks from the next one; the
    port cleared its crouch flag (`$7F98`) and walked in the same update. The other way round, the arcade's
    standing handler sets the crouch flag (`$9305`) and still walks that frame (`$940E`), so Down+Right from
    standing steps 1.125 px as he crouches; the port's gate saw the new flag and didn't. Measured (crouch 20
    frames, then Right): first step on frame 180 in the arcade, 179 in the port, now 180 (Down alone, then
    Right: 185 / 184, now 185); Down+Right together: a step on the crouch frame in both now. Maximo's control
    block ignored the walk gate's answer altogether, so he slid along while crouched; it uses it now.
24. **Ladder bottom** (`lad_exit`, `ground_snap`; `$7E42`, `$8698`). Climbing down, the arcade's ladder ends
    with Arthur at y 64.90; the standing state's floor check (`$8CA7`) finds no floor at his y, so he goes to
    the fall state (`$91E1`) with y unchanged, and the next frame falls 4.25 and lands at 62.65 (`$9660`,
    `$91F1`). The port's ground step snapped him down to the floor within 8 px (`$8744`) in the same update.
    Now the ladder-bottom update checks only the floor at his own y (`$8784`): 66.39, 65.01, 65.01, 62.76 against
    the arcade's 66.27, 64.90, 64.90, 62.65 (the 0.11 is the start fraction).
25. **Stage start** (the same check on a stage's first ground step, set by `stage_hold_entry`). Both games place
    Arthur 2 px above the ground (y 64.28 / 64.21). The arcade then walks a frame at that height, lands at 62.03
    the next without walking, and walks on; the port walked and snapped to 62.21 in one update. Now walk at
    64.21, land at 62.96 without walking, walk: the arcade's sequence, frame for frame.
26. **Armor flag** (`kb_hit`, `kb_dispatch`, `kb_anim`, `kb_land`; `$5FA4`, `$5AAE`, `$5ADC`, `$5B44`, `$5CD4`).
    The arcade's `$0158` is set on the hit frame (with the 120-frame invincibility); the port's `$FFC328`
    (+40 of the physics block `$FFC300`) at the knockback's landing, 33 updates later, because its knockback
    state machine read it as "an armored hit in progress": the dispatcher `$5A9A` runs the knockback (`$5F70`,
    `$5AD8`) while it is 0 and the boxers hit (`$5E60`) while it is 1. During those 33 updates everything else
    that reads it saw armor the arcade had already lost: an armor pickup (the item contexts copy it in and out,
    `$116472`) and the copy the object routine at `$9B52` takes. Now it is set on the hit frame
    and the knockback keeps its own marker (`$FFC343`, unused, cleared by the block init `$6456`). Same knockback
    frame for frame (positions and invincibility identical to the old build's in the same run).
27. **Rank creeps up with play time** (`glue.s` `rank_creep` in `rng_tick`; stage-end blocks `$8A802` etc.).
    Every frame of play (also during a knockback or the death animation; not the death sequence, the map or the
    stage-start hold), when the frame counter's low byte `<$21` is 0, the arcade adds `$006B` to its 16-bit rank
    `<$9A-$9B` (`$EEB9`, high byte capped at `$3F`): +1 about every 612 frames. Each start sets it back to the base
    rank `<$61` with a zero fraction (`$6C65`); a stage clear adds 4 to the base (`$6C58`), a death takes 1 off
    it (`$72BF`). ~28 enemy routines read it. The port had the base (`$FFC501`) and working (`$FFA208`) ranks the
    same way but no creep, and its stage-end blocks added the 4 to the working rank. From the checkpoint:
    arcade 6.00, 6.6B, 6.D6, 7.41, ... 8.ED on updates 52, 308, 564, ... 1588; the port stayed at 6; now the same
    values on the same updates. This was the Unicorn's fireball delay: the shooter's wait comes from `$A324`
    (`1A 16 14 11 10 0E 0A 06`) by rank / 8 (`$A315`), `$1A` at rank 6, `$16` at rank 8: launch 33 updates
    after the allocation in the arcade, 37 in the port, now 33.
28. **Unicorn walk** (`$70A70`). The arcade's walk only moves it (`$A435`-`$A449`, no floor check); the port's
    snapped it to the floor within 8 px (`$70AE2`), so walking off the raised ground at y 78.57 dropped it to 70.57
    on the frame it chose to jump, and the jump ran 8 px low (peak 134.68 against 142.68). The walk no longer
    follows the floor: the jump starts at 78.57 and the arc is the arcade's.
29. **Stage 1 terrain map** (`arthur.s` `map_start_d6/d0`; `$93E0`, `$9454`). The collision map is a ring of 32
    columns of 16 px. The arcade's holds cam/16 - 15 .. cam/16 + 16 (a column written as the camera reaches it),
    the port's cam/16 - 8 .. + 23, so the columns past the screen held the real level in the port and the
    level 512 px back in the arcade. At the boss arena the camera stops at 3234 and the arcade never loads
    x 3504 on: the Unicorn, landing at x 3484, finds floor at x + 24 (its second probe, class 4, `$8CA7`; tile
    `$02` at `$2B6C`) on that old column and stands at 78.34; the port's map had the end wall there (tile `$B1`,
    attribute `$40`) and the Unicorn fell to 70.91. The window is now the arcade's; the screen is drawn
    from the same map and looks the same (compared at several scroll positions).
    With 27-29, the Unicorn fight runs identically in both: 1,640 updates without Arthur attacking, and a fight
    with a lance every 16 frames: ten hits, every walk, jump, landing and fireball, and the death on the same
    updates; the key then falls on the same path.

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

- **Sprite placement not checked:** the final-room boss (no pixel-identical piece to pair), `$B110` frames
  1-4 (ambiguous). Stage 2 zombie walk frames 26-29 matched arcade images 1-2 px apart, possibly the
  streamed art arriving an update late (hypothesis).

- **AI rewritten in the port (to port from the arcade):** the dragon (stages 3, 4, 6: the arcade's head
  follows a (frames, direction) script with the body delayed per segment, `$D6D6`/`$D73D`/`$D955`; the
  port homes, and its re-aim timer byte +$23 overlaps a counter at +$22 so it never re-aims and flies off;
  the stage 6 dragon also spawns at camera-relative (7808,1600) instead of the arcade's absolute
  (7825,2015) record), the Satans (`$1105C6`: choices from the rank byte `$FFA208` instead of a random),
  Astaroth (`$DAD9`: walk/pause, rapid-fire mode, high shots; shot motion), the Petite Devils (rise from
  the lava, hover, dive: `$A89C`/`$A8F9`/`$AB4B`), the stage 5 skulls (sleep/wake/hop, `$CC70`/`$CD08`; the
  port fires them as aimed projectiles). The arcade has a second random source, a shift register at
  `$68F9` (`$6E`/`$6F`), used from 34 places in enemy code; the port has no equivalent.
- **Spawn and activation rules:** stage 2 window devils are never rejected off-screen (arcade `$B25E`,
  on-screen test `$B193`); stage 2 crows start 56-64 frames before they're visible (port `$450A` uses
  512 px; arcade `$A72F` waits until on screen, then perches on random timers); stage 2 tower devils
  (16 spawns, 218-frame life vs the arcade's 9 and 579); the stage 3 dragon fight has one Red Arremer
  instead of two.
- **Ending:** the port walks Arthur 240 frames before the text and has no princess scene (arcade: text 1
  frame after Astaroth dies; 131-frame princess scene on the second clear); +1,000 points at the room's
  end that the arcade doesn't give; "Return to starting point" drawn over the room instead of on black.
- **Smaller:** stage 4 fire pillars one frame early; a stage 5 flying knight drifts after ~600 frames; the
  dragon's score index and weapon-2 pass-through; Astaroth's shot parks on a blinking Arthur; the stage 2
  stone-block edge and elevator walk-step quirks; Big Men 1 px; stage 2 water death y.
- **Bonus lives:** the plus build caps lives at 9 (the arcade doesn't).
- **Continue digit:** the port shows one digit, so the arcade's "10" step shows as 9.

- **Stage start fraction:** start x fraction `$60F5` (arcade) vs `$609C` (port); start y 64.28 vs 64.21
  (leftover RAM in the arcade, `$6D36` sets only the integer bytes).
- **After the Unicorn dies:** the arcade stops updating and drawing Arthur's weapons and the enemy shots (they
  stay in their slots until about 130 frames later, so Arthur can't throw either); the port keeps moving them
  (a fireball goes on 3 px an update) and Arthur keeps throwing. The port also draws a 16x16 sprite (tiles
  `$798`, object `$FF9780`) next to Arthur while the key falls that the arcade doesn't. The key itself matches.
- **Terrain map windows in stages 2-6:** the other streamers (`$9600`, `$104C16`, `$10F06C`, ...) start their
  windows at cam/16 - 8 like stage 1's did; not compared with the arcade's.
- **Intro:** the arcade's opening shows Arthur and the princess in the graveyard (stage background) for
  ~200 frames before the black-background kidnapping scene; the port's intro starts at the kidnapping.
  Start to play is 557 frames in the arcade, ~335 in the port.
- **Dropped fire presses:** about every 23 updates the port advances its update counter without moving the
  weapons; a one-frame fire press there is lost (frame pacing, not weapon logic).
- **Enemies:** with the same input the port's Arthur is hit again ~130 frames after the first tombstone
  while the arcade's isn't hit for another ~340. Not yet traced (enemy tables to be mapped).
