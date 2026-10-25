/* English / Japanese (Makaimura) title logo: boot menu, title screen, attract overlay. */
#include "md.h"
#include "common.h"
#include "build/jp.inc"

#define JP_TILE 0x200               /* free VRAM on the menu and title screens */
#define TITLE_PAL ((const u16 *)0x2045E8)

static u16 title_pal[64];
static const u16 jp_colors[4] = { 0x0000, 0x0EEE, 0x0E88, 0x0026 };

int title_jp(void)
{
    return PERSIST->magic == PERSIST_MAGIC && PERSIST->title_jp;
}

/* Draws the 16x4 logo on plane B at (col 8, row) with palette line `pal`. */
void draw_jp_logo(int row, int pal)
{
    int r, c;
    const u16 *t = jp_tiles_menu;
    VDP_CTRLL = VRAM_W(JP_TILE * 32);
    for (r = 0; r < (int)(sizeof(jp_tiles_menu) / 2); r++) VDP_DATA = *t++;
    for (r = 0; r < 4; r++) {
        VDP_CTRLL = VRAM_W(0xC000 + (row + r) * 128 + 8 * 2);
        for (c = 0; c < 16; c++)
            VDP_DATA = (u16)((pal << 13) | (JP_TILE + r * 16 + c));
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
    draw_jp_logo(5, 1);
    for (i = 0; i < 64; i++) title_pal[i] = TITLE_PAL[i];
    for (i = 1; i < 4; i++) title_pal[16 + i] = jp_colors[i];
    return (u32)title_pal;
}

/* Attract overlay sources (see glue.s ovl_* stubs). */
const u16 *const jp_ovl_chunk[3] = {
    jp_tiles_game, jp_tiles_game + 19 * 16, jp_tiles_game + 55 * 16,
};
const u16 *const jp_ovl_map_ptr = jp_ovl_map;
