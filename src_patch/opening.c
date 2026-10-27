/* The opening (after Start, the Home start and the second clear's restart)
 * and the stage start after it, as the arcade's. The art and the schedule are
 * mkart.py's (build/intro_art.inc, build/intro_waits.inc). */
#include "md.h"
#include "common.h"
typedef signed char s8;
#include "build/intro_art.inc"
#include "build/intro_waits.inc"

static void vram_copy(const u16 *src, u16 words, u16 tile)
{
    VDP_CTRLL = VRAM_W((u32)tile * 32);
    while (words--) VDP_DATA = *src++;
}

/* ---- the opening ---------------------------------------------------------
 * The arcade shows stage 1's graveyard after Start (Start at 800: its bg and
 * the HUD at 804, with Arthur sitting in his boxers, the princess and the
 * armour from 805 to 998), fading its bg palettes at 871 and 935 (Arthur turns
 * his head at 955, the Satan's cloak shows over it at 993 and 996), then the
 * characters on black from 999; the port's intro ($E0C) was only the black
 * part, with 6 black frames while it cleared and loaded VRAM.
 * intro_scene draws the arcade's picture (mkart.py) and loads the black part's
 * VRAM ($E0C's data: tiles $000-$550, plane B at $C000, its CRAM) while the
 * graveyard shows (the graveyard's tiles, planes and window keep out of it;
 * mkart.py), then switches on the frame after the graveyard's last: plane B to
 * $C000, the window over the whole screen (empty: plane A hidden), the CRAM.
 * The black part is $E0C's steps of plane writes ($210088), each shown on the
 * arcade's frame of the same event (intro_sched; the cloak's on and off steps
 * repeated as the arcade's blinking). The top score is the live one, as the
 * arcade's ($D0: 8 digits at row 1, columns 12-19, leading zeros blank).
 * Start skips both, from 826 and from the black part's 21st frame, as before. */
#define ISC_DARK 1                              /* black frames after Start before the graveyard */
#define AF(f) ((f) - 804)                       /* graveyard frame n of the arcade's frame f */
void intro_wait(void);                          /* bossart_glue.s: the VBlank ($EDE's wait) */
void intro_tick(void);                          /* ... then the sound ($8990) and the pads ($BF72) */

#define E0C_TILES 0x204668                      /* $E0C's data: tiles $000-$550 (0x5510 words), */
#define E0C_PLANE 0x20F088                      /* plane B (2048 words), */
#define E0C_CRAM  0x211AA0                      /* CRAM (64 words), */
#define E0C_STEPS 0x210088                      /* 155 steps */
#define E0C_NT    0x5510
#define TOP_ROW_E (0xC000 + 1 * 128 + 12 * 2)   /* the top score's 8 cells in $E0C's plane */

u8 intro_hide;                                  /* the black part ran to its end: stage_hold hides the stage */
static u16 isc_top[8];                          /* the top score's digits (10 = blank) */
static const u16 *ib_blink[2];                  /* steps 8 and 9 (the cloak on, off) */
static const u16 *ib_p;                         /* step ib_s's data */
static u16 ib_s;

/* the data of step s (s >= ib_s, or 8 or 9) */
static const u16 *step_data(u16 s)
{
    if (s < ib_s) return ib_blink[s - 8];
    while (ib_s < s) {
        u16 runs = *ib_p++;
        while (runs--) { ib_p += 2 + ib_p[1]; }
        if (++ib_s == 8 || ib_s == 9) ib_blink[ib_s - 8] = ib_p;
    }
    return ib_p;
}

static void vram_fill_plane(const u16 *src, u16 base)
{
    int r, c;
    for (r = 0; r < 28; r++) {
        VDP_CTRLL = VRAM_W(base + r * 128);
        for (c = 0; c < 32; c++) VDP_DATA = *src++;
    }
}

static void vram_zero(u16 addr, u16 words)
{
    VDP_CTRLL = VRAM_W(addr);
    while (words--) VDP_DATA = 0;
}

static void isc_sprites(const u16 (*s)[3], int n)
{
    int k;
    VDP_CTRLL = VRAM_W(0xF000);
    for (k = 0; k < n; k++) {
        VDP_DATA = s[k][0];
        VDP_DATA = 0x0500 | (k + 1 < n ? k + 1 : 0);
        VDP_DATA = s[k][2];
        VDP_DATA = s[k][1];
    }
}

static void isc_cram(const u16 *c)
{
    int k;
    VDP_CTRLL = CRAM_W(0);
    for (k = 0; k < 64; k++) VDP_DATA = c[k];
}

/* the top score as the arcade prints it */
static void top_digits(void)
{
    u32 best = PERSIST->hs[hiscore_table()][0].score, top = RAM32(0xFFC004);
    int k, lead = 1;
    if (top > best) best = top;
    for (k = 0; k < 8; k++) {
        u16 d = (best >> (28 - 4 * k)) & 15;
        if (d || k == 7) lead = 0;
        isc_top[k] = lead ? 10 : d;
    }
}

/* the black part's digit d at ISC_EDIG + d: the arcade's char with the pens
 * of $E0C's own 0 and 1 (tiles $F and $10) */
static u8 dig_map[4];
static void e0c_digit(int d)
{
    int t, y, x;
    if (d == 0)
        for (t = 0; t < 2; t++)
            for (y = 0; y < 8; y++)
                for (x = 0; x < 8; x++) {
                    u8 b = chr_digits[t][y * 2 + (x >> 2)], s = 3 - (x & 3);
                    u8 pix = RAM8(E0C_TILES + (0xF + t) * 32 + y * 4 + (x >> 1));
                    dig_map[((b >> (s + 4)) & 1) | (((b >> s) & 1) << 1)] = x & 1 ? pix & 15 : pix >> 4;
                }
    VDP_CTRLL = VRAM_W((ISC_EDIG + d) * 32);
    for (y = 0; y < 8; y++) {
        u16 w = 0;
        for (x = 0; x < 8; x++) {
            u8 b = chr_digits[d][y * 2 + (x >> 2)], s = 3 - (x & 3);
            w = (w << 4) | dig_map[((b >> (s + 4)) & 1) | (((b >> s) & 1) << 1)];
            if ((x & 3) == 3) { VDP_DATA = w; w = 0; }
        }
    }
}

/* the black part's VRAM, a piece each graveyard frame (0 when all is there):
 * the window's rows under the HUD's, the tiles, the plane with the top score
 * in it, then its digits, one a frame */
static u16 ld_at;
static u8 win_clear;
static int load_step(void)
{
    u16 n, k;
    u16 sr;
    if (ld_at >= E0C_NT + 2048 + 10) return 0;
    sr = irq_off();
    if (!win_clear) {
        vram_zero(0xD000 + 64 * 2, 32 * 30);    /* the window's other rows */
        win_clear = 1;
    } else if (ld_at < E0C_NT) {
        n = E0C_NT - ld_at < 512 ? E0C_NT - ld_at : 512;
        VDP_CTRLL = VRAM_W((u32)ld_at * 2);
        for (k = 0; k < n; k++) VDP_DATA = RAM16(E0C_TILES + (u32)(ld_at + k) * 2);
        ld_at += n;
    } else if (ld_at < E0C_NT + 2048) {
        u16 p = ld_at - E0C_NT;
        VDP_CTRLL = VRAM_W(0xC000 + p * 2);
        for (k = 0; k < 512; k++) VDP_DATA = RAM16(E0C_PLANE + (u32)(p + k) * 2);
        ld_at += 512;
        if (ld_at == E0C_NT + 2048) {
            u16 zero = RAM16(E0C_PLANE + 128 + 19 * 2) & 0xF800;   /* the 0's attributes */
            VDP_CTRLL = VRAM_W(TOP_ROW_E);
            for (k = 0; k < 8; k++) VDP_DATA = isc_top[k] == 10 ? 0 : zero | (ISC_EDIG + isc_top[k]);
        }
    } else {
        e0c_digit(ld_at - E0C_NT - 2048);
        ld_at++;
    }
    irq_restore(sr);
    return 1;
}

static void ib_regs_normal(void)
{
    vdp_reg(4, 0x06);                           /* plane B $C000 */
    vdp_reg(18, 0);                             /* no window */
}

static int start_pressed(void) { return !(RAM8(0xFF7000) & 1); }

int intro_scene(void)
{
    u16 n, k, sr;
    G_STATE = 0x494E5452;                       /* 'INTR', as $E0C */
    intro_hide = 0;
    top_digits();
    sr = irq_off();
    VDP_CTRL = 0x8104;                          /* display off, as $E0C */
    vram_zero(0, 16);                           /* tile 0 (the empty cells') */
    vram_zero(0xF000, 4);                       /* no sprites */
    vram_zero(0xFC00, 2);                       /* h scroll (whole screen) */
    for (k = 0; k < ISC_NCHUNK; k++)
        vram_copy(isc_tiles + isc_chunks[k][1] * 16, isc_chunks[k][2] * 16, isc_chunks[k][0]);
    vram_fill_plane(isc_planeb, 0xE000);
    VDP_CTRLL = VRAM_W(0xD000);                 /* the HUD's two rows (32 cells each) */
    for (k = 0; k < 64; k++) VDP_DATA = isc_planea[k];
    VDP_CTRLL = VRAM_W(0xD000 + 64 + 12 * 2);
    for (k = 0; k < 8; k++) VDP_DATA = isc_top[k] == 10 ? 0 : isc_digit[isc_top[k]];
    VDP_CTRLL = CRAM_W(0);                      /* black until the graveyard's first frame */
    for (k = 0; k < 64; k++) VDP_DATA = 0;
    VDP_CTRLL = VSRAM_W(0);
    VDP_DATA = 0; VDP_DATA = 0;
    vdp_reg(4, 0x07);                           /* plane B $E000 (plane A too) */
    vdp_reg(18, 0x02);                          /* the window: the top 2 rows */
    VDP_CTRL = 0x8164;                          /* display on (the VBlank flag is set while it's off) */
    irq_restore(sr);
    for (n = 0; n < ISC_DARK; n++) { intro_wait(); intro_tick(); }
    ld_at = 0;
    win_clear = 0;
    ib_p = (const u16 *)E0C_STEPS;
    ib_s = 0;
    for (n = 0; n < ISC_FRAMES; n++) {
        intro_wait();
        sr = irq_off();
        if (n == 0) isc_cram(isc_cram0);
        if (n == AF(805)) isc_sprites(isc_spr870, ISC_NSPR870);
        if (n == AF(871)) isc_cram(isc_cram1);
        if (n == AF(935)) isc_cram(isc_cram2);
        if (n == AF(955) || n == AF(994) || n == AF(997)) isc_sprites(isc_spr955, ISC_NSPR955);
        if (n == AF(993) || n == AF(996)) isc_sprites(isc_spr993, ISC_NSPR993);
        irq_restore(sr);
        intro_tick();
        load_step();
        if (n >= 22 && start_pressed()) { ib_regs_normal(); return 1; }
    }
    while (load_step()) ;                       /* (all there by now) */
    /* the black part */
    for (n = 0, k = 0; n < IB_FRAMES; n++) {
        intro_wait();
        sr = irq_off();
        if (n == 0) {
            isc_cram((const u16 *)E0C_CRAM);
            vram_zero(0xD000, 64);              /* the window's HUD rows */
            vram_zero(0xF000, 4);               /* no sprites */
            vdp_reg(4, 0x06);                   /* plane B $C000 */
            vdp_reg(18, 0x80);                  /* the window over the whole screen */
        } else if (n <= 8)
            vram_zero(0xE000 + (n - 1) * 512, 256);     /* plane A clear again, under the window */
        for (; k < IB_NSCHED && intro_sched[k][0] == n; k++) {
            const u16 *p = step_data(intro_sched[k][1]);
            u16 runs = *p++;
            while (runs--) {
                u16 off = *p++, cnt = *p++;
                VDP_CTRLL = VRAM_W(0xC000 + off * 2);
                while (cnt--) VDP_DATA = *p++;
            }
        }
        irq_restore(sr);
        intro_tick();
        if (n >= 20 && start_pressed()) break;
    }
    if (n == IB_FRAMES) {
        intro_wait();                           /* its last frame shows whole */
        intro_hide = 1;
    }
    ib_regs_normal();
    return 0;
}

/* After the opening the arcade shows the HUD on black (TIME, the lives and
 * the weapon; the stage's bg palettes black) until Arthur appears and the
 * stage fades in. The port's stage start shows the stage at once: from the
 * display's start at the end of stage 1's bg init ($943C, intro_show) lines
 * 1-3 are black (line 0 is the HUD's, the lives', the weapon's and Arthur's)
 * but for line 2's 9 and 15, which take line 3's: the TIME digits (plane A,
 * row 3, line 3, colours 9 and 15) are drawn with line 2 meanwhile (hide_frame,
 * each frame of the hold, which draws them; stage 1's plane B has no pixel of
 * line 2's 9 or 15 there). Lines 1-3 and the digits come back on the
 * arcade's frame (hide_vblank from sat_vblank, by the frame counter $FF7DFC).
 * intro_hold (pad.c stage_hold) returns the hold's frames to take off: the
 * picture ends 2 frames later than before. */
#define HIDE_FRAMES 30
static u16 hide_cram[48];
static u32 hide_cells[2];                       /* plane A rows 2 and 3: the cells moved to line 2 */
static u32 hide_until;
static u8 hiding;

void intro_show(void)
{
    int k;
    if (intro_hide == 1 && RAM8(0xFFC512) == 0) {
        u16 sr = irq_off();
        vdp_reg(15, 2);
        VDP_CTRLL = 0x00200020;                 /* CRAM read from entry 16 */
        for (k = 0; k < 48; k++) hide_cram[k] = VDP_DATA;
        VDP_CTRLL = CRAM_W(32);
        for (k = 16; k < 64; k++)
            VDP_DATA = k == 41 ? hide_cram[57 - 16] : k == 47 ? hide_cram[63 - 16] : 0;
        irq_restore(sr);
        hide_cells[0] = hide_cells[1] = 0;
        hiding = 1;
        hide_until = 0xFFFFFFFF;
        intro_hide = 2;
    }
    VDP_CTRL = 0x8164;                          /* display on, as $943C */
}

/* the HUD's line-3 cells in rows 2 and 3 to line 2 (back = 1: and back) */
static void hide_cells_move(int back)
{
    int r, c;
    vdp_reg(15, 2);                             /* (as $704BE sets it) */
    for (r = 0; r < 2; r++) {
        u16 row[32];
        VDP_CTRLL = VRAM_R(0xE000 + (2 + r) * 128);
        for (c = 0; c < 32; c++) row[c] = VDP_DATA;
        for (c = 0; c < 32; c++) {
            u16 w = row[c];
            if (!back && (w & 0x6000) == 0x6000) {
                hide_cells[r] |= 1UL << c;
                w &= ~0x2000;
            } else if (back && (hide_cells[r] >> c & 1) && (w & 0x6000) == 0x4000)
                w |= 0x2000;
            else continue;
            VDP_CTRLL = VRAM_W(0xE000 + (2 + r) * 128 + c * 2);
            VDP_DATA = w;
        }
    }
}

void hide_frame(void)
{
    u16 sr;
    if (!hiding) return;
    sr = irq_off();
    hide_cells_move(0);
    irq_restore(sr);
}

int intro_hold(void)
{
    if (!intro_hide) return 0;
    if (intro_hide == 2) hide_until = RAM32(0xFF7DFC) + HIDE_FRAMES;
    intro_hide = 0;
    return 2;
}

void hide_vblank(void)
{
    int k;
    u16 sr;
    if (!hiding) return;
    if ((long)(RAM32(0xFF7DFC) - hide_until) < 0) return;
    hiding = 0;
    sr = irq_off();
    VDP_CTRLL = CRAM_W(32);
    for (k = 0; k < 48; k++) VDP_DATA = hide_cram[k];
    hide_cells_move(1);
    irq_restore(sr);
}
