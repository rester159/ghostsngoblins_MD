/* Boot flow and menus: intros -> HOME / ARCADE -> (title + attract) or Home.
 * The previous port's own splash ($CA6: ARCADE MACHINE, PROGRAMED BY FRANK)
 * is never shown. */
#include "md.h"
#include "common.h"
#include "build/credits.inc"

void sound_stop(void);
int  title_jp(void);
void draw_jp_logo(int row, int pal);
int  draw_mega_logo(int sub);            /* title.c: returns the rows drawn */
void hiscore_defaults(void);
void vsync_reset_display(void);
void boot_intros(void);        /* intro.c: SEGA and CAPCOM logos */
void vd_story(void);           /* vendetta.c: Firebrand's Vendetta's story */

enum { FLOW_TITLE = 1, FLOW_HOME_START = 2 };   /* hook_title: 0 and 1 both start the title */
#define MENU_BACK  (-1)
#define MENU_CODE  (-2)

/* ---- generic list --------------------------------------------------- */

typedef struct {
    const char *const *items;
    int n;
    int x;                              /* label column */
    int vx;                             /* value column, 0 = no values */
    const char *(*value)(int i);        /* text for item i, or 0 */
    void (*change)(int i, int dir);     /* left/right */
    int combo;                          /* watch for the developer code */
} Menu;

static u16 pad_prev;
static u8  code_pos;
static const u8 code_seq[8] = {
    BTN_UP, BTN_DOWN, BTN_UP, BTN_DOWN, BTN_LEFT, BTN_RIGHT, BTN_LEFT, BTN_RIGHT,
};

static void draw_menu(const Menu *m, int y0, int sel)
{
    int i;
    for (i = 0; i < m->n; i++) {
        int y = y0 + i * 2, pal = i == sel ? PAL_SEL : PAL_TEXT;
        text(m->x - 2, y, i == sel ? ">" : " ", PAL_SEL);
        text(m->x, y, m->items[i], pal);
        if (m->vx) {
            const char *v = m->value ? m->value(i) : 0;
            text(m->vx, y, "                  ", PAL_TEXT);
            if (v) text(m->vx, y, v, pal);
        }
    }
}

static int menu_run(const Menu *m, int y0, int sel)
{
    pad_prev = 0xFF;                    /* ignore buttons still held */
    code_pos = 0;
    for (;;) {
        u16 p, e;
        draw_menu(m, y0, sel);
        vsync();
        game_sound_tick();
        p = pad_read(0);
        e = p & ~pad_prev;
        pad_prev = p;
        if (m->combo && (e & 0x0F)) {
            code_pos = (e & 0x0F) == code_seq[code_pos] ? code_pos + 1
                     : (e & 0x0F) == code_seq[0] ? 1 : 0;
            if (code_pos == 8) return MENU_CODE;
        }
        if (e & BTN_UP)   sel = sel ? sel - 1 : m->n - 1;
        if (e & BTN_DOWN) sel = sel == m->n - 1 ? 0 : sel + 1;
        if (m->change && (e & (BTN_LEFT | BTN_RIGHT)))
            m->change(sel, e & BTN_LEFT ? -1 : 1);
        if (e & (BTN_A | BTN_C | BTN_START)) return sel;
        if (e & BTN_B) return MENU_BACK;
    }
}

/* Home's screens (its menu and the ones under it) show Mega Ghosts'n Goblins'
 * logo with the English title: whole on the Home menu (its items a row under
 * it), 10 rows of it (MEGA and the title) above a screen title. */
static u8 in_home, logo_rows;

static int mega(void) { return in_home && !title_jp(); }

static void logo(int sub)
{
    if (title_jp()) draw_jp_logo(3, PAL_TEXT);
    else if (in_home) logo_rows = draw_mega_logo(sub);
    else draw_logo(5);
}

static void frame_screen(const char *title)
{
    screen_init();
    logo(title != 0);
    if (title) text_center(10, title, PAL_TEXT);
}

/* OPTIONS' logo after TITLE changes: rows 0-9, OPTIONS on row 10. */
static void redraw_logo(void)
{
    int i;
    VDP_CTRLL = VRAM_W(0xC000);
    for (i = 0; i < 10 * 64; i++) VDP_DATA = 0;     /* any logo */
    clear_rows(10, 10);
    logo(1);
    text_center(10, "OPTIONS", PAL_TEXT);
}

static int wrap(int v, int dir, int n) { v += dir; return v < 0 ? n - 1 : v >= n ? 0 : v; }

/* ---- arcade DIP switches -------------------------------------------- */

static const char *const dip_items[] = {
    "COINAGE", "LIVES", "BONUS", "DIFFICULTY", "DEMO SOUND", "CONTINUE", "BACK",
};
static const char *dip_val(int i) { return i < DIP_N ? dip_value(i, PERSIST->dip[i]) : 0; }
static void dip_chg(int i, int d) { if (i < DIP_N) PERSIST->dip[i] = wrap(PERSIST->dip[i], d, dip_count(i)); }

static void dip_menu(void)
{
    static const Menu m = { dip_items, 7, 3, 14, dip_val, dip_chg, 0 };
    int sel = 0;
    frame_screen("DIP SWITCHES");
    display_on();
    for (;;) {
        sel = menu_run(&m, 12, sel);
        if (sel == MENU_BACK || sel == 6) break;
    }
    save_write();
}

/* ---- options (Home) ----------------------------------------------- */

static const char *const opt_items[] = {
    "LIVES", "CONTINUES", "BONUS", "DIFFICULTY", "WEAPON", "TITLE", "SOUND TEST", "BACK",
};
enum { OPT_TITLE = HOP_N, OPT_SOUND, OPT_BACK };
static char snd_buf[3];
static const char *opt_val(int i)
{
    if (i < HOP_N) return home_value(i, PERSIST->home[i]);
    if (i == OPT_TITLE) return PERSIST->title_jp ? "JAPANESE" : "ENGLISH";
    if (i == OPT_SOUND) { num2(snd_buf, PERSIST->sound_id); return snd_buf; }
    return 0;
}
static void opt_chg(int i, int d)
{
    if (i < HOP_N) PERSIST->home[i] = wrap(PERSIST->home[i], d, home_count(i));
    if (i == OPT_TITLE) { PERSIST->title_jp ^= 1; redraw_logo(); }
    if (i == OPT_SOUND) PERSIST->sound_id = (PERSIST->sound_id + d) & 63;
}

/* 8 items: under OPTIONS, as DEVELOPER (they don't fit under the whole logo) */
static void options_menu(void)
{
    static const Menu m = { opt_items, OPT_BACK + 1, 3, 14, opt_val, opt_chg, 0 };
    int sel = 0;
    frame_screen("OPTIONS");
    display_on();
    game_sound_init();
    for (;;) {
        sel = menu_run(&m, 12, sel);
        if (sel == OPT_SOUND) { sound_stop(); game_sound_play(PERSIST->sound_id); continue; }
        if (sel == MENU_BACK || sel == OPT_BACK) break;
    }
    sound_stop();
    save_write();
}

/* ---- developer (secret) ------------------------------------------- */

static const char *const dev_items[] = {
    "STAGE", "LIVES", "INFINITE", "DIFFICULTY", "PLAYERS", "SOUND TEST", "LAUNCH", "BACK",
};
static char dev_buf[3];
static const char *dev_val(int i)
{
    Persist *p = PERSIST;
    if (i == 0) { dev_buf[0] = '0' + p->dev_stage; dev_buf[1] = 0; return dev_buf; }
    if (i == 1) { dev_buf[0] = '0' + p->dev_lives; dev_buf[1] = 0; return dev_buf; }
    if (i == 2) return p->dev_inf ? "ON" : "OFF";
    if (i == 3) return home_value(HOP_DIFF, p->dev_diff);
    if (i == 4) return p->dev_players == 4 ? "VENDETTA" : p->dev_players == 3 ? "FIREBRAND PLUS"
                     : p->dev_players == 2 ? "FIREBRAND" : p->dev_players ? "2" : "1";
    if (i == 5) { num2(dev_buf, p->sound_id); return dev_buf; }
    return 0;
}
static void dev_chg(int i, int d)
{
    Persist *p = PERSIST;
    if (i == 0) p->dev_stage = wrap(p->dev_stage - 1, d, 6) + 1;
    if (i == 1) p->dev_lives = wrap(p->dev_lives - 1, d, 9) + 1;
    if (i == 2) p->dev_inf ^= 1;
    if (i == 3) p->dev_diff = wrap(p->dev_diff, d, 4);
    if (i == 4) p->dev_players = wrap(p->dev_players % 5, d, 5);
    if (i == 5) p->sound_id = (p->sound_id + d) & 63;
}

/* returns 1 to launch a practice session */
static int dev_menu(void)
{
    static const Menu m = { dev_items, 8, 3, 16, dev_val, dev_chg, 0 };
    Persist *p = PERSIST;
    int sel = 0;
    if (!p->dev_stage) p->dev_stage = 1;
    if (!p->dev_lives) p->dev_lives = 3;
    frame_screen("DEVELOPER");
    text_center(27, "PRACTICE - NO RANKING", PAL_DIM);
    display_on();
    game_sound_init();
    for (;;) {
        sel = menu_run(&m, 12, sel);
        if (sel == 5) { sound_stop(); game_sound_play(p->sound_id); continue; }
        if (sel == 6) { sound_stop(); return 1; }
        if (sel == MENU_BACK || sel == 7) { sound_stop(); return 0; }
    }
}

/* ---- home ---------------------------------------------------------- */

/* FIREBRAND'S QUEST PLUS is listed once Firebrand's Quest has been cleared,
 * DEVELOPER once its code has been entered. No title, no BACK: B goes back. */
static int home_menu(void)
{
    enum { I_1P, I_COOP, I_FB, I_FBPLUS, I_VD, I_OPTIONS, I_DEV };
    static const char *const names[] = {
        "1 PLAYER", "2 PLAYERS", "FIREBRAND'S QUEST", "FIREBRAND'S QUEST PLUS", "FIREBRAND'S VENDETTA",
        "OPTIONS", "DEVELOPER",
    };
    static const u8 dev_sub[5] = { HOME_1P, HOME_COOP, HOME_FIREBRAND, HOME_FIREBRAND, HOME_VENDETTA };
    Persist *p = PERSIST;
    int sel = 0;
    in_home = 1;
    for (;;) {
        const char *items[7];
        u8 ids[7];
        int n = 0, id, k;
        for (k = I_1P; k <= I_DEV; k++) {
            if (k == I_FBPLUS && !p->fb_unlocked) continue;
            if (k == I_DEV && !p->dev_unlocked) continue;
            ids[n] = k; items[n++] = names[k];
        }
        Menu m = { items, n, 9, 0, 0, 0, !p->dev_unlocked };
        frame_screen(0);
        display_on();
        sel = menu_run(&m, mega() ? logo_rows + 1 : 11, sel);
        p->dev_on = 0;
        p->fb_plus = 0;
        p->fly_lv = 1;                  /* a new game: Firebrand's flight from level 1 */
        p->fly_stage = 0;
        if (sel == MENU_CODE) { p->dev_unlocked = 1; sel = n; continue; }
        id = sel < 0 ? -1 : ids[sel];
        if (id == I_1P) { p->home_sub = HOME_1P; return 1; }
        if (id == I_COOP) { p->home_sub = HOME_COOP; return 1; }
        if (id == I_FB) { p->home_sub = HOME_FIREBRAND; return 1; }
        if (id == I_FBPLUS) { p->home_sub = HOME_FIREBRAND; p->fb_plus = 1; return 1; }
        if (id == I_VD) { p->home_sub = HOME_VENDETTA; vd_story(); return 1; }
        if (id == I_OPTIONS) { options_menu(); continue; }
        if (id == I_DEV) {
            if (dev_menu()) {
                p->dev_on = 1;
                p->home_sub = dev_sub[p->dev_players % 5];
                p->fb_plus = p->dev_players % 5 == 3;
                return 1;
            }
            continue;
        }
        return 0;
    }
}

/* ---- arcade -------------------------------------------------------- */

static int arcade_menu(void)
{
    static const char *const items[] = { "PLAY", "DIP SWITCHES", "HIGH SCORES", "BACK" };
    static const Menu m = { items, 4, 10, 0, 0, 0, 0 };
    int sel = 0;
    for (;;) {
        frame_screen("ARCADE");
        display_on();
        sel = menu_run(&m, 13, sel);
        if (sel == 0) return 1;
        if (sel == 1) { dip_menu(); continue; }
        if (sel == 2) { hiscore_show(0, 60 * 30); continue; }
        return 0;
    }
}

/* ---- community credits ------------------------------------------- */

#define CRED_T   0x300                  /* free on the menu screens (Home's logo is elsewhere) */
#define CRED_ROW 3

/* The people from the itch.io page's comments: art, then the playtesters in
 * the order of how much they reported. Any button goes back. */
static void credits_screen(void)
{
    static const char *const art[] = { "ROBOT-RANDOM", "HJRODRIGO", "GOODLUCKTRYING" };
    static const char *const testers[] = {
        "METALCANDYMAN", "ROBOT-RANDOM", "DARKFALZX", "DANGLYLINGHAM",
    };
    u16 p;
    int i;
    screen_init();                      /* no logo: the title in its lettering (mkcredits.py) */
    VDP_CTRLL = VRAM_W(CRED_T * 32);
    for (i = 0; i < CRED_NT * 16; i++) VDP_DATA = cred_tiles[i];
    for (i = 0; i < 3 * 32; i++) {
        if (!(i & 31)) VDP_CTRLL = VRAM_W(0xC000 + (CRED_ROW + i / 32) * 128);
        VDP_DATA = cred_map[i] ? CRED_T + cred_map[i] : 0;
    }
    text_center(8, "ADDITIONAL ART", PAL_SEL);   /* both lists a name every other row */
    for (i = 0; i < (int)(sizeof(art) / sizeof(art[0])); i++) text_center(10 + 2 * i, art[i], PAL_TEXT);
    text_center(17, "PLAYTESTING", PAL_SEL);
    for (i = 0; i < (int)(sizeof(testers) / sizeof(testers[0])); i++) text_center(19 + 2 * i, testers[i], PAL_TEXT);
    display_on();
    pad_prev = 0xFF;                    /* ignore buttons still held */
    for (;;) {
        vsync();
        game_sound_tick();
        p = pad_read(0);
        if (p & ~pad_prev & (BTN_A | BTN_B | BTN_C | BTN_START)) return;
        pad_prev = p;
    }
}

/* ---- boot ---------------------------------------------------------- */

static int boot_menu(void)
{
    static const char *const items[] = { "ARCADE", "HOME", "COMMUNITY CREDITS" };
    static const Menu m = { items, 3, 8, 0, 0, 0, 0 };
    int sel = PERSIST->mode == MODE_HOME ? 1 : 0;
    for (;;) {
        in_home = 0;
        frame_screen(0);
        text_center(26, "RESTER159, 2026 - " VERSION, PAL_TEXT);   /* the opening menu only */
        display_on();
        sel = menu_run(&m, 14, sel);
        if (sel == 0) {
            PERSIST->mode = MODE_ARCADE;
            if (arcade_menu()) return FLOW_TITLE;
        }
        if (sel == 1) {
            PERSIST->mode = MODE_HOME;
            if (home_menu()) return FLOW_HOME_START;
        }
        if (sel == 2) credits_screen();
        if (sel < 0) sel = 0;
    }
}

/* Leave VRAM text-free: the title screen only redraws plane B. */
static int leave_menus(int flow)
{
    int i;
    vdp_reg(1, 0x04);
    vsync_reset_display();
    VDP_CTRLL = VRAM_W(0xE000);
    for (i = 0; i < 0x800; i++) VDP_DATA = 0;
    return flow;
}

int boot_flow(void)
{
    Persist *p = PERSIST;
    int warm = p->magic == PERSIST_MAGIC && p->warm;

    if (p->magic != PERSIST_MAGIC) {
        u8 *b = (u8 *)p;
        int i;
        for (i = 0; i < 256; i++) b[i] = 0;
        p->magic = PERSIST_MAGIC;
        settings_defaults();
        hiscore_defaults();
    }
    p->warm = 0;
    pads_init();
    if (!warm) {
        save_load();
        p->dev_unlocked = 0;            /* the code lasts until a hardware reset */
        p->dev_on = 0;
    }

    if (warm && p->mode == MODE_ARCADE) return FLOW_TITLE;
    if (warm && p->mode == MODE_HOME) {
        if (home_menu()) return leave_menus(FLOW_HOME_START);
        return leave_menus(boot_menu());
    }
    boot_intros();
    return leave_menus(boot_menu());
}
