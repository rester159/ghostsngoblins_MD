/* Firebrand campaign (Home): one player as the Red Arremer.
 *
 * Firebrand is Arthur's engine with different rules and art:
 *  - art: every frame Arthur can show has a Firebrand pose of the same meaning
 *    and facing (art/firebrand, built from the game's own Arremer frames).
 *    Wide frames (wings out) add two 8x32 columns beside Arthur's 32x32 sprite.
 *  - hover: holding jump after the top of a jump holds the altitude for up to
 *    2 s, steering left/right at walking speed; landing refills it.
 *  - one attack: the lance's mechanics, drawn as the fireball (uploaded where
 *    the game uploads the lance art for each shot slot, $11711E); the game's
 *    fire icon is in the HUD weapon box.
 *  - one hit: never armored, so the first hit kills.
 *  - boxes: weapon and armor pickups give 1000 points instead. */
#include "md.h"
#include "common.h"

void dma_vram(u32 src, u16 bytes, u16 vram);
u32  gcall(u32 addr, u32 d0, u32 a3);   /* glue.s: jsr addr, a0=$FF0000 a4=$FF9000 a5=$FF9100 */
void score_event(u16 idx);              /* glue.s: score table entry idx */

#define FB_BANK     0x3A0000UL          /* placed by tools/patch_gng.py from art/firebrand */
#define FB_FLAGS    ((const u8 *)0x3B6000UL)
#define FB_FIRE     0x3B6100UL
#define FB_MAPICON  0x3B6200UL          /* stage-map marker, 4 tiles */
#define MAP_TILE    0x69C               /* stage-map marker tiles (glue.s hook_map_marker) */
#define FIRE_ICON   0x1037D4UL          /* the game's fire weapon-box icon, 4 tiles */
#define FB_FRAME    0x300
#define FB_WALK     84                  /* 6-frame walk cycle, facing right then left */
#define FB_FLY      96                  /* 6-frame flight cycle, the same */
#define ARTHUR_A    0x109E2UL           /* 11 frames */
#define ARTHUR_B    0x40000UL           /* 73 frames, streamed in play */
#define COL_TILE    0x690               /* free in every stage (VRAM $D200) */
#define ICON_TILE   0x698               /* after the wing columns */
#define WEAPON      RAM8(0xFFA218)
#define ARMOR_SET   RAM8(0xFFC328)      /* 0 armored, 1 boxers */
#define JUMP_PHASE  RAM16(0xFF9410)     /* 0 ground, 1 rising, 2 falling */
#define JUMP_SPEED  RAM32(0xFF9404)
#define SCORE_1000  8

enum { F_LEFT = 1, F_RIGHT = 2, F_PAL2 = 4, F_RUN = 8, F_FACES_LEFT = 16 };

static u8  hover_t, hovering, flap, walk_t;
static s16 shown;                       /* bank frame in VRAM + 1, 0 = unknown */
static u32 shown_src;                   /* non-Firebrand frame (the frog) in VRAM */

int fb_on(void)
{
    return is_home() && PERSIST->home_sub == HOME_FIREBRAND;
}

static u8 hover_max(void) { return (RAM8(0xA10001) & 0x40) ? 100 : 120; }   /* 2 s */

/* The stage-end sequence uses its own copies of Arthur's frames ($8AAD4 table);
 * each is identical to one of his frames above, except $C0200 (fist raised),
 * which becomes Firebrand's wings-spread flight frame. */
#define STAGE_END   0xC0000UL
static const u8 stage_end[12] = { 45, FB_FLY, 0, 1, 2, 3, 4, 28, 60, 61, 62, 63 };

/* Arthur's frame address -> bank frame, or -1 */
static int bank_index(u32 a)
{
    if (a >= ARTHUR_A && a < ARTHUR_A + 11 * 0x200 && !((a - ARTHUR_A) & 0x1FF))
        return (a - ARTHUR_A) >> 9;
    if (a >= ARTHUR_B && a < ARTHUR_B + 73 * 0x200 && !((a - ARTHUR_B) & 0x1FF))
        return 11 + ((a - ARTHUR_B) >> 9);
    if (a >= STAGE_END && a < STAGE_END + 12 * 0x200 && !((a - STAGE_END) & 0x1FF))
        return stage_end[(a - STAGE_END) >> 9];
    return -1;
}

/* every gameplay frame, from the pad routine (before Arthur's update) */
void fb_frame(void)
{
    if (!fb_on()) return;
    WEAPON = 1;
    ARMOR_SET = 1;
    if (!RAM8(0xFFC305)) {              /* stage (re)start: VRAM is reloaded */
        shown = 0;
        shown_src = 0;
        hovering = 0;
        hover_t = hover_max();
        return;
    }
    if (JUMP_PHASE == 0 || RAM8(0xFFC342)) {
        hovering = 0;
        if (JUMP_PHASE == 0) hover_t = hover_max();
        return;
    }
    /* jump is bit 5 of the input byte, active low */
    if (JUMP_PHASE == 2 && !(G_P1 & 0x20) && hover_t) {
        hover_t--;
        hovering = 1;
        JUMP_SPEED = 0;                 /* this frame's fall moves 0 px */
        /* steer at walking speed, through the engine's walk moves (wall checks
         * included; the same calls Maximo's walk uses). Direction bits are
         * active low: 2 = right held, 1 = left held. */
        if ((G_P1 & 3) == 2) {
            RAM8(0xFF9006) = 1; RAM16(0xFF920A) = 0;
            gcall(0x11469C, 288, 0x1486E);
        } else if ((G_P1 & 3) == 1) {
            RAM8(0xFF9006) = 2; RAM16(0xFF920A) = 0x800;
            gcall(0x1146CE, (u32)(s16)-288, 0x1496E);
        }
    } else {
        hovering = 0;
    }
}

/* $116472 / $116884: the item code is about to copy its context's armor and
 * weapon back to the game; a pickup changed them. */
void fb_item(u8 *ctx)
{
    if (!fb_on()) return;
    if (ctx[17] != WEAPON || ctx[9] != ARMOR_SET) score_event(SCORE_1000);
    ctx[17] = WEAPON;
    ctx[9] = ARMOR_SET;
}

/* the weapon box (plane A rows 25-26, columns 15-16) shows the game's fire
 * icon (from its icon table at $1037D4, next to the lance's) instead of the
 * lance; the game redraws the box when the weapon changes */
static void draw_icon(void)
{
    static const u16 *const icon = (const u16 *)FIRE_ICON;
    u16 w;
    VDP_CTRLL = VRAM_R(ICON_TILE * 32 + 0x1A);   /* a row through the flame */
    w = VDP_DATA;
    if (w != icon[0x1A / 2]) dma_vram(FIRE_ICON, 128, ICON_TILE * 32);
    VDP_CTRLL = VRAM_W(0xE000 + (25 * 64 + 15) * 2);
    VDP_DATAL = 0x80000000UL | (u32)ICON_TILE << 16 | 0x8000 | (ICON_TILE + 1);
    VDP_CTRLL = VRAM_W(0xE000 + (26 * 64 + 15) * 2);
    VDP_DATAL = 0x80000000UL | (u32)(ICON_TILE + 2) << 16 | 0x8000 | (ICON_TILE + 3);
}

/* At the sprite-table DMA: upload Firebrand's frame and add the wing columns.
 * Returns the new DMA length. Z80 bus is held here. */
/* A shot is two 16x16 pieces from its slot's tiles (base, base + 4). Flying
 * left the game mirrors each piece in place; flying right it draws them as
 * stored. The fireball is one 32-wide picture stored for the flying-left case,
 * so for right-moving shots the two pieces trade places. The game starts a
 * left shot 15 px further back than a right one (over his body), so left
 * shots are drawn 14 px ahead to leave from his mouth too. */
static void fix_shots(volatile u16 *buf, u16 n)
{
    /* only while shots are out (weapon slots at $FF9600, active flag at +8),
     * and only until all their pieces are found: a busy screen has ~60 sprites */
    u16 left = (RAM8(0xFF9608) ? 2 : 0) + (RAM8(0xFF9628) ? 2 : 0) + (RAM8(0xFF9648) ? 2 : 0);
    volatile u16 *e = buf, *end = buf + n * 4;
    for (; left && e < end; e += 4) {
        u16 a = e[2], t = a & 0x7FB;    /* both pieces of a slot: base and base + 4 */
        if (t != 0x2A0 && t != 0x2B0 && t != 0x790) continue;
        if (a & 0x0800) e[3] -= 14;
        else e[3] += a & 4 ? -16 : 16;
        left--;
    }
}

/* the stage map shown between lives and stages: the map code ($113DA2) draws
 * its marker from MAP_TILE in Firebrand mode (glue.s hook_map_marker); keep
 * Firebrand's head there */
static void map_marker(void)
{
    static const u16 *const icon = (const u16 *)FB_MAPICON;
    u16 w;
    VDP_CTRLL = VRAM_R(MAP_TILE * 32 + 0x22);   /* bottom-left tile, first row: the eye */
    w = VDP_DATA;
    if (w != icon[0x22 / 2]) dma_vram(FB_MAPICON, 128, MAP_TILE * 32);
}

u16 fb_sat(u16 len)
{
    volatile u16 *buf = (volatile u16 *)0xFFB500;
    u16 n = len / 8, hf, link;
    int idx;
    u8 f = 0;
    if (n == 0 || n >= 62) return len;
    if ((buf[2] & 0x7FF) != 0x300) return len;  /* sprite 0 isn't Arthur: not in play */
    draw_icon();
    map_marker();
    fix_shots(buf, n);
    idx = bank_index(RAM32(0xFFC380));
    if (idx >= 0) {
        /* Firebrand's own cycles: Arthur's walk has only four distinct frames.
         * Frames Arthur draws pre-mirrored (facing left) take the left set. */
        u8 left = FB_FLAGS[idx] & F_FACES_LEFT ? 6 : 0;
        if (hovering) {
            if (++flap >= 36) flap = 0;
            idx = FB_FLY + left + flap / 6;
        } else if (FB_FLAGS[idx] & F_RUN) {
            if (++walk_t >= 42) walk_t = 0;
            idx = FB_WALK + left + walk_t / 7;
        }
    }
    if (idx < 0) {                      /* not one of Arthur's frames: the frog */
        u32 src = RAM32(0xFFC380);
        if (src != shown_src) { dma_vram(src, 512, 0x6000); shown_src = src; }
        shown = 0;
    } else {
        u32 src = FB_BANK + (u32)idx * FB_FRAME;
        f = FB_FLAGS[idx];
        if (idx + 1 != shown) {
            dma_vram(src, 512, 0x6000);
            if (f & (F_LEFT | F_RIGHT)) dma_vram(src + 0x200, 256, COL_TILE * 32);
            shown = idx + 1;
            shown_src = 0;
        }
    }
    buf[2] = (buf[2] & ~0x6000) | (f & F_PAL2 ? 0x4000 : 0);
    if (!(f & (F_LEFT | F_RIGHT)) || !buf[0]) return len;
    hf = buf[2] & 0x0800;
    link = buf[1] & 0x7F;
    if (f & F_LEFT) {                   /* tile COL_TILE: the column left of the frame */
        buf[n * 4 + 0] = buf[0];
        buf[n * 4 + 1] = 0x0300 | link;
        buf[n * 4 + 2] = (buf[2] & 0xF800) | COL_TILE;
        buf[n * 4 + 3] = hf ? buf[3] + 32 : buf[3] - 8;
        link = n++;
    }
    if (f & F_RIGHT) {
        buf[n * 4 + 0] = buf[0];
        buf[n * 4 + 1] = 0x0300 | link;
        buf[n * 4 + 2] = (buf[2] & 0xF800) | (COL_TILE + 4);
        buf[n * 4 + 3] = hf ? buf[3] - 8 : buf[3] + 32;
        link = n++;
    }
    buf[1] = (buf[1] & 0xFF00) | link;
    return n * 8;
}

/* $11711E: a shot slot's art upload (a0 = source). The lance is art frame 8
 * ($295000, flying right) and 9 ($295200, flying left, drawn flipped). */
u32 fb_shot_src(u32 src)
{
    return fb_on() && (src == 0x295000UL || src == 0x295200UL) ? FB_FIRE : src;
}
