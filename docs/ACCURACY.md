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
   and lives (`$73F3`, `$7446`); the port went to the title. Run in Fixed 56: after the second clear's texts the
   opening, then stage 1 with score, lives and the random kept.

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
18. **Weapons against enemy shots** (`shots.c`, `shot_check` at `$5930`): the port had no such check. The
    arcade's `$F3CE` runs on odd frames before Arthur's shot check: per weapon and shot type a count
    (`$F452`: the cross takes out both itself and shot types 1-9 and 11; the other weapons are used up on
    type 5 and pass everything else) and a box per shot type (`$F498`). Copied with its tables; measured:
    the cross and a man-eater plant's spit both go on the first odd frame, as in the arcade; the lance
    passes through it in both.
19. **Man-eater plant hit box** (`$6BB8`, kind 2 of each weapon in `$2AC94`): the port moved every weapon 18 px along its
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

30. **The dragon** (stages 3, 4, 6; `dragon.c`, hooks `$106F80`, `$106F10`, `$105798`, `$107510`, `$107540`, table
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

31. **The second random source** (`arcrand.c`, also the dragon's now). The arcade's `$68F9` is a 16-bit shift register on `$6E/$6F`:
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

32. **The Satans** (stages 5 and 6; `satan.c`). The port's (`$1105C6`) took its direction (rank >> 3 & 3), whether to
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

33. **Stage 4 halt** (`size_shift` at `$10F816`): a type-14 enemy's size-class change only allowed
    1<->8 and 8<->10 and otherwise stopped the game (fault code `$8C`). Its phase restart (`$10F7C4`)
    sets frame 3 (class 1) whatever is showing, so from a class-10 frame the game halted (reproduced in
    co-op, in the original port's code too). Now any change moves it by the arcade's shape-anchor
    difference (`$F864`: y -16/-24/-32 for classes 1/8/10); the reproduction plays on, the enemy
    dropping 16 px on that frame.

34. **After a boss dies** (`stageend.s`; hooks `$6974`, `$1055A4`, `$BC26`, `$C348C`, `$C35E8`, `$102C56`, `$6938`,
    the sprite-build gates). The boss's removal (`$E844`: `<$B6` to 0, stage index 0-5) sets `<$08 = 2`, and from the
    next frame the arcade runs its stage-end frame `$72C9` instead of the play frame `$72A1`: input, the stage-end
    object (`$7557`: the falling key, in weapon slot 0, `$0540`), Arthur (`$744F`, which still calls his normal handler
    `$90AB`, throws included), the platform/tombstone objects (`$E2B4`) and the scroll (`$8021`); it draws only those
    objects (`$F811`), Arthur and the key. The weapons (`$9C68`), enemies (`$A0A6`), enemy shots (`$FC57`), the two
    item/score slots (`$15E2`, `$E612`), the collisions (`$EF17`) and the spawner (`$E950`) no longer run, and their
    draws (`$F7E5`, `$F7CF`, `$F7FB`, `$F827`) are gone: everything there stops, unseen, and keeps its slot. A weapon
    slot is only freed by the weapon's handler, so with the key in slot 0 Arthur gets one more lance at most (two
    slots for the lance, `$9FA9`), which stays where it was thrown. The port ran all of it until the key was taken
    (`$FFCD7A`, 139 updates later). Now its boss-dead flag `$FFC8D6 = 2` (set by every boss: `$71FFC`, `$118014`,
    `$1185A6`, `$1195E6`) does the same: the two enemy-pass cores, the weapon pass (except the throw frame it shows on
    Arthur), the items, stage 1's weapons-against-tombstones and the spawner are skipped; the builds draw with the
    enemies', shots' and weapons' flags cleared (put back at the next update's start); the first update after it marks
    weapon slot 0 taken, as the key takes the arcade's on the frame after the removal. Measured on the Unicorn (the
    stage 1 boss run in lockstep, a lance every 16 frames): both flags on update 2041; the two lances in the air
    stop at 3411.06/3544.94 (arcade) and 3410.75/3545.25 (port; before: they flew on 4.19 px an update); Arthur's
    throw on 2049 goes into slot 1 in both (3377.75 / 3377.44) and stays there, and none of the later throws gets a
    slot in either; the 16x16 sprite at `$FF9780` (tiles `$798`) is the item in the port's first item slot, the
    arcade's `$15E2` slot it no longer draws: gone. The key, Arthur's walk and the stage-end phases (key taken
    +139, next stage +320 updates) are unchanged. Every stage (1-6, 1P, co-op, Firebrand) with the flag forced in
    play: enemies, shots and weapons stop and disappear, moving platforms keep moving, no faults. The final room
    (index 6, `$736D`) is left as it was.

35. **Weapons off the screen** (`stageend.s` `w_visible`, in the weapon pass; `$115960`). The arcade's weapon slot has
    two flags, allocated (`-$10`) and on screen (`-$F`): before each move `$8E41` sets the second from the camera
    (`<$9C`, `<$9E`) and the slot's window class (`$8E67`): class 0 x + 8 - cam <= `$110`, class 2 x + 16 - cam <=
    `$120`, and y - cam y <= `$100` (unsigned); weapon 1 (the lance) flies in class 2 (`$9E39`), the others and every
    burst in class 0 (`$9CAC`, `$9D8D`). Off the screen a weapon flies on to the end of its range and keeps its slot
    but isn't drawn and hits nothing: enemies (`$EF4A`), tombstones (`$F6A2`) and shots (`$F3CE`) all test the
    on-screen flag. The port's weapon kept its second flag (+9) set from the throw to the end of the range, so it
    hit enemies, tombstones and shots up to 80 px past the right edge (a lance ends 192 px from Arthur, at screen
    x 336). Every hit test already takes +8 AND +9 (`$BE68`, `$6B2E`, `$10457E`, `shots.c`), so +9 is now the arcade's
    flag, set before the move each update, and the build draws by it. Lockstep over the stage 1 boss run (1,700
    updates per weapon, the weapon poked in both): slot-updates whose flags differ from the arcade's, weapon 1
    203 -> 6, weapon 4 395 -> 5, weapons 0, 2, 3 2/2/21 (unchanged: they don't leave the screen); the rest are
    the frames a weapon crosses the edge, a pixel apart because of the fraction below. The Unicorn fight's trace
    (every update of the boss slot and the score) is the same as before.
    Spawn fraction (checked, no change): both games keep the slot's leftover x and y fraction at a throw (arcade
    `$9F76` writes only the two integer bytes; port `$B94A` ORs in the slot's old byte 3), never Arthur's: in 13
    throws with Arthur's fraction `$B1` the new weapon's fraction was its slot's previous one in both games. The two
    differ only by the slot's history (in these runs a constant `$50` per slot, from different start states).

36. **The spawner after the scroll** (`stageend.s` `se_spawn`; `$91E`, `$104AD2`, `$104B0C`, `$10EF2E`/`$10EF44`, ...).
    The arcade's enemies (`$A0A6`) run before the scroll (`$8021`, which moves the camera, `$81C4`, and copies it to
    `<$9C`, `$815F`), as the port's enemy pass runs before its scroll (`$104382`), so their on-screen and despawn tests
    see the same camera in both. Its spawner (`$E950` -> `$EA41` -> `$ECD6`, enemies placed at `$EBB1`) runs after the
    scroll, so it sees this frame's camera and Arthur after his move, and a new enemy first moves the next frame.
    Stage 1's loop calls the port's (`$26DA`) there too; the eight other loops that call it did so before their enemy
    pass and the scroll: a spawn the camera triggers came an update late and the new enemy moved in its spawn update. Those calls
    now come right after the scroll (and not in the stage end). Stage 3 lockstep from the stage start: two spawns on
    updates 406/477 (camera 245/290, y 572) against the arcade's 405/476 (243/289, 574) now land on 405/476 with the
    arcade's camera and y; the dragon (stage 3 dragon lockstep) had its head 1 px off on its spawn update, now the
    same. Stages 2, 5 and 6 over 700 updates: no change (no camera-triggered spawns in them).

37. **Terrain map windows, stages 2-5** (`mapwin.s`; `$11A986`, `$104D16`, `$10F124`, `$11001C`). As in stage 1 (Fixed 29),
    the arcade writes a terrain column as the camera reaches cam/16 + 16 (stage 3 measured: ring column 31 at cam/16
    15, 0 at 16, ...), so its 32-column ring holds cam/16 - 15 .. + 16; the port's streamers kept cam/16 - 8 .. + 23.
    Arthur's floor probe at every 16x16 cell around the camera (columns cam/16 - 24 .. + 31, rows cam y/16 - 12 .. + 19),
    arcade `$8CA7` against port `$8784`, from lockstep states with the same camera: stage 3, 18 disagreeing cells, 14 of
    them at the screen's heights (the platforms at row + 8, columns - 15 .. - 9 and + 17 .. + 23), now 18 all above the
    screen (row + 19); stage 5, 90 cells, now 58, all below the screen; at the screen's heights none are left in either.
    Each window function now starts at cam/16 - 15 with its stage's clamps (the lower one moved with it). What's left
    differs by row, not column (see Open). Stages 2 and 4 were only probed near their start, where the clamp gives
    the same window in both versions (8 and 10 cells there, left of the stage start and below the screen).

38. **Stage 2's crows** (`$47FA`, `$452C`; arcade type 1 `$A44A`). The arcade's crows come in subtypes (`-$E`): 2 (stages 3, 5:
    `$A642`), 3 (stage 2's six crows at x 6208-6576: perch `$A755`, then fly straight at Arthur `$A7DE`), 4 (fly in from off the
    screen `$A72F`, then `$A81C`) and 5 (stage 1: perch `$A755`, then `$A849`). The port's subtype 3-5 handler (`$44FE`) sent
    subtype 3 into subtype 4's entry (moving in at double speed while off the screen), so it drew none of the perch randoms
    (`$A66F` once it is on screen, `$A775`/`$A796` at each 55-75 frame perch timer), and stage 2 held these crows back until they
    were 512 px from the camera (`$452C`). Now subtype 3 perches. Lockstep (Arthur moved through the end of stage 2 to x 6350,
    1,800 frames): every crow's state, x and y and the random state identical (18 draws), where the old build differed on every
    frame and its random parted at the first draw (frame 302). Unchanged and checked: stage 1 (2,400 frames, 18 draws), stage 3
    (1,490 frames, the `$A6AD` flight draws), the stage 5 room (1,500 frames; at a life start both draw `$A66F` for the room's
    three crows on the update after their set-up).

39. **Stage 2's window devils** (type 4; `tdevil.c`, hook `$107A5E`; arcade `$B146`-`$B64D`). The port's states 0/1 were its own:
    no random, the devil turned round at ledges, never glided or dodged, and was only removed 256 px past the screen or when the
    scroll section changed, where the arcade removes it the frame it is off the screen (`$B25E`, so one spawned off screen goes
    at once). Now the arcade's, routine by routine (window `$B41E`, leap `$B4BD`/`$B521` with the tables `$B593`-`$B5F3`, walk
    `$B276` with `$B2BF`, glide `$B309` with `$B348`, hop `$B36F` with `$B37B` and the sine `$4140`, come-down `$B3CD`, dodge
    `$B630`/`$B87E`, life timer `$B1BD`/`$B245`); the floor probe is the port's (`$107ED6` = `$8CA7`). The spawner already
    matched (same records, every 76 frames). Lockstep through the window section (x 4700-5950, 2,500 frames): 11 spawns in
    both, 5 removed at once in both, the other 6 living 155-305 frames, identical frame for frame, and the random identical
    until another enemy's draw (type 10, `$D074`); old build: 9 spawns, 2 removed, lives of 25-419, different from frame 0.
    The dodge test (`$B630` called on 3,000 random placements of the devil, Arthur and four weapons): 0 mismatches.

40. **Red Arremers' first state** (`$4278`; arcade `$B66C`): the arcade starts subtype `& 3` (0 -> 3: awake at once, `$B734`),
    the port 2 for subtype 2 and 1 (asleep until Arthur is within 48 px of its height) for the rest. Stage 3's Arremer spawned
    after the checkpoint (subtype 0, x 1344) never woke in the port and stayed where it was spawned, so the dragon fight had one
    Arremer instead of the arcade's two. From the checkpoint to the dragon (2,400 frames): two Arremers at the dragon in both.

41. **Bonus lives past 9** (`settings.c` `score_added`): the arcade's bonus adds a life with `INC <$60` (`$EDF1`), no cap;
    the plus build stopped at 9. Now no cap. The lives row is the same in both at every count tried (5: 4 heads, 7: 6,
    9 to 11: 7, 20: none, the arcade's row drawn by `$7A3E` and the port's by its HUD), so only the counter changed.

42. **The continue countdown** (`hud.s`; `$62CA`, `$630A`, `$11D260`): the arcade prints "CONTINUE PLAY ?" with the count on
    its own line below, two red digits from 10 down to 01 (BCD `<$0A` from `$10`, a step per 64 frames, `$785D`), at row
    13, columns 15-16 under the text at row 9, column 10. The port counted 9 down to 0 (its 640-frame timer `$FFC594` / 64,
    capped at 9) in one digit after the "?", one behind the arcade all the way. Now the arcade's count (timer / 64 + 1) in
    two digits at its place, in the port's digit tiles with the palette whose colour 15 is red. Compared screen by screen:
    "10" for the first 64 frames, "06" and "02" at the same frames as the arcade's run; on timing out both go to the title.

43. **A kill's score in the update of the hit** (`hud.s` `score_now`, called from `se_objpass`/`se_objpass2`): the arcade's
    weapon-hit code adds the score on the hit frame (stage 1, a lance at each zombie: the zombie's state 1 -> 2 and the
    score `$6A` +2 (200) on the same frame, every kill). The port's enemies queue it as a `$0Cxx` entry in the player's
    event queue (`$FFB400`) during the enemy pass, and every stage loop drains that queue (`$4EE0`, `$78C2`) before the
    pass, so it came an update later (hit on update 551, score on 552). Now the score entries at the queue's head are
    added right after the pass's core with the game's own `$7818` (which stops at the first other entry, left for the
    loop's drain), their count added to `$FFC04C` as the drains do. Stage 1 and stage 3 (the other pass) runs: every kill
    scores in its hit update; the kill count `$FFC04C`, the item slots and the totals are as before.

44. **One-frame presses between updates** (`hud.s` `vb_isr`, vector `$78`; `pad.c`, `p2.c`, `common.c`): the arcade runs
    and reads its pads every frame; the port reads them once per update, and when an update takes longer than a frame
    (stage 1 1P ~0.997 updates a frame, co-op 0.82-0.95) a fire or jump press held only during the skipped frame was
    never seen. The VBlank handler (was `$113E56`: count the frame) now also reads both pads in play and latches the
    fire/jump bits (B, C, A; active low, a press on any frame sticks); each update's read takes them in and clears the
    latch; the readers block interrupts while they read. Stage 2 co-op, fire held for one frame every 37 frames over
    3,400 frames: 92 presses, 89 lances before (3 lost), 92 now. Directions and Start aren't latched (the two-frame
    left/right rule and the pause stay as they were).

45. **The camera doesn't climb while Arthur is in the air** (`hud.s` `cam_air`, `$104392`): the arcade's vertical scroll
    (`$86C4`) skips its scroll-up part while `<$99` is set: set when a jump or fall starts (`$9544`, `$95B4`) and at a hit's
    knockback (`$9BE8`), cleared on landing (`$96F7`) and when the death sequence ends (`$9C32`). The port's camera object
    (`$FFF420`, `$10414A`) has the same thresholds (143/147/152 above, 142/137/132 below) and the same skip, but its copy
    of the flag read `$FFC324`, which nothing writes, so the camera followed every jump up. Now the flag is the jump phase
    (`$FF9410` non-zero), an armored knockback (`KB_ARMOR`) or a death in progress. Stage 5, both games with Arthur placed
    at the same spot and the camera settled at y 1153, the same jump (Arthur to 1334): the arcade's camera stayed at 1153,
    the port's went 1153 -> 1192 -> 1153; now it stays at 1153 on every frame.

46. **A restart keeps Arthur's sub-pixel fraction** (`hud.s` `frac_keep`/`frac_x`/`frac_y`; `se_pace`, `$103E98`, `$103EA6`):
    the arcade's placement (`$6D36`) writes only the integer bytes of x and y, so Arthur restarts with the fraction he had
    when the last life ended (stage 1: died at x `$112B5`, y `$36B0`, restarted at `$60B5`, `$40B0`). The port restores
    its physics block from a copy before its placement (`$103E44`, which also keeps the low byte), so every restart got
    the same `$9C`/`$35`. Now the live fraction is remembered at each update's start and put in at the placement (died at
    `$111C0`/`$3668`, restarted at `$60C0`/`$4068`). The first start of a game still takes what each machine's attract left.

47. **The random counter steps once per update** (`hud.s` `rng_lag_step`, `glue.s` `rng_now`): the arcade's frame counter
    `<$21` counts its interrupts, and since it never misses a frame that's also its update count; the port's (`$FFA206`)
    follows the VBlank count, so an update that ran two frames moved it two and every later draw read one ahead. Now the
    frames past the first in a 2-7 frame update are counted and subtracted (longer gaps, the map, the stage-start hold, a
    pause, count whole as the arcade's counter runs on through them). Stage 1 from the first step, right held, the counter
    and random lined up at the first step: the first hit at +90 (x 196/197) in both; after the port's first long update
    (between +100 and +200) its counter was `$70` against `$6F`, the zombie at x 147 woke at +434 against +467, Arthur was
    pushed over the tombstone 33 frames early and died at +630 against +667. Now the counter is the arcade's on every
    sample, that zombie wakes at +467, the next spawns at +578 in both (x 388 against 389, waking a frame apart) and the
    death is at +667 in both. (This was the Open "Enemies" item: the ~130/340-frame gap came from runs whose counters
    weren't lined up.)

48. **The map after a death** (`$113B8A`): from a death, stage 1, Home start, right held: the death sequence is 121 frames in
    both, the map then took 303 frames in the port (3 to set up, a 300-frame count `$FFC590`) against the arcade's 302
    (mode 0 at +121, play at +423), and from the map's end to the first step 41 frames in both, so every life after the
    first started a frame late. The count is 299 now: map end at +423 and the first step at +464 in both.

49. **Terrain map rows** (`mapwin.s` `mw_rows`, `$9394`): the arcade's collision ring holds the rows cam y/16 - 5 .. + 26,
    the port's held cam y/16 .. + 31, so 1-5 rows under the screen's bottom edge held the rows 27-31 above it. Arthur's
    floor probe at every 16 px cell around the camera (columns - 24 .. + 31, rows - 12 .. + 19; arcade `$8CA7`, port
    `$85D2` called on the RAM of matched stage starts): stage 5 (camera 6656, 512) disagreed on 63 of 1,792 cells, row - 4
    (floor in the port from row + 27's data) and row - 2 (+ 30's) almost all of them; stage 6 (7424, 1536) on 55, row - 3.
    Filling the ring's columns and rows 5 rows lower (`$9386`/`$938E`; the lookup `$9346` already gives an empty cell
    outside the map) leaves 8 and 10, all on the ring's edge columns. A fall below the screen into a pit could find a floor
    there in the port that the arcade doesn't have.

50. **Stage 4's fire pillars step together** (`$10F774`; arcade type 14, `$DE5A`): the arcade's pillars advance their size
    sequence when `(<$21 + 1) & 31 = 0`, all on the same frame; the port's added the slot counter instead of 1, so each
    pillar was offset by its slot (slot 38, the first one on screen from the checkpoint: a frame early; slot 24: 15 frames).
    From the stage 4 checkpoint (the port started there by copying the restart entry for the test) with the counters lined
    up, slot 38's 62 size changes over 700 frames: before, every one a frame early; now 61 on the arcade's update, one (the
    sequence's restart step) 2 frames late (Fixed 57).

51. **The Petite Devils** (type 2, stages 2 and 5; `petite.c`, `petite_glue.s`, hooks `$10C99A`, `$72B6`, `$72F2`,
    `$11AFF0`; arcade `$A89C`-`$AEC0`). The port's (`$3416AA` in stage 2, `$11AEE2` elsewhere) homed on Arthur in 8
    directions for 900 frames, drew no random and dropped nothing. Now the arcade's, routine by routine, on an image of
    the arcade slot (as `satan.c`): stage 2's subtype 0 picks a place on the rock face from the 9 lists at `$AF79` (one
    entry a frame, the scan direction alternating per devil, `$1577`; never the last place, `$1574`/`$1578`) and comes out
    (`$A8C6`, `$AB6F`: weapons pass for 32 frames, 80-111 frames by `$AD1E`); every devil then aims four times (`$AD53`:
    one of six turning plans by the `$8FE4` direction, `$ADAC`), drifts 48-95 frames by rank (`$AD28`) and turns toward
    the plan's direction for 80-111 (`$AC0D`/`$AC33`), then flies off (`$ACD3`); subtype 2 (stage 5) carries a fireball
    and drops it when level with Arthur and more than 50 px away (sideways) or right above him (down) (`$ADFE`/`$AE0E`,
    a 0/1 from the random for an early drop, `$A94A`, and 64-95 frames, `$A953`), then turns through 8 directions
    (`$AC46`); subtype 0 is removed as soon as it is off the screen (`$B25E`), the others out of range (`$8F62`); sound
    `$0B` every 32 frames (`$798D`). The fireball is the port's shot type 6 (its orb art) with the arcade's shot-8
    direction and speeds (`$5D6F` by rank: 1.56/2.0/2.13 px sideways, 2.0/2.06/2.19 down) instead of the aim and the
    2.26 px table. The death in stages 4/5 (`$11AFEA`) lasts the arcade's 21 frames with its sound `$14` (port 36 frames,
    sound `$1B`), as stage 2's (`$11BC0A`) already did. Frames: the arcade's scripts are kept and each sprite is drawn as
    the port frame with the same art (`$F8`-`$FC`, `$F0`-`$F5`); `$FD`-`$FF` (the carrier's other wing poses) have no
    port art and show `$FA`-`$FC`.
    Measured (lockstep, the port's frame counter phase and the devils' spawn fractions set to the arcade's): stage 2,
    Arthur standing, 1,000 frames: 4 devils, every position, state and removal identical frame for frame, the random
    identical (24 draws on the same frames); old build: the same 4 spawns living 185-295 frames against the arcade's
    570-700, no draws. Stage 5, Arthur standing, 2,500 frames: 5 devils, 2,939 play frames identical, 3 fireballs dropped on the
    same frames moving identically (one or two leave a frame apart: leftover shot-slot fractions), the random identical
    (34 draws); old build: 4 spawns, no fireballs, no draws. Stage 5 throwing lances: the same kills on the same frames,
    the random identical for all 31 draws (the spawns after a kill came 15 frames late with the port's 36-frame death).
    `tools/re/test_petite.py` runs the same C on every recorded arcade handler call (subtypes 0, 1 and 2, every state,
    ~29,000 calls, 24 fireballs; subtype 1, which these runs don't meet in stage 4, from devils placed in stages 4
    and 5): 0 mismatches.

52. **Stage 5's skulls** (type 9; `skull.c`, `skull_glue.s`, hook `$110452`; arcade `$CC45`-`$CF33`). The port ran its
    type-9 projectile (`$1074DC`, the dragon's fire) on them: off as soon as they came on the screen (aimed at Arthur;
    since Fixed 30, straight along a leftover direction), removed off the screen. Now, in stage 5, the arcade's: asleep
    until on the screen with Arthur within 32 px both ways (`$CC70`), the rise (3.5 px/frame against 0.16 px/frame^2,
    `$CCB8`-`$CCED`), two hops toward Arthur (`$CD30`: sound `$20`, 3 px/frame up slowing by 0.165, down to the floor
    at up to 3, 0.8 px sideways; the floor probe is the port's `$107ED6` = `$8CA7`), then a leap at his x along a half
    sine 80 px high (`$CE3A`, |dx|/42 px a frame from the `$FED8` division and `$4EE1`), 6 frames, facing him when he's
    more than 64 px away (`$CDDB`); removed out of range (`$8F62`); dying 21 frames with sound `$14` (port: 2 frames).
    The dragon's fire (stages 3, 4, 6) is unchanged. Measured: Arthur teleported next to the first skull (x 6905) and
    standing, 2,500 frames: its wake, rise, hops and leaps identical value for value (1,913 positions until the end of
    the run; the port's own skipped updates only delay it); one lance kills it on the same frame in both and it goes on
    the same frame (old build: it flew off at 3.125 px/frame and left the screen in 60 frames). `tools/re/test_skull.py`
    (every handler call with the floor probes' results, 38,600 calls, every state): 0 mismatches.

53. **Enemy slots keep their x/y fractions over a stage or life start** (`slotfrac.s`; `$9180`, `$98FE`, `$104E90`,
    `$10F1D4`, `$110172`, `$111128`, `$111A82`). The arcade's stage/life start (`$6DA5`) clears only each slot's flags,
    states and type (`-$10`..`-$B`, `+5`), and the initial spawns write only the x and y high:pixel bytes, so a new enemy
    starts with the x/y fractions of whatever was in its slot before. The port's seven stage inits copy a prebuilt
    image of all 40 slots from ROM over `$FFB800` (fractions .00). Now the copy keeps each slot's `+19`/`+23`. Measured:
    stage 1, Arthur drowned at x 1675 with the Red Arremer flying (x 1629.98, fraction bytes in hex): after the restart
    its new Arremer is at 1472.98 in both (port before: 1472.00). Stage 6's second Satan (`satan.c` copies the port slot's fractions when
    it is born) now starts with its slot's leftover fraction as the arcade's does (7696.06 after a life in which that
    slot held the same Satan); at a game's first stage start the leftovers come from each game's own attract and earlier
    play, so they agree only where that history agrees.
54. **Big Men** (type 10, stages 2 and 5; port handler `$11B1BC`, arcade `$CF36`): the arcade's Big Man is size class 3
    in every stage (`$CF54`): its on-screen box (`$8E67`: y within 240 of the camera) wakes it, its floor probe (`$8CA7`,
    `$8DA6`) looks 16 px below its y. The port set class 10 (box 248) outside stage 2 (`$11BA2A`) and probed with its own
    box 32 px below (`$11B7A6`, `$14E82` = class 10's), so a Big Man stood 1-2 px high and could walk off a floor the
    arcade's stays on; the port then confined stage 2's to x 5200-5808, turning them there (`$11B746`), and assumed a
    floor in that stretch when the probe found none (`$11B7D0`). Now class 3 everywhere, the probe with the port's
    class 3 entry (`$6D612`), and neither stand-in. Lockstep (stage 2 from the checkpoint, the same walk, random state and
    Arthur's y fraction lined up): before, the first Big Man to wake stood at y 160 (arcade 158) from frame 378 and turned
    at x 5200 (the arcade's walks on); now every Big Man is identical (states, x, y, facing) until another enemy's draw
    from the shared random parts the two games (frame 1111, a Big Man's `$D09A` facing). Stage 5 (Arthur raised to them
    1 px a frame): the first one wakes on the arcade's frame (437; before 430) and settles at the arcade's 1055.
    Hits to kill weren't compared (the port gives stage 5's 0 hit points at `+11`, stage 2's 10; not traced).

55. **Astaroth** (final room, type 13; `astaroth.c`, `astaroth_glue.s`, hooks in `install_astaroth`; arcade handler `$DAD9`:
    init `$DAF3`, wait `$DB29`, walk `$DB8E`, pause `$DBCB`, fire control `$DC06`-`$DD11`, shot `$DD12`). The port's
    (`$111B9C`) walked and paused on timers from its own tables picked by the rank byte and the frame counter, fired one
    low shot every 12-180 frames as its type-10 enemy (the stage 2/5 fire creature: a walker that stopped on Arthur, so
    the shot parked on a blinking Arthur and hit him when his invincibility ran out) and had no rapid-fire mode or high
    shots. Now the arcade's handler for states 0 and 1, on an image of its 48-byte slot as in `satan.c` (the port keeps
    its drawing: frames 1/3 walking, 2/4 the open mouth in rapid fire): walk 0.18 or 0.41 px/frame (`$53F2`/`$53FA` by
    `$DBF2[random & 15]`) between camera + `$60` and + `$E0` for 1-1023 frames, pauses of `$DBC7[rank]` + random &
    `$2F`, shots on gaps from `$5402` by rank, a rapid-fire mode every 256-767 frames for 64-191 frames (gaps `$5422`,
    high or low at random), high shots 3 times in 4 when Arthur is 80 px or more away, the ten random draws (`$68F9`,
    Fixed 31 table) at the arcade's places. Its shots are the arcade's projectile type `$0A` in the port's shot pool
    (`$FFC100`, the arcade's `<$A7/<$A8`) as type 10: set up on the frame they're made (`$FD17`), then a straight line at
    the rank's speed (`$5E0F`: 1.43-1.79 px/frame forward, 0.59-0.73 down, `$FEA3`), gone 128 px past the screen's
    sides, 64 below it or in the floor (`$8CA7`, the port's `$85D2`); tested against Arthur by the pool's own code on
    odd frames (box `$F5A2` = port `$4BC8C`), weapons pass through them (`$F452` has no entry for `$0A`); drawn by an
    enemy slot of type 10 with no collisions using the port's flame art (`hook_ast_shot`). Its death: the arcade's
    sounds and 22-frame burst (`$DD67`, `$E8D0`) before the 63-frame phase the port's death is (`hook_ast_die`).
    `tools/re/test_astaroth.py` (the same C on every recorded handler call from `arc_start.py 6 0`/`6 1`, with random
    walking, jumping and crouching): 4 runs x 7,127 calls (1,653-1,718 in rapid fire, 98-106 shots, 21-29 high), 0
    mismatches. Lockstep from the arcade's final-room restart against the port's (developer launch with the stage poked
    to the final room; `<$21`, the random and Astaroth's fractions copied at its init; Genesis Plus GX at 200% CPU so the
    port doesn't drop updates): Arthur standing, invincible: Astaroth's x/y, state, rapid-fire flag and every shot equal
    on every frame for 7,830 frames (to the port's time-out); old build: Astaroth differs from frame 4. Jumping and
    throwing the axe: 10 hits on the same 10 frames (112-466), death on 466, removal on 551 in both, 10,000 points in
    both (old build: Astaroth not killed in 1,200 frames with the same input). Arthur not invincible: hit by a shot on
    frame 206 in both, the shots then pass through the blinking Arthur in both. Arthur's y fraction after a knockback
    differs (.01 against .11-.14; Arthur's code, not traced).

56. **The end of the final room** (`ending.c`, `ending_glue.s`, `mkprincess.py`; hooks in `install_ending`). Arcade:
    Astaroth's removal (`$E844` at stage index 6: no sound, no points) switches to the stage-end mode and from the next
    frame `$736D` runs by the clear count `<$7F`. First clear (`$73FE`): the screen black (`$0E00`; the HUD with TIME,
    the lives and the weapon stay), no sprites, "THIS ROOM IS AN ILLUSION ..." (`$022C`) for 300 frames, then `<$7F` = 1
    and stage 1 from its map (`$7446`), score, lives and random kept. Second clear (`$7EDC`): the princess (object
    `$15C2`, x 8179) set up on frame 1, Arthur's target x + (her x - his x, low byte) / 3 (`$7F21`) and y `$0A4E` on
    frame 2; both walk 1.125 px a frame (`$9477`), she until within 16 px of his target, then both take their embrace
    frames, four hearts rise above Arthur on the frames with `<$21` & 15 = 0 (`$7F95`), then "CONGRATULATION / THIS
    STORY IS HAPPY END" (`$022D`, over the top heart) and 50,000 points over the room for 540 frames, "BEING THE WISE
    AND COURAGEOUS KNIGHT ..." (`$022F`; TIME and hearts erased, `$011A`) for 420, "RETURN TO STARTING POINT /
    CHALLENGE AGAIN !" (`$0230`) on black, no lives or sprites, for 180, then the game starts over from its opening
    scene (`$73F3`, `$7446`), score, lives and random kept. Each text's first frame counts and the next starts on the
    frame the last ends. The port waited 240 frames after the removal with the game running, gave 1,000 points and
    sound `$3F`, drew the first text over the room with the last frame's sprites frozen on it (Arthur in the font's
    tiles), went back to stage 1 through the game start (no map, the random reseeded), had no princess scene, drew
    "RETURN TO STARTING POINT" over the room, ran each text a frame long and, after the second clear, played stage 1
    without its opening. Now, measured in lockstep from the frame after the removal (`end.py`-style runs, both clears):
    the first text on frame 2 and stage 1 on frame 301 in both, the map then play (the arcade's play from 604, the
    port's 606), random `eb04` kept in both; second clear: Arthur's x equal on every frame of the walk (8024 -> 8076 on
    frame 49), embrace on 82, hearts on 89/105/121/137, CONGRATULATION and the 50,000 points on 139, the next texts on
    678 and 1097, the restart on 1276 in both, random kept. The princess and both embrace frames aren't in the port's
    art: they are the arcade's sprites (`gg12`-`gg17`: walk 566/574 and 567/575, embrace 550-559, Arthur's 629-638;
    the heart char `$60` of `gg1`) converted at build time to Genesis tiles in the port's palette line 0 (Arthur's
    colours, which are the arcade's: his frame converts exactly; the princess's purples have no match there and come
    out lilac), uploaded to VRAM `$A000` (Astaroth's art, free after his removal) and drawn as sprites. The heart is red
    (no pink in the line). Not as the arcade: the texts are the port's font in one colour and appear whole (the
    arcade's are coloured and typed out); the 50,000 points can give a bonus life at once (the arcade gives it on the
    next play frame, 40 frames into stage 1) (Fixed 58); the opening after the second clear is the port's own picture sequence
    (`$E0C`, ~315 frames; the arcade's runs 517 in the graveyard).

57. **A fire pillar's size at a step of its count** (`pillar.s` `pillar_step`, hook `$10F7C4`; arcade `$DE65`-`$DE89`): when
    a stage 4 pillar's 32-frame count runs out the arcade restarts its animation with `LDU #$54FB / LDB ,U / STU $8,X /
    JSR $8EBF`, setting the first entry's size class (1, with its y offset) on the step frame without advancing the
    pointer, so the same entry is read again when the 2-frame timer (`$2,X` = 2) runs out. The port's step set the
    animation index (`$248BAA`) and the timer only, so its first size change came with that second read, 2 frames late,
    visible when the step cut into an animation not at class 1 (the restart step of Fixed 50). Now the step also calls
    the size change (`size_shift`) with that entry's class. Measured from the stage 4 checkpoint (the port started there
    by a test copy of the restart entry, frames keyed on the update counter so the port's 2-frame updates don't count),
    slot 38 over 3,000 frames: 267 size changes and 94 count steps; before, 4 size changes 2 frames late (frames 330,
    1162, 1738, 2570, once a cycle of the count sequence), now all 267 on the arcade's update.

58. **The ending's bonus life comes in play** (`bonus.c`, `settings.c` `bonus_give`/`score_added`, `ending.c`, `glue.s`
    `rng_tick`): the arcade checks for a bonus life only in its play loop (`$E962` -> `$ED96`), on frames with `<$21 & 7`
    = 0 while Arthur isn't dead (`<$90` = 0) and below 1,000,000 points, one life a check (`$EDEA`-`$EDF1`). The 50,000
    points of the second clear (`$0C15`, on the CONGRATULATION frame) are added in the stage-end mode, so their life comes
    in stage 1: measured (the second clear forced in a final-room state with 49,000 points, so the 50,000 cross both the
    20,000 and 70,000 thresholds), mode 1 from the opening's end, play (`<$0B` = 1) 39 frames later, the first life on
    the next frame (`<$21` = `$10`, 40 frames into stage 1), the second 8 frames later. The port gave one life at once
    with the points (`score_added`, `$779A`), and only one. Now `ending.c` marks its score add, `score_added` then only
    sets `bonus_pending`, and `rng_tick` (once a play update, `$FFA206` = `<$21`) calls `bonus_tick` while it is set:
    the arcade's check on updates with `$FFA206 & 7` = 0 and `$FFC570` = 0, one life a check until none is due. Port,
    the same forced run (`tools/lockstep/port_end.py`, `SCORE=00049000`): no life at the 50,000 (frame 146 after the
    end), stage 1's first play update with `$FFA206` = `$B7`, the first life on the next one (`$B8`), the second 8 updates
    later (`$C0`); before, one life on frame 146. Points scored in play: Fixed 59.

59. **A bonus life in play comes on the arcade's check frame** (`settings.c` `score_added`, `bonus.c`): the arcade's
    life for points scored in play comes 0-7 frames after them, on the next frame with `<$21 & 7` = 0 (`$ED96`; a score
    poked to 20,000 at `<$21` = `$70`: the life at `$78`), and points crossing two thresholds give their lives 8 frames
    apart. The port gave one life with the points (`$779A`). Now `score_added` only sets `bonus_pending` for every score,
    and the check of Fixed 58 gives the lives. Port, stage 1 with the score poked to 19,900 and a lance at the zombies:
    20,100 at `$FFA206` = `$BA` (update 828), the life at `$C0` (update 834); before, the life with the points.
60. **The Satans' art** (stages 5 and 6; `bossart.c`, `bossart_glue.s`, art by `src_patch/mkart.py`; hooks `$11086A`, `$11051A`,
    `$11721C`, `hook_sat_dma`, `hook_satan_die`). The port drew 2 poses (flying, wings closed: tiles `$500`-`$543`, loaded once by
    `$1104FC`), nothing for the burst, and the shot as its type-6 orb. Now the arcade's: the hovering pose with the wings open
    (`$4C6D`: 4 entries of 11 frames, poses A B C B, restarted by `$906B` at `$BF95`/`$C049`/`$C32E` with the facing of that
    moment and counted down by `$9074` at `$BF9D`/`$C1F5`/`$C22D`, as `satan.c` now steps it in the slot image's anim bytes), the
    burst (`$E8A7` for class 4: `$5B89`'s 2x2 then `$5B24`'s 3x3), and the star (`$1D7`/`$1DF`, 4 frames each). mkart.py converts
    the arcade sprites with the port's own pens for the Satan (its conversion of the flying and closed poses is reproduced
    exactly: 16 of 16 pieces equal to `$2552F4`) and the nearest colours of line 0 for the rest. 9 pieces a pose don't fit
    resident, so each Satan on the screen gets a 9-piece buffer in the Satan's own tiles (`$500`, `$524`), and its pose's
    pieces are DMA'd there at the sprite-table DMA of the frame that shows them (`sat_vblank`; skipped with it when `pace.c`
    holds the sprites); the score (the port's 2 pieces, `$255B74`) goes into the buffer too. The star sits in `$5F4`-`$5FB`:
    the only writer of `$5F4`-`$5FE` in the ROM is `$6434`, unreachable (`$6428` returns first), and in 4,061 VRAM snapshots
    of stage 5 (2 bot walks, 1P/Firebrand; the boss room, 1P/co-op/Firebrand) and 1,593 of stage 6 (random play, 3 modes)
    nothing else wrote or showed those tiles.
    Measured (stage 5 boss room, Arthur idle then throwing): the hover poses change every 11 frames A B C B as the arcade's
    (`$4C9F` entries at its frames 7, 18, 29, 40); from the kill frame the arcade shows the pose 3 frames, the 2x2 3, A B A B 4
    each, C 3, then the score; the port the same up to C, which it shows 2 frames (its score phase starts a frame earlier);
    the star alternates every 4 frames from its shot as the arcade's (the port's shot is first drawn a frame later than the
    arcade's, as before). Side by side: hover poses, burst and star match the arcade's frames.

61. **Stage 2's windows** (`bossart.c` `win_step`/`win_vblank`, from `tdevil.c`'s `window_tiles`; arcade `$B457`, tables
    `$B495`/`$B4A9`). The arcade's devil writes 2x2 bg tiles at its window (code `$Fn` + `$F8`.. with attribute `$87`: tiles
    `$2F0`-`$2FF`, colour 7) every 5 frames: opening F0 F2 F4 F6, closing F6 F4 F2 F0; the port drew nothing. The port's stage 2
    bg is plane B (`$C000`, 64 x 32, line 3; a window at the devil's x, y is at column ((x >> 4) - 1) * 2, row 30 - 2 * (y >> 4),
    checked on 4 windows), and its closed windows are its own conversion of F0 (pens 0-6 -> 1 4 5 6 6 A A, which mkart.py
    uses for F2-F7/FA-FF; 45 tiles). Two windows can open at once, so each gets a 16-tile slot (`$6AC`-`$6BB`, `$6BC`-`$6C7` +
    `$5F4`-`$5F7`) filled with the step's pose at the vblank and its 4 x 4 cells pointed at it; the closed cells, saved when
    it opens, are put back at the end. Stage 2 never had anything in `$6AC`-`$6C7` in 2,061 snapshots (1P, co-op, Firebrand,
    the checkpoint); the only code that writes there is the Unicorn's second art slot (`$71DF0`: type 8, `$6A4`-`$6C7`), at the
    stage's end. Side by side from the checkpoint (both 30 frames after the restart, walking right): the window's poses on
    the same frames (frames 127-180: opening, the devil, closing, closed).

62. **The opening** (`bossart.c` `intro_scene`, `intro_waits`; hooks `$C48`, `$E92`, Home start in `glue.s`). After Start the
    arcade draws stage 1's graveyard at camera 0 with the HUD's top rows, Arthur sitting in his boxers, the princess and the
    armour (frames 806-998 with coin at 700 and Start at 800), fades the bg palettes at 871 and 935 (Arthur turns his head at
    955), and goes on on black from 999; the port's intro (`$E0C`: 155 steps of plane writes, 2 frames each) was only the
    black part, and Arthur could move 362 frames after Start (arcade 559). Now the graveyard comes first: mkart.py runs the
    arcade (tools/arcade) to those frames and converts its bg (38 tiles, the black pen as the backdrop), HUD chars and 10
    sprite pieces into 196 tiles and 4 lines packed from the colours of the three palette phases. Then `$E0C` runs with a
    wait per step from the arcade's frames of the same events (the cloak blinking from 993, the wings at 1045, poses at
    1057-1101, the swoop 1110, the princess taken 1126, gone 1149, Arthur lands 1158, gets up 1192, armour 1212, walks
    1246-1287). Measured: the graveyard shows 193 frames as the arcade's (port 908-1100, arcade 806-998: 2 frames later
    after Start); the steps land on the arcade's frames (side by side every 24 frames, 1010-1322); Start to Arthur's first
    step 559 frames in both (the picture ends 5 frames early because the port's stage start takes 4 frames more). Start
    skips both parts from the 21st frame as before; the Home start shows them too; Firebrand's Quest skips them as before.

63. **Stage 5's skulls and Petite Devils, their art** (`bossart.c`, `petite.c`'s frames, `skull.c`'s frames; type-9 draw tables
    `$107642`/`$10764E`/`$107658`, devil frames `$11C256`/`$11C09E`/`$10CE00`/`$11C26E`/`$10CE16`/`$11C0A8`, `$11C15E`, `$11721C`).
    The port had the skull asleep and rising (its type-9 tiles `$4A0`-`$4B3`: `$A7`, `$A2`-`$A5`) and drew the standing skull
    with them; no art for the carrier's wing poses with the fireball (`$FD`-`$FF`, shown as `$FA`-`$FC`) or the fireball (`$F7`,
    the type-6 orb), and the dying devils of stages 3-6 kept flying (frames 9-12, 21-24). Now: the standing frames (`$CE1A`: A8
    A0 A9 A1, AA A2 AB A3, AC A4 AD A5, 2 x 2) through the port's own type-9 draw from a longer frame table (the port's 3 frames,
    then these, then the burst); the 8 new pieces and the fireball in stage 5's second Satan buffer (`$524`-`$547`, unused there:
    one Satan); the devil's 3 poses as frames 41-46 after the port's 41 in its streamed devil bank (both upload loops and the
    draw); and both deaths with the arcade's burst (`$E85B` for class 3: 2 x 2, 5 poses, mirrored, attribute `$54`), which is
    the port's own enemy burst, resident in stage 5 (tiles `$320`-`$36B`, line 2). The pens are the port's own conversions of
    the same characters, reproduced exactly (5 skull pieces, 11 devil frames). Timing by each death's 21-frame count, as in
    the arcade (`$CF07`, pose 3 frames then 4/4/4/4/3). Stage 2's dying devils already showed a burst (`$11BCB0`). Measured:
    co-op stage 5 0.914 -> 0.890 updates per frame (9 seeds; the standing skulls are 4 sprites and the bursts are drawn), 1P
    and Firebrand within noise; no faults in stages 1-6 x 1P/co-op/Firebrand and the stage 5 boss room.

64. **Vertical scroll speed** (`rowfast.s`; hooks `$938E`, `$986C`, `$104DF6`, `$110102`, `$1110B8`, `$11570E`, `$11AB02`). Stage 5,
    Arthur put at y 1167 over the start (the camera then climbs 5 px a frame from 512 to ~1000, a row crossed every 3 frames):
    the arcade's camera moves every frame (its update count is its frame count); the port lost one update in the climb
    (frame 88, camera 847 -> 852 over 2 frames). Each row crossing ran the streamer `$10FF6A` at ~43 of the update's lines
    (Unicorn estimate, `tools/re/uc_profile.py`): the collision ring's row fill `$938E` (32 cells through the lookup `$9346`,
    bounds checks and a multiply each) and the row's plane entries (`$1100E0`: 256 bytes cleared, then 32 cells with a
    multiply each). The same bytes are now written with one bounds check of the row and pointers stepped by the map's
    height and the row's stride, without the clear (the 32 cells cover both halves): 42.9 -> 14.4 lines, that update
    235 -> 206; the climb runs an update every frame. Checked: `tools/re/test_rowfast.py` (every row routine of stages
    2-6 on RAM of each stage start and of the climb, every window column and row in a range, three upper-word patterns of
    d1: identical RAM), `tools/re/test_ab.py` on stage 5 and 6 snapshots (identical RAM and VDP writes), and the climb
    frame by frame: planes A/B and the ring identical at each of 199 updates. (From Fixed 65 the ring part writes nothing.)

65. **The terrain map as the arcade writes it** (`terrain.c`, `terrain_glue.s`; hooks `$9386`, `$938E`, `$1043B4`, `pad.c`
    `stage_hold`; supersedes the ring windows of Fixed 37 and 49, whose plane windows stay). The arcade's collision map is
    its bg RAM (`$2800`/`$2C00`, cell (col & 31) << 5 | (~row & 31)). Logging every write to it (`tools/arcade/bg_writes.py`):
    a camera crossing a column to the right writes column C + 16, to the left C - 1 (`$81E7`/`$8457`, copy `$8677`); a row
    upwards row R + 16, downwards R - 1 (`$8783`/`$88A0`); a column write covers rows R - 8 .. R + 23 and a row write columns
    C - 8 .. C + 23, each cut at its 40-cell buffer's end (rows <= (R & ~15) + 31: stage 5 at R 62, 26 rows; columns <=
    (C & ~15) + 31: at C 431, 25 columns); the stage draw before play (`$726E`/`$80A0`, every life) scrolls its own camera
    18 columns right and back, leaving columns C - 1 .. C + 30. The cells come from one world map: at stage 5's start the
    column left of the screen is stage 4's last (415, a wall), at stage 6's stage 5's 463 (with these and the windows, the
    arcade's ring at the stages 4, 5 and 6 starts is reproduced byte for byte from the port's maps). The port filled from
    its plane windows (cam/16 - 15 .. + 16 clamped to the stage's map, so 416 .. 447 at stage 5's start; rows cam y/16 - 5
    .. + 26) and streamed a row climbing at R + 10, descending at R - 5, a column scrolling left at C - 15. Now the
    streamers' ring fills write nothing (`$9386` returns, `$938E` only leaves d1 as its plane loop needs it) and the ring
    is written after each camera update (`$1043B4`) and in the first frame of the stage-start hold (~0.5 frame, the hold
    keeps its length; the first update after a stage start or a death is on the same frame as before). Arthur's floor
    probe at every cell around the camera (`tools/re/terrain_probe.py`, arcade `$8CA7` vs port `$85D2`, 1,024-1,792 cells):
    stage starts 2/4/5/6 disagreed on 8/10/8/10 cells, now 0; stage 3 on 14, now 13; stage 5 after the 5 px climb above
    (camera 1019) on 173 (rows + 12, + 14, + 17 whole: the top of the screen had the floors of 32 rows lower, and the
    columns left of the start), now 0; then walking right and dropping to camera 833: 122, now 2 (the cameras a column
    apart). Planes A/B identical update for update (stage 5 climb and walk; `test_rowfast.py --noring`, stages 2-6).
    What's left: cells in none of the port's maps keep its tile 0 / attribute `$C0` where the arcade has its world's (zeros
    under stage 5's start, walls under stage 3's floor and below stage 1-2's row 0: no floor in either game's probe); stage
    3's 13 cells are its collision map itself (rows 49-55 of columns 0-12 repeat rows 33-39 in the port's, empty in the
    arcade's), 300 px above the start. With 64 and 66: no faults in stages 1-6 x 1P/co-op/Firebrand (`bench.sh`, seed 7);
    in-play updates per frame, 3 seeds each, before -> after: stage 2 1P 0.931 -> 0.928, co-op 0.710 -> 0.699; stage 5 1P
    0.994 -> 0.990, co-op 0.842 -> 0.854; stage 6 1P 0.980 -> 0.978, co-op 0.834 -> 0.805 (random input: the runs part
    once the terrain or a jump differs, so single seeds move both ways).

66. **Stage 2's ledge-edge jump and elevator walk steps** (`pad.c` `arcade_input`, `arthur.s` `ground_snap`/`carry_gate`,
    `glue.s` `tomb_check`/`box_walk`; hooks `$8698`, `$9DFC`, `$10F602`, `$11A432`, `$11A650` and the eight stage loops'
    ground step calls `$104AA6`, `$10EF06`, `$10FDB6`, `$110DB4`, `$1117FE`, `$118A54`, `$118F92`, `$119ADC`). Both games
    from the stage 2 start with the same plan (walk, x-triggered jumps), compared update by update
    (`tools/lockstep/dual_updates.py`): (1) a jump pressed on the step that carries Arthur past the ice ledge's edge (x
    3880.5): the arcade's press frame walks and takes the jump set-up branch (`$9218`, state `$0503` = 2), which has no
    floor check, stands a frame and takes off from y 142.80; the port's ground step (`$868E`) made him airborne on the press
    frame and its take-off (`$B484`) needs the ground, so he fell (Fixed 2's wind-up already gave the frames). Now the
    wind-up (the press frame and the one after) keeps him on his floor (`ground_snap`, a flag set by `arcade_input`) and
    off the platform carry (`carry_gate`; the arcade's set-up isn't carried: pressed on the elevator at y 194.1D it takes
    off from 194.1D, the port from 192.41). (2) Riding the descending elevator (type 3) the arcade's walk skips a step
    every ~14 updates: its walk test against the objects' boxes (`$9FAE` from `$940E`, every type 1-5 with the boxes of
    `$A052`, type 0 none) probes y + 1, which enters the elevator's box (y ± 24) whenever the elevator's integer y stands
    still for an update. The port's test (`tomb_check`) took type 1 only and only stage 1's and 3's loops called it; now it
    takes types 1-5 with the arcade's table, probes the y of the update's start (the arcade tests before its floor step),
    and the other loops run it after their ground step. Before: the runs parted at update 336 (664 of 1,000 updates
    differed); with (1) only at 596 (404); now 1,000 of 1,000 identical: the edge jump, the ledge, the elevator ride with
    its skipped steps, the jump off it, the landing and the walk on to the water at x 4248. The stepping stones (type 4,
    x 6032-6608) take the same test but weren't reached in a run; the carry gate on the other movers (stages 3-5) wasn't run.

67. **Stepping down, and the walk test's reach** (stage 5 room and all stages; `arthur.s` `ground_snap` at `$8698`, `glue.s`
    `tomb_walk` in `box_walk`). Both games from a life start at x 7008, y 1615 on the room's top floor (stage index 4's
    restart entry pointed there: arcade RAM `$6CFD` = `40 DB 60 50`, port test copy `$1040DC`), the port's x fraction set
    to the arcade's, walking right (`tools/lockstep/route.py` `R7300`), x and y every frame. (1) At x 7048 the floor is a
    pixel lower: the arcade's walk (`$91D1`) finds no floor at its feet (`$8CA7`) and no object at y - 1 (`$9674`/`$9FAE`),
    so it moves to the fall state (`$91F2`, `INC -$C,X`); that frame walks no further, its fall (`$965A`, 4.25 px) lands
    back on the floor (`$8CA7`/`$91EC`): x 7048 for two frames, y 1615 -> 1614. The port's floor search (`$8744`) probed a
    second time 8 px down and snapped him down in the walking update, so from there he was a frame ahead. The ground step
    now takes the floor at his own y (`$8784`) and then the objects (`$84B8`, `$8744`'s last step), never the probe below:
    no floor is a fall, as the arcade's (the ladder-bottom and stage-start cases of Fixed 23-29 were this rule already).
    (2) On this base the port's Arthur then stopped at x 7167 for good (main's build, before Fixed 66, walked on): the walk
    test probes the old x + 1 in its low byte with the high byte kept (as the arcade's, `$946E`/`$9FDC`), so at x 7167 it
    probes 6912, and its y test is a byte one: stage 5's type 5 object at x 6936, y 1112, 503 px below, matched. The
    arcade's objects (`$1010`, 30 x 32 bytes) are only live near the screen (none in the room), the port's are live for the
    whole stage; the test now also needs the object within 128 px in y. Before: the walk 7008 -> 7300 differed from x 7048
    on (and stopped at 7167); now 400 frames identical (two 1 px steps, the second one up). (3) The ladder from the floor at
    y 1455: reached in play from the same start (down the ladder at x 7248 to y 1535, down the one at 7184 to 1455), 56
    targets x 7160-7215 in each game: both take it from x 7168-7199 and put Arthur at x 7184. The old note's 7200 came from
    a life start at x 7233 on that floor: there the arcade's stage draw leaves its whole bg ring one column off (column
    c's cells hold column c - 1's data; at the x 7008 start they're right), so its ladder is 16 px right. Stage 5's own
    restart points (x 6736, 6784) are far from it, so it isn't reached in play; the port writes the map as it is. Other
    stages per update (`dual_updates.py`, walking right, fractions zeroed), before and after alike: stage 2 from the
    checkpoint 388 updates identical (to the water, whose death y is Fixed 46's), stage 3's start 900, stage 4's start 90 (to
    its pit).

68. **The Satans' burst, its last pose** (`glue.s` `hook_satan_die`, `bossart.c` `sat_burst`; `$110826`). Stage 5 room,
    Arthur throwing from x 7233 with the Satan's hit points held at 1, the arcade's sprite buffer and the port's sprite
    table read every frame from the kill: the arcade (`$C368` on the kill frame k, `$E8A7` k+1 .. k+22, `$C375` from k+23,
    state 3 at k+85, removed k+86) shows the pose to k+1, the 2x2 3 frames, A B A B 4 each, C 3 (k+21 .. k+23), the score
    from k+24. The port's burst count runs a frame behind (its count 1 still shows the pose), so its 22 counts gave C 2
    frames and the score a frame early, with the removal on the arcade's frame. Now 23 counts (C for 21-23) and a score
    phase of 62 frames: C 3 frames, the score from the arcade's frame, state 3 and the removal unchanged. The old note that
    the arcade's small burst leaves the flying pose's right column on the screen wasn't reproduced: killed (state set to
    2) on 14 frames covering the hover poses A B C and the flight pose in both facings, at mid-screen and at both edges,
    the arcade's sprite buffer holds the 2x2's 4 pieces only for its 3 frames (the buffer as DMA'd at `$65C4`, checked equal
    to `gng.py`'s copy on every frame of a kill); the port draws the same 4.

69. **Stage 2's windows when their devil is gone** (`bossart.c` `win_step`/`win_vblank`). The arcade writes a window's
    tiles only from its devil's window state (`$B457` from `$B41E`/`$B51B`), so a devil killed or removed before the
    closing is done leaves the window as it was. From the checkpoint walking right, the first window devil removed on its
    closing's first frame (f158): window 312,7 stays open (F6) while two more open and close (f203-f266), until the screen
    is cleared at the death (f511); without intervention a devil gone at F2 left its window at F2 (f376). The port gave a
    window's slot to the next window that opened, taking the first slot whose devil was gone, without putting back the dead
    window's cells: they still pointed at the slot, so the dead window showed the new one's poses and then its last pose.
    Now a window keeps its slot while its devil is gone (not live, not type 4, or out of state 1/4); a new window takes a
    free slot at its first pose, and only when none is free is one given up (a dead devil's, off the camera's reach
    first), its closed cells put back. Port, same test: before, the dead window followed the next two windows' poses; now
    it stays open until the redraw at the death (r549). Not matched: a dead devil's open window with two live ones at
    once (the arcade shows all three; there are two slots, so the dead one closes).
    With 67-69: no faults in stages 1-6 x 1P/co-op/Firebrand (`bench.sh`, seed 1); in-play updates per frame, 1P, seeds
    1-3, before -> after: stage 2 0.918/0.941/0.924 -> 0.918/0.941/0.922, stage 5 0.993/0.987/0.991 -> 0.987/0.988/0.990,
    stage 6 0.983/0.963/0.988 -> 0.984/0.963/0.988.


70. **The opening's black part and the stage start after it** (`opening.c` `intro_scene`, `intro_sched` from `mkart.py`;
    hooks `$C48`, `$943C`, `pad.c` `stage_hold` -> `intro_hold`/`hide_frame`, `bossart.c` `sat_vblank` -> `hide_vblank`).
    Arcade (Start at 800, `tools/arcade`): the graveyard's bg and HUD at 804, its sprites from 805, the fades at 871 and 935,
    Arthur's head at 955, the Satan's cloak over it at 993 and 996; the characters on black from 999 (the port's `$E0C`
    picture), the cloak shown 1000, 1004, 1008, 1012-1015 and 2 frames of 4 to 1043 (11 blinks), wings 1045, poses 1057-1101,
    swoop from 1109, the picture's last frame 1318; then the HUD (TIME, lives, weapon) on black 1320-1358, Arthur on it
    1359-1362, stage 1 from 1363, Arthur's first step 1359. The port (Fixed 62) showed the graveyard 806-998 without the
    cloak, then 6 black frames while `$E0C` cleared all VRAM (64 KiB) and loaded its tiles, plane and CRAM, its picture 2-3
    frames off the arcade's at most events (17 of its 88 picture changes on frames the arcade has none), the cloak in the
    port's 7 on/off steps, black 1717-1725, stage 1 from 1726 (its bg init turns the display on at `$943C`, 4 frames before
    the hold) and the HUD from 1730. Now (port frames - 400 = arcade frames, coin 1100 and Start 1200 in Arcade mode): the
    graveyard's tiles, plane and window keep out of `$E0C`'s VRAM (tiles `$000-$550` and plane B `$C000`; the graveyard's
    tiles go to `$551-$5FF`/`$6C0-$6FF`, its bg to plane B at `$E000` (plane A the same), its HUD to the window at `$D000`),
    which loads 512 words a graveyard frame; the switch is one VBlank (CRAM, plane B to `$C000`, the window over the whole
    screen, empty). Graveyard bg 804, sprites 805, fades 871/935, head 955, cloak 993/996, black part 999 (the cloak art
    over the graveyard is the arcade's sprites, converted by `mkart.py` with the rest); every one of the port's 98 picture
    changes from 990 to 1320 is on a frame where the arcade's picture changes (the steps run off a table of (frame, step),
    the cloak's on and off steps repeated as the arcade's 11 blinks: cloak frames identical in both); the arcade's other
    67 changes in that span are its per-frame animation the port has no pictures for (the swoop, Arthur's fall and
    getting up, his walk). After it: the picture's last frame 1318 in both, the port's stage start black 1319-1331
    (display off while it loads, then 4 frames of its bg init), the HUD on black 1332-1362 (lines 1-3 black but the HUD's
    TIME colours, moved to line 2 meanwhile; plane B uses no pixel of them), Arthur's sprite on it from 1361 (the arcade 1359:
    the port's first sprite table comes 2 frames into play), stage 1 from 1363 in both, Arthur's first step 1359 in both
    (the hold is 2 frames shorter after the opening). After the second clear (the arcade's opening from the last text's
    end R: bg R+3, sprites R+8, fades R+68 and R+132, head R+153, cloak R+191/R+193, black part R+196, the picture's last
    frame R+516, Arthur R+556, stage R+560) the port plays the same (Fixed 72): bg R+2, sprites R+8, every graveyard
    event and the black part on the arcade's frames, the later poses a frame early (the arcade's own run there is a frame
    later than after Start), the picture's last frame R+516, Arthur R+555, stage R+560.

71. **The opening's top score** (`opening.c` `top_digits`, `e0c_digit`): the arcade prints its live top score (`$D0-$D3`, 8
    BCD digits at row 3, columns 12-19, leading zeros blank: `$D0` = 01234560 shows 1234560) in the graveyard's HUD and
    on black; the port's graveyard showed the arcade's 10000 from the frame it was taken from and `$E0C`'s plane a baked
    10000 (tiles `$F` and `$10` only). Now both show the larger of the saved table's best and `$FFC004` (the live top,
    as `score_init`), by the arcade's rule: the graveyard's digits are `mkart.py`'s conversion of the arcade's chars 0-9
    in the window, the black part's are made at the load from the same chars with the pens of `$E0C`'s own 0 and 1
    (tiles `$7D6-$7DF`). Checked with the table's best poked to 123450: 123450 in the graveyard, on black and in play.

72. **The ending's texts, colours and restart** (`ending.c` `text`/`end_tupload`, `mkprincess.py` -> `build/endfont.h`,
    `ending_glue.s` `hook_end_vbl`, `end_restart`). Arcade (from an `arc_start.py 6 0` state, `<$08` = 2): every text is
    written whole on one frame (the first clear's in 2: 31 chars, then 66) in its fg colours by row: "THIS ROOM IS AN
    ILLUSION AND / IS A TRAP DEVISED BY SATAN." colour 8 (red), "GO AHEAD DAUNTLESSLY !" 9 (blue), "MAKE RAPID PROGRES !" 4
    (white); CONGRATULATION 0 (yellow), "THIS STORY IS HAPPY END." 5 (pink); "BEING THE WISE ..." 11 (cyan); "RETURN TO
    STARTING POINT" 5, "CHALLENGE AGAIN !" 11. The port drew them whole too (Fixed 56 had them typed out; they aren't), in
    one colour, with its 26-tile font at VRAM `$6000`, which is Arthur's frame slot: in the first clear Arthur's frame
    upload replaced letters A-P (the text came out "T  S ROO.  S  N ..."; also in the build before this one). Now each
    row is drawn in its arcade colour with the arcade's chars converted as the port's HUD font converts the same colours
    (pen 1 / pen 2 -> line 0 7/6 for colour 0, 15/9 for 4, 12/9 for 5, 3/9 for 8, 14/9 for 9; line 3 15/4 for 11, read from
    the HUD's own tiles), 90 tiles at `$AF00` (`$578-$5D1`, Astaroth's art, unused by the planes and sprites after his
    removal), uploaded at each text's start. The heart takes colour 5's pink (it was red). After the second clear the port
    played only its picture sequence (`$E0C`, ~315 frames); the arcade plays its opening (graveyard and picture, 517 frames):
    now the same opening as after Start (Fixed 70). Not as the arcade: the colours are the nearest the room's palette lines
    allow (pink comes out peach, the grey shade dark blue, cyan lighter), as the port's HUD already has them; the princess's
    purples are still drawn with line 0 (lilac and grey): all 64 CRAM entries are in use during the scene (lines 1-3 the
    room's, including entries that are black and used as black by its tiles; line 0 Arthur's, the HUD's, the lives' and the
    weapon's, each entry used on screen), so she has no palette of her own.
    Fault sweep with these (stages 1-6 x 1P, co-op, Firebrand, seed 1): no fault; updates per frame 1P .993 .914 .981
    .969 .989 .985, co-op .921 .717 .806 .926 .802 .778, Firebrand .991 .915 .964 .930 .970 .968 (stages 1-6); the
    developer launch, a normal Start, the Home start and Firebrand's Quest start all reach play.

73. **The crows' burst the arcade's way round** (`install_burst`; `$493C` stages 1-2, `$1052F4` stages 3-6). The port's
    enemy burst is two sets of frames in its generic tables (`$14B5B0`/`$14C576`, `$239560`/`$23A526`): 37-42 unflipped
    (the pieces at `$14C57A`) and 43-48 h-flipped, the mirror image; the crow's death (type 1; node table `$4E914`/`$105F1C`,
    start nodes `$4E900`) took node 37 when the crow's x was at most Arthur's (`cmp.w 4(a3),d1` / `bls.s`) and node 43
    otherwise. The arcade's burst (`$E85B`) is drawn h-flipped whatever the side (attribute `$54`; Fixed 63). Now node 43
    always. They are the only users of frames 37-42 (the burst tiles are the devils' and skulls' in stage 5, Fixed 63, which
    already draw the flipped way; stage 2's devils and the zombies have their own burst frames, matched). Measured with
    `tools/re/sprite_audit.py` (below): the crows' burst frames 43-47 pair with the arcade's burst pieces at the arcade's
    place (still and moving); the patched code is the `moveq #2,d0` path only (node `$2B` from `$4E902`). Speed (stages 1
    and 5, 1P, seeds 1-3): identical (.993 .994 .994; .989 .991 .986).
    Fault sweep with this (merged with Fixed 67-72; stages 1-6 x 1P, co-op, Firebrand, seed 7): no fault; updates per frame
    1P .994 .946 .982 .959 .994 .989, co-op .914 .603 .853 .914 .892 .834, Firebrand .992 .879 .978 .934 .993 .986
    (stages 1-6; stage 2 co-op is the seed's: Fixed 51's note, the devils on the screen).

74. **Wrong notes in the music after a sound effect** (`glue.s` `sound_scan`, the restore scan at `$11CADC`). The
    music data is the arcade's, note for note: the arcade's sound program (`gg2.bin`, Z80 at 3 MHz, IRQ 4 per frame,
    two YM2203s at `$E000-$E003`, latch `$C800`) was run headlessly for every sound code and its register writes
    logged per IRQ; the port's sound id N is arcade code N-1, one stream tick is one arcade IRQ, and all 29 FM streams
    (every tune and jingle; 11,396 key-ons over 116,339 ticks; `tools/arcade/music_cmp.py`) have the same pitches (to
    0.1 semitone) on the same channels at the same ticks; the only differences are writes that spilled into the next
    IRQ in the Z80 run, the port's fixed +4 total level, and the YM2612's fnums for the same notes (the same with and
    without `attenuate_music`). The music doesn't use the YM2203s' SSG (no non-zero SSG volume in any music code). The
    wrong notes came from the driver: after a PCM effect (it marks channel 6's registers, `$11CA40`) or an FM jingle
    in slots 1-3 ends, it re-sends the music's cached registers in ascending order, `$A0`-`$A2` before `$A4`-`$A6`.
    The YM2612 has one latch for `$A4`-`$A6`, taken by the next `$A0`-`$A2` write, so each restored channel got the
    block and high fnum bits of the last `$A4`-`$A6` written by anything, and held that pitch until the music's next
    note on the channel. Stage 1, a lance thrown every 40 frames (the YM2612 writes read back from the Z80's queue in
    Genesis Plus GX, one state per frame, 450 frames): channel 6 played B2 or F2 +7 cents for B1 and F#2 -20 cents for
    C2 in 95 frames. Now the scan sends each requested `$A0+c` or `$A4+c` as the pair `$A4+c`, `$A0+c` and no channel
    is off (same run, 0 frames); the game RAM at the end is the same apart from a sound driver counter and the stack, and
    `tools/re/test_sound_scan.py` checks both scans against a model of them (300 random cases).

75. **Stage 1's background colours and water** (`tools/patch_gng.py` after the weapon y; `glue.s` `water_cycle`). The
    background is plane B, one 588-tile set (`$C062`) and the palette at `$13FE2` (loaded at `$3B0`), lines 1-3; the map
    (`$19E64`) holds each entry's line. `tools/arcade/bg_capture.py` records the arcade's stage 1 map and palette and
    `tools/re/s1_bg_compare.py` lines the two up pixel for pixel: of 38 background entries, 12 were not the nearest
    3-bit colour of what the arcade shows there, each one step low in a channel (the 4-bit values rounded down). 11 are
    now the nearest: line 1 3, 6-10; line 2 2, 3, 10; line 3 2, 3. Line 3's 9 stays (215 px; the HUD timer's second
    colour). Line 2's three are also drawn by sprites (the zombies' dirt, the forest's flying knights; the arcade's
    sprite colours for them round to the new values too) and the HUD's "PLAYER 1"; no sprite uses line 3 in stage 1
    (sprite tables read every 3rd frame over the whole stage, graveyard to the Unicorn). Mean error per pixel (RGB,
    0-255) against the arcade: line 2 19.9-21.9 -> 9.7-12.0, line 3 12.9-14.5 -> 8.7-10.6, line 1 after the last
    puddle 15.1 -> 8.4. The other two entries were the water: the arcade sets colours 42-44 every 8 frames from tables
    by its frame counter's bits 3-4 (`$EE00`, stage 1 only; 42/43 alternate (0,8,10) and (0,5,9) in 4-bit, 44 is
    (6,10,12) three phases in four and black in one). Those are the port's line 3 13/14 (only the water tiles 253-256
    use them) and, for 44, black: the tiles were converted at the black phase. `water_cycle`, at stage 1's sprite-table
    DMA (`$644`, in VBlank), writes 61/62 by the VBlank count's bits 3-4; the 15 crest pixels of tiles 253-255 now use
    line 3's 15, which is already the crest colour ($CA6) but also the HUD timer's, so the crests stay lit (the arcade's
    are lit 3 frames in 4). Stage 1 over 12,000 frames with deaths, the map and game over: the cycle values only ever
    appear with stage 1's palette in CRAM.

76. **Big Men at a floor's edge** (`bigman.s` `bm_nofloor`/`bm_turn0`/`bm_turn1`, `install_big_man_edge`; hooks `$11B800`,
    `$11B35C`, `$11B4A0`, `$11B493`; arcade `$D0A4`, `$D047`, `$D144`, `$D13B`). The arcade's edge probe (`$D0A4`: the floor
    2 px below, `$8CA7`; every 16 frames while walking, every step while facing Arthur) notes the facing of the first step
    over an edge (`$14`, `$F` = 1) and keeps it until a floor is found again (`$F`, `$15` cleared). Walking (sub-state 0) it
    turns round when it faces that way (`$D047`); facing Arthur (sub-state 1, Arthur 10 px below to 45 above it) it backs
    off the edge toward him once (`$15`) or, with the edge on his side, stands (`$D144`); Arthur leaving its height clears
    `$15` (`$D13B`). The port's (`$11B798` and callers; slot +37/+38/+39 = `$F`/`$14`/`$15`) rewrote +38 at every step over
    the edge, turned while walking only on every second check (+39 used as a count), in sub-state 1 had both tests the
    wrong way round (it never turned and walked on over the edge) and cleared +37 instead of +39. Measured with a life
    start on stage 2's first Big Man's ledge (restart entry `001450A0`, arcade `401450A0`: x 5200, y 159; the frame
    counters lined up with `rng_lag`; `tools/lockstep/slots.py` / `cmp_slots.py`, update for update), 900 frames: before,
    the port's Big Man walked past the ledge's end at x 5174 where the arcade's turns (frame 51), and fired its first shot
    away from Arthur (left from x 5158; the arcade's right from 5190, frame 83), apart from frame 51 on; now the Big Man
    (state bytes, x, y, facing, the edge bytes) and its nine shots are identical on every frame.

77. **The Big Men's shots** (shot type 3; `$AD4C`; arcade projectile type 3: made by `$D1FD`, moved by `$FEBE`). The shot
    pool's type 3 (drawn by `$B042`: the sprite audit's "`$B110` frames 1-4") is the Big Man's: `$D1FD` (in the type-10
    handler `$CF36`; the port's `$11B908`) makes it at x +-16 sideways in sub-state 1 or at y - 8 going down in sub-state 2
    (Arthur within 10 px in x and below it; 10 frames into its 30-frame stop, `$D281`), 2 px a frame (`$5D9B`), and `$FEBE` moves and animates it
    and takes it out only out of range (`$8F62`: 128 px past the screen's sides, 64 below); type 3 has no floor test
    (types 4 and 10 have, `$FEA3`). The port's pool pass (`$ACB8`) also took it out after 120 frames (+33): on the ledge
    the arcade's shots flew to x 5458 and 4942, the port's stopped at 5444 and 4966. Now out of range only: the nine shots
    of the ledge start are made and gone on the arcade's frames at the arcade's places (5458, 4942). The down shots (life
    start under the ledge, `00145A50`: x 5210, y 79; 600 frames) fall through the floor below as the arcade's and were
    already identical (108 frames of flight). The frames (audit, 420 frames): poses 769-772 (frames 1-4: the arcade's
    `$1F0`/`$1F8`, 4 frames each, mirrored by direction) all at the arcade's place, 244 moving pairs, the pose changing
    on the arcade's frames. Kept: the port takes a shot out when stage 2's art bank changes (`$FFB028`, camera column 349),
    as its pictures go with it.

78. **Big Men drawn whole** (`bigman.s` `bm_piece_x`, `$AFB2`; the type-10 builder `$AF1E`/`$AF4A`, records `$125620` via
    `$123B3E`). Fixed 21 swapped the 16 px halves of frames 1-30 for the final room's flames, but the same records draw the
    Big Men of stages 2 and 5, whose pieces are the arcade's art placed as the original records place them: every Big
    Man since was split down the middle, its left half on the right (the audit, ledge start, 420 frames: all 11 poses 16 px
    off, left or right, none at the arcade's place). The swap is now made in the builder in the final room only
    (`$FFC512` = 6), the records are the original's: every Big Man pair at the arcade's place (513 still, 439 moving), and
    the final room's sprite table (1,200 frames, flames on 339) identical to the old build's on every frame.

79. **Stage 2's windows, any number open** (`bossart.c` `win_step`/`win_vblanks`/`win_ring`/`win_chan`, `bossart_glue.s` `win_chan_hook` at `$C35D8`;
    supersedes Fixed 61's two slots).
    The arcade's windows are bg tiles: `$B457` writes the step's 2 x 2 tiles at the cell kept in `$18,X` (the devil's x - 16,
    y when the window opens, `$B432`/`$8DD2`), so there is no limit of its own: every window stays as last written (a dead
    devil's too, Fixed 69) until its ring column is written over or the screen is redrawn. The port had two 16-tile slots,
    one per window, so a dead devil's open window closed when two live windows needed both. Now a pose's 16 tiles go into
    a region and every window showing that pose points at it (8 window records instead of 2; the pose uploaded at the
    vblank of each step to it, 512 bytes as before): R0 `$6AC`-`$6BB` and R1 `$6BC`-`$6C7` + `$5F4`-`$5F7` (Fixed 61's;
    `$5F4`-`$5FB` is otherwise written only by the unreachable `$6434` and by the Satans' star in stages 5-6), and R2
    `$5F8`-`$5FB` + `$6D0`-`$6DB` for a third pose at once. `$6D0`-`$6D7` and `$6D8`-`$6DB` are the object-art streamer's
    channels 2 and 4 (`$1169B8`, reached through `$C35D8` -> `$11692E` from every stage loop, its requests set by `$1168E2`):
    the second item slot (`$FFCEA0`, frames from `$29CA00`) and the stage-end key (`$FFCC20`, run only once the boss is
    dead, from `$E085C`); channel 0 (`$F300`) is the first item slot. While those objects are absent the channels hold
    their frame 0 (loaded `$FF97C2`/`$FF97C4` = asked `$FF97C8`/`$FF97CA` = 0). R2 is taken only then, and `win_chan`, put
    before the streamer at `$C35D8`, gives it back as soon as one of them is live or asked for, or no window uses it: its
    windows are first pointed at R0/R1 (holding or taking their pose) or closed (a live devil's shows again at its next
    step, a dead one's is given up, Fixed 69's behaviour), with the interrupts off, then the channels' loaded frames are set
    to `$FFFF` so the streamer loads them again in the same update. Without R2, a third pose takes a dead devil's
    window's region (it closes, as before Fixed 79). Random runs never spawned the second item slot or the key in stage 2
    (12 runs of 9,000 frames, 1P and co-op: the first item slot live in 11, the second and the key in none), so the case
    was forced: in the window run below with the first devil removed 7 frames into its closing (`KDELAY=7`: 312,7 left at
    F4 in both games, f163 / r165, until the redraw f511 / r517) the second live window at F2 makes three poses (r229) and
    takes R2; an item put into the second slot at r231 (a copy of a live first-slot item from a 1P run): R2 is given back
    in that update, the window goes closed on that frame and shows F4 at its next step (r234), the tiles `$6D0`-`$6DB` are
    the streamer's frame 0 again on the same frame, no window ever showed them, no fault; with the item live a third pose
    then closed the dead window (r248); without the item R2 is taken and given back twice (r229-r234, r248-r253), the
    dead window at F4 throughout, `$6D0`-`$6DB` back at frame 0 after each. Firebrand's and player 2's tiles are `$690`-`$69F`
    (`p2.c`, `firebrand.c`), the life start's load at `$4F4` writes `$6C8`-`$6CF` only (128 words), neither in R0-R2. And as the arcade's
    window tiles are in its terrain map, a step now writes the same four cells of the port's ring (tiles `$F0`-`$FF`,
    attribute `$87`, at the cell kept when the window opened). Forced case, side by side from the checkpoint (both 30
    frames after the restart, walking right, `arc_windows.py` / `port_windows.py` with `LOAD`): the first window devil
    removed on its closing's first frame (`KILL=1`): arcade window 312,7 open (F6) from f143, two live windows 308,11
    (f203-f249) and 310,9 (f220-f266) open and close, 312,7 stays open until the death's redraw (f511). Port before: the
    dead window closed at r225 when 310,9 took its slot; now open from r147 to the redraw (r516; its F6 2 frames later than
    the old build's r145, an update lost to the frame pacing), the live windows' poses within a frame of the old build's
    (r205-r270). `KILL=-1` (every window devil removed on its closing): arcade and port both
    keep all three open to the redraw (f511 / r512). The terrain ring along that walk (`ring_sweep.py`, 34 cameras): 78
    cells differed without the ring writes, 46 with them (the rest: Fixed 80).

80. **The terrain map's other cells, from the arcade's world** (`terrain.c`, `mkworld.py` -> `build/world.inc`; Fixed 65's
    "what's left"). The arcade's world map is in gg5 (banked at `$4000`): page 2 `$4000` + (screen row << 5 | screen column)
    holds a screen's id (the stage-start pointer `<$6C` and the restart entries' `$4000 | y << 5 | x` point here; the column
    and row writes step it, `$81E7`, `$828E`), page 2 `$4200` + 2 x id the base of its blocks in page 1, page 0 `$4000` + `$40`
    x id its 8 x 8 block numbers (column by column, bottom first; `$82AA`, `$8262`), and a block is 2 x 2 cells (tiles at
    + (column & 1) x 2 + (row & 1), attributes 4 bytes on): 32 x 16 screens of 16 x 16 cells, 512 columns by 256 rows,
    wrapping as the screen pointer does. Decoded in Python, it holds the port's seven maps byte for byte (all 34,816 cells);
    the cells outside them were the port's tile 0 / attribute `$C0`. `mkworld.py` writes the world's tables (15,568 bytes,
    in the `.intro` data at `$350000`), and `terrain.c`'s column and row writes read every cell from it (the screen looked
    up once per 16 cells, the block once per 2; quicker than the old per-cell search of the maps: the first version, maps
    first and the world for the rest, made stage 1's start hold 3 frames longer; now the update counter is identical frame
    for frame to frame 1,700 of dev launches of stages 1, 3 and 5 co-op, and the code blob is 68 bytes smaller). The two
    rings byte for byte (`tools/re/ring_cmp.py`, all 1,024 cells, "floor" = a different answer to Arthur's floor probe,
    the port's rule `$860C` with its table `$14A6E`), at the stage starts (both 30 frames after the restart), before ->
    after: stage 1 528 (18 floor) -> 195 (0), stage 2 264 (0) -> 0, stage 3 371 (15) -> 195 (13), stage 4 256 -> 0, stage 5
    8 -> 0, stage 6 256 -> 0; along walks right from the starts, at every camera multiple of 16 both reached
    (`ring_sweep.py`): stage 1, 78 cameras, 40,160 (388 floor) -> 4,095 (0); stage 3, 49 cameras, 14,365 (243) -> 3,285
    (219); stage 5, 26 cameras, 1,104 -> 0; stage 6, 13 cameras, 3,328 -> 0; stage 2 from the checkpoint, 34 cameras, 8,791
    (10) -> 46 (9, with Fixed 79's window cells). What's left is the arcade's, not its world: at a stage start with the
    camera at column 0 (stages 1 and 3) its stage draw (`$726E`/`$80A0`) leaves columns 0-12 with other data in rows R - 8
    .. R - 1 and R + 17 .. R + 23 (195 cells; stage 3's 13 floors are Matching (audited)'s "Stage 3's collision map above
    the start"), which stay until those columns are written again (all of stage 1's: below row 0 and 17 rows up, never
    on the screen or under Arthur); a few column writes in stage 2 leave rows R + 15 .. R + 23 of the arcade's column as its
    buffer had them (12 cells at cameras 5200 and 5280, 15 and more rows above the screen's bottom); and at 2 of the 34
    cameras the port's sample (taken at the frame's end) fell between its camera update and its ring write in an update
    running over a frame's end (one column, the next sample equal).
    With 79: no faults in stages 1-6 x 1P/co-op/Firebrand (`bench.sh`, seed 1); in-play updates per frame, 1P, seeds 1-3,
    before -> after: stage 1 0.994/0.992/0.994 -> 0.991/0.990/0.993, stage 2 0.919/0.946/0.922 -> 0.908/0.952/0.924,
    stage 3 0.979/0.978/0.983 -> 0.981/0.982/0.986, stage 4 0.969/0.927/0.973 -> 0.970/0.932/0.985, stage 5
    0.989/0.990/0.984 -> 0.992/0.993/0.991, stage 6 0.985/0.961/0.989 -> 0.985/0.963/0.988; stage 2 seeds 4-7 1P
    0.967/0.906/0.959/0.938 -> 0.966/0.931/0.967/0.942, co-op seeds 1-7 0.713/0.689/0.700/0.691/0.718/0.684/0.706 ->
    0.708/0.686/0.689/0.700/0.713/0.717/0.684 (mean 0.700 both; random input: the runs part once anything differs).
    With R2 given back to the streamer (79): no faults in stages 1-6 x 1P/co-op/Firebrand (seed 1); stage 2 1P seeds 1-3
    0.919/0.952/0.922, co-op 0.721/0.670/0.708.

82. **Co-op speed: the slot loops and per-update copies in fewer cycles** (`speed.s`, `install_speed`; `p2.c` `draw_hud`;
    measured with `tools/re/uc_profile.py`, PCHIST and a per-slot attribution by type and on-screen flag). The arcade runs
    every frame; the port's co-op took longer than a frame in most updates of stages 2, 3, 5 and 6 (stage 2: an update
    with its sprite build ~270-310 lines on the probe build, `tools/re/probe_rom.py`, so updates alternated with a
    skipped build). On the stage 2 co-op snapshot the update was ~220 lines (Unicorn estimate), and a third of the enemy
    passes went to live enemies off the screen that change nothing: each one cost 600-1,200 cycles of jumps, context
    copies and 11-register saves (stage 2's nine waiting window devils, type 10, and six crows, type 1; stage 3's crows
    and the type-5 handler's slot copies; stage 6's dragon and type 8). Now, with the same RAM and VDP writes:
    - The enemy passes (`$69A2` stages 1-2, `$1055D4` stages 3-6): the handler is picked from the type in one table
      (was 4-5 jumps through `$114C90`/`$114BF2`, `$6A88`, obj_dispatch and its stub, or a pushed address and `rts`),
      entered with the same d0-d4 and flags; the odd-frame step (`$114CDA`/`$114D50` -> `$114D76`, which only does
      anything for type 13) is a type test; runs of empty slots are stepped over in a tight loop (their slot-counter
      writes and the `$FFC9D8` clears repeat what the next live slot or the pass's end writes).
    - Waiting crows (type 1, `$44FE` / `$10505C`) and type-10 enemies (`$11B1BC`) off the screen: the handlers' answer
      (d0 = 0, nothing else changed) from their own state tests, without the register saves; from the passes' tables
      directly, with their preambles' writes to the type block at `$FFC620`/`$FFC630`/`$FFC634` and no calls.
    - The type-5 and type-8 handlers' 64-byte slot copies (`$3448`/`$34B4`, `$714C2`/`$714E0`) unrolled; the stage
      loops' 128-byte `$FF9600` copy unrolled; the HUD rows (`$11AE4E`, 73 VDP words a frame) without dbf loops.
    - The stage 1-2 sprite build (`$B258`) takes empty and off-screen slots straight to the next; eight slot loops test
      the on-screen flag before the live flag (`$9C5A`, `$A1BC`, `$71D8E`, `$106530`, `$106C44`, `$114588`, `$11525A`,
      `$11C304`; most live objects are off the screen, both branches go to the next slot); the multi-piece builder
      `$705C8` works out each object's part of the camera tests and its attribute fix-up once.
    - Maximo's HUD digits without a divide; the co-op test inline.
    Maximo's context swap (~12 lines: 248 bytes exchanged twice an update, already straight-line movem) and his control
    block (~14: the engine's player routines a second time) are unchanged.
    Estimate (Unicorn, seed 1 frame 2,700, 8 updates, before -> after): co-op stage 2 223.2 -> 202.7 lines, stage 3
    194.4 -> 181.6, stage 5 246.7 -> 232.6, stage 6 226.4 -> 212.7; 1P 189.8 -> 170.0, 187.7 -> 175.4, 192.4 -> 179.3,
    174.8 -> 163.5.
    In-play updates per frame (`tools/lockstep/bench.sh`, seeds 1-3, the merged head d702966 before -> after): co-op
    stage 1 0.938/0.884/0.904 -> 0.961/0.960/0.977 (mean 0.909 -> 0.966), stage 2 0.713/0.669/0.671 -> 0.823/0.839/0.810
    (0.684 -> 0.824), stage 3 0.832/0.826/0.872 -> 0.887/0.891/0.940 (0.843 -> 0.906), stage 4 0.931/0.951/0.899 ->
    0.970/0.974/0.966 (0.927 -> 0.970), stage 5 0.797/0.851/0.887 -> 0.917/0.909/0.959 (0.845 -> 0.928), stage 6
    0.758/0.838/0.812 -> 0.876/0.934/0.927 (0.803 -> 0.912); 1P means (stages 1-6) 0.991 0.929 0.978 0.956 0.992 0.977 ->
    0.996 0.943 0.992 0.963 0.997 0.982; Firebrand 0.988 0.925 0.967 0.953 0.982 0.982 -> 0.996 0.929 0.987 0.961 0.996
    0.990 (random input: runs part once a frame's timing differs; Firebrand stage 2 seed 2 0.950 -> 0.873 and seed 3
    0.928 -> 0.993 are such runs). No faults in stages 1-6 x 1P/co-op/Firebrand x seeds 1-3 (54 runs, `$FFC9DC` 0
    throughout).
    Checked: `tools/re/test_ab.py --vbl` (the VBlank counter advanced each update, so the alternating halves of the
    passes both run; random input on both pads; the render skip off, `fs_last` set) against the merged head without
    this work, from 120 snapshots (stages 1-6 x 1P/co-op/Firebrand, seeds 1-3, frames 2,100-3,300, from the merged head d702966): the whole of RAM
    (`$FF0000-$FFFBFF`) and every VDP write identical after every update over 300 updates each, and over 150 with the
    build skipped every other update (`fs_force`). The p2.c change moves the patch's constant data, so a DMA from it is
    compared by the words it transfers (`--dmadata`, new) instead of its source address; RAM holds no pointer into it.
    Each step was also checked against the one before (20-120 snapshots, 40-60 updates).

83. **The opening's picture, every frame the arcade's** (`opening.c` `ib_sprites`, `mkart.py` -> `ib_frame`, `ib_frame2`,
    `ib_lists`, `ib_tiles`; hooks as Fixed 70). The arcade's black part (999-1318 after Start at 800) is its sprites
    only (the Satan, the princess, Arthur; colours 0 and 2) over the HUD's top rows; the port showed `$E0C`'s plane
    picture, 28, 11 and 24 steps for the swoop, the fall, getting up and the walk where the arcade's picture changes
    every frame. Now `mkart.py` runs the arcade on to 1318 and converts every frame's sprite list: 100 pieces (400 tiles,
    loaded at `$001` while the graveyard shows, with an empty plane B at `$C000`), 128 distinct lists, a CRAM of the
    HUD's entries and the two sprite colours (the bg's entries are free there); each frame writes its list.
    Measured frame by frame against `tools/arcade` renders (non-black masks): 999-1318 identical on 320 of 320 frames
    (was 129; mean IoU 0.928 -> 1.000), the arcade's 157 picture changes there all on the same frames (was 91, none
    elsewhere). `$E0C`'s data is no longer used. After the second clear (`tools/lockstep/port_end.py`-style run against
    an `arc_start.py 6 0` state with `<$7F` = 1, `<$08` = 2, `<$0B` = 0; R = the last text's end) the arcade's black part
    is a frame longer and not Start's: the cloak's blinks follow its frame counter's low bits (frames 13-18 on, off,
    off, on, off, off; after Start on 13-16), from the wings every picture comes a frame later but for Arthur's bounce
    after the fall (in step, frames 165-179); `ib_frame2` is that order (Start's lists). Its graveyard: the bg at R + 2,
    the sprites at R + 3 (the port's at R + 8; the first tick, which starts the music `$3A`, now comes after the
    sprites' frame), the fades, the head and the cloak as Fixed 70; the player's score in the HUD is the live one (it
    showed 0; the arcade's 50,000 there). Measured over R .. R + 558: the arcade's 170 picture changes, the port's 169,
    all on the arcade's frames (was 171, 158 of them). Not as the arcade: in the second clear's graveyard the arcade
    draws the bg with the final room's palette for 6 frames (R + 2 .. R + 7: red ground) before stage 1's (the port's
    is stage 1's from the start); the Satan carrying the princess and Arthur's walk stand 1-4 px apart on 47 of its
    frames there (the objects' sub-pixel parts kept from before: Start's positions are drawn).

84. **The stage start after the opening: the HUD on black from the arcade's frame, Arthur and the music on theirs**
    (`opening.c` `hud_show`, `stage_clear`, `intro_cram_load`, `intro_cram`, `bg_off`, `hide_buf`, `intro_hold`;
    `bossart_glue.s` `stage_clear_hook` `$2E2`, `cram_hook` `$3B8`, `intro_cram_hook` `$3C6`, `bg_off_hook` `$940A`,
    `hud_flush_hook` `$588`, `b12_tick` `$B12`, `music_hook` `$B470`; `pad.c` `stage_hold`; `glue.s` `hook_sat_dma`).
    Arcade: the HUD (TIME, lives, the weapon's box) over the last picture at 1319, alone on black 1320-1358 (the
    lance in the box's colours until 1321), Arthur 1359 (y 160, 162 from 1361), the stage 1363, sound `$30`/`$2B`
    (the stage's music) at 1318/1320. The port (Fixed 70) turned the display off for its game start (`$2CC`: the
    64 KiB VRAM clear, the loads, the bg init's own display off at `$940A`): 1319-1331 black, its HUD from 1332
    (TIME's digits from 1333, the box with Arthur), Arthur 1361 (pace.c held the first two sprite tables: the first
    update began late in the hold's last VBlank, its last update before the stage start), music from 1328. Now the
    opening's last frame shows the arcade's HUD chars (rows 2-5, 26-29 -> plane A rows 0-3, 24-27) in the port's own
    colours (each arcade fg colour's pens as the port's HUD tiles have them; line 0 stage 1's, ROM `$13FE2`; the TIME
    digits with line 2's 9 and 15, copies of line 3's), its tiles at `$690-$6C7`/`$6D0-$6DB` (written by nothing in the
    stage start, its hold or play), over the last picture's sprites converted to line 0; the next frame the HUD alone.
    The game start keeps the display on: its clear spares the HUD and what the loads after it write whole, its CRAM
    load (`$3B8`) puts lines 1-3 aside (all black but line 2's 9 and 15) and plane B shows plane A's table (v scrolls
    sent to unused column entries) until the bg init's end (`$943C`), whose display off is skipped; the HUD upload
    (`$588`) puts the TIME digits on line 2 as they go up, so the port's own HUD replaces this one with the same picture.
    The stage's music starts at the load's start (the stage start's `$8812`, sounds `$30`, `$2B`, then skipped) and the
    sound driver ticks at every VBlank the load's copies see (`$B12` in 64-word pieces); the load's frames are counted
    by the VBlank handler (interrupts at level 6 meanwhile: `vb_isr` only counts and latches the pads) and the hold
    ends 35 frames after the load's start, the frame counter in play as before; the first update then starts on a
    VBlank's first line and holds only the stage start's table once, so the sprites show from the first frame of play
    at every stage start (pace.c's state set at the hold's end). Measured (Start at 800 / 1200 in the port): 1319-1363
    identical in mask on 45 of 45 frames (was 4), HUD 1319, lance 1321, Arthur 1359 (y 162 from 1361), the stage 1363,
    Arthur's first step 1359 (x 97, 97, 98, ... as the arcade's), the counter in play equal to before; the music from
    1321 (was 1328). After the second clear: the HUD R + 517, Arthur R + 557, the stage R + 560, as the arcade's (the
    lance as it is: its palette was set before). Not as the arcade: the arcade's bonus life of the ending's 50,000 shows
    at R + 556, the port's a few frames into play (Fixed 58).

85. **The princess in her own colours** (`mkprincess.py`, `ending.c` `prin_cram`, `ending_glue.s` `hook_end_vbl`). Fixed 56/72
    drew her with Arthur's palette line (lilac, grey) because every CRAM entry looked used; counted per pixel from the
    final room's VRAM, CRAM and scroll during the scene, no plane pixel on the screen uses palette line 2 (the room's
    tiles use lines 1 and 3, the HUD and the texts lines 0 and 3) and no sprite but hers does. Her walk and embrace
    pieces are now converted with the arcade's sprite row 2 (pen p -> line 2 entry p + 1, 4 bits a channel halved, as
    the port's other colours) and line 2 is loaded with the scene's tiles; the opening after it loads its own CRAM.
    Checked: frame by frame against the same run with line 0, every pixel that differs is in her sprite's box (x 141-250,
    y 148-177), the room, the texts and the HUD unchanged. Her and the embrace's x/y came from `$FFA200`/`$FFA202`,
    which hold 141/0 in the final room as the developer menu launches it (both off the screen, the embrace invisible):
    they come from the camera at `$FF9100`/`$FF9102` (7936/2560 there, as the arcade's `<$9C`). The heart keeps line 0's
    nearest (peach; no pink in row 2).
    Fault sweep with 83-85 (stages 1-6 x 1P, co-op, Firebrand, seed 1): no fault; updates per frame 1P .991 .916 .972
    .969 .992 .985, co-op .938 .713 .832 .931 .797 .758, Firebrand .993 .898 .969 .926 .987 .975; the developer launch,
    a normal Arcade Start, the Home start and Firebrand's Quest start all reach play.
86. **A third Red Arremer on screen no longer stops the game** (`patch_gng.py`, the big-art lists). The port's enemy
    art lists (`$114318`, `$11C304`, `$11C458`: type 5, the Red Arremers, into the two streams `$FFC6C4`/`$FFC6F4`;
    type 4 into 4 entries, type 2 into 3) jump to the fault trap (codes 15, `$83`, `$88`) on one entry more than they
    hold, freezing the game. Found when Firebrand's bot climbed stage 6's tower with three Arremers on the screen
    (frame 3496 of its path: fault 15, the timer stopped, Firebrand hanging in his knockback). The extra enemy is
    skipped for that frame (its art not streamed) instead; Arthur can meet the same three. Checked: the same path
    goes on without a fault, the knockback lands and the death and restart follow.

87. **After the second clear, the graveyard's first frames in the final room's colours** (`mkart.py` `isc_cram_room`,
    `opening.c` `ISC_ROOM_FRAMES`). The arcade draws the graveyard's bg on the scene's 4th frame and changes its palette
    on the 9th, so the graveyard shows in the final room's bg palette for 5 frames (grey mountains, red ground, the hill
    dark); the port showed stage 1's colours from the first. Now `mkart.py` boots the arcade to the final room, forces
    the end and takes the room's palette 6 frames into the scene; each CRAM entry the graveyard's bg uses takes the
    room's colour for that (palette, pen), the one entry the sprites share keeps its own (25 entries). Measured
    frame by frame (`fb_arc.py` / `fb_port_end.py` / `fb_cmp.py`, an `arc_start.py 6 0` state with the end forced):
    the 5 frames identical in mask (IoU 0.57 -> 1.000), 2580-3060 mean IoU 0.982 -> 0.987, colour agreement 0.9968 ->
    0.9989; after Start nothing changes. Stage 1 1P bench clean, Firebrand's ending into Plus as before.

88. **Stage 5's Big Men: their art and their hit points** (`bmart.c`, `bigman.s` `bm_attr_hook` at `$AFF4`, `glue.s`
    `hook_sat_dma`; `$11BA30`). Reported on V0.6: the stage 5 Big Men looked like sprite glitches and couldn't be killed.
    (1) The type-10 builder draws every Big Man from the frame records (`$125620` via `$123B3E`), whose pieces point at
    tiles `$320`-`$3F3`; stage 2 loads the Big Man's art there (the port's copy at `$123BA0`), stage 5 never does (its
    enemy burst and other art sit there), so its Big Men were drawn from that art. Now, in stage 5 only, each pose drawn
    takes one of three 16-tile VRAM slots stage 5 doesn't use (`$690`, `$6A8`, `$6B8`: the window table's space, the
    window being off in play; zero through the whole tower and the room in VRAM scans), its four pieces uploaded from the
    ROM copy with the sprite table that first shows it, and its pieces point there. The slots are what the mode leaves
    free (scanned per mode): Arthur alone `$690`, `$6A8`, `$6B8`; co-op `$6A8`, `$6B8` (Maximo uses `$681`-`$69B`);
    Firebrand `$6B8` (his wing columns, fire icon and map marker are `$690`-`$69F`, his frames fill the rest to `$6B7`);
    a pose with no slot borrows the first slot's (a Big Man in another pose). Checked in Firebrand's stage 5 proof: his
    weapon-box fire icon intact at all 472 samples, the Big Men drawn from `$6B8`. (2) The Big Man's set-up gave it the arcade's 10 hit points (`$CF36`'s `+$26`, 10 in stages 2 and 5) only at
    stage index 1; in stage 5 `+11` stayed 0 and every hit took it to 255, 254, ... Now every stage but the final room
    (whose type 10 are Astaroth's flames). Measured: the stage 5 pose rendered from VRAM is the Big Man (it was the burst's
    pixels); a stage 5 Big Man takes 10 lance hits, dies and gives 500 points (V0.6: 0 -> 212 after the first hits).

89. **Stage 2's buildings no longer flash** (`glue.s` `water_cycle`). Reported on V0.6. Stage 1's water colour cycle
    (Fixed 75: colours 61 and 62 every 8 frames) is hooked on `$644`, which is stage 2's sprite-table DMA too, where line
    3's 13 and 14 are building colours: they swapped every 8 frames all through stage 2. Now stage 1 only: stage 2's CRAM
    changed 545 times in 5,000 frames, now once (an unrelated load); stage 1's water cycles as before.

90. **Stage 2's stepping stones in their arcade art** (`mkart.py` `stone_tiles`, `bossart.c` `stone_load` from `pad.c`
    `stage_hold`, `bigman.s` `stone_attr` at `$A226`). Reported on V0.6 as frozen platforms. The type-4 platforms over the
    water (x 6032-6608) were drawn from tile `$7F0`, line 0, which the start of play fills with art of the port's own
    (a pale slab, like ice); the arcade draws them with its stone sprites `$170`/`$171` (colour 3, greys). Now those are
    converted into 8 tiles in stage 2's line 1 greys, loaded at `$48C`-`$493` (unused all through stage 2: VRAM scans of a
    whole stage 2 run and two town walks) at every stage 2 start, and the platforms drawn from them. Their movement was
    already the arcade's: all three wake together when Arthur reaches x 6018, in both games, and bob from then on.
    With 88-90: no faults in stages 1-6 x 1P/co-op/Firebrand (`bench.sh`, seed 1), updates per frame as before.

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
- **Red Arremers** (type 5, `$B64E`; port `$3420`, states `$4214`/`$364A`/`$3588`, all stages): the port's handler is a
  line-by-line transliteration of the arcade's, checked routine by routine (state 0's wake-ups `$B67D`/`$B6D5`/`$B734`,
  state 1's seven sub-states `$B802`, `$B9FC`, `$BB2A`, `$BBA5`, `$BC20`, `$BC76`, `$BD4D` with the moves `$B7AA`/`$B85A`,
  timers `$B936`/`$B957`/`$B975`/`$B9E7`, the reach test `$B9C7`, the dodge `$B87E`, the swoop sines `$4140`/`$41C0`, the
  hit flash `$B901`, the shot `$BB57` as the port's type 7) and every table: the speeds (`$B7D2`, `$BA21`, `$BC02`,
  `$BD41`, `$BE8A` = `$502C0`), amplitudes `$BA2D`, rest times `$BBEC`, the rank windows `$B8C8`/`$B996`, the return
  states `$BB93`, and the four rank-indexed timer sequences (`$4A00`, `$4A34`, `$4A47`, `$4A61` = the port's linked lists
  at `$50164`, `$50226`, `$50256`, `$50114`, including the arcade's reads of the next byte, end marker 0 too). It draws no
  random (the arcade's choices come from the frame counter plus the slot counter). One table differs: the dodge window
  in sub-state 5 is two of the arcade's jump-table entries read as numbers (`U` still `$BC8D`: `$BC99`/`$BCD9`); the port
  has `$BCA9`/`$BCE9`, which differ only for Arthur 17,239-17,254 px away. Lockstep (stage 1, the same walk to x 1300,
  then 2,600 frames of random fire/jump/crouch/short walks; the port's skipped updates taken out): the Arremer and all
  131 frames of its shots identical frame for frame through its wake-up, walking, flying, firing, both swoops, the lance
  hits, death (frame 1636) and removal (1737). The devil-to-Arremer change (`tdevil.c`, `$B245`, forced with the life
  timer in both games): the arcade zeroes all three state bytes as `tdevil.c` does, and both games then flicker in
  state 0/2 for 240 frames per step (530 frames in the arcade, 532 in the port with the devil spawned an update later).
  Stage 3's two Arremers at the dragon: Fixed 40.
- **Arthur:** knockback arc (identical frame by frame), 120-frame invincibility (`$00AD`/`$FFC309`), death in
  boxers, ladders (grab zone, 1.375 px/frame, top/bottom sequences), ledge falls, throw lock 14 frames,
  crouch entry, landing keeps the y fraction in both.
- **Timer spawns at a stage start** (stages 2, 3; `tools/lockstep`, both games anchored on the frame the camera reaches the
  restart point, Arthur's first possible step one update later in both): the stage's spawn generator (arcade slot `$06C0`,
  counter `$06CF`; port `$FFC740`, `$FFC74C`) is set up and its counter loaded with 100 three updates after that in both;
  the first timer spawns come 104 (stage 2, type 2 at x 3656) and 74 (stage 3, type 11 at x 176) updates after it in both,
  then every 151 updates. The 3- and 4-update gaps seen before came from the old alignment and the spawner order (Fixed 36).

- **The shared random in the stage 5 boss room** (`tools/lockstep/arc_rand.py`, `port_rand.py`): every draw of the second
  random (`$68F9`, Fixed 31) by frame and caller, both games started in the room at a life start (the stage 5 restart
  entry pointed at the room in both: the arcade's RAM table `$6CED`, a test copy of the port's `$1040CC`), the frame
  counters lined up (`rng_lag`): standing where the Satan wakes at once, 52 draws over 1,600 frames, and walking in from
  x 7100 so it wakes on frame 151, 51 draws: identical in both (frame, count, state). The crows (type 1, `$A66F`) draw
  three in both on the update after their set-up at the life start and none as the Satan wakes; the rest are the Satan's
  (`$C066`, `$BFD2`, `$C147`). The old note (the port's crows missing three draws at the wake-up) predates Fixed 38.

- **Sprite placement** (`tools/re/sprite_audit.py`; Fixed 21's audit redone headless): each game's displayed sprites as
  pixel masks (the arcade's sprite list as its VBlank copies it, `gng.py` `spritebuf`; the port's VDP sprite table and
  tiles from VRAM) against the objects in RAM (Arthur, the 40 enemy slots, the 6 enemy shots, the 30 platform objects);
  every arcade 16x16 piece (24+ opaque pixels) is a key, found in the port's picture on the 16 px grid of its sprites, and
  the two placements relative to the object are compared, separately for frames with the object and the camera still and
  for moving ones. Runs of 6,000 frames per stage (stages 1-6 and the final room, random walking and firing, Arthur
  invincible), 9,500-62,000 pairs per stage: the screens' constant is (0, 0) in every stage, and every enemy pose's still
  pairs are at the arcade's place except misattributed pieces (a piece of another object put to the nearest slot shows as
  one large offset of a single run of frames). Moving objects are drawn at their position at the end of the frame the list
  is built in, in both games (arcade 95-99%; the port's remainder are frames without an update). The camera to measure
  against is the one the background is drawn with: the arcade's `<$9C/<$9E` (its scroll registers), the port's
  `$FF9100/2` (plane B scroll); `$FFA200/2`, read by the port's logic, is a frame behind it while scrolling, which put
  moving sprites 1 px off when measured against it (the earlier "stage 2 zombie walk frames 26-29 1-2 px apart": the
  zombies are stage 1's, and frames 26-29 now pair at the arcade's place still and moving, 1,760-1,800 pairs each).
  Astaroth (the port's own art, no identical piece): the same box in both, x -32..30/31, y -32..31 from his position in
  every pose (~5,000 arcade frames, ~5,900 port). Enemy shots: stage 5/6's type 4 pair at the arcade's place (430 and 830
  moving pairs; their other direction counts as mirrored only because the arcade's runs showed one direction). The shot
  pool's type 3 (the Big Men's shots, `$B042`) pairs at the arcade's place (Fixed 77). Stage 5's skull rise (the port's
  frames 1-2), which paired 8 px low: walked in from the stage start in both (right held), the rise is 3 frames in both
  (`$A2`/`$A3` twice, `$A4`/`$A5`) on the same frames with the pieces at (-16, -8)/(0, -8) from the skull and the same
  pixels; those pieces are the standing skull's upper row (drawn at y -16 in its 2 x 2), so the rise's offset was under
  the key filter's 5% and the rise was compared with the standing place (now counted "at a rare arcade place"). The
  pairs still listed as a few px off while moving (the asleep skull +2..+4 px in x while the camera scrolls, one rise
  frame) are frames on which the port shows the previous sprite table (`pace.c`'s held frames, `hook_sat_dma`: 102 of 399
  frames in that walk), not placement.
- **Stage 4's Petite Devils** (subtype 1; Fixed 51): they spawn only after the checkpoint (Arthur put along stage 4 from its
  start, x 3632-6700, y held: none; from the checkpoint: one every ~100 frames at x 4912, 4992, 5088, y 536). The port started
  at the checkpoint with the restart-entry trick (stage index 3's entry = the checkpoint's, `00538040`) and the arcade
  from `arc_start.py 3 1`, Arthur standing, 1,200 frames: the same slots (23, 22, 21), x/y at spawn, the same removal
  positions (x 5249 y 651, x 4735 y 609, x 4735 y 684), and every spawn and removal 1,868 frames apart in both, except
  the second spawn 1,867. That frame was the frame-counter phase: with the port's `$FFA206` lined up with `<$21`
  (`rng_lag` on the first frame, as Fixed 51) and the port's 2 skipped updates taken out (`tools/lockstep/slots.py` /
  `cmp_slots.py`), 1,300 frames from the checkpoint are identical (every devil's x/y on every frame): spawns on frames
  1, 54, 153, 967, 1048 and 1147, removals on 629, 729 and 787, in both.
- **Stage 3's collision map above the start** (Fixed 65's 13 cells): the map data is the arcade's. Logging the arcade's
  writes, rows 49-55 of columns 0-12 hold the port's values when the camera climbs (row writes); at the stage start the
  stage draw's column writes put zeros there (its 40-cell column buffer `$0388`, cells 24-39, holds an empty screen for
  those columns, `$828E`/`$8262`), which the row writes replace before those rows come on the screen (row R + 16 written
  at camera row R). Not reproduced (not reachable: the cells are 17-23 rows above the camera at the start).

## Not reachable in play

Differences that only a debug teleport or a test life start reaches, or that sit in cells play never shows or uses.
They stay as they are; each note says why.

- **Terrain map, what's left** (Fixed 65, 80): the ring is the arcade's world everywhere; what differs is the arcade's
  own stage draw at a camera column 0 (columns 0-12, rows R - 8 .. R - 1 and R + 17 .. R + 23, out of reach) and a few
  column writes' stale rows R + 15 .. R + 23 in stage 2 (above the screen).
  Traced (2026-10-28, `drawlog`-style write log over the boot to stages 1 and 3): every one of these cells was last written
  by the arcade's column copy (`$8677`, the store at `$86B8`, U from the 40-cell buffer `$0388` + (`$064E` & 15)) on the
  stage's first frames with the camera still at 0,0, before the start camera is placed (stage 3 then moves to row 32 and
  rewrites only rows R .. R + 16 of columns 0-12). For the rows under row 0 the column buffer is filled through the
  screen pointer stepping below the world's first screen row (`$4000` - `$20`), which reads memory outside the world
  map, so those cells hold whatever is there, not terrain. None is on the screen or under Arthur (the rows are 8-23
  below or above the screen, and the columns are written again before the camera reaches them); stage 2's stale rows
  R + 15 .. R + 23 are above the top of the screen (Firebrand's ceiling, Fixed 86's build, is the screen's top).

- **Stage 5 room, the arcade's ring at an x 7233 life start** (Fixed 67): a life start there (a test restart entry, not
  reached in play) leaves the arcade's bg ring one column off, so its ladders sit 16 px right; the port writes the map as
  it is. Not traced in the arcade's stage draw (`$726E`/`$80A0`).
- **Camera snaps (only after a debug teleport):** when Arthur is put far ahead of the camera (stage 2: x 5961 with the
  camera held at 5578) both games snap the camera to the next section (5833); the port blanks the display and refills
  the whole plane (`$93D6`, 32 columns, ~830 scanlines of work) over 8 paused frames where the arcade shows it on the next
  frame. Not reached in play: walked from the checkpoint (x 4736) through the town to x 6024, the camera scrolls past
  5578 one pixel a frame (Arthur 130 px ahead of it), with an update every frame and no refill. Not cheap to change: the
  snap is stage 2's streamer (`$11A89C`) finding the camera off its window or in another section and taking the stage's
  full reload (`$11A7C0`): display off, the section's tiles and palette uploaded again (`$B12` from the section table at
  `$FFB020`, `$B3D2`, `$B416`), the plane's 32 columns refilled, display on. The arcade's bg tiles are all in ROM, so it
  only rewrites its bg RAM; showing the port's on the next frame would mean uploading the section's art while the old
  picture is shown (no free VRAM to hold both) and a refill under a frame, for a case only a teleport reaches.

## Open

- **Petite Devils and skulls, what's left** (Fixed 51, 52; their art: Fixed 63; the crows' burst: Fixed 73; stage 4:
  Matching (audited)): the spawner leaves the spawn's x/y fractions from RAM in both games, and
  the slots it picks differ, so a devil can start a fraction apart (the lockstep runs set them equal). Co-op stage 2 runs
  at 0.73 updates per frame (was 0.81): the devils now stay on the screen as long as the arcade's, and drawing them is
  the cost (the same build with the devils not drawn: 0.88); co-op stage 5 0.98 -> 0.93 (skulls and devils on the screen).

- **Stage 2's devils, what's left** (Fixed 39; the windows: Fixed 61, 69, 79): sound `$12` at the opening is played by
  id, not compared by ear. The subtype 0/2 states (no such spawn records in stage 2) were since forced in both games and
  match: `slots.py FORCE=0/2` (each window devil made subtype 0 or 2 on its first frame, as if spawned so) from the
  checkpoint states (`arc_start.py 1 1`; `port_start.py` on a `restart_entry.py` copy, entry `00128050` index 1, `TX=4736
  TC=4608`), Arthur held at x 4850, 5100 and 5300, 2,500 frames each: every slot's states, x and y identical update for
  update (`cmp_slots.py` offset 1, `STATES=1`; the unforced run too). Subtype 0 went through its wait off the screen,
  walk, glide, hop and come-down (1/0-1/3), subtype 2 through the leap out (1/5) and the walk. The change into a Red
  Arremer was forced in both too (Matching (audited), Red Arremers).

- **Ending, what's left** (Fixed 56, 72, 85): the texts' colours are the nearest the palette lines allow (the HUD's), the
  heart's too. Firebrand's ending is reached headless now (`tools/headless/fb_plus_test.py`: the final room's
  proof played from its launch, the ending's text, then Firebrand's Quest Plus from stage 1 at rank `$20` with the 1 s
  hover, the unlock saved in SRAM and still set after a power-on with it).

- **Smaller:** (the stage 2 ledge-edge and elevator walk steps: Fixed 66.) "A stage 5 flying
  knight drifts after ~600 frames" wasn't reproduced: no flying knight (type 3, `$AFFC`) spawns in stage 5 (every slot
  listed with Arthur held at each height from y 600 to 1800 and x 7100/7380: crows, Petite Devils, the Arremer, the Satan,
  skulls and Big Men only); the stage 1 knight's handler (`$1E8C`) matches the arcade's instruction for instruction; the
  likeliest source was stage 5's Big Men (Fixed 54). Stage 2's water death y (24 in the arcade, 25 in the port) came from
  the restart's y fraction (Fixed 46): with the fractions equal the fall and the death are identical (y 79, 74, ... 24).

- **"Invisible troll" (itch.io report, stage 2 by the brick building after the ladder building):** not reproduced. With
  a check that every live, on-screen Big Man has sprites with pixels in the sprite table on every frame, over the ladder
  building and past it (teleported to x 5488/5632/5760 and walking on, ~6,000 frames) every one was drawn whenever the
  game ran; the only frames without were the 8 paused, blank frames of the camera snap above (after a teleport). The Big Men's own
  stand-ins in that area (a clamp to x 5200-5808 and a floor assumed where the probe found none) were removed with Fixed 54. Fixed 78 later found every Big Man drawn split down the middle (the halves swapped since Fixed 21), which may be what was seen.
- **"Stage 5's enemies run much faster than normal" (player report, Genesis Plus GX; build and mode not given):** not
  reproduced on V0.6. Checked: stage 5 after a real stage 4 clear (stage 4's proof played from its launch) runs as a
  direct launch does, at 1.0 updates per frame once play starts (the first ~700 frames are the map and the stage-start
  hold), rank `$0A` (the base 6 + 4 for the clear, as the arcade's); the rank goes back to the base at every life start
  (20,000 frames of deaths: base and working rank 6 at each restart); the rank-indexed tables of the C handlers (devils,
  Satans, skulls, window devils) are masked to their sizes; per-type steps along Firebrand's stage 5 route are the same
  in V0.5 and V0.6 (no type above the arcade's speeds). Stage 5's devils and skulls are the arcade's (Fixed 51, 52, lockstep),
  much quicker than the original port's own. The report was on V0.5: there, too, stage 5 runs at 1.0 updates per frame and every
  enemy type's steps are within a few percent of V0.6's, none faster than the arcade's (1P walks at the start; `fb_explore.py P=0 STATS=...` on each build, Arthur
  climbing to y 1234 (V0.5) and 1248 (V0.6) of the tower in 22,000 rounds, every update of the play logged: per 200 px
  band and type the mean step 1.3-2.5 px in both, the 95th percentiles the same or a pixel apart; the top: both builds from
  a life start in the Satan's room (`restart_entry.py` entry `40DB6050`), 4,000 rounds each, y 1200-1650: the same,
  the Satan 1.93/1.96 px mean, 95th percentile 4, max 11 in both). Needs the mode (1P, co-op, Firebrand, Plus), the difficulty setting (Hardest starts at
  rank `$20`, so stage 5 at `$30`+) and the place.
- **Co-op speed, a known limit** (Fixed 82; kept as it is for V0.6): co-op now runs 0.82 (stage 2), 0.91-0.93 (stages 3, 5, 6) and 0.97 (stages 1, 4) in-play
  updates per frame (3-seed means), 1P and Firebrand 0.93-1.0. What's left per update on the stage 2 co-op snapshot (~203
  lines, Unicorn estimate): Maximo's context swap (~12, 248 bytes exchanged twice; every byte must stay as before), his
  control block (~14, the engine's player routines a second time), the Petite Devils' C (~5 each on the screen,
  `petite.c`), the type blocks' context copies of the enemies off the screen (~200 cycles each, their RAM writes kept)
  and the platform, item and shot passes; each a few lines at most.
  Reaching 1.0 in stage 2 would need about a fifth of the update cut, which means restructuring the enemy
  passes (lists of the live slots instead of all 40) and a lighter second-player update; that isn't planned for this
  release. In co-op stage 2 the game slows by about a fifth when the screen is busy; nothing is lost (no fault in the
  V0.6 sweep, stages 1-6 x 1P/co-op/Firebrand x 3 seeds).
- **Intro** (Fixed 62, 70, 71, 83, 84, 87): after the second clear the arcade shows the HUD alone for 2 frames before
  the graveyard (2587-2588 of the `fb_cmp.py` run), where the port is still loading the scene with the display off
  (its load takes 3 frames; the arcade's last text is still on the screen until 2586, so the ending can't hand over
  sooner without blanking it: tried, the 2 text frames lost; the HUD frames would also need the graveyard to be
  loaded while the text shows). Its black part's cloak blinks and the Satan's and Arthur's 1-4 px offsets follow the
  frame counter and the sub-pixel parts the objects keep from the final room, so they change with the run (a list
  recorded from one run matched the reference run worse, IoU 0.847 against 0.985): the port plays the reference
  run's frames. The second clear's bonus life follows the arcade's rule (the first frame with the counter & 7 = 0
  in play, Fixed 58), so its frame depends on the counter's phase in both games; the port's counter doesn't count the
  opening's frames (the arcade's counts every frame), which only moves that phase, as the arcade's own time before
  Start does.
