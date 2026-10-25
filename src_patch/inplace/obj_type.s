| In place at $69DA (136 bytes, the per-object type chain of $69A2): the
| object type at 10(a4) picked an index into d4 through up to 14 compares
| (11->0 16->1 17->2 1->3 5->4 3->5 0->6 8->7 7->8 10->9 2->13 4->12 14->14,
| anything else -> the assert at $6C96 with d4 = 14). Same mapping by table.
| d0 is free here: $114C90 reloads it and $6C96 doesn't return.
    moveq   #0,%d0
    move.b  10(%a4),%d0
    cmpi.w  #18,%d0
    bcc.s   1f
    moveq   #0,%d4
    move.b  2f(%pc,%d0.w),%d4
    bmi.s   1f
    jmp     0x114C90
1:  moveq   #14,%d4
    jmp     0x6C96
2:  .byte   6, 3, 13, 5, 12, 4, -1, 8, 7, -1, 9, 0, -1, -1, 14, -1, 1, 2
    .even
