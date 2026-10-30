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
        if (t == 3 && RAM8(0xFFC512) == 2) t = 5;       /* a fire tower's shot */
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

/* Spawn records seen once a life (stageend.s spawn_once; arcade $EB08): 8
 * bytes of bits for each of the 16 records, as the arcade keeps them in the
 * record's own slot. */
static u8 once[16][8];
static const u8 once_base[7] = { 0, 14, 37, 69, 81, 96, 106 };  /* $EB3C */

void spawn_reset(void)
{
    int i, j;
    for (i = 0; i < 16; i++)
        for (j = 0; j < 8; j++) once[i][j] = 0;
}

int spawn_seen(long off, const u8 *rec)
{
    u8 st = RAM8(0xFFC512) & 7;
    u8 a = rec[3] - once_base[st > 6 ? 6 : st];
    u8 *b = &once[(off / 24) & 15][(a >> 3) & 7];
    u8 m = 0x80 >> (a & 7);
    if (*b & m) return 1;
    *b |= m;
    return 0;
}

/* $E18C / $E1B7: a fire tower's shot (arcade type 5, moved as its type 3: the port's
 * type 3, $ACB8, the Big Men's, drawn from tower_art by bm_shot_attr), 16 px above its y (top mouth) or
 * 7 below (low mouth), going left when Arthur is left of it (not at or right
 * of its x: the arcade's `-$2,Y`, the port's +24). */
static void tower_shot(const u8 *s, int dy)
{
    u16 *pool = (u16 *)0xFFC220;
    u8 *p, **sp;
    u16 x = s[0] << 8 | s[1], y = (s[2] << 8 | s[3]) + dy;
    sp = *(u8 ***)0xFFC228;
    p = *--sp;
    *(u8 ***)0xFFC228 = sp;
    pool[0]--;
    p[0] = x >> 8; p[1] = x;
    RAM32(p + 16) = (u32)x << 8 | p[19];
    p[2] = y >> 8; p[3] = y;
    RAM32(p + 20) = (u32)y << 8 | p[23];
    p[7] = 0; p[8] = 0; p[9] = 0;
    p[24] = (s16)x >= (s16)RAM16(0xFF9001) ? 1 : 0;
    p[4] = 1; p[5] = 0;
    p[10] = 3;
}

void pillar_shots(const u8 *s, long sub)
{
    if (sub != 3) tower_shot(s, -16);
    if (sub != 2) tower_shot(s, 7);
}
