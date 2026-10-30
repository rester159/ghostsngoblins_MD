/* Render skip ("draw fewer frames when busy"). The game logic runs every
 * update; in busy stretches the sprite layer is drawn less often.
 *
 * pace_start() runs at the start of every stage-loop update ($6938, in
 * VBlank, before any of the update's DMA) and decides two things:
 *  - hold: this frame uploads nothing for the sprites (sprite table,
 *    Arthur's and Maximo's frames), so the screen keeps the last sprites.
 *    Always when no build waits to be shown (the last one is on screen; a
 *    build held so far is shown by the next update that may upload), and
 *    when this update starts late in VBlank: from NTSC line 241 on, the
 *    uploads would run into the active display, where DMA is ~10x slower
 *    and halts the CPU (updates starting there took 290-320 lines instead
 *    of ~265).
 *  - skip this update's sprite build (render_gate in glue.s): when behind,
 *    i.e. it started 5 or more lines into VBlank (an update takes about a
 *    frame, so it would end past the next VBlank start too and the delay
 *    grows) or a whole frame was lost since the last one.
 * The sprites are never held more than FS_MAX frames in a row, except by an
 * update that starts in the picture: the one before ran past the VBlank and
 * the wait let this one go at once (glue.s vbl_wait) rather than lose a
 * frame. It uploads nothing (the screen stays as it was: no DMA or scroll
 * change in the picture) and always skips its build: that keeps it short
 * (~240 lines in co-op stage 6), so the starts come back into VBlank within a
 * few updates. Building there past FS_MAX kept every update long and starting
 * in the picture, the sprites frozen ~30 frames (measured).
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
/* The sprite buffer holds a build not shown yet (glue.s clear_sat and
 * render_gate1 set it, an upload clears it). A build held past its next
 * update is shown by the first one that may upload, with the plane B scroll
 * it was built for (fs_dsx/fs_dsy, taken at the first hold: the camera the
 * next update starts with is the one that build drew against). */
u16 fs_unshown, fs_deferred, fs_dsx, fs_dsy;
u16 fs_how;     /* glue.s hook_sat_dma: pace_sat's answer */

void pace_start(void)
{
    u16 now = RAM16(0xFF7DFE);
    u16 lost = now - fs_last >= 2;
    u16 built = !(fs_flags & 2);
    u16 st = VDP_CTRL;
    u16 ntsc = !(st & 1);
    u16 mid = !(st & 8);                /* not in VBlank: started in the picture */
    u8 v = RAM8(0xC00008);
    u16 late = ntsc && v >= 0xE5;       /* line 229 on (the counter runs $00-$EA, $E5-$FF) */
    u16 very_late = ntsc && v >= 0xEB;  /* line 241 on */
    fs_last = now;
    fs_hold = !fs_unshown || mid || (very_late && fs_stale < FS_MAX);
    fs_stale = fs_hold ? fs_stale + 1 : 0;
    fs_flags = (mid || ((late || lost || (fs_force && built)) && fs_stale < FS_MAX)) ? 1 : 0;
}

/* Holding is only meant for the uploads of the update pace_start opened. */
static u16 holding(void) { return fs_hold && RAM16(0xFF7DFE) == fs_last; }

/* The plane B scroll ($FF9100/$FF9102) that goes with the sprites on screen:
 * the stage loops write it right after the sprite table DMA, so on a held
 * frame the background moved on while the sprites stayed, and everything
 * fixed to the scenery (the tombstones) slipped by the camera's step for a
 * frame, a shiver while scrolling. A held frame now writes these instead
 * (glue.s hook_sat_dma). */
u16 fs_sx, fs_sy;

static u16 near(u16 a, u16 b, u16 d) { return (u16)(a - b + d) <= 2 * d; }

/* hook_sat_dma: 1 = skip the sprite table upload this frame; 0 = upload it
 * (the scroll from $FF9100/2 as the loop writes it); 2 = upload a held build
 * with its own scroll (fs_sx/fs_sy, written as on a held frame). The
 * held-back Arthur frame goes up with an upload. */
u16 pace_sat(void)
{
    u16 sx = RAM16(0xFF9100), sy = RAM16(0xFF9102);
    if (holding()) {
        if (fs_unshown && !fs_deferred) { fs_dsx = sx; fs_dsy = sy; fs_deferred = 1; }
        /* a jump (a restart, a new stage) isn't held back */
        if (!near(sx, fs_sx, 16) || !near(sy, fs_sy, 16)) { fs_sx = sx; fs_sy = sy; }
        /* nor a vertical scroll into another cell row: the plane has 32 rows
         * for 29 on screen and the game streams the rows past the bottom edge
         * into the other 3, so the held view's top row may already hold the
         * new bottom's (a line of it at the top of the screen, measured on
         * falls). The sprites then lag the background vertically for that
         * frame, as before. */
        if ((u16)(16 - sy) >> 3 != (u16)(16 - fs_sy) >> 3) fs_sy = sy;
        return 1;
    }
    fs_unshown = 0;
    if (fs_pend) { dma_vram(fs_pend, 512, 0x6000); fs_pend = 0; }
    if (fs_deferred) {
        fs_deferred = 0;
        fs_sx = fs_dsx; fs_sy = fs_dsy;
        return 2;
    }
    fs_sx = sx; fs_sy = sy;
    return 0;
}

/* hook_arthur_dma: nonzero = hold this upload of Arthur's frame. */
u16 pace_arthur(u32 src)
{
    if (holding()) { fs_pend = src; return 1; }
    fs_pend = 0;
    return 0;
}
