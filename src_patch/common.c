/* Shared helpers: vsync, pads, text in the arcade font. */
#include "md.h"
#include "common.h"
#include "build/font.inc"   /* font_tiles[]: ASCII $20-$7F, generated from rom/gg1.bin */

static u8 disp_on;

/* With the display disabled the VB status bit stays set, so wait about one
 * frame by time instead. */
extern u8 menu_frames;               /* glue.s: the random source counts menu time too */

void vsync(void)
{
    menu_frames++;
    if (!disp_on) {
        volatile u16 n = 9000;
        while (n--) ;
        return;
    }
    while (VDP_CTRL & 8) ;
    while (!(VDP_CTRL & 8)) ;
}

/* 3-button read. Returns BTN_* bits, 1 = pressed. */
u16 pad_read(int port)
{
    volatile u8 *d = (volatile u8 *)(0xA10003 + port * 2);
    u8 hi, lo;
    *d = 0x40; nop(); nop(); nop(); nop();
    hi = *d;                        /* TH=1: C B R L D U */
    *d = 0x00; nop(); nop(); nop(); nop();
    lo = *d;                        /* TH=0: S A 0 0 D U */
    *d = 0x40;
    return (u16)(~((hi & 0x3F) | ((lo & 0x30) << 2)) & 0xFF);
}

void pads_init(void)
{
    RAM8(0xA10009) = 0x40;
    RAM8(0xA1000B) = 0x40;
    RAM8(0xA10003) = 0x40;
    RAM8(0xA10005) = 0x40;
}

/* ---- screen setup for menus ---------------------------------------- */

static void vram_fill(u16 addr, u16 words, u16 v)
{
    VDP_CTRLL = VRAM_W(addr);
    while (words--) VDP_DATA = v;
}

static void vram_copy(u16 addr, const u16 *src, u16 words)
{
    VDP_CTRLL = VRAM_W(addr);
    while (words--) VDP_DATA = *src++;
}

static const u16 menu_pal[16 * 3] = {
    /* line 1: normal text */
    0x0000, 0x0EEE, 0x0E86, 0x0222, 0,0,0,0, 0,0,0,0, 0,0,0,0,
    /* line 2: selected text */
    0x0000, 0x00EE, 0x006E, 0x0222, 0,0,0,0, 0,0,0,0, 0,0,0,0,
    /* line 3: dim text */
    0x0000, 0x0888, 0x0666, 0x0222, 0,0,0,0, 0,0,0,0, 0,0,0,0,
};

/* Title art straight from the game's title loader ($B88-$BCA). */
#define TITLE_TILES  ((const u16 *)0x202408)   /* 2288 words -> VRAM $0000 */
#define TITLE_MAP    ((const u16 *)0x2035E8)   /* 64x32 plane map */
#define TITLE_PAL    ((const u16 *)0x2045E8)   /* 64 words */

void screen_init(void)
{
    int i;
    __asm__ volatile ("move.w #0x2700,%sr");
    vdp_reg(1, 0x04);               /* display off */
    disp_on = 0;
    vdp_reg(0, 0x04);
    vdp_reg(2, 0x38);               /* plane A $E000 */
    vdp_reg(3, 0x34);               /* window  $D000 */
    vdp_reg(4, 0x06);               /* plane B $C000 */
    vdp_reg(5, 0x78);               /* SAT     $F000 */
    vdp_reg(7, 0x00);
    vdp_reg(10, 0xFF);
    vdp_reg(11, 0x00);
    vdp_reg(12, 0x00);              /* H32, as the game */
    vdp_reg(13, 0x3F);              /* hscroll $FC00 */
    vdp_reg(15, 0x02);
    vdp_reg(16, 0x01);              /* 64x32 */
    vdp_reg(17, 0x00);
    vdp_reg(18, 0x00);
    vram_fill(0xC000, 0x2000, 0);   /* planes B, W, A */
    vram_fill(0xF000, 0x0400, 0);   /* SAT + hscroll */
    VDP_CTRLL = VSRAM_W(0); VDP_DATAL = 0;

    vram_copy(0x0000, TITLE_TILES, 2288);
    VDP_CTRLL = CRAM_W(0);
    for (i = 0; i < 16; i++) VDP_DATA = TITLE_PAL[i];
    for (i = 0; i < 16 * 3; i++) VDP_DATA = menu_pal[i];
    vram_copy(FONT_VRAM, font_tiles, sizeof(font_tiles) / 2);
}

void draw_logo(int row)
{
    int y;
    for (y = 0; y < 3; y++)
        vram_copy(0xC000 + (row + y) * 128, TITLE_MAP + (6 + y) * 64, 32);
}

void display_on(void) { vdp_reg(1, 0x44); disp_on = 1; }
void vsync_reset_display(void) { disp_on = 0; }

void text(int x, int y, const char *s, int pal)
{
    VDP_CTRLL = VRAM_W(0xE000 + (y * 64 + x) * 2);
    while (*s) {
        u8 c = (u8)*s++;
        VDP_DATA = c < 0x20 || c > 0x7F ? 0 :
            (u16)(0x8000 | (pal << 13) | (FONT_TILE + c - 0x20));
    }
}

void text_center(int y, const char *s, int pal)
{
    int n = 0;
    while (s[n]) n++;
    text((32 - n) / 2, y, s, pal);
}

void clear_rows(int y0, int y1)
{
    for (; y0 <= y1; y0++) vram_fill(0xE000 + y0 * 128, 32, 0);
}

void num2(char *dst, int v)
{
    dst[0] = '0' + (v / 10) % 10;
    dst[1] = '0' + v % 10;
    dst[2] = 0;
}

/* 8 BCD digits, leading zeros blanked (keeps the last digit). */
void bcd_str(char *dst, u32 bcd)
{
    int i, lead = 1;
    for (i = 0; i < 8; i++) {
        int d = (bcd >> (28 - i * 4)) & 15;
        if (d || i == 7) lead = 0;
        dst[i] = lead ? ' ' : '0' + d;
    }
    dst[8] = 0;
}
