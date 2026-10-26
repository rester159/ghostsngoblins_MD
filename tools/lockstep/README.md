# Lockstep tools: the port and the arcade side by side

Headless only (no emulator windows). The port runs in Genesis Plus GX through `tools/headless/lr.py`'s harness
(`lrbase.py` exec's its setup), the arcade in `tools/arcade/gng.py` (Python 6809, ~550 frames/s, ROMs in `rom/`).
Core: `C="$HOME/Library/Application Support/RetroArch/cores/genesis_plus_gx_libretro.dylib"`.

| Script | What it does |
|---|---|
| `devscript.py <stage 1-6> <players>` | the pad script that boots the plus build and launches a stage from the developer menu (players: 0 = 1P, 1 = co-op, 2 = Firebrand); play starts ~1,400 frames in |
| `port_start.py <core> <rom> <frames> <out>` | `SCRIPT=$(devscript.py ...) TX= TC=`: saves `<out>_st.state` 30 frames after Arthur is at x TX with the camera at TC |
| final room (port) | the developer menu stops at STAGE 6; poke its stage `$FF500B` = 7 (stage index 6) on every frame 1000-1300 of a `devscript.py 6 <players>` launch (`POKE` in `port_walk.py`, e.g. `POKE=$(python3 -c "print(','.join('%d:FF500B:07'%f for f in range(1000,1301)))")`) and the final room starts ~1,310 frames in; set it back to 1 before a clear, or the next game start relaunches the room. Arcade: `arc_start.py 6 0` |
| `port_checkpoint.py` | stage 2 only: walks in, dies, saves `<out>_cp.state` 30 frames after the checkpoint respawn |
| `arc_start.py <stage index 0-6> <checkpoint> <out.state>` | the arcade's equivalent (pokes `$72`/`$81` while booting); 30 frames after its restart, so timers start in phase with `port_start.py` |
| `port_walk.py <core> <rom> <frames> <out>` / `arc_walk.py <state> <frames> "<script>"` | the same walk in each game (`BOT=1`, `AJ`=jump x list, `CL`=climb x list, `TP`=frame:x teleport in the arcade, `POKE` in the port), logging every enemy slot change of `TYPES` (or `all`) and Arthur every 100 frames |
| `port_score.py` | score and slot-state changes with the update counter (score timing) |
| `bench.sh <rom> <stage> <players>` | speed (in-play updates per frame, `SEED` = random input) and a log with the fault word `$FFC9DC` (`OUT` = output dir) |
| `bot.py` | the walk bot both walkers share |
| `route.py` | a scripted route (`ROUTE="W58,L7200,U,R7262,U"`: walk to x, climb, jump, wait, fire) both games follow from their own positions |
| `arc_rand.py <state> <frames> "<script>"` / `port_rand.py <core> <rom> <frames> <out>` | every draw of the shared second random (`$68F9` / `$FFC62C`, Fixed 31): the arcade's by frame, call site and slot; the port's per frame as a count of register steps, frames counted from the restart (`TX`), `ROUTE`, `RPOKE` (e.g. `1:FF5600:0F` sets `rng_lag` to line `$FFA206` up with `<$21`), `XLOG=1` Arthur every frame. A life start anywhere: point a stage's restart entry there (arcade RAM `$6CED` + 4 x stage during the boot, port a test copy of the ROM table `$1040CC`) |
| `port_end.py` | the final room's end forced in the port (second clear by default, `SCORE`), logging score, lives, stage and the update counter; the arcade's equivalent: poke `<$7F` = 1, `<$08` = 2, `<$0B` = 0 into an `arc_start.py 6 0` state |

RAM: port enemy slots `$FFB800` (40 x 48: +4 live, +5 on screen, +6 subtype, +7 state, +10 type, +17 x, +21 y,
y points up: screen y = 224 - (y - cam y)), camera `$FFA200/2`, Arthur x `$FF9001`, y `$FF9004`, invincibility `$FFC309`,
dying `$FFC571`, stage/checkpoint `$FFF400/1`; arcade slots `$0880` (40 x 48, X = slot + `$10`: +0 live, +1 on
screen, +2 subtype, +3 state, +4/+5 sub-states, +6 x, +9 y, +`$15` type), camera `$9C/$9E`, Arthur x `$0506`, y
`$0509`, invincibility `$AD`, score `$68-$6B`, lives `$60`.
