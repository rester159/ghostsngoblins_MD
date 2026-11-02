| Firebrand's Vendetta hooks (vendetta.c). Vendetta is Home (mode 2) with
| home_sub 3: the word at $FF5004 (Persist mode, home_sub) is $0203.

    .section .text,"ax"
    .global vd_sound, vd_satan_gone, vd_start_entry, vd_cp_cmp, vd_cam_xgap, vd_cam_ygap, vd_cam_speed, vd_cam_init, vd_cam_s6, vd_cam_lead

| $103E72: `jsr vd_start_entry` over `lea $1040CC(pc),a1` / `adda.w d0,a1`
| (d0 = (checkpoint * 7 + stage index) * 4): Vendetta's checkpoint-0 entries
| are vd_starts, the stages' far ends.
vd_start_entry:
    lea     0x1040CC,%a1
    cmpi.w  #0x0203,0xFF5004
    bne.s   1f
    cmpi.w  #7*4,%d0
    bcc.s   1f
    lea     vd_starts,%a1
    cmpi.w  #5*4,%d0                | stage 6 before its Satan is dead: his room
    bne.s   1f
    tst.b   vd_satan_done
    bne.s   1f
    lea     vd_satan_start-5*4,%a1
1:  adda.w  %d0,%a1
    rts

| $110558: `jsr vd_satan_gone` + nop over `jsr $10EA0C` (the port's boss
| count down: at 0 the stage-end sequence and the key) / `clr.w 4(a4)` at a
| Satan's removal. Vendetta's opening Satan only marks the regicide done:
| no key, the way down stays open.
vd_satan_gone:
    cmpi.w  #0x0203,0xFF5004
    beq.s   1f
    jsr     0x10EA0C
    bra.s   2f
1:  move.b  #1,vd_satan_done
2:  clr.w   4(%a4)
    rts

| $103CB0: `jsr vd_cp_cmp` + `bls.s` over `cmp.w (a0,d0.w),d1` / `bls.w`
| (d1 = the camera x, (a0,d0.w) = the stage's checkpoint mark): ls = not
| passed. Vendetta passes it with the camera 16 px left of the mark instead
| (stage 6's mark is its left limit, which the camera touches by a pixel:
| that sent a death to the tower's foot, Vendetta's end of the stage).
vd_cp_cmp:
    cmpi.w  #0x0203,0xFF5004
    beq.s   1f
    cmp.w   (%a0,%d0.w),%d1
    rts
1:  movem.l %d2,-(%sp)
    move.w  (%a0,%d0.w),%d2
    subi.w  #16,%d2
    cmp.w   %d1,%d2
    movem.l (%sp)+,%d2
    rts

| The camera object ($FFF420, follow routine $10414A) holds the player 128 px
| from the screen's left and 142 px above its bottom, scrolling down at 1, 3
| or 5 px a frame. Vendetta goes left and down: it holds him 176 px from the
| left (VD_XREST, vendetta.c), so more of the way ahead is on screen; and
| while he drops below where he left the ground the camera leads down by
| vd_lead px (vd_frame: up to 48) and scrolls down at 1, 4 or 7 px a frame.
| His standing height on screen stays the game's: the screen's top is
| Firebrand's ceiling, and a camera held lower stopped his jumps.
    .set    XBIAS, 176 - 128
    .set    ARENA_BIAS, 240 - 176

| $10415C: `jsr vd_cam_xgap` over `sub.w d1,d0` / `tst.w d0` / `bmi.s $104198`
| (d0 his x, d1 the camera's): the gap, and the bmi's branch taken by
| returning there.
vd_cam_xgap:
    sub.w   %d1,%d0
    cmpi.w  #0x0203,0xFF5004
    bne.s   1f
    subi.w  #XBIAS,%d0
    tst.b   vd_arena                | Arthur's fight: no scroll until 240 px
    beq.s   1f
    subi.w  #ARENA_BIAS,%d0
1:  tst.w   %d0
    bpl.s   2f
    move.l  #0x104198,(%sp)
2:  rts

| $1042BE: `jmp vd_cam_lead` over the scroll's new x (the low word of his x
| 128 px back, the carry out of the camera's page for the page step): 176 px
| back in Vendetta
vd_cam_lead:
    move.w  2(%a4),%d0
    sub.w   10(%a3),%d0
    cmpi.w  #0x0203,0xFF5004
    beq.s   1f
    subi.w  #0x8000,%d0
    bra.s   2f
1:  subi.w  #176 << 8,%d0
2:  add.w   10(%a3),%d0
    rts

| $1041E6: `jsr vd_cam_ygap` over `sub.w d1,d0` / `tst.b 1(a3)` (d0 his y,
| d1 the camera's; the flags are the tst's for the bne that follows)
vd_cam_ygap:
    sub.w   %d1,%d0
    cmpi.w  #0x0203,0xFF5004
    bne.s   1f
    sub.w   vd_lead,%d0
1:  tst.b   1(%a3)
    rts

| $1042D0: `jmp vd_cam_speed` over the start of the speed lookup (d0 = the
| band, a3@5, times 4; a0 = the table: up, down words per band)
vd_cam_speed:
    moveq   #0,%d0
    move.b  5(%a3),%d0
    cmpi.w  #3,%d0
    bcc.s   2f
    lsl.w   #2,%d0
    lea     0x10441E,%a0
    cmpi.w  #0x0203,0xFF5004
    bne.s   1f
    lea     vd_speeds,%a0
1:  rts
2:  jmp     0x1042E4

vd_speeds:
    .word   0x100, -0x100, 0x300, -0x400, 0x500, -0x700

| $104372: `jsr vd_cam_init` + 2 nops over `move.w d0,32(a3)` / `move.w
| d1,34(a3)` / `bsr.s $1043C4` at the end of the camera's set-up ($1042F4,
| which starts it at the 256 px page of the restart entry): Vendetta's is
| put on him (vd_cam_place).
vd_cam_init:
    move.w  %d0,32(%a3)
    move.w  %d1,34(%a3)
    cmpi.w  #0x0203,0xFF5004
    bne.s   1f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     vd_cam_place
    movem.l (%sp)+,%d0-%d1/%a0-%a1
1:  jmp     0x1043C4

| $110A2C / $119724: `jsr vd_cam_s6` + `bra.s` over stage 6's set-up of the
| camera at the tower's foot (7424, 1536: $FF9100/2 and the object's x/y)
vd_cam_s6:
    move.w  #7424,0xFF9100
    move.w  #1536,0xFF9102
    move.l  #7424 << 8,0xFFF428
    move.l  #1536 << 8,0xFFF42C
    cmpi.w  #0x0203,0xFF5004
    bne.s   1f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     vd_cam_place
    movem.l (%sp)+,%d0-%d1/%a0-%a1
1:  rts

| C: void vd_sound(int id): a sound on the player's queue ($8846, a6 = $FF9500)
vd_sound:
    move.l  4(%sp),%d0
    movem.l %d1/%a1/%a6,-(%sp)
    lea     0xFF9500,%a6
    jsr     0x8846
    movem.l (%sp)+,%d1/%a1/%a6
    rts
