/* Cold-boot intros, as in the Black Tiger port: the SEGA logo (Revenge of
 * Shinobi, rolling sheen) with the Sonic 1 "SE-GA" chant, then the CAPCOM
 * logo with its FM jingle (SF2' SCE). Art, palettes, chant and jingle come
 * from build/intro.inc (mkintro.py); without the kits the intros are skipped.
 * Start skips the rest. On PAL every 5th frame steps twice, so both logos
 * keep their 60 Hz timing. */
#include "md.h"
#include "common.h"
/* The logos, chant and jingle go in their own section, linked at $350000
 * (the padding past the original image) to keep the code blob small. */
#define INTRO_DATA __attribute__((section(".intro")))
#include "build/intro.inc"

void sound_stop(void);
void vsync_reset_display(void);

#ifdef INTRO_HAVE

#define LOGO_TILE  0x200                /* VRAM $4000, above the font */
#define SEGA_TICKS 210
#define CHANT_TICK 24
#define CAPCOM_TICKS 360
#define Z80_RAM    ((volatile u8 *)0xA00000)
#define Z80_BUS    RAM16(0xA11100)
#define Z80_RESET  RAM16(0xA11200)
#define YM(p)      RAM8(0xA04000 + (p) * 2)
#define YMD(p)     RAM8(0xA04001 + (p) * 2)
#define IS_PAL     (RAM8(0xA10001) & 0x40)

#define GAME_Z80   ((const u8 *)0x202380)   /* the game's Z80 program, loaded at $238 */
#define GAME_Z80_N 136

static u8 skipped;

static void set_pal(const u16 *c)
{
    int i;
    VDP_CTRLL = CRAM_W(0);
    for (i = 0; i < 16; i++) VDP_DATA = c[i];
}

/* Blank screen, black palette line 0, logo tiles loaded, w x h map at (x,y). */
static void logo_screen(const u32 *tiles, int ntiles, int first, int w, int h, int x, int y)
{
    static const u16 black[16];
    int i;
    screen_init();
    set_pal(black);
    VDP_CTRLL = VRAM_W(LOGO_TILE * 32);
    for (i = 0; i < ntiles * 8; i++) VDP_DATAL = tiles[i];
    for (i = 0; i < w * h; i++) {
        VDP_CTRLL = VRAM_W(0xE000 + ((y + i / w) * 64 + x + i % w) * 2);
        VDP_DATA = LOGO_TILE + first + i;
    }
}

/* Waits a frame; returns how many ticks to advance (0 = Start, skip). */
static int frame(int *phase)
{
    vsync();
    if (pad_read(0) & BTN_START) { skipped = 1; return 0; }
    if (IS_PAL && ++*phase == 5) { *phase = 0; return 2; }
    return 1;
}

/* ---- Z80: bus and reset ------------------------------------------------ */

static void z80_hold(void)
{
    Z80_BUS = 0x100;
    while (Z80_BUS & 0x100) ;
}

/* Copies a program to Z80 RAM and runs it from 0. Z80 RAM is only reachable
 * with the bus held and the Z80 out of reset; the reset pulse afterwards
 * also resets the YM. */
static void z80_run(const u8 *code, int n)
{
    int i;
    Z80_RESET = 0x100;
    z80_hold();
    for (i = 0; i < n; i++) Z80_RAM[i] = code[i];
    Z80_RESET = 0;
    for (i = 0; i < 32; i++) nop();
    Z80_RESET = 0x100;
    Z80_BUS = 0;
}

/* The chant: the Z80 streams it from a 32 KiB ROM bank to the YM2612 DAC.
 * 224 Z80 cycles per sample (incl. ~3 bank wait states) = 16.0 kHz, the
 * rate Sonic 1's driver plays it at. */
static void chant_start(void)
{
    u32 a = (u32)sega_chant;
    u16 win = 0x8000 | (a & 0x7FFF), n = sizeof(sega_chant);
    u8 bank = a >> 15;
    u8 code[] = {
        0xF3,                       /*      di                         */
        0x21, 0x00, 0x60,           /*      ld hl,$6000   bank register */
        0x3E, bank,                 /*      ld a,bank                  */
        0x06, 0x08,                 /*      ld b,8                     */
        0x77,                       /* b1:  ld (hl),a     bits 15..22  */
        0x0F,                       /*      rrca                       */
        0x10, 0xFC,                 /*      djnz b1                    */
        0xAF,                       /*      xor a                      */
        0x77,                       /*      ld (hl),a     bit 23       */
        0x3E, 0x2B, 0x32, 0x00, 0x40, /*    ld a,$2B : ld ($4000),a    */
        0x3E, 0x80, 0x32, 0x01, 0x40, /*    ld a,$80 : ld ($4001),a  DAC on */
        0x3E, 0x2A, 0x32, 0x00, 0x40, /*    ld a,$2A : ld ($4000),a  DAC data */
        0x21, win & 0xFF, win >> 8, /*      ld hl,sample               */
        0x01, n & 0xFF, n >> 8,     /*      ld bc,length               */
        0x7E,                       /* lp:  ld a,(hl)          7       */
        0x32, 0x01, 0x40,           /*      ld ($4001),a      13       */
        0x23,                       /*      inc hl             6       */
        0x0B,                       /*      dec bc             6       */
        0x78,                       /*      ld a,b             4       */
        0xB1,                       /*      or c               4       */
        0x28, 0x07,                 /*      jr z,end           7       */
        0x16, 0x0A,                 /*      ld d,10            7       */
        0x15,                       /* dl:  dec d              4       */
        0x20, 0xFD,                 /*      jr nz,dl          12/7     */
        0x18, 0xEF,                 /*      jr lp             12       */
        0x3E, 0x2B, 0x32, 0x00, 0x40, /* end: DAC off                  */
        0xAF, 0x32, 0x01, 0x40,
        0x18, 0xFE,                 /*      jr $                       */
    };
    z80_run(code, sizeof(code));
}

/* ---- SEGA: entries 2..10 slide through a 20-step wave, a step every 4 ticks */

static void sega_logo(void)
{
    u16 cram[16];
    int t = 0, e, step = 0, phase = 0, n = 1;
    logo_screen(sega_tiles, 49, 1, 12, 4, 10, 10);
    for (e = 0; e < 16; e++) cram[e] = sega_pal[e];
    for (e = 2; e <= 10; e++) cram[e] = sega_wave[(20 - (e - 2)) % 20];
    set_pal(cram);
    display_on();
    while (t < SEGA_TICKS && (n = frame(&phase))) {
        while (n-- && t < SEGA_TICKS) {
            if (++t % 4 == 0) {
                step = (step + 1) % 20;
                for (e = 2; e <= 10; e++) cram[e] = sega_wave[(step + 20 - (e - 2)) % 20];
            }
            if (t == CHANT_TICK) chant_start();
        }
        set_pal(cram);
    }
}

/* ---- CAPCOM: fade in, glint, fade out, with the FM jingle replayed ------- */

static void ym_write(int part, int reg, int val)
{
    while (YM(0) & 0x80) ;
    YM(part) = reg;
    while (YM(0) & 0x80) ;
    YMD(part) = val;
}

/* per channel max(0, c - 2k), the game's fade */
static void capcom_fade(u16 *cram, int k)
{
    int i, s = k * 2;
    for (i = 0; i < 16; i++) {
        int c = capcom_pal[i], b = (c >> 8) & 15, g = (c >> 4) & 15, r = c & 15;
        b = b > s ? b - s : 0; g = g > s ? g - s : 0; r = r > s ? r - s : 0;
        cram[i] = (b << 8) | (g << 4) | r;
    }
}

static void capcom_tick(u16 *cram, int t, int *ev)
{
    int i;
    while (*ev < (int)sizeof(capcom_ev) / 4 && capcom_ev[*ev * 4] == t - 1) {
        const u8 *e = &capcom_ev[*ev * 4];
        ym_write(e[1], e[2], e[3]);
        ++*ev;
    }
    if (t >= 34 && t <= 58 && ((t - 34) & 3) == 0) capcom_fade(cram, 6 - ((t - 34) >> 2));
    for (i = 0; i < 6; i++)
        if (t == capcom_glint_t[i])
            { int j; for (j = 0; j < 16; j++) cram[j] = capcom_glint[i * 16 + j]; }
    if (t >= 333 && t <= 357 && ((t - 333) & 3) == 0) capcom_fade(cram, 1 + ((t - 333) >> 2));
}

static void capcom_logo(void)
{
    static const u8 idle[] = { 0xF3, 0x18, 0xFE };   /* di : jr $ */
    u16 cram[16];
    int t = 0, i, ev = 0, phase = 0, n = 1;
    logo_screen(capcom_tiles, 36, 0, 12, 3, 10, 12);
    for (i = 0; i < 16; i++) cram[i] = 0;

    z80_run(idle, sizeof(idle));        /* chant off, YM reset */
    z80_hold();                         /* the 68k reaches the YM through the Z80 bus */
    for (i = 0; i < (int)sizeof(capcom_setup); i += 3)
        ym_write(capcom_setup[i], capcom_setup[i + 1], capcom_setup[i + 2]);
    display_on();
    while (t < CAPCOM_TICKS && (n = frame(&phase))) {
        while (n-- && t < CAPCOM_TICKS) capcom_tick(cram, ++t, &ev);
        set_pal(cram);
    }
}

void boot_intros(void)
{
    int i;
    skipped = 0;
    sega_logo();
    if (!skipped) capcom_logo();
    z80_run(GAME_Z80, GAME_Z80_N);      /* the game loads it only at power-on */
    sound_stop();                       /* its sound init resets the Z80 and YM again */
    while (pad_read(0) & BTN_START) vsync();   /* a skip can't pick a menu item */
    vdp_reg(1, 0x04);
    vsync_reset_display();
    VDP_CTRLL = VRAM_W(0xC000);         /* the game's splash only draws its own cells */
    for (i = 0; i < 0x2000; i++) VDP_DATA = 0;
}

#else
void boot_intros(void) { }
#endif
