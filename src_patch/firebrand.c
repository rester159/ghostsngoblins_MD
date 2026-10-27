/* Firebrand campaign (Home): one player as the Red Arremer.
 *
 * Firebrand is Arthur's engine with different rules and art:
 *  - art: every frame Arthur can show has a Firebrand pose of the same meaning
 *    and facing (art/firebrand, built from the game's own Arremer frames).
 *    Wide frames (wings out) add two 8x32 columns beside Arthur's 32x32 sprite.
 *  - hover: holding jump after the top of a jump holds the altitude for up to
 *    2 s, steering left/right at walking speed; landing refills it.
 *  - walls: in the air, pushing into a wall (a map cell the engine's wall
 *    probe stops him at, never an object) makes him cling to it, facing out,
 *    for as long as he likes; he fires away from it. Jump leaps straight up
 *    and he grabs the wall again at the top of the leap if still pushing into
 *    it; pushing away lets go. A grab refills the hover.
 *  - solid scenery: the insides of rocks and stage 3's tower are only
 *    background to the engine (attribute $C0, no wall or floor): Arthur can't
 *    get there, but Firebrand flies. A move that puts his body in one is
 *    undone (scenery_block): sideways he stops at its surface, rising he stops
 *    as under a ceiling, and dropping onto one refills the hover.
 *  - one attack: the lance's mechanics, drawn as the fireball (uploaded where
 *    the game uploads the lance art for each shot slot, $11711E); the game's
 *    fire icon is in the HUD weapon box.
 *  - one hit: never armored, so the first hit kills.
 *  - boxes: weapon and armor pickups give 1000 points instead.
 *  - the end: stage 6 needs no cross (the game's check at $119D2E sees one),
 *    the fireball hurts Astaroth (cross-only for everyone else, glue.s
 *    hook_weapon_mask),
 *    and beating the final room shows Firebrand's ending (ending.c), then
 *    Firebrand's Quest Plus from stage 1 with the score and lives kept: the
 *    top starting rank and half the hover. Plus is in the Home menu once
 *    the quest has been cleared (saved in SRAM). */
#include "md.h"
#include "common.h"

void dma_vram(u32 src, u16 bytes, u16 vram);
u32  gcall(u32 addr, u32 d0, u32 a3);   /* glue.s: jsr addr, a0=$FF0000 a4=$FF9000 a5=$FF9100 */
long wall_probe(u32 addr, u32 x, u32 y, u32 table);    /* glue.s: px into the wall, or -1 */
void jump_sfx(void);                    /* glue.s */
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
#define FB_CLING    108                 /* clinging facing right, left; then firing, the same */
#define ARTHUR_A    0x109E2UL           /* 11 frames */
#define ARTHUR_B    0x40000UL           /* 73 frames, streamed in play */
#define COL_TILE    0x690               /* free in every stage (VRAM $D200) */
#define ICON_TILE   0x698               /* after the wing columns */
#define WEAPON      RAM8(0xFFA218)
#define ARMOR_SET   RAM8(0xFFC328)      /* 0 armored, 1 boxers */
#define JUMP_PHASE  RAM16(0xFF9410)     /* 0 ground, 1 rising, 2 falling */
#define JUMP_SPEED  RAM32(0xFF9404)
#define ON_GROUND   RAM16(0xFF9408)
#define JUMP_DIR    RAM16(0xFF9414)     /* the jump's sideways motion: 0 none, 1 right, 2 left */
#define JUMP_DX     RAM32(0xFF9418)
#define JUMP_POSE   RAM16(0xFF941C)
#define FACING      RAM16(0xFF920A)     /* 0 right, $800 left */
#define POS_X       RAM32(0xFF9000)     /* 16.8 */
#define POS_Y       RAM16(0xFF9004)
#define SCORE_1000  8

enum { F_LEFT = 1, F_RIGHT = 2, F_PAL2 = 4, F_RUN = 8, F_FACES_LEFT = 16 };
enum { WALL_RIGHT = 1, WALL_LEFT = 2 };

static u8  hover_t, hovering, flap, walk_t;
static u8  cling;                       /* the side of the wall he holds, 0 = none */
static u8  wall_jump;                   /* rising from a wall: no grab until the top */
static u8  jump_was;                    /* jump held last frame */
static u8  shots_was, cling_fire;       /* shots out last frame; frames of the cling-fire pose left */
#define CLING_FIRE  15                  /* Demon's Crest holds it about as long */
static s16 shown;                       /* bank frame in VRAM + 1, 0 = unknown */
static u32 shown_src;                   /* non-Firebrand frame (the frog) in VRAM */

int fb_on(void)
{
    return is_home() && PERSIST->home_sub == HOME_FIREBRAND;
}

int fb_plus_on(void)
{
    return fb_on() && PERSIST->fb_plus;
}

/* the end of Firebrand's ending (ending.c): Plus from here on, with the top
 * starting rank, and unlocked in the Home menu (saved; not from practice) */
void fb_cleared(void)
{
    Persist *p = PERSIST;
    if (!p->dev_on && !p->fb_unlocked) {
        p->fb_unlocked = 1;
        save_write();
    }
    p->fb_plus = 1;
    RAM8(0xFFC501) = FB_PLUS_RANK;      /* rank */
    RAM8(0xFFC561) = FB_PLUS_RANK;      /* its floor for the per-death decrease */
}

/* 2 s, 1 s in Firebrand's Quest Plus */
static u8 hover_max(void)
{
    u8 n = (RAM8(0xA10001) & 0x40) ? 100 : 120;
    return fb_plus_on() ? n / 2 : n;
}

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

/* Is the wall on this side within 2 px? If so, move him flush against it.
 * The probe tests one point (x +- 16, y - 8) against the cell's wall edge,
 * as the walk and the jump do. */
static int touch_wall(u8 side)
{
    u16 x = POS_X >> 8;
    long in = side == WALL_RIGHT ? wall_probe(0x8510, x + 2, POS_Y, 0x1486E)
                                : wall_probe(0x8538, x - 2, POS_Y, 0x1496E);
    if (in < 0) return 0;
    in -= 2;                            /* px into the wall where he is */
    if (in) {
        POS_X = (POS_X + ((side == WALL_RIGHT ? -in : in) << 8)) & 0xFFFFFF;
        gcall(0xA35C, 0, 0);            /* the camera, as after a walk step */
    }
    return 1;
}

/* held on the wall: still in the air (falling at 0 px), facing out, and the
 * engine sees no left/right (it would turn him to the wall to fire or jump) */
static void hold_wall(void)
{
    JUMP_PHASE = 2;
    JUMP_SPEED = 0;
    JUMP_DIR = 0;
    JUMP_DX = 0;
    FACING = cling == WALL_RIGHT ? 0x800 : 0;
    G_P1 |= 3;
}

/* Solid scenery per stage index ($FFC512): background tiles (attribute bits
 * $C0) that draw rock or a building. Stages 5 and 6 share their rock: $10-$12,
 * $18-$1A (the faces, $82-$85 and $9D/$9E, are the engine's walls). Stage 3:
 * the cave's stone ($E5, $E6, $E8-$EA, $EC, $F8, its underside $F1, $F2, $F4,
 * $FA; the dark cave $E2, $E3, $ED, $EE stays open) and the tower's stones
 * beside and above its door ($C8-$CF, its right edge $EF and $F6), not those
 * flanking the door at the floor ($C0-$C7), which he walks past to reach it. tools/headless/fb_mapdump.py shows the maps. */
static const u8 rock[] = { 0x10, 0x11, 0x12, 0x18, 0x19, 0x1A, 0 };
static const u8 tower[] = { 0xE5, 0xE6, 0xE8, 0xE9, 0xEA, 0xEC, 0xF8, 0xF1, 0xF2, 0xF4, 0xFA,
                            0xC8, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD, 0xCE, 0xCF, 0xEF, 0xF6, 0 };
static const u8 *const scenery[7] = { 0, 0, tower, 0, rock, rock, 0 };

static int solid_at(u16 x, u16 y)       /* the terrain ring cell, as $84D4 finds it */
{
    const u8 *t = RAM8(0xFFC512) < 7 ? scenery[RAM8(0xFFC512)] : 0;
    u16 i = (x & 0x1F0) * 2 | (((y >> 4) ^ 15) & 31);
    u8 tile = RAM8(0xFF0000 + i);
    if (!t || !(RAM8(0xFF0000 + 1024 + i) & 0xC0)) return 0;
    for (; *t; t++)
        if (*t == tile) return 1;
    return 0;
}

static int body_solid(u32 x16, u32 y16)  /* 16.8 position: his body, 12 x 24 px above his feet */
{
    u16 x = (u16)(x16 >> 8), y = (u16)(y16 >> 8);
    return solid_at(x - 6, y + 6) || solid_at(x + 6, y + 6) ||
           solid_at(x - 6, y + 22) || solid_at(x + 6, y + 22);
}

static u32 prev_x, prev_y;              /* his last position outside solid scenery (16.8) */
static u8 prev_ok;
#define POS_Y16 RAM32(0xFF9400)         /* y 16.8; POS_Y is its pixel copy */

static void scenery_block(void)
{
    u32 x = POS_X & 0xFFFFFF, y = POS_Y16;
    if (RAM8(0xFF9459) || RAM8(0xFFC342) || !prev_ok || !body_solid(x, y)) {
        prev_x = x; prev_y = y; prev_ok = 1;
        return;
    }
    if (!body_solid(prev_x, y)) {       /* sideways into it: stop at its surface */
        x = prev_x;
        JUMP_DIR = 0;
        JUMP_DX = 0;
    } else {
        if (body_solid(x, prev_y))
            x = prev_x;                 /* into it both ways: back where he was */
        if (y < prev_y)                 /* dropping onto it: can fly off again */
            hover_t = hover_max();
        y = prev_y;
        /* no rise left (a ceiling): falling from 0, as at the top of a jump
         * (the rise subtracts gravity from the speed, which would wrap) */
        if (JUMP_PHASE == 1) JUMP_PHASE = 2;
        JUMP_SPEED = 0;
    }
    POS_X = (POS_X & 0xFF000000) | x;
    POS_Y16 = y;
    POS_Y = (u16)(y >> 8);
    prev_x = x; prev_y = y;
}

/* every gameplay frame, from the pad routine (before Arthur's update) */
void fb_frame(void)
{
    u8 in, jump, toward;
    if (!fb_on()) return;
    WEAPON = 1;
    ARMOR_SET = 1;
    if (!RAM8(0xFFC305)) {              /* stage (re)start: VRAM is reloaded */
        shown = 0;
        shown_src = 0;
        hovering = 0;
        cling = wall_jump = 0;
        hover_t = hover_max();
        prev_ok = 0;
        return;
    }
    scenery_block();
    /* jump is bit 5 of the input byte, active low; 2 = right held, 1 = left */
    in = G_P1;
    jump = !(in & 0x20);
    toward = (in & 3) == 2 ? WALL_RIGHT : (in & 3) == 1 ? WALL_LEFT : 0;
    {   /* a shot thrown from the wall: the firing pose for a moment */
        u8 n = (RAM8(0xFF9608) != 0) + (RAM8(0xFF9628) != 0) + (RAM8(0xFF9648) != 0);
        if (!cling) cling_fire = 0;
        else if (n > shots_was) cling_fire = CLING_FIRE;
        else if (cling_fire) cling_fire--;
        shots_was = n;
    }
    if (JUMP_PHASE == 0 || RAM8(0xFFC342)) {
        hovering = 0;
        cling = wall_jump = 0;
        if (JUMP_PHASE == 0) hover_t = hover_max();
        jump_was = jump;
        return;
    }
    if (cling) {
        if (toward && toward != cling) {
            cling = 0;                  /* pushed away: let go */
        } else if (jump && !jump_was) {
            cling = 0;                  /* leap straight up */
            wall_jump = 1;
            JUMP_PHASE = 1;
            ON_GROUND = 0;
            JUMP_SPEED = 0x44000;       /* Arthur's jump ($B4CA) */
            JUMP_DIR = 0;
            JUMP_DX = 0;
            JUMP_POSE = 8;
            jump_sfx();
        } else if (touch_wall(cling)) {
            hold_wall();
        } else {
            cling = 0;                  /* the wall ended */
        }
    }
    if (JUMP_PHASE == 2) wall_jump = 0;
    if (!cling && toward && !wall_jump && touch_wall(toward)) {
        cling = toward;
        hovering = 0;
        hover_t = hover_max();
        hold_wall();
    }
    jump_was = jump;
    if (cling) return;
    if (JUMP_PHASE == 2 && jump && hover_t) {
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

/* $119E16 (hook_cross_gate): the weapon the stage 6 check tests, 3 = the
 * cross (without it the game sends the player back to stage 5) */
int fb_gate_weapon(void)
{
    return fb_on() ? 3 : WEAPON;
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
        if (cling) {
            idx = FB_CLING + (cling == WALL_RIGHT) + (cling_fire ? 2 : 0);
        } else if (hovering) {
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
