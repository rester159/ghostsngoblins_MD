| Stage 4's fire pillars (type 14): the size class at a step of the count.
|
| Arcade $DE65-$DE89: when the 32-frame count (`$C,X`) runs out the pillar's
| animation restarts at $54FB with `LDU #$54FB / LDB ,U / STU $8,X / JSR $8EBF`:
| the first entry's size class (1) is set on the step frame, and the pointer
| isn't advanced, so the same entry is read again when the 2-frame timer
| (`$2,X` = 2) runs out. The port's step ($10F7C4) set the animation index
| (word $248BAA) and the 2-frame timer only, so its first size change came with
| that second read, 2 frames late: seen when a step cuts into an animation
| that isn't at class 1 (once a cycle of the count sequence; Fixed 50).
|
| $10F7C4: `jsr pillar_step` + 7 nops over the step's four moves (a4 = slot).
    .text
    .global pillar_step
pillar_step:
    move.w  0x248BAA,%d0            | the restart's animation index
    move.w  %d0,28(%a4)
    move.w  %d0,30(%a4)
    move.b  #2,26(%a4)              | $2,X = 2
    lsl.w   #3,%d0
    lea     0x248AB0,%a1
    moveq   #0,%d1
    move.b  5(%a1,%d0.w),%d1        | that entry's size class (= $54FB's, 1)
    jmp     0x10F816                | size_shift: y and class as $8EBF (rts to the caller)
