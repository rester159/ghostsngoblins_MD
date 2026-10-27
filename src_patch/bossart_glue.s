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
    cmpi.b  #0xD8,8(%a1)            | a Petite Devil's fireball in stage 5: $F7
    bne.s   0f
    cmpi.b  #4,0xFFC512
    bne.s   0f
    lea     fire_frame,%a2
    jmp     0x117238
0:  move.l  %a1,%d7
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
| `jsr intro_hook` + nop. The opening (bossart.c intro_scene: the arcade's
| graveyard, then the port's intro picture on the arcade's frames) in place of
| $E0C, which it leaves as $E0C does (interrupts off).
| intro_rest: the same after the music (the Home start, glue.s hook_title).
    .global intro_hook, intro_rest, intro_wait, intro_tick
intro_hook:
    jsr     0x89E4                  | the intro music (d0 = 58)
intro_rest:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr     intro_scene
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    move.w  #0x2700,%sr             | as $E0C leaves it
    rts

| The game start's VRAM after the opening (opening.c): $2E2 `jsr
| stage_clear_hook` + `bra.w $304` over the display off and the VRAM clear;
| $3C6 `jsr intro_cram_hook` + 2 nops over the VSRAM address after the CRAM
| load; $940A `jsr bg_off_hook` + nop over the bg init's display off.
    .global stage_clear_hook, intro_cram_hook, bg_off_hook
stage_clear_hook:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr     stage_clear
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    moveq   #0,%d0                  | (as the clear leaves it)
    rts
intro_cram_hook:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     intro_cram
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts
| $B12 (the VRAM copy, d1 + 1 words from a0): `jmp b12_tick` over its first
| 3 instructions. While load_ticks is set (opening.c: the game start after
| the opening, display on) it copies 64 words at a time and runs the sound
| driver's tick ($8990) at each VBlank start it sees, as the frames go by.
    .global b12_tick
b12_tick:
    tst.b   load_ticks
    bne.s   1f
    move.l  %d2,-(%sp)
    addq.w  #1,%d1
    move.w  %d1,%d2
    jmp     0xB18
1:  movem.l %d0/%d2,-(%sp)
    move.w  %d1,%d2                 | words - 1
2:  moveq   #63,%d0
    cmp.w   %d0,%d2
    bcc.s   3f
    move.w  %d2,%d0
3:  sub.w   %d0,%d2
4:  move.w  (%a0)+,0xC00000
    dbf     %d0,4b
    bsr.s   load_tick
    subq.w  #1,%d2
    bcc.s   2b
    movem.l (%sp)+,%d0/%d2
    move.w  #-1,%d1
    rts
| $B470 (a stage start's music: `jsr $8812` with a6 = $FF9500, the driver's
| init then sounds $30, $2B, unless $FFC57F): `jmp music_hook`. After the
| opening opening.c has started it at the load's start (music_early).
    .global music_hook, music_now
music_hook:
    tst.b   0xFFC57F
    bne.s   1f
    tst.b   music_early
    bne.s   2f
    jsr     0x8812
2:  sf      music_early
    move.b  #1,68(%a6)
1:  rts
music_now:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    lea     0xFF9500,%a6
    jsr     0x8812
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

| a tick if a VBlank started since the last look
    .global load_tick
load_tick:
    move.w  %d0,-(%sp)
    move.w  0xC00004,%d0
    andi.b  #8,%d0
    cmp.b   load_vb,%d0
    beq.s   1f
    move.b  %d0,load_vb
    beq.s   1f
    jsr     game_sound_tick
1:  move.w  (%sp)+,%d0
    rts

| $588 `jsr hud_flush_hook` + nop over `jsr $63B4` and `jsr $63FA` (the
| stage start's HUD upload): opening.c hide_buf around the upload.
    .global hud_flush_hook
hud_flush_hook:
    jsr     0x63B4
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    clr.l   -(%sp)
    jsr     hide_buf
    addq.l  #4,%sp
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    jsr     0x63FA
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    pea     1
    jsr     hide_buf
    addq.l  #4,%sp
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts
bg_off_hook:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     bg_off
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts

| the VBlank's start, as $EDE waits for it
intro_wait:
    move.l  %d0,-(%sp)
1:  move.w  0xC00004,%d0
    btst    #3,%d0
    bne.s   1b
2:  move.w  0xC00004,%d0
    btst    #3,%d0
    beq.s   2b
    move.l  (%sp)+,%d0
    rts

| then the rest of a frame of $E0C's: the sound ($8990, as $EDE) and the pads
| ($BF72 -> $FF7000)
intro_tick:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr     0x8990
    jsr     0xBF72
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

| $11C15E (the type-2 draw, stages 3-6): `jmp pd_draw_hook` + nop over
| `cmpi.b #1,$FFC512`. A dying devil in stage 5: the burst (pd_burst).
    .global pd_draw_hook
pd_draw_hook:
    cmpi.b  #4,0xFFC512
    bne.s   1f
    cmpi.b  #2,7(%a4)
    bne.s   1f
    tst.b   4(%a4)
    beq.s   1f
    tst.b   5(%a4)
    beq.s   1f
    movem.l %d7/%a1,-(%sp)
    lea     pd_burst,%a1
    bsr.s   art_call_r
    tst.w   %d7
    movem.l (%sp)+,%d7/%a1          | (flags kept)
    bne.s   8f
1:  cmpi.b  #1,0xFFC512
    bne.s   2f
    jmp     0x11C168
2:  jmp     0x11C176
8:  rts

| a draw in C with the Spr record (as sat_draw_hook): the function in a1 with
| (a4, a3, &spr); d7 = its result: nonzero, it drew (d0/d1 out); 0, nothing
| changed (d0/d1 as they were) and the original goes on.
art_call_r:
    movem.l %d0-%d1,-(%sp)
    movem.l %a0-%a1,-(%sp)
    lea     -12(%sp),%sp
    move.l  %a5,(%sp)
    move.w  %d0,4(%sp)
    move.w  %d1,6(%sp)
    clr.l   8(%sp)
    pea     (%sp)
    move.l  %a3,-(%sp)
    move.l  %a4,-(%sp)
    jsr     (%a1)
    lea     12(%sp),%sp
    move.w  %d0,%d7
    beq.s   1f
    movea.l (%sp),%a5
    moveq   #0,%d0
    moveq   #0,%d1
    move.w  8(%sp),%d0
    move.w  10(%sp),%d1
    lea     12(%sp),%sp
    movem.l (%sp)+,%a0-%a1
    addq.l  #8,%sp                  | (the saved d0/d1)
    rts
1:  lea     12(%sp),%sp
    movem.l (%sp)+,%a0-%a1
    movem.l (%sp)+,%d0-%d1          | not drawn: d0/d1 as they were
    rts

| $11C26E (the devil frame upload): `jsr pd_src_hook` + 3 nops over `mulu.w
| #128,d0` / `lea $10D526,a0` / `adda.l d0,a0`: a0 = the frame's art.
    .global pd_src_hook, pd_entry_hook
pd_src_hook:
    cmpi.w  #41,%d0
    bcc.s   1f
    mulu.w  #128,%d0                | the port's frames, as before
    lea     0x10D526,%a0
    adda.l  %d0,%a0
    rts
1:  movem.l %d1/%a1,-(%sp)
    move.l  %d0,-(%sp)
    jsr     pd_src
    addq.l  #4,%sp
    movea.l %d0,%a0
    movem.l (%sp)+,%d1/%a1
    rts

| $11C0A8 (its draw): `jsr pd_entry_hook` + nops over the frame lookup
| ($10D392 -> $10D3E4): a2 = the frame's entry, d2 = the frame on entry.
pd_entry_hook:
    cmpi.w  #41,%d2
    bcc.s   1f
    add.w   %d2,%d2                 | the port's frames, as before
    lea     0x10D392,%a2
    move.w  (%a2,%d2.w),%d2
    lea     0x10D3E4,%a2
    adda.w  %d2,%a2
    rts
1:  movem.l %d0-%d1/%a0-%a1,-(%sp)
    move.l  %d2,-(%sp)
    jsr     pd_entry
    addq.l  #4,%sp
    movea.l %d0,%a2
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts
