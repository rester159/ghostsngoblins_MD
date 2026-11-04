| Stage 1's far mountains in parallax (all modes; install_parallax in
| tools/patch_gng.py).
|
| Stage 1 draws everything on plane B with one horizontal scroll for the
| whole screen (VDP register 11 = 0, $FC02 = -$FF9100). The mountains are
| plane B rows 8-13, world x 112-352, and nothing else is in those rows until
| the hill's tree tops and crosses at x 640. So while the camera is left of
| PAR_END (and the vertical scroll is the stage's usual 16, plane row 8 on
| screen row 6), the screen rows that show plane rows 8-13 get their own
| scroll (register 11 = 2, one entry per 8-line row) and look further right,
| by d = (PAR_END - cam) * PAR_K / 256 px: the mountains sit d px to the left
| of where they were drawn and drift at 1 - PAR_K/256 of the camera's speed.
| At PAR_END d is 0 and the view there (x 368-624 in those rows) is empty
| either way, so the hand-over is seamless, both ways (it is a function of
| the camera only: a walk back gets the same picture). Those rows read world
| x cam .. cam + d + 256 from the ring, which the streamer keeps from
| cam - 128 to cam + 384 (after the stage draw's 0-511), so it already holds
| them.
|
| Every stage loop's $FF9600 copy (patch_gng.py, ten places) comes here
| first. It runs after the loop's scroll write on every path (a held frame,
| glue.s hook_sat_dma, returns there too), so the scroll read back from the
| VDP is the one on screen this frame. Outside the parallax the register is
| put back to 0 (one word): the other stages, and stage 1 past PAR_END, scroll
| as they always did.
|
| Cost (68000 cycles, counted): other stages ~60 (0.1 line); stage 1 past
| the hand-over ~260; stage 1 with the mountains on screen ~950 (2 lines of
| the VBlank: 56 unrolled VDP word writes).

    .equ    PAR_END, 368            | camera x where the parallax hands over
    .equ    PAR_K,   96             | 256 * (1 - mountain speed): 96 = 5/8 of the camera's speed
    .equ    PAR_ROW0, 6             | screen rows 6-11: plane rows 8-13 at v scroll 16
    .equ    PAR_ROWS, 6

    .section .text,"ax"
    .global par_9600
par_9600:
    tst.b   0xFFC512                | stage 1 only
    beq.s   1f
    move.w  #0x8B00,0xC00004        | one scroll for the whole screen
    jmp     copy9600
1:  movem.l %d0-%d2/%a0-%a1,-(%sp)
    lea     0xC00004,%a0
    lea     0xC00000,%a1
    move.l  #0x00020010,(%a0)       | VSRAM read 2: plane B's v scroll
    cmpi.w  #16,(%a1)
    bne.w   8f
    move.l  #0x3C020003,(%a0)       | VRAM read $FC02: plane B's h scroll
    move.w  (%a1),%d0               | -cam
    move.w  #PAR_END,%d1
    add.w   %d0,%d1                 | PAR_END - cam
    ble.w   8f                      | (signed) at or past the hand-over
    mulu    #PAR_K,%d1
    lsr.l   #8,%d1                  | d
    move.w  %d0,%d2
    sub.w   %d1,%d2                 | -(cam + d)
    moveq   #0,%d1
    move.w  #0x8B02,(%a0)           | h scroll per 8-line row
    move.w  #0x8F20,(%a0)           | auto-increment 32: one row's entry to the next
    move.l  #0x7C000003,(%a0)       | plane A, rows 0-27: 0, as the loops write it
    .rept   28
    move.w  %d1,(%a1)
    .endr
    move.l  #0x7C020003,(%a0)       | plane B
    .rept   PAR_ROW0
    move.w  %d0,(%a1)
    .endr
    .rept   PAR_ROWS
    move.w  %d2,(%a1)
    .endr
    .rept   28-PAR_ROW0-PAR_ROWS
    move.w  %d0,(%a1)
    .endr
    move.w  #0x8F02,(%a0)
    bra.s   9f
8:  move.w  #0x8B00,(%a0)           | one scroll for the whole screen
9:  movem.l (%sp)+,%d0-%d2/%a0-%a1
    jmp     copy9600

| Every `move.w #$8104,$C00004` (display off: a new screen is being drawn;
| fourteen places, patch_gng.py): the display off, then one scroll for the
| whole screen. The stage map after a death scrolls only $FC00/$FC02, so
| with register 11 still 2 its rows kept the stage's scrolls (measured: the
| map drawn in two halves, and the stage's redraw after it).
    .global par_dispoff
par_dispoff:
    move.w  #0x8104,0xC00004
    move.w  #0x8B00,0xC00004
    rts
