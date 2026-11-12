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
    jsr     score_now                   | hud.s: this update's kill scores
    movem.l %a0/%a3-%a5,-(%sp)
    jmp     0x697C
se_objpass2:
    bsr.s   se_active
    bne.s   9f
    jsr     0x1055D4
    jsr     score_now
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
    tst.b   0xFFCEA4                | an item object live (bmart.c ch_live):
    bne.s   2f                      | the cache off its tiles
    tst.b   0xFFC8C4
    bne.s   2f
    tst.b   0xFF9784
    beq.s   3f
2:  movem.l %d0-%d1/%a0-%a1,-(%sp)
    jsr     item_guard
    movem.l (%sp)+,%d0-%d1/%a0-%a1
3:  jmp     0x11677A
se_items_draw:
    bsr     se_active
    bne.s   1f
    jmp     0x11693E
1:  rts

| $10F1C8 / $110166 / $11111C: `jmp item_reload4/5/6` over `lea <table>,a0`.
| Stages 4-6 load their enemy and item tables a second time after the stage
| start's item init ($C3456), falling into their item-table init ($10F1FC /
| $11019A / $111154), which clears $FFCE10-$FFCE5B and with it $FFCE18, the
| second item object ($FFCEA0) that $C3456 points it at; stages 1-3 don't.
| A hidden item's drop ($C2F9E, the arcade's $E402: the pot when Arthur has
| lost his armor) went to address 0, so stage 6's pot never came.
    .global item_reload4, item_reload5, item_reload6
item_reload4:
    lea     0x247C14,%a0
    jsr     0x10F1CE
    bra.s   1f
item_reload5:
    lea     0x254414,%a0
    jsr     0x11016C
    bra.s   1f
item_reload6:
    lea     0x25DBC4,%a0
    jsr     0x111122
1:  move.l  #0xFFCEA0,0xFFCE18
    rts

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
6:  jsr     frac_keep               | hud.s: Arthur's fraction for a restart
    movem.l (%sp)+,%d0/%a0-%a1
    jmp     pace_hook

| $8A550 (`jsr door_art`, over `lea 0xA0700,a0`): the stage-end door's
| opening art for kind 1 (stages 2 on; kind 0, stage 1's, is $A0000). It is
| stage 1's art with its colours moved for another palette line, which drew
| the opening door in other colours than the closed one beside it: teal with
| orange edges in stage 2, red in stage 5, ochre in stage 6. Those stages
| take copies in the closed door's greys of their line 1 (filled by
| tools/patch_gng.py).
    .global door_art, door2_art, door5_art, door6_art
door_art:
    lea     0xA0700,%a0
    cmpi.b  #1,0xFFC512
    bne.s   1f
    lea     door2_art,%a0
1:  cmpi.b  #4,0xFFC512
    bne.s   2f
    lea     door5_art,%a0
2:  cmpi.b  #5,0xFFC512
    bne.s   3f
    lea     door6_art,%a0
3:  rts

    .section .rodata
    .even
door2_art:
    .byte   1
    .space  0x6FF
door5_art:
    .byte   1
    .space  0x6FF
door6_art:
    .byte   1
    .space  0x6FF
    .section .text,"ax"

    .lcomm  se_save, 49
    .lcomm  se_hidden, 1
    .lcomm  se_slot0, 1

| $71AAE: `jsr spawn_once` over `moveq #0,d0 / move.b 13(a5),d0`, at each spawn
| record of the spawner ($71A62, a5 = the record, a6 = its block). The arcade
| ($EB08, for types 5, 6, 8, 10, 12 and 13, table $EAE8) lets a record with
| subtype bit 1 make its enemy once per life: a bit for its id less the
| stage's first id (<$72, $EB3C) in the record's slot, cleared at each life
| start; a second try removes the record. The port had no such test, so every
| Red Arremer of stage 6's tower came back each time the map position came
| round. The port's first state (+1 = 0) is the arcade's set-up, one call.
    .global spawn_once
spawn_once:
    moveq   #0,%d0
    move.b  13(%a5),%d0
    tst.b   1(%a5)
    bne.s   9f
    btst    #1,6(%a5)
    beq.s   9f
    cmpi.w  #14,%d0
    bcc.s   9f
    move.w  #0x3560,%d1
    btst    %d0,%d1
    beq.s   9f
    movem.l %d0/%a0,-(%sp)
    move.l  %a5,%d0
    sub.l   4(%a6),%d0
    move.l  %a5,-(%sp)
    move.l  %d0,-(%sp)
    jsr     spawn_seen
    addq.l  #8,%sp
    tst.l   %d0
    movem.l (%sp)+,%d0/%a0
    beq.s   9f
    clr.b   (%a5)
    clr.b   1(%a5)
    clr.b   2(%a5)
    addq.l  #4,%sp
    jmp     0x71CA6
9:  rts
