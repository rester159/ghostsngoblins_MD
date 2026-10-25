| After a boss dies: the arcade's stage-end freeze (docs/ACCURACY.md, Fixed 34).
| Hooks: tools/patch_gng.py.
|
| The arcade's boss removal ($E844, <$B6 down to 0) sets <$08 = 2, and from
| the next frame the play frame $72A1 is replaced by the stage-end frame
| $72C9 (stage index 0-5): input, the stage-end object ($7557, the falling
| key, in weapon slot 0 = $0540), Arthur ($744F, which still runs his normal
| handler $90AB, throws included), the platform/tombstone objects ($E2B4) and
| the scroll ($8021); then it draws the objects ($F811), Arthur and slot
| $0540 only. Not run any more: the weapons ($9C68), the enemies ($A0A6), the
| enemy shots ($FC57), the item/score slots ($15E2, $E612), the collisions
| ($EF17) and their draws ($F7E5, $F7CF, $F7FB, $F827). So everything in
| those tables stays where it is, unseen, and still occupies its slot: a
| weapon slot is only freed by the weapon's own handler, so with slot 0 taken
| by the key Arthur gets at most one more lance (two slots, $9FA9), which
| also stays put. The port ran all of them until the key was picked up.
|
| Here, "stage end" is the port's boss-dead flag $FFC8D6 = 2 (set by every
| boss's death, $71FFC / $118014 / $1185A6 / $1195E6 / the dragon's boss
| count; set back to 1 by the stage init $266E), stage index 0-5.

    .section .text,"ax"

    .set    BOSS_DEAD, 0xFFC8D6
    .set    STAGE, 0xFFC512
    .set    ENEMIES, 0xFFB800           | 40 x 48, +4 live
    .set    SHOTS, 0xFFC100             | 6 x 48, +4 live
    .set    WEAPONS, 0xFF9600           | 3 x 32, +8 allocated, +9 on screen

| Z clear (bne) while the stage end is on. d0 unchanged.
    .global se_active
se_active:
    cmpi.b  #2,BOSS_DEAD
    bne.s   2f
    cmpi.b  #6,STAGE
    bcc.s   2f
    andi.b  #0xFB,%ccr              | Z = 0
    rts
2:  ori.b   #0x04,%ccr              | Z = 1
    rts

| $6974 / $1055A4: `jmp se_objpass` / `jmp se_objpass2` + nop over
| `jsr $69A2` (`jsr $1055D4`) and `movem.l a0/a3-a5,-(sp)`: the two cores
| of the enemy pass (enemies, their shots, their hits on Arthur and the
| weapons' hits on them), called by every stage's pass wrapper after the
| random counter step (rng_tick).
    .global se_objpass, se_objpass2
se_objpass:
    bsr.s   se_active
    bne.s   9f
    jsr     0x69A2
    movem.l %a0/%a3-%a5,-(%sp)
    jmp     0x697C
se_objpass2:
    bsr.s   se_active
    bne.s   9f
    jsr     0x1055D4
    movem.l %a0/%a3-%a5,-(%sp)
    jmp     0x1055AC
9:  rts

| $BC26: `jmp se_wmove` over `jmp $1158D0`, the weapon pass ($523C after
| the hit handling). Its first step shows the throwing frame on Arthur
| (the throw timer $FF9700 and frame $FF9704 come from the throw at
| $115DFC, which still runs, as the arcade's $90AB does); the slot loop is
| skipped.
    .global se_wmove
se_wmove:
    bsr     se_active
    bne.s   1f
    bsr.s   w_visible
    jmp     0x1158D0
1:  tst.b   0xFF9700
    beq.s   2f
    move.w  0xFF9704,0xFF9206
2:  rts

| Weapons off the screen (docs/ACCURACY.md, Fixed 35). The arcade's weapon
| slot has two flags: -$10 allocated, -$F on screen. Every frame, before the
| weapon moves, $8E41 sets -$F from its position against the camera (<$9C,
| <$9E) and the window of its class -1,X (table $8E67: class 0 x + 8 - cam
| <= $110, class 2 x + 16 - cam <= $110 + $10; both y - camy <= $100,
| unsigned): weapon type 1 flies in class 2 ($9E39), the others in class 0
| ($9CAC), and a burst is class 0 ($9D8D, table $9DBA). Off the screen a
| weapon flies on to the end of its range (and keeps its slot) but isn't
| drawn ($F7E5) and hits nothing: enemies ($EF4A), tombstones ($F6A2) and
| shots ($F3CE) all test -$F. The port's +9 was set with +8 at the throw
| and cleared with it at the end ($115AF0), and every hit test already
| takes +8 AND +9 ($BE68, $6B2E, $10457E, shots.c); so +9 becomes the
| arcade's on-screen flag here, and the build draws by it ($115960).
w_visible:
    movem.l %d0-%d2/%a0,-(%sp)
    lea     WEAPONS,%a0
    moveq   #2,%d2
1:  tst.b   8(%a0)
    beq.s   4f
    move.l  (%a0),%d0
    lsr.l   #8,%d0
    sub.w   0xFF9100,%d0
    moveq   #8,%d1                  | class 0: x + 8 - cam <= $110
    cmpi.b  #1,11(%a0)
    bne.s   2f
    cmpi.b  #2,12(%a0)
    bcc.s   2f
    moveq   #16,%d1                 | class 2 (type 1 in flight): + 16 <= $120
2:  add.w   %d1,%d0
    add.w   %d1,%d1
    addi.w  #0x100,%d1
    cmp.w   %d1,%d0
    bhi.s   3f
    move.l  4(%a0),%d0
    lsr.l   #8,%d0
    sub.w   0xFF9102,%d0
    cmpi.w  #0x100,%d0
    bhi.s   3f
    move.b  #1,9(%a0)
    bra.s   4f
3:  clr.b   9(%a0)
4:  lea     32(%a0),%a0
    dbf     %d2,1b
    movem.l (%sp)+,%d0-%d2/%a0
    rts

| The spawner (docs/ACCURACY.md, Fixed 36). The arcade's ($E950 -> $EA41 ->
| $ECD6, records at $EB08, enemies placed at $EBB1) runs once a frame after
| the enemies ($A0A6) and the scroll ($8021, which also copies the camera
| to <$9C at $815F), so it sees this frame's camera, Arthur after his move
| and the frame's random, and a new enemy's first update is the next
| frame. Stage 1's loop calls the port's ($26DA, through $A460 at $91E)
| in that place, after the scroll ($104382, which writes $FF9100/$FF9102);
| the eight other loops that call it did so before their enemy pass and the scroll, so it
| saw the camera a scroll step behind and the enemy it made moved in the
| same update. Those calls are gone ($104AD2, $10EF2E, $10FDDE, $110DDC,
| $1179FC, $118A80, $118FBE, $119B08) and se_scroll_spawn runs it right
| after their scroll ($104B0C's `jsr $525E` in the first, which calls
| $104382 with a 4-byte jsr just before). Not in the stage end, where the
| arcade doesn't call $E950.
    .global se_spawn, se_scroll_spawn, se_525e_spawn
se_scroll_spawn:
    jsr     0x104382
    bra.s   se_spawn
se_525e_spawn:
    jsr     0x525E
se_spawn:
    bsr     se_active
    bne.s   1f
    jmp     0x26DA
1:  rts

| $C348C / $C35E8: `jmp se_items` / `jmp se_items_draw` over `jmp $11677A`
| / `jmp $11693E`: the two item/pickup objects ($FF9780, $FFCEA0; the
| arcade's two $15E2 slots) and their draw.
    .global se_items, se_items_draw
se_items:
    bsr     se_active
    bne.s   1f
    jmp     0x11677A
se_items_draw:
    bsr     se_active
    bne.s   1f
    jmp     0x11693E
1:  rts

| $102C56: `jsr se_wtomb` + 3 nops over `jsr $104546` / `move.w #71,$FFCFB0`
| (stage 1's weapons against the tombstones; the arcade's $F6A2 is part of
| the collisions it no longer runs).
    .global se_wtomb
se_wtomb:
    bsr     se_active
    bne.s   1f
    jsr     0x104546
1:  move.w  #71,0xFFCFB0
    rts

| The draw: every stage's sprite build draws the enemies, their shots and
| the weapons (with Arthur) from the same tables. While the stage end is on,
| their live flags are cleared for the build and put back at the start of
| the next update (se_pace), before any game logic runs.
| se_rg / se_rg1 stand in for render_gate / render_gate1 (glue.s) at the
| builds' entries and go on to them.
    .global se_rg, se_rg1, se_pace
se_rg:
    bsr.s   se_hide
    jmp     render_gate
se_rg1:
    bsr.s   se_hide
    jmp     render_gate1

se_hide:
    bsr     se_active
    beq.s   9f
    tst.b   se_hidden
    bne.s   9f
    movem.l %d0/%a0-%a1,-(%sp)
    lea     se_save,%a1
    lea     ENEMIES+4,%a0
    moveq   #39,%d0
1:  move.b  (%a0),(%a1)+
    clr.b   (%a0)
    lea     48(%a0),%a0
    dbf     %d0,1b
    lea     SHOTS+4,%a0
    moveq   #5,%d0
2:  move.b  (%a0),(%a1)+
    clr.b   (%a0)
    lea     48(%a0),%a0
    dbf     %d0,2b
    lea     WEAPONS+9,%a0
    moveq   #2,%d0
3:  move.b  (%a0),(%a1)+
    clr.b   (%a0)
    lea     32(%a0),%a0
    dbf     %d0,3b
    st      se_hidden
    movem.l (%sp)+,%d0/%a0-%a1
9:  rts

| $6938: `jmp se_pace` (patch_gng.py, in place of `jmp pace_hook`). Puts
| the hidden flags back (unless the stage has changed since: the stage init
| $266E sets $FFC8D6 back to 1, and a new stage's slots are its own), and on the
| first update of the stage end marks weapon slot 0 as taken, as the
| arcade's key takes slot $0540 on the frame after the boss's removal (its
| $7557 runs before Arthur's throw, as this does).
se_pace:
    movem.l %d0/%a0-%a1,-(%sp)
    tst.b   se_hidden
    beq.s   4f
    clr.b   se_hidden
    cmpi.b  #2,BOSS_DEAD
    bne.s   4f
    lea     se_save,%a1
    lea     ENEMIES+4,%a0
    moveq   #39,%d0
1:  move.b  (%a1)+,(%a0)
    lea     48(%a0),%a0
    dbf     %d0,1b
    lea     SHOTS+4,%a0
    moveq   #5,%d0
2:  move.b  (%a1)+,(%a0)
    lea     48(%a0),%a0
    dbf     %d0,2b
    lea     WEAPONS+9,%a0
    moveq   #2,%d0
3:  move.b  (%a1)+,(%a0)
    lea     32(%a0),%a0
    dbf     %d0,3b
4:  bsr     se_active
    bne.s   5f
    clr.b   se_slot0
    bra.s   6f
5:  tst.b   se_slot0
    bne.s   6f
    st      se_slot0
    move.b  #1,WEAPONS+8
6:  movem.l (%sp)+,%d0/%a0-%a1
    jmp     pace_hook

    .lcomm  se_save, 49
    .lcomm  se_hidden, 1
    .lcomm  se_slot0, 1
