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

18. **The second random source** (`arcrand.c`). The arcade's `$68F9` is a 16-bit shift register on `$6E/$6F`:
    `B = ~($6F ^ $6E)`, two `ASLB` put its bit 6 in the carry, `ROL <$6F / ROL <$6E` shift it in (state =
    state << 1 | (1 ^ bit 14 ^ bit 6)), and the new low byte is returned in B and kept in `$70`; A is kept. Only its
    34 callers advance it (a write watch over boot, attract and stage 1: no other writer). It is seeded with
    `$87CD` at power-on (`$6872`) and whenever the top level restarts (`$69EB`, `$05` = 0: each attract cycle, a
    coin, after a game over), so every game starts at `$87CD`. The port has the same routine six times, working on
    `$FFC62C`/`$FFC62E` (= `$6E/$6F`, `$70`) through enemy contexts: `$218A` (port type 3, `$1E8C`), `$4A28` and
    `$105472` (crows, type 1), `$ABB4` and `$11B8DE` (type 10), `$70B78` (stage 5's `$71F32` unit); but its ten
    stage inits (`$9C0`, `$104728`, `$10EB60`, `$10FA2A`, `$1109D0`, `$111450`, `$11761C`, `$118688`, `$118BEC`,
    `$1196C8`) reloaded `$87CD` at every stage and life start. Now seeded at boot and game start only; `arc_rand`
    (C) and `arc_rand_asm` (d0 = byte, other registers kept) are the replica for later fixes. Measured: after a
    death in the stage 5 boss room the state carries on (`$5582` -> `$5825`, as the arcade's) where the port went
    back to `$87CD`. The call sites (stage = arcade stage index + 1, from runs of every respawn state; types from
    the enemy table `$4544`):

    | Type (handler), stages | Call sites | What the random picks |
    |---|---|---|
    | 1 crow (`$A44A`), 1-3, 5 | `$A599` `$A66F` `$A6AD` `$A775` `$A796` | wake-up branch (with the slot counter), perch times by rank (`$1C,X` table, 8), flight table `$A69D` (16), timers `$A7D6`/`$A7CE` (8) |
    | 2 Petite Devil (`$A89C`), 2, 4, 5 | `$A94A` `$A953` `$AD1E` `$AD33` | a 16-entry table, hover 64-95 frames, 80-111, an offset (& `$2F`) |
    | 3 (`$AFFC`), 1 | `$B09D` | one bit: a 0/1 choice |
    | 4 window/tower devil (`$B146`), 2 | `$B1D1` `$B2D0` `$B352` `$B393` | timer 10-25, two 4-entry tables, a 2-entry table |
    | 6 Satan (`$BED5`), 5, 6 | `$BFD2` `$C066` `$C147` | drift direction (every 128 frames), phase/shot/back-off lengths (`$C06E`, `$C072`, `$C358`), the swoop's target height |
    | 8 (`$C4EA`), 6 | `$C6CF` `$C83B` `$CADE` `$CB7A` | table `$C68E` (8), a timer (4), two 0/1 choices |
    | 10 (`$CF36`), 2, 5 | `$D074` `$D09A` | 0/1: a table, the facing |
    | 12 dragon (`$D518`), 6 | `$D80A` | the whole byte (`<$EB`) |
    | 13 Astaroth (`$DAD9`), final room | `$DB7A` `$DB81` `$DBB3` `$DBDE` `$DC2F` `$DC39` `$DC41` `$DC5E` `$DC84` `$DD01` | two-byte timers (`$6,X`, `$F,X`), offsets, tables `$DBF2` (16) and 8, 1-2, 64-191 frames, and the 0/1 at `$DC84`/`$DD01` that it draws almost every frame |

19. **The Satans** (stages 5 and 6; `satan.c`). The port's (`$1105C6`) took its direction (rank >> 3 & 3), whether to
    move (rank bit 0) and its timers (`$2551EC`/`$2551F4`) from the rank byte `$FFA208`, clamped itself to a box,
    and froze while off screen: with Arthur standing at x 7233 in the stage 5 room it never left x 7385, y 1664
    (arcade: x 7069-7394, y 1588-1730), so Arthur couldn't reach it. The arcade's (init `$BEF1`, asleep until on
    screen `$BF1E`, ground states `$BF4C`, flight `$C0B5`, return dash `$C285`, back-off `$C310`, wings/shots
    `$C001`) is now translated whole, with the arcade's random, `$8FE4` direction, `$FEF0`/`$FED8` divisions and
    `$4140` sine; its shots go into the port's shot pool as its type 6, whose motion is the arcade's type `$0B`.
    Its death keeps the port's score phase but first waits out the arcade's 22-frame burst (`$E8A7`).
    Measured (stage 5 room, the port's frame counter, random state and Arthur's x lined up with the arcade's at
    the Satan's wake-up): Arthur idle, 1,500 frames: x/y (16.8), flags, random state and every shot position
    identical frame for frame (18 shots); throwing lances from where he stands: the same 10 hits on the same
    frames, killed on frame 4,489 in both, removed (and the key released) on frame 4,576 in both (before: 22
    frames early), the key falls the same way, +3,000 in both, 0 differing frames in 4,700; a shot hits Arthur on
    the same frame (163) in both. With the arcade's inputs fed to a test build (`SATAN_TEST`): 6,000 frames of
    walking, jumping and crouching in stage 5 and 8,000 frames with both stage 6 Satans awake, identical.
    `tools/re/test_satan.py` runs the same C on every recorded arcade handler call (~50,000 calls, every state
    including the straight dash): 0 mismatches.

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

- **AI rewritten in the port (to port from the arcade):** the dragon (stages 3, 4, 6: the arcade's head
  follows a (frames, direction) script with the body delayed per segment, `$D6D6`/`$D73D`/`$D955`; the
  port homes, and its re-aim timer byte +$23 overlaps a counter at +$22 so it never re-aims and flies off;
  the stage 6 dragon also spawns at camera-relative (7808,1600) instead of the arcade's absolute
  (7825,2015) record), Astaroth (`$DAD9`: walk/pause, rapid-fire mode, high shots; shot motion), the Petite Devils (rise from
  the lava, hover, dive: `$A89C`/`$A8F9`/`$AB4B`), the stage 5 skulls (sleep/wake/hop, `$CC70`/`$CD08`; the
  port fires them as aimed projectiles). The arcade's second random (`$68F9`, see Fixed 18) is shared by all
  its callers, so each of these has to draw from it (`arc_rand`) exactly when the arcade does, or the numbers
  everyone else gets shift: in the stage 5 boss room the arcade's crows (type 1, `$A66F`) draw three as the
  Satan wakes and the port's crows (`$105472`) didn't in the same run, so in play the Satan's numbers differ
  from the arcade's (the lockstep runs above set the state at its wake-up).
- **The Satans, what's left:** nothing is drawn for the 22-frame burst before the score (the port has no burst
  frames for it); the arcade's hovering pose with the wings open has no port frame (drawn as the flying pose),
  and its shot (a star, sprites `$D7/$DF`) is drawn with the port's type-6 shot art (a small orb). The
  arcade's spawn leaves the x fraction from RAM (stage 6's second Satan starts at 7696.06; the port's at .00),
  which can move a drift step by a frame.
- **Stage 5 boss room camera:** with the same jump, the port's camera follows Arthur up (y 1475 -> 1512) while
  the arcade's stays at 1475; while it scrolls the port lost an update (one frame).
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
