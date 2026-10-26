| Row streaming in fewer cycles (docs/ACCURACY.md, Fixed 64).
|
| When the camera crosses a 16 px row, each stage's streamer ($10FF6A in
| stage 5, the same shape in the others) fills one row of the collision ring
| ($938E: 32 cells, each through the map lookup $9346 with its bounds checks
| and a multiply) and builds the row's plane entries in $FF0A00/$FF0A80
| (clearing the 256 bytes first, then 32 cells each with a multiply), for the
| VBlank DMA. That was ~43 of an update's ~200 lines (Unicorn estimate,
| stage 5): with the camera catching up a long way vertically (5 px a frame,
| a row every 3 frames) an update ran past its frame and the game lost an
| update the arcade doesn't. The same work done incrementally (one bounds
| check of the row, pointers stepped by the map's height / the row's stride,
| no clear: the 32 cells write every word of both halves) writes the same
| bytes; tools/re/test_ab.py: identical RAM and VDP writes.

    .section .text,"ax"
    .global fast_maprow, row_s124, row_s3, row_s5, row_s6

| $938E: `jmp fast_maprow` over `movem.l d4-d7,-(sp) / moveq #1,d7`. In: d0
| first column, d1 row (the ring holds row d1 - 5, mw_rows), a3 the map
| descriptor (+0 x0, +2 y0, +4 w, +6 h, +8 tile bytes, +12 attribute bytes,
| column-major), a4 the ring ($FF0000: tiles, +1024 attributes; offset
| (col & 31) << 5 | (~row & 31)). A cell outside the map is tile 0,
| attribute $C0. Out as the original: d0 = 32, d1 as the last lookup left it
| (the attribute byte, or $C0 in the low word over the upper word of the last
| in-map lookup's 0, or of the entry d1 if no cell was in the map; the
| callers' tile loops add d1.l), d4-d7 kept.
fast_maprow:
    movem.l %d4-%d7,-(%sp)
    move.l  %d1,%d7                 | upper word of d1 while no cell is in the map
    move.w  %d1,%d5
    subq.w  #5,%d5                  | mw_rows: the row 5 lower
    move.w  %d5,%d2
    eori.w  #15,%d2
    andi.w  #31,%d2
    move.w  %d0,%d1
    andi.w  #31,%d1
    lsl.w   #5,%d1
    or.w    %d1,%d2                 | ring offset of the first cell
    lea     1024(%a4),%a2
    moveq   #31,%d6
    sub.w   (%a3),%d0               | column in the map
    sub.w   2(%a3),%d5              | row in the map
    cmp.w   6(%a3),%d5
    bcc.s   6f                      | the row is outside the map: every cell empty
    move.w  4(%a3),%d3              | w
    moveq   #0,%d4
    move.w  6(%a3),%d4              | h
    move.w  %d0,%d1
    muls.w  %d4,%d1                 | column * h (signed: left of the map)
    andi.l  #0xFFFF,%d5
    add.l   %d1,%d5                 | map offset of the first cell
    movea.l 8(%a3),%a0
    movea.l 12(%a3),%a1
1:  cmp.w   %d3,%d0
    bcc.s   2f
    move.b  0(%a0,%d5.l),0(%a4,%d2.w)
    move.b  0(%a1,%d5.l),0(%a2,%d2.w)
    moveq   #0,%d7
    bra.s   3f
2:  clr.b   0(%a4,%d2.w)
    move.b  #0xC0,0(%a2,%d2.w)
3:  addq.w  #1,%d0
    add.l   %d4,%d5
    addi.w  #32,%d2
    andi.w  #0x3FF,%d2
    dbf     %d6,1b
    subq.w  #1,%d0                  | the last cell
    cmp.w   %d3,%d0
    bcc.s   4f
    sub.l   %d4,%d5
    moveq   #0,%d1
    move.b  0(%a1,%d5.l),%d1
    bra.s   5f
4:  move.l  %d7,%d1
    move.w  #0xC0,%d1
5:  movem.l (%sp)+,%d4-%d7
    moveq   #32,%d0
    rts
6:  clr.b   0(%a4,%d2.w)
    move.b  #0xC0,0(%a2,%d2.w)
    addi.w  #32,%d2
    andi.w  #0x3FF,%d2
    dbf     %d6,6b
    bra.s   4b

| The row's plane entries: each stage's loop after `jsr $938E` (`lea
| $FF0A00,a1` replaced by `jmp row_sN`) cleared $FF0A00-$FF0AFF, then for 32
| cells (column d4 on, row d5) computed the cell's 8-byte entry in the
| stage's plane map ($FFB014 + column * stride + row * 8, the column offset
| with the stage's own formula) and stored its four words at
| (d4 & 31) * 4 of $FF0A00 and $FF0A80. Each stub computes the first cell's
| address with its loop's own instructions (d1's upper word as the original
| sees it) and its stride; row_core steps it. The callers return straight to
| a movem that restores every register.

| $986C, $11570E, $11AB02 (map $125A70): (d4 - $FFB018) << 8 + d5 * 8. A
| column left of $FFB018 gives the same address mod 2^24 either way.
row_s124:
    moveq   #0,%d0
    move.w  %d4,%d0
    sub.w   0xFFB018,%d0
    lsl.l   #8,%d0
    move.w  %d5,%d1
    lsl.w   #3,%d1
    add.l   %d1,%d0
    move.w  #256,%d2
    bra.s   row_core

| $104DF6 (stage 3): d4 << 9 + (d5 - 32) * 8.
row_s3:
    moveq   #0,%d0
    move.w  %d4,%d0
    lsl.l   #8,%d0
    lsl.l   #1,%d0
    move.w  %d5,%d1
    subi.w  #32,%d1
    lsl.w   #3,%d1
    add.l   %d1,%d0
    move.w  #512,%d2
    bra.s   row_core

| $110102 (stage 5): (d4 - 416) * 640 + (d5 - 32) * 8 (d4 >= 416: the
| window's clamp, mw_stage5).
row_s5:
    moveq   #0,%d0
    move.w  %d4,%d0
    subi.w  #416,%d0
    mulu.w  #640,%d0
    move.w  %d5,%d1
    subi.w  #32,%d1
    lsl.w   #3,%d1
    add.l   %d1,%d0
    move.w  #640,%d2
    bra.s   row_core

| $1110B8 (stage 6): (d4 - 464) * 640 + (d5 - 96) * 8 (d4 = 464).
row_s6:
    moveq   #0,%d0
    move.w  %d4,%d0
    subi.w  #464,%d0
    mulu.w  #640,%d0
    move.w  %d5,%d1
    subi.w  #96,%d1
    lsl.w   #3,%d1
    add.l   %d1,%d0
    move.w  #640,%d2

row_core:
    movea.l 0xFFB014,%a0
    adda.l  %d0,%a0
    lea     0xFF0A00,%a1
    lea     0xFF0A80,%a2
    moveq   #31,%d6
1:  move.w  %d4,%d0
    andi.w  #31,%d0
    add.w   %d0,%d0
    add.w   %d0,%d0
    move.w  (%a0),0(%a1,%d0.w)
    move.w  2(%a0),2(%a1,%d0.w)
    move.w  4(%a0),0(%a2,%d0.w)
    move.w  6(%a0),2(%a2,%d0.w)
    adda.w  %d2,%a0
    addq.w  #1,%d4
    dbf     %d6,1b
    rts
