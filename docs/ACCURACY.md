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

## Open

- **Stage start:** the arcade spends a frame landing (y 64.28 -> 62.03) without moving; the port lands and
  moves in one frame. Start x fraction `$60F5` (arcade) vs `$609C` (port); start y 64.28 vs 64.00.
- **Landing keeps the y fraction** in the arcade (`$96CA`: only the integer moves); the port's ground
  landing after a knockback leaves y at 62.00 where the arcade has 62.86.
- **Knockback path** after the first zombie hit differs by ~3 px (partly the start offset).
- **Enemies:** with the same input the port's Arthur is hit again ~130 frames after the first tombstone
  while the arcade's isn't hit for another ~340. Not yet traced (enemy tables to be mapped).
