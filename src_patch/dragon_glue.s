| The dragon (stages 3, 4 and 6) and its fire: engine side of dragon.c.
|
| $106F80: `jmp dragon_entry` over the type-12 handler's first instruction.
| Called by the object pass ($105902) with a4 = the slot, a3 = the pass
| context ($FFC960: camera x/y, Arthur x/y words, the frame counter $FFA206 at
| +8, the slot counter at +9, the projectile list at +12), a5 = the enemy
| free list ($FFB300) and a6 = the sound queue. The original saved d4-a6
| (d0-d3 are free); C keeps d2-d7/a2-a6, so a0/a1 are saved here.
|
| Speed: the body segments (8 of the 9 nodes) in state 1 are handled here
| without the C call: segment() and the far-off-screen check of
| dragon_update(), the same steps on the same fields (dragon_vel is the C
| table). Everything else (the head, set-up, death, removal) goes to C.
    .global dragon_entry, dragon_spawn_pos, dragon_wtest
    .global eng_alloc, eng_free, eng_sound, eng_score, eng_boss_init, eng_boss_done

dragon_entry:
    move.l  %a6,dr_a6
    cmpi.b  #12,10(%a4)
    bne.w   .Lc
    cmpi.b  #1,7(%a4)               | state 1 (a dead slot, alloc 0, never is)
    bne.w   .Lc
    tst.b   4(%a4)
    beq.w   .Lc
    tst.b   12(%a4)                 | kind: 0 = the head
    beq.w   .Lc
    tst.b   27(%a4)                 | segment(): frozen
    bne.w   .Lrange
    tst.b   35(%a4)                 | a pending direction ...
    beq.s   .Lmove
    subq.b  #1,34(%a4)              | ... whose delay runs out now
    bne.s   .Lmove
    move.b  33(%a4),%d0
    move.b  %d0,32(%a4)             | dir = pdir
    clr.b   35(%a4)
    moveq   #0,%d1
    move.w  40(%a4),%d1             | next
    beq.s   .Lmove
    move.l  %a0,-(%sp)
    ori.l   #0xFF0000,%d1
    movea.l %d1,%a0
    move.b  %d0,33(%a0)             | it goes on down the chain
    moveq   #7,%d0
    cmpi.b  #2,12(%a0)
    bne.s   1f
    moveq   #6,%d0                  | to the tail
1:  move.b  %d0,34(%a0)
    move.b  #1,35(%a0)
    move.l  (%sp)+,%a0
.Lmove:                             | move(): 2 px/frame in one of 16 directions
    move.l  %a0,-(%sp)
    moveq   #0,%d0
    move.b  32(%a4),%d0
    lsl.w   #2,%d0
    lea     dragon_vel,%a0
    adda.w  %d0,%a0
    move.w  (%a0)+,%d1
    ext.l   %d1
    add.l   16(%a4),%d1
    andi.l  #0xFFFFFF,%d1
    move.l  %d1,16(%a4)
    lsr.l   #8,%d1
    move.w  %d1,(%a4)
    move.w  (%a0),%d1
    ext.l   %d1
    add.l   20(%a4),%d1
    andi.l  #0xFFFFFF,%d1
    move.l  %d1,20(%a4)
    lsr.l   #8,%d1
    move.w  %d1,2(%a4)
    move.l  (%sp)+,%a0
.Lrange:                            | $D6DE: lost when far off screen (not in stage 3)
    cmpi.b  #2,0xFFC512
    beq.s   2f
    move.w  (%a4),%d0
    sub.w   (%a3),%d0
    addi.w  #0x180,%d0
    cmpi.w  #0x400,%d0
    bhi.s   1f
    move.w  2(%a4),%d0
    sub.w   2(%a3),%d0
    addi.w  #0x180,%d0
    cmpi.w  #0x400,%d0
    bls.s   2f
1:  move.b  #3,7(%a4)
    clr.b   8(%a4)
    clr.b   9(%a4)
2:  rts

.Lc:
    movem.l %a0-%a1,-(%sp)
    move.l  %a5,-(%sp)              | enemy free list
    move.l  %a3,-(%sp)              | context
    move.l  %a4,-(%sp)              | slot
    jsr     dragon_update
    lea     12(%sp),%sp
    movem.l (%sp)+,%a0-%a1
    rts

| a2 = list's next free slot ($7BD2 pops it), or 0 when the list is empty.
| C: void *eng_alloc(void *list)
eng_alloc:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  48(%sp),%a4
    jsr     0x7BD2
    move.l  %a2,%d0
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| C: void eng_free(void *list, void *slot)   ($7BEC pushes it back)
eng_free:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  48(%sp),%a4
    move.l  52(%sp),%a2
    jsr     0x7BEC
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| C: void eng_sound(int id): the sound queue at a6 ($8846), id then $FF as the
| game's own one-shot calls ($B782, $B7F2, $B842: ids $0F, $1B, $21) do.
eng_sound:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  dr_a6,%a6
    move.l  48(%sp),%d0
    jsr     0x8846
    move.w  #0xFF,%d0
    jsr     0x8846
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| C: void eng_score(int msg): a $0Cxx score message on the queue at $FFB400 ($7C1C)
eng_score:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  48(%sp),%d0
    lea     0xFFB400,%a4
    jsr     0x7C1C
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| C: void eng_boss_init(void *slot), eng_boss_done(void *slot): the port's boss
| count for the stage-end key ($10E9B6 at the head's start, $10EA0C when it
| is removed; both look at the slot's type, stage 6's dragon counts nothing).
eng_boss_init:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  48(%sp),%a4
    jsr     0x10E9B6
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts
eng_boss_done:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  48(%sp),%a4
    jsr     0x10EA0C
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| $106F10: `jsr dragon_spawn_pos` + `bra` to $106F3C over the spawner's
| position code (a2 = the new slot, a3 = the spawn context: camera x at +0,
| camera y at +14). The arcade's spawn records ($EB43: relative to the camera,
| or absolute with bit 0 of the record's +2, $EB5B): stages 3 and 4 put the
| head at camera + ($180, $40), stage 6 at the absolute (7824, 2016)
| ($1E90, $07E0) in the tower. The port used the camera offsets everywhere.
dragon_spawn_pos:
    move.w  0xFF9100,%d0
    add.w   #0x180,%d0
    move.w  0xFF9102,%d1
    add.w   #0x40,%d1
    cmpi.b  #5,0xFFC512
    bne.s   1f
    move.w  #0x1E90,%d0
    move.w  #0x07E0,%d1
1:  move.w  %d0,(%a2)
    move.w  %d1,2(%a2)
    andi.l  #0xFFFF,%d0
    lsl.l   #8,%d0
    move.l  %d0,16(%a2)
    andi.l  #0xFFFF,%d1
    lsl.l   #8,%d1
    move.l  %d1,20(%a2)
    move.b  #1,9(%a2)               | just spawned: set up next update (as the arcade)
    rts

| $114D58: `jmp dragon_wtest` over `cmpi.b #12,10(a4)` / `jmp $105796`, the
| object pass's way into its weapon test ($1057A0, every other update; $105798,
| the dragon's own entry, is a nop since every node is a target). For a slot
| that isn't both live and on screen (+4 & +5 = 0) the test ($BE3A) only clears
| its 16-byte hit list and returns nothing, whatever the enemy and whatever the
| weapons are doing (it looks at no weapon before that test); this does what
| $1057A0-$105838 then do (the same RAM, and d0/d1/d2/d6 as they leave them)
| without the table set-up, the call and the message loop. Every type but 8,
| whose test ($7201A) records the slot in RAM and runs its own pass ($71500),
| so type 8 and every live, on-screen slot go to $1057A0 as before.
dragon_wtest:
    cmpi.b  #8,10(%a4)
    beq.s   .Lfull
    move.b  4(%a4),%d1
    and.b   5(%a4),%d1
    bne.s   .Lfull
    tst.b   0xFFC39C                | $1057A0: no weapon tests at all
    bne.s   .Lnext
    moveq   #0,%d2
    move.b  24(%a3),%d2             | the weapon
    cmpi.w  #5,%d2
    bcc.s   .Lerr                   | $1057B4: the game's fault trap
    move.w  %d2,%d1                 | d2 = (d2 * 18 + d4) << 4 ($1057B8-$1057BE)
    lsl.w   #3,%d2
    add.w   %d1,%d2
    add.w   %d2,%d2
    add.w   %d4,%d2
    lsl.w   #4,%d2
    move.l  %a0,-(%sp)
    movea.l 16(%a3),%a0             | $BE3A: its hit list at a6 = 16(a3), cleared
    clr.l   (%a0)+
    clr.l   (%a0)+
    clr.l   (%a0)+
    clr.l   (%a0)
    move.l  (%sp)+,%a0
    moveq   #0,%d0                  | ... and it returns 0 hits, 0 kills
    moveq   #0,%d1
    moveq   #0,%d6                  | $105816: no score messages
    cmpi.w  #11,%d4                 | $105800: the dragon's hit flash
    bne.s   .Lnext
    clr.b   6(%a4)
.Lnext:
    jmp     0x10583C
.Lfull:
    jmp     0x1057A0
.Lerr:
    jmp     0x10587A

    .bss
    .even
dr_a6:  .space 4
