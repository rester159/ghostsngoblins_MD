/* Stage 5's Big Men, their art (type 10). The type-10 builder ($AF1E/$AF4A)
 * draws every Big Man from the frame records ($125620 via $123B3E), whose
 * pieces point at tiles $320-$3F3: stage 2 loads the Big Man's art there
 * (the port's ROM copy at $123BA0), stage 5 doesn't (its enemy burst and
 * other art sit at $320-$36B), so stage 5's Big Men were drawn from whatever
 * those tiles held. Here, in stage 5 only, each pose drawn gets a 16-tile
 * slot in VRAM that stage 5 leaves unused in the mode being played (VRAM
 * scans of the tower and the room): Arthur alone $690, $6A8, $6B8; co-op
 * $6A8, $6B8 (Maximo uses $681-$69B); Firebrand $6B8 (his wings, fire icon,
 * map marker and frames fill $680-$6B7). All are in the window table's
 * space, the window being off in play. Its four pieces are uploaded from the
 * ROM copy with the sprite table that first shows it (hook_sat_dma), and its
 * pieces point there. Poses already in a slot keep it; a slot is taken over
 * only when no Big Man of the build being made uses it; a pose that finds
 * none borrows the first slot's (a Big Man in another pose, not garbage).
 *
 * Their shots (shot type 3, $B042) are one 16x16 piece each, from the same
 * art: tiles $390, $394 (frames 1-4, flipped by direction), $398, $39C
 * (frames 5, 6). In stage 5 the four pieces sit in tiles free there in every
 * mode (VRAM scans of the tower, the Big Men's floors and the room): $6D0,
 * $6D4, $6D8 and $24D, uploaded together with the sprite table that first
 * shows a shot. */
#include "md.h"

void dma_vram(u32 src, u16 bytes, u16 vram);
extern u16 fs_last;                     /* pace.c: the VBlank count at this update's start */

#define BM_IDX   0x123B3E               /* frame -> record offset */
#define BM_REC   0x125620
#define BM_ART   0x123BA0               /* the art of tiles $320-$3F3 */
#define BM_T0    0x320
#define NSLOT    3

int fb_on(void);                        /* firebrand.c */
int coop_on(void);                      /* p2.c */
static const u16 bm_base[NSLOT] = { 0x6B8, 0x6A8, 0x690 };   /* in the order the modes allow them */
/* skull_hook's fast path (bigman.s), a piece's lookup without the C (12 a frame
 * with three skeletons standing cost ~20 lines, and stage 6 lost updates): per
 * 4-tile piece from $320 (CR_T0) to $543 (SK_T1), the slot + 1 that holds it, 0
 * when not known, $FF when skull_attr passes it through; kept by piece_slot.
 * Defined first so that it sits after the other RAM here. */
#define SK_NMAP  ((0x544 - 0x320) >> 2)
static u8 sk_map[SK_NMAP];
static u8 bm_nslot;                    /* slots usable in this mode (1-3) */
static u16 bm_frame[NSLOT];             /* the pose a slot holds, + 1 (0: none) */
static u16 bm_used[NSLOT];              /* the build (fs_last) that last drew it */
static u16 bm_build;                    /* the last build seen */
static u8 bm_pend;                      /* slots to upload with the next sprite table */
#define SH_T0    0x390                  /* the shots' first piece */
static const u16 sh_base[4] = { 0x6D0, 0x6D4, 0x6D8, 0x24D };
static u8 sh_state;                     /* 0: not in VRAM, 1: upload pending, 2: loaded */
static u16 sh_build;                    /* the last build that drew a shot */

static u32 rec_of(u16 frame) { return BM_REC + RAM16(BM_IDX + 2 * frame); }

/* bigman.s bm_attr: a piece's attribute word (slot = the Big Man's slot,
 * piece = its record entry: x, y, attribute) */
u16 bm_attr(const u8 *slot, u32 piece)
{
    u16 frame = RAM16((u32)slot + 30), attr = RAM16(piece + 4);
    u32 first = rec_of(frame) + 2;
    int s, k = (int)(piece - first) / 6;
    if ((u16)(fs_last - bm_build) > 30 || !bm_nslot) {  /* a pause, a death, a map: VRAM may have been reloaded */
        for (s = 0; s < NSLOT; s++) bm_frame[s] = 0;
        bm_pend = 0;
        bm_nslot = fb_on() ? 1 : coop_on() ? 2 : 3;
    }
    bm_build = fs_last;
    for (s = 0; s < bm_nslot; s++)
        if (bm_frame[s] == frame + 1) break;
    if (s == bm_nslot) {
        for (s = 0; s < bm_nslot; s++)
            if (!bm_frame[s]) break;
        if (s == bm_nslot)
            for (s = 0; s < bm_nslot; s++)
                if (bm_used[s] != fs_last) break;
        if (s == bm_nslot)                          /* more poses than slots: the first slot's */
            return (attr & 0xF800) | (bm_base[0] + k * 4);
        bm_frame[s] = frame + 1;
        bm_pend |= 1 << s;
    }
    bm_used[s] = fs_last;
    return (attr & 0xF800) | (bm_base[s] + k * 4);
}

/* bigman.s bm_shot_hook: a shot piece's attribute in stage 5 */
u16 bm_shot_attr(u16 attr)
{
    u16 k = ((attr & 0x7FF) - SH_T0) >> 2;
    if (k > 3) return attr;
    if (RAM8(0xFFC512) == 2) return (attr & 0x1800) | (0x6C0 + (k & 1) * 4);    /* stage 3: a fire tower's shot, line 0 */
    if ((u16)(fs_last - sh_build) > 30) sh_state = 0;   /* a pause, a death, a map: VRAM may have been reloaded */
    sh_build = fs_last;
    if (!sh_state) sh_state = 1;
    return (attr & 0xF800) | sh_base[k];
}

/* Stage 2's crows in the building (type 1, the stage 1-2 build's $B152).
 * Their pieces point at the crow bank's tiles $320-$397 (perches and flight
 * $378-$397, the burst $320-$377; the ROM copy at $14B676), but while the
 * building's bank is in ($FFB028 = 0) those tiles hold the Big Man: a crow
 * was drawn as pieces of him (its burst) or, flying, not at all (its frames).
 * Here each piece drawn there takes a 4-tile slot of a small cache in tiles
 * the building leaves free in every mode (VRAM scans of its floors; $6AB-$6B6
 * not with Firebrand, whose frames go up to $6B7), uploaded with the sprite
 * table that first shows it; a slot is reused once no piece of the build
 * being made uses it. A crow takes 1 piece flying, 4 bursting. Its poses
 * ($378-$397) are uploaded from crow_blue, the same tiles recoloured blue on
 * line 0 by tools/patch_gng.py (the arcade's building crows are blue, its
 * stepping-stone crows red, as the port's). */
#define CR_ART   0x14B676               /* the crow bank's tiles from $320 */
#define CR_T0    0x320
#define CR_T1    0x398
#define NCR      12
static const u16 cr_base[NCR] = { 0x6B8, 0x6BC, 0x6C0, 0x6C4, 0x6D0, 0x6D4, 0x6D8, 0x79A, 0x79E,
                                   0x6AB, 0x6AF, 0x6B3 };
static u16 cr_tile[NCR];                /* the crow bank tile a slot holds, 0: none */
static u16 cr_used[NCR];                /* the build that last drew it */
static u16 cr_build;
static u16 cr_pend;                     /* slots to upload with the next sprite table */
#define CR_POSE  0x378                  /* the first pose tile; below it the burst */
const u8 crow_blue[32 * 32] = { 1 };    /* filled by tools/patch_gng.py */

/* Stage 6's skulls: their standing pieces (the Satans' second buffer holds
 * something else there) and burst (not resident in stage 6) come the same way,
 * into tiles the tower leaves free in every mode (VRAM scans of the climb; from $6AC
 * is type 8's art here, $700 up the live plane and tables). Piece tiles are stage 5's: $320-$36B the
 * burst, SK_T0 the standing art. */
#define SK_T0    0x524
#define SK_T1    0x544
#define NSK      8
extern const u16 *const skull_pieces;
const u16 sk_base[NSK] = { 0x6A0, 0x24D, 0x79E, 0x7CC, 0x6A4, 0x6D0, 0x6D4, 0x6D8 };
/* for skull_hook (the RAM here keeps its place; cr_used follows cr_build) */
u8 *const sk_map_p = sk_map;
u16 *const sk_build_p = &cr_build;

/* sk_map's entry for tile t, if it has one */
static void map_set(u16 t, u8 v)
{
    u16 i = t - CR_T0;
    if (i < SK_T1 - CR_T0 && !(i & 3)) sk_map[i >> 2] = v;
}

/* The item objects' art: the object-art streamer ($1169B8, its state at
 * $FF97C0: loaded frames +0/+2, wanted +6/+8) uploads 8 tiles of the first
 * item object's frame ($FF9780, an enemy's drop; live at $FFC8C4, copied to
 * $FF9784 for its update) to $798-$79F, and the second's ($FFCEA0: a hidden
 * item's pot) to $6D0-$6D7, each time the frame changes. The cache's slots
 * there were measured free because the second object never came in stages
 * 4-6 (stageend.s item_reload). While an object is live, the slots on its
 * tiles are given up and not taken (item_guard each update, before the
 * objects' update and the sprites; piece_slot), and once the cache has written
 * there the channel is made to load its frame again. Bit c: channel c
 * ($FF97C0 + 2c). The skulls' fast path (bigman.s) finds no entry for a slot
 * given up, so it needs no test of its own. */
static u8 ch_dirty;                     /* channels whose tiles the cache wrote */

static u8 ch_live(void)
{
    return ((RAM8(0xFFC8C4) | RAM8(0xFF9784)) ? 1 : 0) | (RAM8(0xFFCEA4) ? 2 : 0);
}

/* the channels a 4-tile slot at v overlaps */
static u8 ch_mask(u16 v)
{
    return (v < 0x7A0 && v + 4 > 0x798 ? 1 : 0) | (v < 0x6D8 && v + 4 > 0x6D0 ? 2 : 0);
}

/* the slots of base[0..n) on a live channel's tiles */
static u16 ch_blocked(const u16 *base, int n, u8 live)
{
    u16 blk = 0;
    int s;
    if (live)
        for (s = 0; s < n; s++)
            if (ch_mask(base[s]) & live) blk |= 1 << s;
    return blk;
}

/* stageend.s se_items, each update before the item objects' */
void item_guard(void)
{
    u8 live = ch_live();
    u16 blk;
    int s;
    if (!live) return;
    blk = RAM8(0xFFC512) == 5 ? ch_blocked(sk_base, NSK, live) : ch_blocked(cr_base, NCR, live);
    for (s = 0; s < NCR; s++)
        if ((blk & (1 << s)) && cr_tile[s]) {
            map_set(cr_tile[s], 0);
            cr_tile[s] = 0;
            cr_pend &= ~(1 << s);
        }
    for (s = 0; s < 2; s++)
        if (live & ch_dirty & (1 << s)) {
            RAM16(0xFF97C0 + 2 * s) = 0xFFFF;
            ch_dirty &= ~(1 << s);
        }
}

/* sk_map follows cr_tile here: a skull's piece taking a slot is entered, any
 * tile leaving one cleared */
static u16 piece_slot(u16 attr, const u16 *base, int n)
{
    u16 t = attr & 0x7FF, blk;
    int s;
    if ((u16)(fs_last - cr_build) > 30) {           /* a pause, a death, a map: VRAM may have been reloaded */
        for (s = 0; s < NCR; s++) {
            if (cr_tile[s]) map_set(cr_tile[s], 0);
            cr_tile[s] = 0;
        }
        cr_pend = 0;
    }
    cr_build = fs_last;
    blk = ch_blocked(base, n, ch_live());
    for (s = 0; s < n; s++)
        if (cr_tile[s] == t) break;
    if (s == n) {
        for (s = 0; s < n; s++)
            if (!cr_tile[s] && !(blk & (1 << s))) break;
        if (s == n)
            for (s = 0; s < n; s++)
                if (cr_used[s] != fs_last && !(blk & (1 << s))) break;
        if (s == n) s = 0;                          /* more pieces than slots: the first slot's */
        else {
            if (cr_tile[s]) map_set(cr_tile[s], 0);
            cr_tile[s] = t; cr_pend |= 1 << s;
            ch_dirty |= ch_mask(base[s]);
            if (base == sk_base) map_set(t, s + 1);
        }
    }
    cr_used[s] = fs_last;
    return (attr & 0xF800) | base[s];
}

/* bigman.s crow_hook: a crow piece's attribute while the building's bank is in */
u16 crow_attr(u16 attr)
{
    u16 t = attr & 0x7FF;
    if (t < CR_T0 || t >= CR_T1) return attr;
    return piece_slot(attr, cr_base, fb_on() ? NCR - 3 : NCR);
}

/* bigman.s skull_hook: a type-9 piece's attribute in stage 6 */
u16 skull_attr(u16 attr)
{
    u16 t = attr & 0x7FF;
    if ((t < CR_T0 || t >= CR_POSE) && (t < SK_T0 || t >= SK_T1)) {
        map_set(t, 0xFF);
        return attr;
    }
    return piece_slot(attr, sk_base, NSK);
}

/* hook_sat_dma, with the sprite table: the new poses' pieces */
void bm_vblank(void)
{
    int s, j, n;
    u32 rec;
    if (cr_pend) {
        const u16 *base = RAM8(0xFFC512) == 5 ? sk_base : cr_base;
        for (s = 0; s < NCR; s++)
            if ((cr_pend & (1 << s)) && cr_tile[s]) {
                u16 t = cr_tile[s];
                dma_vram(t >= SK_T0 ? (u32)skull_pieces + (u32)(t - SK_T0) * 32
                         : t >= CR_POSE ? (u32)crow_blue + (u32)(t - CR_POSE) * 32
                         : CR_ART + (u32)(t - CR_T0) * 32, 128, base[s] * 32);
            }
        cr_pend = 0;
    }
    if (sh_state == 1) {
        for (j = 0; j < 4; j++)
            dma_vram(BM_ART + (u32)(SH_T0 - BM_T0 + 4 * j) * 32, 128, sh_base[j] * 32);
        sh_state = 2;
    }
    if (!bm_pend) return;
    for (s = 0; s < NSLOT; s++) {
        if (!(bm_pend & (1 << s)) || !bm_frame[s]) continue;
        rec = rec_of(bm_frame[s] - 1);
        n = RAM16(rec);
        for (j = 0; j < n && j < 4; j++) {
            u16 t = RAM16(rec + 2 + 6 * j + 4) & 0x7FF;
            dma_vram(BM_ART + (u32)(t - BM_T0) * 32, 128, (bm_base[s] + j * 4) * 32);
        }
    }
    bm_pend = 0;
}
