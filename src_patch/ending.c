/* The end of the final room, as the arcade's (docs/ACCURACY.md). Replaces
 * the port's ending routine ($113916, each update of the final room).
 *
 * Arcade: Astaroth's removal ($DDA3 -> $E844 at stage index 6: no sound, no
 * points) switches the top level to its stage-end mode (<$08 = 2); from the
 * next frame that mode runs the ending ($736D, by the clear count <$7F):
 *  - first clear (<$7F = 0, $73FE): the screen cleared to black ($0E00; the
 *    HUD, its TIME and the lives stay), no sprites, "THIS ROOM IS AN
 *    ILLUSION ..." ($022C), 300 frames counting the first; then <$7F = 1 and
 *    stage 1 from its map (<$72 = 0, <$08 = 0: the map, 302 frames, then
 *    play), score and lives kept;
 *  - second clear (<$7F = 1, $7EDC): the princess scene. Frame 1 sets up
 *    the princess (the object at $15C2, x 8179) and clears Arthur's state;
 *    frame 2: Arthur's target is his x + (princess x - his x, low byte) / 3
 *    ($7F21, $FED8), his y $0A4E, facing right; he walks 1.125 px a frame
 *    ($7F45, $9477 with $9553) until his x reaches it, then stands. The
 *    princess walks 1.125 px a frame towards him from frame 2 ($7FDC) until
 *    she is within 16 px of his target; then both take their embrace frames
 *    ($7C86, $7F8D) and a heart rises above Arthur on each frame with <$21 &
 *    15 = 0 (fg char $60 colour 5, one row up each time, $7F95), four; the
 *    frame after the fourth <$7F = 2 ($7FB5), and the next "CONGRATULATION
 *    / THIS STORY IS HAPPY END" ($022D, writing over the top heart) with
 *    50,000 points ($0C15) over the room and the embrace, 540 frames; then
 *    the TIME display erased ($011A) and "BEING THE WISE AND COURAGEOUS
 *    KNIGHT ..." ($022F), 420 frames; then black ($0E00) with the TIME erased,
 *    no sprites ($68DF), "RETURN TO STARTING POINT / CHALLENGE AGAIN !"
 *    ($0230), 180 frames; then <$7F = 0 and the game starts over from the
 *    opening scene of stage 1 ($73F3, $7446), score and lives kept.
 * The port waited 240 frames after the removal with the game running (Arthur
 * could walk about), gave 1,000 points and sound $3F (its stage-end block at
 * $10EA5A, hook_room_end), drew the first clear's text over the room with
 * the last frame's sprites frozen on it (Arthur in the font's tiles), went
 * back to stage 1 through the game start (the opening scene, no map, the
 * random reseeded) after the first clear, had no princess scene, drew
 * "RETURN TO STARTING POINT" over the room, and each text ran a frame long.
 *
 * The port has no art for the standing, walking or embracing princess (only
 * the seated one of its opening) nor Arthur's embrace: those frames are the
 * arcade's own sprites converted to Genesis tiles (mkprincess.py, in the
 * port's palette line 0), put in the VRAM Astaroth's art used ($A000), drawn
 * as sprites here. Arthur's walk is the port's own art and animation.
 *
 * Firebrand's Quest has its own end (either clear): the first clear's black
 * screen with Firebrand's text (fb_texts, in the arcade's colours) for
 * FB_END frames, then Firebrand's Quest Plus from stage 1's map with the
 * score and lives kept (the top starting rank; half the hover, firebrand.c),
 * and Plus unlocked in the Home menu (saved; not from a practice launch). */
#include "md.h"
#include "build/endfont.h"

#define LOOPED   RAM8(0xFF7FC0)         /* the arcade's <$7F: 1 after the first clear */
#define TEXT_ON  RAM8(0xFF7FC2)         /* the port's text layer is shown (uploaded each frame) */
#define TBUF     ((volatile u8 *)0xFFD000)  /* the text layer: 32 x 32, rows 9-20 shown as screen rows 7-18 */
#define STAGE    RAM8(0xFFC512)
#define ART_X    RAM32(0xFF9000)        /* x 16.8 in the low 3 bytes */
#define ART_Y    RAM16(0xFF9004)
#define ART_POSE RAM16(0xFFC30E)        /* the pose $52C6 shows: $0C standing, $0D-$12 walking */
#define ART_WF   RAM16(0xFF9206)        /* walk phase (0-6) */
#define ART_WT   RAM16(0xFF9208)        /* its timer (2, 1, 0) */
#define ART_DIR  RAM16(0xFF920A)        /* 0 right, 8 left */
#define CAM_X    RAM16(0xFFA200)
#define CAM_Y    RAM16(0xFFA202)
#define SPR      ((volatile u16 *)0xFFB500) /* sprite buffer: y, size | link, attributes, x */
#define SPR_LAST RAM16(0xFFB20C)        /* its length in words - 1 */

#define TILE     0x500                  /* VRAM $A000: mkprincess.py's tiles */
#define T_WALK0  (TILE + 0)
#define T_WALK1  (TILE + 8)
#define T_HUG_P  (TILE + 16)
#define T_HUG_A  (TILE + 32)
#define T_HEART  (TILE + 48)

extern u8 menu_frames;                  /* glue.s: the frame counter <$21 is $FF7DFF + this */
int  end_trigger(void);                 /* ending_glue.s: the port's $10EAA4 (the room is over) */
void end_text(int id);                  /* the port's text id into the text layer ($4EBA, $113A88) */
void end_black(void);                   /* planes cleared, the HUD rows and the lives kept */
void end_black_all(void);               /* the same down to the bottom row */
void end_time_off(void);                /* the TIME display erased */
void end_50k(void);                     /* 50,000 points ($0C15) */
void score_now(void);                   /* hud.s: the queued score now, as the arcade's */
void end_sound(int id);
void end_to_map(void);                  /* stage 1 from its map (no return) */
void end_restart(void);                 /* stage 1 from its opening scene (glue.s loop_again) */
int  fb_on(void);                       /* firebrand.c */
void fb_cleared(void);                  /* firebrand.c: Plus from here on, unlocked */

void dma_vram(u32 src, u16 bytes, u16 vram);   /* glue.s */

/* ---- the texts -----------------------------------------------------------
 * The port's text writer ($113A88) puts a text's chars into the text layer
 * (TBUF) at the arcade's rows and columns; its upload ($113B00) drew them all
 * in one colour with its font at VRAM $6000, where Arthur's frame also goes
 * (so a frame of his could replace letters: the first clear's text came out
 * with A-P missing). end_tupload draws each row in its arcade colour (fg colour
 * 0, 4, 5, 8, 9 or 11 by text and row, the arcade's attributes) with the
 * arcade's chars in those colours (mkprincess.py, build/endfont.h) at $AF00.
 * Both games show a text whole on its first frame (the arcade's printer
 * writes all its chars in one frame; the first clear's in 2). */
#define FB_END    480                   /* Firebrand's ending: 8 s */
#define FONT_VRAM 0xAF00                /* tiles $578-$5D1 */
static u8 row_slot[32];                 /* each TBUF row's colour (end_glyph's slot) */
static u8 font_pending;

static void text(int id)
{
    int r;
    u8 dflt = id == 44 ? 3 : id == 45 ? 2 : 5;     /* colours 8, 5, 11 */
    for (r = 0; r < 32; r++) row_slot[r] = dflt;
    if (id == 44) { row_slot[15] = 4; row_slot[17] = 1; }     /* colours 9 and 4 */
    if (id == 45) row_slot[9] = 0;                  /* CONGRATULATION: colour 0 */
    if (id == 48) row_slot[11] = 2;                 /* RETURN TO STARTING POINT: 5 */
    end_text(id);
    font_pending = 1;
}

/* Firebrand's ending: TBUF row, colour slot (0 4 5 8 9 11 = arcade colours
 * 0, 4, 5, 8, 9, 11; mkprincess.py has their letters), text */
static const struct { u8 row, slot; const char *s; } fb_texts[] = {
    { 10, 0, "CONGRATULATION" },
    { 12, 5, "THE RED ARREMER HAS" },
    { 13, 5, "DEFEATED ASTAROTH." },
    { 15, 4, "A HARDER QUEST AWAITS !" },
    { 17, 1, "FIREBRAND'S QUEST PLUS" },
};

static void fb_text(void)
{
    unsigned i;
    int r, c;
    for (r = 9; r <= 20; r++) {
        row_slot[r] = 5;
        for (c = 0; c < 32; c++) TBUF[r * 32 + c] = ' ';
    }
    for (i = 0; i < sizeof fb_texts / sizeof fb_texts[0]; i++) {
        const char *s = fb_texts[i].s;
        int n = 0;
        while (s[n]) n++;
        row_slot[fb_texts[i].row] = fb_texts[i].slot;
        for (c = 0; c < n; c++) TBUF[fb_texts[i].row * 32 + (32 - n) / 2 + c] = s[c];
    }
    font_pending = 1;
}

/* hook_end_vbl (after the VBlank) in place of $113B00: rows 9-20 of the text
 * layer to plane A rows 7-18 */
void end_tupload(void)
{
    int r, c;
    if (!TEXT_ON) return;
    if (font_pending) {
        dma_vram((u32)end_font, sizeof end_font, FONT_VRAM);
        font_pending = 0;
    }
    vdp_reg(15, 2);
    for (r = 9; r <= 20; r++) {
        const u8 *g = end_glyph[row_slot[r]];
        u16 attr = 0x8000 | (u16)end_slot_line[row_slot[r]] << 13 | ((FONT_VRAM >> 5) - 1);
        volatile u8 *t = TBUF + r * 32;
        VDP_CTRLL = VRAM_W(0xE000 + (r - 2) * 128);
        for (c = 0; c < 32; c++) {
            u8 ch = t[c];
            u8 k = ch >= 32 && ch < 96 ? g[ch - 32] : 0;
            VDP_DATA = k ? attr + k : 0;
        }
    }
}

/* the scene's state */
static u8 phase;                        /* 0 waiting, 1 first clear's text, 2 princess scene, 3 its texts,
                                           4 Firebrand's ending */
static u16 t;                           /* frames since the ending began (1 = the arcade's frame 1) */
static u16 count;                       /* the arcade's <$09 */
static u8 tx;                           /* which text of the second clear */
static u8 ast, pst, hearts, hug, black; /* Arthur's -$D,X; the princess's <$0E; ... */
static u8 stopped;                      /* Arthur's $6,X */
static u16 target, hx, hy;
static u32 px;                          /* the princess's x, 16.8 */
u8 end_upload;                          /* ending_glue.s: the tiles go to VRAM at the next upload */

void end_reset(void) { phase = 0; }

static u8 c21(void) { return RAM8(0xFF7DFF) + menu_frames; }

static void arthur_walk_anim(void)
{
    if (ART_WT) ART_WT--;
    else { ART_WT = 2; if (++ART_WF > 6) ART_WF = 1; }
    ART_POSE = 0x0D + (ART_WF % 6);
}

/* Second clear, one arcade frame of $7EDC: Arthur ($7EF9), then the
 * princess ($7FBC). */
static void scene_frame(void)
{
    u16 ax = (u16)(ART_X >> 8);
    switch (ast) {
    case 0:                             /* $7F21 */
        target = ax + (u8)((u8)((u16)(px >> 8) - ax) / 3);
        ART_Y = 0x0A4E;
        ART_DIR = 0;
        stopped = 0;
        ART_WF = 0; ART_WT = 2;
        ast = 1;
        break;
    case 1:                             /* $7F45 */
        if (stopped) break;
        if (ax < target) { ART_X += 0x120; arthur_walk_anim(); }
        else { stopped = 1; ART_POSE = 0x0C; }
        break;
    case 2:                             /* $7F61: the embrace, the hearts' place */
        hug = 1;
        hearts = 0;
        hx = (ax & 0xFF) >> 3;
        hy = ((0xE0 - (ART_Y & 0xFF)) & 0xF8) >> 3;
        ast = 3;
        break;
    case 3:                             /* $7F95: a heart on each 16th frame */
        if ((c21() & 15) == 0 && ++hearts == 4) ast = 4;
        break;
    case 4:                             /* $7FB5: <$7F = 2, the texts from the next frame */
        phase = 3; tx = 0; count = 0;
        break;
    }
    switch (pst) {                      /* the princess */
    case 0:                             /* $7FCC: set up (frame 1) */
        pst = 1;
        break;
    case 1:                             /* $7FDC: towards Arthur's target */
        if ((u16)(target + 16) < (u16)(px >> 8)) px -= 0x120;
        else { ast = 2; pst = 2; }
        break;
    case 2:                             /* $7FF8: her embrace frame */
        pst = 3;
        break;
    }
}

/* the second clear's texts ($7389) */
static void text_start(void)
{
    switch (tx) {
    case 0:                             /* $7399 */
        text(45);
        end_50k();                      /* its bonus life comes in play (bonus.c) */
        score_now();
        count = 540;
        break;
    case 1:                             /* $73B4 */
        end_time_off();
        text(47);
        end_sound(26);                  /* the port's own (the arcade's text queue has none) */
        count = 420;
        break;
    case 2:                             /* $73CF */
        black = 1;
        end_black_all();
        text(48);
        end_sound(26);
        count = 180;
        break;
    }
    TEXT_ON = 1;
}

/* each text's first frame counts (the arcade's state falls through into its
 * countdown), and the next one starts on the frame the last one ends */
static void texts_frame(void)
{
    if (count == 0) text_start();
    if (--count == 0) {
        if (++tx == 3) end_restart();   /* $73F3 */
        text_start();
        count--;
    }
}

/* $113916: one update of the final room. Returns 1 while the ending runs
 * (the stage loop then skips the game update and only draws). */
int end_update(void)
{
    if (phase == 0) {
        if (STAGE != 6 || !end_trigger()) return 0;
        t = 0;
        black = 0; hug = 0; hearts = 0;
        if (fb_on()) {
            phase = 4;
            black = 1;
            end_black();
            fb_text();
            TEXT_ON = 1;
            count = FB_END;
        } else if (!LOOPED) {           /* $73FE */
            phase = 1;
            black = 1;
            end_black();
            text(44);
            TEXT_ON = 1;
            count = 300;
        } else {                        /* $7EDC */
            phase = 2;
            ast = 0; pst = 0;
            px = 8179UL << 8;
            ART_POSE = 0x0C;
            end_upload = 1;
        }
    }
    t++;
    switch (phase) {
    case 1:
        if (--count == 0) {             /* $743E */
            LOOPED = 1;
            end_to_map();
        }
        break;
    case 2:
        if (t == 1) pst = 1;            /* frame 1: the princess set up ($7FCC), Arthur's state cleared */
        else scene_frame();
        break;
    case 3:
        texts_frame();
        break;
    case 4:
        if (--count == 0) {
            fb_cleared();
            end_to_map();
        }
        break;
    }
    return 1;
}

/* ---- sprites ------------------------------------------------------------ */

static int put(int n, int x, int y, int size, int tile)
{
    volatile u16 *e = SPR + 4 * n;
    e[0] = 128 + y;
    e[1] = size << 8;
    e[2] = tile;
    e[3] = 128 + x;
    return n + 1;
}

/* the scene's sprites from entry n on; returns the new count */
static int scene_sprites(int n)
{
    int k, nh, top = 224 + CAM_Y - 0x0A4E;
    int cx = CAM_X;
    if (phase < 2 || black) return n;
    /* the hearts are fg chars in the arcade (over the sprites): the first
     * text writes over the top one, the second clears them ($011A) */
    nh = phase < 3 ? hearts : tx == 0 && hearts > 3 ? 3 : 0;
    for (k = 0; k < nh; k++)
        n = put(n, hx * 8, (hy - k - 2) * 8, 0, 0x8000 | T_HEART);
    if (hug) {
        n = put(n, (int)(px >> 8) - cx - 16, top, 15, T_HUG_P);
        if (!fb_on()) n = put(n, (int)(u16)(ART_X >> 8) - cx - 16, top, 15, T_HUG_A);
    } else {
        /* script $7C7C: the first frame until frame 5, then 3 frames each */
        int f = t < 5 ? 0 : !(((t - 5) / 3) & 1);
        n = put(n, (int)(px >> 8) - cx - 8, top, 7, f ? T_WALK1 : T_WALK0);
    }
    return n;
}

static void link_all(int n)
{
    int i;
    for (i = 0; i < n; i++) SPR[4 * i + 1] = (SPR[4 * i + 1] & 0xFF00) | (i + 1 < n ? i + 1 : 0);
}

/* $1118BC (the final room's sprites while the text layer is shown): the
 * buffer is clear; the scene's sprites, or one off-screen sprite so the old
 * table doesn't stay on screen. */
void end_text_sprites(void)
{
    int n = scene_sprites(0);
    if (!n) n = put(0, -128, -128, 0, 0);
    link_all(n);
    SPR_LAST = 4 * n - 1;
}

/* after the final room's sprite build ($111922; not on a skipped build):
 * the scene's sprites after the port's (Arthur first), Arthur hidden while
 * the embrace is drawn. */
void end_build_sprites(void)
{
    int n;
    if (phase < 2 || STAGE != 6) return;
    n = 1;                              /* Arthur ($5302's first entry) only: */
    if (hug && !fb_on()) SPR[0] = 0;    /* the stage-end mode draws no weapons */
    n = scene_sprites(n);
    link_all(n);
    SPR_LAST = 4 * n - 1;
}
