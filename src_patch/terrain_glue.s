| Hooks for terrain.c (the collision ring as the arcade writes it; docs/ACCURACY.md, Fixed 61).

    .section .text,"ax"
    .global ter_cam, maprow_noring

| $1043B4 (the camera update $104382, every stage loop): `jsr ter_cam` + 2 nops over
| `move.w #91,$FFC370` / `bsr.s $1043C4` (the camera's x/y to $FF9100/$FF9102). The caller
| restores every register after.
ter_cam:
    move.w  #91,0xFFC370
    move.w  28(%a3),0xFF9100
    move.w  30(%a3),0xFF9102
    jmp     ter_update

| $938E (the collision ring's row fill, called before each stage's row of plane entries):
| `jmp maprow_noring` over `movem.l d4-d7,-(sp) / moveq #1,d7`. Writes no cells now;
| leaves d0 = 32 and d1 as the fill left it, which the callers' plane loops add (d1.l): the
| last cell's attribute byte if that cell is in the map (row d1 - 5, columns d0 .. d0 + 31,
| map a3: +0 x0, +2 y0, +4 w, +6 h, +12 attributes), else $C0 in the low word over 0 if any
| cell was in the map, or over the entry d1's upper word. a0 as a lookup leaves it.
maprow_noring:
    movem.l %d2-%d4,-(%sp)
    move.l  %d1,%d4
    move.w  %d1,%d2
    subq.w  #5,%d2
    sub.w   2(%a3),%d2              | row in the map
    cmp.w   6(%a3),%d2
    bcc.s   3f
    sub.w   (%a3),%d0               | first column in the map
    moveq   #31,%d3
1:  cmp.w   4(%a3),%d0
    bcc.s   2f
    moveq   #0,%d4                  | a cell in the map
2:  addq.w  #1,%d0
    dbf     %d3,1b
    subq.w  #1,%d0                  | the last cell
    cmp.w   4(%a3),%d0
    bcc.s   3f
    mulu.w  6(%a3),%d0
    andi.l  #0xFFFF,%d2
    add.l   %d2,%d0
    movea.l 12(%a3),%a0
    moveq   #0,%d1
    move.b  0(%a0,%d0.l),%d1
    bra.s   4f
3:  move.l  %d4,%d1
    move.w  #0xC0,%d1
4:  movem.l (%sp)+,%d2-%d4
    moveq   #32,%d0
    rts
