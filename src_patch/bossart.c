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
#include "build/intro_waits.inc"     /* intro_waits[], ISC_FRAMES */

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

/* ---- stage 2's windows -------------------------------------------------
 * The arcade's devils open and close their window by writing bg tiles
 * ($B457: 4 steps of 5 frames, at the devil's x - 16 .. + 15 and its tile
 * row and the one above). Here the same poses go onto plane B ($C000, 64 x 32
 * cells; a window at world x X, y Y is at column ((X >> 4) - 1) * 2, row
 * 30 - 2 * (Y >> 4), 4 x 4 cells), from two 16-tile slots ($6AC-$6BB and
 * $6BC-$6C7 + $5F4-$5F7, unused in stage 2; $6A4-$6C7 is the second
 * Unicorn's art slot, $71DF0, only at the stage's end), uploaded at the
 * vblank of the step; the closed window's cells, saved when it opens, are put
 * back at the end. A window off the camera's reach (the plane holds 512 px)
 * is left alone. */
#define WIN_PLANE 0xC000
typedef struct { u8 *owner; u16 wx; u8 col, row, pend, saved; u16 cell[16]; } Win;
static Win win[2];
static const u16 win_tile[2][16] = {
    { 0x6AC, 0x6AD, 0x6AE, 0x6AF, 0x6B0, 0x6B1, 0x6B2, 0x6B3, 0x6B4, 0x6B5, 0x6B6, 0x6B7, 0x6B8, 0x6B9, 0x6BA, 0x6BB },
    { 0x6BC, 0x6BD, 0x6BE, 0x6BF, 0x6C0, 0x6C1, 0x6C2, 0x6C3, 0x6C4, 0x6C5, 0x6C6, 0x6C7, 0x5F4, 0x5F5, 0x5F6, 0x5F7 } };

static int win_reach(const Win *w)
{
    u16 d = w->wx - RAM16(0xFFA200) + 64;
    return d < 384;
}

/* tdevil.c's window_tiles, at each of its steps (n = 1-4) */
void win_step(u8 *p, int closing, int n)
{
    Win *w = 0;
    int k;
    if (RAM8(0xFFC512) != 1) return;
    for (k = 0; k < 2; k++)
        if (win[k].owner == p) w = &win[k];
    if (!closing && n == 1) {                   /* a window opens (this step writes it closed) */
        u16 x = p[17] << 8 | p[18], y = p[21] << 8 | p[22];     /* (odd addresses) */
        if (!w) {
            for (k = 0; k < 2 && !w; k++) {
                u8 *q = win[k].owner;
                if (!q || !q[4] || q[10] != 4) w = &win[k];     /* free, or its devil is gone */
            }
            if (!w) w = &win[0];
        }
        w->owner = p;
        w->wx = ((x >> 4) - 1) << 4;
        w->col = (((x >> 4) - 1) * 2) & 63;
        w->row = (30 - 2 * (y >> 4)) & 31;
        w->saved = 0;
        w->pend = 0;
        return;
    }
    if (!w) return;
    k = closing ? 4 - n : n - 1;                /* 0 closed, 1-3 the open poses */
    w->pend = k ? k : 0xFF;
}

static void win_vblank(Win *w, int k)
{
    int r, c;
    u16 a;
    if (!w->pend) return;
    if (!win_reach(w)) { w->pend = 0; return; }
    if (w->pend == 0xFF) {
        if (w->saved == 1)
            for (r = 0; r < 4; r++) {
                VDP_CTRLL = VRAM_W(WIN_PLANE + ((w->row + r) & 31) * 128 + w->col * 2);
                for (c = 0; c < 4; c++) VDP_DATA = w->cell[r * 4 + c];
            }
        w->saved = 0;                           /* closed again: the slot is free */
        w->owner = 0;
        w->pend = 0;
        return;
    }
    if (!w->saved) {
        for (r = 0; r < 4; r++) {
            VDP_CTRLL = VRAM_R(WIN_PLANE + ((w->row + r) & 31) * 128 + w->col * 2);
            for (c = 0; c < 4; c++) w->cell[r * 4 + c] = VDP_DATA;
        }
        w->saved = 1;
    }
    a = (w->pend - 1) * 256;                    /* 16 tiles of 16 words */
    if (k == 0) dma_vram((u32)(win_art + a), 512, 0x6AC * 32);
    else { dma_vram((u32)(win_art + a), 384, 0x6BC * 32); dma_vram((u32)(win_art + a + 192), 128, 0x5F4 * 32); }
    for (r = 0; r < 4; r++) {
        VDP_CTRLL = VRAM_W(WIN_PLANE + ((w->row + r) & 31) * 128 + w->col * 2);
        for (c = 0; c < 4; c++) VDP_DATA = (w->cell[r * 4 + c] & 0xE000) | win_tile[k][r * 4 + c];
    }
    w->pend = 0;
}

/* hook_sat_dma: the uploads for the sprites about to be shown */
void sat_vblank(void)
{
    int b;
    win_vblank(&win[0], 0);
    win_vblank(&win[1], 1);
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

/* the burst ($E8A7 for size class 4: $5B89's 2x2 for 3 frames, then $5B24's
 * 3x3, 4 frames a pose) by the port's burst count (+9, 1-22, hook_satan_die;
 * 0 = the pose stays). Lined up with the arcade on the frame the Satan dies:
 * the pose for 3 frames, the 2x2 for 3, A B A B for 4 each, then C, which the
 * arcade shows 3 frames and the port 2 (its score comes a frame earlier). */
const u8 sat_burst[23] = {
    0, 0, 12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15 };

/* the star's frames for the shot draw ($117238: count, then dx, dy, attr) */
const s16 star_frames[2][4] = { { 1, -8, 8, STAR_T }, { 1, -8, 8, STAR_T + 4 } };

/* ---- the opening: the graveyard before the black part ------------------
 * The arcade shows stage 1's graveyard with Arthur sitting in his boxers, the
 * princess and the armour for 193 frames after Start, fading its bg palettes
 * at +65 and +129 (Arthur turns his head at +149), then goes on on black; the
 * port's intro ($E0C) was only the black part. intro_scene draws the arcade's
 * picture (mkart.py) and waits that long, then $E0C runs, its 155 steps
 * paced by intro_waits so its events come when the arcade's do. Start skips
 * both after 20 frames, as in $E0C. */
void intro_frame(void);                         /* bossart_glue.s: $EDE + $BF72 */

static void vram_fill_plane(const u16 *src, u16 base)
{
    int r, c;
    for (r = 0; r < 28; r++) {
        VDP_CTRLL = VRAM_W(base + r * 128);
        for (c = 0; c < 32; c++) VDP_DATA = *src++;
    }
}

static void isc_sprites(const u16 (*s)[3])
{
    int k;
    VDP_CTRLL = VRAM_W(0xF000);
    for (k = 0; k < ISC_NSPR; k++) {
        VDP_DATA = s[k][0];
        VDP_DATA = 0x0500 | (k + 1 < ISC_NSPR ? k + 1 : 0);
        VDP_DATA = s[k][2];
        VDP_DATA = s[k][1];
    }
}

static void isc_cram(const u16 *c)
{
    int k;
    VDP_CTRLL = CRAM_W(0);
    for (k = 0; k < 64; k++) VDP_DATA = c[k];
}

int intro_scene(void)
{
    u16 n;
    u32 k;
    VDP_CTRL = 0x8104;                          /* display off, as $E0C */
    VDP_CTRLL = VRAM_W(0);
    for (k = 0; k < 0x4000; k++) VDP_DATAL = 0;
    vram_copy(isc_tiles, sizeof isc_tiles / 2, 0);
    vram_fill_plane(isc_planeb, 0xC000);
    vram_fill_plane(isc_planea, 0xE000);
    isc_sprites(isc_spr870);
    isc_cram(isc_cram0);
    VDP_CTRLL = VSRAM_W(0);
    VDP_DATA = 0; VDP_DATA = 0;
    VDP_CTRL = 0x8164;                          /* display on */
    for (n = 0; n < ISC_FRAMES; n++) {
        intro_frame();
        if (n == 65) isc_cram(isc_cram1);
        if (n == 129) isc_cram(isc_cram2);
        if (n == 149) isc_sprites(isc_spr955);
        if (n >= 20 && !(RAM8(0xFF7000) & 1)) return 1;
    }
    return 0;
}
