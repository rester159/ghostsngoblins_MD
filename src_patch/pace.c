/* Render skip ("draw fewer frames when busy"). The game logic runs every
 * update; in busy stretches the sprite layer is drawn less often.
 *
 * pace_start() runs at the start of every stage-loop update ($6938, in
 * VBlank, before any of the update's DMA) and decides two things:
 *  - hold: this frame uploads nothing for the sprites (sprite table,
 *    Arthur's and Maximo's frames), so the screen keeps the last sprites.
 *    Always when the last update skipped its build (the buffer is stale),
 *    and when this update starts late in VBlank: from NTSC line 241 on, the
 *    uploads would run into the active display, where DMA is ~10x slower
 *    and halts the CPU (updates starting there took 290-320 lines instead
 *    of ~265).
 *  - skip this update's sprite build (render_gate in glue.s): when behind,
 *    i.e. it started 5 or more lines into VBlank (an update takes about a
 *    frame, so it would end past the next VBlank start too and the delay
 *    grows) or a whole frame was lost since the last one.
 * The sprites are never held more than FS_MAX frames in a row.
 *
 * Linked last so adding this RAM moves no other variable. */
#include "md.h"

#define FS_MAX 3

void dma_vram(u32 src, u16 bytes, u16 vram);

u16 fs_last;    /* VBlank count (low word) at the last update start */
u16 fs_flags;   /* bit 0: skip this update's sprite build; bit 1: it was skipped */
u16 fs_force;   /* nonzero: skip every other build (equivalence tests only) */
u16 fs_hold;    /* nonzero: no sprite uploads this frame */
u16 fs_stale;   /* frames shown in a row without a sprite upload */
u32 fs_pend;    /* Arthur's frame upload held back (source; 0 = none) */

void pace_start(void)
{
    u16 now = RAM16(0xFF7DFE);
    u16 lost = now - fs_last >= 2;
    u16 built = !(fs_flags & 2);
    u16 ntsc = !(VDP_CTRL & 1);
    u8 v = RAM8(0xC00008);
    u16 late = ntsc && v >= 0xE5;       /* line 229 on (the counter runs $00-$EA, $E5-$FF) */
    u16 very_late = ntsc && v >= 0xEB;  /* line 241 on */
    fs_last = now;
    fs_hold = !built || (very_late && fs_stale < FS_MAX);
    fs_stale = fs_hold ? fs_stale + 1 : 0;
    fs_flags = ((late || lost || (fs_force && built)) && fs_stale < FS_MAX) ? 1 : 0;
}

/* Holding is only meant for the uploads of the update pace_start opened. */
static u16 holding(void) { return fs_hold && RAM16(0xFF7DFE) == fs_last; }

/* hook_sat_dma: nonzero = skip the sprite table upload this frame. Otherwise
 * the held-back Arthur frame goes up with it. */
u16 pace_sat(void)
{
    if (holding()) return 1;
    if (fs_pend) { dma_vram(fs_pend, 512, 0x6000); fs_pend = 0; }
    return 0;
}

/* hook_arthur_dma: nonzero = hold this upload of Arthur's frame. */
u16 pace_arthur(u32 src)
{
    if (holding()) { fs_pend = src; return 1; }
    fs_pend = 0;
    return 0;
}
