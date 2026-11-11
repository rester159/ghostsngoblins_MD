#ifndef COMMON_H
#define COMMON_H
#include "md.h"

#define VERSION    "V0.8.4 ALPHA"     /* Mega Ghosts'n Goblins; also tools/patch_gng.py VERSION */
#define FONT_TILE  0x100
#define FONT_VRAM  (FONT_TILE * 32)

enum { PAL_TEXT = 1, PAL_SEL = 2, PAL_DIM = 3 };
enum { MODE_NONE = 0, MODE_ARCADE = 1, MODE_HOME = 2 };
enum { HOME_1P = 0, HOME_COOP = 1, HOME_FIREBRAND = 2, HOME_VENDETTA = 3 };

/* Arcade DIP switches (indices into the option tables in settings.c) */
enum { DIP_COIN, DIP_LIVES, DIP_BONUS, DIP_DIFF, DIP_DEMO, DIP_CONT, DIP_N };
/* Home options */
enum { HOP_LIVES, HOP_CONT, HOP_BONUS, HOP_DIFF, HOP_WEAPON, HOP_N };
#define HOME_WEAPON_LANCE 1         /* HOP_WEAPON: 0 = kept after a death, as the arcade */
#define HOME_CONT_INF 10
#define FB_PLUS_RANK  0x20          /* VERY DIFFICULT's starting rank (settings.c diff_rank) */

typedef struct {        /* 8 bytes */
    char name[3];
    u8   stage;         /* 1-6 */
    u32  score;         /* BCD, as the game keeps it */
} HiScore;

/* Survives the game's RAM clear ($FF5000-$FF50FF; see glue.s).
 * glue.s uses the offsets of `warm` (6) and `title_jp` (8). */
typedef struct {
    u32 magic;          /* 0  */
    u8  mode;           /* 4  */
    u8  home_sub;       /* 5  */
    u8  warm;           /* 6  set by warm_restart */
    u8  dev_unlocked;   /* 7  until a hardware reset */
    u8  title_jp;       /* 8  */
    u8  sound_id;       /* 9  last sound-test id */
    u8  dev_on;         /* 10 practice session (debug launch) */
    u8  dev_stage;      /* 11 1-6 */
    u8  dev_lives;      /* 12 */
    u8  dev_inf;        /* 13 infinite lives */
    u8  coin_count;     /* 14 coins towards the next credit */
    u8  dev_diff;       /* 15 */
    u8  dip[8];         /* 16 */
    u8  home[8];        /* 24 */
    u32 bonus_next;     /* 32 BCD score of the next extra life, 0 = none */
    u8  bonus_step_i;   /* 36 */
    u8  dev_players;    /* 37 developer launch: 0 = 1P, 1 = co-op, 2 = Firebrand, 3 = Plus, 4 = Vendetta */
    u8  fb_unlocked;    /* 38 Firebrand's Quest has been cleared (saved): PLUS in the menu */
    u8  fb_plus;        /* 39 this game is Firebrand's Quest Plus */
    HiScore hs[2][10];  /* 40  [0] arcade, [1] home */
    u8  fly_lv;         /* 200 Firebrand's flight level, 1-FLY_MAX (firebrand.c) */
    u8  fly_given;      /* 201 wings given out in fly_stage */
    u8  fly_stage;      /* 202 the stage fly_given counts for, + 1 (0: none) */
} Persist;              /* 203 bytes */
#define PERSIST       ((Persist *)0xFF5000)
#define PERSIST_MAGIC 0x4D584D50UL   /* 'MXMP' (layout 2) */

void pads_init(void);

typedef struct { u8 prev_lr, prev_jump, wind, dir; } InFilter;
u8 arcade_input(u8 raw, InFilter *f, int on_ground);   /* pad.c */
void screen_init(void);
void draw_logo(int row);
void display_on(void);
void text(int x, int y, const char *s, int pal);
void text_center(int y, const char *s, int pal);
void clear_rows(int y0, int y1);
void num2(char *dst, int v);
void bcd_str(char *dst, u32 bcd);   /* 8 digits, leading zeros blank */

/* settings.c */
void settings_defaults(void);
int  is_home(void);
int  is_arcade(void);
extern const char *const dip_names[DIP_N];
extern const char *const home_names[HOP_N];
int  dip_count(int i);
int  home_count(int i);
const char *dip_value(int i, int v);
const char *home_value(int i, int v);

/* sram.c */
void save_load(void);
void save_write(void);

/* hiscore.c */
int  hiscore_table(void);           /* 0 arcade, 1 home */
void hiscore_show(int table, int wait);

/* bonus.c (with settings.c bonus_give) */
extern u8 bonus_pending;
int  bonus_give(void);
#endif
