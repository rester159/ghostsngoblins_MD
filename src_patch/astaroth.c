/* The arcade's Astaroth (enemy type 13, the final room), translated from
 * its handler ($DAD9: init $DAF3, wait $DB29, walk $DB8E, pause $DBCB, fire
 * control $DC06-$DD11, shot $DD12) instead of the port's own one ($111B9C),
 * which walked and paused on timers from its own tables picked by the rank
 * byte and the frame counter, fired one low shot every 12-180 frames and had
 * no rapid-fire mode or high shots.
 *
 * As in satan.c, each Astaroth keeps an image of the arcade's 48-byte enemy
 * slot (`s`, s[n] = X-$10+n for the routines' X), so the code below reads
 * like the 6809 code. The port slot gets x/y, the state and the frame; the
 * port keeps its own drawing (frames 1/3 walking right/left, 2/4 the open
 * mouth, shown in the rapid-fire mode as the arcade's $5308/$5302 scripts
 * do), hit points, death (+7 = 2, see astaroth_glue.s) and removal (+7 = 3).
 *
 * The arcade slot (X offsets):
 *   -$10 live  -$F on screen  -$D/-$C/-$B states  -$A..-$5 x, y (16.8)
 *   -$4 walk speed table ($53F2 slow / $53FA fast)  -$2 walk direction (0 right)
 *   -$1 size class 6
 *   $6 walk time (word)  $8 pause time  $9 shot countdown  $B left end (word)
 *   $D rapid-fire mode  $E time to the next rapid-fire mode (word)
 *   $10 rapid-fire length (word)  $12 high shot  $13 right end (word)
 *   $16 hit points  $17 Arthur 80 px or more away  $18 facing (1 = left)
 *   $19 walking (0) / pausing (1)  $1A rank & $30 >> 3
 * Its inputs: <$A0 Arthur's x ($FFA204), <$9C camera x ($FFA200), <$9E camera y,
 * <$21 the frame counter ($FFA206), <$9A the rank ($FFA208), <$E0 the
 * enemy loop's counter (40 - slot index, only for the walk sound), <$A7 the free
 * projectiles (see ast_fire).
 *
 * The random calls ($68F9, arc_rand) are the arcade's ten, in its order:
 * $DB7A/$DB81 walk time, $DBB3 pause, $DBDE speed, $DC2F shot gap, $DC39/$DC41
 * next rapid-fire mode, $DC5E its length, $DC84 high/low in it, $DD01 high/low
 * when Arthur is far.
 *
 * HOST builds (tools/re/test_astaroth.py) compile only the core against the
 * arcade's recorded inputs. */
#include "md.h"

typedef struct {
    u16 ax, camx, camy;     /* <$A0, <$9C, <$9E */
    u8  c21, rank, e0;      /* <$21, <$9A, <$E0 */
    u8  free_shots;         /* <$A7 */
} AstIn;

u8 arc_rand(void);                      /* arcrand.c: the arcade's $68F9 */
static const AstIn *in;
static u8 fired, stomp;                 /* outputs of one step */
u16 ast_shot_x, ast_shot_y;             /* the last shot's position */

#define FL   s[0x00]
#define ONS  s[0x01]
#define ST0  s[0x03]
#define ST1  s[0x04]
#define ST2  s[0x05]
#define DIR  s[0x0E]                    /* -$2 */
#define X(n) s[0x10 + (n)]

static u16 rd16(const u8 *p) { return (u16)(p[0] << 8 | p[1]); }
static void wr16(u8 *p, u16 v) { p[0] = v >> 8; p[1] = v; }
#define XI rd16(s + 6)
#define YI rd16(s + 9)
#define W(n) rd16(&X(n))
#define SETW(n, v) wr16(&X(n), v)

/* $53F2 / $53FA: walk speeds by direction (x, y) */
static const u16 T_53F2[2][2] = { { 0x002D, 0 }, { 0xFFD3, 0 } };
static const u16 T_53FA[2][2] = { { 0x0069, 0 }, { 0xFF97, 0 } };
static const u8 T_DBF2[16] = { 0, 0, 0, 2, 2, 0, 0, 2, 0, 2, 2, 0, 2, 0, 0, 2 };
static const u8 T_DBC7[4] = { 0x8F, 0x6F, 0x5F, 0x1F };            /* pause base by rank */
/* $5402: shot gaps by rank ($540A twice, $5412, $541A); $5422: rapid fire */
static const u8 T_GAP[4][8] = {
    { 100, 150, 180, 160, 70, 150, 115, 80 }, { 100, 150, 180, 160, 70, 150, 115, 80 },
    { 200, 105, 90, 60, 100, 150, 50, 100 }, { 60, 100, 90, 100, 34, 100, 90, 105 } };
static const u8 T_RAPID[8] = { 30, 50, 80, 20, 60, 15, 25, 40 };

/* $DCDE: the animation for facing $18 and walking/pausing/rapid fire. Only
 * the script choice matters here (the port draws its own frames); it returns
 * the A it leaves (2 * the script index), which $DC39 stores. */
static u8 anim(u8 *s)
{
    u8 a = X(0xD) ? 2 : X(0x19);
    X(2) = 0;                           /* CLR $2,X: the script restarts */
    return (u8)(a << 1);
}

/* $DBDE: a new walk speed */
static void new_speed(u8 *s)
{
    wr16(s + 12, T_DBF2[arc_rand() & 15] ? 0x53FA : 0x53F2);
}

/* $DC20 / $DC2F: the next shot gap */
static void shot_gap(u8 *s)
{
    const u8 *t = X(0xD) ? T_RAPID : T_GAP[(X(0x1A) >> 1) & 3];
    X(9) = t[arc_rand() & 7];
}

/* $DC39: time to the next rapid-fire mode, (1-2) << 8 | the caller's A; the
 * second random lands in $10,X (the high byte of the rapid-fire length) */
static void rapid_time(u8 *s, u8 a)
{
    X(0xE) = (arc_rand() & 1) + 1;
    X(0xF) = a;
    X(0x10) = arc_rand();
}

/* $DCC0: face Arthur */
static void face(u8 *s)
{
    u8 e1 = XI >= in->ax;
    if (X(0x18) != e1) { X(0x18) ^= 1; anim(s); }
}

/* $DD12: a shot, if a projectile is free ($8E2E). The port makes it (ast_fire);
 * x/y here are the integer words the arcade sets (the fractions are the
 * slot's own leftovers). */
static void fire(u8 *s)
{
    u16 dx = X(0x12) ? 10 : 4;
    if (!in->free_shots) return;
    fired = X(0x12) ? 2 : 1;
    ast_shot_x = X(0x18) ? XI - dx : XI + dx;
    ast_shot_y = X(0x12) ? YI + 12 : YI - 5;
}

/* $DC9F */
static void shot_tick(u8 *s)
{
    if (--X(9) == 0) { fire(s); shot_gap(s); }
}

/* $DC71: the rapid-fire mode */
static void rapid(u8 *s)
{
    u16 t;
    if (!X(0xD)) return;
    face(s);
    t = W(0x10) - 1;
    SETW(0x10, t);
    if (t) {
        X(0x12) = arc_rand() & 1;
        shot_tick(s);
        return;
    }
    new_speed(s);
    X(0xD) = 0;
    X(0x12) = 0;
    rapid_time(s, anim(s));
}

/* $DC47 */
static void rapid_timer(u8 *s)
{
    if (!X(0xD)) {
        u16 t = W(0xE) - 1;
        SETW(0xE, t);
        if (!t) {
            X(0xD) = 1;
            anim(s);
            SETW(0x10, (arc_rand() & 0x7F) + 0x40);
            X(9) = 1;
        }
    }
    rapid(s);
}

/* $DC06: aim, fire */
static void fire_control(u8 *s)
{
    face(s);
    rapid_timer(s);
    if (X(0xD)) return;
    X(0x17) = (u16)(XI - in->ax + 0x50) >= 0xA0;    /* $DCAA */
    if (X(0x17)) {                                  /* $DCFA */
        X(0x12) = 1;
        if ((arc_rand() & 3) == 0) X(0x12) = 0;
        shot_tick(s);
        X(0x12) = 0;
    } else
        shot_tick(s);
}

/* $A427 with -$4/-$2, then $DB42's ends of the walk */
static void walk(u8 *s)
{
    const u16 (*t)[2] = rd16(s + 12) == 0x53FA ? T_53FA : T_53F2;
    const u16 *u = t[DIR & 1];
    u16 d;
    if (((in->c21 + in->e0) & 0x1F) == 0) stomp = 1;     /* sound $0C ($7992) */
    d = rd16(s + 7) + u[0];
    s[6] += (u8)((u[0] & 0x8000 ? 0xFF : 0) + (d < rd16(s + 7) ? 1 : 0));
    wr16(s + 7, d);
    d = rd16(s + 10) + u[1];
    s[9] += (u8)((u[1] & 0x8000 ? 0xFF : 0) + (d < rd16(s + 10) ? 1 : 0));
    wr16(s + 10, d);
    if (XI <= W(0xB)) { wr16(s + 6, W(0xB)); DIR = 0; return; }
    if (XI >= W(0x13)) { wr16(s + 6, W(0x13)); DIR = 1; }
}

/* $8F62 */
static void range_check(u8 *s)
{
    if ((u16)(XI - in->camx + 0x80) > 0x200 || (u16)(YI - in->camy + 0x40) > 0x180) {
        ST0 = 3; ST1 = 0; ST2 = 0;
    }
}

/* One arcade frame of the handler for states -$D = 0 and 1. Returns what it
 * did: bit 0-1 a shot (1 low, 2 high), bit 2 the walk sound, bit 3 the frame
 * it starts (<$A4/<$A5: it is the boss of the room). */
int ast_step(u8 *s, const AstIn *inp)
{
    u16 t;
    int r = 0;
    in = inp;
    fired = stomp = 0;
    if (ST0 == 0) {
        if (ST1 == 0) {                                 /* $DAF3 */
            r = 8;
            s[0xF] = 6;
            DIR = 1;
            X(0x18) = 1;
            X(0x19) = 0;
            X(0xD) = 0;
            X(0x12) = 0;
            X(0x1A) = (in->rank & 0x30) >> 3;
            wr16(s + 12, 0x53F2);
            X(0x16) = 10;
            rapid_time(s, 0x0A);
            shot_gap(s);
            ST1++;
        } else if (ONS) {                               /* $DB29 */
            SETW(0xB, in->camx + 0x60);
            SETW(0x13, in->camx + 0xE0);
            ST0 = 1; ST1 = 0; ST2 = 0;
        }
    } else if (ST0 == 1) {
        switch (ST1) {
        case 0:                                         /* $DB7A */
            t = (arc_rand() & 3) << 8;
            SETW(6, t | arc_rand());
            X(0x19) = 0;
            anim(s);
            ST1++;
            /* fall through: no RTS after $DB8C */
        case 1:                                         /* $DB8E */
            t = W(6) - 1;
            SETW(6, t);
            if (!t) {                                   /* $DBA8 */
                u8 e1 = T_DBC7[(X(0x1A) >> 1) & 3];
                X(8) = (arc_rand() & 0x2F) + e1;
                X(0x19) = 1;
                anim(s);
                ST1++;
                break;
            }
            fire_control(s);
            if (!X(0xD)) walk(s);
            range_check(s);
            break;
        case 2:                                         /* $DBCB */
            if (--X(8)) { fire_control(s); break; }
            new_speed(s);
            DIR ^= 1;
            ST1 = 0;
            break;
        }
    }
    return r | fired | stomp << 2;
}

#ifndef HOST
/* ---- the port side ---------------------------------------------------- */

#define NAST 2
typedef struct { u8 *slot; u8 s[48]; } Ast;
static Ast ast[NAST];

void ast_shot_spawn(u8 *slot, u16 x, u16 y, u8 dir, u8 rank);   /* below */
void *ast_alloc(void);                  /* astaroth_glue.s: an enemy slot ($7BD2) */
int ast_floor(int x, int y);            /* astaroth_glue.s: $8CA7 for size class 0 */
void ast_sound(int id);                 /* astaroth_glue.s: $B762 etc. */

/* The arcade's projectile pool (<$A7 free count, <$A8 stack; 6 slots) is the
 * port's shot pool ($FFC220 count, $FFC228 stack, slots at $FFC100), which
 * the port's Satans use too. */
#define POOL_FREE RAM16(0xFFC220)

static Ast *bind(u8 *p, int *fresh)
{
    int i, k = -1;
    for (i = 0; i < NAST; i++) {
        if (ast[i].slot == p) { *fresh = 0; return &ast[i]; }
        if (k < 0 && (!ast[i].slot || ast[i].slot[10] != 13 || !ast[i].slot[4])) k = i;
    }
    if (k < 0) k = 0;
    ast[k].slot = p;
    *fresh = 1;
    return &ast[k];
}

/* $111BB2 (the port's states 0 and 1, from hook_ast with a4). Returns 1 on the
 * frame the arcade's init runs (the port raises its boss count then, as its
 * own init did). */
int ast_update(u8 *p)
{
    AstIn i;
    int fresh, k, r;
    Ast *a = bind(p, &fresh);
    u8 *s = a->s;
    /* a new Astaroth: the spawner leaves the hit points at 0 */
    if (fresh || (p[7] == 0 && p[11] == 0)) {
        for (k = 0; k < 48; k++) s[k] = 0;
        FL = p[4];
        s[6] = p[17]; s[7] = p[18]; s[8] = p[19];
        s[9] = p[21]; s[10] = p[22]; s[11] = p[23];
        X(5) = 13;
    }
    i.ax = RAM16(0xFFA204);
    i.camx = RAM16(0xFFA200);
    i.camy = RAM16(0xFFA202);
    i.c21 = RAM8(0xFFA206);
    i.rank = RAM8(0xFFA208);
    i.e0 = 40 - ((u32)p - 0xFFB800) / 48;
    i.free_shots = POOL_FREE;
    ONS = p[5];
#ifdef AST_TEST
    if (RAM16(0xFF6F00) == 0x4153) {    /* test builds: the arcade's inputs */
        i.ax = RAM16(0xFF6F02); i.camx = RAM16(0xFF6F06); i.camy = RAM16(0xFF6F08);
        i.c21 = RAM8(0xFF6F0A); ONS = RAM8(0xFF6F0B); i.free_shots = RAM8(0xFF6F0C);
    }
#endif
    r = ast_step(s, &i);
    if (r & 3)      /* $DD12: x +-4, y - 5 (low) or x +-10, y + 12 (high) */
        ast_shot_spawn(p, ast_shot_x, ast_shot_y, X(0x18), X(0x1A) >> 1);
    if (r & 4) ast_sound(0x0C);
    if (r & 8) p[11] = 10;              /* hit points (the arcade's $16,X) */
    p[25] = 6;
    p[8] = 0;
    p[9] = 0;                           /* the death's frame count (hook_ast_die) */
    p[7] = ST0 == 3 ? 3 : ST0;
    p[16] = 0; p[17] = s[6]; p[18] = s[7]; p[19] = s[8];
    p[20] = 0; p[21] = s[9]; p[22] = s[10]; p[23] = s[11];
    wr16(p, XI);
    wr16(p + 2, YI);
    p[24] = !X(0x18);                   /* the port's: 1 = facing right */
    p[26] = X(0xD);
    wr16(p + 30, (X(0x18) ? 3 : 1) + (X(0xD) ? 1 : 0));
    return r >> 3;
}

/* ---- its shots (the arcade's projectile type $0A) ----------------------
 * $DD12 takes a projectile ($8E2E) and gives it the facing as its direction
 * and the rank; the projectile pass ($FC57, after the enemy pass) sets it up
 * the same frame ($FD17: size class 0, speed table $5E0F[rank]) and from the
 * next moves it in a straight line ($FEA3: $A427; $8F62 removes it 128 px
 * past the sides of the screen or 64 px below it, $8CA7 when it reaches the
 * floor): 1.43-1.79 px/frame forward and 0.59-0.73 px/frame down by rank.
 * On odd frames $F530 tests it against Arthur (box $F5A2 for type $0A:
 * x +-6, y +-8; crouching y -8..+2): a hit knocks him back and removes it.
 * Weapons pass through it ($F452 has nothing for type $0A).
 * The port made it its type-10 enemy (the stage 2/5 fire creature: a walker
 * along the floor that turns at Arthur and stops on him, hit by weapons for
 * points). Here it is a projectile of type 10 in the port's shot pool, which
 * is the arcade's (<$A7/<$A8 = $FFC220, the same 6 slots, the same leftover
 * fractions, the same on-screen schedule and the same tests against Arthur,
 * $59B6 with the box table $4BC8C = $F5A2): the pool pass ($724C, after the
 * enemy pass) runs ast_pool_update for it (hook_pool10), the pool's sprite
 * builder skips it (hook_pool_draw), and an enemy slot of type 10 (+4 = $80:
 * no weapon or body collisions; +41 = $A5, +44 = the pool slot) draws it with
 * the port's flame art (hook_ast_shot). */
static const u16 T_SHOT[4][2] = {       /* $5E17.. : (x, y) facing right */
    { 0x016E, 0xFF69 }, { 0x01A2, 0xFF54 }, { 0x01AB, 0xFF50 }, { 0x01C9, 0xFF44 } };

void ast_shot_spawn(u8 *slot, u16 x, u16 y, u8 dir, u8 rank)
{
    u8 *ps, *q, **sp;
    int k;
    (void)slot;
    if (!POOL_FREE) return;
    sp = *(u8 ***)0xFFC228;             /* $8E2E */
    ps = *--sp;
    *(u8 ***)0xFFC228 = sp;
    POOL_FREE--;
    RAM32(ps + 16) = (u32)x << 8 | ps[19];      /* the fractions are left over */
    RAM32(ps + 20) = (u32)y << 8 | ps[23];
    wr16(ps, x);
    wr16(ps + 2, y);
    ps[4] = 1; ps[5] = 0;
    ps[7] = 0; ps[8] = 0; ps[9] = 0;
    ps[10] = 10;
    ps[24] = dir;
    ps[40] = rank & 3;
    RAM32(ps + 44) = 0;
    q = ast_alloc();                    /* its picture */
    if (!q) return;
    for (k = 0; k < 48; k++) q[k] = 0;
    RAM32(q + 16) = RAM32(ps + 16);
    RAM32(q + 20) = RAM32(ps + 20);
    wr16(q, x);
    wr16(q + 2, y);
    q[4] = 0x80;
    q[10] = 10;
    q[11] = 3;
    q[24] = dir;                        /* the port's type 10: 1 = left */
    q[41] = 0xA5;
    RAM32(q + 44) = (u32)ps;
    RAM32(ps + 44) = (u32)q;
}

void ast_pic_free(u8 *q);               /* astaroth_glue.s */

/* The pool pass for a type-10 projectile ($FC78 for the arcade's type $0A),
 * after the on-screen test. Returns 1 when the slot is to be freed ($FECD). */
int ast_pool_update(u8 *ps)
{
    const u16 *v = T_SHOT[ps[40] & 3];
    u16 camx = RAM16(0xFFA200), camy = RAM16(0xFFA202);
    u8 *q = (u8 *)RAM32(ps + 44);
    int h;
    switch (ps[7]) {
    case 0:                             /* $FD17 */
        ps[25] = 0;
        ps[7] = 1;
        break;
    case 1:                             /* $FEA3 */
        RAM32(ps + 16) = (RAM32(ps + 16) + (u32)(long)(s16)(ps[24] ? (u16)-v[0] : v[0])) & 0xFFFFFF;
        RAM32(ps + 20) = (RAM32(ps + 20) + (u32)(long)(s16)v[1]) & 0xFFFFFF;
        wr16(ps, RAM32(ps + 16) >> 8);
        wr16(ps + 2, RAM32(ps + 20) >> 8);
        if ((u16)(rd16(ps) - camx + 0x80) > 0x200 || (u16)(rd16(ps + 2) - camy + 0x40) > 0x180)
            ps[7] = 3;
        h = ast_floor(rd16(ps), rd16(ps + 2));  /* $8CA7: in the floor -> gone */
        if (h >= 0) {
            wr16(ps + 2, rd16(ps + 2) + (s16)(signed char)h);
            ps[7] = 3;
        }
        break;
    case 2:                             /* $FECA: it hit Arthur */
        ps[7] = 3;
        break;
    default:                            /* $FECD */
        if (q) ast_pic_free(q);
        RAM32(ps + 44) = 0;
        ps[4] = 0; ps[5] = 0; ps[7] = 0; ps[8] = 0; ps[9] = 0;
        return 1;
    }
    if (q) {                            /* its picture */
        RAM32(q + 16) = RAM32(ps + 16);
        RAM32(q + 20) = (u32)rd16(ps + 2) << 8 | ps[23];
        wr16(q, rd16(ps));
        wr16(q + 2, rd16(ps + 2));
        if (ps[4] != 1) q[4] = 0;       /* hit: hidden, as the arcade's -$10 = 2 */
    }
    return 0;
}
#endif
