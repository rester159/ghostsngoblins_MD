| The enemy slots' leftover x/y fractions at a stage or life start.
|
| The arcade's stage/life start ($6DA5) clears only each slot's flags, states
| and type (-$10..-$B, +5) and its initial spawns write only the x and y
| high:pixel bytes, so every slot keeps the x and y fractions (-$8, -$5) of
| whatever was in it before: after a death in the stage 1 Red Arremer's
| fight its new Arremer starts at x 1472.98 (the old one's .98), and stage
| 6's second Satan at 7696.06. The port's seven stage inits ($9180, $98FE,
| $104E90, $10F1D4, $110172, $111128, $111A82) copy a prebuilt image of all
| 40 slots from ROM over $FFB800 (fractions .00).
|
| `jsr slot_copy` + 2 nops over `move.w #479,d0 / move.l (a0)+,(a1)+ /
| dbf d0,*-2`: the same copy, keeping bytes +19 and +23 (the x and y
| fractions of the 16.8 longs at +16 and +20) of every slot. a0/a1 end as the
| loop leaves them (+1920), d0.w = -1.
    .global slot_copy
slot_copy:
    movem.l %d0-%d3,-(%sp)
    moveq   #39,%d1
1:  move.b  19(%a1),%d2
    move.b  23(%a1),%d3
    moveq   #11,%d0
2:  move.l  (%a0)+,(%a1)+
    dbf     %d0,2b
    move.b  %d2,19-48(%a1)
    move.b  %d3,23-48(%a1)
    dbf     %d1,1b
    movem.l (%sp)+,%d0-%d3
    move.w  #-1,%d0
    rts
