/* Firebrand's Vendetta: Arthur, the last boss, in stage 1's graveyard
 * (docs/FIREBRAND_VENDETTA.md).
 *
 * When Firebrand reaches the graveyard's left end (the camera at the stage's
 * left limit), Arthur leaps in from the left edge and the screen locks: the
 * camera stays (vendetta_glue.s vd_cam_xgap, vd_arena) and Firebrand stays
 * on it. Arthur is his own small engine here, not the player's: flat ground,
 * a walk, a jump, a crouch, and thrown lances, drawn with the game's own
 * frames of him (ARTHUR_B, uploaded to A_TILE) and of the lance.
 *  - two suits: ARMOR_HP fireballs take his armour off (he is knocked back
 *    in his boxers), BOXERS_HP more kill him; each hit leaves him blinking
 *    and untouchable for a moment;
 *  - armoured, he keeps his distance and throws lances straight, standing,
 *    crouching or at the top of a jump when Firebrand is at that height, and
 *    jumps or ducks Firebrand's fireballs;
 *  - in his boxers he is faster, rushes closer, and throws daggers aimed at
 *    Firebrand wherever he is, three at a time;
 *  - touching him or a lance kills Firebrand (one hit, as everywhere in his
 *    campaigns); a fireball and a lance that meet both go.
 * Firebrand's death restarts the stage as anywhere; Arthur waits at the
 * arena with his armour back. The stage time stands still during the
 * fight. Arthur's death: his skeleton falls apart, then the ending
 * (vendetta.c vd_ending). */
#include "md.h"
#include "common.h"

typedef signed long s32;

void dma_vram(u32 src, u16 bytes, u16 vram);   /* glue.s */
void score_event(u16 idx);              /* glue.s */
void vd_sound(int id);                  /* vendetta_glue.s */
void vd_ending(void);                   /* vendetta.c */

#define CAM_X       RAM16(0xFF9100)
#define CAM_Y       RAM16(0xFF9102)
#define FB_X        ((u16)(RAM32(0xFF9000) >> 8))
#define FB_Y        RAM16(0xFF9004)     /* his sprite's top; feet 32 px below (y is up) */
#define PHYS(n)     RAM8(0xFFC300 + (n))    /* the player's physics block */
#define INVULN      PHYS(9)

#define ARTHUR_B    0x40000UL           /* the game's frames of him, 512 bytes each */
#define LANCE_ART   0x295000UL          /* the lance flying right: two 16x16 pieces */
#define A_TILE      0x7A0               /* VRAM $F400: the gap after the third shot's tiles */
#define L_TILE      0x7B0
#define SCORE_1000  8

#define GROUND      62                  /* the graveyard's floor at its left end (his y standing) */
#define ARENA_L     12
#define ARENA_R     244
#define FB_MAX_X    232
#define ARMOR_HP    14
#define BOXERS_HP   14
#define JUMP_V      0x440               /* the player's jump (8.8 px a frame) */
#define GRAVITY     0x3A
#define NLANCE      3

/* frames by suit and facing: stand, run 1-4, jump up, jump down, throw,
 * crouch, crouch throw, hurt (the left ones are the right ones mirrored) */
enum { F_STAND, F_RUN, F_JUMP = 5, F_FALL, F_THROW, F_CROUCH, F_CTHROW, F_HURT, F_N };
static const u8 frames[2][2][F_N] = {
    { { 50, 49, 50, 51, 52, 53, 54, 55, 56, 58, 22 },     /* boxers, right */
      { 64, 63, 64, 65, 66, 67, 68, 69, 70, 71, 23 } },   /* boxers, left */
    { {  0,  1,  2,  3,  4,  5,  6,  7,  9, 11, 22 },     /* armour, right */
      { 16, 39, 40, 41, 42, 43, 44, 45, 19, 48, 23 } },   /* armour, left */
};
static const u8 bones[2][5] = { { 24, 26, 27, 30, 31 }, { 25, 28, 29, 32, 33 } };

enum { B_OFF, B_ENTER, B_FIGHT, B_HURT, B_DYING, B_DEAD };

static u8  st, armor, hp, face, inv, crouch, act, anim;
static s32 ax, ay, vx, vy;              /* 8.8; ay is his sprite's top, as Firebrand's y */
static u16 t, think, cool, shown;       /* shown: the frame in VRAM + 1 */
static u16 seed;
static struct { s32 x, y; s16 vx, vy; u8 live; } lance[NLANCE];
static u8  lance_loaded;
u8 vd_arena;                            /* the fight is on: the camera holds (vendetta_glue.s) */

static u8 rnd(void)
{
    seed = seed * 25173 + 13849;
    return seed >> 8;
}

static s16 px(s32 v) { return (s16)(v >> 8); }

void vd_boss_reset(void)
{
    st = B_OFF;
    vd_arena = 0;
    shown = 0;
    lance_loaded = 0;
    for (int i = 0; i < NLANCE; i++) lance[i].live = 0;
}

int vd_boss_on(void) { return st != B_OFF; }

/* Firebrand hit, as an enemy's touch ($5A48): unless blinking or already hit */
static void hit_firebrand(void)
{
    if (INVULN || !(PHYS(4) & 1) || PHYS(5) != 1) return;
    PHYS(4) <<= 1;
    PHYS(5) = 3;
    PHYS(6) = 0;
    PHYS(7) = 0;
}

static int fb_touch(s16 x0, s16 x1, s16 y0, s16 y1)   /* a box (y up) against his body */
{
    s16 fx = FB_X, fy = FB_Y;
    return fx + 7 > x0 && fx - 7 < x1 && fy - 4 > y0 && fy - 28 < y1;
}

static int body(s16 *x0, s16 *x1, s16 *y0, s16 *y1)
{
    s16 x = px(ax), y = px(ay);
    *x0 = x - 9; *x1 = x + 9;
    *y1 = crouch ? y - 14 : y - 2;
    *y0 = y - 31;
    return 1;
}

static int on_ground(void) { return ay <= (GROUND << 8) && vy <= 0; }

static void jump(s16 dx)
{
    vy = JUMP_V;
    vx = dx;
    crouch = 0;
    act = 0;
}

static int lances_out(void)
{
    int n = 0;
    for (int i = 0; i < NLANCE; i++) n += lance[i].live;
    return n;
}

/* a throw: straight in his armour, aimed at Firebrand in his boxers */
static void throw_lance(void)
{
    s16 dir = face ? -1 : 1;
    s16 sx = px(ax) + dir * 12, sy = px(ay) - (crouch ? 22 : 12);
    for (int i = 0; i < NLANCE; i++) {
        if (lance[i].live) continue;
        lance[i].live = 1;
        lance[i].x = (s32)sx << 8;
        lance[i].y = (s32)sy << 8;
        if (armor) {
            lance[i].vx = dir * 0x500;
            lance[i].vy = 0;
        } else {
            /* towards his middle, 6 px a frame: the larger axis gets 6 and
             * the other its share (a divide only on a throw) */
            s16 dx = FB_X - sx, dy = (FB_Y - 16) - sy;
            s16 adx = dx < 0 ? -dx : dx, ady = dy < 0 ? -dy : dy;
            if (dx * dir < 0) { dx = dir; adx = 1; }       /* never backwards */
            if (adx >= ady) {
                lance[i].vx = dir * 0x600;
                lance[i].vy = (s16)((s32)dy * 0x600 / adx);
            } else {
                lance[i].vy = dy < 0 ? -0x600 : 0x600;
                lance[i].vx = (s16)((s32)dx * 0x600 / ady);
            }
        }
        act = 12;                       /* the throwing pose */
        cool = armor ? 40 + (rnd() & 31) : 22 + (rnd() & 15);
        vd_sound(5);
        return;
    }
}

/* Firebrand's fireballs: the game's weapon slots ($FF9600, 32 bytes each:
 * x, y 16.8 at +0, +4; +8 allocated, +9 on screen). y is the top of the
 * shot's 16 px pieces: their middle is 8 px below (a shot from a standing
 * player flies at the height of his head). */
#define SHOT(k) ((volatile u8 *)(0xFF9600 + 32 * (k)))
#define SHOT_X(q) ((s16)(u16)(RAM32((u32)(q)) >> 8))
#define SHOT_Y(q) ((s16)(u16)(RAM32((u32)(q) + 4) >> 8) - 8)
static void shot_gone(volatile u8 *q)   /* as a shot that hit ($BF14) */
{
    q[8] <<= 1;
    q[0x1E] = 0;
    q[0xC] = 2;
    q[0xD] = 1;
}

static void hurt(void)
{
    vd_sound(0x0F);
    if (--hp) {
        inv = armor ? 40 : 30;
        return;
    }
    if (armor) {                        /* the armour goes: knocked back in his boxers */
        armor = 0;
        hp = BOXERS_HP;
        inv = 60;
        st = B_HURT;
        vy = 0x300;
        vx = face ? 0x180 : -0x180;
        crouch = 0;
        act = 0;
        score_event(SCORE_1000);
        return;
    }
    st = B_DYING;                       /* the knight falls */
    t = 0;
    vx = vy = 0;
    ay = (s32)GROUND << 8;
    crouch = act = 0;
    inv = 0;
    for (int i = 0; i < NLANCE; i++) lance[i].live = 0;
    vd_sound(0x1B);
    for (int i = 0; i < 5; i++) score_event(SCORE_1000);
}

static void fireballs(void)
{
    s16 x0, x1, y0, y1;
    body(&x0, &x1, &y0, &y1);
    for (int k = 0; k < 3; k++) {
        volatile u8 *q = SHOT(k);
        if (!(q[8] & q[9] & 1)) continue;
        s16 sx = SHOT_X(q), sy = SHOT_Y(q);
        for (int i = 0; i < NLANCE; i++) {          /* fire and steel cancel out */
            s16 lx = px(lance[i].x), ly = px(lance[i].y);
            if (lance[i].live && lx - sx < 14 && sx - lx < 14 && ly - sy < 10 && sy - ly < 10) {
                lance[i].live = 0;
                shot_gone(q);
                break;
            }
        }
        if (!(q[8] & 1)) continue;
        if (st == B_DYING || inv) continue;
        if (sx + 8 > x0 && sx - 8 < x1 && sy + 6 > y0 && sy - 6 < y1) {
            shot_gone(q);
            hurt();
            return;
        }
    }
}

/* the nearest fireball coming at him at his height: px away, or 0. A shot
 * flies away from Firebrand, so it comes at Arthur from Firebrand's side. */
static s16 incoming(void)
{
    s16 best = 0, side = FB_X - px(ax);
    for (int k = 0; k < 3; k++) {
        volatile u8 *q = SHOT(k);
        if (!(q[8] & q[9] & 1)) continue;
        s16 sx = SHOT_X(q), sy = SHOT_Y(q);
        s16 d = sx - px(ax);
        s16 h = px(ay) - sy;            /* below his sprite's top */
        if (h < -6 || h > 32) continue;
        if ((d < 0) != (side < 0)) continue;   /* already past him */
        if (d < 0) d = -d;
        if (!best || d < best) best = d;
    }
    return best;
}

static void think_fight(void)
{
    s16 dx = FB_X - px(ax), adx = dx < 0 ? -dx : dx;
    s16 fh = FB_Y - px(ay);             /* how far above him Firebrand is */
    int ground = on_ground();
    if (act) act--;
    if (cool) cool--;
    if (ground && !act) face = dx < 0;
    /* dodge: jump a fireball, or duck one at head height */
    if (ground) {
        s16 d = incoming();
        if (d && d < (armor ? 64 : 88) && !crouch && (rnd() & 7) < (armor ? 5 : 7)) {
            if (rnd() & 3) { jump(armor ? 0 : (FB_X < px(ax) ? -0x1C0 : 0x1C0)); return; }
            crouch = 18;
        }
    }
    if (crouch && ground) crouch--;
    /* throw */
    if (!cool && lances_out() < (armor ? 2 : NLANCE)) {
        s16 lh = fh - (crouch ? -10 : 0);
        if (!armor) {
            if (adx > 24) throw_lance();
        } else if (lh > -20 && lh < 16) {
            throw_lance();
        } else if (ground && fh > 16 && fh < 72 && adx < 140 && !(rnd() & 7)) {
            jump(0);                    /* up to his height, then throw at the top */
        }
    }
    if (!ground) return;
    /* move: hold his distance, rush closer in his boxers */
    if (!think) {
        think = (armor ? 20 : 10) + (rnd() & 15);
        {
            s16 want = armor ? 96 : 56;
            s16 spd = armor ? 0x120 : 0x1C0;
            u8 r = rnd();
            if (adx > want + 24) vx = dx < 0 ? -spd : spd;
            else if (adx < want - 24) vx = dx < 0 ? spd : -spd;
            else vx = r & 1 ? 0 : (r & 2 ? spd : -spd);
            if (!armor && fh > 24 && (r & 0x1C) == 0) jump(vx);
            if (armor && (r & 0x70) == 0) crouch = 24;
        }
    } else {
        think--;
    }
    if (crouch) vx = 0;
}

static void move(void)
{
    ax += vx;
    if (st != B_ENTER) {
        if (px(ax) < ARENA_L) { ax = (s32)ARENA_L << 8; vx = 0; }
        if (px(ax) > ARENA_R) { ax = (s32)ARENA_R << 8; vx = 0; }
    }
    if (vy || ay > (GROUND << 8)) {
        ay += vy;
        vy -= GRAVITY;
        if (ay <= (GROUND << 8) && vy < 0) {
            ay = (s32)GROUND << 8;
            vy = 0;
            if (st != B_FIGHT) vx = 0;
            if (st == B_ENTER || st == B_HURT) { st = B_FIGHT; think = 20; vx = 0; }
        }
    }
}

static void lances(void)
{
    s16 cx = CAM_X, cy = CAM_Y;
    for (int i = 0; i < NLANCE; i++) {
        if (!lance[i].live) continue;
        lance[i].x += lance[i].vx;
        lance[i].y += lance[i].vy;
        s16 lx = px(lance[i].x), ly = px(lance[i].y);
        if (lx < cx - 16 || lx > cx + 272 || ly < cy - 16 || ly > cy + 240) { lance[i].live = 0; continue; }
        if (fb_touch(lx - 12, lx + 12, ly - 4, ly + 4)) hit_firebrand();
    }
}

/* the fight starts: Firebrand at the graveyard's left end */
static void start(void)
{
    st = B_ENTER;
    vd_arena = 1;
    armor = 1;
    hp = ARMOR_HP;
    face = 0;
    inv = 0;
    crouch = act = 0;
    cool = 60;
    think = 0;
    ay = (s32)GROUND << 8;
    if (FB_X < 128) {                   /* in from the side Firebrand is away from */
        ax = (s32)264 << 8;
        face = 1;
        jump(-0x1C0);
    } else {
        ax = (s32)-8 << 8;
        jump(0x1C0);
    }
    seed ^= RAM16(0xFF7DFC);
}

/* The duel is one on one: the graveyard's monsters on screen leave
 * (state 3, the removal; type 17, the stage's off-screen fixtures, stays) */
static void clear_monsters(void)
{
    for (int k = 0; k < 40; k++) {
        volatile u8 *p = (volatile u8 *)(0xFFB800 + 48 * k);
        if ((p[4] & 1) && p[5] && p[10] != 17 && p[7] < 2) p[7] = 3;
    }
}

/* once a frame of play in stage 1 (vendetta.c vd_frame); left: the camera
 * is at the stage's left limit and Firebrand is in play */
void vd_boss(int left)
{
    if (st == B_OFF) {
        if (left && FB_X < 200 && !PHYS(0x42)) start();
        return;
    }
    /* Firebrand stays on the locked screen, short of where the camera
     * would follow him (240 px in, vendetta_glue.s) */
    if (FB_X > FB_MAX_X) RAM32(0xFF9000) = (RAM32(0xFF9000) & 0xFF000000) | ((u32)FB_MAX_X << 8);
    if (inv) inv--;
    anim++;
    clear_monsters();
    switch (st) {
    case B_FIGHT:
        if (!PHYS(0x42)) think_fight();
        /* fall through */
    case B_ENTER:
    case B_HURT:
        move();
        break;
    case B_DYING:
        if (++t > 150) st = B_DEAD, t = 0;
        break;
    case B_DEAD:
        if (++t == 90) vd_ending();
        return;
    }
    lances();
    if (st < B_DYING) {
        s16 x0, x1, y0, y1;
        fireballs();
        body(&x0, &x1, &y0, &y1);
        if (st != B_ENTER && fb_touch(x0, x1, y0, y1)) hit_firebrand();
    }
}

static int frame_now(void)
{
    int f;
    if (st == B_DYING || st == B_DEAD) {
        int k = t / 16;
        return bones[face][k > 4 ? 4 : k];
    }
    if (st == B_HURT) return frames[armor][face][F_HURT];
    if (!on_ground()) f = vy > 0 ? F_JUMP : F_FALL;
    else if (crouch) f = act ? F_CTHROW : F_CROUCH;
    else if (act) f = F_THROW;
    else if (vx) f = F_RUN + ((anim >> 3) & 3);
    else f = F_STAND;
    return frames[armor][face][f];
}

static u16 add(volatile u16 *buf, u16 n, s16 y, u16 size, u16 tile, s16 x)
{
    if (n >= 64 || x < -32 || x > 256 || y < -32 || y > 224) return n;
    buf[n * 4 + 0] = 128 + y;
    buf[n * 4 + 1] = size | (buf[1] & 0x7F);
    buf[n * 4 + 2] = tile;
    buf[n * 4 + 3] = 128 + x;
    buf[1] = (buf[1] & 0xFF00) | n;    /* drawn just after Firebrand */
    return n + 1;
}

/* At the sprite-table DMA (firebrand.c fb_sat, the Z80 bus held): Arthur
 * and his lances after Firebrand's sprites. Returns the new count. */
u16 vd_sat(volatile u16 *buf, u16 n)
{
    s16 cx = CAM_X, cy = CAM_Y;
    if (st == B_OFF) return n;
    if (!lance_loaded) {
        dma_vram(LANCE_ART, 256, L_TILE * 32);
        lance_loaded = 1;
    }
    for (int i = 0; i < NLANCE; i++) {
        if (!lance[i].live) continue;
        s16 x = px(lance[i].x) - cx, y = 224 + cy - px(lance[i].y) - 8;
        if (lance[i].vx >= 0) {
            n = add(buf, n, y, 0x0500, 0x8000 | L_TILE, x - 16);
            n = add(buf, n, y, 0x0500, 0x8000 | (L_TILE + 4), x);
        } else {                        /* the picture mirrored: the pieces trade places */
            n = add(buf, n, y, 0x0500, 0x8800 | (L_TILE + 4), x - 16);
            n = add(buf, n, y, 0x0500, 0x8800 | L_TILE, x);
        }
    }
    if (inv & 2) return n;              /* blinking */
    {
        int f = frame_now();
        if (f + 1 != shown) {
            dma_vram(ARTHUR_B + (u32)f * 0x200, 512, A_TILE * 32);
            shown = f + 1;
        }
        n = add(buf, n, 224 + cy - px(ay), 0x0F00, 0x8000 | A_TILE, px(ax) - cx - 16);
    }
    return n;
}
