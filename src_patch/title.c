/* English / Japanese (Makaimura) title logo: boot menu, title screen, attract overlay. */
#include "md.h"
#include "common.h"
#include "build/jp.inc"

#define JP_TILE 0x200               /* free VRAM on the menu and title screens ($200-$286) */
#define TITLE_PAL ((const u16 *)0x2045E8)
#define TITLE_JP_ROW 3              /* rows 3-9, above the title's text */

void dma_vram(u32 src, u16 bytes, u16 vram);

static u16 title_pal[64];
/* the arcade's char palette 7 (red, light grey, blue) in pens 4-6 of the
 * logo's line; the menus' text has pens 1-3 */
const u16 jp_colors[3] = { 0x000C, 0x0CCC, 0x0A40 };

int title_jp(void)
{
    return PERSIST->magic == PERSIST_MAGIC && PERSIST->title_jp;
}

/* Draws the 21x7 logo on plane B at (col 5, row) with palette line `pal`. */
void draw_jp_logo(int row, int pal)
{
    int r, c;
    const u16 *t = jp_tiles_menu, *m = jp_map_menu;
    VDP_CTRLL = VRAM_W(JP_TILE * 32);
    for (r = 0; r < (int)(sizeof(jp_tiles_menu) / 2); r++) VDP_DATA = *t++;
    for (r = 0; r < JP_H; r++) {
        VDP_CTRLL = VRAM_W(0xC000 + (row + r) * 128 + 5 * 2);
        for (c = 0; c < JP_W; c++, m++)
            VDP_DATA = *m == 0xFFFF ? 0 : (u16)((pal << 13) | (*m + JP_TILE));
    }
}

/* Called from the title loader ($BB8, in place of `lea $2045E8,a0`).
 * Returns the palette the loader should copy to CRAM. */
u32 title_logo_fix(void)
{
    int i, r;
    if (!title_jp()) return (u32)TITLE_PAL;
    for (r = 5; r <= 8; r++) {                  /* remove the English logo */
        VDP_CTRLL = VRAM_W(0xC000 + r * 128);
        for (i = 0; i < 32; i++) VDP_DATA = 0;
    }
    draw_jp_logo(TITLE_JP_ROW, 1);
    for (i = 0; i < 64; i++) title_pal[i] = TITLE_PAL[i];
    for (i = 0; i < 3; i++) title_pal[16 + 4 + i] = jp_colors[i];
    return (u32)title_pal;
}

/* Attract overlay sources (see glue.s ovl_* stubs): the three uploads of
 * the overlay routine, then (ovl_extra) the 67 tiles beyond its 65. */
const u16 *const jp_ovl_chunk[3] = {
    jp_tiles_game, jp_tiles_game + 19 * 16, jp_tiles_game + 55 * 16,
};
const u16 *const jp_ovl_map_ptr = jp_ovl_map;

void jp_ovl_extra_up(void)
{
    const u16 *t = jp_tiles_game + JP_OVL_EXTRA * 16;
    int i;
    for (i = 0; i < 3; i++) {
        dma_vram((u32)t, jp_ovl_extra[i][1] * 32, jp_ovl_extra[i][0] * 32);
        t += jp_ovl_extra[i][1] * 16;
    }
}
