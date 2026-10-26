| In place at $B2B4 (124 bytes, linked there): the type chain of the stage
| 1-2 sprite build's slot loop ($B258), taken for every live slot on the
| screen. The type at 10(a4) went through up to 12 byte compares to a jsr
| site; the same mapping by table (6, 9, 12-15 and anything above 17 -> the
| fault at $B3A4). The type-10 call that sat at the chain's end ($B32A) is
| here now. d3 is the scratch: every draw routine writes it before reading.
    .set    AT, 0xB2B4
base:
    moveq   #0,%d3
    move.b  10(%a4),%d3
    cmpi.w  #17,%d3
    bhi.w   base + (0xB3A4 - AT)
    add.w   %d3,%d3
    move.w  1f(%pc,%d3.w),%d3
    jmp     1f(%pc,%d3.w)
1:  .word   s0 - 1b, s1 - 1b, s2 - 1b, s3 - 1b, s4 - 1b, s5 - 1b, sx - 1b, s7 - 1b, s8 - 1b
    .word   sx - 1b, s10 - 1b, s11 - 1b, sx - 1b, sx - 1b, sx - 1b, sx - 1b, s16 - 1b, s16 - 1b
    .macro  stub n, at
s\n: bra.w  base + (\at - AT)
    .endm
    stub 0, 0xB336
    stub 1, 0xB360
    stub 2, 0xB34E
    stub 3, 0xB33E
    stub 4, 0xB358
    stub 5, 0xB346
    stub 7, 0xB3C8
    stub 8, 0xB3B4
    stub 11, 0xB366
    stub 16, 0xB330
    stub x, 0xB3A4
s10: jsr    0xAF1E
    bra.w   base + (0xB36A - AT)
