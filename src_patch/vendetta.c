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
 *  - each life has a minute more than the game's stage time;
 *  - the checkpoint is passed with the camera left of the game's mark
 *    ($103E1A) instead of right of it (vd_cp_cmp); a death after it
 *    restarts at the game's checkpoint, facing left. */
#include "md.h"
#include "common.h"

void stage_jump(int stage);             /* glue.s */
int  fb_lifting(void);                  /* firebrand.c */

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
#define EXTRA_TIME  60

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

#define VD_XREST    176                 /* his place on screen (vendetta_glue.s XBIAS) */
#define VD_YREST    142                 /* the game's */
#define LEAD_MAX    48
#define CAM_LIMITS  ((const u16 *)0x1043E6UL)   /* per stage: x min, x max, y max, y min */

static u8 was_in_play;
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
        RAM8(0xFF9006) = 2;
        FACING = 0x800;
        TIME += EXTRA_TIME;             /* backwards, Arthur's drops are climbs */
    }
    if (HIT || DYING || JUMP_PHASE || s == 0 || s > 5) return;
    if (POS_X <= start_x(s) + 16 && (u16)(POS_Y - start_y(s) + 32) <= 64)
        stage_jump(s - 1);
}
