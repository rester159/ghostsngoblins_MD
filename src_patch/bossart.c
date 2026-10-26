/* Arcade art the port lacked (converted by mkart.py into build/art.inc).
 *
 * The Satans (stages 5 and 6, type 6): the port had 2 poses (flying, wings
 * closed, each facing left or right) in tiles $500-$543 and the score in
 * $544-$54B, loaded once at the stage start ($1104FC). The arcade also has
 * the hovering pose with the wings open (3 poses, $4C6D) and the burst
 * before the score ($E8A7: 2x2 then 3x3, 4 poses), 9 pieces each: too much
 * to keep resident. So each Satan on screen gets a buffer of 9 pieces (36
 * tiles) in the Satan's own tiles ($500 and $524, two Satans at most: stage 6
 * has two, stage 5 one) and the pieces of its current pose are uploaded into
 * it when the pose changes, at the sprite-table DMA of the frame that shows
 * the new sprites (so tiles and sprites change together). The score frame
 * moves to tiles $6D0-$6D7 and the shot's star to $5F4-$5FB, both unused in
 * stages 5 and 6 (docs/ACCURACY.md has the survey).
 *
 * The shot (the port's type-6 shot, its orb) is drawn as the arcade's star
 * (sprites $1D7/$1DF, 4 frames each from the shot's first frame) when a
 * Satan fired it (satan_fire tags the shot slot). */
#include "md.h"
typedef signed char s8;
#include "build/art.inc"

void dma_vram(u32 src, u16 bytes, u16 vram);

#define SAT_BUF0  0x500
#define SAT_BUF1  0x524
#define SCORE_T   0x6D0         /* the port's score frame (its tiles $544-$54B) */
#define STAR_T    0x5F4
#define SCORE_SRC 0x255B74      /* the port's ROM copy of tiles $544-$54B */

static u8 *sb_owner[2];         /* the Satan slot each buffer is drawn for */
static u16 sb_want[2];          /* art offset + 1 of the pose last drawn (0 none) */
static u16 sb_have[2];          /* ... and of what the buffer holds (0 unknown) */
static u8 sb_nart[2];
u8 star_tag[6];                 /* shot slots $FFC100 + 48n fired by a Satan */
u8 star_t0[6];                  /* ... the update counter ($FFA206) at the shot */

static int stage_has_satans(void)
{
    u8 st = RAM8(0xFFC512);
    return st == 4 || st == 5;
}

static void vram_copy(const u16 *src, u16 words, u16 tile)
{
    VDP_CTRLL = VRAM_W((u32)tile * 32);
    while (words--) VDP_DATA = *src++;
}

/* $1104FC (every stage init that loads the Satan's art): after the port's
 * load, the buffers hold nothing known; in stages 5 and 6 the score and the
 * star go to their tiles. */
void sat_art_init(void)
{
    int b;
    sb_owner[0] = sb_owner[1] = 0;
    sb_want[0] = sb_want[1] = 0;
    sb_have[0] = sb_have[1] = 0;
    for (b = 0; b < 6; b++) star_tag[b] = 0;
    if (stage_has_satans()) {
        vram_copy((const u16 *)SCORE_SRC, 8 * 16, SCORE_T);
        vram_copy(star_art, 8 * 16, STAR_T);
    }
}

/* hook_sat_dma: the uploads for the sprites about to be shown */
void sat_vblank(void)
{
    int b;
    for (b = 0; b < 2; b++) {
        if (sb_want[b] && sb_want[b] != sb_have[b]) {
            dma_vram((u32)(sat_art + sb_want[b] - 1), (u16)sb_nart[b] * 128, (b ? SAT_BUF1 : SAT_BUF0) * 32);
            sb_have[b] = sb_want[b];
        }
    }
}

static int buffer_for(u8 *p)
{
    int b;
    u8 *q;
    for (b = 0; b < 2; b++)
        if (sb_owner[b] == p) return b;
    for (b = 0; b < 2; b++) {
        q = sb_owner[b];
        if (!q || !q[4] || q[10] != 6) { sb_owner[b] = p; return b; }
    }
    return -1;
}

typedef struct { u8 *sat; u16 link, left, drawn, dropped; } Spr;

/* one 16x16 sprite, as the port's builds write them ($1108B8) */
static void put(Spr *o, const u8 *p, const u16 *cam, s16 dx, s16 dy, u16 attr)
{
    u16 x = dx + RAM16((u32)p) - cam[0] + 15;
    u16 y = 239 + dy + RAM16(0xFF9102) - RAM16((u32)p + 2);
    u8 *s;
    if (x > 270 || y > 238) return;
    if (!o->left) { o->dropped++; return; }
    s = o->sat;
    if (o->link) s[-5] = o->link;
    ((u16 *)s)[0] = y + 113;
    ((u16 *)s)[1] = 0x0500;
    ((u16 *)s)[2] = attr;
    ((u16 *)s)[3] = x + 113;
    o->sat = s + 8;
    o->link++; o->drawn++; o->left--;
}

/* $11086A: the Satan's draw (a4 = the slot, a3 = the camera), from
 * sat_draw_hook */
void sat_draw(u8 *p, const u16 *cam, Spr *o)
{
    u16 f = (u16)(p[30] << 8 | p[31]), base;
    const SatFrame *fr;
    int b, k;
    if (f >= SAT_NFRAMES) f = 0;
    fr = &sat_frames[f];
    if (fr->art == 0xFFFF) {                    /* the score, as the port's frame 5 */
        put(o, p, cam, -16, 8, SCORE_T);
        put(o, p, cam, 0, 8, SCORE_T + 4);
        return;
    }
    if (!fr->npc) return;
    b = buffer_for(p);
    if (b < 0) return;
    sb_want[b] = fr->art + 1;
    sb_nart[b] = fr->nart;
    base = b ? SAT_BUF1 : SAT_BUF0;
    for (k = 0; k < fr->npc; k++) {
        const SatPiece *c = &fr->pc[k];
        put(o, p, cam, c->dx, c->dy, (base + c->slot * 4) | (u16)c->flip << 8);
    }
}

/* the burst ($E8A7 for size class 4) by the port's burst count (+9, 1-22,
 * hook_satan_die): 0 = the pose stays */
const u8 sat_burst[23] = {
    0, 0, 0, 0, 12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 13, 13, 13, 13, 14, 14, 14, 14 };

/* the star's frames for the shot draw ($117238: count, then dx, dy, attr) */
const s16 star_frames[2][4] = { { 1, -8, 8, STAR_T }, { 1, -8, 8, STAR_T + 4 } };
