/* The collision ring written as the arcade writes its bg RAM (docs/ACCURACY.md, Fixed 65).
 *
 * The arcade's terrain map is its bg video RAM ($2800 tiles, $2C00 attributes; cell
 * (col & 31) << 5 | (~row & 31) with rows counted up from the bottom, which is the port's
 * $FF0000 ring with the port's (row ^ 15) & 31). Measured in tools/arcade/gng.py, writes to
 * $2800-$2FFF logged per frame:
 *   - camera crossing a 16 px column to the right (C = cam x / 16 after it): column C + 16;
 *     to the left: column C - 1 ($81E7 / $8457, the copy $8677);
 *   - crossing a row upwards (R = cam y / 16): row R + 16; downwards: row R - 1 ($8783 / $88A0);
 *   - a column write covers rows R - 8 .. R + 23, a row write columns C - 8 .. C + 23, each
 *     cut at the end of its 40-cell buffer (rows <= (R & ~15) + 31, columns <= (C & ~15) + 31:
 *     stage 5 at R 62, 26 rows; at C 431, 25 columns);
 *   - the stage draw before play ($726E/$80A0, also after each death) scrolls its own camera
 *     18 columns right and back, writing as above: columns C - 1 .. C + 30.
 * The world is the stages' maps side by side (stage 4's last column, 415, is the column left
 * of stage 5's start; stage 5's 463 left of stage 6's: the arcade's ring at those stage starts
 * holds exactly that, all 2,048 bytes). A cell in none of them stays the port's tile 0 /
 * attribute $C0 (the arcade has data in some of those places, e.g. walls under stage 3's floor,
 * zeros in others, e.g. under stage 5's start; neither is a floor to the probes).
 *
 * The port's streamers wrote the ring through $9386/$938E from their plane windows (cam/16 -
 * 15 .. + 16 after Fixed 37, rows cam y/16 - 5 .. + 26 after Fixed 49, a row climbing at
 * R + 10 and descending at R - 5, a column scrolling left at C - 15).
 * Those now write no ring cells; ter_update (after each camera update, $1043B4) and ter_fill
 * (in the first frame of the stage-start hold, pad.c stage_hold, after the stage init placed
 * the camera; ~0.5 frame, so the hold keeps its length) write it here. */
#include "md.h"

#define CAMX RAM16(0xFF9100)
#define CAMY RAM16(0xFF9102)
#define RING ((volatile u8 *)0xFF0000)

/* the port's map descriptors: x0, y0, w, h (cells), tile bytes, attribute bytes (column-major) */
struct map { u16 x0, y0, w, h; const u8 *t, *a; };
static const struct map *const maps[7] = {
    (const struct map *)0x18254,  /* stage 1: columns 0-223, rows 0-15 */
    (const struct map *)0x125A70, /* stage 2: 224-447, 0-31 */
    (const struct map *)0x211B20, /* stage 3: 0-223, 32-95 */
    (const struct map *)0x23CCC4, /* stage 4: 224-415, 32-47 */
    (const struct map *)0x249644, /* stage 5: 416-463, 32-111 */
    (const struct map *)0x255C74, /* stage 6: 464-495, 96-175 */
    (const struct map *)0x25E994, /* final room: 496-511, 160-175 */
};

static s16 tcx, tcy;        /* camera column / row the ring was last written for */

struct seg { s16 lo, hi; const u8 *t, *a; u16 step; };

/* a column write: rows tcy - 8 .. tcy + 23 (cut at the buffer's end) of column c */
static void column(s16 c)
{
    struct seg sg[7];
    u8 n = 0, k;
    s16 r = tcy - 8, end = tcy + 23, cut = (tcy & ~15) + 31;
    u16 base = (u16)(c & 31) << 5;
    if (end > cut)
        end = cut;
    for (k = 0; k < 7; k++) {          /* the maps holding column c, as row ranges */
        const struct map *m = maps[k];
        u16 dc = (u16)(c - m->x0);
        if (dc < m->w) {
            u16 i = dc * m->h;             /* mulu.w: all maps are under 64 KiB */
            sg[n].lo = m->y0;
            sg[n].hi = m->y0 + m->h;
            sg[n].t = m->t + i - m->y0;
            sg[n].a = m->a + i - m->y0;
            n++;
        }
    }
    for (; r <= end; r++) {
        u16 off = base | ((r ^ 15) & 31);
        for (k = 0; k < n; k++)
            if (r >= sg[k].lo && r < sg[k].hi)
                break;
        if (k < n) {
            RING[off] = sg[k].t[r];
            RING[off + 1024] = sg[k].a[r];
        } else {
            RING[off] = 0;
            RING[off + 1024] = 0xC0;
        }
    }
}

/* a row write: columns tcx - 8 .. tcx + 23 (cut at the buffer's end) of row r */
static void row(s16 r)
{
    struct seg sg[7];
    u8 n = 0, k;
    s16 c = tcx - 8, end = tcx + 23, cut = (tcx & ~15) + 31;
    u16 rb = (r ^ 15) & 31;
    if (end > cut)
        end = cut;
    for (k = 0; k < 7; k++) {          /* the maps holding row r, as column ranges */
        const struct map *m = maps[k];
        u16 dr = (u16)(r - m->y0);
        if (dr < m->h) {
            sg[n].lo = m->x0;
            sg[n].hi = m->x0 + m->w;
            sg[n].t = m->t + dr;
            sg[n].a = m->a + dr;
            sg[n].step = m->h;
            n++;
        }
    }
    for (; c <= end; c++) {
        u16 off = ((u16)(c & 31) << 5) | rb;
        for (k = 0; k < n; k++)
            if (c >= sg[k].lo && c < sg[k].hi)
                break;
        if (k < n) {
            u16 i = (u16)(c - sg[k].lo) * sg[k].step;
            RING[off] = sg[k].t[i];
            RING[off + 1024] = sg[k].a[i];
        } else {
            RING[off] = 0;
            RING[off + 1024] = 0xC0;
        }
    }
}

/* the stage draw: columns C - 1 .. C + 30 */
void ter_fill(void)
{
    s16 c;
    tcx = (s16)(CAMX >> 4);
    tcy = (s16)(CAMY >> 4);
    for (c = tcx - 1; c <= tcx + 30; c++)
        column(c);
}

/* each update after the camera moved: the column, then the row, entering at each crossing */
void ter_update(void)
{
    s16 cx = (s16)(CAMX >> 4), cy = (s16)(CAMY >> 4);
    if (cx - tcx > 4 || tcx - cx > 4 || cy - tcy > 4 || tcy - cy > 4) {
        ter_fill();                 /* a camera snap or a new stage before its entry */
        return;
    }
    while (cx > tcx) { tcx++; column(tcx + 16); }
    while (cx < tcx) { tcx--; column(tcx - 1); }
    while (cy > tcy) { tcy++; row(tcy + 16); }
    while (cy < tcy) { tcy--; row(tcy - 1); }
}
