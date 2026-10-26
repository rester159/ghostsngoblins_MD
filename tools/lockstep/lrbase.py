"""The setup half of tools/headless/lr.py (core load, callbacks, ram(), rd(),
png(), SCRIPT/SCRIPT2 input, LOAD) as a module body: exec'd by the lockstep
scripts so they share lr.py's harness. Defines L, C, ram, rd, png, frames,
out, frame_no, SCRIPT, SCRIPT2 in the caller's globals."""
import os
_LR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'headless', 'lr.py')


def setup(g):
    src = open(_LR).read()
    src = src[:src.index('\npokes = []')]
    exec(compile(src, _LR, 'exec'), g)


def w8(g, a, v):
    C = g['C']; p = g['L'].retro_get_memory_data(2)
    C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v
