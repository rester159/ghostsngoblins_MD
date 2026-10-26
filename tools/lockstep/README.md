# Lockstep tools: the port and the arcade side by side

Headless only (no emulator windows). The port runs in Genesis Plus GX through `tools/headless/lr.py`'s harness
(`lrbase.py` exec's its setup), the arcade in `tools/arcade/gng.py` (Python 6809, ~550 frames/s, ROMs in `rom/`).
Core: `C="$HOME/Library/Application Support/RetroArch/cores/genesis_plus_gx_libretro.dylib"`.

| Script | What it does |
|---|---|
| `devscript.py <stage 1-6> <players>` | the pad script that boots the plus build and launches a stage from the developer menu (players: 0 = 1P, 1 = co-op, 2 = Firebrand); play starts ~1,400 frames in |
| `port_start.py <core> <rom> <frames> <out>` | `SCRIPT=$(devscript.py ...) TX= TC=`: saves `<out>_st.state` 30 frames after Arthur is at x TX with the camera at TC |
| `port_checkpoint.py` | stage 2 only: walks in, dies, saves `<out>_cp.state` 30 frames after the checkpoint respawn |
| `arc_start.py <stage index 0-6> <checkpoint> <out.state>` | the arcade's equivalent (pokes `$72`/`$81` while booting); 30 frames after its restart, so timers start in phase with `port_start.py` |
| `port_walk.py <core> <rom> <frames> <out>` / `arc_walk.py <state> <frames> "<script>"` | the same walk in each game (`BOT=1`, `AJ`=jump x list, `CL`=climb x list, `TP`=frame:x teleport in the arcade, `POKE` in the port), logging every enemy slot change of `TYPES` (or `all`) and Arthur every 100 frames |
| `port_score.py` | score and slot-state changes with the update counter (score timing) |
| `bench.sh <rom> <stage> <players>` | speed (in-play updates per frame, `SEED` = random input) and a log with the fault word `$FFC9DC` (`OUT` = output dir) |
| `bot.py` | the walk bot both walkers share |

RAM: port enemy slots `$FFB800` (40 x 48: +4 live, +5 on screen, +6 subtype, +7 state, +10 type, +17 x, +21 y,
y points up: screen y = 224 - (y - cam y)), camera `$FFA200/2`, Arthur x `$FF9001`, y `$FF9004`, invincibility `$FFC309`,
dying `$FFC571`, stage/checkpoint `$FFF400/1`; arcade slots `$0880` (40 x 48, X = slot + `$10`: +0 live, +1 on
screen, +2 subtype, +3 state, +4/+5 sub-states, +6 x, +9 y, +`$15` type), camera `$9C/$9E`, Arthur x `$0506`, y
`$0509`, invincibility `$AD`, score `$68-$6B`, lives `$60`.
