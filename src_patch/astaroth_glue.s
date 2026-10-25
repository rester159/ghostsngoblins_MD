| Astaroth (the final room, type 13) and its shots: engine side of astaroth.c.
|
| $111BB2: `jsr hook_ast` over `moveq #0,d0` / `move.b 7(a4),d0` (the state
| dispatch of the port's handler $111B9C, entered from the object pass with
| a4 = the slot, a5 = the enemy free list, a6 = the sound queue; the handler
| saved d4-a2 and restores them at its exit $111E54). States 0 and 1 are
| astaroth.c's; 2 (death) and 3 (removal) stay the port's.
    .global hook_ast, hook_ast_die, hook_ast_shot, ast_alloc, ast_sound
hook_ast:
    cmpi.b  #2,7(%a4)
    bcc.s   1f
    move.l  %a5,ast_a5
    move.l  %a6,ast_a6
    move.l  %a4,-(%sp)
    jsr     ast_update
    addq.l  #4,%sp
    tst.l   %d0
    beq.s   2f
    jsr     0x10E9B6                | the port's boss count (+1), as its init did
2:  addq.l  #4,%sp
    jmp     0x111E54                | the handler's exit
1:  moveq   #0,%d0
    move.b  7(%a4),%d0
    rts

| C: void *ast_alloc(void): an enemy slot from the free list ($7BD2), or 0
ast_alloc:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  ast_a5,%a4
    jsr     0x7BD2
    move.l  %a2,%d0
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| C: void ast_sound(int id): $0C (the walk, the port's $B762) or the death's
ast_sound:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  ast_a6,%a6
    move.l  48(%sp),%d0
    cmpi.w  #0x0C,%d0
    bne.s   1f
    jsr     0xB762
    bra.s   9f
1:  jsr     0x8846                  | the others: the id alone, as $7915 sends them
9:  movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| $111DE8 (state 2, the death): `jsr hook_ast_die` over `tst.b 8(a4)` /
| `bne.s $111E1E`. The arcade's death ($DD67) first plays its sounds and the
| generic burst ($E8D0: 1 + 3 + 18 frames) and only then the 63-frame phase
| ($DD8C) that the port's death is, so the port removed it (and started the
| ending) 22 frames early. +9 counts the frames (ast_update keeps it 0 while
| alive); the burst is drawn as the port's first death frame. The sounds are
| the arcade's ($3F, $07 + $08, then $1C, or $32 after the first clear,
| <$7F = the port's $FF7FC0); the port's own two calls are removed.
hook_ast_die:
    tst.b   8(%a4)
    bne.s   2f                      | the port's countdown is running
    addq.b  #1,9(%a4)
    cmpi.b  #22,9(%a4)
    bcc.s   1f                      | burst done: the port's death from $111DEE
    cmpi.b  #1,9(%a4)
    bne.s   3f
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     0xB942                  | $3F
    jsr     0xB73A                  | $07, $08
    moveq   #0x1C,%d0
    tst.b   0xFF7FC0
    beq.s   4f
    moveq   #0x32,%d0
4:  jsr     0x8846
    movem.l (%sp)+,%d0-%d1/%a0-%a1
3:  moveq   #5,%d0                  | the death frame (5 left, 6 right)
    tst.b   24(%a4)
    beq.s   5f
    moveq   #6,%d0
5:  move.w  %d0,30(%a4)
    addq.l  #4,%sp
    jmp     0x111E54                | the handler's exit
1:  rts
2:  addq.l  #4,%sp
    jmp     0x111E1E

| $11B1C8 (the type-10 handler $11B1BC, after its live test): `jsr
| hook_ast_shot` over `cmpi.b #10,10(a4)`. The picture of an Astaroth shot
| (+41 = $A5; astaroth.c) only runs the port's flame animation ($11B822 the
| first time, then $11B840); its position comes from its pool slot. Anything
| else goes on to the port's type-10 handler, which saved d4-a6 and restores
| them at $11BA10.
hook_ast_shot:
    cmpi.b  #0xA5,41(%a4)
    bne.s   8f
    cmpi.b  #10,10(%a4)
    bne.s   8f
    cmpi.b  #6,0xFFC512             | the final room only
    bne.s   8f
    tst.b   42(%a4)
    bne.s   1f
    move.b  #1,42(%a4)
    moveq   #0,%d0                  | the flying animation
    jsr     0x11B822
    bra.s   2f
1:  jsr     0x11B840
2:  addq.l  #4,%sp
    jmp     0x11BA10
8:  cmpi.b  #10,10(%a4)
    rts

| C: void ast_pic_free(void *slot): a shot's picture back to the enemy free list
    .global ast_pic_free
ast_pic_free:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  48(%sp),%a2
    clr.w   4(%a2)
    clr.b   7(%a2)
    clr.w   8(%a2)
    clr.b   41(%a2)
    move.l  ast_a5,%a4
    jsr     0x7BEC
    movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts

| $32EE (the shot pool pass of stages 2-6 and the final room, $329E, its type
| chain): `jsr hook_pool10` over `cmpi.b #9,10(a4)` (then `bne.w` to the
| assert). A type-10 projectile (an Astaroth shot, astaroth.c) gets the
| on-screen test on the arcade's schedule ($FC62: (<$21 + <$E0) & 3 = 0, as the
| port's type 6 at $7282 -> $73B4, the same table) and ast_pool_update; when
| that frees it ($FECD), it goes back on the pool's list (a5, $7BEC). a3 = the
| pass context (+8 the frame counter, +9 the slot counter).
    .global hook_pool10
hook_pool10:
    cmpi.b  #10,10(%a4)
    bne.s   8f
    move.b  8(%a3),%d0
    add.b   9(%a3),%d0
    andi.w  #3,%d0
    bne.s   1f
    jsr     0x73B4
1:  move.l  %a4,-(%sp)
    jsr     ast_pool_update
    addq.l  #4,%sp
    tst.l   %d0
    beq.s   2f
    move.l  %a4,-(%sp)
    move.l  %a4,%a2
    move.l  %a5,%a4
    jsr     0x7BEC                  | $8E38
    move.l  (%sp)+,%a4
2:  addq.l  #4,%sp
    jmp     0x3332                  | the next slot
8:  cmpi.b  #9,10(%a4)
    rts

| $AE9C (the pool's sprite builder, its type chain): `jsr hook_pool_draw`
| over `cmpi.b #3,10(a4)` (then `beq.s`). Type 10 (an Astaroth shot) has no
| picture here (its enemy slot draws it): no pieces, on to the next slot.
    .global hook_pool_draw
hook_pool_draw:
    cmpi.b  #10,10(%a4)
    bne.s   8f
    addq.l  #4,%sp
    moveq   #0,%d0
    moveq   #0,%d1
    jmp     0xAED0
8:  cmpi.b  #3,10(%a4)
    rts

| C: int ast_floor(int x, int y): the arcade's floor probe $8CA7 for size
| class 0 (the shot: x - 8, y - 8, then the tile below, $8DA6/$8D7A), with the
| port's own copy ($85D2 on the terrain map at $FF0000, heights $14A6E, the
| arcade's $42C0). Returns the snap (the arcade's B) or -1 for no floor.
    .global ast_floor
ast_floor:
    movem.l %d2-%d7/%a2-%a6,-(%sp)
    move.l  48(%sp),%d0
    move.l  52(%sp),%d1
    lea     0xFF0000,%a0
    lea     ast_probe(%pc),%a4
    lea     0x14A6E,%a3
    jsr     0x85D2
    tst.l   %d0
    beq.s   1f
    moveq   #0,%d0
    move.b  %d1,%d0
    bra.s   2f
1:  moveq   #-1,%d0
2:  movem.l (%sp)+,%d2-%d7/%a2-%a6
    rts
ast_probe:
    .word   8, 8, 32

    .bss
    .even
ast_a5: .space 4
ast_a6: .space 4

| ---- the end of the final room (ending.c) -------------------------------
| $10EA5A: `jmp hook_room_end` over the port's room-end block (after the last
| boss of stages 2-6 is removed: $FFDB08 = 1, a 240-frame wait $FFDB0A,
| 1,000 points ($0C09), sound $3F). In the final room the arcade has none of
| it ($E844 at stage index 6: no sound, no points, the ending from the next
| frame), so there the wait is 0 and nothing else is done.
    .global hook_room_end, hook_end_frame, hook_end_start
    .text
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

| $113916 (the port's ending routine, each update of the final room): `jsr
| hook_end_frame` over `tst.b $FF7FC2`. While the princess scene runs
| (end_frame returns 1) the routine returns 1 (the game update is skipped).
hook_end_frame:
    pea     end_trigger(%pc)
    jsr     end_frame
    addq.l  #4,%sp
    tst.l   %d0
    beq.s   1f
    addq.l  #4,%sp
    moveq   #1,%d0
    rts
1:  tst.b   0xFF7FC2
    rts
end_trigger:
    jsr     0x10EAA4
    ext.l   %d0
    rts

| $11392A (the ending starts): `jsr hook_end_start` + nop over `move.b
| #1,$FF7FC2`.
hook_end_start:
    move.b  #1,0xFF7FC2
    movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     end_start
    movem.l (%sp)+,%d0-%d1/%a0-%a1
    rts

| C: void end_black(void): the room's planes cleared for the first clear's
| text (plane B $C000 whole, plane A $E000 rows 3-24), with the display off
| for the length of it (full VRAM bandwidth; the screen goes black anyway)
| and interrupts off so the VBlank's VDP accesses can't come in between.
    .global end_black
end_black:
    move.w  %sr,-(%sp)
    move.w  #0x2700,%sr
    movem.l %d1/%a0,-(%sp)
    lea     0xC00000,%a0
    move.w  #0x8124,4(%a0)          | display off (the port keeps $64)
    move.w  #0x8F02,4(%a0)
    moveq   #0,%d1
    move.l  #0x40000003,4(%a0)      | VRAM $C000: 4 KiB
    move.w  #4096/32-1,%d0
1:  .rept 8
    move.l  %d1,(%a0)
    .endr
    dbf     %d0,1b
    move.l  #0x61800003,4(%a0)      | VRAM $E180 (row 3): 22 rows
    move.w  #22*128/32-1,%d0
2:  .rept 8
    move.l  %d1,(%a0)
    .endr
    dbf     %d0,2b
    move.w  #0x8164,4(%a0)          | display on (DMA off, as $704BE leaves it)
    movem.l (%sp)+,%d1/%a0
    move.w  (%sp)+,%sr
    rts
