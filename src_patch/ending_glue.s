| The end of the final room: engine side of ending.c. Hooks: tools/patch_gng.py
| install_ending.

    .text
    .global hook_room_end, hook_end, hook_end_tspr, hook_end_build, hook_end_vbl
    .global end_trigger, end_text, end_black, end_black_all, end_time_off, end_50k, end_sound
    .global end_to_map, end_restart, hook_end_restore

| $10EA5A / $1174B2: `jmp hook_room_end` over the port's room-end block
| (after the last boss of stages 2-6 is removed: $FFDB08 = 1, a 240-frame
| wait $FFDB0A, 1,000 points ($0C09), sound $3F). In the final room the
| arcade has none of it ($E844 at stage index 6: no sound, no points, the
| ending from the next frame), so there the wait is 0 and nothing else is
| done.
hook_room_end:
    move.b  #1,0xFFDB08
    addq.w  #1,0xFFDB0E
    cmpi.b  #6,0xFFC512
    bne.s   1f
    clr.w   0xFFDB0A
    rts
1:  move.w  #240,0xFFDB0A
    move.l  %a4,-(%sp)
    lea     0xFFB400,%a4
    move.w  #0x0C09,%d0
    jsr     0x7C1C
    move.l  (%sp)+,%a4
    jmp     0xB942

| $113916 (the port's ending routine, `jsr` from the final room's loop at
| $1116F0, which skips the game update when it returns d0 != 0): `jmp
| hook_end`. The whole routine is ending.c's.
hook_end:
    movem.l %d1-%d7/%a0-%a6,-(%sp)
    jsr     end_update
    movem.l (%sp)+,%d1-%d7/%a0-%a6
    tst.w   %d0
    rts

| C: int end_trigger(void): the port's $10EAA4 (1 once the room-end wait is over)
end_trigger:
    movem.l %d1-%d7/%a0-%a6,-(%sp)
    jsr     0x10EAA4
    andi.l  #0xFFFF,%d0
    movem.l (%sp)+,%d1-%d7/%a0-%a6
    rts

| C: void end_text(int id): the text layer cleared ($4EBA) and the port's
| text `id` written into it ($113A88: table $4C1B8, buffer $FFD000)
end_text:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr     0x4EBA
    move.l  64(%sp),%d0
    moveq   #0,%d1
    lea     0x4C1B8,%a0
    lea     0xFFD000,%a4
    jsr     0x4E62
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

| C: void end_50k(void): 50,000 points through the score queue ($0C15)
end_50k:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    lea     0xFFB400,%a4
    move.w  #0x0C15,%d0
    jsr     0x7C1C
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

| C: void end_sound(int id): the port's $89E4
end_sound:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    move.l  64(%sp),%d0
    jsr     0x89E4
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

| C: void end_black(void): the arcade's black screen ($0E00) for a text:
| plane B ($C000, all name data) cleared and plane A ($E000) rows 4-24,
| columns 0-31 only (the screen is 32 columns wide; rows 0-3 are the HUD,
| 25-27 the lives and the weapon; past column 31 plane A holds tiles, the
| HUD font's among them). Display and
| interrupts off for the length of it, so the VBlank's VDP accesses can't
| come in between.
| end_black_all: rows 4-27 (the second clear's last text, $68DF: no lives
| or weapon either)
end_black_all:
    move.w  %sr,-(%sp)
    move.w  #0x2700,%sr
    movem.l %d0-%d3/%a0,-(%sp)
    moveq   #27-4,%d3
    bra.s   3f
end_black:
    move.w  %sr,-(%sp)
    move.w  #0x2700,%sr
    movem.l %d0-%d3/%a0,-(%sp)
    moveq   #24-4,%d3
3:
    lea     0xC00000,%a0
    move.w  #0x8124,4(%a0)          | display off
    move.w  #0x8F02,4(%a0)
    moveq   #0,%d1
    move.l  #0x40000003,4(%a0)      | VRAM $C000: 4 KiB
    move.w  #4096/32-1,%d0
1:  .rept 8
    move.l  %d1,(%a0)
    .endr
    dbf     %d0,1b
    move.l  #0x62000003,%d2         | VRAM $E200: row 4
    move.w  %d3,%d0
2:  move.l  %d2,4(%a0)
    .rept 16
    move.l  %d1,(%a0)               | 32 columns
    .endr
    addi.l  #0x00800000,%d2         | the next row (128 bytes)
    dbf     %d0,2b
    move.w  #0x8164,4(%a0)          | display on (DMA off, as $704BE leaves it)
    movem.l (%sp)+,%d0-%d3/%a0
    move.w  (%sp)+,%sr
    rts

| C: void end_time_off(void): the TIME display erased (the arcade's $011A):
| plane A rows 2 and 3, columns 2-5
end_time_off:
    move.w  %sr,-(%sp)
    move.w  #0x2700,%sr
    move.l  %a0,-(%sp)
    lea     0xC00000,%a0
    move.w  #0x8F02,4(%a0)
    move.l  #0x61040003,4(%a0)      | VRAM $E104: row 2, column 2
    clr.l   (%a0)
    clr.l   (%a0)
    move.l  #0x61840003,4(%a0)      | VRAM $E184: row 3, column 2
    clr.l   (%a0)
    clr.l   (%a0)
    move.l  (%sp)+,%a0
    move.w  (%sp)+,%sr
    rts

| C: void end_to_map(void): after the first clear, stage 1 from its map as
| the arcade's ($7446: <$72 = 0, <$08 = 0): the port's stage advance to the
| map ($113B70, as the stage ends and the developer launch use) with the
| port's first-loop clears ($1139D6), score, lives and the random kept. The
| port went through the game start ($2CC), which plays the opening scene
| instead of the map and reseeds the random.
end_to_map:
    move.w  #0x2700,%sr
    clr.b   0xFF7FC2
    clr.b   0xFFC512
    clr.b   0xFFC894
    clr.b   0xFFC521
    clr.b   0xFFC5FE
    clr.w   0xFFCD78
    clr.w   0xFFCD7A
    jmp     0x113B70

| C: void end_restart(void): after the second clear, the game starts over
| from its opening scene, score and lives kept, as the arcade's ($73F3,
| $7446: mode 0, the opening, then stage 1). Here the port's opening (its
| music $3A and the picture sequence $E0C that the title plays at a game
| start) and then glue.s loop_again (the port's restart through the game
| start, $2CC, which keeps score and lives). The game start reseeds the
| arcade's random (player_init); the arcade's restart doesn't, so its state
| is kept here and put back with the score and lives (hook_end_restore).
end_restart:
    move.w  #0x2700,%sr
    move.l  0xFFC62C,end_rand
    st      end_rand_keep
    clr.b   0xFF7FC2
    moveq   #0x3A,%d0
    jsr     intro_hook              | the opening, as after Start (bossart.c)
    jmp     loop_again

| $414 (the game start, after its inits): `jsr hook_end_restore` over `jsr
| $113AC4` (the port's restore of the score and lives after its restarts).
hook_end_restore:
    jsr     0x113AC4
    tst.b   end_rand_keep
    beq.s   1f
    move.l  end_rand,0xFFC62C
    sf      end_rand_keep
1:  rts

| $1118BC (the final room's sprites while the text layer is on): `jsr
| hook_end_tspr` + nops over `jsr clear_sat` + nops and `move.w #-1,$FFB20C`.
hook_end_tspr:
    jsr     clear_sat
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     end_text_sprites
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts

| $111922: `jsr hook_end_build` + 2 nops over `jsr $111B1A` (the final
| room's sprite build) and `jsr $C35E8`. The scene's sprites go after the
| build's, unless pace.c skipped the build (fs_flags bit 1).
hook_end_build:
    jsr     0x111B1A
    btst    #1,fs_flags+1
    bne.s   1f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     end_build_sprites
    movem.l (%sp)+,%d0-%d1/%a0-%a1
1:  jmp     0xC35E8

| $1115D6 (after the VBlank, Z80 bus held): `jsr hook_end_vbl` + 2 nops
| over `jsr $113B00` (the text layer's upload) and `jsr $63FA`. The text layer
| is ending.c's end_tupload's (the arcade's colours); the scene's tiles go to
| VRAM $A000 (Astaroth's art, free after his removal) once.
hook_end_vbl:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     end_tupload
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    tst.b   end_upload
    beq.s   1f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    lea     prin_tiles,%a0
    move.w  #prin_end-prin_tiles,%d0
    move.w  #0xA000,%d1
    jsr     0x704BE
    clr.b   end_upload
    movem.l (%sp)+,%d0-%d1/%a0-%a1
1:  jmp     0x63FA

    .balign 2
prin_tiles:
    .include "build/princess.inc"
prin_end:

    .bss
    .even
end_rand:      .space 4             | $FFC62C-$FFC62F across the restart
end_rand_keep: .space 1
