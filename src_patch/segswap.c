/* Stage 2's background changes without the display off.
 *
 * Stage 2's streamer ($11A89C) took the full reload ($11A7C0: display off,
 * the segment's tile set, bank art, palette, 32 columns, display on; two
 * black frames) whenever the column 15 left of the camera (d6, Fixed 49)
 * changed segment ($FFB01C, the section's table at $FFB020) or window
 * ($FFB00C, $11AA08: columns 353, 398), and turned the display off inside
 * the update to swap the bank art at $320-$3F3 ($FFB028, $11AA44: column
 * 349; a black band). The arcade's background is all in ROM and changes
 * nothing there.
 *
 * Segments: tools/seg_reindex.py lays each segment's tiles out on the one
 * before it, so that every cell in the plane's ring at a change is drawn the
 * same in both and a change only needs the new segment's own tiles, in tiles
 * no cell on the plane uses. A step to the next or the previous segment sets
 * the streamer's segment, start column and map (as $11A9DE) and uploads the
 * run list seg_xfer[section][change][direction] at the vblanks, SEG_BUDGET
 * tiles each (the column entering at the right edge, the only one that can
 * show before the end, in the first). Anything else (a life start, a jump of
 * more than one segment, a section change) still takes the reload.
 * Window: its only change outside the reload is the 16 tiles at $7F0 ($B416),
 * uploaded at the vblank. Bank: the art ($B3E2 / $B3FC) at the vblanks after,
 * in pieces, with the display on.
 * A reload (it counts $FFB008) drops what is left: it uploads everything. */
#include "md.h"

void dma_vram(u32 src, u16 bytes, u16 vram);

#define SEG_BUDGET 96                   /* tiles a vblank: tools/seg_reindex.py BUDGET */
#define B_SEG    RAM16(0xFFB01C)
#define B_SECT   RAM16(0xFFB01E)
#define B_TAB    RAM32(0xFFB020)
#define B_GEN    RAM32(0xFFB008)

/* run lists (u16 runs; runs x u16 first tile, u16 tiles, u32 source):
 * [section][change k: segment k <-> k + 1][0 rightwards, 1 leftwards];
 * filled by tools/seg_reindex.py */
const volatile u32 seg_xfer[3][4][2] = { { { 1 } } };   /* volatile: the patcher, not this, decides */

static const u16 *run;                  /* the run being uploaded */
static u16 nrun, done;                  /* runs left, tiles of this one done */
static u32 bank_src;                    /* bank art left to upload, 0 none */
static u16 bank_left, bank_at;
static u8 win_pend;
static u32 gen;                         /* $FFB008 when these were asked */

static void ask(void)
{
    if (B_GEN != gen) {                 /* a reload since the last: nothing left of before */
        nrun = 0; run = 0; bank_src = 0; win_pend = 0;
        gen = B_GEN;
    }
}

/* segswap.s seg_check: the streamer's d6 is in segment seg; 0 when done
 * here, 1 for the reload */
u16 seg_step(u16 seg)
{
    u16 old = B_SEG, sec = B_SECT, k, dir;
    u32 e, x;
    if (sec > 2) return 1;
    if (seg == old + 1) { k = old; dir = 0; }
    else if (seg + 1 == old) { k = seg; dir = 1; }
    else return 1;
    if (k > 3 || !(x = seg_xfer[sec][k][dir])) return 1;
    ask();
    e = B_TAB + 16 * (u32)seg;
    B_SEG = seg;
    RAM16(0xFFB018) = RAM16(e);         /* the segment's first column */
    RAM32(0xFFB014) = RAM32(e + 12);    /* its map */
    nrun = *(const u16 *)x;
    run = (const u16 *)x + 1;
    done = 0;
    return 0;
}

/* the window's art, as $B416 */
void winart_step(u16 win)
{
    ask();
    RAM16(0xFFB00C) = win;
    win_pend = 1;
}

/* segswap.s bank_hook: the bank art, as $11AA28 */
void bank_step(u16 bank)
{
    ask();
    RAM8(0xFFB028) = bank;
    if (bank) { bank_src = 0x14B676; bank_left = 1920 * 2; }
    else { bank_src = 0x123BA0; bank_left = 3392 * 2; }
    bank_at = 0x6400;
}

/* glue.s hook_sat_dma, at the vblank */
void seg_vblank(void)
{
    u16 left = SEG_BUDGET * 32, n;
    if (!nrun && !bank_src && !win_pend) return;
    if (B_GEN != gen) {                 /* a reload since: it put everything in */
        nrun = 0; run = 0; bank_src = 0; win_pend = 0;
        return;
    }
    while (nrun && left >= 32) {
        n = run[1] - done;
        if (n * 32 > left) n = left / 32;
        dma_vram((((u32)run[2] << 16) | run[3]) + (u32)done * 32, n * 32, (run[0] + done) * 32);
        done += n;
        left -= n * 32;
        if (done == run[1]) { run += 4; nrun--; done = 0; }
    }
    if (!nrun) run = 0;
    if (bank_src && left) {
        n = bank_left < left ? bank_left : left;
        dma_vram(bank_src, n, bank_at);
        bank_src += n; bank_at += n; bank_left -= n; left -= n;
        if (!bank_left) bank_src = 0;
    }
    if (win_pend && left >= 512) {
        dma_vram(RAM16(0xFFB00C) ? 0x14C8B4 : 0x14C9F2, 512, 0xFE00);
        win_pend = 0;
    }
}
