/* The dragon of stages 3, 4 and 6, translated from the arcade (gg3: $D518,
 * $D6D6-$DAD8; tables in gg4 at $5182-$52FD; Capcom `gng` set).
 *
 * The port had its own: the head homed on Arthur (its re-aim timer at +$23
 * overlapped a counter word at +$22, so it never re-aimed and flew off in a
 * straight line) and the body replayed the head's position history. In the
 * arcade the head follows (frames, direction) scripts, turning at the arena's
 * ends, and every body segment moves on its own, taking over the direction
 * of the one before it a few frames later.
 *
 * One 48-byte slot per node (head, 7 body segments, tail), as the arcade's.
 * The engine reads x/y (+0/+2), +4/+5 (live, on screen), +7-+9 (state; a
 * weapon kill sets 2/0/0), +10 (type 12), +11 (HP), +$19 (hit-box class) and
 * +$1E (frame of the type-12 sprite table, $1073D2); +6 is its hit flash.
 * The rest is the arcade's object fields, named after its offsets from X.
 *
 * Head (kind 0):
 *  - state 0: set up; 8 free slots: 7 segments + tail to its right ($D5A9);
 *    chain index 8..0 ($D633).
 *  - state 1 sub 0: the uncoiling script $D789 (the head steps once per pair,
 *    the body moves every frame), then frozen ($13) until on screen, Arthur
 *    within 32 px below it, and 2-5 ticks of 16 frames ($D797-$D7C0).
 *  - state 1 sub 1 ($D7EE): animate, steer at the end of each step ($D818),
 *    fire ($D981), move 2 px/frame in one of 16 directions ($A427, $51B6).
 * Segments (kind 1, tail 2): take the direction the one before passed on,
 *    after 10 frames from the head, 7 between segments, 6 to the tail
 *    ($D955).
 * Hits ($DA15): a hit segment survives and the tail is lost instead; 6 hits
 *    on the head kill it and every segment with it; the score messages are
 *    the arcade's ($F0D8: index 4 per kill, then $0C09 when the head's
 *    "1000" ends).
 */
#include "md.h"

typedef struct Node {
    u16 x, y;           /* 0  integer position (engine) */
    u8  alloc;          /* 4  live; a weapon kill doubles it (arcade -$10) */
    u8  onscr;          /* 5  on screen (engine, every 4th update; -$F) */
    u8  flash;          /* 6  engine hit flash (cleared after the hit test) */
    u8  state, sub, sub2; /* 7-9  arcade -$D, -$C, -$B */
    u8  type, hp;       /* 10, 11  12; arcade $10 */
    u8  kind;           /* 12 0 head, 1 body, 2 tail ($D) */
    u8  idx;            /* 13 chain index, head 8 ... tail 0 ($1B) */
    u8  thresh;         /* 14 aim threshold ($E) */
    u8  key;            /* 15 killed (not lost off screen): key/score ($B) */
    u32 lx, ly;         /* 16, 20  16.8 position */
    u8  side;           /* 24 0: started left of Arthur, 1: right ($14) */
    u8  size;           /* 25 hit-box / screen-box class (engine; -1) */
    u8  atimer;         /* 26 animation timer (+2) */
    u8  frozen;         /* 27 ($13) */
    u16 anim;           /* 28 animation: index into anims[] (+0) */
    u16 frame;          /* 30 type-12 sprite frame (engine; +3) */
    u8  dir;            /* 32 direction 0-15 (-2) */
    u8  pdir, delay, pend; /* 33-35 passed-on direction, its delay, pending (+6, +7, $18) */
    u8  cnt;            /* 36 frames left in this step / death timer ($A) */
    u8  fire, ftimer;   /* 37, 38 ($15, $16) */
    u8  wait;           /* 39 wake-up ticks ($11) */
    u16 next, prev;     /* 40, 42 the chain (low words of the slots, $1E, $1C) */
    u16 script;         /* 44 arcade address of the next (frames, direction) pair (+8) */
    u16 homey;          /* 46 y at the start ($19) */
} Node;

typedef char node_size_check[sizeof(Node) == 48 ? 1 : -1];

typedef struct {        /* the object pass context ($FFC960) */
    u16 camx, camy;     /* 0, 2 */
    u16 ax, ay;         /* 4, 6 Arthur */
    u8  frame;          /* 8  $FFA206 (the arcade's <$21) */
    u8  slot;           /* 9  40..1 (the arcade's <$E0 in its object loop) */
    u8  pad[2];
    u16 *projs;         /* 12 projectile free list */
} Ctx;

void *eng_alloc(void *list);
void eng_free(void *list, void *slot);
void eng_sound(int id);
void eng_score(int msg);
void eng_boss_init(void *slot);
void eng_boss_done(void *slot);

#define STAGE   RAM8(0xFFC512)
#define RANK    RAM8(0xFFC501)
#define NODE(w) ((Node *)(0xFF0000UL | (w)))
#define LOW(n)  ((u16)(u32)(n))

/* velocity per direction, 8.8 (gg4 $51B6): 0 right, 4 down, 8 left, 12 up */
static const s16 vel[16][2] = {
    {0x0200, 0x0000}, {0x01D9, -0x00C3}, {0x016A, -0x016A}, {0x00C3, -0x01D9},
    {0x0000, -0x0200}, {-0x00C3, -0x01D9}, {-0x016A, -0x016A}, {-0x01D9, -0x00C3},
    {-0x0200, 0x0000}, {-0x01D9, 0x00C3}, {-0x016A, 0x016A}, {-0x00C3, 0x01D9},
    {0x0000, 0x0200}, {0x00C3, 0x01D9}, {0x016A, 0x016A}, {0x01D9, 0x00C3},
};

/* the head's scripts, gg4 $5216-$52FD as in the arcade: (frames, direction)
 * pairs; frames with bit 7 = last pair, followed by the address to go on at.
 * $5216: the first script after the uncoiling; $52C2/$52E0: where to go after
 * turning round, from the left/right side, low/high. */
static const u8 scr[] = {
    0x52,0x18,0x0a,0x08,0x0a,0x0b,0x0a,0x0a,0x0a,0x09,0x0a,0x08,0x0a,0x07,0x0a,0x06,
    0x0a,0x05,0x0a,0x05,0x0a,0x08,0x0a,0x07,0x0a,0x06,0x0a,0x0a,0x0a,0x06,0x0a,0x0a,
    0x0a,0x06,0x0a,0x0a,0x0a,0x06,0x0a,0x06,0x0a,0x06,0x0a,0x09,0x0a,0x0a,0x0a,0x0b,
    0x0a,0x05,0x0a,0x05,0x0a,0x06,0x0a,0x06,0x0a,0x05,0x0a,0x08,0x0a,0x0b,0x0a,0x0a,
    0x0a,0x0a,0x0a,0x07,0x0a,0x06,0x0a,0x05,0x0a,0x07,0x0a,0x0b,0x0a,0x08,0x0a,0x06,
    0x0a,0x05,0x8a,0x06,0x52,0x18,0x52,0x6e,0x0a,0x00,0x0a,0x0d,0x0a,0x0e,0x0a,0x0f,
    0x0a,0x00,0x0a,0x0f,0x0a,0x01,0x0a,0x02,0x0a,0x02,0x0a,0x02,0x0a,0x03,0x0a,0x00,
    0x0a,0x0d,0x0a,0x0e,0x0a,0x0f,0x0a,0x01,0x0a,0x02,0x0a,0x01,0x0a,0x02,0x0a,0x03,
    0x0a,0x02,0x0a,0x01,0x0a,0x0d,0x0a,0x0f,0x0a,0x0e,0x0a,0x0f,0x0a,0x00,0x0a,0x01,
    0x0a,0x02,0x0a,0x03,0x0a,0x02,0x0a,0x01,0x0a,0x00,0x0a,0x01,0x0a,0x00,0x0a,0x0f,
    0x0a,0x0e,0x0a,0x0d,0x0a,0x0f,0x0a,0x0d,0x8a,0x02,0x52,0x6e,0x52,0xc6,0x52,0xd2,
    0x0a,0x0d,0x0a,0x0c,0x0a,0x0b,0x0a,0x0a,0x8a,0x09,0x52,0x18,0x0a,0x03,0x0a,0x04,
    0x0a,0x05,0x0a,0x06,0x0a,0x07,0x8a,0x07,0x52,0x18,0x52,0xe4,0x52,0xf2,0x0a,0x0b,
    0x0a,0x0c,0x0a,0x0d,0x0a,0x0e,0x0a,0x0f,0x8a,0x00,0x52,0x6e,0x0a,0x05,0x0a,0x04,
    0x0a,0x03,0x0a,0x02,0x8a,0x01,0x52,0x6e,
};
#define SCR_BASE 0x5216
/* the uncoiling script ($D789, in gg3), ended by (0, 0) */
static const u8 intro[] = { 0x0a,0x09, 0x0a,0x0f, 0x0a,0x00, 0x0a,0x01, 0x0a,0x07, 0x0a,0x08, 0x00,0x00 };
#define INTRO_BASE 0xD789

static u8 rd(u16 a)
{
    return a >= INTRO_BASE ? intro[a - INTRO_BASE] : scr[a - SCR_BASE];
}
static u16 rdw(u16 a) { return rd(a) << 8 | rd(a + 1); }

/* 36-frame steps by side: down-right/down-left ($D943), up-right/up-left ($D947) */
static const u8 step_down[2][2] = { {0x24, 0x02}, {0x24, 0x06} };
static const u8 step_up[2][2]   = { {0x24, 0x0E}, {0x24, 0x0A} };

/* Animations, as the arcade's ($9074): each entry shows `frame` for dur+1
 * frames, then goes on at `next`. Frames are the port's type-12 sprite table
 * ($23BE5A): 1/2 the head facing right, 3/4 facing left, 5/6 the open mouth
 * (every 128 frames, with the roar), 7-10 firing, 11 a body segment, 12 the
 * tail, 13 "1000", 14 "200". */
typedef struct { u8 frame, dur; u16 next; } Anim;
enum { A_HEAD0 = 0, A_HEAD1 = 2, A_FIRE0 = 4, A_FIRE1 = 6, A_BODY = 8, A_TAIL = 9, A_NONE = 10 };
static const Anim anims[] = {
    {1, 5, 1}, {2, 5, 0},           /* $518A: side 0 */
    {3, 5, 3}, {4, 5, 2},           /* $5198: side 1 */
    {7, 8, 5}, {8, 8, 4},           /* $51FA: firing, side 0 */
    {9, 8, 7}, {10, 8, 6},          /* $5208: side 1 */
    {11, 3, 8},                     /* $D68A */
    {12, 3, 9},                     /* $D6D1 */
    {0, 0x7F, 10},                  /* the burn-up flames (not drawn) */
};

static void anim_set(Node *n, u16 a)
{
    n->anim = a; n->frame = anims[a].frame; n->atimer = 0;
}

static void animate(Node *n)            /* $9074 */
{
    if (n->atimer) { n->atimer--; return; }
    const Anim *e = &anims[n->anim];
    n->frame = e->frame; n->atimer = e->dur; n->anim = e->next;
}

static void move(Node *n)               /* $A427 */
{
    n->lx = (n->lx + vel[n->dir][0]) & 0xFFFFFF;
    n->ly = (n->ly + vel[n->dir][1]) & 0xFFFFFF;
    n->x = n->lx >> 8; n->y = n->ly >> 8;
}

/* the arcade's second random source ($68F9: a shift register at $6E/$6F).
 * In the arcade 34 places in the enemy code step it; here only the dragon
 * does. [0] = $6E, [1] = $6F (the tests set them to the arcade's). */
u8 dragon_rnd[2];
static u8 rnd(void)
{
    u8 hi = dragon_rnd[0], lo = dragon_rnd[1];
    u8 c = (u8)~(lo ^ hi) >> 6 & 1;
    dragon_rnd[0] = hi << 1 | lo >> 7;
    dragon_rnd[1] = lo = lo << 1 | c;
    return lo;
}

/* direction 0-15 from the node to Arthur ($8FE4) */
static u8 aim(Node *n, Ctx *c)
{
    static const u8 t0[4] = {0x0F, 0x09, 0x01, 0x07}, t1[4] = {0x00, 0x08, 0x00, 0x08},
                    t2[4] = {0x0D, 0x0B, 0x03, 0x05}, t3[4] = {0x0C, 0x0C, 0x04, 0x04},
                    t4[4] = {0x0E, 0x0A, 0x02, 0x06};
    u8 q = 0;
    s16 dx = c->ax - n->x, dy = c->ay - n->y;
    if (dx < 0) { dx = -dx; q = 1; }
    if (dy < 0) { dy = -dy; q |= 2; }
    u8 a = dy, b = dx;                  /* low bytes only, as the arcade */
    u8 rem = 0;                         /* $FED8: the 6809's 8-bit division, step for step */
    for (int i = 0; i < 8; i++) {
        u8 ca = a >> 7, cr = rem >> 7;  /* ASLA / ROLB carries */
        a = (a << 1) + 1;               /* ... INCA */
        rem = rem << 1 | ca;
        int r = rem - b - cr;           /* SBCB (borrows the ROLB carry) */
        rem = r;
        if (r < 0) { a--; rem += b; }   /* BCC; DECA; ADDB */
    }
    u16 p = a * 100;                    /* MUL: quotient x 100 */
    const u8 *t;
    if (p >= 600) t = t3;
    else if (p >= 150) t = t2;
    else if (p >= 75) t = t4;
    else t = (u8)(b >> 2) > rem ? t1 : t0;
    return t[q];
}

static Node *nxt(Node *n) { return n->next ? NODE(n->next) : 0; }

/* the new step's direction goes to the first segment after 10 frames, if it changed */
static void pass_on(Node *n)
{
    Node *s = nxt(n);
    if (s && s->dir != n->dir) { s->pdir = n->dir; s->delay = 10; s->pend = 1; }
}

static void load_step(Node *n, u16 p)  /* $D8C2-$D8CC */
{
    u8 f = rd(p), d = rd(p + 1);
    p += 2;
    if (f & 0x80) { f &= 0x7F; p = rdw(p); }
    n->cnt = f; n->dir = d; n->script = p;
    pass_on(n);
}

static void set_step(Node *n, u8 f, u8 d)   /* $D8CC with the script unchanged */
{
    n->cnt = f; n->dir = d;
    pass_on(n);
}

static void steer(Node *n, Ctx *c, u8 r)    /* $D818 */
{
    if (--n->cnt) return;
    u8 stage = STAGE;
    s16 x = n->x, ax = c->ax;
    if (stage != 5 && (r & 15) <= n->thresh &&
        (n->side ? (s16)(x - ax - 0x18) >= 0 : (s16)(ax - x - 0x18) >= 0)) {
        u8 d = aim(n, c);
        if (d != 4) {
            set_step(n, n->y > (u16)(c->camy + 0x60) ? 0x28 : 0x12, d);
            return;
        }
    }
    /* $D864: has it passed Arthur? */
    int passed = (u16)n->x <= (u16)c->ax ? n->side : !n->side;
    if (passed) {
        u16 xmax = *(const u16 *)(0x1043E6 + stage * 8 + 2);   /* the arcade's $5A */
        if ((u16)(xmax + 0x100) <= n->x || (u16)(n->x - c->ax + 0x5E) >= 0xBC) {
            /* $D88E: turn round */
            u16 tab = n->side ? 0x52E0 : 0x52C2;
            int hi = n->y >= (u16)(c->camy + 0x80);
            u16 p = rdw(tab + 2 * hi);
            n->side ^= 1;
            anim_set(n, n->side ? A_HEAD1 : A_HEAD0);
            load_step(n, p);
            return;
        }
    }
    /* $D8E8 */
    const u8 *s;
    if (stage != 5) {
        s16 dy = n->y - c->ay;
        if (dy < 0) s = step_up[n->side];
        else if (dy < 0xA0) { load_step(n, n->script); return; }
        else s = step_down[n->side];
    } else if ((u16)(n->homey - c->ay + 0x100) > 0x200) {
        s = n->y > c->ay ? step_up[n->side] : step_down[n->side];
    } else if ((u16)(n->y - c->ay + 0x5E) < 0xBC) {
        load_step(n, n->script); return;
    } else {
        s = n->y < c->ay ? step_up[n->side] : step_down[n->side];
    }
    set_step(n, s[0], s[1]);
}

static void fire(Node *n, Ctx *c, u8 r)     /* $D981 */
{
    if (!n->fire) {
        if ((u16)(n->y - c->ay + 0x48) > 0x90) return;
        if ((u8)(c->frame + 1) & 0x1F) return;
        if (r & 3) return;
        if (!c->projs || !*c->projs) return; /* a free projectile slot ($A7) */
        anim_set(n, n->side ? A_FIRE1 : A_FIRE0);
        n->ftimer = 10;
        n->fire = 1;
        Node *f = eng_alloc(c->projs);
        if (f) {
            u32 *p = (u32 *)f;
            for (int i = 0; i < 12; i++) p[i] = 0;
            f->x = n->side ? n->x - 10 : n->x + 10;
            f->y = n->y - 5;
            f->lx = (u32)f->x << 8; f->ly = (u32)f->y << 8;
            f->alloc = 1; f->type = 9;
            f->side = n->side;              /* its direction (+$18, dragon_fire_vel) */
        }
    }
    if (--n->ftimer) return;
    n->fire = 0;
    anim_set(n, n->side ? A_HEAD1 : A_HEAD0);
}

static void segment(Node *n)            /* $D94B / $D955 */
{
    if (n->frozen) return;
    if (n->pend && !--n->delay) {
        n->dir = n->pdir;
        n->pend = 0;
        Node *s = nxt(n);
        if (s) { s->pdir = n->dir; s->delay = s->kind == 2 ? 6 : 7; s->pend = 1; }
    }
    move(n);
}

static void each(Node *n, int count, u8 frozen)
{
    for (; n && count; count--, n = nxt(n)) n->frozen = frozen;
}

static void head_init(Node *n, Ctx *c)  /* $D542 */
{
    if (STAGE != 5) {
        /* placed at the camera + ($180, $40) as the arcade's spawn record:
         * its camera is from after the spawn frame's scroll, which here is
         * the one the object pass sees on the next update */
        n->x = c->camx + 0x180; n->y = c->camy + 0x40;
        n->lx = (u32)n->x << 8; n->ly = (u32)n->y << 8;
    }
    n->side = (s16)n->x >= (s16)c->ax;
    n->size = 3;
    anim_set(n, n->side ? A_HEAD1 : A_HEAD0);
    n->cnt = rd(INTRO_BASE); n->dir = rd(INTRO_BASE + 1); n->script = INTRO_BASE + 2;
    { static const u8 th[4] = {2, 3, 4, 5}; n->thresh = th[(RANK >> 4) & 3]; }
    n->fire = n->ftimer = 0;
    n->wait = n->frozen = 0;
    n->hp = 6;
    n->homey = n->y;
    n->sub = 1; n->sub2 = 0;
    eng_boss_init(n);
}

static void head_build(Node *n, void *free)   /* $D5A9: 7 segments and the tail */
{
    if (*(u16 *)free < 8) return;
    n->prev = 0;
    Node *u = n;
    for (int i = 7; i >= 0; i--) {
        Node *s = eng_alloc(free);
        u32 *p = (u32 *)s;
        for (int k = 0; k < 12; k++) p[k] = 0;
        if (i == 7) { s->x = u->x + 0x14; s->y = u->y - 3; }
        else if (i > 0) { s->x = u->x + 0x0E; s->y = u->y; }
        else { s->x = u->x + 0x0C; s->y = u->y + 2; }
        s->lx = (u32)s->x << 8; s->ly = (u32)s->y << 8;
        s->alloc = 1;
        s->type = 12;
        s->kind = i ? 1 : 2;
        s->prev = LOW(u);
        u->next = LOW(s);
        u = s;
    }
    n->sub = 2;
}

static void seg_init(Node *n, Ctx *c)   /* $D64B, $D690 */
{
    n->dir = (s16)n->x >= (s16)c->ax ? 8 : 0;
    n->size = n->kind == 2 ? 0 : 1;
    anim_set(n, n->kind == 2 ? A_TAIL : A_BODY);
    n->pdir = n->delay = n->pend = 0;
    n->frozen = n->fire = 0;
    n->hp = 1;
    n->state = 1; n->sub = 0; n->sub2 = 0;
}

static void head_run(Node *n, Ctx *c)
{
    if (n->sub == 0) {
        switch (n->sub2) {
        case 0: {                       /* $D728 */
            Node *s = nxt(n);
            s->delay = n->cnt; s->pdir = n->dir; s->pend = 1;
            n->sub2 = 1;
            return;
        }
        case 1: {                       /* $D73D */
            if (--n->cnt) return;
            u8 f = rd(n->script), d = rd(n->script + 1);
            Node *s = nxt(n);
            if (f | d) {
                n->cnt = f; n->dir = d; n->script += 2;
                s->delay = f; s->pdir = d; s->pend = 1;
                move(n);
                return;
            }
            each(n, 9, 1);
            u16 p = rdw(SCR_BASE);
            n->cnt = rd(p); n->dir = rd(p + 1); n->script = p + 2;
            s->delay = n->cnt; s->pdir = n->dir; s->pend = 1;
            n->sub2 = 2;
            return;
        }
        case 2: {                       /* $D797 */
            static const u8 w6[4] = {5, 2, 5, 4}, w[4] = {3, 2, 3, 2};
            n->wait = (STAGE == 5 ? w6 : w)[(u8)(c->frame + c->slot) & 3];
            n->sub2 = 3;
            return;
        }
        case 3:                         /* $D7B9 */
            if (n->onscr) n->sub2 = 4;
            return;
        default:                        /* $D7C0 */
            if ((s16)(c->ay + 0x20 - n->y) < 0) return;
            if ((u8)(c->frame + 1) & 0x0F) return;
            if (--n->wait) return;
            n->sub = 1; n->sub2 = 0;
            each(n, 9, 0);
            return;
        }
    }
    /* $D7EE */
    if (!((u8)(c->frame + 1) & 0x7F)) {
        n->frame = n->side ? 6 : 5;
        n->atimer = 10;
        eng_sound(0x21);
    }
    animate(n);
    u8 r = rnd();
    steer(n, c, r);
    fire(n, c, r);
    move(n);
}

static void lose_tail(Node *t)          /* $DA3B */
{
    Node *p = NODE(t->prev);
    if (p->idx != 8) p->idx = 0;
    p->next = 0;
    t->state = 2; t->sub = 4;
}

static void dying(Node *n, Ctx *c)
{
    switch (n->sub) {
    case 0:                             /* $DA15: just hit */
        if (n->idx == 8) {              /* the head: everything goes */
            for (Node *s = nxt(n); s; s = nxt(s)) { s->state = 2; s->sub = 4; s->alloc++; }
            n->state = 2; n->sub = 1;
            return;
        }
        if (n->idx) {                   /* a segment: it lives on, the tail goes */
            Node *t = n;
            while (t->idx) t = nxt(t);
            t->alloc++;
            n->state = 1; n->sub = 0;
            n->alloc = 1; n->hp = 1;
            segment(n);
            lose_tail(t);
            return;
        }
        lose_tail(n);
        return;
    case 1:                             /* $DA6D */
        eng_sound(0x0F);
        n->key = 1; n->cnt = 0x3F; n->sub = 2;
        return;
    case 2:                             /* $E8A7: burn-up, 3 + 18 frames */
        if (n->sub2 == 0) { n->size = 3; anim_set(n, A_NONE); animate(n); n->dir = 3; n->sub2 = 1; return; }
        if (n->sub2 == 1) {
            if (--n->dir) { animate(n); return; }
            n->size = 4; anim_set(n, A_NONE); animate(n); n->dir = 0x12; n->sub2 = 2; return;
        }
        if (--n->dir) { animate(n); return; }
        n->sub = 3; n->sub2 = 0;
        return;
    case 3:                             /* $DA87: "1000" */
        n->size = 2; n->frame = 13;
        if (--n->cnt) return;
        eng_score(0x0C09);
        n->state = 3; n->sub = 0; n->sub2 = 0;
        return;
    case 4:                             /* $DA7B */
        eng_sound(0x1B);
        n->key = 0; n->cnt = 0x3F; n->sub = 5;
        return;
    case 5:                             /* $E886: burn-up, 36 frames */
        if (n->sub2 == 0) { n->size = 3; anim_set(n, A_NONE); animate(n); n->dir = 0x24; n->sub2 = 1; return; }
        if (--n->dir) { animate(n); return; }
        n->sub = 6; n->sub2 = 0;
        return;
    default:                            /* $DAA2: "200" */
        n->size = 2; n->frame = 14;
        if (--n->cnt) return;
        n->state = 3; n->sub = 0; n->sub2 = 0;
        return;
    }
}

void dragon_update(Node *n, Ctx *c, void *free)
{
    if (n->type != 12 || !n->alloc) return;
    switch (n->state) {
    case 0:
        if (n->kind) { seg_init(n, c); return; }
        if (n->sub == 0) {
            if (n->sub2) { n->sub2 = 0; return; }   /* the spawn update (dragon_spawn_pos) */
            head_init(n, c); return;
        }
        if (n->sub == 1) { head_build(n, free); return; }
        {                               /* $D633 */
            u8 i = 8;
            for (Node *s = n; s; s = nxt(s)) s->idx = i--;
            n->state = 1; n->sub = 0; n->sub2 = 0;
        }
        return;
    case 1:
        if (n->kind == 0) head_run(n, c);
        else segment(n);
        if (STAGE != 2 &&                /* $D6DE: lost when far off screen (not in stage 3) */
            ((u16)(n->x - c->camx + 0x180) > 0x400 || (u16)(n->y - c->camy + 0x180) > 0x400)) {
            n->state = 3; n->sub = 0; n->sub2 = 0;
        }
        return;
    case 2:
        dying(n, c);
        return;
    default:                            /* $DAB7 */
        n->state = n->sub = n->sub2 = 0;
        if (n->kind == 0 && n->key) eng_boss_done(n);
        n->alloc = 0; n->onscr = 0;
        eng_free(free, n);
        return;
    }
}

/* the fire's speed by direction (+$18: 0 right, 1 left), 3.125 px/frame along
 * the head's side (gg4 $5E07, type 9 of the projectile table $5D57); read by
 * the port's type-9 mover ($107540) in place of its aimed 16-direction table */
const s16 dragon_fire_vel[2][2] = { {0x0320, 0}, {-0x0320, 0} };
