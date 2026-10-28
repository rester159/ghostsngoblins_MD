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
 * none borrows the first slot's (a Big Man in another pose, not garbage). */
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
static u8 bm_nslot;                     /* slots usable in this mode (1-3) */
static u16 bm_frame[NSLOT];             /* the pose a slot holds, + 1 (0: none) */
static u16 bm_used[NSLOT];              /* the build (fs_last) that last drew it */
static u16 bm_build;                    /* the last build seen */
static u8 bm_pend;                      /* slots to upload with the next sprite table */

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

/* hook_sat_dma, with the sprite table: the new poses' pieces */
void bm_vblank(void)
{
    int s, j, n;
    u32 rec;
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
