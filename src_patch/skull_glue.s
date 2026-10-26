| Engine side of skull.c (stage 5's skulls, enemy type 9, arcade $CC45).
|
| $110452: `jmp skull_entry` over `tst.b 4(a4)` / `beq.s $1104A0`, the type-9
| entry of the stage 3-6 object pass ($105C58, a4 = the slot, a3 = the pass
| context $FFA200). In stage 5 (stage index 4) states 0-2 go to skull_update;
| elsewhere (the dragon's fire, stages 3, 4 and 6) and in state 3 (removal)
| the port's own code runs. skull_update is C (d2-d7/a2-a6 kept); a0/a1
| and d0/d1 are free here as in the port's handler ($1074DC uses them).
    .global skull_entry, sk_floor, sk_sound

skull_entry:
    tst.b   4(%a4)
    beq.s   9f
    cmpi.b  #4,0xFFC512
    bne.s   1f
    cmpi.b  #3,7(%a4)
    bcc.s   1f
    move.l  %a6,sk_a6
    move.l  %a0,sk_ctx+12            | the terrain map (the pass's a0)
    move.l  %a0,-(%sp)
    move.l  %a3,-(%sp)              | context
    move.l  %a4,-(%sp)              | slot
    jsr     skull_update
    addq.l  #8,%sp
    move.l  (%sp)+,%a0
9:  rts
1:  jmp     0x110458

| C: long sk_floor(void *slot): the port's floor probe for the slot's size
| class (+25) at its x/y ($107ED6 -> $85D2, the arcade's $8CA7; the terrain
| map, the pass's a0, at +12 of the context it's given): 0 when there is no floor, else $10000 | the y
| adjustment (word).
sk_floor:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  48(%sp),%a4
    lea     sk_ctx,%a3               | +12 = the terrain map, as $107ED6 reads it
    jsr     0x107ED6
    tst.l   %d0
    beq.s   1f
    andi.l  #0xFFFF,%d1
    move.l  %d1,%d0
    ori.l   #0x10000,%d0
1:  movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| C: void sk_sound(int id): the sound id on the queue at a6 ($8846; the
| arcade's $7915 requests, like $79E7, send no $FF after it)
sk_sound:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  sk_a6,%a6
    move.l  48(%sp),%d0
    jsr     0x8846
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| C: void sk_sound2(int id): id then $FF ($7958-style requests, like $79B5)
    .global sk_sound2
sk_sound2:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  sk_a6,%a6
    move.l  48(%sp),%d0
    jsr     0x8846
    move.w  #0xFF,%d0
    jsr     0x8846
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

    .bss
    .even
sk_a6:  .space 4
sk_ctx: .space 16
