| Co-op speed (docs/ACCURACY.md, Fixed 82): the slot loops of the enemy
| passes and sprite builds in fewer cycles, the same RAM and VDP writes.
| Each routine below states the code it replaces and what it keeps.
| The code sits after all the other files' constant data (link.ld puts
| .rodata* after .text*; this is the last object), so adding it moves no
| data the game uploads by DMA.

    .section .rodata.speed

| ---------------------------------------------------------------------------
| The stage 1-2 sprite build's slot loop ($B258; the type table at $B2B4 is
| inplace/spr12.s). $B282: `jmp spr12_top` over `move.w d4,d0` / `move.w
| d7,d1` / `moveq #1,d2`; $B36A (where every draw routine comes back): `jmp
| spr12_tail` over `add.w d0,d4` / `sub.w d0,d7`. An empty slot went to
| $B392 (the last entry's link cleared once anything is in the buffer, d0 = d1
| = 0) and through the sums; a live slot off the screen checked its type
| against the build's list ($30DBF: the fault at $B3A4 for any other) and did
| the same. Now both take the clear and the next slot directly; d0-d2 are
| set again at every live slot and after the loop ($B37C), as before, and d3
| is the type as before.
    .global spr12_top, spr12_tail
spr12_top:
    tst.b   4(%a4)
    beq.s   2f                      | empty
    move.w  %d4,%d0
    move.w  %d7,%d1
    moveq   #1,%d2
    tst.b   5(%a4)
    bne.s   1f                      | on the screen: $B2B4, the type table
    moveq   #0,%d3
    move.b  10(%a4),%d3
    cmpi.w  #17,%d3
    bhi.s   9f
    move.l  #0x30DBF,%d0
    btst    %d3,%d0
    beq.s   9f
2:  tst.w   %d4
    beq.s   3f
    andi.w  #0xFF00,-6(%a5)
3:  lea     48(%a4),%a4
    dbf     %d6,spr12_top
    jmp     0xB378
1:  jmp     0xB2B4
9:  jmp     0xB3A4
spr12_tail:
    add.w   %d0,%d4
    sub.w   %d0,%d7
    add.w   %d1,%d5
    lea     48(%a4),%a4
    dbf     %d6,spr12_top
    jmp     0xB378

| ---------------------------------------------------------------------------
| The stage 1-2 enemy pass's slot loop ($69A2, from se_objpass). $69CA: `jmp
| op12_top` over the slot counter's `move.w d7,d0` / `addq.w #1,d0`; $6BFC
| (the next slot, where every path ends): `jmp op12_next` over `adda.w #48,a4`;
| $6B04 (after a handler, for the hit tests): `jmp op12_hit` over `jmp
| $114CDA`. A live slot went from its type (the table at $69FA) through
| $114C90 (the touch test on every fourth frame of each slot), $6A88, the
| handler pick obj_dispatch (glue.s) and its stub: four jumps and a table.
| Now the table's index jumps straight to the stub's `moveq #k,d4` / `jmp
| target`, with the same registers (d0-d2 as $114C90 or $BD9E left them, d4
| = k) and the flags of that moveq. $114CDA (odd frames: the type-13 extra
| test $114D76, which does nothing for any other type; even frames: the hit
| tests at $6B0C once a weapon is out, 50(a3)) is inlined, the call made for
| type 13 only.
    .global op12_top, op12_next, op12_hit
op12_top:
    move.w  %d7,%d0
    addq.w  #1,%d0
    move.b  %d0,7(%a3)
    tst.b   4(%a4)
    beq.w   op12_next
    moveq   #0,%d0
    move.b  10(%a4),%d0
    cmpi.w  #18,%d0
    bcc.s   8f
    moveq   #0,%d4
    move.b  1f(%pc,%d0.w),%d4
    bmi.s   8f
    moveq   #0,%d0                  | $114C90
    move.b  7(%a3),%d0
    add.b   6(%a3),%d0
    andi.w  #3,%d0
    beq.w   5f
4:  lsl.w   #3,%d4
    jmp     2f(%pc,%d4.w)
8:  jmp     0x69F4                  | the fault (type out of range)
1:  .byte   0x06, 0x03, 0x0D, 0x05, 0x0C, 0x04, 0xFF, 0x08, 0x07, 0xFF, 0x09, 0x00, 0xFF, 0xFF, 0x0E, 0xFF, 0x01, 0x02
    .macro  op12s k, at             | 8 bytes each (jmp kept absolute long)
    moveq   #\k,%d4
    .word   0x4EF9
    .long   \at
    .endm
2:  op12s 0, 0x6ADC
    op12s 1, 0x6AE2
    op12s 2, 0x6AE2
    op12s 3, 0x6CB8
    op12s 4, 0x6D7C
    op12s 5, 0x6E02
    op12s 6, 0x6E7C
    op12s 7, 0x6EE4
    op12s 8, 0x6EEE
    op12s 9, 0x6D22
    op12s 10, 0x6AE2
    op12s 11, 0x6AE2
    op12s 12, 0x6F4E
    op12s 13, 0x6FA4
    op12s 14, 0x6F44
5:  move.w  (%a3),%d0               | $114CA6: the touch test
    move.w  2(%a3),%d1
    moveq   #0,%d2
    move.b  25(%a4),%d2
    cmpi.w  #11,%d2
    bcc.s   9f
    lsl.w   #3,%d2
    move.l  %a3,-(%sp)
    lea     0x2AC3C,%a3
    adda.w  %d2,%a3
    jsr     0xBD9E
    movea.l (%sp)+,%a3
    bra.w   4b
9:  jmp     0x6C96                  | the fault (size class out of range)
op12_hit:
    btst    #0,6(%a3)
    bne.s   1f
    tst.w   50(%a3)
    beq.s   op12_next
    jmp     0x6B0C
1:  cmpi.b  #13,10(%a4)
    bne.s   op12_next
    move.l  %a0,-(%sp)
    movea.l 12(%a3),%a0
    jsr     0x114D76
    movea.l (%sp)+,%a0
op12_next:
    lea     48(%a4),%a4
    dbf     %d7,op12_top
    jmp     0x6C04

| ---------------------------------------------------------------------------
| Waiting enemies off the screen. Each handler below saved and restored 11
| registers and went through its state tests to change nothing; these take
| the same tests up front and return what the handler returned (d0 = 0, the
| flags of its last test), everything else to the handler as before.

| Type 1 in stages 1-2 (the crows, $44FE; from $6CB8): state 1, waiting
| (+8 = 0, +9 = 0), off the screen (+5 = 0), +6 = 3 or 5 (4 is another
| path, anything else the fault). `jmp t1_entry` over `movem.l
| d4-a0/a3-a6,-(sp)` and the opcode of `tst.b 4(a4)`.
    .global t1_entry
t1_entry:
    cmpi.b  #1,7(%a4)
    bne.s   9f
    tst.b   8(%a4)
    bne.s   9f
    tst.b   9(%a4)
    bne.s   9f
    cmpi.b  #1,10(%a4)
    bne.s   9f
    move.b  6(%a4),%d0
    cmpi.b  #3,%d0
    beq.s   1f
    cmpi.b  #5,%d0
    bne.s   9f
1:  tst.b   4(%a4)
    beq.s   9f
    tst.b   5(%a4)
    bne.s   9f
    moveq   #0,%d0                  | +9 as $4804 loads it; Z set as by $486A
    rts
9:  movem.l %d4-%d7/%a0/%a3-%a6,-(%sp)
    tst.b   4(%a4)
    jmp     0x4506

| Type 10 in every stage (the window devils of stage 2 and their kin, $11B1BC;
| from $6D22 and $105976 through $A536): state 0 with its set-up done (+8
| non-zero), off the screen; not an Astaroth shot picture (+41 = $A5,
| hook_ast_shot). `jmp ta_entry` over `movem.l d4-a0/a3-a6,-(sp)` and the
| opcode of `tst.b 4(a4)`.
    .global ta_entry
ta_entry:
    tst.b   7(%a4)
    bne.s   9f
    cmpi.b  #10,10(%a4)
    bne.s   9f
    cmpi.b  #0xA5,41(%a4)
    beq.s   9f
    tst.b   8(%a4)
    beq.s   9f
    tst.b   4(%a4)
    beq.s   9f
    tst.b   5(%a4)
    bne.s   9f
    moveq   #0,%d0                  | +7 as $11B1D2 loads it; Z set as by $11BA92
    rts
9:  movem.l %d4-%d7/%a0/%a3-%a6,-(%sp)
    tst.b   4(%a4)
    jmp     0x11B1C4
