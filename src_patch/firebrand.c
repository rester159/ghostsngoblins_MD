/* Firebrand campaign (Home): one player as the Red Arremer.
 *
 * Firebrand is Arthur's engine with different rules and art:
 *  - art: every frame Arthur can show has a Firebrand pose of the same meaning
 *    and facing (art/firebrand, built from the game's own Arremer frames).
 *    Wide frames (wings out) add two 8x32 columns beside Arthur's 32x32 sprite.
 *  - flight: jump, then jump again in the air locks it on; from the top of the
 *    jump he holds his altitude, steering left/right at walking speed, until
 *    his flight runs out (DOWN drops him). Its length is his flight level
 *    (1-FLY_MAX, a second a level), shown as wings on the HUD (FLY); landing
 *    or grabbing a wall refills it. Wing pickups raise the level, a death
 *    takes one away.
 *  - walls: in the air, pushing into a wall (a map cell the engine's wall
 *    probe stops him at, never an object) makes him cling to it, facing out,
 *    for as long as he likes; he fires away from it. Jump leaps straight up
 *    and he grabs the wall again at the top of the leap if still pushing into
 *    it; pushing away lets go. A grab refills the hover. In Firebrand's
 *    Vendetta he also grabs solid scenery's faces (below), and jump pressed
 *    again in the air flaps him up (FLAPS a jump, refilled by landing or a
 *    grab).
 *  - solid scenery: the insides of rocks and stage 3's tower are only
 *    background to the engine (attribute $C0, no wall or floor): Arthur can't
 *    get there, but Firebrand flies. A move that puts his body in one is
 *    undone (scenery_block): sideways he stops at its surface, rising he stops
 *    as under a ceiling, and dropping onto one refills the hover; resting
 *    on top of one, left/right walks him along it (as the hover steers).
 *  - the stage-end key is taken standing (fb_key_y): taken in flight it
 *    left him hanging in the air, the stage end never finishing.
 *  - the top of the screen is a ceiling too (screen_top): stage 6's boss room
 *    has no ceiling cells, and above a stage's map he walked on the terrain
 *    ring's wrapped copies of floors 512 px further down, off screen.
 *  - one attack: the lance's mechanics, drawn as the fireball (uploaded where
 *    the game uploads the lance art for each shot slot, $11711E); the HUD's
 *    weapon box shows the fireball, and its lives icons his head.
 *  - two hits: he starts each life with the armor flag on, so the first hit
 *    is Arthur's armored knockback (with its invincibility) and the second
 *    kills. Wounded (the flag off) he can't fly: his flight is 0 and the FLY
 *    gauge shows it spent until a wing heals him (the flag on again, his
 *    flight back at his level; the next wing raises it) or his next life.
 *    Vendetta's flaps are jumps and stay (its climbs need them).
 *  - boxes: weapon and armor pickups give 1000 points instead.
 *  - the end: stage 6 needs no cross (the game's check at $119D2E sees one),
 *    the fireball hurts Astaroth (cross-only for everyone else, glue.s
 *    hook_weapon_mask),
 *    and beating the final room shows Firebrand's ending (ending.c), then
 *    Firebrand's Quest Plus from stage 1 with the score and lives kept: the
 *    top starting rank and half the flight. Plus is in the Home menu once
 *    the quest has been cleared (saved in SRAM). */
#include "md.h"
#include "common.h"
#include "fly_art.h"

void dma_vram(u32 src, u16 bytes, u16 vram);
u32  gcall(u32 addr, u32 d0, u32 a3);   /* glue.s: jsr addr, a0=$FF0000 a4=$FF9000 a5=$FF9100 */
long wall_probe(u32 addr, u32 x, u32 y, u32 table);    /* glue.s: px into the wall, or -1 */
void jump_sfx(void);                    /* glue.s */
void score_event(u16 idx);              /* glue.s: score table entry idx */
int  vd_on(void);                       /* vendetta.c */
u16  vd_sat(volatile u16 *buf, u16 n);  /* vd_arthur.c: Arthur's sprites in Vendetta */

#define FB_BANK     0x3A0000UL          /* placed by tools/patch_gng.py from art/firebrand */
#define FB_FLAGS    ((const u8 *)0x3B6000UL)
#define FB_FIRE     0x3B6100UL
#define FB_MAPICON  0x3B6200UL          /* stage-map marker, 4 tiles */
#define FB_FIRE_ANIM 0x3B6300UL         /* the flying fireball's 4 shapes, then its 3 impact
                                           pictures, 0x100 bytes each */
#define FB_WING     0x3B7A00UL          /* the wing pickup: one 16x16 piece, 0x100 bytes */
#define ITEM_ART    0x29CA00UL          /* the game's item frames, 0x100 bytes each */
#define TORCH_F     0x0A                /* the torch pickup's 4 frames: drawn as the wing */
#define SPARK       0x298000UL          /* the game's hit spark, art frames 32-34 */
#define FROG        0x49200UL           /* the game's frog, 8 frames */
#define FB_FROG     0x3B6A00UL          /* the same, red like him (art/firebrand/src/frog.py) */
#define FIRE_HOLD   3                   /* frames a shape is shown (Demon's Crest's) */
#define MAP_TILE    0x69C               /* stage-map marker tiles (glue.s hook_map_marker) */
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
#define SCORE_1000  9                   /* the score table's entry 9 ($28F2E): 1000 */

enum { F_LEFT = 1, F_RIGHT = 2, F_PAL2 = 4, F_RUN = 8, F_FACES_LEFT = 16 };
enum { WALL_RIGHT = 1, WALL_LEFT = 2 };

static u8  hover_t, hovering, flap, walk_t;
static u8  flying;                      /* flight locked on: held up until hover_t runs out */
static u8  died;                        /* this life's death has taken its level */
static u8  item_made[2];                /* the item slot's weapon has been decided */
static u8  cling;                       /* the side of the wall he holds, 0 = none */
static u8  wall_jump;                   /* rising from a wall: no grab until the top */
static u8  jump_was;                    /* jump held last frame */
static u8  flaps, flapping;             /* Vendetta: flaps left in this jump; risen by one, not landed */
#define FLAPS       3
#define FLAP_SPEED  0x3C000             /* 3.75 px a frame up: ~30 px (Arthur's jump: 4.25, ~40 px) */
static u8  shots_was, cling_fire;       /* shots out last frame; frames of the cling-fire pose left */
#define CLING_FIRE  15                  /* Demon's Crest holds it about as long */
static s16 shown;                       /* bank frame in VRAM + 1, 0 = unknown */
static u32 shown_src;                   /* non-Firebrand frame (the frog) in VRAM */

int fb_on(void)
{
    return is_home() && (PERSIST->home_sub == HOME_FIREBRAND || PERSIST->home_sub == HOME_VENDETTA);
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

/* clinging to a wall or hovering: climbing on purpose (vendetta.c) */
int fb_lifting(void)
{
    return cling || hovering || flapping;
}

/* Flight: jump, then jump again in the air locks it on: he stays up (and
 * steers) until his flight runs out, DOWN drops him. Its length is the
 * flight level, FLY_MAX levels of a second each (half that in Firebrand's
 * Quest Plus), shown on the HUD as one wing a second, emptying as he flies;
 * landing or grabbing a wall fills it. A wing pickup raises the level,
 * a death takes one away, a new game or a continue starts at 1. */
#define FLY_MAX     4
#define FLY_DX      0x200               /* flight's sideways speed: 2 px a frame, every step the same */
static u8 fly_unit(void)                /* frames of flight one wing holds */
{
    u8 n = (RAM8(0xA10001) & 0x40) ? 50 : 60;
    return fb_plus_on() ? n / 2 : n;
}

static u8 fly_level(void)
{
    u8 l = PERSIST->fly_lv;
    return l < 1 ? 1 : l > FLY_MAX ? FLY_MAX : l;
}

/* frames of flight from a landing or a grab: none once he has been hit */
static u8 hover_max(void) { return ARMOR_SET ? 0 : fly_unit() * fly_level(); }

/* Vendetta's flaps a jump: three at levels 1-2 (its routes need three),
 * then one more a level */
static u8 flaps_max(void) { u8 l = fly_level(); return l < 3 ? 3 : l + 1; }

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
static int solid_at(u16 x, u16 y);

static int touch_wall(u8 side)
{
    u16 x = POS_X >> 8;
    long in = side == WALL_RIGHT ? wall_probe(0x8510, x + 2, POS_Y, 0x1486E)
                                : wall_probe(0x8538, x - 2, POS_Y, 0x1496E);
    if (in < 0) {
        /* Vendetta: solid scenery's faces too (stage 3's cave stone, the
         * towers' rock), where scenery_block stops his body (6 px each side) */
        u16 sx = side == WALL_RIGHT ? x + 8 : x - 8;
        return vd_on() && (solid_at(sx, POS_Y + 8) || solid_at(sx, POS_Y + 20));
    }
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
static u8 perched;                      /* held on top of solid scenery (frames left) */
static u8 prev_ok;
#define POS_Y16 RAM32(0xFF9400)         /* y 16.8; POS_Y is its pixel copy */

/* The top of the screen is a ceiling: his sprite's top stays on screen
 * (screen y = 224 + camera y - y). Arthur never jumps that high, so the
 * stages have no ceiling over their open tops (stage 6's boss room), and
 * above a stage's map the terrain ring holds other parts of the world. */
static u32 screen_top(u32 y)
{
    u32 top = (u32)(RAM16(0xFF9102) + 224) << 8;
    if (y <= top || RAM8(0xFF9459)) return y;
    if (JUMP_PHASE == 1) JUMP_PHASE = 2;    /* as under a ceiling, below */
    JUMP_SPEED = 0;
    POS_Y16 = top;
    POS_Y = (u16)(top >> 8);
    return top;
}

static void scenery_block(void)
{
    u32 x = POS_X & 0xFFFFFF, y = screen_top(POS_Y16);
    /* It stops his flight only: on the engine's floor he walks where Arthur
     * walks (the floor can stand him beside an edge stone, stage 3's cave at
     * x 1960, and every step from there was undone: held for good). Already
     * inside it where he was, moves are let be too, so he flies out. */
    if (RAM8(0xFF9459) || RAM8(0xFFC342) || !prev_ok || JUMP_PHASE == 0 || !body_solid(x, y) ||
        body_solid(prev_x, prev_y)) {
        /* still resting on top of it (it is just under him): perched */
        if (JUMP_PHASE == 2 && !RAM8(0xFF9459) && prev_ok && body_solid(x, y - (2 << 8))) perched = 2;
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
        if (y < prev_y) {               /* dropping onto it: can fly off again, */
            hover_t = hover_max();
            perched = 2;                /* and walk along its top (fb_frame) */
        }
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
    u8 in, jump, toward, leapt = 0;
    if (!fb_on()) return;
    WEAPON = 1;
    RAM8(0xFFC39C) = 0;                 /* no armor shatter: Arthur's armor pieces ($5572 -> $6700) */
    if (ARMOR_SET) {                    /* hit once: no flight left */
        hover_t = 0;
        flying = 0;
    }
    if (RAM8(0xFF9787)) item_made[0] = 0;   /* the items past state 0 */
    if (RAM8(0xFFCEA7)) item_made[1] = 0;
    if (RAM16(0xFFC570) && !died) {     /* dying: the flight level drops one */
        died = 1;
        if (PERSIST->fly_lv > 1) PERSIST->fly_lv--;
    }
    if (!RAM8(0xFFC305)) {              /* stage (re)start: VRAM is reloaded */
        shown = 0;
        shown_src = 0;
        hovering = 0;
        flying = 0;
        died = 0;
        cling = wall_jump = 0;
        hover_t = hover_max();
        flaps = flaps_max();
        flapping = 0;
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
        flying = 0;
        cling = wall_jump = 0;
        flapping = 0;
        if (JUMP_PHASE == 0) {
            hover_t = hover_max();
            flaps = flaps_max();
        }
        jump_was = jump;
        return;
    }
    if (cling) {
        if (toward && toward != cling) {
            cling = 0;                  /* pushed away: let go */
        } else if (jump && !jump_was) {
            leapt = 1;
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
        flying = 0;
        hover_t = hover_max();
        flaps = flaps_max();
        flapping = 0;
        hold_wall();
    }
    /* Vendetta: jump pressed again in the air is a flap, a smaller jump up
     * (FLAPS of them until he lands or grabs a wall): going back the way
     * Arthur came, his drops are climbs, and not all of them have a wall */
    if (!cling && !leapt && jump && !jump_was && flaps && vd_on()) {
        flaps--;
        flapping = 1;
        hovering = 0;
        if (hover_t) flying = 1;        /* and flight locks on: held up at the flap's top */
        JUMP_PHASE = 1;
        ON_GROUND = 0;
        JUMP_SPEED = FLAP_SPEED;
        JUMP_DIR = 0;
        JUMP_DX = 0;
        JUMP_POSE = 8;
        jump_sfx();
    }
    /* jump again in the air: flight locks on (a press, not a hold) */
    if (!cling && !leapt && jump && !jump_was && hover_t) flying = 1;
    if (!(in & 4)) flying = 0;          /* DOWN: drop */
    if (!hover_t) flying = 0;           /* run out: he falls */
    jump_was = jump;
    if (cling) return;
    if (perched) perched--;
    if ((JUMP_PHASE == 2 && flying) || (perched && JUMP_PHASE == 2)) {
        if (flying) {
            hover_t--;
            hovering = 1;
        } else {
            hovering = 0;
        }
        JUMP_SPEED = 0;                 /* this frame's fall moves 0 px */
        /* only the steering below moves him sideways: the jump's own sideways
         * motion went on too, 1 + 1.125 px a frame in steps of 2 and 3 */
        JUMP_DIR = 0;
        JUMP_DX = 0;
        /* steer at 2 px a frame, through the engine's walk moves (wall checks
         * included; the same calls Maximo's walk uses). Direction bits are
         * active low: 2 = right held, 1 = left held. Resting on top of solid
         * scenery (the engine's floor isn't there: he is held in his fall)
         * he walks along it the same way, and off its edge. */
        if ((G_P1 & 3) == 2) {
            RAM8(0xFF9006) = 1; RAM16(0xFF920A) = 0;
            gcall(0x11469C, flying ? FLY_DX : 288, 0x1486E);
        } else if ((G_P1 & 3) == 1) {
            RAM8(0xFF9006) = 2; RAM16(0xFF920A) = 0x800;
            gcall(0x1146CE, (u32)(s16)(flying ? -FLY_DX : -288), 0x1496E);
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

/* the stage-end key's contact context (hook_key_y): Arthur's y, or in the air
 * Firebrand's y moved far off, so he takes the key standing. The sequence the
 * key starts ($FFC305 = 3) moves no airborne player: taken in flight, he
 * hung in the air for good. */
void fb_key_y(u16 *ctx)
{
    ctx[1] = POS_Y;
    if (fb_on() && JUMP_PHASE) ctx[1] += 0x2000;
}

/* Wings: the pickups that raise Firebrand's flight level. Weapons make no
 * sense for him, so the game's weapon items (types 1-5: torch, lance, axe,
 * cross, knife) become wings as they are made, up to WINGS[stage] a stage,
 * and the stage's point item (type 6 + stage) after that. A wing is the
 * torch (type 1), drawn as the wing. Taken, it heals him if he has been hit
 * (fb_item), else raises his level and fills his flight; at FLY_MAX it is
 * 1000 points. The game makes a weapon item about
 * every 21 enemies (an item every 6th, 2 of its 7-step cycle weapons):
 * a run through stage 1 meets about 3. With 4 levels, a wing a stage
 * through stage 4 and two in 5 and 6 build him up as the stages get harder,
 * and leave something to win back a level lost in the last two. */
static const u8 WINGS[6] = { 1, 1, 1, 1, 2, 2 };

/* $116A7E (glue.s hook_item_new): item state 0, an item being made, in
 * either slot ($FF9780, $FFCEA0); runs again while its carrier gets ready,
 * so a slot's decision is kept until its state moves on (fb_frame) */
void fb_item_new(u8 *it)
{
    Persist *p = PERSIST;
    u8 t = it[6], k = it != (u8 *)0xFF9780, st = RAM8(0xFFC512);
    if (!fb_on() || t < 1 || t > 5 || st > 5) return;
    if (item_made[k]) return;
    item_made[k] = 1;
    if (p->fly_stage != st + 1) {       /* a new stage: its wings */
        p->fly_stage = st + 1;
        p->fly_given = 0;
    }
    if (p->fly_given < WINGS[st]) {
        p->fly_given++;
        it[6] = 1;                      /* a wing */
    } else {
        it[6] = 6 + st;                 /* the stage's point item */
    }
}

/* $1169DE (glue.s hook_item_art): the source of item frame `frame`
 * (off = frame * 256); the torch's frames show the wing for Firebrand */
u32 fb_item_art(u32 off, u32 frame)
{
    frame &= 0xFFFF;
    if (fb_on() && frame >= TORCH_F && frame < TORCH_F + 4) return FB_WING;
    return ITEM_ART + off;
}

/* $116472 / $116884: the item code is about to copy its context's armor and
 * weapon back to the game; a pickup changed them. A weapon taken is a wing. */
void fb_item(u8 *ctx)
{
    if (!fb_on()) return;
    if (ctx[17] != WEAPON) {
        if (ARMOR_SET) {                /* wounded: the wing heals him, flight back at his level */
            ARMOR_SET = 0;
            hover_t = hover_max();
        } else if (PERSIST->fly_lv < FLY_MAX) {
            PERSIST->fly_lv = fly_level() + 1;
            hover_t = hover_max();
        } else {
            score_event(SCORE_1000);
        }
    } else if (ctx[9] != ARMOR_SET) {
        score_event(SCORE_1000);
    }
    ctx[17] = WEAPON;
    ctx[9] = ARMOR_SET;
}

/* A 16x16 sprite picture (4 tiles, a column at a time) as the HUD's 2x2
 * plane tiles (a row at a time: top left, top right, bottom left, bottom
 * right), uploaded again whenever the game has put its own back */
static void hud_tiles(u32 src, const u16 *dst)
{
    static const u8 order[4] = { 0, 2, 1, 3 };
    for (int i = 0; i < 4; i++) {
        const u32 *t = (const u32 *)(src + 32 * order[i]);
        VDP_CTRLL = VRAM_R(dst[i] * 32 + 16);
        if (VDP_DATAL != t[4]) dma_vram((u32)t, 32, dst[i] * 32);
    }
}

/* The fireball's ball (the left 13 x 8 px of its leading 16x16 piece,
 * FB_FIRE) in the middle of a 16x16 box picture: 2 px (a byte) right, 4 px
 * down; byte bx (0-7) of row y of the picture */
static u8 fire_byte(int y, int bx)
{
    const u8 *src = (const u8 *)FB_FIRE;
    int sy = y - 4, sbx = bx - 1;
    if (sy < 0 || sy > 15 || sbx < 0) return 0;
    return src[((sbx >> 2) * 2 + (sy >> 3)) * 32 + (sy & 7) * 4 + (sbx & 3)];   /* a column at a time */
}

static u32 fire_long(int y, int tx)     /* a tile row: 4 bytes */
{
    return (u32)fire_byte(y, tx * 4) << 24 | (u32)fire_byte(y, tx * 4 + 1) << 16 |
           (u16)(fire_byte(y, tx * 4 + 2) << 8 | fire_byte(y, tx * 4 + 3));
}

/* The FLY gauge, on the right of the HUD across from TIME (plane A rows 2-3,
 * columns 26-29): FLY, and under it a wing for each second of flight left
 * and a spent wing for each second of his level used up. Its tiles are in
 * plane A's table rows 28-31 (tiles $770-$77F), never on screen and never
 * written in any stage (checked over all six). */
#define FLY_TILE    0x770               /* F L Y, wing, spent wing */
static void fly_hud(void)
{
    u16 unit = fly_unit(), lv = fly_level();
    u16 left = (hover_t + unit - 1) / unit;
    VDP_CTRLL = VRAM_R((FLY_TILE + 3) * 32 + 8);
    if (VDP_DATAL != fly_art[3 * 8 + 2]) {
        VDP_CTRLL = VRAM_W(FLY_TILE * 32);
        for (int i = 0; i < 5 * 8; i++) VDP_DATAL = fly_art[i];
    }
    VDP_CTRLL = VRAM_W(0xE000 + (2 * 64 + 26) * 2);
    VDP_DATAL = (u32)(0x8000 | FLY_TILE) << 16 | (0x8000 | (FLY_TILE + 1));
    VDP_DATA = 0x8000 | (FLY_TILE + 2);
    VDP_CTRLL = VRAM_W(0xE000 + (3 * 64 + 26) * 2);
    for (u16 k = 0; k < FLY_MAX; k++)
        VDP_DATA = k < left ? 0x8000 | (FLY_TILE + 3) : k < lv ? 0x8000 | (FLY_TILE + 4) : 0;
}

/* The HUD as Firebrand's: the weapon box (plane A rows 25-26, columns 15-16)
 * shows the fireball he spits instead of the lance, in tiles of its own (the
 * game redraws the box when the weapon changes); the lives icons (the game's
 * tiles $74F $752 / $753 $756, shown nowhere else) show his head (the stage
 * map's, FB_MAPICON, in his sprite's colours). */
static void draw_icon(void)
{
    static const u16 life[4] = { 0x74F, 0x752, 0x753, 0x756 };
    VDP_CTRLL = VRAM_R(ICON_TILE * 32 + 16);            /* row 4 of the top left tile */
    if (VDP_DATAL != fire_long(4, 0)) {
        VDP_CTRLL = VRAM_W(ICON_TILE * 32);
        for (int t = 0; t < 4; t++)                     /* top left, top right, bottom left, bottom right */
            for (int r = 0; r < 8; r++) VDP_DATAL = fire_long((t >> 1) * 8 + r, t & 1);
    }
    hud_tiles(FB_MAPICON, life);
    fly_hud();
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
 * left shot 15 px further back than a right one (over his body), so a new
 * left shot (+10 = 2) is moved SHOT_DX ahead to leave from his mouth too. The
 * arcade Red Arremer's mouth is SHOT_DY px below the lance's line: each new
 * shot is moved that much lower (its y, +6, counts up the screen). Moved, not
 * drawn elsewhere: what it hits is where it is drawn, and it stops at a
 * tombstone's face, where its impact shows. */
#define SHOT_DY 8
#define CROUCHED RAM8(0xFF944B)         /* crouched, the game's shot is already at his mouth */
#define SHOT_DX 14
#define HIT_DX  12                     /* the game tests a shot's hits this far behind its head:
                                           shots move this much further ahead, drawn this much back */
#define IMPACT_DX (-4)
static u8 fire_t;                       /* the fireball's animation clock */
static u8 shot_was[3];                  /* each weapon slot's active flag last frame */

static u32 fire_src(void) { return FB_FIRE_ANIM + (fire_t / FIRE_HOLD) * 0x100; }

static void fix_shots(volatile u16 *buf, u16 n)
{
    /* the fireball animates as in Demon's Crest: a new shape every FIRE_HOLD
     * frames, uploaded to each shot slot's tiles drawn this frame */
    int next = fire_t % FIRE_HOLD == FIRE_HOLD - 1;
    if (++fire_t == 4 * FIRE_HOLD) fire_t = 0;
    u8 fresh = 0;                       /* slots that started this frame: drawn where they were */
    u8 dy = CROUCHED ? 0 : SHOT_DY;     /* this frame's new shots are lowered by this */
    for (int k = 0; k < 3; k++) {
        u8 on = RAM8(0xFF9608 + 0x20 * k);
        if (on && !shot_was[k]) {
            fresh |= 1 << k;
            RAM8(0xFF9606 + 0x20 * k) -= dy;
            if (RAM8(0xFF960A + 0x20 * k) == 2) RAM32(0xFF9600 + 0x20 * k) -= (SHOT_DX + HIT_DX) << 8;
            else RAM32(0xFF9600 + 0x20 * k) += HIT_DX << 8;                                /* x 16.8 */
        }
        shot_was[k] = on;
    }
    /* only while shots are out (weapon slots at $FF9600, active flag at +8),
     * and only until all their pieces are found: a busy screen has ~60 sprites */
    u16 left = (RAM8(0xFF9608) ? 2 : 0) + (RAM8(0xFF9628) ? 2 : 0) + (RAM8(0xFF9648) ? 2 : 0);
    volatile u16 *e = buf, *end = buf + n * 4;
    for (; left && e < end; e += 4) {
        u16 a = e[2], t = a & 0x7FB;    /* both pieces of a slot: base and base + 4 */
        int k = t == 0x2A0 ? 0 : t == 0x2B0 ? 1 : t == 0x790 ? 2 : -1;   /* its weapon slot */
        if (k < 0) continue;
        if (RAM8(0xFF9608 + 0x20 * k) != 1) {          /* hit: the impact, on the wall's face */
            e[3] += a & 0x0800 ? IMPACT_DX : -IMPACT_DX;
            left--;
            continue;
        }
        if (!(a & 0x0800)) e[3] += a & 4 ? -16 : 16;
        if (fresh & 1 << k) {           /* this frame's sprites were placed before the move */
            e[0] += dy;
            if (a & 0x0800) e[3] -= SHOT_DX;
        } else {
            e[3] += a & 0x0800 ? HIT_DX : -HIT_DX;
        }
        if (next && !(a & 4)) dma_vram(fire_src(), 0x100, t * 32);
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
        if (src != shown_src) {
            shown_src = src;
            if (src >= FROG && src < FROG + 8 * 0x200) src += FB_FROG - FROG;
            dma_vram(src, 512, 0x6000);
        }
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
    if (!(f & (F_LEFT | F_RIGHT)) || !buf[0]) return vd_sat(buf, n) * 8;
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
    return vd_sat(buf, n) * 8;
}

/* $11711E: a shot slot's art upload (a0 = source). The lance is art frame 8
 * ($295000, flying right) and 9 ($295200, flying left, drawn flipped). */
u32 fb_shot_src(u32 src)
{
    if (!fb_on()) return src;
    if (src == 0x295000UL || src == 0x295200UL) return fire_src();
    if (src >= SPARK && src < SPARK + 3 * 0x200 && !(src & 0x1FF))     /* hitting: the impact */
        return FB_FIRE_ANIM + (4 + ((src - SPARK) >> 9)) * 0x100;
    return src;
}
