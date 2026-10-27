"""Firebrand's ending into Firebrand's Quest Plus, headless: the final room
launched as fb_campaign does (stage 7), its proof (fb_proofs/stage7_final_room.moves)
played straight, then the game left to run through the ending into Plus.

usage: [UNLOCK=1] [SRM=<file>] fb_plus_test.py <rom> <out prefix> [--boot]
UNLOCK=1 clears the practice flag (Persist dev_on) once the launch is done, as
if the quest had been played from the Home menu, so the unlock is saved
(a practice launch never unlocks Plus). Prints the Plus state once he is
controllable in stage 1 (stage index, rank, the Persist flags, the unlock in
SRAM) and the hover's length there, and saves <out>_ending.png / <out>_plus.png.
SRM=<file> writes the cartridge SRAM there at the end; --boot then powers on
with that SRAM and reports whether the unlock is still set."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fbh import Game, J     # noqa: E402

rom, out = sys.argv[1], sys.argv[2]
if len(sys.argv) > 3 and sys.argv[3] == '--boot':     # power on with SRM's SRAM: is Plus still unlocked?
    import ctypes as C
    g = Game(rom, sysdir=os.path.dirname(os.path.abspath(out)))
    raw = open(os.environ['SRM'], 'rb').read()
    C.memmove(g.L.retro_get_memory_data(0), raw, min(len(raw), g.L.retro_get_memory_size(0)))
    g.run(600, 0)
    print('power-on with the saved SRAM: fb_unlocked %d, fb_plus %d' % (g.r8(0xFF5026), g.r8(0xFF5027)))
    sys.exit(0)
SYM = {l.split()[2]: int(l.split()[0], 16) for l in
       open(os.path.join(HERE, '..', '..', 'src_patch', 'build', 'patch.sym')) if len(l.split()) == 3}
g = Game(rom, sysdir=os.path.dirname(os.path.abspath(out)), options={'genesis_plus_gx_overclock': '200%'})
g.launch(6, poke=lambda gg: 880 <= gg.frame <= 1300 and gg.w8(0xFF500B, 7))
moves = [int(v, 16) for v in open(os.path.join(HERE, 'fb_proofs', 'stage7_final_room.moves')).read().split()]
if os.environ.get('UNLOCK'):
    g.w8(0xFF500A, 0)
g.want_video = False
for i, m in enumerate(moves):             # the proof ends with the ending's 8 s and the cut to stage 1's map
    g.want_video = i == len(moves) - 240
    g.run(1, m)
    if g.want_video:
        g.png(out + '_ending.png')
print('after the proof: stage index', g.r8(0xFFC512))
g.want_video = False
for f in range(6000):
    g.run(1, 0)
    if g.r8(0xFFC512) == 0 and g.r8(0xFFC305) == 1 and f > 60:
        break
g.want_video = True
g.run(30, 0)
g.png(out + '_plus.png')
print('Plus: stage index %d, rank $%02X (floor $%02X), fb_plus %d, fb_unlocked %d, dev_on %d, frames %d' % (
    g.r8(0xFFC512), g.r8(0xFFC501), g.r8(0xFFC561), g.r8(0xFF5027), g.r8(0xFF5026), g.r8(0xFF500A), f))
# the hover: a jump held through its top, counting the frames the hover timer runs
n, prev = 0, None
for k in range(200):
    g.run(1, J)
    t = g.r8(SYM['hover_t'])
    if prev is not None and t < prev:
        n += 1
    prev = t
print('hover: %d frames' % n)
if os.environ.get('SRM'):                 # the cartridge SRAM, for a power-on with it (fb_plus_test.py --boot)
    import ctypes as C
    L = g.L
    n = L.retro_get_memory_size(0)
    open(os.environ['SRM'], 'wb').write(C.string_at(L.retro_get_memory_data(0), n))
    print('SRAM saved: %d bytes' % n)
