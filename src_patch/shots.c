/* Arthur's weapons against enemy shots, as the arcade's $F3CE (called on odd
 * frames before Arthur's own shot check, $EF24). The port had no such check:
 * the cross could not stop a shot and nothing knocked out a weapon on one.
 *
 * Per weapon (<$73 = $FFA218: 0 torch, 1 lance, 2 axe, 3 cross, 4 knife) and
 * shot type, a count ($F452, 12 bytes a weapon): 0 the weapon passes, 1 the
 * weapon is used up, 2 both go. Each live shot is tested against the four
 * weapon slots with the shot type's box ($F498, 8 bytes a type); the count
 * runs down over the slots the shot touches, as in the arcade.
 * Port shots: $FFC100, 6 x 48 (+4/+5 live, +$A type, x/y 16.8 at +$10/+$14).
 * Port weapons: $FF9600, 4 x 32 (x/y 16.8 at +0/+4, +8/+9 live). */
#include "common.h"

/* $F452..$F491: read flat, as the arcade indexes it (weapon * 12 + type). */
static const u8 count_tab[64] = {
    0,0,0,0,0,1,0,0,0,0,0,0,  0,0,0,0,0,1,0,0,0,0,0,0,
    0,0,0,0,0,1,0,0,0,0,0,0,  0,2,2,2,2,2,2,2,2,2,0,2,
    0,0,0,0,0,1,0,0,0,0,0,0,  0xF4,0x98,0xF4,0x98,
};
/* $F498: x offset, x range, y offset, y range per shot type. */
static const u16 box_tab[16][4] = {
    {12,24,8,16}, {12,24,8,16}, {12,24,8,16}, {12,24,8,16},
    {12,24,8,16}, {12,24,13,24}, {16,32,16,32}, {12,24,13,26},
    {16,32,16,32}, {12,24,12,24}, {5,10,5,10}, {12,24,12,24},
    {12,24,8,16}, {10,20,8,16}, {12,24,8,16}, {12,24,8,16},
};

void weapon_vs_shots(void)
{
    u8 w = RAM8(0xFFA218);
    if (w > 4) return;
    for (int s = 0; s < 6; s++) {
        volatile u8 *p = (volatile u8 *)(0xFFC100 + 48 * s);
        if (!(p[4] & p[5])) continue;
        u8 t = p[10] & 15;
        u8 n = count_tab[w * 12 + t];
        if (!n) continue;
        const u16 *b = box_tab[t];
        u16 px = RAM32((u32)p + 0x10) >> 8, py = RAM32((u32)p + 0x14) >> 8;
        for (int k = 0; k < 4; k++) {
            volatile u8 *q = (volatile u8 *)(0xFF9600 + 32 * k);
            if (!(q[8] & q[9])) continue;
            if ((u16)(px - (u16)(RAM32((u32)q) >> 8) + b[0]) > b[1]) continue;
            if ((u16)(py - (u16)(RAM32((u32)q + 4) >> 8) + b[2]) > b[3]) continue;
            if (--n) {                      /* the shot goes ($5A20) */
                p[4] <<= 1; p[7] = 2; p[8] = 0; p[9] = 0;
            }
            q[8] <<= 1; q[0x1E] = 0;        /* the weapon goes ($BF14) */
            q[0xC] = 2; q[0xD] = 1;
        }
    }
}
