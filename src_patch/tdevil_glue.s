| Engine side of tdevil.c (stage 2's type-4 devils, arcade handler $B146).
|
| $107A5E: `jmp tdevil_entry` + nop over `moveq #0,d0 / move.b 7(a4),d0 /
| beq.w $107AA2` in the port's type-4 handler ($107A48, called from the
| object pass stub $105B9E with a4 = the slot, a3 = the pass context $FFC700:
| camera x/y, Arthur x/y words, the frame counter, the slot counter and the
| rank at +8/+9/+10, the terrain map at +12; a6 = the sound queue). States 0
| and 1 go to tdevil_update; 2 (dying) and 3 (removed) stay the port's. The
| handler saved d4-d7/a0/a3-a6 and restores them at $107F12.
    .global tdevil_entry, tdv_floor, tdv_sound

tdevil_entry:
    moveq   #0,%d0
    move.b  7(%a4),%d0
    cmpi.b  #2,%d0
    bcc.s   1f
    move.l  %a6,tdv_a6
    move.l  %a3,-(%sp)              | context
    move.l  %a4,-(%sp)              | slot
    jsr     tdevil_update
    addq.l  #8,%sp
    jmp     0x107F12
1:  jmp     0x107A68                | the port's dying / removal states, d0 = state

| C: long tdv_floor(void *slot, void *ctx): the port's floor probe for the
| slot's size class (+25) at its x/y ($107ED6 -> $85D2, the arcade's $8CA7):
| 0 when there is no floor, else $10000 | the y adjustment (word).
tdv_floor:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  48(%sp),%a4
    move.l  52(%sp),%a3
    jsr     0x107ED6
    tst.l   %d0
    beq.s   1f
    andi.l  #0xFFFF,%d1
    move.l  %d1,%d0
    ori.l   #0x10000,%d0
1:  movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| C: void tdv_sound(int id): sound id then $FF on the queue at a6 ($8846)
tdv_sound:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  tdv_a6,%a6
    move.l  48(%sp),%d0
    jsr     0x8846
    move.w  #0xFF,%d0
    jsr     0x8846
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| $468E (the crows' flight start, subtypes 4 and 5): `jsr crow_fly_tab` over
| `lea 0x4E8F6,a1`. The flight frames by facing: $4E8F6 holds stage 1's
| numbers (31, 13: frames 1-36, the stage 1 build's), $4E90A stage 2's (79,
| 61: the same poses at 49-84, $B152's records, where 1-36 are empty).
| Subtype 4 is stage 2's (the building's crows), and was drawn from nothing.
    .global crow_fly_tab
crow_fly_tab:
    lea     0x4E8F6,%a1
    cmpi.b  #4,6(%a4)
    bne.s   1f
    lea     0x4E90A,%a1
1:  rts

    .bss
    .even
tdv_a6: .space 4
