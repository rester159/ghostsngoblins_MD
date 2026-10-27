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
 * VRAM (its sprite tiles at $001-$550, an empty plane B at $C000) while the
 * graveyard shows (the graveyard's tiles, planes and window keep out of it;
 * mkart.py), then switches on the frame after the graveyard's last: plane B to
 * $C000, the window over the whole screen (the HUD's rows, the rest empty:
 * plane A hidden), the CRAM. The black part is the arcade's sprites (Satan,
 * princess, Arthur), its own list of every frame converted by mkart.py, so
 * every picture change is the arcade's (the swoop, the fall, getting up and
 * the walk change every frame there). The top score is the live one, as the
 * arcade's ($D0: 8 digits at row 1, columns 12-19, leading zeros blank).
 * Start skips both, from 826 and from the black part's 21st frame, as before.
 * After the second clear (end_restart) the arcade's graveyard comes 3 frames
 * after the last text's, its bg alone for 5 frames, and runs 3 frames shorter:
 * the same here (isc_ev). */
#define ISC_DARK 1                              /* black frames after Start before the graveyard */
#define AF(f) ((f) - 804)                       /* graveyard frame n of the arcade's frame f */
void intro_wait(void);                          /* bossart_glue.s: the VBlank ($EDE's wait) */
void intro_tick(void);                          /* ... then the sound ($8990) and the pads ($BF72) */

u8 intro_hide;                                  /* the black part ran to its end: stage_hold hides the stage */
u8 intro_after_end;                             /* ending_glue.s end_restart: after the second clear */
static u8 after_end;
/* the graveyard's events (frame n from its first): the sprites, the two
 * fades, Arthur's head, Start's first frame, the cloak on, off, on, off, the
 * black part. After Start (arcade frames, Start at 800: the bg at 804) and
 * after the second clear (the arcade's from the last text's end R: the bg at
 * R + 3 (here R + 2), the sprites at R + 8,
 * the fades at R + 68 and R + 132, the head at R + 153, the cloak at R + 191
 * and R + 193, the black part at R + 196). */
static const u16 isc_ev[2][10] = {
    { AF(805), AF(871), AF(935), AF(955), AF(826), AF(993), AF(994), AF(996), AF(997), AF(999) },
    { 5, 65, 129, 150, 22, 188, 189, 190, 191, 193 } };
#define HIDE_FRAMES 29
#define HOLD_CUT 13                             /* the hold's frames taken off after the opening (its load is longer, display on) */
static u16 hide_cram[48];
static u32 hide_cells[2];                       /* plane A rows 2 and 3: the cells moved to line 2 */
static u32 hide_until;
static u8 hiding;
static void hud_load_step(void);
static void hud_show(void);
static u16 isc_top[8];                          /* the top score's digits (10 = blank) */
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

/* the black part's VRAM, a piece each graveyard frame (0 when all is there):
 * the window's rows under the HUD's, an empty plane B at $C000, the sprite
 * tiles (mkart.py: the arcade's sprites of every frame of it) */
#define LD_PLANE 2048
static u16 ld_at;
static u8 win_clear;
static int load_step(void)
{
    u16 n, k;
    u16 sr;
    if (ld_at >= LD_PLANE + IB_NTILES * 16) return 0;
    sr = irq_off();
    if (win_clear < 2) {                        /* the window's other rows, in 2 */
        vram_zero(0xD000 + 64 * 2 + win_clear * 32 * 30, 32 * 15);
        win_clear++;
    } else if (ld_at < LD_PLANE) {
        vram_zero(0xC000 + ld_at * 2, 512);
        ld_at += 512;
    } else {
        u16 at = ld_at - LD_PLANE;
        n = IB_NTILES * 16 - at < 512 ? IB_NTILES * 16 - at : 512;
        VDP_CTRLL = VRAM_W((u32)IB_TILE0 * 32 + at * 2);
        for (k = 0; k < n; k++) VDP_DATA = ib_tiles[at + k];
        ld_at += n;
    }
    irq_restore(sr);
    return 1;
}

/* the black part's frame n: the arcade's sprite list of its frame 999 + n */
static void ib_sprites(int n)
{
    const u16 *p = ib_lists + ib_frame[n];
    u16 k, cnt = *p++;
    VDP_CTRLL = VRAM_W(0xF000);
    if (!cnt) { VDP_DATA = 0; VDP_DATA = 0; return; }
    for (k = 0; k < cnt; k++, p += 3) {
        VDP_DATA = p[0];
        VDP_DATA = 0x0500 | (k + 1 < cnt ? k + 1 : 0);
        VDP_DATA = p[2];
        VDP_DATA = p[1];
    }
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
    const u16 *ev;
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
    after_end = intro_after_end ? 1 : 0;
    intro_after_end = 0;
    for (n = after_end ? 1 : 0; n < ISC_DARK; n++) { intro_wait(); intro_tick(); }
    ld_at = 0;
    win_clear = 0;
    ev = isc_ev[after_end];
    for (n = 0; n < ev[9]; n++) {
        intro_wait();
        sr = irq_off();
        if (n == 0) isc_cram(isc_cram0);
        if (n == ev[0]) isc_sprites(isc_spr870, ISC_NSPR870);
        if (n == ev[1]) isc_cram(isc_cram1);
        if (n == ev[2]) isc_cram(isc_cram2);
        if (n == ev[3] || n == ev[6] || n == ev[8]) isc_sprites(isc_spr955, ISC_NSPR955);
        if (n == ev[5] || n == ev[7]) isc_sprites(isc_spr993, ISC_NSPR993);
        irq_restore(sr);
        intro_tick();
        load_step();
        if (n >= ev[4] && start_pressed()) { ib_regs_normal(); return 1; }
    }
    while (load_step()) ;                       /* (all there by now) */
    /* the black part */
    for (n = 0; n < IB_FRAMES; n++) {
        intro_wait();
        sr = irq_off();
        if (n == 0) {
            isc_cram(ib_cram);
            vdp_reg(4, 0x06);                   /* plane B $C000 (empty) */
            vdp_reg(18, 0x80);                  /* the window (the HUD's rows) over the whole screen */
        } else if (n <= 8)
            vram_zero(0xE000 + (n - 1) * 512, 256);     /* plane A clear again, under the window */
        else if (n == 9)
            vdp_reg(18, 0x02);                  /* plane A empty: the window back to the HUD's rows */
        if (n == 0 || ib_frame[n] != ib_frame[n - 1]) ib_sprites(n);
        irq_restore(sr);
        intro_tick();
        if (n >= 10) hud_load_step();
        if (n >= 20 && start_pressed()) break;
    }
    if (n == IB_FRAMES) {
        if (after_end) { intro_wait(); intro_tick(); }  /* (the arcade's ends a frame later there) */
        intro_wait();                           /* the HUD over the last picture */
        sr = irq_off();
        hud_show();
        irq_restore(sr);
        intro_tick();
        intro_wait();                           /* the HUD alone */
        vram_zero(0xF000, 4);
        intro_hide = 1;
        return 0;
    }
    ib_regs_normal();
    return 0;
}

/* After the opening the arcade shows the HUD on black (TIME, the lives and
 * the weapon under the top rows; the stage's bg palettes black) from the
 * picture's last frame (1319, over its sprites) until Arthur appears and the
 * stage fades in; the port's stage start ($2CC) turned the display off while
 * it cleared VRAM and loaded stage 1 (13 black frames) and showed its own HUD
 * after it. Now the HUD is on plane A from 1319 (hud_show: the arcade's chars
 * in the port's colours, mkart.py; its tiles where the stage start writes
 * nothing) with lines 1-3 black (line 0 stage 1's, ROM $13FE2, and line 2's 9
 * and 15 line 3's for the TIME digits), and the stage start keeps the display
 * on: its VRAM clear spares the HUD and the areas its loads write whole
 * (stage_clear, $2E2), the CRAM it loads is hidden as it lands (intro_cram,
 * $3C6), plane B shows plane A's table until its bg init is done (intro_show,
 * $943C; its display off at $940A skipped: bg_off), so the port's own HUD
 * replaces this one with the same picture when it is drawn. */
static u16 hud_at;
static void hud_load_step(void)
{
    u16 n, k, sr;
    if (hud_at >= HUD_NTILES) return;
    sr = irq_off();
    for (n = 0; n < 32 && hud_at < HUD_NTILES; n++, hud_at++) {
        VDP_CTRLL = VRAM_W((u32)hud_vtile[hud_at] * 32);
        for (k = 0; k < 16; k++) VDP_DATA = hud_tiles[hud_at * 16 + k];
    }
    irq_restore(sr);
}

#define STAGE1_CRAM 0x13FE2                     /* the CRAM stage 1's start loads */
static void hud_cells(int lance)
{
    u16 k;
    for (k = 0; k < HUD_NCELLS; k++) {
        VDP_CTRLL = VRAM_W(0xE000 + hud_cell[k][0]);
        VDP_DATA = hud_cell[k][1];
    }
    for (k = 0; k < HUD_NLANCE && lance; k++) {
        VDP_CTRLL = VRAM_W(0xE000 + hud_cell[hud_lance[k][0]][0]);
        VDP_DATA = hud_lance[k][1];
    }
}

static void hud_show(void)
{
    u16 k;
    while (hud_at < HUD_NTILES) hud_load_step();
    vdp_reg(18, 0);                             /* no window: plane A (empty but for the HUD) */
    vdp_reg(4, 0x07);                           /* plane B shows plane A's table while stage 1 loads */
    VDP_CTRLL = CRAM_W(0);
    for (k = 0; k < 64; k++)
        VDP_DATA = k < 16 ? RAM16(STAGE1_CRAM + k * 2) : k == 41 ? RAM16(STAGE1_CRAM + 57 * 2)
                 : k == 47 ? RAM16(STAGE1_CRAM + 63 * 2) : 0;
    hud_cells(1);
    VDP_CTRLL = VRAM_W(0xE000 + 1 * 128 + 12 * 2);
    for (k = 0; k < 8; k++) VDP_DATA = isc_top[k] == 10 ? 0 : hud_digit[isc_top[k]];
    VDP_CTRLL = VRAM_W(0xF000);                 /* the last picture's sprites in line 0 */
    for (k = 0; k < HUD_NLAST; k++) {
        VDP_DATA = hud_last[k][0];
        VDP_DATA = 0x0500 | (k + 1 < HUD_NLAST ? k + 1 : 0);
        VDP_DATA = hud_last[k][2];
        VDP_DATA = hud_last[k][1];
    }
}

static void vblank_start(void)
{
    while (VDP_CTRL & 8) ;
    while (!(VDP_CTRL & 8)) ;
}

/* $2E2 (display off and the 64 KiB VRAM clear of the game start): after the
 * opening the display stays on, the lance takes its colours on the arcade's
 * frame (1321), and the clear spares the HUD's cells and tiles and what the
 * loads after it write whole ($0020-$49A0, $4A00-$5800, $6000-$A920,
 * $AF00-$BE80, plane B $C000-$CFFF) */
u8 load_ticks, load_vb;                         /* bossart_glue.s b12_tick: the sound's tick in the load */
u8 music_early;                                 /* bossart_glue.s music_hook */
void music_now(void);
void load_tick(void);
static void zero_range(u16 a, u16 b)
{
    VDP_CTRLL = VRAM_W(a);
    for (; a < b; a += 2) {
        VDP_DATA = 0;
        if (!(a & 127)) load_tick();
    }
}

void stage_clear(void)
{
    static const u16 zr[][2] = { {0x0000, 0x0020}, {0x49A0, 0x4A00}, {0x5800, 0x6000}, {0xA920, 0xAF00},
                                 {0xBE80, 0xC000}, {0xD000, 0xD200}, {0xD900, 0xDA00}, {0xDB80, 0xE000} };
    u16 k, r;
    if (intro_hide != 1) {
        VDP_CTRL = 0x8104;
        VDP_CTRLL = VRAM_W(0);
        for (k = 0; k < 0x4000; k++) { VDP_DATAL = 0; }
        return;
    }
    vblank_start();
    hud_cells(0);
    if (!RAM8(0xFFC57F)) {                      /* the stage's music from here, as the arcade's (sounds */
        music_now();                            /* $30, $2B at 1318, 1320): the load's own start ($B470) */
        music_early = 1;                        /* came ~15 frames on (music_hook skips it now), */
    }
    load_vb = 8;
    load_ticks = 1;                             /* and the driver's tick runs every frame of the load */
    for (k = 0; k < sizeof zr / sizeof zr[0]; k++) zero_range(zr[k][0], zr[k][1]);
    for (r = 0; r < 32; r++)                    /* plane A but the HUD's rows' visible half */
        zero_range(0xE000 + r * 128 + ((r < 4 || (r >= 24 && r < 28)) ? 64 : 0), 0xE000 + r * 128 + 128);
    zero_range(0xF000, 0xFFFE);
    VDP_CTRLL = VRAM_W(0xFFFE);
    VDP_DATA = 0;
}

/* $3C6, after stage 1's CRAM load ($3B8): lines 1-3 hidden at once */
void intro_cram(void)
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
        VDP_CTRLL = VSRAM_W(0x48);              /* the v scrolls $3D0 writes (0, 16) go to unused */
        return;                                 /* column entries: plane B shows plane A's table */
    }
    VDP_CTRLL = VSRAM_W(0);                     /* (as $3C6) */
}

/* $940A (the bg init's display off): not while the HUD shows after the opening */
void bg_off(void)
{
    if (intro_hide != 2) VDP_CTRL = 0x8104;
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

void intro_show(void)
{
    if (intro_hide == 2) {
        vdp_reg(4, 0x06);                       /* plane B its own again (lines 1-3 black), */
        VDP_CTRLL = VSRAM_W(0);                 /* with $3D0's v scrolls */
        VDP_DATA = 0;
        VDP_DATA = 16;
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

/* $588 (hud_flush_hook, bossart_glue.s): the stage start's HUD upload ($63FA)
 * puts the TIME digits on the screen with line 2 at once while hidden (its
 * RAM rows at $FF2920, 32 cells each, line 3's cells moved for the upload) */
static u32 buf_moved[2];
void hide_buf(int after)
{
    int r, c;
    if (!hiding) return;
    for (r = 0; r < 2; r++)
        for (c = 0; c < 32; c++) {
            volatile u16 *w = (volatile u16 *)(0xFF2920 + (2 + r) * 64 + c * 2);
            if (!after && (*w & 0x6000) == 0x6000) {
                buf_moved[r] |= 1UL << c;
                *w &= ~0x2000;
            } else if (after && (buf_moved[r] >> c & 1)) {
                *w |= 0x2000;
                hide_cells[r] |= 1UL << c;
            }
        }
    if (after) buf_moved[0] = buf_moved[1] = 0;
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
    if (!intro_hide) { hiding = 0; return 0; }  /* (another stage start: nothing to put back) */
    if (intro_hide == 2) hide_until = RAM32(0xFF7DFC) + HIDE_FRAMES;
    intro_hide = 0;
    load_ticks = 0;
    RAM32(0xFF7DFC) += HOLD_CUT - 3;            /* the load's longer time, counted: the counter in play as
                                                   before (the hold's 2 frames, its last now the handler's) */
    return HOLD_CUT;
}

void hide_vblank(void)
{
    int k;
    u16 sr;
    if (!hiding) return;
    if ((long)(RAM32(0xFF7DFC) - hide_until) < 0) return;
    hiding = 0;
    if (RAM8(0xFFC512) != 0 || RAM32(0xFF7DFC) - hide_until > 8) return;   /* stage 1 left already */
    sr = irq_off();
    VDP_CTRLL = CRAM_W(32);
    for (k = 0; k < 48; k++) VDP_DATA = hide_cram[k];
    hide_cells_move(1);
    irq_restore(sr);
}
