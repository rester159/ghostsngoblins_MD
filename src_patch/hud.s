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
