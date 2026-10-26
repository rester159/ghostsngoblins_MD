/* Stage 2's devils (enemy type 4: the ones that come out of the town's
 * windows and walk, hop and glide after Arthur), translated from the arcade's
 * handler ($B146) in place of the port's states 0 and 1 ($107A48), which had
 * no random, no walking off ledges (it turned round), no gliding, no dodging
 * of Arthur's weapons, and kept going off the screen (the arcade removes them
 * as soon as they leave it, $B25E).
 *
 * Arcade states (-$D, -$C, -$B = port +7, +8, +9), by subtype (-$E = +6):
 *   0/0 set up: subtype 0 waits until on screen ($B170, $B193); subtypes 1
 *       (windows) and 2 start at 1/4 or 1/5 with 2 in their live flag
 *       (weapons pass) ($B1EC)
 *   1/0 walk for 16-160 frames (random, $B2C3), stepping off ledges into a hop
 *   1/1 glide at the top of a hop for 60-180 frames (random, $B34C)
 *   1/2 hop up 32 or 48 px (random, $B37F) along a sine
 *   1/3 come down the other half, then fall 2 px a frame to the floor ($B3CD)
 *   1/4 the window opens (20 frames, sound $12), then 1/5's jump ($B41E)
 *   1/5 10 frames, then leap out at Arthur in a falling arc ($B4BD, $B521)
 *   while walking or gliding, a weapon coming at it from its side of Arthur
 *   makes it hop / come down ($B630); off the screen it's removed ($B25E);
 *   after 1200-3600 frames by rank it turns into a Red Arremer ($B245).
 * Dying (2) and removal (3) stay the port's.
 *
 * The arcade's fields live in the port slot: +12 velocity table (-4),
 * +13 direction / step (-2), +14 animation group = size class (-1, also +25),
 * +15 timer ($D), +32 base y ($6), +34 phase ($9), +36 hop height ($C),
 * +37 jump side ($F), +38/+39 step counter and reload ($10/$11), +40 the
 * emerging wait ($12), +41 Arthur more than 64 px away ($14), +42 the life timer ($1E),
 * +44/+45 the window's tile timer and step ($15/$16). Animation: the port's
 * scripts (+28 script, +26 timer, +30 frame; table $108158), set and stepped
 * where the arcade sets and steps its own ($906B, $9074). */
#include "md.h"

u8 arc_rand(void);
long tdv_floor(void *slot, void *ctx);
void tdv_sound(int id);

typedef struct {        /* the object pass context ($FFC700) */
    u16 camx, camy;     /* 0, 2 */
    u16 ax;             /* 4 Arthur */
    u16 ay;             /* 6 */
    u8  frame, slot, rank;  /* 8-10 */
} Ctx;

#define LIVE  p[4]
#define ONS   p[5]
#define SUB   p[6]
#define ST0   p[7]
#define ST1   p[8]
#define ST2   p[9]
#define VT    p[12]
#define DIR   p[13]
#define GRP   p[14]
#define TIM   p[15]
#define JSIDE p[37]
#define STEP  p[38]
#define SRLD  p[39]
#define EMRG  p[40]
#define FAR   p[41]
#define TILE  p[44]
#define TSTEP p[45]

static u16 rd16(const u8 *a) { return (u16)(a[0] << 8 | a[1]); }
static void wr16(u8 *a, u16 v) { a[0] = v >> 8; a[1] = v; }
#define XI rd16(p + 17)
#define YI rd16(p + 21)
#define SETY(v) wr16(p + 21, v)

/* velocity tables (x, y 8.8 per -2): $B230 walk; the leap at Arthur to the
 * right / left: $B593/$B5AB with him within 64 px, $B5C3/$B5DB farther; $B5F3 straight down */
static const s16 VEL0[2][2] = {{0x016D, 0}, {-0x016D, 0}};
static const s16 LEAPX[4][6] = {
    {0x0030, 0x004F, 0x0078, 0x00C0, 0x0198, 0x01E0},
    {-0x0030, -0x004F, -0x0078, -0x00C0, -0x0198, -0x01E0},
    {0x0048, 0x0060, 0x00C0, 0x01B0, 0x01E0, 0x01F8},
    {-0x0048, -0x0060, -0x00C0, -0x01B0, -0x01E0, -0x01F8}};
enum { VT_WALK, VT_LEAP_R, VT_LEAP_L, VT_LEAP_RF, VT_LEAP_LF, VT_DOWN };

static const u8 WALK_T[4] = { 0x78, 0xA0, 0x3C, 0x10 };    /* $B2BF */
static const u8 GLIDE_T[4] = { 0x3C, 0x5A, 0x78, 0xB4 };   /* $B348 */
static const u8 HOP_H[2] = { 0x20, 0x30 };                 /* $B37B */
static const u16 LIFE_T[4] = { 3600, 2700, 1800, 1200 };   /* $B1BD */
static const u16 DODGE[4][2] = {                           /* $B63E */
    {0x0080, 0x0100}, {0x0060, 0x00C0}, {0x0040, 0x0080}, {0x0020, 0x0040}};
/* $4140 (bank 4): half sine */
static const u8 SINE[256] = {
    0x00,0x02,0x03,0x05,0x06,0x08,0x09,0x0b,0x0c,0x0e,0x10,0x11,0x13,0x14,0x16,0x17,
    0x19,0x1a,0x1c,0x1d,0x1f,0x20,0x22,0x23,0x25,0x26,0x28,0x29,0x2b,0x2c,0x2e,0x2f,
    0x31,0x32,0x33,0x35,0x36,0x38,0x39,0x3a,0x3c,0x3d,0x3f,0x40,0x41,0x43,0x44,0x45,
    0x47,0x48,0x49,0x4a,0x4c,0x4d,0x4e,0x4f,0x51,0x52,0x53,0x54,0x55,0x56,0x58,0x59,
    0x5a,0x5b,0x5c,0x5d,0x5e,0x5f,0x60,0x61,0x62,0x63,0x64,0x65,0x66,0x67,0x68,0x69,
    0x6a,0x6a,0x6b,0x6c,0x6d,0x6e,0x6f,0x6f,0x70,0x71,0x71,0x72,0x73,0x73,0x74,0x75,
    0x75,0x76,0x76,0x77,0x78,0x78,0x79,0x79,0x7a,0x7a,0x7a,0x7b,0x7b,0x7c,0x7c,0x7c,
    0x7d,0x7d,0x7d,0x7d,0x7e,0x7e,0x7e,0x7e,0x7e,0x7f,0x7f,0x7f,0x7f,0x7f,0x7f,0x7f,
    0x7f,0x7f,0x7f,0x7f,0x7f,0x7f,0x7f,0x7f,0x7e,0x7e,0x7e,0x7e,0x7e,0x7d,0x7d,0x7d,
    0x7d,0x7c,0x7c,0x7c,0x7b,0x7b,0x7a,0x7a,0x7a,0x79,0x79,0x78,0x78,0x77,0x76,0x76,
    0x75,0x75,0x74,0x73,0x73,0x72,0x71,0x71,0x70,0x6f,0x6f,0x6e,0x6d,0x6c,0x6b,0x6a,
    0x6a,0x69,0x68,0x67,0x66,0x65,0x64,0x63,0x62,0x61,0x60,0x5f,0x5e,0x5d,0x5c,0x5b,
    0x5a,0x59,0x58,0x56,0x55,0x54,0x53,0x52,0x51,0x4f,0x4e,0x4d,0x4c,0x4a,0x49,0x48,
    0x47,0x45,0x44,0x43,0x41,0x40,0x3f,0x3d,0x3c,0x3a,0x39,0x38,0x36,0x35,0x33,0x32,
    0x31,0x2f,0x2e,0x2c,0x2b,0x29,0x28,0x26,0x25,0x23,0x22,0x20,0x1f,0x1d,0x1c,0x1a,
    0x19,0x17,0x16,0x14,0x13,0x11,0x10,0x0e,0x0c,0x0b,0x09,0x08,0x06,0x05,0x03,0x02};
#define sine(i) SINE[(u8)(i)]

/* the port's scripts for the arcade's ($108158: frame, next, time) */
enum { AN_WALK_R = 0x0B, AN_WALK_L = 0x0F, AN_EMERGE = 0x13, AN_OUT = 0x15, AN_FLY_R = 0x17, AN_FLY_L = 0x1B };
static void anim_set(u8 *p, u8 id) { p[28] = 0; p[29] = id; p[26] = 0; }
static void anim(u8 *p)                 /* $9074 */
{
    const u8 *e;
    if (p[26]) { p[26]--; return; }
    e = (const u8 *)0x108158 + 8 * rd16(p + 28);
    p[30] = e[0]; p[31] = e[1];
    p[28] = e[2]; p[29] = e[3];
    p[26] = e[4];
}
static void anim_dir(u8 *p, u8 r, u8 l) { anim_set(p, DIR ? l : r); }   /* $906B by -2 */

static void add24(u8 *a, s16 v)
{
    u32 t = ((u32)a[0] << 16 | (u32)a[1] << 8 | a[2]) + (u32)(long)v;
    a[0] = t >> 16; a[1] = t >> 8; a[2] = t;
}
static void move(u8 *p)                 /* $A427 */
{
    s16 vx, vy;
    switch (VT) {
    case VT_WALK: vx = VEL0[DIR & 1][0]; vy = 0; break;
    case VT_DOWN: vx = 0; vy = -0x01B7; break;
    default: vx = LEAPX[VT - 1][DIR < 6 ? DIR : 5]; vy = -0x01B7; break;
    }
    add24(p + 17, vx);
    add24(p + 21, vy);
}

static void face(u8 *p, const Ctx *c)   /* $B222 */
{
    DIR = (s16)XI >= (s16)c->ax;
    p[24] = DIR;
}

static int floor_at(u8 *p, const Ctx *c, s16 *adj)     /* $8CA7 */
{
    long r;
    wr16(p, XI); wr16(p + 2, YI);
    r = tdv_floor(p, (void *)c);
    *adj = (s16)r;
    return r != 0;
}

static void remove_off(u8 *p, const Ctx *c)    /* $8F62 */
{
    if ((u16)(XI - c->camx + 0x80) > 0x200 || (u16)(YI - c->camy + 0x40) > 0x180) {
        ST0 = 3; ST1 = 0; ST2 = 0;
    }
}

/* $8E41 now (the port's $BD9E with the class's box, $2AC3C) */
static void onscreen_now(u8 *p, const Ctx *c)
{
    const u16 *b = (const u16 *)(0x2AC3C + 8 * p[25]);
    ONS = (u16)(XI + b[0] - c->camx) <= b[1] && (u16)(YI + b[2] - c->camy) <= b[3];
}

static void init_walk(u8 *p, const Ctx *c)     /* $B170 */
{
    wr16(p + 32, YI);
    p[36] = 0x10;
    p[34] = 0; p[35] = 0;
    GRP = 0; p[25] = 0;
    face(p, c);
    anim_dir(p, AN_WALK_R, AN_WALK_L);
    VT = VT_WALK;
    ST1++;
}

static void life_start(u8 *p, const Ctx *c)    /* $B1A9 */
{
    wr16(p + 42, LIFE_T[(c->rank & 0x30) >> 4]);
    ST1 = 0;
    ST0++;
}

/* $B3B6: y = base + the sine of the phase x the height */
static void arc_y(u8 *p)
{
    u8 b = sine(p[34]);
    b = (u8)(b << 1);
    SETY(rd16(p + 32) + (u8)((u16)b * p[36] >> 8));
}

/* $B630 -> $B87E: a weapon coming at it from its side of Arthur (outside a
 * window around Arthur that narrows with the rank) */
static int dodge(u8 *p, const Ctx *c)
{
    const u16 *t = DODGE[(c->rank & 0x30) >> 4];
    u16 d = XI - c->ax;
    u8 e4 = d >> 8, e5;
    const u8 *w;
    int k;
    if ((u16)(d + t[0]) <= t[1]) return 0;
    w = *(const u8 **)0xFFA20C;
    for (k = 0; k < 4; k++, w += 32) {
        u16 dw, dy;
        if (!w[9]) continue;
        dw = rd16(w + 1) - c->ax;
        e5 = dw >> 8;
        if ((u16)(dw + 8) <= 0x10) continue;
        dy = YI - rd16(w + 5) + 0x1C;
        if (dy >= 0x2C) continue;
        JSIDE = dy >> 8;
        if (!((e5 ^ e4) & 0x80)) return 1;
    }
    return 0;
}

/* $B457: the window's tiles, 4 steps of 5 frames (the tiles themselves
 * aren't drawn: the port has no window art); 1 at the end */
static int window_tiles(u8 *p)
{
    if (!TILE) { TILE = 5; TSTEP++; }
    if (--TILE) return 0;
    return TSTEP >= 4;
}

/* ST1 4 ST2 2 and ST1 5 ST2 0 ($B4BD) */
static void emerge(u8 *p, const Ctx *c)
{
    if (--EMRG) { anim(p); return; }
    LIVE >>= 1;
    GRP = 2; p[25] = 2;
    anim_set(p, AN_OUT);
    face(p, c);
    JSIDE = DIR;
    DIR = 0;
    if ((u16)(c->ax - 10) <= XI && (u16)(c->ax + 10) >= XI) JSIDE = 2;
    FAR = 1;
    if ((u16)(c->ax - 0x40) <= XI && (u16)(c->ax + 0x40) >= XI) FAR = 0;
    ST2++;
    anim(p);
}

/* ST1 4 ST2 5, ST1 5 ST2 1 ($B521): the leap until it lands */
static void leap(u8 *p, const Ctx *c)
{
    s16 adj;
    if (floor_at(p, c, &adj)) {
        init_walk(p, c);
        ST1 = 0; ST2 = 0;
        return;
    }
    if (JSIDE < 2) {                    /* $B545 / $B564 */
        if (--STEP == 0) {
            if (DIR != 5) DIR++;
            STEP = SRLD;
        }
        VT = (JSIDE ? VT_LEAP_L : VT_LEAP_R) + (FAR ? 2 : 0);
    } else {                            /* $B583 */
        DIR = 0;
        VT = VT_DOWN;
    }
    move(p);
    anim(p);
    remove_off(p, c);
}

static void walk(u8 *p, const Ctx *c)  /* ST1 0 ($B276) */
{
    s16 adj;
    if (ST2 == 0) {                     /* $B2C3, then on into $B2DE */
        face(p, c);
        GRP = 0; p[25] = 0;
        anim_dir(p, AN_WALK_R, AN_WALK_L);
        TIM = WALK_T[arc_rand() & 3];
        ST2++;
    }
    anim(p);                            /* $B2DE */
    if (--TIM == 0) { ST1 = 2; ST2 = 0; }
    else {
        anim(p);
        move(p);
        SETY(YI - 1);
        if (!floor_at(p, c, &adj)) { ST1 = 2; ST2 = 0; }
        else SETY(YI + adj);
    }
    if (dodge(p, c)) { ST1 = 2; ST2 = 0; }
}

static void glide(u8 *p, const Ctx *c) /* ST1 1 ($B309) */
{
    if (ST2 == 0) {                     /* $B34C, then on into $B360 */
        anim_dir(p, AN_FLY_R, AN_FLY_L);
        TIM = GLIDE_T[arc_rand() & 3];
        ST2++;
    }
    anim(p);
    if (--TIM) move(p);
    else { ST1 = 3; ST2 = 0; }
    if (dodge(p, c)) { ST1 = 3; ST2 = 0; }
}

static void hop(u8 *p)                  /* ST1 2 ($B36F) */
{
    u16 ph;
    if (ST2 == 0) {                     /* $B37F, then on into $B3A1 */
        GRP = 2; p[25] = 2;
        anim_dir(p, AN_FLY_R, AN_FLY_L);
        wr16(p + 32, YI);
        p[34] = 0; p[35] = 0;
        p[36] = HOP_H[arc_rand() & 1];
        ST2++;
    }
    move(p);
    anim(p);
    ph = rd16(p + 34) + 0x400;
    wr16(p + 34, ph);
    if (ph & 0x8000) { ST1 = 1; ST2 = 0; return; }
    arc_y(p);
}

static void descend(u8 *p, const Ctx *c)   /* ST1 3 ($B3CD) */
{
    s16 adj;
    u16 ph;
    switch (ST2) {
    case 0:                             /* $B3DB, then on into $B3E3 */
        anim_dir(p, AN_FLY_R, AN_FLY_L);
        ST2++;
        /* fall through */
    case 1:                             /* $B3E3 */
        move(p);
        anim(p);
        ph = rd16(p + 34);
        wr16(p + 34, ph + 0x400);
        if ((u16)(ph + 0x400) < ph) { ST2++; break; }
        arc_y(p);
        if (floor_at(p, c, &adj)) SETY(YI + adj);
        break;
    default:                            /* $B402 */
        move(p);
        anim(p);
        SETY(YI - 2);
        if (floor_at(p, c, &adj)) { SETY(YI + adj); ST1 = 0; ST2 = 0; }
        break;
    }
}

static void window(u8 *p, const Ctx *c)    /* ST1 4 ($B41E) */
{
    switch (ST2) {
    case 0:                             /* $B432 */
        if (ONS) { TILE = 0; TSTEP = 0; tdv_sound(0x12); ST2++; }
        break;
    case 1:                             /* $B457, opening */
        if (window_tiles(p)) ST2++;
        break;
    case 2: emerge(p, c); break;
    case 3: TILE = 0; TSTEP = 0; ST2++;  /* $B510, closing, and on into $B51B */
        /* fall through */
    case 4: if (window_tiles(p)) ST2++;  /* $B51B */
        leap(p, c);
        break;
    default: leap(p, c); break;
    }
}

void tdevil_update(u8 *p, const Ctx *c)
{
    if (ST0 == 0) {
        if (SUB == 0) {
            if (ST1 == 0) init_walk(p, c);                      /* $B170 */
            else if ((u16)(XI - c->camx - 0x10) > 0xE0) anim(p);    /* $B193 */
            else life_start(p, c);
        } else {                                                /* $B1EC */
            LIVE <<= 1;
            p[25] = 0;
            onscreen_now(p, c);
            life_start(p, c);
            init_walk(p, c);
            STEP = SRLD = (u8)((u8)YI - (u8)c->ay) >> 3;
            EMRG = 10;
            anim_set(p, AN_EMERGE);
            anim(p);                    /* $3,X = the first entry at once */
            p[26] = 0; p[28] = 0; p[29] = AN_EMERGE;
            ST0 = 1; ST1 = SUB == 2 ? 5 : 4; ST2 = 0;
        }
    } else {
        switch (ST1) {                  /* $B238 */
        case 0: walk(p, c); break;
        case 1: glide(p, c); break;
        case 2: hop(p); break;
        case 3: descend(p, c); break;
        case 4: window(p, c); break;
        default:
            if (ST2 == 0) emerge(p, c); else leap(p, c);
            break;
        }
        if (!ONS) { ST0 = 3; ST1 = 0; ST2 = 0; }    /* $B25E */
        {                                           /* $B245 */
            u16 t = rd16(p + 42) - 1;
            wr16(p + 42, t);
            if (!t) {                   /* a Red Arremer, as the port did it */
                p[10] = 5; SUB = 2;
                ST0 = ST1 = ST2 = 0;
                LIVE = 1;
                wr16(p + 28, RAM16(0x4FECA));
                p[26] = 0;
                wr16(p + 30, RAM16(0x50420));
            }
        }
        remove_off(p, c);
    }
    wr16(p, XI);
    wr16(p + 2, YI);
}
