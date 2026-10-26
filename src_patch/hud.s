| The continue countdown as the arcade's: "CONTINUE PLAY ?" with the count
| on its own line below, two digits from 10 down to 01 (BCD <$0A from $10, a
| step per 64 frames, `$785D`; drawn at row 13, columns 15-16 under the text
| at row 9, column 10). The port counted 9 down to 0 (its 640-frame timer
| $FFC594 / 64, capped at 9) in one digit after the "?". $FFC596 keeps the
| count + '0' as before ($3A for 10). Hooks: tools/patch_gng.py.

    .section .text,"ax"
    .global cont_digit, cont_draw

| $630A (after `subq.w #1,$FFC594`): was d0 = min(timer / 64, 9) + '0'. Now
| timer / 64 + 1 + '0' (10 on the first 64 frames, 1 on the last); returns
| to $6322 (`move.w d0,$FFC596`).
cont_digit:
    moveq   #0,%d0
    move.w  0xFFC594,%d0
    lsr.w   #6,%d0
    addi.w  #0x31,%d0
    rts

| $11D260 (the continue text's draw, after its 15 cells at row 9, column 10
| of the plane at $E000): was the digit cell right after them. Now that
| cell is blank and the count goes to row 13, columns 15-16, two digits
| with the leading zero, red as the arcade's (the port's digit tiles $250 + n,
| drawn in their colour 15, with palette 2, whose colour 15 is red here).
cont_draw:
    move.w  #0,0xC00000
    move.l  #0x669E0003,0xC00004
    moveq   #0,%d0
    move.w  0xFFC596,%d0
    subi.w  #0x30,%d0
    divu.w  #10,%d0
    move.w  %d0,%d1
    addi.w  #0xC250,%d1
    move.w  %d1,0xC00000
    swap    %d0
    addi.w  #0xC250,%d0
    move.w  %d0,0xC00000
    rts

| A kill's score in the update of the hit, as the arcade's (its weapon-hit
| code adds it, `$EF17`). The port's enemies queue the score as a $0Cxx
| entry in the player's event queue ($FFB400) during the enemy pass, and
| every stage loop drains that queue ($4EE0 / $78C2) before the pass, so
| the score came an update late (stage 1, a lance at each zombie: hit on
| update 551, score on 552; the arcade's on the hit frame). Called by
| se_objpass/se_objpass2 (stageend.s) right after the pass's core: the score
| entries at the head of the queue go now ($7818, the game's own: it adds
| each and stops at the first other entry, which stays for the loop's
| drain), with their count added to $FFC04C as the drains do.
    .global score_now
score_now:
    movem.l %d0-%d7/%a0-%a6,-(%sp)
    lea     0xFFB400,%a4
    lea     0xFFC000,%a5
    lea     0x28F2E,%a0
    jsr     0x7818
    add.l   %d0,0xFFC04C
    movem.l (%sp)+,%d0-%d7/%a0-%a6
    rts

| One-frame presses on frames without an update. The arcade reads its pads
| every frame (60 updates a second); the port reads them once per update
| ($BF72 pad_update, p2.c read_pad2), and when an update takes longer than a
| frame (co-op runs 0.82-0.95 updates a frame) a press held only during the
| frame it skipped was never seen: a lost lance or jump. The VBlank handler
| (vector $78, was $113E56: count the frame) now also reads both pads while
| in play (dv_latch_on, set by pad_update) and ANDs the fire/jump bits into
| a latch (active low, so a press on any frame sticks); the update's read
| takes them in and clears the latch. The pad readers block interrupts
| while they read, so the two never interleave on the port.
    .global vb_isr, pad_latch_on, pad_lat
vb_isr:
    addq.l  #1,0xFF7DFC
    tst.b   pad_latch_on
    beq.s   9f
    movem.l %d0/%a0-%a1,-(%sp)
    lea     0xA10003,%a0
    lea     pad_lat,%a1
    bsr.s   1f
    lea     0xA10005,%a0
    bsr.s   1f
    movem.l (%sp)+,%d0/%a0-%a1
9:  rte
1:  move.b  #0x40,(%a0)
    nop
    nop
    nop
    nop
    move.b  (%a0),%d0                   | TH=1: C B R L D U
    ori.b   #0xCF,%d0
    and.b   %d0,(%a1)+
    move.b  #0x00,(%a0)
    nop
    nop
    nop
    nop
    move.b  (%a0),%d0                   | TH=0: S A 0 0 D U
    ori.b   #0xEF,%d0
    and.b   %d0,(%a1)+
    move.b  #0x40,(%a0)
    rts

    .lcomm  pad_latch_on, 1
    .lcomm  pad_lat, 4                  | pad 1 TH=1, TH=0, pad 2 TH=1, TH=0
