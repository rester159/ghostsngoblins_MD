| Stage 2's streamer ($11A89C) without the display-off reload for a segment,
| window or bank change (segswap.c).

    .section .text,"ax"
    .global seg_check, bank_hook

| $11A8B6-$11A8D3: `jsr seg_check` / `bne.w $11A936` / `bra.s $11A8D4` over
| the window test (`bsr $11AA08` / `cmp.w $FFB00C,d0` / `bne.w $11A936`) and
| the segment test (`move.w d6,d0` / `bsr $11A9C4` / `cmp.w $FFB01C,d0` /
| `bne.w $11A936`). Z clear: the reload, as before.
seg_check:
    movem.l %d1/%a0-%a1,-(%sp)
    jsr     0x11AA08                | d0: the window of d6
    cmp.w   0xFFB00C,%d0
    beq.s   1f
    move.l  %d0,-(%sp)
    jsr     winart_step
    addq.l  #4,%sp
1:  move.w  %d6,%d0
    jsr     0x11A9C4                | d0: the segment of d6
    cmp.w   0xFFB01C,%d0
    beq.s   2f
    andi.l  #0xFFFF,%d0
    move.l  %d0,-(%sp)
    jsr     seg_step
    addq.l  #4,%sp
    bra.s   3f
2:  moveq   #0,%d0
3:  movem.l (%sp)+,%d1/%a0-%a1
    tst.w   %d0
    rts

| $11AA4E (in $11AA44, the bank test, d0 the new bank): `jmp bank_hook`
| over `jsr $39669E` (display off) / `nop` / `bsr.s $11AA28` / display on;
| returns for $11AA44.
bank_hook:
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    andi.l  #0xFF,%d0
    move.l  %d0,-(%sp)
    jsr     bank_step
    addq.l  #4,%sp
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts
