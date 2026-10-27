| Arthur's frame timing as the arcade's and the stage 1 boss (docs/ACCURACY.md,
| Fixed 23-26, 28, 29; the rank creep, 27, is in glue.s). Hooks: tools/patch_gng.py.

    .section .text,"ax"

| Flags in unused bytes of the player control block $FF9440 (+17, +21;
| cleared with it by $7FA4), which Maximo's context swap covers. WALK_FLAGS:
| bit 0 the stand-up frame, bit 1 the crouch-entry frame, bit 2 a jump's
| wind-up (pad.c arcade_input, ground_snap below).
    .set    WALK_FLAGS, 0xFF9455
    .set    EXACT_FLOOR, 0xFF9451

| $7F98: `jmp stand_up` + 3 nops over `move.b #7,12(a4)` / `clr.b 11(a4)` /
| `rts`: the end of a crouch (the stand-up countdown at $FF944C ran out,
| $7F36). The arcade's crouch handler ($91B4, stand-up at $9A6C: `$0520` back
| to 7, crouch flag `$050F` cleared) returns without the walk, so the
| stand-up frame doesn't move and the walk starts on the next one. The port
| cleared the crouch flag and then walked in the same update (its walk gate
| $8114 runs after $7FC4). Flag it for walk_gate.
    .global stand_up, crouch_in
stand_up:
    move.b  #7,12(%a4)
    clr.b   11(%a4)
    bset    #0,WALK_FLAGS
    rts
| $7E56: `jsr crouch_in` over `move.b #1,11(a4)` (crouch entry, $7E50). The
| arcade's standing handler sets the crouch flag ($9305) and still walks in
| the same frame ($940E/$947D): with right and down pressed together it
| steps 1.125 px on the frame it crouches; the port's walk gate saw the new
| crouch flag and didn't.
crouch_in:
    move.b  #1,11(%a4)
    bset    #1,WALK_FLAGS
    rts

| $8114: `jmp walk_gate` over the walk gate (d0 = the walk direction from the
| stick, returned as is, or 0 for no walk: on a ladder $FF9459, crouching
| $FF944B, or neither on the ground nor jumping). Same tests, plus: no walk on
| the stand-up frame, and the crouch-entry frame still walks (flags above).
| Every stage loop and Maximo's control block call $7FC4 then $8114 in the
| same sequence, so the flags never outlive the update they were set in.
    .global walk_gate
walk_gate:
    bclr    #0,WALK_FLAGS
    bne.s   1f
    tst.b   0xFF9459
    bne.s   1f
    bclr    #1,WALK_FLAGS
    bne.s   2f
    tst.b   0xFF944B
    bne.s   1f
2:  tst.w   0xFF9408
    bne.s   3f
    tst.w   0xFF9410
    bne.s   3f
1:  moveq   #0,%d0
3:  bclr    #1,WALK_FLAGS
    rts

| $7E42: `jsr lad_exit` + 2 nops over `clr.b 8(a4)` / `cmpi.b #4,9(a4)` in the
| down handler ($7DFE), taken when there's no ladder under him: on a ladder
| (+8 set), that's the bottom. The arcade's ladder handler then hands over to
| the standing state, whose floor check ($8CA7) finds no floor under y 64.9:
| it goes to the fall state ($91E1, $0504 = 1) with y unchanged, and the next
| frame falls the usual 4.25 ($9660) and lands at 62.65 ($91F1). The port's
| ground step ($868E) snapped him down to the floor (up to 8 px, $8744) in the
| same update. Flag the bottom for ground_snap; the cmpi's flags are returned.
    .global lad_exit
lad_exit:
    tst.b   8(%a4)
    beq.s   1f
    st      EXACT_FLOOR
1:  clr.b   8(%a4)
    cmpi.b  #4,9(%a4)
    rts

| $8698: `jsr ground_snap` over `bsr $8744` / `tst.l d0` in the ground step
| (d0 = 0: no floor within reach; the port's own code then makes him airborne
| at $86A2 with y unchanged, and its fall at $86AC, y - 4.25 and a landing
| with the fraction kept, runs the next update). On the ladder-bottom update
| and on the first ground step of a stage start (stage_hold_entry in glue.s
| sets the flag: the arcade's $6D36 and the port's start both place him at
| y 64, 2 px above the ground) only the floor at his own y counts ($8784, the
| first probe of $8744), as in the arcade's standing check, so he falls like
| the arcade's instead of snapping down. Stage start, right held, arcade:
| walk at y 64.28, then land at 62.03 without walking; the port walked and
| snapped in the same update.
| Every other ground step too (docs/ACCURACY.md, Fixed 67): the floor at his
| own y, then the objects ($84B8, $8744's last step), but not $8744's second
| probe 8 px down, which snapped him down onto a lower floor in the walk. The
| arcade's walk ($91D1) has no such probe: no floor at $8CA7 and no object at
| y - 1 ($9674/$9FAE) starts its fall state ($91F2), which doesn't walk, so a
| floor one pixel lower costs a frame standing (stage 5 room, x 7048: y 1615
| -> 1614).
| Also (docs/ACCURACY.md, Fixed 66): during a jump's wind-up (pad.c
| arcade_input sets WALK_FLAGS bit 2 on the press frame and the frame between,
| the walk and stand-still frames before the take-off) he stays on his floor.
| The arcade's press frame walks and then takes the jump set-up branch ($9218),
| which has no floor check, and the next frame ($9542) neither: a jump pressed
| on the step that carries him past a ledge's edge still takes off from it
| (stage 2, the ice ledge ending at x 3880.5: walk/stand at 142.80, then up).
| The port's ground step ($868E) made him airborne on the press frame, and the
| take-off ($B484) needs the ground: he fell instead.
| $9DFC (stage 2's elevators and stepping stones, types 3/4), $10F602,
| $11A432, $11A650 (the other movers): the platform carry of Arthur, skipped while he
| jumps: `jsr carry_gate` over `tst.w $FF9410`; also skipped in a jump's
| wind-up, as the arcade's jump set-up isn't carried (stage 2's elevator:
| pressed on it at y 194.1D, the arcade takes off from 194.1D, the port from
| 192.41 after two frames of carry). Z clear = no carry.
    .global carry_gate
carry_gate:
    tst.w   0xFF9410
    bne.s   1f
    btst    #2,WALK_FLAGS
1:  rts

    .global ground_snap
ground_snap:
    btst    #2,WALK_FLAGS
    beq.s   2f
    moveq   #0,%d1                  | a floor right at his feet: y unchanged
    moveq   #1,%d0
    rts
2:  tst.b   EXACT_FLOOR
    bne.s   1f
    jsr     0x8784                  | the floor at his own y (as $8744's first probe)
    tst.l   %d0
    bne.s   3f
    jsr     0x84B8                  | the objects ($8744's last step)
    tst.l   %d0
3:  rts
1:  clr.b   EXACT_FLOOR
    jsr     0x8784
    tst.l   %d0
    rts

| Armor (`$FFC328`, +40 of the physics block $FFC300): the arcade sets its
| armor flag `$0158` on the hit frame; the port set it when the knockback
| landed ($5CD4), 33 updates later, because its knockback state machine used
| it as "this is an armored hit": the dispatcher $5A9A picks the knockback
| ($5F70 start, $5AD8 later frames) while it's 0 and the boxers hit/death
| ($5E60) while it's 1. Everything else that reads it during those 33
| updates (item pickups and the copies of it in the item and object
| contexts, $116472 / $9B7E etc.) saw armor the arcade had already lost. Now
| the hit sets it at once, and a separate marker KB_ARMOR (+67, unused,
| cleared by the block init $6456, in Maximo's swap) keeps the knockback on
| the armored path until it lands.
    .set    KB_ARMOR, 67
| $5FA4: `jsr kb_hit` over `move.b #120,9(a4)` (the armored hit: 120 frames
| of invincibility, then the armor pieces).
    .global kb_hit, kb_dispatch, kb_anim, kb_land
kb_hit:
    move.b  #120,9(%a4)
    move.b  #1,40(%a4)
    move.b  #1,KB_ARMOR(%a4)
    rts
| $5AAE: `jmp kb_dispatch` over `tst.b 40(a4)` / `bne.s $5AC8`: the armored
| path ($5AB4) while the marker is set or the armor is on, else $5AC8.
kb_dispatch:
    tst.b   KB_ARMOR(%a4)
    bne.s   1f
    tst.b   40(%a4)
    bne.s   2f
1:  jmp     0x5AB4
2:  jmp     0x5AC8
| $5B44: `jsr kb_anim` + nop over `tst.b 40(a4)` / `beq.s` / `addq.w #6,d0`:
| the knockback/death animation pick (shared by both paths): +6 for the
| boxers death only, as before (the armored knockback had +40 = 0 here).
kb_anim:
    tst.b   KB_ARMOR(%a4)
    bne.s   1f
    tst.b   40(%a4)
    beq.s   1f
    addq.w  #6,%d0
1:  rts
| $5CD4: `jsr kb_land` over `move.b #1,40(a4)` (the knockback landing).
| $5ADC (the armored path's check that +40 is 0) tests the marker instead.
kb_land:
    move.b  #1,40(%a4)
    clr.b   KB_ARMOR(%a4)
    rts

| rank_creep (glue.s): the fraction of the working rank, the counter at the
| last update and the VBlank count then. Last in .bss so the earlier
| variables (menu_frames at $FF5137, ...) keep their addresses.
    .global rank_frac, rank_prev, rank_vbl
    .lcomm  rank_vbl, 4
    .lcomm  rank_frac, 1
    .lcomm  rank_prev, 1

| Stage 1's terrain map ($FF0000: 32 columns of 16 px, a ring) holds the
| columns cam/16 - 8 .. cam/16 + 23 in the port ($93D6 full fill, $944A one
| column per step) and cam/16 - 15 .. cam/16 + 16 in the arcade (bg RAM
| $2800, a column written as the camera reaches it). The ring columns ahead
| of the screen therefore held the real level in the port and the level 512
| px back in the arcade. At the boss arena the camera stops at 3234, so the
| arcade never loads x 3504 on and the unicorn lands on the old terrain at
| x + 24 (its second floor probe, $8CA7 class 4); the port's map had the end
| wall there and the unicorn fell 8 px further to the arena floor.
| $93E0 / $9454: `jsr map_start_d6` / `jsr map_start_d0` + nop over
| `lsr.w #4` / `subq.w #8` / `bpl.s` / `moveq #0` (the clamp to 192 after
| them stays).
    .global map_start_d6, map_start_d0
map_start_d6:
    lsr.w   #4,%d6
    subi.w  #15,%d6
    bpl.s   1f
    moveq   #0,%d6
1:  rts
map_start_d0:
    lsr.w   #4,%d0
    subi.w  #15,%d0
    bpl.s   1f
    moveq   #0,%d0
1:  rts
