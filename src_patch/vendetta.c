/* Firebrand's Vendetta (Home): Firebrand's Quest backwards (docs/FIREBRAND_VENDETTA.md).
 *
 * Every Firebrand rule applies (fb_on() is true here too). What differs:
 *  - the stages run 6, 5, 4, 3, 2, 1 (a game starts on stage 6; a practice
 *    launch starts on the stage it picks);
 *  - a stage starts at its far end, beside the boss arena, facing left
 *    (vd_starts, used for checkpoint 0 by the game's restart-entry lookup,
 *    vendetta_glue.s vd_start_entry), and ends where Arthur's run starts:
 *    standing back at the stage's own start (the game's table, $1040CC);
 *  - the camera keeps more of the way ahead on screen, leads down while he
 *    drops, and climbs while he clings or hovers (vendetta_glue.s, hud.s);
 *  - each life has two minutes more than the game's stage time;
 *  - the checkpoint is passed with the camera left of the game's mark
 *    ($103E1A) instead of right of it (vd_cp_cmp); a death after it
 *    restarts at the game's checkpoint, facing left. */
#include "md.h"
#include "common.h"

void stage_jump(int stage);             /* glue.s */
int  fb_lifting(void);                  /* firebrand.c */
void vd_boss(int left);                 /* vd_arthur.c */
void vd_boss_reset(void);
int  vd_boss_on(void);
void sound_stop(void);                  /* glue.s */
void game_sound_tick(void);
void game_sound_play(int id);
void game_over(void);                   /* hiscore.c */
void warm_restart_sp(void);             /* glue.s */
void stage_jump(int stage);             /* glue.s: the game's own stage (re)start, no return */

#define STAGE       RAM8(0xFFC512)
#define IN_PLAY     RAM8(0xFFC305)      /* 0 while a stage (re)starts */
#define HIT         RAM8(0xFFC342)
#define DYING       RAM16(0xFFC570)
#define JUMP_PHASE  RAM16(0xFF9410)
#define FACING      RAM16(0xFF920A)     /* 0 right, $800 left */
#define POS_X       ((u16)(RAM32(0xFF9000) >> 8))   /* x is 16.8 */
#define POS_Y       RAM16(0xFF9004)
#define START_TAB   ((const u8 *)0x1040CCUL)
#define TIME        RAM16(0xFFCD62)     /* seconds left on the stage */
#define EXTRA_TIME  120                 /* the danger is the monsters, not the clock */

/* the game's restart-entry format: y >> 8 in bits 15-5 and x >> 8 in bits 4-0
 * of the first word, then x & $FF and y & $FF */
#define E(x, y) { (u8)((((y) >> 8 << 5) | ((x) >> 8)) >> 8), (u8)(((y) >> 8 << 5) | ((x) >> 8)), \
                  (u8)(x), (u8)(y) }

/* stage index 0-6: where each stage starts, at its far end (the final room's
 * entry is the game's: Vendetta never goes there) */
const u8 vd_starts[7][4] = {
    E(3150, 64),
    E(6880, 112),
    E(3300, 576),
    E(6200, 576),
    E(6900, 1392),                      /* two floors under Satan's (he stays asleep), by the ladder down */
    E(7600, 2432),                      /* the same under the two Satans' */
    E(8024, 2624),
};

/* the opening (stage 6's top room, one Satan): the game's start there, and
 * the regicide done (vendetta_glue.s vd_satan_gone; until then a death
 * restarts in his room) */
const u8 vd_satan_start[4] = E(7560, 2624);
u8 vd_satan_done;
u8 vd_regicide_due;                     /* Satan has died: his page is due (vd_satan_gone) */
u8 vd_regicide_rs;                      /* the restart after that page: in his room */
static u8 regicide_t;
#define REGICIDE_WAIT 90                /* frames of his death before the page */
static void regicide(void);

/* a new game (settings.c player_init) */
void vd_new_game(void)
{
    vd_satan_done = 0;
    vd_regicide_due = 0;
    vd_regicide_rs = 0;
    regicide_t = 0;
}

/* Stage 6 has two Satans; Vendetta has one, the nearer. The other is freed
 * while asleep (it never raised the boss count). After the regicide both
 * stay away. Enemy slots: $FFB800, 40 x 48 (+4 live, +7 state, +10 type,
 * +17 x). */
static void one_satan(void)
{
    volatile u8 *keep = 0;
    for (int k = 0; k < 40; k++) {
        volatile u8 *p = (volatile u8 *)(0xFFB800 + 48 * k);
        if (!p[4] || p[10] != 6) continue;
        /* x at +17 is at an odd address: read it a byte at a time */
        if (!vd_satan_done && (!keep || (p[17] << 8 | p[18]) < (keep[17] << 8 | keep[18]))) {
            if (keep && !keep[7]) keep[4] = 0;
            keep = p;
        } else if (!p[7]) {
            p[4] = 0;
        }
    }
}

/* No double bosses: the Big Men (type 10) come in pairs in stages 4 and 5
 * (a pair flanks the drop on stage 5's way down); Vendetta keeps one of
 * those near the screen, the first found, and frees the others there.
 * Enemy slots as one_satan's (+17 x, read a byte at a time). */
static void one_bigman(void)
{
    u16 cx = RAM16(0xFF9100);
    int kept = 0;
    for (int k = 0; k < 40; k++) {
        volatile u8 *p = (volatile u8 *)(0xFFB800 + 48 * k);
        u16 x;
        if (!p[4] || p[10] != 10) continue;
        x = p[17] << 8 | p[18];
        if ((u16)(x - cx + 96) > 256 + 192) continue;      /* not near the screen */
        if (kept++) p[4] = 0;
    }
}

#define VD_XREST    176                 /* his place on screen (vendetta_glue.s XBIAS) */
#define VD_YREST    142                 /* the game's */
#define LEAD_MAX    48
#define CAM_LIMITS  ((const u16 *)0x1043E6UL)   /* per stage: x min, x max, y max, y min */

static u8 was_in_play;
static u16 fight_time;                  /* the stage time when Arthur came */
static u16 takeoff_y;                   /* his y when he last left the ground */
u16 vd_lead;                            /* the camera's lead below him (vendetta_glue.s vd_cam_ygap) */
u8  vd_climb;                           /* the camera climbs with him in the air (hud.s cam_air) */

int vd_on(void)
{
    return is_home() && PERSIST->home_sub == HOME_VENDETTA;
}

/* a game's first stage (settings.c player_init) */
int vd_first_stage(void)
{
    return 6;
}

static u16 start_w(int s) { return START_TAB[4 * s] << 8 | START_TAB[4 * s + 1]; }
static u16 start_x(int s) { return (start_w(s) & 0x1F) << 8 | START_TAB[4 * s + 2]; }
static u16 start_y(int s) { return start_w(s) >> 5 << 8 | START_TAB[4 * s + 3]; }

/* the camera object ($FFF420) and the camera put on him, inside the stage's
 * limits (vendetta_glue.s vd_cam_init, vd_cam_s6) */
void vd_cam_place(void)
{
    const u16 *lim = CAM_LIMITS + 4 * STAGE;
    s16 cx = POS_X - VD_XREST, cy = POS_Y - VD_YREST;
    if (cx < (s16)lim[0]) cx = lim[0];
    if (cx > (s16)lim[1]) cx = lim[1];
    if (cy < (s16)lim[3]) cy = lim[3];
    if (cy > (s16)lim[2]) cy = lim[2];
    RAM32(0xFFF428) = (u32)(u16)cx << 8;
    RAM32(0xFFF42C) = (u32)(u16)cy << 8;
    RAM8(0xFFF426) = (cx & 16) ^ 16;    /* the 16 px crossing parities */
    RAM8(0xFFF427) = (cy & 16) ^ 16;
    RAM16(0xFFF43C) = cx;
    RAM16(0xFFF43E) = cy;
    RAM16(0xFFF440) = cx & 511;
    RAM16(0xFFF442) = cy & 511;
    RAM16(0xFF9100) = cx;
    RAM16(0xFF9102) = cy;
}

/* once per frame of play (settings.c play_tick) */
void vd_frame(void)
{
    int s = STAGE;
    if (!vd_on()) return;
    vd_climb = 0;
    if (!IN_PLAY) {
        was_in_play = 0;
        vd_lead = 0;
        vd_boss_reset();
        return;
    }
    /* clinging or hovering, the camera climbs with him: going back the way
     * Arthur came, the stages' drops (stage 3's shaft, stage 2's towers) are
     * climbs, and the screen's top is Firebrand's ceiling */
    vd_climb = fb_lifting();
    /* the camera leads down while he drops below where he left the ground */
    if (!JUMP_PHASE) takeoff_y = POS_Y;
    if (JUMP_PHASE == 2 && POS_Y < takeoff_y - 16) {
        if (vd_lead < LEAD_MAX) vd_lead += 2;
    } else if (vd_lead) {
        vd_lead--;
    }
    if (!was_in_play) {                 /* the first frame of a life: face the way he goes */
        was_in_play = 1;
        vd_regicide_rs = 0;
        RAM8(0xFF9006) = 2;
        FACING = 0x800;
        if (s == 5 && !vd_satan_done) { RAM8(0xFF9006) = 1; FACING = 0; }   /* Satan is to the right */
        TIME += EXTRA_TIME;             /* backwards, Arthur's drops are climbs */
    }
    if (s == 5) one_satan();
    if (vd_regicide_due && !DYING && ++regicide_t >= REGICIDE_WAIT) {
        vd_regicide_due = 0;
        regicide();                     /* no return */
    }
    one_bigman();
    if (s == 0) {                       /* the graveyard: Arthur */
        int on = vd_boss_on();
        vd_boss(RAM16(0xFF9100) <= CAM_LIMITS[0]);
        if (!on && vd_boss_on()) fight_time = TIME;
        if (vd_boss_on()) TIME = fight_time;    /* no clock in the duel */
        return;
    }
    if (HIT || DYING || JUMP_PHASE || s > 5) return;
    if (POS_X <= start_x(s) + 16 && (u16)(POS_Y - start_y(s) + 32) <= 64)
        stage_jump(s - 1);
}

/* Arthur is dead (vd_arthur.c): the ending text, then the high-score entry
 * and the Home menu (as after a game over). No return. */
void vd_ending(void)
{
    static const char *const lines[] = {
        "THE KNIGHT HAS FALLEN.",
        "",
        "THE PACT IS ASHES.",
        "NO KING. NO MASTER.",
        "",
        "THE DEMON REALM BELONGS",
        "TO THE RED ARREMER.",
    };
    u16 n, prev = 0xFF;
    sound_stop();
    screen_init();
    text_center(5, "FIREBRAND'S VENDETTA", PAL_SEL);
    for (n = 0; n < sizeof lines / sizeof lines[0]; n++) text_center(9 + 2 * n, lines[n], PAL_TEXT);
    text_center(25, "THE END", PAL_SEL);
    display_on();
    game_sound_play(26);
    for (n = 0; n < 60 * 20; n++) {
        u16 p;
        vsync();
        game_sound_tick();
        p = pad_read(0);
        if (n > 120 && (p & ~prev & (BTN_A | BTN_B | BTN_C | BTN_START))) break;
        prev = p;
    }
    game_over();
    warm_restart_sp();
}

/* A story page: the title, up to 7 lines, a button (or Start) goes on */
static void story_page(const char *title, const char *const *lines)
{
    u16 prev = 0xFF;
    screen_init();
    text_center(5, "FIREBRAND'S VENDETTA", PAL_DIM);
    text_center(8, title, PAL_SEL);
    for (int i = 0; i < 7; i++) text_center(12 + 2 * i, lines[i], PAL_TEXT);
    text_center(26, "PRESS A BUTTON", PAL_DIM);
    display_on();
    for (u16 n = 0;; n++) {
        u16 p;
        vsync();
        game_sound_tick();
        p = pad_read(0);
        if (n > 20 && (p & ~prev & (BTN_A | BTN_B | BTN_C | BTN_START))) return;
        prev = p;
    }
}

/* The story, before a game of Vendetta (boot.c home_menu): one page, then
 * the game opens on the fight with Satan */
void vd_story(void)
{
    static const char *const lines[7] = {
        "SATAN PAID FOR HIS THRONE",
        "WITH THE RED ARREMERS:",
        "EACH ONE A PRICE GIVEN",
        "TO ARTHUR'S LANCE.",
        "",
        "FIREBRAND HAS COME",
        "FOR THE DEMON KING.",
    };
    story_page("THE PACT", lines);
}

/* After Satan's death (REGICIDE_WAIT frames of it): the realm turns on
 * Firebrand. The page, then the stage starts again through the game's own
 * stage entry ($113B70: the map, then play) in Satan's room, now empty. */
static void regicide(void)
{
    static const char *const lines[7] = {
        "THE DEMON KING IS DEAD.",
        "",
        "NO ONE FORGIVES A KINGSLAYER:",
        "EVERY MONSTER OF THE REALM",
        "NOW HUNTS FIREBRAND.",
        "",
        "ONE NAME IS LEFT: ARTHUR.",
    };
    story_page("THE VENDETTA", lines);
    vd_regicide_rs = 1;
    stage_jump(5);
}
