| The dragon (stages 3, 4 and 6) and its fire: engine side of dragon.c.
|
| $106F80: `jmp dragon_entry` over the type-12 handler's first instruction.
| Called by the object pass ($105902) with a4 = the slot, a3 = the pass
| context ($FFC960: camera x/y, Arthur x/y words, the frame counter $FFA206 at
| +8, the slot counter at +9, the projectile list at +12), a5 = the enemy
| free list ($FFB300) and a6 = the sound queue. The original saved d4-a6
| (d0-d3 are free); C keeps d2-d7/a2-a6, so a0/a1 are saved here.
    .global dragon_entry, dragon_spawn_pos
    .global eng_alloc, eng_free, eng_sound, eng_score, eng_boss_init, eng_boss_done

dragon_entry:
    movem.l %a0-%a1,-(%sp)
    move.l  %a6,dr_a6
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

    .bss
    .even
dr_a6:  .space 4
