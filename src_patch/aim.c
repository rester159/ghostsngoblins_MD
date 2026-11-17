/* Home's ATTACK: 4-WAY (OPTIONS). Arthur throws the lance straight up while
 * Up is held, and straight down while Down is held in a jump; otherwise as
 * the game throws it. Arthur only: not Maximo (player 2), Firebrand or the
 * Vendetta; the lance only (the other weapons keep their own flights).
 *
 * The game's throw ($BA4A -> $115DFC) allocates a weapon slot ($FF9600, 32
 * bytes each: x, y 16.8 at +0, +4 (y counts up the screen, Arthur's y is his
 * feet), +8 allocated, +9 on screen, +10 direction 1 right / 2 left, +11
 * weapon, +12 state (0 new, 1 flying, 2 hit), +13 sub-state, +16 start x).
 * glue.s hook_throw calls aim_pre / aim_post around it: a slot that became
 * allocated is Arthur's new lance, and Up or Down sets its aim and moves it
 * above his head or under his feet. The weapon pass ($1158D0) moves a lance
 * along x only (table $293D9C: 1072 / 256 px a frame) and ends it 192 px
 * from its start x (+16); aim_move (after the pass, stageend.s se_wmove)
 * puts x back and moves y that much instead, ends it after 192 px itself,
 * and a downward lance stops at the ground Arthur jumped from, with the hit
 * spark a tombstone gives ($BF14). Its hits are the game's, from x and y.
 *
 * Drawn: the game uploads the lance's art for a slot when its frame changes
 * ($11711E, frames 8 and 9 at $295000/$295200: two 16 x 16 pieces, 8 tiles)
 * and builds it as two pieces side by side. An aimed lance gets the art
 * turned on its end (made once from $295000 into RAM), and aim_sat stacks
 * its two pieces on the centre of the pair the game built.
 *
 * RAM: $FF4400-$FF46FF, in the range the game never touches ($FF2BE1-
 * $FF6FFF; Vendetta's buffers are $FF4000-$FF43FF). Not cleared at power-on,
 * so a magic word guards it. */
#include "common.h"

#define ART_UP   ((volatile u8 *)0xFF4400)  /* 256 bytes: tip up, pieces top, bottom */
#define ART_DOWN ((volatile u8 *)0xFF4500)  /* 256 bytes: tip down */
typedef struct {
    u16 magic;
    u8  dir[3];         /* each weapon slot's aim: 0 none, 1 up, 2 down */
    u8  art[3];         /* the aim of the art last uploaded to the slot */
    u8  was[3];         /* allocated before the throw */
    u8  in_p2;          /* p2.c: Maximo's control block is running */
    u8  art_ok;
    u8  pad;
    u32 x0[3];          /* an aimed lance's x (16.8), held */
    u16 went[3];        /* px travelled */
    u16 ground;         /* Arthur's y the last time he stood */
} Aim;
#define AIM      ((volatile Aim *)0xFF4600)
#define AIM_MAGIC 0x4157

#define SLOT(k)   ((volatile u8 *)(0xFF9600 + 32 * (k)))
#define P1        RAM8(0xFF7001)        /* active low: bit 3 up, bit 2 down */
#define JUMPING   RAM16(0xFF9410)       /* 0 on the ground, 1 rising, 2 falling */
#define ARTHUR_X  RAM32(0xFF9000)       /* 16.8 */
#define ARTHUR_Y  RAM32(0xFF9400)       /* 16.8, his feet */
#define FACING    RAM16(0xFF920A)       /* 0 right, $800 left */
#define LANCE     1
#define SPEED     1072                  /* the lance's x step ($293D9C), 16.8 */
#define RANGE     192                   /* the lance's range ($293DC4) */
#define LANCE_ART 0x295000UL
#define LANDED    0xFFFF                /* went: a downward lance's tip is on the ground */

int fb_on(void);
u32 fb_shot_src(u32 src);

static volatile Aim *aim(void)
{
    volatile Aim *a = AIM;
    if (a->magic != AIM_MAGIC) {
        volatile u8 *p = (volatile u8 *)a;
        for (u16 i = 0; i < sizeof(Aim); i++) p[i] = 0;
        a->magic = AIM_MAGIC;
    }
    return a;
}

static int four_way(void)
{
    return is_home() && PERSIST->home[HOP_ATTACK] == HOME_ATTACK_4WAY && !fb_on() && !G_ATTRACT;
}

/* the lance turned on its end: $295000 is two 16 x 16 pieces (tiles in
 * column order) side by side, tip at the left, shaft on rows 10-15. Up: the
 * tip on top, the shaft on columns 6-11; down: the tip at the bottom. */
static void make_art(void)
{
    const u8 *src = (const u8 *)LANCE_ART;
    for (u16 i = 0; i < 256; i++) ART_UP[i] = ART_DOWN[i] = 0;
    for (u16 y = 10; y < 16; y++) {
        for (u16 x = 0; x < 32; x++) {
            u16 t = (x >> 4) * 4 + ((x >> 3) & 1) * 2 + (y >> 3);
            u8 b = src[t * 32 + (y & 7) * 4 + ((x & 7) >> 1)];
            u8 c = x & 1 ? b & 15 : b >> 4;
            if (!c) continue;
            u16 nx = y - 4;
            for (int d = 0; d < 2; d++) {
                u16 ny = d ? 31 - x : x;
                volatile u8 *dst = d ? ART_DOWN : ART_UP;
                u16 o = ((ny >> 4) * 4 + ((nx >> 3) & 1) * 2 + ((ny >> 3) & 1)) * 32
                      + (ny & 7) * 4 + ((nx & 7) >> 1);
                dst[o] |= nx & 1 ? c : c << 4;
            }
        }
    }
    aim()->art_ok = 1;
}

void aim_pre(void)
{
    volatile Aim *a = aim();
    for (int k = 0; k < 3; k++) a->was[k] = SLOT(k)[8];
}

void aim_post(void)
{
    volatile Aim *a = aim();
    for (int k = 0; k < 3; k++) {
        volatile u8 *q = SLOT(k);
        u8 d = 0;
        if (!q[8] || a->was[k]) continue;
        if (!a->in_p2 && q[11] == LANCE && four_way()) {
            u8 in = ~P1;
            if ((in & 0x0C) == 0x08) d = 1;
            else if ((in & 0x0C) == 0x04 && JUMPING) d = 2;
        }
        a->dir[k] = d;
        if (d != a->art[k]) RAM16(0xFF9730 + 2 * k) = 0xFFFF;  /* upload its art again */
        if (!d) continue;
        if (!a->art_ok) make_art();
        /* the pair the game draws is centred on x and 11 px above y; Arthur's
         * sprite on his x, its top 32 px above his feet. The shaft goes on his
         * front hand, the lance just above his head or under his feet. */
        u16 x = (u16)(ARTHUR_X >> 8) + (FACING ? -4 : 4);
        u16 y = (u16)(ARTHUR_Y >> 8) + (d == 1 ? 25 : -15);
        a->x0[k] = (RAM32((u32)q) & 0xFF0000FFUL) | (u32)x << 8;
        RAM32((u32)q) = a->x0[k];
        RAM32((u32)q + 4) = (RAM32((u32)q + 4) & 0xFF0000FFUL) | (u32)y << 8;
        a->went[k] = 0;
    }
}

/* after the weapon pass (stageend.s se_wmove) */
void aim_move(void)
{
    volatile Aim *a = aim();
    if (!JUMPING) a->ground = (u16)(ARTHUR_Y >> 8);
    for (int k = 0; k < 3; k++) {
        volatile u8 *q = SLOT(k);
        if (!a->dir[k]) continue;
        if (!q[8] || q[11] != LANCE) { a->dir[k] = 0; continue; }
        if (q[12] != 1 || q[13]) continue;              /* not flying */
        RAM32((u32)q) = a->x0[k];
        u32 y = RAM32((u32)q + 4) & 0xFFFFFF;
        if (a->went[k] == LANDED) {
            /* its tip in the ground for an update, hit-tested there (the hits
             * come before the pass); now the spark, on the ground */
            y = (u32)(u16)(a->ground - 7) << 8;
            q[8] <<= 1; q[0x1E] = 0; q[12] = 2; q[13] = 1;
        } else {
            y = a->dir[k] == 1 ? y + SPEED : y - SPEED;
            a->went[k] += SPEED;
            if (a->dir[k] == 2 && (u16)(y >> 8) <= a->ground + 5) {
                y = (u32)(u16)(a->ground + 5) << 8;     /* the tip (5 px under y) on the ground */
                a->went[k] = LANDED;
            } else if (a->went[k] >= RANGE << 8) {
                q[13] = 1;                              /* the end of its range, as the pass ends it */
            }
        }
        RAM32((u32)q + 4) = (RAM32((u32)q + 4) & 0xFF000000UL) | (y & 0xFFFFFF);
    }
}

/* $11711E: a slot's art upload (a0 = src, d3 = slot * 2) */
u32 aim_shot_src(u32 src, u16 d3)
{
    src = fb_shot_src(src);
    u16 k = d3 >> 1;
    if (k > 2 || AIM->magic != AIM_MAGIC) return src;
    volatile Aim *a = AIM;
    u8 d = 0;
    if (src == LANCE_ART || src == LANCE_ART + 0x200) {
        if (a->dir[k] && four_way()) d = a->dir[k];
        a->art[k] = d;
    }
    return d == 1 ? 0xFF4400UL : d == 2 ? 0xFF4500UL : src;
}

/* at the sprite-table DMA (p2.c p2_sat): an aimed lance's two pieces, stacked */
void aim_sat(volatile u16 *buf, u16 n)
{
    static const u16 tile[3] = { 0x2A0, 0x2B0, 0x790 };
    if (AIM->magic != AIM_MAGIC) return;
    volatile Aim *a = AIM;
    if (RAM8(0xFFC8D6) == 2) {                          /* the stage end takes the slots */
        a->dir[0] = a->dir[1] = a->dir[2] = 0;
        return;
    }
    for (int k = 0; k < 3; k++) {
        volatile u8 *q = SLOT(k);
        if (!a->dir[k] || a->art[k] != a->dir[k] || q[8] != 1 || q[12] != 1) continue;
        volatile u16 *e0 = 0, *e1 = 0, *e = buf, *end = buf + n * 4;
        for (; e < end; e += 4) {
            if ((e[2] & 0x7FB) != tile[k]) continue;
            if (e[2] & 4) e1 = e; else e0 = e;
        }
        if (!e0 || !e1) continue;
        u16 cx = (e0[3] < e1[3] ? e0[3] : e1[3]) + 16, cy = e0[0] + 13;
        e0[0] = cy - 16; e1[0] = cy;
        e0[3] = e1[3] = cx - 8;
        e0[2] &= ~0x1800; e1[2] &= ~0x1800;
    }
}

void aim_p2(int on) { if (PERSIST->home[HOP_ATTACK]) aim()->in_p2 = on; }

/* a new game (settings.c player_init): no aims; a slot whose last upload
 * was the lance on its end gets the game's art again (the hooks above don't
 * run while ATTACK is NORMAL) */
void aim_reset(void)
{
    volatile Aim *a = AIM;
    if (a->magic != AIM_MAGIC) return;
    for (int k = 0; k < 3; k++) {
        a->dir[k] = 0;
        if (a->art[k]) RAM16(0xFF9730 + 2 * k) = 0xFFFF;
        a->art[k] = 0;
    }
    a->in_p2 = 0;
}
