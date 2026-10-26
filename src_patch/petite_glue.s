| Engine side of petite.c (the Petite Devils, enemy type 2, arcade $A89C).
|
| $10C99A: `jmp petite_entry` over `jmp $11C5C2` + nop, the type-2 handler both
| object passes call ($6FE2 in stages 1-2, $105C34 in stages 3-6) with a4 = the
| slot and a3 = the pass context (24 bytes: camera x/y, Arthur x/y, the frame
| counter, slot counter and rank at +8/+9/+10). $11C5C2 sent stage 2's states
| 0/1 to $3416AA, state 2 to $11BC0A and everything else to $11AEE2; those
| save d4-d7/a0/a3-a6, as this does. States 0 and 1 go to petite_update, 2
| (dying) and 3 (removed) still to $11C5C2.
    .global petite_entry, pd_sound, petite_shot_aim, petite_shot_vel_sel

petite_entry:
    cmpi.b  #2,7(%a4)
    bcc.s   1f
    movem.l %d4-%d7/%a0/%a3-%a6,-(%sp)
    move.l  %a6,pd_a6
    move.l  %a3,-(%sp)              | context
    move.l  %a4,-(%sp)              | slot
    jsr     petite_update
    addq.l  #8,%sp
    movem.l (%sp)+,%d4-%d7/%a0/%a3-%a6
    rts
1:  jmp     0x11C5C2

| C: void pd_sound(int id): sound id then $FF on the queue at a6 ($8846)
pd_sound:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  pd_a6,%a6
    move.l  48(%sp),%d0
    jsr     0x8846
    move.w  #0xFF,%d0
    jsr     0x8846
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| $72B6, the port's type-6 shot set-up: `jsr petite_shot_aim` + nop over
| `jsr $7442` (the direction to Arthur) / `move.b d0,24(a4)`. A devil's
| fireball (+8 = $D8) keeps the arcade's shot-8 direction from +9 (0 right,
| 1 left, 2 down -> 0, 8, 4); d0 = the direction as before.
petite_shot_aim:
    cmpi.b  #0xD8,8(%a4)
    bne.s   1f
    moveq   #0,%d0
    move.b  9(%a4),%d0
    andi.w  #3,%d0
    move.b  2f(%pc,%d0.w),%d0
    move.b  %d0,24(%a4)
    rts
1:  jsr     0x7442
    move.b  %d0,24(%a4)
    rts
2:  .byte   0, 8, 4, 0

| $72F2, its move: `jsr petite_shot_vel_sel` over `lea $29238,a1` (the 16
| directions at 2.26 px/frame): a devil's fireball moves at the arcade's
| shot-8 speeds for its rank (+11, petite_shot_vel).
petite_shot_vel_sel:
    lea     0x29238,%a1
    cmpi.b  #0xD8,8(%a4)
    bne.s   1f
    lea     petite_shot_vel,%a1
    move.l  %d1,-(%sp)
    moveq   #3,%d1
    and.b   11(%a4),%d1
    lsl.w   #6,%d1
    adda.w  %d1,%a1
    move.l  (%sp)+,%d1
1:  rts

    .bss
    .even
pd_a6:  .space 4
