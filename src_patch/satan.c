/* The arcade's Satan (enemy type 6, stages 5 and 6), translated from the
 * arcade's handler ($BED5: init $BEF1, wake-up $BF1E, ground states $BF4C,
 * flight states $C0B5) instead of the port's own one ($110520), which took
 * its choices from the rank byte $FFA208 and never flew.
 *
 * Each Satan keeps an image of the arcade's 48-byte enemy slot (`s`, the
 * arcade's offsets: s[n] = X-$10+n for the routines' X), so the code below
 * reads like the 6809 code it comes from. The port slot gets the results:
 * x/y, the live/shielded flags (+4 = the arcade's -$10: 1 live, $81 wings
 * closed = weapons blocked, which the port's weapon code already honours),
 * the state (+7 = -$D: 0 init/asleep, 1 awake, 3 remove) and the frame.
 * The port keeps its own drawing (frames 1/2 flying, 3/4 wings closed), hit
 * points, death (+7 = 2) and removal/key (+7 = 3).
 *
 * Arcade direct-page inputs and their port equivalents:
 *   <$A0/<$A2 Arthur x/y   $FFA204 / $FFA230 (set at the start of the update pass)
 *   <$9C/<$9E camera x/y   $FFA200 / $FFA202
 *   <$21 frame counter     $FFA206 (rng_tick)
 *   <$9A rank              $FFC501
 *   $051F Arthur crouching $FF944B
 *   -$F on screen          +5 (the port's $BD9E = the arcade's $8E41, same
 *                          4-frame schedule)
 *   <$A7/<$A8 shot pool    $FFC220 (free count, stack at +8), slots $FFC100
 *
 * HOST builds (tools/re/test_satan.py) compile only the core against the
 * arcade's recorded inputs. */
#include "md.h"

typedef signed long s32;

typedef struct {
    u16 ax, ay;             /* <$A0, <$A2 */
    u16 camx, camy;         /* <$9C, <$9E */
    u8  c21, rank, crouch;  /* <$21, <$9A, $051F */
} SatanIn;

u8 arc_rand(void);                      /* arcrand.c: the arcade's $68F9 */
static void satan_fire(u8 *s);          /* $C24C */
static const SatanIn *in;
static u8 counted;                      /* set by $BF5F (the arcade's <$B5 count) */

/* the arcade slot image */
#define FL   s[0x00]                    /* -$10 */
#define ONS  s[0x01]                    /* -$F  */
#define ST0  s[0x03]                    /* -$D  */
#define ST1  s[0x04]                    /* -$C  */
#define ST2  s[0x05]                    /* -$B  */
#define FAC  s[0x0E]                    /* -2   */
#define X(n) s[0x10 + (n)]
/* anim (visual only): which of the arcade's scripts is set */
#define ANIM X(0)
enum { AN_WRAP = 1, AN_FLAP, AN_FLYL, AN_FLYR };

static u16 rd16(const u8 *p) { return (u16)(p[0] << 8 | p[1]); }
static void wr16(u8 *p, u16 v) { p[0] = v >> 8; p[1] = v; }
#define XI rd16(s + 6)                  /* LDD -$A,X: x high:pixel */
#define YI rd16(s + 9)                  /* LDD -$7,X */

/* $C092 / $C0A3: a signed 8.8 step added to the 16.8 x or y */
static void add24(u8 *p, u16 v)
{
    u32 a = (u32)p[0] << 16 | (u32)p[1] << 8 | p[2];
    a = (a + (u32)(s32)(s16)v) & 0xFFFFFF;
    p[0] = a >> 16; p[1] = a >> 8; p[2] = a;
}
#define ADDX(v) add24(s + 6, v)
#define ADDY(v) add24(s + 9, v)

/* $C063/$C066: one of four table bytes by the random */
static u8 pick4(const u8 *t) { return t[arc_rand() & 3]; }
static const u8 T_C06E[4] = { 0x2F, 0x3C, 0x5A, 0x2F };    /* phase lengths */
static const u8 T_C072[4] = { 0x32, 0x2D, 0x28, 0x2F };    /* shot gaps */
static const u8 T_C358[4] = { 0x20, 0x10, 0x18, 0x10 };    /* back-off lengths */
static const u8 T_C30C[4] = { 0x1F, 0x15, 0x1A, 0x10 };    /* return-dash lengths */
static const u8 T_BF91[4] = { 0xB4, 0xA0, 0x8C, 0x78 };    /* ground time by rank */
static const u16 T_BFE4[4] = { 0x0070, 0xFF90, 0x0070, 0xFF90 };  /* drift */
static const u16 T_C304[4] = { 0x0300, 0xFD00, 0x0400, 0xFC00 };  /* return dash */
static const u16 T_C354[2] = { 0xFEB0, 0x0150 };                  /* back-off */
static const u16 T_C18B[4] = { 0xFFE8, 0x0018, 0x0020, 0x0018 };  /* swoop target dy */
static const u16 T_C193[4] = { 0xFFF0, 0x0010, 0x0018, 0x0010 };  /* ... Arthur crouching */
/* $C19B: the straight dash, 3.5 px/frame in 16 directions (x, y) */
static const u16 T_C19B[16][2] = {
    {0x0380, 0x0000}, {0x033B, 0xFEAA}, {0x0279, 0xFD87}, {0x0156, 0xFCC5},
    {0x0000, 0xFC80}, {0xFEAA, 0xFCC5}, {0xFD87, 0xFD87}, {0xFCC5, 0xFEAA},
    {0xFC80, 0x0000}, {0xFCC5, 0x0156}, {0xFD87, 0x0279}, {0xFEAA, 0x033B},
    {0x0000, 0x0380}, {0x0156, 0x033B}, {0x0279, 0x0279}, {0x033B, 0x0156}};
/* swoop speeds (left, right) by rank: $4D09 -> $4D19.. and, for the second
 * half of a swoop, $4D11 -> $4D29.. The slot keeps the arcade's pointer. */
static const u16 T_VEL[8][2] = {
    {0xFD00, 0x0300}, {0xFCE0, 0x0320}, {0xFCB0, 0x0350}, {0xFC90, 0x0370},
    {0xFCC0, 0x0340}, {0xFCA0, 0x0360}, {0xFC80, 0x0380}, {0xFC00, 0x0400}};
#define VEL_PTR(i) (0x4D19 + 4 * (i))
static const u16 *vel(u16 ptr) { return T_VEL[((ptr - 0x4D19) >> 2) & 7]; }
/* $4140 (bank 4): half sine, 0..$7F..1 */
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

/* $FEF0: the 16-bit restoring division (quotient replaces the dividend),
 * with the 6809's carry handling */
static u16 div16(u16 dvd, u16 dvs)
{
    u16 rem = 0;
    int i;
    for (i = 0; i < 16; i++) {
        u16 c = dvd >> 15, c2;
        s32 t;
        dvd = (u16)(dvd << 1);
        c2 = rem >> 15;
        rem = (u16)(rem << 1 | c);
        dvd |= 1;
        t = (s32)rem - dvs - c2;
        rem = (u16)t;
        if (t < 0) { dvd &= ~1; rem = (u16)(rem + dvs); }
    }
    return dvd;
}

/* $8FE4: direction 0-15 from the slot to Arthur (0 right, 4 down, 8 left,
 * 12 up), via the 8-bit division $FED8 on the low bytes of |dx|, |dy| */
static u8 dir_to_arthur(const u8 *s)
{
    static const u8 T[5][4] = {
        {0x0F, 0x09, 0x01, 0x07}, {0x00, 0x08, 0x00, 0x08}, {0x0D, 0x0B, 0x03, 0x05},
        {0x0C, 0x0C, 0x04, 0x04}, {0x0E, 0x0A, 0x02, 0x06}};
    u8 e1 = 0, a, d, b = 0, c;
    u16 dx = in->ax - XI, dy = in->ay - YI, p;
    int i, t;
    if ((s16)dx < 0) { dx = -dx; e1 = 1; }
    if ((s16)dy < 0) { dy = -dy; e1 |= 2; }
    a = dy; d = dx;
    for (i = 0; i < 8; i++) {           /* $FED8 */
        u8 c2;
        c = a >> 7; a <<= 1;
        c2 = b >> 7; b = (u8)(b << 1 | c);
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

/* $8F62: out of range of the camera -> remove (-$D = 3) */
static void range_check(u8 *s)
{
    if ((u16)(XI - in->camx + 0x80) > 0x200 || (u16)(YI - in->camy + 0x40) > 0x180) {
        ST0 = 3; ST1 = 0; ST2 = 0;
    }
}

/* $C26E: keep it above the ground line near the bottom of a map */
static void floor_clamp(u8 *s)
{
    if (in->camy <= 0x2E) {
        u16 d = 0x47 - in->camy - YI;
        if ((s16)d >= 0) wr16(s + 9, YI + (d & 0xFF));
    }
}

/* $C285: off the screen -> dash back onto it (3/4 px a frame), then land */
static void return_dash(u8 *s)
{
    if (!X(0x1F)) {
        if ((s16)(in->camx - 0x20) > (s16)XI) { X(0x16) = 0; ANIM = AN_FLYR; }
        else if ((s16)(in->camx + 0x120) < (s16)XI) { X(0x16) = 1; ANIM = AN_FLYL; }
        else if ((s16)in->camy > (s16)YI) X(0x16) = 2;
        else if ((s16)(in->camy + 0x100) < (s16)YI) X(0x16) = 3;
        else return;
        X(0x1E) = T_C30C[in->c21 & 3];
        X(0x1F) = 1;
    }
    if (--X(0x1E) == 0) { ST1 = 0; ST2 = 1; X(0x1F) = 0; return; }
    if (X(0x16) < 2) ADDX(T_C304[X(0x16)]); else ADDY(T_C304[X(0x16)]);
}

/* $C310: Arthur within 48 px in x -> back away from him for a while */
static void back_off(u8 *s)
{
    for (;;) {
        if (!X(0xE) && (u16)(XI - in->ax + 0x30) < 0x60) {
            X(0x17) = pick4(T_C358);
            X(0xE) = 1;
            ANIM = AN_FLAP;
        }
        if (!X(0xE)) return;
        if (--X(0x17)) { ADDX(T_C354[(s16)(in->ax - XI) >= 0 ? 0 : 1]); return; }
        X(0xE) = 0;
    }
}

/* $BFEC: turn towards Arthur */
static void face(u8 *s)
{
    u8 a = XI >= in->ax;
    if (a != FAC) { FAC = a; ST2 = 2; }
}

/* $C001: shots while open; every so often the wings close for 30 frames */
static void wings(u8 *s)
{
    switch (X(0x10)) {
    case 0:
        if (ONS && --X(0x12) == 0) { satan_fire(s); X(0x12) = pick4(T_C072); }
        if (--X(0x1A) == 0) X(0x10)++;
        break;
    case 1:
        ANIM = AN_WRAP;
        FL = 0x81;
        if (--X(0x1B) == 0) { X(0x10)++; FL = 1; }
        break;
    case 2:
        ANIM = AN_FLAP;
        X(0x10) = 0;
        X(0x1B) = 0x1E;
        X(0x1A) = pick4(T_C06E);
        X(0x12) = 5;
        break;
    }
}

/* -$D = 1, -$C = 0: on the ground / hovering ($BF4C) */
static void ground(u8 *s)
{
    switch (ST2) {
    case 0: counted = 1; ST2++; break;              /* $BF5F: INC <$B5 (bosses to kill) */
    case 1:                                         /* $BF64 */
        X(0x13) = T_BF91[X(0x1C) & 3];
        X(0x10) = 0;
        X(0x1B) = 0x1E;
        X(0x1A) = pick4(T_C06E);
        X(0x1D) = 0;
        X(0xF) = 0;
        FAC = in->ax >= XI;
        ST2++;
        break;
    case 2: ANIM = AN_FLAP; ST2++;                  /* $BF95, on into $BF9D */
        /* fall through */
    case 3:                                         /* $BF9D */
        return_dash(s);
        if (X(0x1F)) break;
        back_off(s);
        if (X(0xE)) {
            if (--X(0x13) == 0) goto fly;
            break;
        }
        face(s);
        wings(s);
        if (--X(0x13) == 0) {
fly:        ST1 = 1; ST2 = 0; FL = 1;
            break;
        }
        if ((in->c21 & 0x7F) == 0x7F) X(0xF) = arc_rand() & 3;   /* $BFCA */
        if (X(0xF) < 2) ADDX(T_BFE4[X(0xF) & 3]); else ADDY(T_BFE4[X(0xF) & 3]);
        floor_clamp(s);
        break;
    }
    range_check(s);
}

/* -$D = 1, -$C = 1: flight ($C0B5) */
static void flight(u8 *s)
{
    u16 d;
    const u16 *u;
    return_dash(s);
    if (X(0x1F) || !ST1) return;
    switch (ST2) {
    case 0:                                         /* $C0DA: pick a swoop */
        wr16(&X(0xC), in->ax);
        if (dir_to_arthur(s) & 7) {
            if ((s16)(YI - in->ay) < 0) {           /* below Arthur: straight at him */
                FAC = dir_to_arthur(s);
                ST2 = 3;
                break;
            }
        } else
            X(0x1D) = 1;                            /* level with him */
        d = XI - in->ax;
        if ((s16)d < 0) d = -d;
        wr16(&X(0x18), VEL_PTR(X(0x1C) & 3));
        d = div16((u16)(d << 8 | d >> 8), vel(rd16(&X(0x18)))[1]);   /* frames to reach him */
        X(0x15) = div16(0x7F00, d) >> 8;            /* phase step */
        FAC = XI < in->ax;
        ANIM = FAC ? AN_FLYR : AN_FLYL;
        d = in->ay + (in->crouch ? T_C193 : T_C18B)[arc_rand() & 3] - YI;
        if ((s16)d < 0) d = -d;
        X(6) = d;                                   /* depth of the arc */
        wr16(&X(7), YI);                            /* its top */
        X(9) = 0;                                   /* phase */
        if (X(0x1D)) {
            wr16(&X(7), rd16(&X(7)) + 0x60);
            X(9) = 0x80;
            X(6) = 0x60;
            ST2 = 2;
        } else
            ST2++;
        break;
    case 1:                                         /* $C1DB: the arc */
        u = vel(rd16(&X(0x18)));
        if (!X(0x1D) && X(9) >= 0x7F) u = T_VEL[4 + (X(0x1C) & 3)];
        ADDX(u[FAC & 1]);
        d = (u16)(SINE[X(9)] << 1 & 0xFF) * X(6) >> 8;
        wr16(&X(0xA), d);
        wr16(s + 9, rd16(&X(7)) - d);
        floor_clamp(s);
        if ((u16)X(9) + X(0x15) > 0xFF) { ST1 = 0; ST2 = 1; break; }
        X(9) += X(0x15);
        break;
    case 2:                                         /* $C227: level run to his old x */
        ADDX(vel(rd16(&X(0x18)))[FAC & 1]);
        if ((u16)(XI - rd16(&X(0xC)) + 0x10) < 0x20) ST2 = 1;
        break;
    case 3:                                         /* $C242: straight dash */
        ADDX(T_C19B[FAC & 15][0]);
        ADDY(T_C19B[FAC & 15][1]);
        ANIM = (FAC >= 5 && FAC <= 12) ? AN_FLYL : AN_FLYR;
        break;
    }
    range_check(s);
}

/* One arcade frame of the handler for states -$D = 0 and 1. Returns 1 on
 * the frame it counts itself as a boss to kill ($BF5F). */
int satan_step(u8 *s, const SatanIn *inp)
{
    in = inp;
    counted = 0;
    if (ST0 == 0) {
        if (ST1 == 0) {                             /* $BEF1 */
            X(0x14) = 10;
            s[0xF] = 4;
            FAC = (s16)XI >= (s16)in->ax;
            ANIM = AN_WRAP;
            X(0x1F) = 0;
            X(0xE) = 0;
            X(0x1C) = in->rank >> 4;
            ST1++;
        } else {                                    /* $BF1E: asleep until on screen */
            FL = 0x81;
            if ((u16)(XI - in->camx) <= 0x100 && (u16)(YI - in->camy) <= 0xF0) {
                ST0 = 1; ST1 = 0; ST2 = 0; FL = 1;
            }
        }
    } else if (ST0 == 1) {
        if (ST1 == 0) ground(s); else flight(s);
    }
    return counted;
}

#ifndef HOST
/* ---- the port side ---------------------------------------------------- */

#define NSAT 4
typedef struct { u8 *slot; u8 s[48]; } Satan;
static Satan sat[NSAT];

/* $C24C: a shot from the pool ($FFC220 = <$A7/<$A8), as the port's own
 * shot type 6 (motion as the arcade's type $0B: 16 directions at the $5DBF
 * speeds = the port's $29238; the port's $7442 = $8FE4 picks the direction
 * in the shot's first update, the same frame, from the same position). The
 * fractions are left from the slot's last shot, as in the arcade. */
static void satan_fire(u8 *s)
{
    u16 *pool = (u16 *)0xFFC220;
    u8 *p, **sp;
    if (!pool[0]) return;
    sp = *(u8 ***)0xFFC228;
    p = *--sp;
    *(u8 ***)0xFFC228 = sp;
    pool[0]--;
    wr16(p, XI);
    RAM32(p + 16) = (u32)XI << 8 | p[19];
    wr16(p + 2, YI);
    RAM32(p + 20) = (u32)YI << 8 | p[23];
    p[7] = 0; p[8] = 0; p[9] = 0;
    p[4] = 1; p[5] = 0;
    p[10] = 6;
}

static Satan *bind(u8 *p, int *fresh)
{
    int i, k = -1;
    for (i = 0; i < NSAT; i++) {
        if (sat[i].slot == p) { *fresh = 0; return &sat[i]; }
        if (k < 0 && (!sat[i].slot || sat[i].slot[10] != 6 || !sat[i].slot[4])) k = i;
    }
    if (k < 0) k = 0;
    sat[k].slot = p;
    *fresh = 1;
    return &sat[k];
}

/* $110578 / $1105C6 (port states 0 and 1, from hook_satan with a4).
 * Returns 1 when the port's boss count ($10E9B6, which the port's own init
 * raised) is to be raised: where the arcade raises its <$B5, on waking. */
int satan_update(u8 *p)
{
    SatanIn i;
    int fresh, k, born;
    Satan *r = bind(p, &fresh);
    u8 *s = r->s;
    u8 left;
    /* a new Satan: the spawner leaves the hit points at 0, and they can
     * only drop while it's awake (+7 = 1) */
    born = fresh || (p[7] == 0 && p[11] == 0);
    if (born) {
        for (k = 0; k < 48; k++) s[k] = 0;
        FL = p[4];                      /* live, as the spawner left it */
        s[6] = p[17]; s[7] = p[18]; s[8] = p[19];       /* x, 16.8 */
        s[9] = p[21]; s[10] = p[22]; s[11] = p[23];     /* y */
        X(5) = 6;
        p[11] = 10;                     /* hit points (the arcade's $14,X) */
        p[25] = 4;                      /* size class (-1,X) */
    }
    i.ax = RAM16(0xFFA204);
    i.ay = RAM16(0xFFA230);
    i.camx = RAM16(0xFFA200);
    i.camy = RAM16(0xFFA202);
    i.c21 = RAM8(0xFFA206);
    i.rank = RAM8(0xFFC501);
    i.crouch = RAM8(0xFF944B);
    ONS = p[5];
#ifdef SATAN_TEST
    /* test builds only (tools/re/lockstep_satan.py): the arcade's inputs */
    if (RAM16(0xFF6F00) == 0x5354) {
        i.ax = RAM16(0xFF6F02); i.ay = RAM16(0xFF6F04);
        i.camx = RAM16(0xFF6F06); i.camy = RAM16(0xFF6F08);
        i.c21 = RAM8(0xFF6F0A); i.crouch = RAM8(0xFF6F0B);
        ONS = RAM8(0xFF6F10 + ((u32)p - 0xFFB800) / 48);
    }
#endif
    born = satan_step(s, &i);
    p[6] = 0;
    p[4] = FL;
    if (ST0 == 3) { p[7] = 3; p[8] = 0; p[9] = 0; }
    else p[7] = ST0;
    p[16] = 0; p[17] = s[6]; p[18] = s[7]; p[19] = s[8];
    p[20] = 0; p[21] = s[9]; p[22] = s[10]; p[23] = s[11];
    wr16(p, XI);
    wr16(p + 2, YI);
    /* the port's frames: 1/2 flying (left/right), 3/4 wings closed */
    if (ANIM == AN_FLYL) left = 1;
    else if (ANIM == AN_FLYR) left = 0;
    else left = FAC;                    /* ground states: 1 = facing left */
    p[24] = !left;
    wr16(p + 30, (ANIM == AN_WRAP ? 3 : 1) + !left);
    return born;
}
#else
/* host build: shots are recorded by the test */
void host_fire(const u8 *s, u8 dir);
static void satan_fire(u8 *s) { host_fire(s, dir_to_arthur(s)); }
#endif
