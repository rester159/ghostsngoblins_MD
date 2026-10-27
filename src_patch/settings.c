/* Arcade DIP switches, Home options, and the gameplay hooks that apply them. */
#include "md.h"
#include "common.h"

#define LIVES      RAM8(0xFFC500)
#define RANK       RAM8(0xFFC501)   /* bits 4-5 pick the enemy parameter set */
#define SCORE      RAM32(0xFFC000)  /* BCD */
#define TOPSCORE   RAM32(0xFFC004)
#define STAGE      RAM8(0xFFC512)
#define CONT_TIMER RAM16(0xFFC594)

/* ---- option tables ---------------------------------------------------- */

const char *const dip_names[DIP_N] = {
    "COINAGE", "LIVES", "BONUS", "DIFFICULTY", "DEMO SOUND", "CONTINUE",
};
static const char *const coin_vals[] = { "1C 1P", "1C 2P", "1C 3P", "2C 1P", "3C 1P", "FREE PLAY" };
static const char *const dlives_vals[] = { "3", "4", "5", "7" };
static const char *const bonus_vals[] = {
    "20K 70K EVERY 70K", "30K 80K EVERY 80K", "20K 80K", "30K 80K", "NONE",
};
/* the arcade's DSW2 difficulty in its own order: starting rank $57 from its
 * table at $6228, indexed by (~DSW2 & $60) >> 5 */
static const char *const diff_vals[] = { "NORMAL", "EASY", "DIFFICULT", "VERY DIFFICULT" };
static const u8 diff_rank[4] = { 0x06, 0x00, 0x18, 0x20 };
static const char *const onoff_vals[] = { "OFF", "ON" };

const char *const home_names[HOP_N] = { "LIVES", "CONTINUES", "BONUS", "DIFFICULTY" };
static const char *const digits[] = { "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "INFINITE" };

int dip_count(int i)
{
    static const u8 n[DIP_N] = { 6, 4, 4, 4, 2, 2 };   /* arcade bonus: the 4 board settings */
    return n[i];
}

const char *dip_value(int i, int v)
{
    switch (i) {
    case DIP_COIN:  return coin_vals[v];
    case DIP_LIVES: return dlives_vals[v];
    case DIP_BONUS: return bonus_vals[v];
    case DIP_DIFF:  return diff_vals[v];
    default:        return onoff_vals[v];
    }
}

int home_count(int i)
{
    static const u8 n[HOP_N] = { 9, 11, 5, 4 };
    return n[i];
}

const char *home_value(int i, int v)
{
    switch (i) {
    case HOP_LIVES: return digits[v + 1];           /* 1-9 */
    case HOP_CONT:  return digits[v];               /* 0-9, INFINITE */
    case HOP_BONUS: return bonus_vals[v];
    default:        return diff_vals[v];
    }
}

void settings_defaults(void)
{
    Persist *p = PERSIST;
    p->dip[DIP_COIN] = 0;
    p->dip[DIP_LIVES] = 0;          /* 3 */
    p->dip[DIP_BONUS] = 0;
    p->dip[DIP_DIFF] = 0;           /* the parameter set the port shipped with */
    p->dip[DIP_DEMO] = 1;
    p->dip[DIP_CONT] = 1;
    p->home[HOP_LIVES] = 2;         /* 3 */
    p->home[HOP_CONT] = 3;
    p->home[HOP_BONUS] = 0;
    p->home[HOP_DIFF] = 0;
}

int is_home(void)   { return PERSIST->magic == PERSIST_MAGIC && PERSIST->mode == MODE_HOME; }
int is_arcade(void) { return PERSIST->magic == PERSIST_MAGIC && PERSIST->mode == MODE_ARCADE; }

static int start_lives(void)
{
    static const u8 arcade_lives[4] = { 3, 4, 5, 7 };
    Persist *p = PERSIST;
    if (p->dev_on) return p->dev_lives;
    if (is_home()) return p->home[HOP_LIVES] + 1;
    if (is_arcade()) return arcade_lives[p->dip[DIP_LIVES]];
    return 3;
}

int coop_start_lives(void) { return start_lives(); }

static int difficulty(void)
{
    Persist *p = PERSIST;
    if (p->dev_on) return p->dev_diff;
    if (is_home()) return p->home[HOP_DIFF];
    if (is_arcade()) return p->dip[DIP_DIFF];
    return 0;
}

static int bonus_setting(void)
{
    if (is_home()) return PERSIST->home[HOP_BONUS];
    if (is_arcade()) return PERSIST->dip[DIP_BONUS];
    return 4;                       /* the shipped port has no extra lives */
}

/* first, second, then every (BCD); 0 = none */
static const u32 bonus_tab[5][3] = {
    { 0x20000, 0x70000, 0x70000 },
    { 0x30000, 0x80000, 0x80000 },
    { 0x20000, 0x80000, 0 },
    { 0x30000, 0x80000, 0 },
    { 0, 0, 0 },
};

static u32 bcd_add(u32 a, u32 b)
{
    u32 r = 0, carry = 0, shift;
    for (shift = 0; shift < 32; shift += 4) {
        u32 d = ((a >> shift) & 15) + ((b >> shift) & 15) + carry;
        carry = d > 9;
        if (carry) d -= 10;
        r |= d << shift;
    }
    return r;
}

/* ---- hooks (called from glue.s) ------------------------------------- */

static u8 stage_pending;
void stage_jump(int stage);         /* glue.s: what the game does at a stage end */

void p2_frame(void);
void fb_frame(void);
int  fb_plus_on(void);
void p2_reset(void);

/* $61A2: player block initialised at game start */
void arc_rand_seed(void);   /* arcrand.c */

void player_init(void)
{
    arc_rand_seed();                /* every game starts from $87CD, as the arcade's */
    p2_reset();
    LIVES = start_lives();
    RANK = diff_rank[difficulty()];
    if (fb_plus_on()) RANK = FB_PLUS_RANK;  /* Firebrand's Quest Plus: the top starting rank */
    RAM8(0xFFC561) = RANK;          /* floor for the per-death rank decrease */
    /* debug launch to a later stage: entered on the first frame of play */
    stage_pending = PERSIST->dev_on && PERSIST->dev_stage > 1 ? PERSIST->dev_stage : 0;
}

/* $6348: continue. As the arcade's ($7882 -> $6C33): lives from the setting,
 * the score back to 0 and the bonus-life thresholds from the start; the stage
 * and checkpoint stay. The port kept the score. */
void continue_lives(void)
{
    LIVES = start_lives();
    SCORE = 0;
    PERSIST->bonus_next = bonus_tab[bonus_setting()][0];
    PERSIST->bonus_step_i = 1;
}

/* $7890: score block initialised at game start */
void score_init(void)
{
    Persist *p = PERSIST;
    int t = hiscore_table();
    u32 best = p->hs[t][0].score;
    if (best > TOPSCORE) TOPSCORE = best;
    p->bonus_next = bonus_tab[bonus_setting()][0];
    p->bonus_step_i = 1;
}

/* One bonus-life check (the arcade's $EDA8-$EDF1): returns 1 if a life was given. */
int bonus_give(void)
{
    Persist *p = PERSIST;
    if (!p->bonus_next) return 0;
    if (SCORE >= 0x1000000) return 0;       /* the arcade stops at 1,000,000 ($ED95) */
    if (SCORE < p->bonus_next) return 0;
    LIVES++;                                /* no cap: the arcade's INC <$60 ($EDF1) */
    {
        const u32 *t = bonus_tab[bonus_setting()];
        if (p->bonus_step_i == 1) p->bonus_next = t[1];
        else p->bonus_next = t[2] ? bcd_add(p->bonus_next, t[2]) : 0;
        if (p->bonus_step_i < 2) p->bonus_step_i++;
    }
    return 1;
}

/* $779A: after points were added to the score at a4. The life waits for the
 * arcade's check in play (bonus.c). */
void score_added(u32 a4)
{
    if (a4 != 0xFFC000) return;
    bonus_pending = 1;
}

/* $62FA: each frame of the continue countdown */
void continue_tick(void)
{
    Persist *p = PERSIST;
    if (p->dev_on && p->dev_inf) { G_CREDITS = 9; return; }
    if (is_home()) {
        if (p->home[HOP_CONT] == HOME_CONT_INF) G_CREDITS = 9;
        else if (!G_CREDITS) CONT_TIMER = 0;
    } else if (is_arcade()) {
        if (!p->dip[DIP_CONT]) CONT_TIMER = 0;
        else if (p->dip[DIP_COIN] == 5) G_CREDITS = 9;      /* free play */
    }
}

/* $89E4 (sound play): returns 0 to drop the sound */
int sound_allowed(void)
{
    return !(is_arcade() && !PERSIST->dip[DIP_DEMO] && G_ATTRACT);
}

/* Home start: credits are the continues; debug launches pick the stage. */
void home_prestart(void)
{
    Persist *p = PERSIST;
    int c = p->home[HOP_CONT];
    G_CREDITS = c == HOME_CONT_INF ? 9 : c;
}

/* once per frame from the pad routine during play */
void play_tick(void)
{
    Persist *p = PERSIST;
    if (stage_pending) {
        int st = stage_pending;
        stage_pending = 0;
        stage_jump(st - 1);         /* STAGE n is stage index n - 1 ($FFC512) */
    }
    if (p->dev_on && p->dev_inf && LIVES < 3) LIVES = 3;
    p2_frame();
    fb_frame();
}

/* coin inserted (arcade) */
void coin_inserted(void)
{
    static const u8 coins[6] = { 1, 1, 1, 2, 3, 1 };
    static const u8 creds[6] = { 1, 2, 3, 1, 1, 9 };
    Persist *p = PERSIST;
    int c = is_arcade() ? p->dip[DIP_COIN] : 0;
    if (++p->coin_count < coins[c]) return;
    p->coin_count = 0;
    G_CREDITS = G_CREDITS + creds[c] > 9 ? 9 : G_CREDITS + creds[c];
}
