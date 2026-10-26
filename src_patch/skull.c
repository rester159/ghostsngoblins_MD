/* Stage 5's skulls (enemy type 9), translated from the arcade's handler
 * ($CC45: asleep $CC5F/$CC70, the rise $CCAA, hops $CD30, the leap $CE3A).
 * The port ran its type-9 projectile on them ($1074DC, the dragon's fire:
 * set off at Arthur, or since the dragon fix straight along +24) as soon as
 * they came on the screen, so they flew off instead of waking up.
 *
 * Arcade states (-$D/-$C/-$B):
 *   0/0 a small skull (class 0); 0/1 asleep until on the screen with Arthur
 *       within 32 px both ways ($CC70)
 *   1/0 it jumps up at 3.5 px/frame against a 0.16 px/frame^2 pull while its
 *       rising script plays (class 2, 8 px left), then stands up 16 px higher
 *       as the full skeleton (class 3) ($CCB8-$CCED)
 *   1/1 two hops ($CD30): sound $20, a 3 px/frame rise slowing by 0.165 to the
 *       top, then down to the floor at up to 3 px/frame ($8CA7), 0.8 px/frame
 *       sideways toward Arthur; 6 frames on the floor, facing him when he's
 *       more than 64 px away ($CDDB)
 *   1/2 a leap at Arthur's x along a half sine 80 px high ($CE3A: the x speed
 *       is |dx| / 42 per frame, 43 frames), landing on the floor if any
 *       ($8CA7 from phase $E0), 6 frames, then 1/1 again
 *   out of range of the camera in state 1: removed ($8F62).
 * It draws no random. Dying lasts the arcade's 21 frames (sound $14, then the
 * burst, which isn't drawn); the removal is the port's.
 *
 * As petite.c, the arcade's slot image (s[n] = X-$10+n) is kept per skull;
 * the port slot gets x/y, the size class (+25: the port's floor probe,
 * $107ED6 = $8CA7, and on-screen boxes are by class as the arcade's) and the
 * state. The port has no art for them: they are drawn with its type-9 frames
 * (0 asleep, 1/2 awake). */
#include "md.h"

typedef struct {
    u16 camx, camy, ax, ay;
    u8 frame, slot, rank;
} SkCtx;

long sk_floor(void *slot);
void sk_sound(int id);
void sk_sound2(int id);

static const SkCtx *c;
static u8 *s;

#define ONS  s[0x01]
#define ST0  s[0x03]
#define ST1  s[0x04]
#define ST2  s[0x05]
#define DIR  s[0x0E]
#define CLS  s[0x0F]
#define X(n) s[0x10 + (n)]

static u16 rd16(const u8 *p) { return (u16)(p[0] << 8 | p[1]); }
static void wr16(u8 *p, u16 v) { p[0] = v >> 8; p[1] = v; }
#define XI rd16(s + 6)
#define YI rd16(s + 9)

/* the scripts: $CC96 asleep (class 0), $CD26 rising (class 2, which loops
 * into $CE1A as the arcade's does), $CE1A and gg4 $4EF6 standing/hopping
 * (class 3) */
static const u8 A_CC96[] = { 0xa7, 0x30, 0x83, 0xcc, 0x96 };
static const u8 A_CD26[] = { 0xa2, 0x30, 0xa3, 0x01, 0xa4, 0x30, 0xa5, 0x81, 0xce, 0x1a };
static const u8 A_CE1A[] = {
    0xa8, 0x30, 0xa0, 0xa9, 0xa1, 0x06, 0xaa, 0x30, 0xa2, 0xab, 0xa3, 0x06, 0xac, 0x30, 0xa4, 0xad,
    0xa5, 0x18, 0xaa, 0x30, 0xa2, 0xab, 0xa3, 0x03, 0xa8, 0x30, 0xa0, 0xa9, 0xa1, 0x84, 0xce, 0x1a };
static const u8 A_4EF6[] = {
    0xa8, 0x30, 0xa0, 0xa9, 0xa1, 0x06, 0xaa, 0x30, 0xa2, 0xab, 0xa3, 0x06, 0xac, 0x30, 0xa4, 0xad,
    0xa5, 0x18, 0xaa, 0x30, 0xa2, 0xab, 0xa3, 0x03, 0xa8, 0x30, 0xa0, 0xa9, 0xa1, 0x83, 0x4e, 0xf6 };
static u8 ab(u16 a)
{
    if ((u16)(a - 0xCC96) < sizeof A_CC96) return A_CC96[a - 0xCC96];
    if ((u16)(a - 0xCD26) < sizeof A_CD26) return A_CD26[a - 0xCD26];
    if ((u16)(a - 0xCE1A) < sizeof A_CE1A) return A_CE1A[a - 0xCE1A];
    if ((u16)(a - 0x4EF6) < sizeof A_4EF6) return A_4EF6[a - 0x4EF6];
    return 0;
}
static const u8 ESIZE[4] = { 3, 4, 4, 6 };     /* $9060 by class */
/* $4EE1: remainder / 21 as a fraction */
static const u8 T_4EE1[21] = {
    0x00,0x0c,0x18,0x24,0x31,0x3d,0x49,0x56,0x62,0x6e,0x7a,0x87,0x93,0x9f,0xac,0xb8,0xc4,0xd0,0xdd,0xe9,0xf5};
static const s16 VX[5] = { 0, 0x00CC, 0, -0x00CC, 0 };     /* $CD44, x by direction */
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

static void anim(void)                  /* $9074 */
{
    u16 y;
    u8 b;
    if (X(2)) { X(2)--; return; }
    y = rd16(&X(0));
    wr16(&X(3), y);
    y += ESIZE[CLS & 3];
    b = ab(y - 1);
    if (b & 0x80) { y = (u16)(ab(y) << 8 | ab(y + 1)); b &= 0x7F; }
    X(2) = b;
    wr16(&X(0), y);
}

static void add24(u8 *p, u32 v)
{
    u32 a = (u32)p[0] << 16 | (u32)p[1] << 8 | p[2];
    a = (a + v) & 0xFFFFFF;
    p[0] = a >> 16; p[1] = a >> 8; p[2] = a;
}

/* the vertical speed: X+$A..$D, 16.16; y (16.8) += its top 24 bits */
static void y_step(void) { add24(s + 9, (u32)X(0x0A) << 16 | (u32)X(0x0B) << 8 | X(0x0C)); }
static void pull(u16 g)                 /* SUBD #g on X+$C, borrow into X+$A */
{
    u32 v = (u32)X(0x0A) << 24 | (u32)X(0x0B) << 16 | (u32)X(0x0C) << 8 | X(0x0D);
    v -= g;
    X(0x0A) = v >> 24; X(0x0B) = v >> 16; X(0x0C) = v >> 8; X(0x0D) = v;
}

static void fall(void)                  /* $CD08 */
{
    y_step();
    pull(0x2985);
    anim();
}

static void hop_move(void)              /* $CDF6 */
{
    add24(s + 6, (u32)(long)VX[DIR < 5 ? DIR : 4]);
    y_step();
    anim();
}

static void face(void)                  /* $CDDB */
{
    if ((u16)(XI - c->ax + 0x40) < 0x80) return;
    DIR = XI > c->ax ? 3 : 1;
}

static void remove_far(void)            /* $8F62 */
{
    if ((u16)(XI - c->camx + 0x80) > 0x200 || (u16)(YI - c->camy + 0x40) > 0x180) {
        ST0 = 3; ST1 = 0; ST2 = 0;
    }
}

static int floor_at(u8 *p, u8 *adj)    /* $8CA7: carry and B */
{
    long r;
    wr16(p, XI); wr16(p + 2, YI); p[25] = CLS;
    r = sk_floor(p);
    *adj = (u8)r;
    return r != 0;
}

static void arc_y(u8 ph)                /* $CEF3 */
{
    u8 b = (u8)(SINE[ph] << 1);
    wr16(s + 9, (u16)(((u16)X(0x17) * b) >> 8) + rd16(&X(0x18)));
}

static void leap_x(void)                /* $CEA5 */
{
    add24(s + 6, (u32)X(0x1A) << 16 | (u32)X(0x1B) << 8 | X(0x1C));
}

static void rise(void)                  /* 1/0 */
{
    switch (ST2) {
    case 0:                             /* $CCB8 */
        wr16(s + 12, 0xCD44);           /* -4: the velocity table (VX) */
        DIR = 4;
        CLS = 2;
        wr16(&X(0), 0xCD26); X(2) = 0;
        anim();
        X(0x0A) = 0; X(0x0B) = 3; X(0x0C) = 0x80; X(0x0D) = 0;
        wr16(s + 6, XI - 8);
        ST2++;
        break;
    case 1:                             /* $CCE3 */
        fall();
        if (!X(2)) ST2++;
        break;
    default:                            /* $CCED */
        fall();
        if (X(2)) break;
        wr16(s + 9, YI - 0x10);
        CLS = 3;
        anim();
        ST1 = 1; ST2 = 0;
        break;
    }
}

static void hops(u8 *p)                 /* 1/1 ($CD30) */
{
    u8 adj;
    switch (ST2) {
    case 0:                             /* $CD58 */
        sk_sound(0x20);
        wr16(s + 12, 0xCD44);
        X(9) = 2;
        ST2++;
        break;
    case 1:                             /* $CD67 */
        wr16(&X(0), 0xCE1A); X(2) = 0;
        anim();
        X(0x0A) = 0; X(0x0B) = 3; X(0x0C) = 0; X(0x0D) = 0;
        ST2++;
        /* fall through */
    case 2:                             /* $CD7D */
        hop_move();
        pull(0x2A16);
        if (!X(0x0A) && !X(0x0B)) ST2++;
        break;
    case 3:                             /* $CD94 */
        hop_move();
        if ((s16)rd16(&X(0x0A)) >= -3) pull(0x2A16);    /* $CDA7 */
        if (floor_at(p, &adj)) { wr16(s + 9, YI + adj); ST2++; }
        break;
    case 4:                             /* $CDBF */
        X(8) = 6;
        ST2++;
        /* fall through */
    default:                            /* $CDC5 */
        if (--X(8)) { anim(); break; }
        face();
        ST2 = 1;
        if (--X(9) == 0) { ST1 = 2; ST2 = 0; }
        break;
    }
}

static void leap(u8 *p)                 /* 1/2 ($CE3A) */
{
    u8 adj, a, b, q, r, sgn;
    u16 v;
    int i;
    switch (ST2) {
    case 0:                             /* $CE4C */
        wr16(&X(0), 0x4EF6); X(2) = 0;
        anim();
        wr16(&X(0x18), YI);
        X(0x16) = 0; X(0x17) = 0x50;
        a = (u8)c->ax - s[7];
        sgn = 0;
        if (a & 0x80) { a = -a; sgn = 1; }
        X(0x1D) = sgn;
        a = (u8)((signed char)a >> 1);
        q = a; r = 0;                   /* $FED8: q, r = a / 21 */
        for (i = 0; i < 8; i++) {
            u8 cy = q >> 7, c2;
            q <<= 1;
            c2 = r >> 7; r = (u8)(r << 1 | cy);
            q++;
            { int t = (int)r - 0x15 - c2; r = (u8)t; if (t < 0) { q--; r += 0x15; } }
        }
        b = T_4EE1[r < 21 ? r : 0];
        v = (u16)(q << 8 | b);
        if (X(0x1D)) v = -v;
        wr16(&X(0x1B), v);
        X(0x1A) = (v & 0x8000) ? 0xFF : 0;
        ST2++;
        break;
    case 1:                             /* $CE93 */
        X(0x16) += 6;
        if (X(0x16) & 0x80) { ST2++; break; }
        arc_y(X(0x16));
        leap_x();
        break;
    case 2:                             /* $CEB4 */
        v = X(0x16) + 6;
        X(0x16) = v;
        if (v > 0xFF) { wr16(s + 9, rd16(&X(0x18))); ST2++; break; }
        if (X(0x16) >= 0xE0 && floor_at(p, &adj)) { wr16(s + 9, YI + adj); ST2++; break; }
        arc_y(X(0x16));
        leap_x();
        break;
    case 3:                             /* $CEDE */
        X(8) = 6;
        ST2++;
        /* fall through */
    default:                            /* $CEE4 */
        if (--X(8)) { anim(); break; }
        face();
        ST1 = 1; ST2 = 0;
        break;
    }
}

static void skull_step(u8 *p)
{
    if (ST0 == 0) {
        if (ST1 == 0) {                 /* $CC5F */
            CLS = 0;
            wr16(&X(0), 0xCC96); X(2) = 0;
            anim();
            ST1++;
        } else if (ONS && (u16)(XI - c->ax + 0x20) <= 0x40 && (u16)(YI - c->ay + 0x20) <= 0x40) {
            ST0 = 1; ST1 = 0; ST2 = 0;  /* $CC70 */
        }
        return;
    }
    switch (ST1) {                      /* $CC9B */
    case 0: rise(); break;
    case 1: hops(p); break;
    default: leap(p); break;
    }
    remove_far();
}

#ifdef HOST
/* tools/re/test_skull.py: the handler on an arcade slot image */
void skull_host(u8 *img, const SkCtx *x)
{
    static u8 dummy[48];
    s = img; c = x;
    skull_step(dummy);
}
#else
/* ---- the port side ---------------------------------------------------- */

#define NREC 8
typedef struct { u8 *slot; u8 s[48]; } Rec;
static Rec rec[NREC];

static Rec *bind(u8 *p, int *fresh)
{
    Rec *r, *k = 0;
    for (r = rec; r < rec + NREC; r++) {
        if (r->slot == p) { *fresh = 0; return r; }
        if (!k && (!r->slot || r->slot[10] != 9 || !r->slot[4])) k = r;
    }
    if (!k) k = rec;
    k->slot = p;
    *fresh = 1;
    return k;
}

/* from skull_entry (stage 5, type 9, states 0 and 1): p = the slot, a = the
 * object pass context ($FFA200: camera +0/+2, Arthur x +4, y +48, frame +6,
 * slot counter +7, rank +8) */
void skull_update(u8 *p, const u8 *a)
{
    SkCtx x;
    int fresh, k;
    Rec *r;
    u8 code;
    if (p[7] == 2) {
        /* dying ($CF07): sound $14 ($79B5), then the generic burst ($E85B),
         * 21 frames in all before the removal (the port went to it at once;
         * nothing is drawn for the burst: the frame stays) */
        if (p[9] == 0) sk_sound2(0x14);
        if (++p[9] >= 21) { p[7] = 3; p[8] = 0; p[9] = 0; }
        return;
    }
    r = bind(p, &fresh);
    s = r->s;
    x.camx = rd16(a); x.camy = rd16(a + 2); x.ax = rd16(a + 4); x.ay = rd16(a + 48);
    x.frame = a[6]; x.slot = a[7]; x.rank = a[8];
    c = &x;
    if (fresh || (p[7] == 0 && ST0 != 0)) {
        for (k = 0; k < 48; k++) s[k] = 0;
        s[0] = p[4];
        s[2] = p[6];
        s[6] = p[17]; s[7] = p[18]; s[8] = p[19];
        s[9] = p[21]; s[10] = p[22]; s[11] = p[23];
        X(5) = 9;
    }
    ONS = p[5];
    skull_step(p);
    p[7] = ST0;
    p[8] = 0; p[9] = 0;
    p[16] = 0; p[17] = s[6]; p[18] = s[7]; p[19] = s[8];
    p[20] = 0; p[21] = s[9]; p[22] = s[10]; p[23] = s[11];
    wr16(p, XI);
    wr16(p + 2, YI);
    p[24] = DIR;
    p[25] = CLS;
    /* the port's type-9 frames (no skull art): 0 asleep, 1/2 by the script */
    code = ab(rd16(&X(3)));
    wr16(p + 30, CLS == 0 ? 0 : (code == 0xa8 || code == 0xa2 ? 1 : 2));
}
#endif
