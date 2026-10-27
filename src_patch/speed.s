| Co-op speed (docs/ACCURACY.md, Fixed 82): the slot loops of the enemy
| passes and sprite builds in fewer cycles, the same RAM and VDP writes.
| Each routine below states the code it replaces and what it keeps.

    .text

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
