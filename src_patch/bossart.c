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
 * the new sprites (so tiles and sprites change together); the score (the
 * port's 2 pieces) goes into the buffer too. Stage 5 has one Satan, so there
 * the second buffer holds the skulls' standing poses and the Petite Devils'
 * fireball. The shot's star goes to $5F4-$5FB, a block an unused loader once
 * filled ($6434, unreachable) and nothing reads in stages 5 and 6.
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
#define STAR_T    0x5F4
#define SCORE_SRC 0x255B74      /* the port's ROM copy of its score tiles ($544-$54B) */
#define SKULL_T   0x524         /* stage 5: the skulls' 8 standing pieces */
#define FIRE_T    0x544         /* stage 5: the devils' fireball */

static u8 *sb_owner[2];         /* the Satan slot each buffer is drawn for */
static const u16 *sb_want[2];   /* the art of the pose last drawn (0 none) */
static const u16 *sb_have[2];   /* ... and what the buffer holds (0 unknown) */
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
    if (stage_has_satans())
        vram_copy(star_art, 8 * 16, STAR_T);
    if (RAM8(0xFFC512) == 4) {
        vram_copy(skull_art, 8 * 64, SKULL_T);
        vram_copy(fire_art, 64, FIRE_T);
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

/* a window whose devil no longer steps it: dead, removed, or out of its
 * window state (the arcade's tiles then stay as they were: $B457 is their
 * only writer, from the devil's own window state) */
static int win_orphan(const Win *w)
{
    const u8 *q = w->owner;
    return !q[4] || q[10] != 4 || q[7] != 1 || q[8] != 4;
}

/* give up a slot: its closed cells go back at the vblank (pend $FF) while the
 * window is in reach; out of reach they are the streamer's again */
static void win_free(Win *w)
{
    if (win_reach(w) && w->saved == 1) { w->pend = 0xFF; return; }
    w->owner = 0; w->saved = 0; w->pend = 0;
}

static int win_free_slot(void)
{
    int k;
    for (k = 0; k < 2; k++)
        if (!win[k].owner) return k;
    return -1;
}

/* tdevil.c's window_tiles, at each of its steps (n = 1-4). A window whose
 * devil dies or leaves before it is closed keeps its slot and its pose, as
 * the arcade's stays open; the slot is given up only when a new window finds
 * none free (preferring one off the camera's reach), and then its closed
 * cells are put back: the arcade can show three open windows, there are two
 * slots. The new window takes its slot at its first pose (step 2: step 1
 * writes it closed), so a slot given up at step 1 is free by then. */
void win_step(u8 *p, int closing, int n)
{
    Win *w = 0;
    int k;
    if (RAM8(0xFFC512) != 1) return;
    for (k = 0; k < 2; k++)
        if (win[k].owner == p) w = &win[k];
    if (!closing && n == 1) {                   /* a window opens */
        if (w) win_free(w);                     /* the slot's last devil's window */
        if (win_free_slot() < 0) {
            Win *v = 0;
            for (k = 0; k < 2; k++)
                if (win[k].pend != 0xFF && win_orphan(&win[k]) && (!v || !win_reach(&win[k]))) v = &win[k];
            if (v) win_free(v);
        }
        return;
    }
    if (!w && !closing && n == 2) {             /* its first pose: take a slot */
        u16 x = p[17] << 8 | p[18], y = p[21] << 8 | p[22];     /* (odd addresses) */
        k = win_free_slot();
        w = &win[k < 0 ? 0 : k];
        w->owner = p;
        w->wx = ((x >> 4) - 1) << 4;
        w->col = (((x >> 4) - 1) * 2) & 63;
        w->row = (30 - 2 * (y >> 4)) & 31;
        w->saved = 0;
        w->pend = 0;
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
    if (!win_reach(w)) {
        if (w->pend == 0xFF) { w->owner = 0; w->saved = 0; }
        w->pend = 0;
        return;
    }
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
            dma_vram((u32)sb_want[b], (u16)sb_nart[b] * 128, (b ? SAT_BUF1 : SAT_BUF0) * 32);
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
    for (b = 0; b < (RAM8(0xFFC512) == 4 ? 1 : 2); b++) {
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
    if (!fr->npc && fr->art != 0xFFFF) return;
    b = buffer_for(p);
    if (b < 0) return;
    base = b ? SAT_BUF1 : SAT_BUF0;
    if (fr->art == 0xFFFF) {                    /* the score, as the port's frame 5 */
        sb_want[b] = (const u16 *)SCORE_SRC;
        sb_nart[b] = 2;
        put(o, p, cam, -16, 8, base);
        put(o, p, cam, 0, 8, base + 4);
        return;
    }
    sb_want[b] = sat_art + fr->art;
    sb_nart[b] = fr->nart;
    for (k = 0; k < fr->npc; k++) {
        const SatPiece *c = &fr->pc[k];
        put(o, p, cam, c->dx, c->dy, (base + c->slot * 4) | (u16)c->flip << 8);
    }
}

/* the burst ($E8A7 for size class 4: $5B89's 2x2 for 3 frames, then $5B24's
 * 3x3, 4 frames a pose) by the port's burst count (+9, 1-23, hook_satan_die;
 * 0 = the pose stays). Lined up with the arcade on the frame the Satan dies:
 * the pose for 3 frames, the 2x2 for 3, A B A B for 4 each, then C for 3,
 * then the score (the port's count is a frame behind the arcade's, so it
 * needs 23 of them for the arcade's 22). */
const u8 sat_burst[24] = {
    0, 0, 12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15 };

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

/* ---- stage 5's skulls and Petite Devils ----------------------------------
 * The burst both die in ($E85B for class 3: 2 x 2 pieces, 5 poses after 3
 * frames of the last pose, 4 frames each, the last 3) is the port's own
 * enemy burst, resident in stage 5 at tiles $320-$36B (line 2, the frames at
 * $14C57A; the same art as the arcade's $1C0-$1D9). j = the frames since
 * the death (1-20, the 21-frame death count of each). */
static const u16 BURST[5][4] = {                /* (-16,16) (-16,0) (0,16) (0,0), */
    { 0x4B28, 0x4B2C, 0x4B20, 0x4B24 }, { 0x4B38, 0x4B3C, 0x4B30, 0x4B34 },     /* each mirrored */
    { 0x4B48, 0x4B4C, 0x4B40, 0x4B44 }, { 0x4B58, 0x4B5C, 0x4B50, 0x4B54 },     /* (attribute $54) */
    { 0x4B68, 0x4B2C, 0x4B60, 0x4B24 } };

static int burst(Spr *o, const u8 *p, const u16 *cam, int j)
{
    const u16 *t;
    if (j < 2) return 0;                        /* the pose stays */
    t = BURST[j < 18 ? (j - 2) >> 2 : 4];
    put(o, p, cam, -16, 16, t[0]);
    put(o, p, cam, -16, 0, t[1]);
    put(o, p, cam, 0, 16, t[2]);
    put(o, p, cam, 0, 0, t[3]);
    return 1;
}

/* The type-9 frames for its draw ($107626, which reads them through the
 * offset table and frame base patched to these): 0-2 the port's ($23CA18:
 * the skull asleep, $A7, and rising, $A2 $A3 / $A4 $A5; also the dragon's
 * fire in stages 3, 4 and 6), 3-5 the skull standing up ($CE1A: A8 A0 A9 A1,
 * AA A2 AB A3, AC A4 AD A5; the new pieces in SKULL_T), 6-10 the burst (BURST
 * above) for skull.c to show while it dies. Count, then dx, dy, attribute. */
#define SK(a, b, c, d) 4, -16, 16, a, -16, 0, b, 0, 16, c, 0, 0, d
const s16 t9_frames[] = {
    1, -8, 8, 0x04A0,
    2, -16, 8, 0x04A4, 0, 8, 0x04A8,
    2, -16, 8, 0x04AC, 0, 8, 0x04B0,
    SK(SKULL_T + 8, SKULL_T, SKULL_T + 12, SKULL_T + 4),
    SK(SKULL_T + 16, 0x4A4, SKULL_T + 20, 0x4A8),
    SK(SKULL_T + 24, 0x4AC, SKULL_T + 28, 0x4B0),
    SK(0x4B28, 0x4B2C, 0x4B20, 0x4B24), SK(0x4B38, 0x4B3C, 0x4B30, 0x4B34),
    SK(0x4B48, 0x4B4C, 0x4B40, 0x4B44), SK(0x4B58, 0x4B5C, 0x4B50, 0x4B54),
    SK(0x4B68, 0x4B2C, 0x4B60, 0x4B24) };
const s16 t9_offs[11] = { 0, 8, 22, 36, 62, 88, 114, 140, 166, 192, 218 };

/* $11C15E in stage 5, a dying devil (the port's count +36: 21 down to 1) */
int pd_burst(u8 *p, const u16 *cam, Spr *o)
{
    u16 n = p[36] << 8 | p[37];
    return burst(o, p, cam, n ? 21 - n : 0);
}

/* the port's devil frames ($10D392/$10D3E4, art $10D526, 41 frames) and the
 * carrier's wing poses with the fireball after them: 41-43 $FD-$FF facing
 * right, 44-46 left */
#define PD_N0 41
static const s16 PD_ENT[2][4] = { { 1, -8, 8, 0x03B0 }, { 1, -8, 8, 0x0BB0 } };
const u16 *pd_src(u16 f)
{
    if (f < PD_N0) return (const u16 *)(0x10D526 + (u32)f * 128);
    return pd_art + ((f - PD_N0) % 3) * 64;
}
const s16 *pd_entry(u16 f)
{
    if (f < PD_N0) return (const s16 *)(0x10D3E4 + RAM16(0x10D392 + f * 2));
    return PD_ENT[f >= PD_N0 + 3];
}

/* a devil's fireball (type-6 shot, +8 = $D8) in stage 5: $F7 */
const s16 fire_frame[4] = { 1, -8, 8, FIRE_T };
