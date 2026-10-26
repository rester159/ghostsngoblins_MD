"""port_end.py <core> <rom> <frames> <out>: the final room from a developer launch (SCRIPT = devscript.py 6 <players>;
the stage poke $FF500B = 7 is done here), then the room's end forced on frame START (default: 30 updates into the room's play, Arthur at x 8024; Arthur kept invincible): the boss-removal
flags ($FFDB08 = 1, wait $FFDB0A = 0), the clear count $FF7FC0 = LOOPED (default 1: the second clear) and the score
$FFC000 = SCORE (BCD hex, optional). Logs every change of the score, lives, stage, the death flag $FFC570 and the update
counter's run state, with the frame counted from the forced end (e1 = the first frame after it) and $FFA206. Compare with
an arcade run that pokes <$7F, <$08 = 2 (the removal's mode switch) into a final-room state."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lrbase
lrbase.setup(globals())


def w8(a, v):
    p = L.retro_get_memory_data(2); C.c_uint8.from_address(p + ((a - 0xFF0000) ^ 1)).value = v


START = int(os.environ['START']) if os.environ.get('START') else None; LOOP = int(os.environ.get('LOOPED', '1'))
SC = os.environ.get('SCORE')
prev = None; lastu = None
for f in range(1, int(frames) + 1):
    frame_no[0] = f
    if 1000 <= f <= 1300: w8(0xFF500B, 7)
    if f == 1301: w8(0xFF500B, 1)
    w8(0xFFC309, 60)
    if START is None and f > 1310:
        r = ram()
        if rd(r, 0xFF9001, 2) == 8024 and rd(r, 0xFF7084, 4) > 330: START = f + 30
    if f == START:
        w8(0xFFDB08, 1); w8(0xFFDB0A, 0); w8(0xFFDB0B, 0); w8(0xFF7FC0, LOOP)
        if SC:
            v = int(SC, 16)
            for k in range(4): w8(0xFFC000 + k, (v >> (24 - 8 * k)) & 255)
    L.retro_run()
    if START is None or f < START: continue
    r = ram(); u = rd(r, 0xFF7084, 4)
    cur = (rd(r, 0xFFC000, 4), rd(r, 0xFFC500, 1), rd(r, 0xFFC512, 1), rd(r, 0xFFC570, 2), u != lastu)
    lastu = u
    if cur != prev:
        print('e%d score %08X lives %d stage %d death %d running %d c21 %02X upd%d ax%d' % ((f - START + 1,) + cur + (rd(r, 0xFFA206, 1), u, rd(r, 0xFF9001, 2))))
        prev = cur
