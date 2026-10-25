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
5:  jsr     0xE0C                   | INTR: the princess scene
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
1:  movem.l %d1/%a0-%a1,-(%sp)
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

| $10442A: `jmp tomb_check` over its first instruction. The tombstone check
| (lands the player on and stops him against each live type-1 slot of the 30
| at $FFE000) runs three times an update in co-op stage 1 over 12 tombstones.
| Same tests, writes and exits as the original; with $FFC512 clear (the usual
| case) its loop-invariant tests come out of the loop: whether $FF9410 is 1
| (bit 31 of d4; the loop only ever clears it) and the X/Y offsets d5+20,
| d7+12 (d2, a0). A tombstone whose x is outside [min(d3,d5)-20,
| max(d3,d5)+20] can't pass the landing (|d5-x| <= 20) or the stop tests
| (within 13 of d5 and d3), so one compare skips it (a3 = the low end, a1 =
| the width). Otherwise the original runs. d2/a0-a1/a3 are kept for the caller.
    .global tomb_check
tomb_check:
    tst.b   0xFFC512
    beq.s   1f
    jmp     0x104432                | the original, from its next instruction
1:  movem.l %d2/%d4-%d7/%a0-%a3,-(%sp)
    move.w  0xFF9004,%d7
    move.l  0xFF922A,%d6
    lsr.l   #8,%d6
    move.l  0xFF9220,%d3
    lsr.l   #8,%d3
    move.l  0xFF9000,%d5
    lsr.l   #8,%d5
    lea     0xFFE000,%a2
    moveq   #29,%d4
    cmpi.w  #1,0xFF9410
    bne.s   2f
    bset    #31,%d4                 | already landed: no landing tests
2:  moveq   #20,%d2
    add.w   %d5,%d2
    moveq   #12,%d0
    add.w   %d7,%d0
    movea.w %d0,%a0
    move.w  %d3,%d0                 | low end and width of the x window
    move.w  %d5,%d1
    cmp.w   %d0,%d1
    bge.s   7f
    exg     %d0,%d1
7:  sub.w   %d0,%d1
    subi.w  #20,%d0
    movea.w %d0,%a3
    addi.w  #40,%d1
    movea.w %d1,%a1
3:  tst.b   4(%a2)
    beq.w   8f
    cmpi.b  #1,10(%a2)
    bne.w   8f
    move.w  (%a2),%d0
    sub.w   %a3,%d0
    cmp.w   %a1,%d0
    bhi.w   8f
    tst.l   %d4
    bmi.s   4f
    move.w  %d2,%d0                 | d5 - x + 20 <= 40 (unsigned)
    sub.w   (%a2),%d0
    cmpi.w  #40,%d0
    bhi.s   4f
    move.w  2(%a2),%d1
    addi.w  #20,%d1
    cmp.w   %d1,%d6
    blt.s   4f
    cmp.w   %d1,%d7
    bgt.s   4f
    move.w  %d1,%d7                 | land on it
    move.w  %d1,0xFF9004
    andi.l  #0xFFFF,%d1
    lsl.l   #8,%d1
    move.l  %d1,0xFF9400
    move.l  #0x3D90,0xFF9404
    move.w  #1,0xFF9408
    clr.w   0xFF9410
    moveq   #12,%d0
    add.w   %d7,%d0
    movea.w %d0,%a0
4:  move.w  %a0,%d0                 | d7 - y + 12 <= 31 (unsigned)
    sub.w   2(%a2),%d0
    cmpi.w  #31,%d0
    bhi.s   8f
    cmp.w   %d3,%d5
    beq.s   8f
    blt.s   5f
    move.w  (%a2),%d1               | moving right: stop at x - 13
    subi.w  #13,%d1
    cmp.w   %d1,%d5
    blt.s   8f
    move.w  (%a2),%d0
    addi.w  #13,%d0
    cmp.w   %d0,%d3
    bge.s   8f
    bra.s   6f
5:  move.w  (%a2),%d1               | moving left: stop at x + 13
    addi.w  #13,%d1
    cmp.w   %d1,%d5
    bgt.s   8f
    move.w  (%a2),%d0
    subi.w  #13,%d0
    cmp.w   %d0,%d3
    ble.s   8f
6:  move.w  %d1,%d5
    andi.l  #0xFFFF,%d5
    lsl.l   #8,%d5
    move.l  %d5,0xFF9000
    bra.s   9f
8:  lea     48(%a2),%a2
    dbf     %d4,3b
9:  movem.l (%sp)+,%d2/%d4-%d7/%a0-%a3
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
