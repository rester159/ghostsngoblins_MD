| In place at $114746 (178 bytes, linked there): the per-slot type chain of
| the 40-slot pass at $114704, taken for every live object with 5(a4) set.
| The type at 10(a4) went through up to 19 byte compares to a jsr site; the
| same mapping by table (15 and anything above 18 -> the assert at $114896).
| d2 is the scratch: every target is entered with d2 = 1 as before.
    .set    AT, 0x114746
base:
    moveq   #0,%d2
    move.b  10(%a4),%d2
    cmpi.w  #18,%d2
    bhi.w   9f
    add.w   %d2,%d2
    move.w  1f(%pc,%d2.w),%d2
    jmp     1f(%pc,%d2.w)
1:  .irp t, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18
    .word   s\t - 1b
    .endr
    .macro  stub t, at
s\t: moveq  #1,%d2
    bra.w   base + (\at - AT)
    .endm
    stub 0, 0x114838
    stub 1, 0x11485E
    stub 2, 0x114840
    stub 3, 0x114846
    stub 4, 0x11484E
    stub 5, 0x114856
    stub 6, 0x114816
    stub 7, 0x1148BA
    stub 8, 0x1148A6
    stub 9, 0x11481E
    stub 10, 0x114828
    stub 11, 0x114866
    stub 12, 0x1147F8
    stub 13, 0x11480E
    stub 14, 0x114800
s15:
9:  bra.w   base + (0x114896 - AT)
    stub 16, 0x114830
    stub 17, 0x114830
    stub 18, 0x114806
