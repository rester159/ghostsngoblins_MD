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
    tst.b   4(%a4)
    beq.w   6f
op12_live:
    move.w  %d7,%d0
    addq.w  #1,%d0
    move.b  %d0,7(%a3)
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
| A run of empty slots: each set the slot counter 7(a3) (= d7 + 1, through
| d0's low word) and went on; nothing reads it before the next live slot sets
| it again or the pass clears it at the end ($6C04), so only d0 is kept: its
| low word is 1 when the last slot was empty, as before.
6:  lea     48(%a4),%a4
    dbf     %d7,7f
    move.w  #1,%d0
    jmp     0x6C04
7:  tst.b   4(%a4)
    beq.s   6b
    bra.w   op12_live

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

| ---------------------------------------------------------------------------
| The stage 3-6 enemy pass's slot loop ($1055D4, from se_objpass2), as
| op12 for stages 1-2. $1055DA: `jmp op36_top` over the slot counter's
| `move.w d7,d0` / `addq.w #1,d0`; $10583C (the next slot): `jmp op36_next`
| over `clr.w $FFC9D8`; $105790 (after a handler): `jmp op36_hit` over `jmp
| $114D50`. A live slot went $1055EA -> $114BF2 (the type's index, table
| $114C22) -> $1056C0 -> $114D06 (the touch test on every fourth frame) ->
| $1056E8 -> $114C18 (the handler from the table at $114C48, pushed and
| entered by rts after `lsr.w #2,d4`). Now one table of `moveq #4k,d4` /
| `lsr.w #2,d4` / `jmp handler`: the same d0-d2, d4 = k and the flags of that
| lsr (X clear). After the handler, odd frames ran $114D76 for every slot
| (only type 13 does anything there), even frames dragon_wtest (unchanged).
| The first slot comes in at op36_first (the hook at $1055DA): an empty one
| clears $FFC9D8 as its pass end did, then empty runs go as in op12 (their
| clears repeat the one after the slot before).
    .global op36_first, op36_top, op36_next, op36_hit
op36_first:
    tst.b   4(%a4)
    bne.s   op36_live
    clr.w   0xFFC9D8
    bra.w   6f
op36_top:
    tst.b   4(%a4)
    beq.w   6f
op36_live:
    move.w  %d7,%d0
    addq.w  #1,%d0
    move.b  %d0,7(%a3)
    moveq   #0,%d4                  | $114BF2
    move.b  10(%a4),%d4
    cmpi.w  #18,%d4
    bhi.s   8f
    add.w   %d4,%d4
    move.w  1f(%pc,%d4.w),%d4
    bmi.s   8f
    moveq   #0,%d0                  | $114D06
    move.b  7(%a3),%d0
    add.b   6(%a3),%d0
    andi.w  #3,%d0
    beq.w   5f
4:  lsl.w   #4,%d4
    jmp     2f(%pc,%d4.w)
8:  moveq   #17,%d4                 | $114C10: the fault
    jmp     0x10587A
1:  .word   6, 3, 13, 5, 12, 4, 16, 8, 7, 15, 9, 0, 11, 17, 14, -1, 1, 2, 10
    .macro  op36s k, at             | 16 bytes each
    moveq   #4*\k,%d4
    lsr.w   #2,%d4
    .word   0x4EF9
    .long   \at
    .word   0, 0, 0
    .endm
2:  op36s 0, 0x105764
    op36s 1, 0x10576C
    op36s 2, 0x10576C
    op36s 3, 0x10589E
    op36s 4, 0x1059C2
    op36s 5, 0x105A5A
    op36s 6, 0x105AD6
    op36s 7, 0x105B40
    op36s 8, 0x105B4A
    op36s 9, 0x105976
    op36s 10, 0x105942
    op36s 11, 0x105902
    op36s 12, 0x105B9E
    op36s 13, 0x105BEE
    op36s 14, 0x105C4E
    op36s 15, 0x105C58
    op36s 16, 0x105C6C
    op36s 17, 0x105C62
5:  move.w  (%a3),%d0               | $114D1C: the touch test
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
9:  jmp     0x10587A                | the fault (size class out of range)
op36_hit:
    btst    #0,6(%a3)
    bne.s   1f
    jmp     dragon_wtest            | as $114D58
1:  cmpi.b  #13,10(%a4)
    bne.s   op36_next
    move.l  %a0,-(%sp)              | $114D64
    movea.l 12(%a3),%a0
    jsr     0x114D76
    movea.l (%sp)+,%a0
op36_next:
    clr.w   0xFFC9D8
    lea     48(%a4),%a4
    dbf     %d7,op36_top
    jmp     0x10584A
6:  lea     48(%a4),%a4
    dbf     %d7,7f
    move.w  #1,%d0
    jmp     0x10584A
7:  tst.b   4(%a4)
    beq.s   6b
    bra.w   op36_live

| Type 1 in stages 3-6 ($10505C; from $10589E): state 1, waiting (+8 = 0,
| +9 non-zero), off the screen, +6 = 2 (anything else the fault). `jmp
| t1b_entry` over `movem.l d4-a0/a3-a6,-(sp)` and the opcode of `tst.b 4(a4)`.
    .global t1b_entry
t1b_entry:
    cmpi.b  #1,7(%a4)
    bne.s   9f
    tst.b   8(%a4)
    bne.s   9f
    tst.b   9(%a4)
    beq.s   9f
    cmpi.b  #1,10(%a4)
    bne.s   9f
    cmpi.b  #2,6(%a4)
    bne.s   9f
    tst.b   4(%a4)
    beq.s   9f
    tst.b   5(%a4)
    bne.s   9f
    moveq   #0,%d0                  | +8 as $10513C loads it; Z set as by $10518C
    rts
9:  movem.l %d4-%d7/%a0/%a3-%a6,-(%sp)
    tst.b   4(%a4)
    jmp     0x105064

| ---------------------------------------------------------------------------
| The type-5 handler $3420 (stages 3-6 from $1059C2, stages 1-2 from $6DF0)
| copies the slot (48 bytes) and its 16-byte extension into the work buffer
| at 16(a3) and back after the state routine, each with a dbf loop of
| move.l; the same moves unrolled. $3448: `jmp t5_in` over the copy in, back
| at $3460 with a0 and a2 past the copies and d0 = $FFFF as the loops left
| them; $34B4: `jmp t5_out` over the copy back, on to $34D4 as `bra.s` there
| did (d0 is then the result, a0-a2 restored).
    .global t5_in, t5_out
t5_in:
    move.l  #0xFFFF,%d0             | (first: the flags are the last move's)
    movea.l %a4,%a0
    movea.l 16(%a3),%a2
    .rept   12
    move.l  (%a0)+,(%a2)+
    .endr
    movea.l %a1,%a0
    .rept   4
    move.l  (%a0)+,(%a2)+
    .endr
    jmp     0x3460
t5_out:
    move.l  #0xFFFF,%d0
    movea.l %a4,%a0
    .rept   12
    move.l  (%a2)+,(%a0)+
    .endr
    .rept   4
    move.l  (%a2)+,(%a1)+
    .endr
    jmp     0x34D4

| The same in the type-8 handler $7149C (stage 6's, from $105B40 via $71F32):
| $714C2 `jmp t8_in` over the copy in (this one steps a1 itself; the caller's
| a1/a2/a4 are back from the stack at $714DC), back at $714D4; $714E0 `jmp
| t8_out` over the copy back, on to $714F8 as its `bra.s` did.
    .global t8_in, t8_out
t8_in:
    move.l  #0xFFFF,%d0
    movea.l %a4,%a0
    .rept   12
    move.l  (%a0)+,(%a2)+
    .endr
    .rept   4
    move.l  (%a1)+,(%a2)+
    .endr
    jmp     0x714D4
t8_out:
    move.l  #0xFFFF,%d0
    movea.l %a4,%a0
    .rept   12
    move.l  (%a2)+,(%a0)+
    .endr
    .rept   4
    move.l  (%a2)+,(%a1)+
    .endr
    jmp     0x714F8
