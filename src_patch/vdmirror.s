| Firebrand's Vendetta shown mirrored (vendetta.c vd_mirror): the stages run
| backwards, right to left in the game's world, and the screen shows that world
| mirrored, so Firebrand goes left to right on the screen. The game itself is
| untouched (positions, collisions, the camera, every enemy); only what reaches
| the VDP is turned round:
|  - plane B (the whole stage; plane A, the HUD, doesn't scroll and stays):
|    world cell column c is drawn at plane column 63 - (c & 63), each entry with
|    its h flip toggled. The game writes plane B in two places in play: the
|    column streamer ($94D8, every stage, which also draws a stage's start) and
|    each stage's row upload (`jsr $704BE` of $FF0A00, 256 bytes); stage 2's
|    windows (bossart.c) do the same themselves;
|  - plane B's h scroll -v becomes v - 256 (screen x maps to 255 - x), after
|    every stage loop's scroll write (parallax.s par_9600's tail, stage 1's
|    mountain rows included) and at a stage start (pad.c stage_hold);
|  - the sprites: x becomes 512 - x - width, h flip toggled (a copy of the
|    table is uploaded, glue.s hook_sat_dma);
|  - left and right on the pad trade places (pad.c).
| The buffers live in the RAM the game never touches ($FF2BE1-$FF6FFF).

    .equ    VDM_SAT, 0xFF4000       | the mirrored sprite table (80 x 8 bytes)
    .equ    VDM_ROW, 0xFF4280       | the mirrored row upload (256 bytes)

    .section .text,"ax"
    .global vdm_col, vdm_row_dma, vdm_scroll, vdm_sat_dma

| $94D8: `jmp vdm_col` + nop over `cmpi.w #-1,$FFB002`. The streamer draws the
| two cell columns of 16 px column k ($FFB002 & 31) from $FF0800 (32 entries,
| 64 bytes skipped, 32 entries), down the plane (auto-increment 128).
vdm_col:
    cmpi.w  #-1,0xFFB002
    beq.s   9f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     vd_mirror
    tst.l   %d0
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    bne.s   1f
    jmp     0x94E4                  | not mirrored: the game's own
9:  rts
1:  movem.l %d0-%d4/%a0,-(%sp)
    move.w  #0x8F80,0xC00004
    moveq   #0,%d4
    move.w  0xFFB002,%d4
    andi.w  #31,%d4
    lsl.w   #2,%d4
    neg.w   %d4
    addi.w  #0xC000+126,%d4         | cell column 63 - 2k
    lea     0xFF0800,%a0
    move.l  #0x08000800,%d3
    moveq   #1,%d2
2:  move.l  %d4,%d0
    andi.w  #0x3FFF,%d0
    ori.w   #0x4000,%d0
    swap    %d0
    ori.l   #3,%d0
    move.l  %d0,0xC00004
    moveq   #15,%d1
3:  move.l  (%a0)+,%d0
    eor.l   %d3,%d0
    move.l  %d0,0xC00000
    dbf     %d1,3b
    adda.w  #64,%a0
    subq.w  #2,%d4                  | the second: 62 - 2k
    dbf     %d2,2b
    move.w  #0x8F02,0xC00004
    move.w  #-1,0xFFB002
    addq.l  #1,0xFFB004
    movem.l (%sp)+,%d0-%d4/%a0
    rts

| Each stage's row upload: `jsr vdm_row_dma` over `jsr $704BE` (a0 = $FF0A00,
| d0 = 256, d1 = the plane address of a 2-row band). Mirrored, the band goes
| up from VDM_ROW: each row's 64 entries reversed, h flips toggled.
vdm_row_dma:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     vd_mirror
    tst.l   %d0
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    beq.s   9f
    movem.l %d2-%d3/%a1,-(%sp)
    lea     VDM_ROW+128,%a1
    move.w  #0x0800,%d3
    moveq   #63,%d2
1:  move.w  (%a0)+,-(%a1)
    eor.w   %d3,(%a1)
    dbf     %d2,1b
    lea     VDM_ROW+256,%a1
    moveq   #63,%d2
2:  move.w  (%a0)+,-(%a1)
    eor.w   %d3,(%a1)
    dbf     %d2,2b
    movem.l (%sp)+,%d2-%d3/%a1
    lea     VDM_ROW,%a0
9:  jmp     0x704BE

| parallax.s par_9600's exits (after the stage loop's scroll write, held frames
| included): plane B's h scroll -v as v - 256. Stage 1 with its mountain rows
| on (par_ok) has 28 row entries, every 32 bytes from $FC02; otherwise $FC02.
| The values are read back from VRAM, so they are whatever the frame wrote.
vdm_scroll:
    movem.l %d0-%d2/%a0-%a1,-(%sp)
    jsr     vd_mirror
    tst.l   %d0
    beq.s   9f
    lea     0xC00004,%a0
    lea     0xC00000,%a1
    moveq   #0,%d2                  | rows after the first
    tst.b   0xFFC512
    bne.s   1f
    tst.b   par_ok
    beq.s   1f
    moveq   #27,%d2
1:  move.l  #0x3C020003,%d1         | read $FC02
2:  move.l  %d1,(%a0)
    move.w  (%a1),%d0
    neg.w   %d0
    subi.w  #256,%d0
    bset    #30,%d1                 | write it
    move.l  %d1,(%a0)
    move.w  %d0,(%a1)
    bclr    #30,%d1
    addi.l  #0x00200000,%d1         | the next row's entry
    dbf     %d2,2b
9:  movem.l (%sp)+,%d0-%d2/%a0-%a1
    jmp     copy9600

| glue.s hook_sat_dma's end, in place of `jmp $704BE` (a0 = $FFB500,
| d0 = bytes): mirrored, the copy at VDM_SAT goes up instead.
vdm_sat_dma:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    move.l  %d0,-(%sp)
    jsr     vd_mirror_sat
    addq.l  #4,%sp
    tst.l   %d0
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    beq.s   9f
    lea     VDM_SAT,%a0
9:  jmp     0x704BE
