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

- **Not yet audited:** stages 2-6 enemies and bosses, the stage-1 plants (spit timing), the raft and
  forest, per-enemy hit points and drops beyond stage 1, two-player alternation.
- **Bonus lives:** the plus build caps lives at 9 (the arcade doesn't).
- **Continue digit:** the port shows one digit, so the arcade's "10" step shows as 9.

- **Stage start:** the arcade spends a frame landing (y 64.28 -> 62.03) without moving; the port lands and
  moves in one frame. Start x fraction `$60F5` (arcade) vs `$609C` (port); start y 64.28 vs 64.00.
- **Stage start / respawn:** the arcade draws the stage over the map for ~37 frames (`$726E` calling `$80A0`
  until done) before play (`<$0B` = 1); death to control is 504 frames in the arcade vs 481 in the port.
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
