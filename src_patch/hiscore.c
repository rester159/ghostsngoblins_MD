/* Top-10 tables (Arcade and Home) kept in SRAM, initials entry at game over. */
#include "md.h"
#include "common.h"

void sound_stop(void);
int  title_jp(void);
void draw_jp_logo(int row, int pal);

#define SCORE RAM32(0xFFC000)
#define STAGE RAM8(0xFFC512)

/* the attract-mode ranking's names */
static const char def_names[10][4] = {
    "YUK", "FUM", "MIK", "TOM", "TAN", "KEI", "RUM", "MAY", "ODA", "CAP",
};

void hiscore_defaults(void)
{
    int t, i, k;
    for (t = 0; t < 2; t++)
        for (i = 0; i < 10; i++) {
            HiScore *h = &PERSIST->hs[t][i];
            for (k = 0; k < 3; k++) h->name[k] = def_names[i][k];
            h->stage = 1;
            h->score = 0x10000;     /* 10000, the game's default TOP SCORE */
        }
}

int hiscore_table(void) { return is_home() ? 1 : 0; }

static const char *const ordinals[10] = {
    "TOP", "2ND", "3RD", "4TH", "5TH", "6TH", "7TH", "8TH", "9TH", "10TH",
};

static void header(const char *title)
{
    screen_init();
    if (title_jp()) draw_jp_logo(1, PAL_TEXT);
    else draw_logo(1);
    text_center(6, title, PAL_TEXT);
    display_on();
}

static void draw_table(int t, int hl)
{
    int i;
    char buf[12], st[2] = { 0, 0 };
    text(3, 8, "RANK  NAME     SCORE  STAGE", PAL_DIM);
    for (i = 0; i < 10; i++) {
        HiScore *h = &PERSIST->hs[t][i];
        int pal = i == hl ? PAL_SEL : PAL_TEXT, y = 10 + i;
        char nm[4] = { h->name[0], h->name[1], h->name[2], 0 };
        text(3, y, ordinals[i], pal);
        text(9, y, nm, pal);
        bcd_str(buf, h->score);
        text(14, y, buf, pal);
        st[0] = '0' + h->stage;
        text(27, y, st, pal);
    }
}

static int wait_button(int frames)
{
    u16 prev = 0xFF;
    while (frames-- > 0) {
        u16 p;
        vsync();
        game_sound_tick();
        p = pad_read(0);
        if (p & ~prev & (BTN_A | BTN_B | BTN_C | BTN_START)) return 1;
        prev = p;
    }
    return 0;
}

void hiscore_show(int t, int wait)
{
    header(t ? "BEST RANKING  HOME" : "BEST RANKING  ARCADE");
    draw_table(t, -1);
    wait_button(wait);
}

static void enter_initials(int t, int pos)
{
    static const char abc[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ.!? ";
    HiScore *h = &PERSIST->hs[t][pos];
    int cur = 0, idx[3] = { 0, 0, 0 }, timer = 60 * 30;
    u16 prev = 0xFF;
    header("ENTER YOUR INITIALS");
    while (cur < 3 && timer-- > 0) {
        u16 p, e;
        int k;
        for (k = 0; k < 3; k++) {
            h->name[k] = k <= cur ? abc[idx[k]] : '.';
        }
        draw_table(t, pos);
        vsync();
        game_sound_tick();
        p = pad_read(0);
        e = p & ~prev;
        prev = p;
        if (e & BTN_UP)    idx[cur] = idx[cur] ? idx[cur] - 1 : (int)sizeof(abc) - 2;
        if (e & BTN_DOWN)  idx[cur] = idx[cur] == (int)sizeof(abc) - 2 ? 0 : idx[cur] + 1;
        if (e & (BTN_A | BTN_C | BTN_START | BTN_RIGHT)) cur++;
        if ((e & (BTN_B | BTN_LEFT)) && cur) cur--;
    }
    for (; cur < 3; cur++) h->name[cur] = abc[idx[cur]];
}

/* Called from the game-over path before the soft restart. */
void game_over(void)
{
    Persist *p = PERSIST;
    int t = hiscore_table(), i, pos = -1;
    u32 s = SCORE;
    if (p->dev_on || p->mode == MODE_NONE) return;     /* practice runs don't count */
    for (i = 0; i < 10; i++)
        if (s > p->hs[t][i].score) { pos = i; break; }
    sound_stop();
    if (pos >= 0) {
        for (i = 9; i > pos; i--) p->hs[t][i] = p->hs[t][i - 1];
        p->hs[t][pos].score = s;
        p->hs[t][pos].stage = STAGE < 2 ? 1 : STAGE;
        enter_initials(t, pos);
        save_write();
        header(t ? "BEST RANKING  HOME" : "BEST RANKING  ARCADE");
        draw_table(t, pos);
        wait_button(60 * 5);
    }
}
