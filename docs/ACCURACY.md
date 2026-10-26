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

## Open

- **Sprite placement not checked:** the final-room boss (no pixel-identical piece to pair; its shots use the port's flame art), `$B110` frames
  1-4 (ambiguous). Stage 2 zombie walk frames 26-29 matched arcade images 1-2 px apart, possibly the
  streamed art arriving an update late (hypothesis).

- **Petite Devils and skulls, what's left** (Fixed 51, 52): the skulls have no port art (drawn with the type-9 frames,
  a blue orb); the devils' fireball is the port's orb, not sprite `$F7`, and the carrier's wing poses `$FD`-`$FF` show
  `$FA`-`$FC`; neither death draws the arcade's burst (the 21 frames are kept). Stage 4's devils (subtype 1) weren't met in
  a play run (checked on placed devils only). The spawner leaves the spawn's x/y fractions from RAM in both games, and
  the slots it picks differ, so a devil can start a fraction apart (the lockstep runs set them equal). Co-op stage 2 runs
  at 0.73 updates per frame (was 0.81): the devils now stay on the screen as long as the arcade's, and drawing them is
  the cost (the same build with the devils not drawn: 0.88); co-op stage 5 0.98 -> 0.93 (skulls and devils on the screen).

- **The Satans, what's left:** nothing is drawn for the 22-frame burst before the score (the port has no burst
  frames for it); the arcade's hovering pose with the wings open has no port frame (drawn as the flying pose),
  and its shot (a star, sprites `$D7/$DF`) is drawn with the port's type-6 shot art (a small orb). (Their spawn
  fractions: Fixed 53.)

- **Vertical scroll speed:** while the camera catches up a long way vertically (stage 5, 50 frames of 5 px steps) the port
  loses an update (the row streaming runs past the frame); the camera's moves are the arcade's (Fixed 45).

- **Stage 2's devils, what's left** (Fixed 39): the window tiles opening and closing aren't drawn (the port has no window
  art; their 20-frame timing is kept); sound `$12` at the opening is played by id, not compared by ear; the change into a Red
  Arremer after 1200-3600 frames and the subtype 0/2 states (no such spawn records seen in stage 2) are translated but weren't
  reached in a run (the change into an Arremer was since forced in both games: Matching (audited), Red Arremers).

- **Ending, what's left** (Fixed 56): the texts in the port's one-colour font, shown whole; the princess's colours
  from Arthur's palette line; the port's
  own opening after the second clear.

- **Smaller:** the stage 2 stone-block edge and elevator walk-step quirks (not measured). "A stage 5 flying
  knight drifts after ~600 frames" wasn't reproduced: no flying knight (type 3, `$AFFC`) spawns in stage 5 (every slot
  listed with Arthur held at each height from y 600 to 1800 and x 7100/7380: crows, Petite Devils, the Arremer, the Satan,
  skulls and Big Men only); the stage 1 knight's handler (`$1E8C`) matches the arcade's instruction for instruction; the
  likeliest source was stage 5's Big Men (Fixed 54). Stage 2's water death y (24 in the arcade, 25 in the port) came from
  the restart's y fraction (Fixed 46): with the fractions equal the fall and the death are identical (y 79, 74, ... 24).

- **Stage 5 room, Arthur:** walking right from x 7008 on the top floor the arcade's Arthur stands still for a frame where
  the floor steps down a pixel (x 7048, y 1615 -> 1614) and the port's doesn't, so he is a frame ahead from there; the
  ladder up from the floor at y 1455 is climbed from x 7200 in the arcade (Arthur put at x 7200 on it) and from x 7196 in
  the port (put at x 7184; up at x 7200 doesn't take it). Not traced.
- **Camera snaps (only after a debug teleport):** when Arthur is put far ahead of the camera (stage 2: x 5961 with the
  camera held at 5578) both games snap the camera to the next section (5833); the port blanks the display and refills
  the whole plane (`$93D6`, 32 columns, ~830 scanlines of work) over 8 paused frames where the arcade shows it on the next
  frame. Not reached in play: walked from the checkpoint (x 4736) through the town to x 6024, the camera scrolls past
  5578 one pixel a frame (Arthur 130 px ahead of it), with an update every frame and no refill.
- **"Invisible troll" (itch.io report, stage 2 by the brick building after the ladder building):** not reproduced. With
  a check that every live, on-screen Big Man has sprites with pixels in the sprite table on every frame, over the ladder
  building and past it (teleported to x 5488/5632/5760 and walking on, ~6,000 frames) every one was drawn whenever the
  game ran; the only frames without were the 8 paused, blank frames of the camera snap above (after a teleport). The Big Men's own
  stand-ins in that area (a clamp to x 5200-5808 and a floor assumed where the probe found none) were removed with Fixed 54.
- **Co-op speed:** with the enemies now behaving as the arcade's (devils staying on the screen as long, skulls, Big Men)
  and the per-update fixes above, co-op runs slower than the last install (seed 1: stage 2 0.70, stage 5 0.89, stage 6
  0.82 updates per frame; 1P and Firebrand stay 0.92-1.0). On identical RAM the per-update fixes cost ~3 scanlines of
  ~165; the rest is the arcade's enemies on the screen. The big costs are the port's own stage 2 enemy pass (`$99C0`,
  ~22 lines) and sprite build (`$B258`, ~12), and Maximo's context swaps (~12).
- **Terrain map edges:** after Fixed 49 a few cells on the ring's edge columns still differ at a stage start (stage 5: 8
  of 1,792 probed, stage 6: 10), where the arcade's first fill left them as they were; not traced.

- **Intro:** the arcade's opening shows Arthur and the princess in the graveyard (stage background) for
  ~200 frames before the black-background kidnapping scene; the port's intro starts at the kidnapping.
  Start to play is 557 frames in the arcade, ~335 in the port.
