| Terrain map windows in stages 2-5 (docs/ACCURACY.md, Fixed 37). Hooks:
| tools/patch_gng.py.
|
| The collision map ($FF0000) is a ring of 32 x 32 cells of 16 px, like the
| arcade's bg RAM ($2800, read by $8DD2: column x/16 & 31, row ~(y/16) & 31),
| which is its collision map too. The arcade writes a column as the camera
| reaches it, cam/16 + 16 when scrolling right (stages 1 and 3 measured: at
| cam/16 = 15 ring column 31, at 16 column 0, ...), so its ring holds
| cam/16 - 15 .. cam/16 + 16. The port's streamers hold cam/16 - 8 ..
| cam/16 + 23 (stage 1's was moved in arthur.s, map_start_d6/d0). Probing
| the floor at every cell around the camera in both games from lockstep
| states with the same camera (Arthur's probe, $8CA7 / $8784) gave
| disagreements in the columns cam/16 - 15 .. - 9 and + 17 .. + 23
| in stages 3 and 5 (the real level in one game, the level 512 px away
| in the other). These give the stages' window functions the arcade's
| start, cam/16 - 15, with their own clamps to the stage's map (the lower
| clamp moved with it, so the first window is the same).
| Each replaces the x part of its function (d6 = window start column) and
| returns to its y part (d5), or to its caller.

    .section .text,"ax"
    .global mw_stage2, mw_stage3, mw_stage4, mw_stage5

| $11A986 (stage 2, called from $11A7E6 / $11A8AE): was cam/16 < 232 ? 224
| : cam/16 - 8, at least 224, at most 416.
mw_stage2:
    move.w  0xFF9100,%d6
    lsr.w   #4,%d6
    cmpi.w  #239,%d6
    bcc.s   1f
    move.w  #224,%d6
    bra.s   2f
1:  subi.w  #15,%d6
2:  cmpi.w  #416,%d6
    bls.s   3f
    move.w  #416,%d6
3:  rts

| $104D16 (stage 3): was cam/16 < 8 ? 0 : cam/16 - 8, at most 192.
mw_stage3:
    move.w  0xFF9100,%d6
    lsr.w   #4,%d6
    cmpi.w  #15,%d6
    bcc.s   1f
    moveq   #0,%d6
    bra.s   2f
1:  subi.w  #15,%d6
2:  cmpi.w  #192,%d6
    bls.s   3f
    move.w  #192,%d6
3:  rts

| $10F124 (stage 4): was cam/16 < 232 ? 224 : cam/16 - 8, at most 384.
mw_stage4:
    move.w  0xFF9100,%d6
    lsr.w   #4,%d6
    cmpi.w  #239,%d6
    bcc.s   1f
    move.w  #224,%d6
    bra.s   2f
1:  subi.w  #15,%d6
2:  cmpi.w  #384,%d6
    bls.s   3f
    move.w  #384,%d6
3:  rts

| $11001C (stage 5): was cam/16 < 424 ? 416 : cam/16 - 8, at most 432.
mw_stage5:
    move.w  0xFF9100,%d6
    lsr.w   #4,%d6
    cmpi.w  #431,%d6
    bcc.s   1f
    move.w  #416,%d6
    bra.s   2f
1:  subi.w  #15,%d6
2:  cmpi.w  #432,%d6
    bls.s   3f
    move.w  #432,%d6
3:  rts
