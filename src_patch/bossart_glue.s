| Hooks for bossart.c (the Satan's poses, burst and star).

| $11086A (the Satan's draw): `jmp sat_draw_hook`. In: a4 the slot, a3 the
| camera, a5 the sprite buffer, d0 the next link, d1 the sprites left. Out:
| d0 sprites written, d1 sprites dropped, a5 past them (as the original).
    .global sat_draw_hook
sat_draw_hook:
    tst.b   4(%a4)
    beq.s   9f
    tst.b   5(%a4)
    beq.s   9f
    movem.l %a0-%a1,-(%sp)
    lea     -12(%sp),%sp            | Spr: sat, link, left, drawn, dropped
    move.l  %a5,(%sp)
    move.w  %d0,4(%sp)
    move.w  %d1,6(%sp)
    clr.l   8(%sp)
    pea     (%sp)
    move.l  %a3,-(%sp)
    move.l  %a4,-(%sp)
    jsr     sat_draw
    lea     12(%sp),%sp
    movea.l (%sp),%a5
    moveq   #0,%d0
    moveq   #0,%d1
    move.w  8(%sp),%d0
    move.w  10(%sp),%d1
    lea     12(%sp),%sp
    movem.l (%sp)+,%a0-%a1
    rts
9:  moveq   #0,%d0
    moveq   #0,%d1
    rts

| $11051A (the end of $1104FC, the Satan's art load): `jmp sat_load_tail`
| over `movem.l (sp)+,d0-d1/a0` + `rts`.
    .global sat_load_tail
sat_load_tail:
    move.l  %a1,-(%sp)
    jsr     sat_art_init
    movea.l (%sp)+,%a1
    movem.l (%sp)+,%d0-%d1/%a0
    rts

| $11721C (the shot draw, type 6): `jmp star_sel` + nop over `cmpi.w #8,d2`
| + `bcc.w $1172B6`. A shot a Satan fired (star_tag) is drawn as the star:
| frame $1D7 for 4 updates from the shot, then $1DF for 4, and so on.
| d2, d7 and a2 are free here (set again at $117238).
    .global star_sel
star_sel:
    move.l  %a1,%d7
    subi.l  #0xFFC100,%d7
    bcs.s   8f
    divu    #48,%d7
    cmpi.w  #6,%d7
    bcc.s   8f
    lea     star_tag,%a2
    tst.b   (%a2,%d7.w)
    beq.s   8f
    lea     star_t0,%a2
    move.b  0xFFA206,%d2
    sub.b   (%a2,%d7.w),%d2
    lsr.b   #2,%d2
    andi.w  #1,%d2
    lsl.w   #3,%d2
    lea     star_frames,%a2
    adda.w  %d2,%a2
    jmp     0x117238
8:  cmpi.w  #8,%d2
    bcc.s   1f
    jmp     0x117224
1:  jmp     0x1172B6

| $C48 (`jsr $89E4` + `jsr $E0C`, the intro's music and the intro):
| `jsr intro_hook` + nop. The arcade's graveyard first (intro_scene), then the
| port's intro unless Start skipped it.
    .global intro_hook, intro_frame, intro_loop
intro_hook:
    jsr     0x89E4                  | the intro music (d0 = 58)
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr     intro_scene
    tst.l   %d0
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    bne.s   1f
    jmp     0xE0C
1:  move.w  #0x2700,%sr             | as $E0C leaves it
    rts

| one frame: $EDE (VBlank wait, sound) and $BF72 (pads -> $FF7000)
intro_frame:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr     0xEDE
    jsr     0xBF72
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

| $E92 (`bsr.w $EDE` + `lea $210088,a2`): `jmp intro_loop` + 2 nops. $E0C's
| step loop with a wait per step (intro_waits, bossart.c) instead of 2 frames
| each; Start skips from the 21st frame as before. $E0C saved d0-a2.
intro_loop:
    jsr     0xEDE
    lea     0x210088,%a2
    moveq   #0,%d3                  | step
    moveq   #0,%d4                  | frames
1:  lea     intro_waits,%a0
    move.b  (%a0,%d3.w),%d5
2:  jsr     0xEDE
    jsr     0xBF72
    addq.w  #1,%d4
    cmpi.w  #20,%d4
    bls.s   3f
    btst    #0,0xFF7000
    beq.s   9f
3:  subq.b  #1,%d5
    bhi.s   2b
    cmpi.w  #155,%d3
    beq.s   9f
    jsr     0xEFC
    addq.w  #1,%d3
    bra.s   1b
9:  jmp     0xED4
