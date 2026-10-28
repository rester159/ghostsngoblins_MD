| Big Men at a floor's edge (type 10, stages 2 and 5; port handler $11B1BC,
| arcade $CF36). The arcade's edge probe ($D0A4: the floor 2 px below, $8CA7)
| notes the facing of the first step over an edge (<$14 = facing, $F = 1,
| until a floor is found again: $F and $15 cleared); walking (sub-state 0,
| $D047) it turns round when it faces that way again (once); facing Arthur
| (sub-state 1, step 2: $D144) it backs off the edge toward him once ($15)
| or stands still when the edge is on his side. The port's slot keeps them
| at +37 ($F), +38 ($14), +39 ($15); its code rewrote +38 at every step
| over the edge, turned only on every second check while walking (+39 as a
| count), and in sub-state 1 never turned and walked on over the edge.
    .global bm_nofloor, bm_turn0, bm_turn1

| $11B800 (`jmp`): no floor below ($D0B0): +38 and +37 set once
bm_nofloor:
    tst.b   37(%a4)
    bne.s   1f
    move.b  24(%a4),38(%a4)
    move.b  #1,37(%a4)
1:  addq.w  #2,2(%a4)
    jmp     0x11B810

| $11B35C (`jmp`): walking, every 16 frames after the probe ($D047): turn
| round when facing the way it stepped over the edge
bm_turn0:
    tst.b   37(%a4)
    beq.s   9f
    move.b  24(%a4),%d0
    cmp.b   38(%a4),%d0
    bne.s   9f
    eori.b  #1,24(%a4)
    moveq   #0,%d0
    jsr     0x11B822                | the walk script ($4F26)
9:  jmp     0x11B38E

| $11B4A0 (`jmp`): sub-state 1 step 2 after the probe ($D147)
bm_turn1:
    tst.b   37(%a4)
    beq.s   8f                      | on a floor: move
    move.w  (%a4),%d0
    cmp.w   4(%a3),%d0
    bhi.s   2f                      | right of Arthur ($D162)
    tst.b   38(%a4)
    beq.s   9f                      | the edge on his side: stand
    tst.b   39(%a4)
    bne.s   8f
    move.b  38(%a4),39(%a4)
    clr.b   24(%a4)                 | toward him (right)
    bra.s   3f
2:  tst.b   38(%a4)
    bne.s   9f
    tst.b   39(%a4)
    bne.s   8f
    move.b  #1,39(%a4)
    move.b  #1,24(%a4)              | toward him (left)
3:  moveq   #0,%d0
    jsr     0x11B822
8:  jmp     0x11B4E2                | the move ($D179)
9:  jmp     0x11B4EE                | no move ($D188)

| The type-10 builder ($AF1E/$AF4A) draws Big Men (stages 2 and 5) and, in
| the final room, Astaroth's flames from the same frame records ($125620 via
| $123B3E). Their 16 px halves were swapped for the flames (Fixed 21), which
| split every Big Man down the middle (its pieces are the arcade's, placed
| as the original records place them); now the swap is made here, in the
| final room only. $AFB2 (`jsr`, over move.w (a2),d2 / add.w (a1),d2 /
| sub.w (a3),d2): a2 = the piece record (x first), a1 = the slot, a3 = the
| camera.
    .global bm_piece_x
bm_piece_x:
    move.w  (%a2),%d2
    cmpi.b  #6,0xFFC512             | the final room
    bne.s   1f
    neg.w   %d2
    subi.w  #16,%d2                 | 0 <-> -16
1:  add.w   (%a1),%d2
    sub.w   (%a3),%d2
    rts


| $AFF4 (`jsr`, over move.w 4(a2),4(a5)): the piece's attribute; in stage 5
| the Big Man's pose from its VRAM slot (bmart.c), elsewhere as before.
    .global bm_attr_hook
bm_attr_hook:
    cmpi.b  #4,0xFFC512
    beq.s   1f
    move.w  4(%a2),4(%a5)
    rts
1:  movem.l %d0-%d1/%a0-%a1,-(%sp)
    move.l  %a2,-(%sp)
    move.l  %a1,-(%sp)
    jsr     bm_attr
    addq.l  #8,%sp
    move.w  %d0,4(%a5)
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts

| $A226 (`jsr` + nop, over move.w $14C9B4,4(a5)): the stage 1-2 build's type-4
| platform attribute (tile $7F0, line 0); stage 2's stepping stones from their
| arcade stone art, tile $48C, line 1 (bossart.c stone_load).
    .global stone_attr
stone_attr:
    move.w  0x14C9B4,4(%a5)
    cmpi.b  #1,0xFFC512
    bne.s   1f
    move.w  #0x248C,4(%a5)
1:  rts
