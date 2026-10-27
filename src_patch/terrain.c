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
 * The cells come from one world, the arcade's own map (mkworld.py -> build/world.inc, gg5: 32 x 16
 * screens of 16 x 16 cells, 512 columns by 256 rows). The port's seven stage maps are that world's
 * cells byte for byte (all 34,816), so the stages sit side by side in it (stage 4's last column,
 * 415, is the column left of stage 5's start; stage 5's 463 left of stage 6's: the arcade's ring
 * at those stage starts holds exactly that, all 2,048 bytes); the cells in none of the port's maps
 * (below stage 1-2's row 0, under stage 5's start, around stage 3's floor, ...) were the port's
 * tile 0 / attribute $C0 until Fixed 80 and are now the arcade's too.
 *
 * The port's streamers wrote the ring through $9386/$938E from their plane windows (cam/16 -
 * 15 .. + 16 after Fixed 37, rows cam y/16 - 5 .. + 26 after Fixed 49, a row climbing at
 * R + 10 and descending at R - 5, a column scrolling left at C - 15).
 * Those now write no ring cells; ter_update (after each camera update, $1043B4) and ter_fill
 * (in the first frame of the stage-start hold, pad.c stage_hold, after the stage init placed
 * the camera; ~0.5 frame, so the hold keeps its length) write it here. */
#include "md.h"

/* the world tables go in the data section at $350000 (link.ld), not the code blob */
#define WORLD __attribute__((section(".intro.world")))
#include "build/world.inc"

#define CAMX RAM16(0xFF9100)
#define CAMY RAM16(0xFF9102)
#define RING ((volatile u8 *)0xFF0000)

static s16 tcx, tcy;        /* camera column / row the ring was last written for */

/* The world (mkworld.py): w_map[screen row << 5 | screen column] is a screen's id, w_scr[id * 64 +
 * block column * 8 + block row] its 2 x 2-cell blocks (bottom first), w_blk + w_base[id] + 8 x block
 * the block: tiles at + (column & 1) * 2 + (row & 1), attributes 4 on. Columns and rows wrap as the
 * arcade's screen pointer does (32 screens across, 16 up). The screen and the block are looked up
 * once per 16 and per 2 cells along the write. */

/* a column write: rows tcy - 8 .. tcy + 23 (cut at the buffer's end) of column c */
static void column(s16 c)
{
    s16 r = tcy - 8, end = tcy + 23, cut = (tcy & ~15) + 31;
    u16 base = (u16)(c & 31) << 5;
    u16 sx = (u16)c >> 4 & 31;
    const u8 *scr = 0, *blk = 0, *b = 0;
    if (end > cut)
        end = cut;
    for (; r <= end; r++) {
        u16 off = base | ((r ^ 15) & 31);
        if (!scr || !(r & 15)) {
            u8 sid = w_map[((u16)r >> 4 & 15) << 5 | sx];
            scr = w_scr + (u16)sid * 64 + ((u16)c >> 1 & 7) * 8;
            blk = w_blk + w_base[sid] + (c & 1) * 2;
            b = 0;
        }
        if (!b || !(r & 1))
            b = blk + (u16)scr[(u16)r >> 1 & 7] * 8;
        RING[off] = b[r & 1];
        RING[off + 1024] = b[(r & 1) + 4];
    }
}

/* a row write: columns tcx - 8 .. tcx + 23 (cut at the buffer's end) of row r */
static void row(s16 r)
{
    s16 c = tcx - 8, end = tcx + 23, cut = (tcx & ~15) + 31;
    u16 rb = (r ^ 15) & 31;
    u16 sy = ((u16)r >> 4 & 15) << 5;
    const u8 *scr = 0, *blk = 0, *b = 0;
    if (end > cut)
        end = cut;
    for (; c <= end; c++) {
        u16 off = ((u16)(c & 31) << 5) | rb;
        if (!scr || !(c & 15)) {
            u8 sid = w_map[sy | ((u16)c >> 4 & 31)];
            scr = w_scr + (u16)sid * 64 + ((u16)r >> 1 & 7);
            blk = w_blk + w_base[sid] + (r & 1);
            b = 0;
        }
        if (!b || !(c & 1))
            b = blk + (u16)scr[((u16)c >> 1 & 7) * 8] * 8;
        RING[off] = b[(c & 1) * 2];
        RING[off + 1024] = b[(c & 1) * 2 + 4];
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
