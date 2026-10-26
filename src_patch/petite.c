/* The Petite Devils (enemy type 2: stage 2's that come out of the rock face
 * by the waterfall, stage 5's that carry a fireball), translated from the
 * arcade's handler ($A89C: set-up $A8AC, play $AB4B) in place of the port's
 * states 0 and 1 ($3416AA in stage 2, $11AEE2 elsewhere), which homed on
 * Arthur in 8 directions for 900 frames, drew no random and never dropped
 * anything.
 *
 * As in satan.c, each devil keeps an image of the arcade's 48-byte slot
 * (`s`, s[n] = X-$10+n for the routines' X), so the code reads like the 6809
 * code. The port slot gets x/y, the live flag (+4 = -$10: 2 while it can't be
 * hit), the state (+7 = -$D: 0 set-up, 1 play, 3 remove) and the frame (+30,
 * from the arcade's animation entry). Dying (2) and removal (3) stay the
 * port's.
 *
 * Arcade states (-$D/-$C/-$B), by subtype (-$E):
 *   0/0 subtype 0 (stage 2): pick a place on the rock face that is on the
 *       screen from 9 lists ($AECE, $AF79), one entry a frame, alternating the
 *       direction of the scan per devil ($1577), never the last one used
 *       ($1574/$1578); then 0/1 ($A8C6): out, weapons pass (-$10 = 2)
 *   0   subtype 1 ($A8F9), subtype 2 ($A91C: weapons pass, a 0/1 from the
 *       random for an early drop, 64-95 frames before it may drop)
 *   1/0 coming out: 80-111 frames (random, $AD1E), 1/16 px a frame, open to
 *       weapons and 1.4 px a frame after 32 ($AB6F)
 *   1/1 four times: aim ($AD53: one of six turning plans by the direction to
 *       Arthur, $ADAC), drift at 0.38 px a frame for 48-95 frames by rank
 *       ($AD28), then turn toward the planned direction at 1.65 px (2.5 for
 *       subtype 1) a frame for 80-111 ($AD1E); then 1/3: fly off ($ACD3)
 *   1/2 after dropping its fireball (subtype 2, $AE0E: level with Arthur and
 *       more than 50 px away -> sideways, right above him -> down): a turn
 *       through 8 directions ($AC46), then 1/1 again
 *   subtype 0 is removed as soon as it is off the screen ($B25E), the others
 *   once they're out of range ($8F62); every 32 frames sound $0B ($798D).
 * The fireball is the port's shot type 6 (its orb art; the arcade's is sprite
 * $F7) moving as the arcade's shot type 8 (petite_shot_aim/_vel hooks in the
 * port's type-6 shot, $72B6/$72F2).
 *
 * Arcade inputs and their port equivalents (the object pass context, as for
 * tdevil.c): <$A0/<$A2 Arthur x/y +4/+6, <$9C/<$9E camera +0/+2, <$21 frame
 * +8, <$E0 slot counter +9, <$9A rank +10, <$A7/<$A8 shot pool $FFC220.
 * The arcade's animation scripts are kept (entries: sprite, attribute, time)
 * and each sprite maps to the port's frame with the same art (fd-ff, the wing
 * poses with the fireball, are frames 41-46 that bossart.c adds). */
#include "md.h"

u8 arc_rand(void);
void pd_sound(int id);

typedef struct {        /* the object pass context (24 bytes on the stack) */
    u16 camx, camy;     /* 0, 2 */
    u16 ax;             /* 4 Arthur */
    u16 ay;             /* 6 */
    u8  frame, slot, rank;  /* 8-10 */
} Ctx;

/* $1574 (last y), $1577 (scan direction), $1578 (last x) */
struct { u16 last_y; u8 toggle, pad; u16 last_x; } pd_glob;

static const Ctx *c;
static u8 *s;

#define FL   s[0x00]                    /* -$10 */
#define ONS  s[0x01]                    /* -$F  */
#define SUB  s[0x02]                    /* -$E  */
#define ST0  s[0x03]                    /* -$D  */
#define ST1  s[0x04]                    /* -$C  */
#define ST2  s[0x05]                    /* -$B  */
#define DIR  s[0x0E]                    /* -2   */
#define CLS  s[0x0F]                    /* -1   */
#define X(n) s[0x10 + (n)]

static u16 rd16(const u8 *p) { return (u16)(p[0] << 8 | p[1]); }
static void wr16(u8 *p, u16 v) { p[0] = v >> 8; p[1] = v; }
#define XI rd16(s + 6)                  /* LDD -$A,X */
#define YI rd16(s + 9)                  /* LDD -$7,X */
#define VT (s + 12)                     /* -4: velocity table */

/* $A9AF-$AB4A: the animation table by turning plan ($A9AF), the scripts
 * ($A9BF-$AA72) and the velocity tables ($AA73-$AB4A), as one block so that
 * the pointers the slot keeps can stay the arcade's */
static const u8 ROMD[412] = {
    0xa9,0xd9,0xa9,0xc5,0xa9,0xc5,0xa9,0xd9,0xaa,0x33,0xaa,0x1f,0xaa,0x1f,0xaa,0x33,
    0xf8,0x30,0x07,0xf9,0x30,0x07,0xfa,0x30,0x02,0xfb,0x30,0x01,0xfc,0x30,0x01,0xfb,
    0x30,0x81,0xa9,0xc5,0xf8,0x34,0x07,0xf9,0x34,0x07,0xfa,0x34,0x02,0xfb,0x34,0x01,
    0xfc,0x34,0x01,0xfb,0x34,0x81,0xa9,0xd9,0xfa,0x30,0x02,0xfb,0x30,0x01,0xfc,0x30,
    0x01,0xfb,0x30,0x01,0xfd,0x30,0x01,0xfe,0x30,0x01,0xff,0x30,0x02,0xfe,0x30,0x01,
    0xfa,0x34,0x02,0xfb,0x34,0x01,0xfc,0x34,0x01,0xfb,0x34,0x01,0xfd,0x34,0x01,0xfe,
    0x34,0x01,0xff,0x34,0x02,0xfe,0x34,0x81,0xa9,0xe7,0xf8,0x30,0x07,0xf9,0x30,0x07,
    0xf0,0x30,0x02,0xf1,0x30,0x01,0xf2,0x30,0x01,0xf1,0x30,0x81,0xaa,0x1f,0xf8,0x34,
    0x07,0xf9,0x34,0x07,0xf0,0x34,0x02,0xf1,0x34,0x01,0xf2,0x34,0x01,0xf1,0x34,0x81,
    0xaa,0x33,0xf0,0x30,0x02,0xf1,0x30,0x01,0xf2,0x30,0x01,0xf1,0x30,0x01,0xf3,0x30,
    0x01,0xf4,0x30,0x01,0xf5,0x30,0x02,0xf4,0x30,0x01,0xf0,0x34,0x02,0xf1,0x34,0x01,
    0xf2,0x34,0x01,0xf1,0x34,0x01,0xf3,0x34,0x01,0xf4,0x34,0x01,0xf5,0x34,0x02,0xf4,
    0x34,0x81,0xaa,0x41,0x00,0x10,0x00,0x00,0xff,0xf0,0x00,0x00,0x00,0x00,0x01,0x00,
    0x01,0x65,0x00,0x00,0xfe,0x9b,0x00,0x00,0x00,0x00,0x01,0x65,0x01,0xa6,0x00,0x00,
    0x01,0x85,0xff,0x5f,0x01,0x2a,0xfe,0xd6,0x00,0xa1,0xfe,0x7b,0x00,0x00,0xfe,0x5a,
    0xff,0x5f,0xfe,0x7b,0xfe,0xd6,0xfe,0xd6,0xfe,0x7b,0xff,0x5f,0xfe,0x5a,0x00,0x00,
    0xfe,0x7b,0x00,0xa1,0xfe,0xd6,0x01,0x2a,0xff,0x5f,0x01,0x85,0x00,0x00,0x01,0xa6,
    0x00,0xa1,0x01,0x85,0x01,0x2a,0x01,0x2a,0x01,0x85,0x00,0xa1,0x02,0x80,0x00,0x00,
    0x02,0x4f,0xff,0x0c,0x01,0xc4,0xfe,0x3c,0x00,0xf4,0xfd,0xb1,0x00,0x00,0xfd,0x80,
    0xff,0x0c,0xfd,0xb1,0xfe,0x3c,0xfe,0x3c,0xfd,0xb1,0xff,0x0c,0xfd,0x80,0x00,0x00,
    0xfd,0xb1,0x00,0xf4,0xfe,0x3c,0x01,0xc4,0xff,0x0c,0x02,0x4f,0x00,0x00,0x02,0x80,
    0x00,0xf4,0x02,0x4f,0x01,0xc4,0x01,0xc4,0x02,0x4f,0x00,0xf4,0x00,0x61,0x00,0x00,
    0x00,0x59,0xff,0xdb,0x00,0x44,0xff,0xbc,0x00,0x25,0xff,0xa7,0x00,0x00,0xff,0x9f,
    0xff,0xdb,0xff,0xa7,0xff,0xbc,0xff,0xbc,0xff,0xa7,0xff,0xdb,0xff,0x9f,0x00,0x00,
    0xff,0xa7,0x00,0x25,0xff,0xbc,0x00,0x44,0xff,0xdb,0x00,0x59,0x00,0x00,0x00,0x61,
    0x00,0x25,0x00,0x59,0x00,0x44,0x00,0x44,0x00,0x59,0x00,0x25};
#define ROMD_AT 0xA9AF
static u8 rb(u16 a) { return (u16)(a - ROMD_AT) < sizeof ROMD ? ROMD[a - ROMD_AT] : 0; }
static u16 rw(u16 a) { return (u16)(rb(a) << 8 | rb(a + 1)); }

/* $AF79: the rock-face lists (9 pointers, then count + (x, y) words) */
static const u8 LAVA[131] = {
    0xaf,0xef,0xaf,0xde,0xaf,0xd1,0xaf,0xc4,0xaf,0xb3,0xaf,0xaa,0xaf,0x99,0xaf,0x94,
    0xaf,0x8b,0x02,0x0e,0x48,0x00,0x98,0x0e,0x48,0x00,0xf4,0x01,0x0e,0x98,0x00,0x64,
    0x04,0x0e,0xf8,0x00,0x88,0x0e,0xf8,0x00,0xe8,0x0e,0xf8,0x01,0x48,0x0e,0xf8,0x01,
    0x88,0x02,0x0f,0x48,0x01,0x94,0x0f,0x48,0x01,0xc4,0x04,0x0f,0x78,0x00,0x54,0x0f,
    0x78,0x00,0xc4,0x0f,0x78,0x01,0x18,0x0f,0x78,0x01,0x54,0x03,0x0f,0xd8,0x00,0xf4,
    0x0f,0xd8,0x01,0x48,0x0f,0xd8,0x01,0x84,0x03,0x10,0x08,0x00,0x64,0x10,0x08,0x00,
    0xa8,0x10,0x18,0x01,0xa8,0x04,0x10,0x68,0x00,0x58,0x10,0x68,0x00,0xb8,0x10,0x58,
    0x01,0x08,0x10,0x68,0x01,0x68,0x03,0x10,0xd8,0x00,0xb4,0x10,0xd8,0x00,0xf4,0x10,
    0xd8,0x01,0x68};
#define LAVA_AT 0xAF79
static u8 lb(u16 a) { return (u16)(a - LAVA_AT) < sizeof LAVA ? LAVA[a - LAVA_AT] : 0; }
static u16 lw(u16 a) { return (u16)(lb(a) << 8 | lb(a + 1)); }

static const u8 T_AD3F[4] = { 0x30, 0x30, 0x25, 0x10 };    /* drift time base by rank */
static const u8 T_AD43[16] = { 0,0,1,0, 0,0,1,0, 1,0,0,1, 0,0,1,0 };  /* early drop */
/* $ADAC: turning plan by the direction to Arthur; $ADCC: (turn, start, end) */
static const u8 T_ADAC[16] = { 5,1,1,1, 1,0,0,0, 4,3,3,3, 2,2,2,2 };
static const u8 PLAN[6][3] = {
    {0x00, 0x04, 0x0A}, {0x01, 0x04, 0x0E}, {0x02, 0x0C, 0x0E},
    {0x03, 0x0C, 0x0A}, {0x00, 0x09, 0x0B}, {0x01, 0x0F, 0x0D}};
static const u8 T_ACF0[4] = { 0x08, 0x00, 0x00, 0x08 };    /* fly-off direction */

static void add24(u8 *p, u16 v)
{
    u32 a = (u32)p[0] << 16 | (u32)p[1] << 8 | p[2];
    a = (a + (u32)(long)(s16)v) & 0xFFFFFF;
    p[0] = a >> 16; p[1] = a >> 8; p[2] = a;
}

static void move(void)                  /* $A427 */
{
    u16 u = rd16(VT) + 4 * DIR;
    add24(s + 6, rw(u));
    add24(s + 9, rw(u + 2));
}

static void anim(void)                  /* $9074 (class 0: 3-byte entries) */
{
    u16 y;
    u8 b;
    if (X(2)) { X(2)--; return; }
    y = rd16(&X(0));
    wr16(&X(3), y);
    y += 3;
    b = rb(y - 1);
    if (b & 0x80) { y = rw(y); b &= 0x7F; }
    X(2) = b;
    wr16(&X(0), y);
}

static void anim_set(u16 a) { wr16(&X(0), a); wr16(&X(3), a); X(2) = 0; }

static void remove_far(void)            /* $8F62 */
{
    if ((u16)(XI - c->camx + 0x80) > 0x200 || (u16)(YI - c->camy + 0x40) > 0x180) {
        ST0 = 3; ST1 = 0; ST2 = 0;
    }
}

static void onscreen_now(void)          /* $8E41, class 0 ($8E67) */
{
    ONS = 0;
    if ((u16)(XI + 8 - c->camx) <= 0x110 && (u16)(YI - c->camy) <= 0x100) ONS = 1;
}

/* $8FE4: the direction (0-15) from the slot to Arthur, as satan.c's */
static u8 dir_to_arthur(void)
{
    static const u8 T[5][4] = {
        {0x0F, 0x09, 0x01, 0x07}, {0x00, 0x08, 0x00, 0x08}, {0x0D, 0x0B, 0x03, 0x05},
        {0x0C, 0x0C, 0x04, 0x04}, {0x0E, 0x0A, 0x02, 0x06}};
    u8 e1 = 0, a, d, b = 0, cy;
    u16 dx = c->ax - XI, dy = c->ay - YI, p;
    int i, t;
    if ((s16)dx < 0) { dx = -dx; e1 = 1; }
    if ((s16)dy < 0) { dy = -dy; e1 |= 2; }
    a = dy; d = dx;
    for (i = 0; i < 8; i++) {           /* $FED8 */
        u8 c2;
        cy = a >> 7; a <<= 1;
        c2 = b >> 7; b = (u8)(b << 1 | cy);
        a++;
        t = (int)b - d - c2;
        b = (u8)t;
        if (t < 0) { a--; b += d; }
    }
    p = (u16)a * 100;
    if (p >= 600) return T[3][e1];
    if (p >= 150) return T[2][e1];
    if (p >= 75) return T[4][e1];
    return T[(u8)dx >> 2 > b ? 1 : 0][e1];
}

static void common_init(void)           /* $A961 */
{
    X(0x1C) = SUB;
    CLS = 0;
    wr16(VT, 0xAA73);
    X(0x15) = 4;
    X(0x0B) = 2;
    wr16(&X(0x13), c->ay);
    ST0 = 1; ST1 = 0; ST2 = 0;
}

static void hover_time(void)            /* $AD1E: 80-111 */
{
    X(6) = (arc_rand() & 0x1F) + 0x50;
}

static void drift_time(void)            /* $AD28 */
{
    u8 a = T_AD3F[(c->rank >> 4) & 3];
    X(6) = a + (arc_rand() & 0x2F);
}

static void close_above(void)           /* $ADDE: right above Arthur, slower turns */
{
    u16 d = c->ax - 0x1E;
    if (d > XI) return;
    d += 0x3C;
    if (d < XI) return;
    if (c->ay > YI) return;
    X(7) = X(8) = 0x0A;
}

static void aim(void)                   /* $AD53 */
{
    const u8 *u;
    u8 a = s[10] - (u8)c->ay, b;
    if (s[10] < (u8)c->ay) a = (u8)(-a + 0x0A);
    a >>= 1;
    if (X(0x1B)) a >>= 1;
    a >>= 1;
    if (a) {
        X(7) = X(8) = a;
        u = PLAN[T_ADAC[dir_to_arthur()]];
    } else {
        X(7) = X(8) = 5;
        u = PLAN[c->ax < XI ? 5 : 4];
    }
    X(0x0B) = u[0];
    DIR = u[1];
    X(0x12) = u[2];
    close_above();
    b = X(0x0B);
    if (X(0x0C)) b += 4;
    anim_set(rw(ROMD_AT + 2 * b));
}

static void turn(void)                  /* $ACF4 / $AD09 by the plan */
{
    if (--X(7)) return;
    if (DIR == X(0x12)) return;
    DIR = (X(0x0B) & 1 ? DIR - 1 : DIR + 1) & 0x0F;
    X(7) = X(8);
}

static void move_far(void)              /* $A985 */
{
    move();
    if (YI <= 0x35) wr16(s + 9, 0x0036);
    if (X(0x1C) == 0 && XI >= 0x11ED && XI < c->ax) {
        X(0x0B) = 0;
        ST1 = 3; ST2 = 0;
    }
}

static void fly(void)                   /* $ABBE */
{
    move_far();
    anim();
    remove_far();
}

/* $AE70: the fireball (shot_out: the pool, below), then the slot's side */
static void shot_out(u8 dir);
static int shots_free(void);
static void drop(u8 dir)
{
    shot_out(dir);
    X(0x0C) = 1;
    X(0x11) = dir;
    ST1 = 2; ST2 = 0;
}

static void drop_check(void)            /* $AE0E */
{
    u16 d;
    if (!X(0x0D) || !shots_free()) return;
    d = c->ay + 0x10;
    if (d >= YI && (u16)(d - 0x10) <= YI) {         /* level with him */
        d = c->ax - 0x32;
        if (d > XI || (u16)(d + 0x64) < XI) {       /* and more than 50 px away */
            drop(c->ax < XI ? 1 : 0);
            return;
        }
    }
    d = c->ax - 5;                                  /* $AE3A: right above him */
    if (d > XI) return;
    d += 10;
    if (d < XI) return;
    d = c->ay + 0x3C;
    if (d < YI) drop(2);
}

static void drop_tick(void)             /* $ADFE */
{
    if (--X(0x0E) == 0) X(0x0D) = 1;
    if (X(0x0C) == 0) drop_check();
}

static void pick_list(u16 u)            /* $AEFC */
{
    u16 y = lw(u);
    u8 b;
    wr16(&X(8), u + 2);
    b = lb(y++);
    X(0x0A) = b;
    if (X(6) == 0) y += (u8)(b - 1) * 4;
    wr16(&X(0x0B), y);
}

static void rock_face(void)             /* $AECE */
{
    if (ST2 == 0) {                     /* $AEDA */
        wr16(&X(3), 0xA631);
        s[6] = 0;
        s[9] = 0;
        pd_glob.toggle = (pd_glob.toggle + 1) & 1;
        X(6) = pd_glob.toggle;
        pick_list(LAVA_AT);
        X(7) = 9;
        ST2++;
        return;
    }
    {                                   /* $AF12 */
        u16 y = rd16(&X(0x0B)), ex = lw(y), ey = lw(y + 2);
        if (c->camx <= ex && (u16)(c->camx + 0x100) >= ex
            && (u16)(c->camy + 0x20) <= ey && (u16)(c->camy + 0xE0) >= ey
            && (pd_glob.last_y != ey || pd_glob.last_x != ex)) {
            wr16(s + 6, ex); pd_glob.last_x = ex;
            wr16(s + 9, ey); pd_glob.last_y = ey;
            ST1 = 1;
            return;
        }
        y -= 4;
        if (X(6)) y += 8;
        wr16(&X(0x0B), y);
        if (--X(0x0A)) return;
        pick_list(rd16(&X(8)));
        if (--X(7)) return;
        ST0 = 3; ST1 = 0;
    }
}

static void setup(void)                 /* state 0 ($A8AC) */
{
    u16 y;
    switch (SUB) {
    case 0:
        if (ST1 == 0) { rock_face(); return; }
        onscreen_now();                 /* $A8C6 */
        FL <<= 1;
        common_init();
        y = 0xAA19; DIR = 0;
        if ((s16)XI > (s16)c->ax) { y = 0xAA2D; DIR = 1; }
        anim_set(y);
        wr16(&X(0x19), 0xAA8B);
        X(0x1B) = 0;
        X(0x0C) = 1;
        return;
    case 1:                             /* $A8F9 */
        common_init();
        DIR = 2;
        anim_set(0xAA41);
        wr16(&X(0x19), 0xAACB);
        X(0x1B) = 1;
        X(0x0C) = 1;
        return;
    default:                            /* $A91C */
        FL <<= 1;
        common_init();
        y = 0xA9BF; DIR = 0;
        if ((s16)XI > (s16)c->ax) { y = 0xA9D3; DIR = 1; }
        anim_set(y);
        wr16(&X(0x19), 0xAA8B);
        X(0x1B) = 0;
        X(0x0F) = T_AD43[arc_rand() & 0x0F];
        X(0x0E) = (arc_rand() & 0x1F) + 0x40;
        X(0x0D) = 0;
        X(0x0C) = 0;
        return;
    }
}

static void come_out(void)              /* 1/0 ($AB6F) */
{
    if (ST2 == 0) {                     /* $AB7B */
        hover_time();
        X(0x18) = X(6);
        ST2++;
    }
    if (X(6) == 5) {                    /* $AB94 */
        X(6)--;
        if (X(0x0F) == 0) { X(0x0D) = 1; drop_tick(); }
    } else if (--X(6) == 0) {
        ST1++; ST2 = 0;
        return;
    }
    if ((u8)(X(0x18) - X(6)) == 0x20) { FL = 1; wr16(VT, 0xAA7F); }
    move();
    anim();
    remove_far();
}

static void hover(void)                 /* 1/1 ($ABCF) */
{
    switch (ST2) {
    case 0:                             /* $ABDF */
        if (--X(0x15) == 0) { ST1 = 3; ST2 = 0; return; }
        drift_time();
        wr16(VT, 0xAB0B);
        wr16(&X(0x13), c->ay);
        aim();
        anim_set(X(0x0C) ? 0xAA41 : 0xA9E7);
        ST2++;
        return;
    case 1:                             /* $AC0D */
        drop_tick();
        if (--X(6) == 0) { wr16(VT, rd16(&X(0x19))); ST2++; return; }
        break;
    case 2:                             /* $AC25 */
        hover_time();
        wr16(&X(0x13), c->ay);
        aim();
        ST2++;
        return;
    default:                            /* $AC33 */
        drop_tick();
        if (--X(6) == 0) { ST2 = 0; return; }
        break;
    }
    turn();                             /* $AC1C -> $ABBC */
    fly();
}

static void after_drop(void)            /* 1/2 ($AC46) */
{
    u16 u;
    switch (ST2) {
    case 0:                             /* $AC56 */
        wr16(VT, rd16(&X(0x19)));
        X(0x10) = 2;
        u = 0xAA1F; DIR = 0x0F;
        if (X(0x11)) {
            u = 0xAA33; DIR = 9;
            if (X(0x11) != 1) { u = 0xAA41; DIR = 0x0C; ST2++; }
            ST2++;
        }
        ST2++;
        wr16(&X(0), u); wr16(&X(3), u);
        return;
    case 1:                             /* $AC8C */
        if (--X(0x10) == 0) {
            X(0x10) = 2;
            if (DIR == 8) { ST1 = 1; ST2 = 0; return; }
            DIR--;
        }
        break;
    case 2:                             /* $ACA7 */
        if (--X(0x10) == 0) {
            X(0x10) = 1;
            if (DIR == 0x0F) { ST1 = 1; ST2 = 0; return; }
            DIR++;
        }
        break;
    default:                            /* $ACBC */
        if (--X(0x10) == 0) {
            X(0x10) = 2;
            if (DIR == 4) { ST1 = 1; ST2 = 0; return; }
            DIR -= 8;
        }
        break;
    }
    fly();
}

static void fly_off(void)               /* 1/3 ($ACD3) */
{
    if (ST2 == 0) {
        DIR = T_ACF0[X(0x0B) & 3];
        wr16(VT, rd16(&X(0x19)));
        ST2++;
        return;
    }
    fly();
}

static void play(void)                  /* state 1 ($AB4B) */
{
    if (((c->frame + c->slot) & 0x1F) == 0) pd_sound(0x0B);
    switch (ST1) {
    case 0: come_out(); break;
    case 1: hover(); break;
    case 2: after_drop(); break;
    default: fly_off(); break;
    }
    if (X(0x1C) == 0 && !ONS) { ST0 = 3; ST1 = 0; ST2 = 0; }   /* $B25E */
}

/* the port's frame for the arcade's sprite (left = attribute bit 2) */
static u8 port_frame(u16 e)
{
    /* fd-ff: the frames bossart.c adds after the port's 41 (pd_src/pd_entry) */
    static const u8 R[16] = { 15, 16, 17, 29, 30, 31, 0, 0, 1, 2, 3, 4, 5, 41, 42, 43 };
    static const u8 L[16] = { 21, 22, 23, 37, 38, 39, 0, 0, 7, 8, 9, 10, 11, 44, 45, 46 };
    u8 code = rb(e), attr = rb(e + 1);
    if ((code & 0xF0) != 0xF0) return 0;
    return (attr & 4 ? L : R)[code & 15];
}

/* the arcade handler for states 0 and 1 on the image (HOST builds: tools/re/test_petite.py) */
void petite_step(u8 *img, const Ctx *x)
{
    s = img;
    c = x;
    if (ST0 == 0) setup(); else play();
}

#ifndef HOST
/* ---- the port side ---------------------------------------------------- */

/* the fireball into the port's shot pool ($FFC220 = <$A7/<$A8) as its type 6
 * with +8 = $D8 (petite_shot_aim / petite_shot_vel_sel: the arcade's shot
 * type 8, direction +9: 0 right, 1 left, 2 down; speed by rank +11). The
 * fractions are left from the slot's last shot, as in the arcade. */
static int shots_free(void) { return RAM16(0xFFC220) != 0; }
static void shot_out(u8 dir)
{
    u16 *pool = (u16 *)0xFFC220;
    u8 *p, **sp;
    u16 y = YI - 10;
    sp = *(u8 ***)0xFFC228;
    p = *--sp;
    *(u8 ***)0xFFC228 = sp;
    pool[0]--;
    p[11] = (c->rank & 0x30) >> 4;
    wr16(p, XI);
    RAM32(p + 16) = (u32)XI << 8 | p[19];
    wr16(p + 2, y);
    RAM32(p + 20) = (u32)y << 8 | p[23];
    p[7] = 0; p[8] = 0xD8; p[9] = dir;
    p[4] = 1; p[5] = 0;
    p[10] = 6;
}

#define NREC 6
typedef struct { u8 *slot; u8 s[48]; } Rec;
static Rec rec[NREC];

static Rec *bind(u8 *p, int *fresh)
{
    Rec *r, *k = 0;
    for (r = rec; r < rec + NREC; r++) {
        if (r->slot == p) { *fresh = 0; return r; }
        if (!k && (!r->slot || r->slot[10] != 2 || !r->slot[4])) k = r;
    }
    if (!k) k = rec;
    k->slot = p;
    *fresh = 1;
    return k;
}

/* $10C99A (from petite_entry, states 0 and 1; p = the slot, x = the context) */
void petite_update(u8 *p, const Ctx *x)
{
    int fresh, k;
    Rec *r = bind(p, &fresh);
    u8 f;
    s = r->s;
    c = x;
    /* a new devil: the slot was just spawned (the port's state 0) and the
     * image isn't in the arcade's set-up for it */
    if (fresh || (p[7] == 0 && ST0 != 0)) {
        fresh = 1;
        for (k = 0; k < 48; k++) s[k] = 0;
        FL = p[4];
        SUB = p[6];
        s[6] = p[17]; s[7] = p[18]; s[8] = p[19];
        s[9] = p[21]; s[10] = p[22]; s[11] = p[23];
        X(5) = 2;
    }
    /* -$F: the port's pass recomputes +5 as the arcade's $8E41 (every 4
     * frames by frame + slot counter, the same box for class 0); +5 is only
     * forced to 0 in the set-up, where the arcade's flag isn't read */
    ONS = p[5];
    petite_step(s, x);
    f = port_frame(rd16(&X(3)));
    p[4] = FL;
    p[5] = f ? ONS : 0;                 /* the port can't draw frame 0 (fault $87) */
    p[7] = ST0;
    p[8] = 0; p[9] = 0;
    p[16] = 0; p[17] = s[6]; p[18] = s[7]; p[19] = s[8];
    p[20] = 0; p[21] = s[9]; p[22] = s[10]; p[23] = s[11];
    wr16(p, XI);
    wr16(p + 2, YI);
    p[24] = DIR;
    p[25] = CLS;
    wr16(p + 30, f);
    wr16(p + 28, f);                    /* the port's death goes on from this frame */
    p[26] = 0;
    p[36] = 0; p[37] = 0;               /* its death timer starts from 0 */
}
#else
int host_free = 1, host_nshot; u8 host_shot[16];
static int shots_free(void) { return host_free; }
static void shot_out(u8 dir) { if (host_nshot < 16) host_shot[host_nshot] = dir; host_nshot++; }
#endif

/* the fireball's speeds (the arcade's shot type 8: $5D6F -> $5D77/$5D83/$5D8F
 * by rank), as the port's 16-direction table (0 right, 8 left, 4 down) */
const s16 petite_shot_vel[4][16][2] = {
    {{0x0190, 0}, {0}, {0}, {0}, {0, -0x0200}, {0}, {0}, {0}, {-0x0190, 0}},
    {{0x0190, 0}, {0}, {0}, {0}, {0, -0x0200}, {0}, {0}, {0}, {-0x0190, 0}},
    {{0x0200, 0}, {0}, {0}, {0}, {0, -0x0210}, {0}, {0}, {0}, {-0x0200, 0}},
    {{0x0220, 0}, {0}, {0}, {0}, {0, -0x0230}, {0}, {0}, {0}, {-0x0220, 0}}};
