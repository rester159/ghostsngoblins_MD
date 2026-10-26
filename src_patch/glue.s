| Engine hooks. The patcher writes a jsr/jmp to each entry at the addresses noted.

    .section .text.hooks,"ax"
    .global hook_ramclear, hook_title, hook_pad, warm_restart, warm_restart_sp
    .global game_sound_tick, game_sound_play, game_sound_init

| $28E: `jsr hook_ramclear` replaces `lea $FF0000,a0`; the original clear loop
| at $294-$29F is skipped. Clears work RAM except the persistent block
| $FF5000-$FF50FF, and reads the VDP control port first so a reset that
| interrupted a two-word command can't corrupt VDP init.
hook_ramclear:
    move.l  (%sp)+,%a1              | return address ($294); RAM below is wiped
    tst.w   0xC00004
    lea     0xFF0000,%a0
    moveq   #0,%d0
    move.w  #(0x5000/4)-1,%d1
1:  move.l  %d0,(%a0)+
    dbra    %d1,1b
    lea     0xFF5100,%a0
    move.w  #((0x10000-0x5100)/4)-1,%d1
2:  move.l  %d0,(%a0)+
    dbra    %d1,2b
    move.w  #0x87CD,0xFFC62C        | the arcade's random seed at power-on (arcrand.c)
    jmp     12(%a1)                 | -> $2A0, d0 = 0 as the original leaves it

| $B7A: the title routine's entry jumps here; this repeats its prologue.
hook_title:
    movem.l %d0-%a2,-(%sp)
    jsr     0xBF58                  | pad port init
    jsr     boot_flow               | d0: 0 or 1 = title, 2 = home start
    cmp.w   #1,%d0
    blt.s   3f
    beq.s   4f
    | Home start: what $B7A does after coin + start, without the title screen
    jsr     home_prestart           | credits = continues, debug stage
    clr.w   0xFF7FFC                | not attract
    moveq   #58,%d0
    jsr     0x89E4                  | start jingle
    jsr     fb_on                   | Firebrand's Quest skips the princess scene
    tst.l   %d0
    beq.s   5f
    move.w  #0x2700,%sr             | as the intro leaves it
    bra.s   6f
5:  jsr     intro_rest              | INTR: the graveyard, then the princess scene (bossart.c)
6:  clr.l   0xFF83F8
    clr.l   0xFF7FF0
    movem.l (%sp)+,%d0-%a2
    rts
3:  jmp     0xB88                   | title (the old port's splash at $B84/$CA6 is never shown)
4:  jmp     0xB88                   | title without splash (menu already shown)

| $BF72: `jmp hook_pad` replaces the pad routine. Keeps every register.
hook_pad:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr     pad_update
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

| ---- gameplay hooks (settings.c / hiscore.c). C clobbers d0-d1/a0-a1.

| $61A2: `clr.l $FFC570` in the player-block init (game start)
    .global hook_player_init
hook_player_init:
    clr.l   0xFFC570
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     player_init
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts

| $6348: `move.b #3,$FFC500` on continue
    .global hook_continue_lives
hook_continue_lives:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     continue_lives
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts

| $7890: `clr.l $FFC040` in the score-block init (game start)
    .global hook_score_init
hook_score_init:
    clr.l   0xFFC040
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     score_init
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts

| $779A: `move.l (a4),d1 ; cmp.l 4(a4),d1` after points are added (bonus life).
| The caller branches on the cmp flags, so it runs last.
    .global hook_score_added
hook_score_added:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    move.l  %a4,-(%sp)
    jsr     score_added
    addq.l  #4,%sp
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    move.l  (%a4),%d1
    cmp.l   4(%a4),%d1
    rts

| $62FA: `tst.w $FFC594` each frame of the continue countdown
    .global hook_continue_tick
hook_continue_tick:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     continue_tick
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    tst.w   0xFFC594
    rts

| $89E4: sound play entry (`jmp $11C73E`); demo-sound DIP. movem keeps the CCR.
    .global hook_sound_play
hook_sound_play:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     sound_allowed
    tst.l   %d0
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    beq.s   1f
    jmp     0x11C73E
1:  rts

| void stage_jump(int stage): the game's own stage advance
| (`move.b #n,$FFC512 ; clr.b $FFC521 ; jmp $113B70`); $113B70 resets SP/SR.
    .global stage_jump
stage_jump:
    move.l  4(%sp),%d0
    move.b  %d0,0xFFC512
    clr.b   0xFFC521
    jmp     0x113B70

| $639C: continue countdown expired -> high-score entry, then soft restart
    .global hook_game_over
hook_game_over:
    jsr     game_over
    bra     warm_restart_sp

| The game's soft restarts (`jmp $200`) come through here so the boot flow
| can tell them from a real reset.
warm_restart_sp:
    movea.l #0xFFFFFC,%sp
warm_restart:
    move.b  #1,persist_warm
    jmp     0x200

| C-callable wrappers for the game's sound jump table ($88D6 init, $8990 tick,
| $89E4 play d0). They clobber freely, so save everything.
game_sound_init:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr     0x88D6
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts
game_sound_tick:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    jsr     0x8990
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts
game_sound_play:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    move.l  64(%sp),%d0             | arg after 15 saved regs + return address
    jsr     0x89E4
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

| Silence: force the driver to re-initialise ($11C5EC skips init while
| $FF83F8 holds its magic; the title code clears it the same way).
    .global sound_stop
sound_stop:
    clr.l   0xFF83F8
    bra     game_sound_init

| Persistent block: survives the RAM clear above; validated by magic/checksum.
    .global persist, persist_warm
    .set persist,      0xFF5000
    .set persist_warm, 0xFF5006

| ---- attract overlay logo sources -------------------------------------
| Each replaces a `lea <src>,aN` (6 bytes) in the overlay routine with a jsr.
    .global ovl_tiles1, ovl_tiles2, ovl_tiles3, ovl_map
ovl_tiles1:                         | $11CE80: lea $320000,a0
    tst.b   0xFF5008                | persist.title_jp
    bne.s   1f
    lea     0x320000,%a0
    rts
1:  movea.l jp_ovl_chunk,%a0
    rts
ovl_map:                            | $11CE86: lea $320920,a1
    tst.b   0xFF5008
    bne.s   1f
    lea     0x320920,%a1
    rts
1:  movea.l jp_ovl_map_ptr,%a1
    rts
ovl_tiles2:                         | $11CF0C: lea $320260,a0
    tst.b   0xFF5008
    bne.s   1f
    lea     0x320260,%a0
    rts
1:  movea.l jp_ovl_chunk+4,%a0
    rts
ovl_tiles3:                         | $11CF2C: lea $3206E0,a0
    tst.b   0xFF5008
    bne.s   1f
    lea     0x3206E0,%a0
    rts
1:  movea.l jp_ovl_chunk+8,%a0
    rts

| $BB8: title loader palette source (`lea $2045E8,a0`); may draw the JP logo.
    .global hook_title_pal
hook_title_pal:
    movem.l %d0-%d1/%a1,-(%sp)
    jsr     title_logo_fix
    movea.l %d0,%a0
    movem.l (%sp)+,%d0-%d1/%a1
    rts

| ---- SRAM ----------------------------------------------------------------
| void sram_xfer(u8 *buf, int len, int write): copies sram_ram_code to work RAM
| ($FF5F00) and runs it there, since $200000-$3FFFFF may switch to SRAM.
    .global sram_xfer
sram_xfer:
    movem.l %d2/%a2,-(%sp)
    lea     sram_ram_code,%a0
    lea     0xFF5F00,%a1
    move.w  #(sram_ram_end-sram_ram_code)/2-1,%d0
1:  move.w  (%a0)+,(%a1)+
    dbra    %d0,1b
    movea.l 12(%sp),%a0             | buf
    move.l  16(%sp),%d0             | len
    move.l  20(%sp),%d1             | write
    jsr     0xFF5F00
    movem.l (%sp)+,%d2/%a2
    rts

| Position independent: absolute addresses only. a0 = buf, d0 = len, d1 = write.
sram_ram_code:
    move.w  %sr,-(%sp)
    move.w  #0x2700,%sr
    move.b  #1,0xA130F1             | map SRAM
    lea     0x200001,%a1            | odd bytes
    subq.w  #1,%d0
    tst.l   %d1
    bne.s   2f
1:  move.b  (%a1),(%a0)+
    addq.l  #2,%a1
    dbra    %d0,1b
    bra.s   3f
2:  move.b  (%a0)+,(%a1)
    addq.l  #2,%a1
    dbra    %d0,2b
3:  move.b  #0,0xA130F1             | back to ROM
    move.w  (%sp)+,%sr
    rts
sram_ram_end:

| ---- player 2 (p2.c) ------------------------------------------------------
| u32 gcall(u32 addr, u32 d0, u32 a3): call a game routine with the base
| registers its player code expects (a0 = map, a4 = $FF9000, a5 = $FF9100).
    .global gcall
gcall:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    movea.l 48(%sp),%a1
    move.l  52(%sp),%d0
    movea.l 56(%sp),%a3
    lea     0xFF0000,%a0
    lea     0xFF9000,%a4
    lea     0xFF9100,%a5
    jsr     (%a1)
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| void dma_vram(u32 src, u16 bytes, u16 vram): the game's checked DMA helper
    .global dma_vram
dma_vram:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    movea.l 20(%sp),%a0
    move.l  24(%sp),%d0
    move.l  28(%sp),%d1
    jsr     0x704BE
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts

| Sprite-table DMA (`jsr $704BE` with a0=$FFB500, d0=length, d1=$F000) in
| every stage loop: link player 2's sprite, then the original DMA.
|
| On a held frame (pace.c) nothing is uploaded: the sprites stay as they
| are on screen.
    .global hook_sat_dma
hook_sat_dma:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     pace_sat
    tst.w   %d0
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    beq.s   1f
    rts
1:  movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     sat_vblank              | bossart.c: the Satans' pose uploads
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    movem.l %d1/%a0-%a1,-(%sp)
    move.l  %d0,-(%sp)
    jsr     p2_sat
    addq.l  #4,%sp
    movem.l (%sp)+,%d1/%a0-%a1
    jmp     0x704BE

| $6938 (`jmp $114F58`, the first call of every stage-loop update):
| `jmp pace_hook`. Decides this frame's render skip (pace.c), then goes on.
    .global pace_hook
pace_hook:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     pace_start
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    jmp     0x114F58

| render_gate*: the sprite builds, skipped when pace_start says so (bit 0
| of fs_flags; bit 1 then tells the next pace_start the buffer is stale).
| Everything the builds write is render state (the sprite buffer and its
| counts at $FFB200, the enemy and shot art requests at $FF2600/$FF9730,
| $FFC37E), rebuilt from scratch by the next build.
| $92A0: `jmp render_gate1` over its first two instructions. Stage 1's
| build (reached by a jmp from $A3F2) doesn't start with the clear.
    .global render_gate1
render_gate1:
    bclr    #0,fs_flags+1
    bne.s   1f
    jsr     0x52F8
    move.w  #47,0xFFB204
    jmp     0x92AC
1:  bset    #1,fs_flags+1
    rts

| $4CBE: `jmp render_gate2` + nop. Stage 1's second sprite pass (the 30
| slots at $FFE000, appended after the build's count; it only also stores
| its piece counts at $FFC60C/E) is skipped with the build it follows.
    .global render_gate2
render_gate2:
    btst    #1,fs_flags+1
    bne.s   1f
    moveq   #0,%d0
    move.w  0xFFB20C,%d0
    jmp     0x4CC6
1:  rts

    .global render_gate
render_gate:
    bclr    #0,fs_flags+1
    bne.s   1f
    bra     clear_sat
1:  bset    #1,fs_flags+1
    addq.l  #4,%sp
    rts

| $61DC: `tst.w $FFC570` at the start of the game's death handling. In co-op
| p1_death() may take over (Z clear -> the following bne skips the routine).
    .global hook_p1_death
hook_p1_death:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     p1_death
    tst.l   %d0
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    beq.s   1f
    andi.b  #0xFB,%ccr              | Z = 0
    rts
1:  tst.w   0xFFC570
    rts

| $690E: `jsr $704BE` uploading Arthur's frame. Firebrand uploads his own
| frame at the sprite-table DMA instead (fb_sat).
    .global hook_arthur_dma
hook_arthur_dma:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     fb_on
    tst.l   %d0
    bne.s   1f
    move.l  8(%sp),-(%sp)               | a0: the frame
    jsr     pace_arthur                 | held frame: upload it later
    addq.l  #4,%sp
    tst.w   %d0
    bne.s   1f
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    jmp     0x704BE
1:  movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts

| $116472 and $116884 (12 bytes each): the item code copies its context's armor
| (+9) and weapon (+17) back to the game; a3 = context.
    .global hook_item_copy
hook_item_copy:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    move.l  %a3,-(%sp)
    jsr     fb_item
    addq.l  #4,%sp
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    move.b  9(%a3),0xFFC328
    move.b  17(%a3),0xFFA218
    rts

| void score_event(u16 idx): queue the game's score message $0C00|idx (points
| from the BCD table at $28F32) on the message queue at $FFB400.
    .global score_event
score_event:
    move.l  4(%sp),%d0
    movem.l %d1/%a1/%a4,-(%sp)
    lea     0xFFB400,%a4
    andi.w  #0xFF,%d0
    ori.w   #0x0C00,%d0
    jsr     0x7C1C
    movem.l (%sp)+,%d1/%a1/%a4
    rts

| $11711E: `jsr $704BE` uploading a shot slot's art (a0 = source, d0 = length,
| d1 = VRAM). Firebrand's shots get the fireball instead of the lance.
    .global hook_shot_dma
hook_shot_dma:
    movem.l %d0-%d1/%a1,-(%sp)
    move.l  %a0,-(%sp)
    jsr     fb_shot_src
    addq.l  #4,%sp
    movea.l %d0,%a0
    movem.l (%sp)+,%d0-%d1/%a1
    jmp     0x704BE

| $113DA2: `move.w #$2A9,$C00000`, the stage map writing its marker's tile into
| sprite 0 (mid-entry, so only the data word changes). Firebrand mode draws
| his head from tiles $69C-$69F (uploaded during play by firebrand.c).
    .global hook_map_marker
hook_map_marker:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     fb_on
    tst.l   %d0
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    beq.s   1f
    move.w  #0x69C,0xC00000
    rts
1:  move.w  #0x2A9,0xC00000
    rts

| $11CADC (jmp from the sound driver's request scan in $11CAB8, registers
| saved by its movem): the original tests the 512 request bits of the 64-byte
| bitmap at $FF8650 one at a time every update. This walks the bytes and skips
| zero ones: the same requests in the same ascending order, the same bit
| clears and the same calls of $11CB5C (d0 = id >> 8, d1 = id & $FF,
| d2 = $FF8410[id]; it keeps d3-d5/a0 only, so the counters are saved).
    .global sound_scan
sound_scan:
    lea     0xFF8650,%a1
    moveq   #0,%d6                  | byte index 0-63
5:  tst.l   (%a1,%d6.w)             | four clear bytes: skip them
    bne.s   1f
    addq.w  #4,%d6
    cmp.w   #64,%d6
    bcs.s   5b
    jmp     0x11CB28
1:  tst.b   (%a1,%d6.w)
    beq.s   4f
    moveq   #0,%d5                  | bit 0-7 (id & 7)
2:  btst    %d5,(%a1,%d6.w)
    beq.s   3f
    bclr    %d5,(%a1,%d6.w)
    lea     0xFF8610,%a0
    btst    %d5,(%a0,%d6.w)
    beq.s   3f
    move.w  %d6,%d3
    lsl.w   #3,%d3
    or.w    %d5,%d3                 | id
    lea     0xFF8410,%a0
    moveq   #0,%d2
    move.b  (%a0,%d3.w),%d2
    move.w  %d3,%d0
    lsr.w   #8,%d0
    moveq   #0,%d1
    move.b  %d3,%d1
    movem.l %d5-%d6/%a1,-(%sp)
    jsr     0x11CB5C
    movem.l (%sp)+,%d5-%d6/%a1
3:  addq.w  #1,%d5
    cmp.w   #8,%d5
    bcs.s   2b
4:  addq.w  #1,%d6
    cmp.w   #64,%d6
    bcc.s   6f
    move.w  %d6,%d0
    andi.w  #3,%d0
    bne.s   1b                      | still inside this long
    bra.s   5b
6:  jmp     0x11CB28

| The game's random source. The arcade's is its frame counter ($20-21, `inc`
| in the interrupt at $65CA, read as <$21: zombie waits $D336, rise/walk
| timers $D406/$D457, ...): it runs from power-on through the title, attract,
| deaths and the map and is never reset. The port's ($FFA206) stepped once a
| game update, stopped while Arthur was dead, and was set to $96 by the
| init block copied from $14F60 at every stage and life start ($91D4, $9952,
| $104EE6), so each life replayed the same zombie pattern. Now it follows the
| VBlank count ($FF7DFC) plus the frames spent in the boot menus.
    .global rng_tick, rng_init, item_init, menu_frames
rng_now:
    move.b  0xFF7DFF,%d0
    add.b   menu_frames,%d0
    sub.b   rng_lag,%d0             | hud.s: frames lost by long updates in play
    rts

| $927C and the seven other stage loops' copies (patch_gng.py): `jsr rng_tick`
| + 2 nops over `addq.b #1,6(a3)` and `lea $FFB800,a4`
rng_tick:
    move.l  %d0,-(%sp)
    jsr     rng_lag_step            | hud.s
    bsr.s   rng_now
    move.b  %d0,6(%a3)
    tst.b   bonus_pending           | bonus.c: a life earned outside play
    beq.s   1f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     bonus_tick
    movem.l (%sp)+,%d0-%d1/%a0-%a1
1:  bsr.s   rank_creep
    move.l  (%sp)+,%d0
    lea     0xFFB800,%a4
    rts

| The arcade's rank also creeps up with play time: every frame of play
| ($72A1 -> $E950 -> $EEB9, also during a knockback or the death animation,
| not in the death sequence, the map or the stage-start hold), when the frame
| counter's low byte <$21 is 0, the 16-bit rank <$9A-$9B gets $006B added,
| the high byte capped at $3F; each life or stage start sets it back to the
| base rank <$61 with a zero fraction ($6C65). That's +1 rank about every
| 612 frames, and ~28 enemy routines read it (the stage 1 boss's fireball
| delay $A315: table $A324 by rank / 8, the zombie waits, ...). The port has
| the base ($FFC501) and working ($FFA208) ranks the same way (the stage inits
| copy one to the other, $61C0) but no creep. d0 = the new counter; a3 =
| $FFA200. Runs while $FFC570 is 0 (not the death sequence or the continue
| countdown). Updates that miss a frame still count a wrap of the counter;
| after a gap (the map) only a counter of 0 does.
    .global rank_creep
rank_creep:
    tst.w   0xFFC570
    bne.s   9f
    movem.l %d1-%d2,-(%sp)
    move.l  0xFF7DFC,%d1
    move.l  %d1,%d2
    sub.l   rank_vbl,%d2
    move.l  %d1,rank_vbl
    subq.l  #8,%d2
    bcs.s   4f
    tst.b   %d0                     | after a gap: only a counter of 0
    beq.s   2f
    bra.s   1f
4:  move.b  %d0,%d2                 | wrapped since the last update: a borrow
    sub.b   rank_prev,%d2           | but a small step forward (a step back
    bcc.s   1f                      | isn't a wrap)
    bmi.s   1f
2:  moveq   #0,%d1
    move.b  8(%a3),%d1
    lsl.w   #8,%d1
    move.b  rank_frac,%d1
    addi.w  #0x6B,%d1
    move.b  %d1,rank_frac
    lsr.w   #8,%d1
    cmpi.b  #0x3F,%d1
    bls.s   3f
    moveq   #0x3F,%d1
3:  move.b  %d1,8(%a3)
1:  move.b  %d0,rank_prev
    movem.l (%sp)+,%d1-%d2
9:  rts

| $91D4, $9952, $104EE6: `jsr rng_init` over `lea $14F60,a0`: the same 12
| bytes with the counter carried on (the caller copies them to $FFA200)
rng_init:
    movem.l %d0/%a1,-(%sp)
    lea     0x14F60,%a0
    lea     rng_buf,%a1
    move.l  (%a0)+,(%a1)+
    move.l  (%a0)+,(%a1)+
    move.l  (%a0)+,(%a1)+
    bsr.w   rng_now
    move.b  %d0,rng_buf+6
    lea     rng_buf,%a0
    movem.l (%sp)+,%d0/%a1
    rts

| $25DA: `jsr item_init` over `lea $6EA6A,a0`. Every 6th enemy spawn makes an
| item; its type comes from a 7-step cycle, an accumulator and a 5-byte
| generator ($FFC890 +7..+13; arcade $7D, $7E, $78-$7C, logic $EBA4-$EC33).
| The arcade clears those only at power-on (only the 6-spawn countdown is
| reset at a stage or life start, $6E0F); the port reloaded them every time.
| The same 32 bytes, with +7..+13 carried on. They're saved by item_save
| ($25A8, `jsr item_save` over `lea $FFC700,a0`) before the routine clears
| $FFC700-$FFC90F.
    .global item_save
item_save:
    movem.l %d0/%a1,-(%sp)
    lea     0xFFC897,%a0
    lea     item_keep,%a1
    moveq   #6,%d0
1:  move.b  (%a0)+,(%a1)+
    dbf     %d0,1b
    movem.l (%sp)+,%d0/%a1
    lea     0xFFC700,%a0
    rts
item_init:
    movem.l %d0/%a1,-(%sp)
    lea     0x6EA6A,%a0
    lea     item_buf,%a1
    moveq   #7,%d0
1:  move.l  (%a0)+,(%a1)+
    dbf     %d0,1b
    lea     item_keep,%a0
    lea     item_buf+7,%a1
    moveq   #6,%d0
2:  move.b  (%a0)+,(%a1)+
    dbf     %d0,2b
    lea     item_buf,%a0
    movem.l (%sp)+,%d0/%a1
    rts
    .lcomm  rng_buf, 12
    .lcomm  item_buf, 32
    .lcomm  item_keep, 7
    .lcomm  menu_frames, 1

| $6328: `jsr cont_start` + `bne` over the continue countdown's Start test
| (`btst #0,$FF7000` / `bne`). Returns ne when there's no continue this frame.
| In Arcade mode, as the arcade ($786C/$7882): Start together with fire or
| jump; Start alone does nothing there. Home keeps Start alone.
    .global cont_start
cont_start:
    btst    #0,0xFF7000             | Start (active low)
    bne.s   1f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     is_arcade
    move.l  %d0,%d1
    move.b  0xFF7001,%d0
    not.b   %d0
    andi.b  #0x30,%d0               | fire or jump
    tst.l   %d1
    beq.s   2f                      | Home: Start is enough
    tst.b   %d0
    beq.s   3f
2:  movem.l (%sp)+,%d0-%d1/%a0-%a1
    ori     #4,%ccr                 | eq: continue
    rts
3:  movem.l (%sp)+,%d0-%d1/%a0-%a1
    andi    #0xFB,%ccr              | ne: not yet
1:  rts

| $113A1C: `jmp loop_again` after the second loop's ending. The arcade then
| starts over from stage 1 on a fresh first loop, score and lives kept
| ($73F3 clears the loop flags, $7446 sets stage 0 and restarts play); the
| port went back to the title (`jmp $200`). This takes the port's own
| first-loop path ($1139C2: keep the player state, stage 0, no checkpoint,
| restart through $2CC) with the loop flag cleared instead of set.
    .global loop_again
loop_again:
    addq.w  #1,0xFF7FD0             | as the port's path
    jsr     0x113A9C                | keep score and lives across the restart
    clr.b   0xFF7FC0                | a first loop again
    move.b  #1,0xFF7FC1
    clr.b   0xFF7FC2
    clr.b   0xFFC512
    clr.b   0xFFC894
    clr.b   0xFFC521
    clr.b   0xFFC5FE
    clr.w   0xFFCD78
    clr.w   0xFFCD7A
    movea.l #0xFFFFFC,%sp
    jmp     0x3F0032

| $7CF8: `jsr zombie_y` + nop over `move.w d7,(a5)` / `move.w #$0F00,2(a5)` in
| the zombie sprite builder ($7C5A, type-11 objects). The port draws each
| enemy frame as one 32x32 image at y = 352 + camera - object y, laid out as
| the arcade's 2x2 shape (object +$0F = 3: pieces from (-16,-16), `$F864`);
| the arcade draws the frames of a zombie coming out of the ground or
| sinking back with shape 0 (one 16x16 piece at (-8,-8)) or 2 (two pieces at
| (-16,-8)), 8 px higher. Those frames (0-4, 8-17, 21-25: both rise sets and
| the sinking sets) are moved up 8; measured row for row against the arcade,
| the others (shape 3) already matched. d3 = frame * 2 here.
    .global zombie_y
zombie_y:
    cmpi.w  #2*25,%d3
    bhi.s   1f
    cmpi.w  #2*4,%d3
    bls.s   2f
    cmpi.w  #2*8,%d3
    bcs.s   1f
    cmpi.w  #2*21,%d3
    bcc.s   2f
    cmpi.w  #2*17,%d3
    bhi.s   1f
2:  subq.w  #8,%d7
1:  move.w  %d7,(%a5)
    move.w  #0x0F00,2(%a5)
    rts

| $5A8 and the nine other stage-loop entries (patch_gng.py): `jsr
| stage_hold_entry` + 4 nops over `move.w #$2300,sr` and `move.l
| #'LIVE',$FF7FF0`: the arcade's stage-draw wait (pad.c stage_hold), then the
| same two instructions. Also sets the stage's starting time ($103D10: the
| stage's entry in the normal or checkpoint table, $103E28/$103E36, as the
| arcade's $6EAD/$6EBB): the stage inits copy a default HUD block with the
| timer at $74 and only stage 1's then called $103D10, so stages 3, 4 and 6
| (index 2, 3, 5) started at 1:56 instead of 2:30, 2:30 and 3:00.
    .global stage_hold_entry
stage_hold_entry:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     0x103D10                | the stage's time from its table (see below)
    jsr     stage_hold
    st      0xFF9451                | the first ground step checks the floor
                                    | at his own y only (arthur.s ground_snap)
    clr.b   rank_frac               | the rank creep restarts from the base
                                    | rank ($6C65; rank_creep below)
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    move.l  #0x4C495645,0xFF7FF0
    move.w  #0x2300,%sr
    rts

| $106B24: `jsr mover_load` + `rts` + 2 nops over the moving-platform mover's
| load of its next (step, direction, count) entry. The arcade's mover ($E482)
| returns after loading, so a platform stands still for a frame at every
| segment change; the port loaded and moved in the same frame and drifted
| out of phase (~25 frames in 1200).
    .global mover_load, mover_load2
mover_load:
    move.w  (%a0)+,28(%a4)
    move.b  (%a0)+,24(%a4)
    move.b  (%a0),26(%a4)
    rts
| The other three movers ($10F560, $11A390, $11A5AE: the stage 3-5 platform
| types) load from per-type sequences and wrap the index; `jsr mover_load2`
| + `rts` over their `bcs.s` / `moveq #0,d1` / `move.w d1,28(a4)` (flags from
| their `cmp.w` survive the jsr).
mover_load2:
    bcs.s   1f
    moveq   #0,%d1
1:  move.w  %d1,28(%a4)
    rts

| $110578 and $1105C6 (the port's Satan handler, states 0 and 1): `jsr
| hook_satan` + `bra.w $110846` (the handler's exit, which restores d4-a2).
| The arcade's Satan (satan.c) instead of the port's; a4 = the slot.
    .global hook_satan, arc_rand_asm
hook_satan:
    move.l  %a4,-(%sp)
    jsr     satan_update
    addq.l  #4,%sp
    tst.l   %d0
    beq.s   1f
    jsr     0x10E9B6                | the port's boss count (+1)
1:  rts

| $11080E (the Satan's death, state 2): `jsr hook_satan_die` over `tst.b 8(a4)`
| + `bne.s $110834`. The arcade first plays the generic enemy burst ($E8A7:
| 1 + 3 + 18 frames, after $C368's frame) and only then the 63-frame score
| phase ($C375) that the port's death is; the port went straight to it, so the
| slot (and the key, which comes with its removal) went 22 frames early. The
| burst frames count in +9 (cleared by the weapon code at the kill), and
| the slot shows the arcade's burst for them (bossart.c `sat_burst`, by the count). The death
| sound moves to the first of them (its own call at $11082C is removed).
    .global hook_satan_die
hook_satan_die:
    tst.b   8(%a4)
    bne.s   2f                      | the port's countdown is running
    addq.b  #1,9(%a4)
    cmpi.b  #23,9(%a4)
    bcc.s   1f                      | burst done: the port's death from $110814
    cmpi.b  #1,9(%a4)
    bne.s   3f
    jsr     0xB7F2                  | the death sound (arcade $C368 -> $79A1)
3:  movem.l %d0/%a0,-(%sp)
    moveq   #0,%d0
    move.b  9(%a4),%d0
    lea     sat_burst,%a0
    move.b  (%a0,%d0.w),%d0
    beq.s   4f                      | the pose stays
    move.w  %d0,30(%a4)             | the burst's frame
4:  movem.l (%sp)+,%d0/%a0
    addq.l  #4,%sp
    jmp     0x110846                | the handler's exit
1:  rts
2:  addq.l  #4,%sp
    jmp     0x110834

| The arcade's $68F9 (arcrand.c) for assembly callers: d0 = the next random
| byte (0-255), every other register kept.
arc_rand_asm:
    movem.l %d1/%a0-%a1,-(%sp)
    jsr     arc_rand
    andi.l  #0xFF,%d0
    movem.l (%sp)+,%d1/%a0-%a1
    rts

| $10442A: `jmp tomb_check` over its first instruction. The tombstone check,
| rewritten from the arcade's ($9FAE in gg3, Capcom `gng` set, called from the
| walk at $940E/$9435 and the fall at $9638), for the type-1 slots of the 30
| at $FFE000 (x word, y word, +4 live, +10 type). The arcade box comes from
| its table at $A052 for type 1: x -12..+12 of the tombstone, y -19..+19,
| landing top y + 19. The port had its own: landing within 20 px of x on a
| top at +20, and a side stop at 13 px that also applied in mid-air, so no
| jump could clear one (the arcade never blocks a jump; it only lands it).
|   on the ground ($FF9408 = 1) and moving: probe the old x +/- 1 (low byte,
|     same high byte) and y + 1; if it's inside a box the move is cancelled
|     (x back to $FF9220, fraction and all), as the arcade skips its x step.
|   rising ($FF9410 = 1): no test.
|   falling: probe (x, y - 1); inside a box and not below its y, land: on top
|     (y + 19), or where he is if he's within -3..+2 of its y. The y fraction
|     is kept, as in the arcade; the landing state is the port's ($3D90 etc.).
| The x and y tests use bytes like the arcade (after a word test that x is
| within 128). In every stage, as the arcade's (no stage test there): the
| port's original only checked stage 1, and in stage 3 only one variant, so
| the stage 3 rocks kept the port's old box.
    .set TOMB_X, 12                     | $A052 type 1: x reach (E4; E5 = 2 * 12)
    .set TOMB_Y, 19                     | y reach and landing height (E6; E7 = 2 * 19)
    .global tomb_check
tomb_check:
    movem.l %d0-%d7/%a2,-(%sp)
    move.l  0xFF9000,%d5
    lsr.l   #8,%d5                  | x
    move.w  0xFF9004,%d7            | y
    lea     0xFFE000,%a2
    moveq   #29,%d4
    cmpi.w  #1,0xFF9408
    beq.w   tomb_walk
    cmpi.w  #1,0xFF9410
    beq.w   9f                      | rising
    move.b  %d7,%d6
    subq.b  #1,%d6                  | probe y - 1
2:  tst.b   4(%a2)
    beq.w   8f
    cmpi.b  #1,10(%a2)
    bne.w   8f
    move.w  %d5,%d0                 | within 128 (word)
    sub.w   (%a2),%d0
    addi.w  #0x80,%d0
    cmpi.w  #0x100,%d0
    bhi.s   8f
    move.b  %d5,%d0
    sub.b   1(%a2),%d0
    addi.b  #TOMB_X,%d0
    cmpi.b  #2*TOMB_X,%d0
    bhi.s   8f
    move.b  %d6,%d0
    sub.b   3(%a2),%d0
    addi.b  #TOMB_Y,%d0
    cmpi.b  #2*TOMB_Y,%d0
    bhi.s   8f
    move.w  %d7,%d0                 | not below its y
    sub.w   2(%a2),%d0
    bmi.s   8f
    move.b  %d7,%d0                 | near its base: land where he is
    sub.b   3(%a2),%d0
    addq.b  #3,%d0
    cmpi.b  #6,%d0
    bcs.s   3f
    move.w  2(%a2),%d7
    addi.w  #TOMB_Y,%d7             | on top
3:  move.w  %d7,0xFF9004
    moveq   #0,%d1
    move.w  %d7,%d1
    lsl.l   #8,%d1
    move.l  0xFF9400,%d0
    andi.l  #0xFF,%d0
    or.l    %d0,%d1
    move.l  %d1,0xFF9400
    move.l  #0x44000,0xFF9404       | 4.25, as every landing (the fall speed
    move.w  #1,0xFF9408             | if he walks off: the arcade's $51B)
    clr.w   0xFF9410
    bra.s   9f
8:  lea     48(%a2),%a2
    dbf     %d4,2b
    bra.s   9f

tomb_walk:
    move.l  0xFF9220,%d3
    lsr.l   #8,%d3                  | old x
    move.w  %d3,%d2
    cmp.w   %d3,%d5
    beq.s   9f                      | not moving
    bgt.s   4f
    subq.b  #2,%d2                  | moving left: old x - 1
4:  addq.b  #1,%d2                  | moving right: old x + 1
    move.b  %d7,%d6
    addq.b  #1,%d6                  | probe y + 1
5:  tst.b   4(%a2)
    beq.s   7f
    cmpi.b  #1,10(%a2)
    bne.s   7f
    move.w  %d2,%d0
    sub.w   (%a2),%d0
    addi.w  #0x80,%d0
    cmpi.w  #0x100,%d0
    bhi.s   7f
    move.b  %d2,%d0
    sub.b   1(%a2),%d0
    addi.b  #TOMB_X,%d0
    cmpi.b  #2*TOMB_X,%d0
    bhi.s   7f
    move.b  %d6,%d0
    sub.b   3(%a2),%d0
    addi.b  #TOMB_Y,%d0
    cmpi.b  #2*TOMB_Y,%d0
    bhi.s   7f
    move.l  0xFF9220,0xFF9000       | blocked: the move doesn't happen
    bra.s   9f
7:  lea     48(%a2),%a2
    dbf     %d4,5b
9:  movem.l (%sp)+,%d0-%d7/%a2
    rts

| $6A88: `jmp obj_dispatch`. The object pass ($69A2) then picked its handler
| from the index in d4 (0-14, set by moveq/move.b just before, so its high
| word is clear) with up to 11 compares; the same targets by table, each
| entered with d4 unchanged. 0 -> $6ADC (jsr $79D6), unmatched -> $6AE2.
    .global obj_dispatch
obj_dispatch:
    cmpi.w  #14,%d4
    bhi.s   1f
    add.w   %d4,%d4
    add.w   %d4,%d4
    jmp     2f(%pc,%d4.w)
1:  jmp     0x6AE2
2:  .irp k, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14
    bra.w   od\k
    .endr
    .macro  odis k, at
od\k: moveq #\k,%d4
    jmp     \at
    .endm
    odis 0, 0x6ADC
    odis 1, 0x6AE2
    odis 2, 0x6AE2
    odis 3, 0x6CB8
    odis 4, 0x6D7C
    odis 5, 0x6E02
    odis 6, 0x6E7C
    odis 7, 0x6EE4
    odis 8, 0x6EEE
    odis 9, 0x6D22
    odis 10, 0x6AE2
    odis 11, 0x6AE2
    odis 12, 0x6F4E
    odis 13, 0x6FA4
    odis 14, 0x6F44

| $76A4: `jmp slot_dispatch`. Stage 1's 40-slot pass ($768A) picked the
| handler of each live slot from its type at 10(a4) with up to 9 byte
| compares; the same targets by table. d2 is the scratch and is 1 again at
| every target, as before; types without a handler -> the assert at $773A.
    .global slot_dispatch
slot_dispatch:
    moveq   #0,%d2
    move.b  10(%a4),%d2
    cmpi.w  #17,%d2
    bhi.s   1f
    add.w   %d2,%d2
    add.w   %d2,%d2
    jmp     2f(%pc,%d2.w)
1:  jmp     0x773A
2:  .irp k, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17
    bra.w   sd\k
    .endr
    .macro  sdis k, at
sd\k: moveq #1,%d2
    jmp     \at
    .endm
    sdis 0, 0x76F6
    sdis 1, 0x7708
    sdis 3, 0x76FC
    sdis 5, 0x7702
    sdis 7, 0x775C
    sdis 8, 0x7748
    sdis 11, 0x770E
    sdis 16, 0x76F0
    sdis 17, 0x76F0
sd2:
sd4:
sd6:
sd9:
sd10:
sd12:
sd13:
sd14:
sd15:
    jmp     0x773A

| `jsr clear_sat` + 4 nops over each `lea $FFB500,a1; moveq #127,d0;
| 1: clr.l (a1)+; dbf d0,1b` (the sprite buffer clear before every sprite
| build: 128 longs at 30 cycles). Same end state: $FFB500-$FFB6FF zero, a1 =
| $FFB700, d0 = $FFFF, Z set with N/V/C clear and X kept as clr.l leaves them.
    .global clear_sat
clear_sat:
    movem.l %d1-%d7/%a0,-(%sp)
    moveq   #0,%d1
    moveq   #0,%d2
    moveq   #0,%d3
    moveq   #0,%d4
    moveq   #0,%d5
    moveq   #0,%d6
    moveq   #0,%d7
    movea.l %d1,%a0
    lea     0xFFB700,%a1
    .rept   16
    movem.l %d1-%d7/%a0,-(%a1)
    .endr
    lea     0x200(%a1),%a1
    movem.l (%sp)+,%d1-%d7/%a0
    move.l  #0xFFFF,%d0
    andi.b  #0x10,%ccr
    ori.b   #0x04,%ccr
    rts

| void p2_control(void): Maximo's control block, the main loop's player block
| ($7BA-$8AC) replayed on his swapped-in state. Same calls, arguments and order
| as the C version it replaces, but one register save for the whole sequence
| instead of one per call (gcall). (sp) holds the direction (d0 of the chain,
| $FF9204 at the start), 2(sp) whether this is stage 1 (both read once).
    .macro PCALL addr
    lea     0xFF0000,%a0
    lea     0xFF9000,%a4
    lea     0xFF9100,%a5
    jsr     \addr
    .endm
    .macro PCALL0 addr
    moveq   #0,%d0
    suba.l  %a3,%a3
    PCALL   \addr
    .endm
    .macro PCALLD addr
    moveq   #0,%d0
    move.w  (%sp),%d0
    suba.l  %a3,%a3
    PCALL   \addr
    .endm
    .global p2_control
p2_control:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    subq.l  #4,%sp
    clr.w   2(%sp)
    cmpi.b  #2,0xFFC512
    bcc     0f
    move.w  #1,2(%sp)               | stage 1
0:  tst.b   0xFFC305                | not in a controllable state
    beq     9f
    tst.w   0xFFCF34
    bne     1f
    PCALL0  0x51DA
1:  tst.w   0xFFC37C
    bne     7f
    move.w  0xFF9204,(%sp)          | d0 of the chain (2 = right, 1 = left)
    PCALLD  0x7FC4
    PCALLD  0x80BA
    PCALLD  0x80DE
    PCALLD  0xBC12
    PCALLD  0x8114
    move.w  %d0,(%sp)               | the walk gate's answer, as the main loop
                                    | uses it (no walk while crouching, on a
                                    | ladder or on the stand-up frame)
    cmpi.w  #2,(%sp)
    bne     2f
    move.b  #1,0xFF9006
    move.l  #288,%d0
    lea     0x1486E,%a3
    PCALL   0x11469C
    clr.w   0xFF920A
    bra     3f
2:  cmpi.w  #1,(%sp)
    bne     5f
    move.b  #2,0xFF9006
    move.l  #-288,%d0
    lea     0x1496E,%a3
    PCALL   0x1146CE
    move.w  #0x800,0xFF920A
3:  tst.w   2(%sp)
    beq     4f
    PCALL0  0xA35C
4:  tst.w   0xFF9208                | walk animation timer
    beq     41f
    subq.w  #1,0xFF9208
    bra     5f
41: addq.w  #1,0xFF9206
    cmpi.w  #7,0xFF9206
    bcs     42f
    move.w  #1,0xFF9206
42: move.w  #2,0xFF9208
5:  clr.w   0xFFB11E
    PCALL0  0x8138
    tst.w   2(%sp)
    beq     6f
    PCALL0  0x10442A
6:  PCALL0  0x8144
    bra     8f
7:  tst.w   0xFFCF34
    bne     8f
    PCALL0  0x522E
8:  PCALL0  0x525E
9:  addq.l  #4,%sp
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| $5930: `jsr shot_check` over `btst #0,16(a4)` (the following `bne.w $59B6`
| stays): on the odd frames (bit set, the branch to Arthur's shot check) the
| weapons are tested against the enemy shots first (shots.c, arcade $F3CE
| before $F530). Returns with the flags of the btst.
    .global shot_check
shot_check:
    btst    #0,16(%a4)
    beq.s   1f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     weapon_vs_shots
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    btst    #0,16(%a4)
1:  rts

| $10F816: `jmp size_shift` over `moveq #0,d0` / `move.b 25(a4),d0`. The
| stage 4 type-14 enemy's size-class change (+$19 -> d1 from the frame table
| $248AB0) moves its y by the change in the arcade's shape anchor ($F864: y
| -16 for class 1, -24 for 8, -32 for 10). The port only allowed 1<->8 and
| 8<->10 and stopped the game with fault code $8C on anything else; its
| phase restart ($10F7C4) can go from a class-10 frame straight to frame 3
| (class 1), so in play the game could halt in stage 4. Now any change
| between the three classes moves it by the anchor difference (10 -> 1:
| -16), as the arcade's drawing would; an unknown class still traps.
    .global size_shift
size_shift:
    moveq   #0,%d0
    move.b  25(%a4),%d0
    cmp.w   %d1,%d0
    beq.s   9f
    move.w  %d1,%d2
    bsr.s   1f                      | new class's offset
    move.w  %d2,-(%sp)
    move.w  %d0,%d2
    bsr.s   1f                      | old class's offset
    neg.w   %d2
    add.w   (%sp)+,%d2
    jmp     0x10F85C                | y += d2, class = d1
1:  cmpi.w  #1,%d2
    bne.s   2f
    moveq   #0,%d2
    rts
2:  cmpi.w  #8,%d2
    bne.s   3f
    moveq   #8,%d2
    rts
3:  cmpi.w  #10,%d2
    bne.s   4f
    moveq   #16,%d2
    rts
4:  addq.l  #4,%sp
    jmp     0x10F880                | the port's fault trap, as before
9:  rts
