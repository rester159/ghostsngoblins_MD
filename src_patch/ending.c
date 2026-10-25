/* The end of the final room, as the arcade's (docs/ACCURACY.md).
 *
 * Arcade: Astaroth's removal ($DDA3 -> $E844, stage index 6: no sound, no
 * points) switches the top level to its stage-end mode (<$08 = 2), and from
 * the next frame that mode runs the ending ($736D by <$7F, the clear count):
 *  - first clear (<$7F = 0, $73FE): the room is cleared to black ($F788),
 *    only Arthur is drawn, "THIS ROOM IS AN ILLUSION ..." ($022C) for 300
 *    frames; then <$7F = 1 and the game goes back to stage 1;
 *  - second clear (<$7F = 1, $7EDC): the princess scene. Arthur's target is
 *    his x + (princess x - his x, low byte) / 3 ($7F21, $FED8); from the frame
 *    after he walks 1.125 px/frame until he reaches it ($7F45, $9477 with
 *    $9553); the princess (the object at $15C2, x 8179 in the room) walks
 *    1.125 px/frame towards him ($7FDC) until she is within 16 px of his
 *    target; then they embrace ($7C86) and four hearts rise above Arthur, one
 *    on each frame with <$21 & 15 = 0 ($7F61, $7F95: fg tile $60, attribute 5,
 *    one row up each time); then <$7F = 2 ($7FB5) and the next frame
 *    "CONGRATULATION" ($022D) with 50,000 points ($0C15), 540 frames; ...
 * The port instead waited 240 frames after the removal with the game running
 * (Arthur could walk about), gave 1,000 points and played sound $3F (its
 * stage-end block at $10EA5A), drew the first clear's text over the room and
 * had no princess scene.
 *
 * The port's art has no standing, walking or embracing princess (only the
 * seated one of the opening), so here the princess is not drawn: her walk is
 * kept invisibly, so Arthur's walk, the hearts and the text come on the
 * arcade's frames. The hearts are the port's text layer's character $60.
 */
#include "md.h"

#define LOOPED   RAM8(0xFF7FC0)         /* the arcade's <$7F: 1 after the first clear */
#define TEXT_ON  RAM8(0xFF7FC2)         /* the port's ending text running */
#define TEXT_PH  RAM8(0xFF7FC3)
#define FONT_LD  RAM8(0xFF7FC6)
#define TBUF     ((volatile u8 *)0xFFD000)  /* 32 x 32 text buffer, rows 9-20 shown as rows 7-18 */
#define ART_X    RAM32(0xFF9000)
#define ART_FR   RAM16(0xFF9206)
#define ART_FRT  RAM16(0xFF9208)
#define ART_DIR  RAM16(0xFF920A)
#define C21      RAM8(0xFFA206)

static u8 phase;                        /* 0 idle, 1 princess scene, 2 its text is on */
static u8 t, astate, hearts, hrow, hcol, prin_walk;
static u16 target;
static u32 px;                          /* the princess's x, 16.8 */

void end_reset(void) { phase = 0; }
void end_black(void);                   /* astaroth_glue.s: planes B and A (rows 3-24) cleared */

/* Hide every enemy and enemy shot (the arcade's stage-end mode draws only
 * Arthur and, in the final room, the princess). */
static void hide_objects(void)
{
    int i;
    for (i = 0; i < 40; i++) RAM8(0xFFB800 + 48 * i + 4) = 0;
    for (i = 0; i < 6; i++) RAM8(0xFFC100 + 48 * i + 4) = 0;
}

static void put_hearts(int n)
{
    int k;
    for (k = 0; k < n; k++) {
        int row = hrow - k;
        if (row >= 7 && row <= 18) TBUF[(row + 2) * 32 + hcol] = 0x60;
    }
}

/* $11392A (the port's ending starts: its text is set up next). The first
 * clear's text is on black: the room's planes are cleared (B at $C000; A at
 * $E000 holds the throne and the text, the HUD is on the window plane). */
void end_start(void)
{
    hide_objects();
    if (!LOOPED) end_black();
}

/* At the start of the port's ending routine ($113916). Returns 1 while the
 * princess scene runs (the routine is skipped and the game update with it),
 * 0 to go on with the routine. */
int end_frame(int (*trigger)(void))
{
    if (phase == 2) {                   /* the text is on: keep the hearts */
        if (TEXT_ON && TEXT_PH == 0) put_hearts(4);
        return 0;
    }
    if (phase == 0) {
        if (TEXT_ON || !LOOPED || RAM8(0xFFC512) != 6) return 0;
        if (!trigger()) return 0;       /* $10EAA4: the frame after the removal */
        phase = 1; t = 0; astate = 0; hearts = 0; prin_walk = 1;
        px = 8179UL << 8;
        hide_objects();
        TEXT_ON = 1; TEXT_PH = 0;       /* the text layer is uploaded each frame */
        FONT_LD = 1;
        {   int i; for (i = 0; i < 1024; i++) TBUF[i] = ' '; }
    }
    t++;
    switch (astate) {
    case 0:                             /* $7F21 */
        if (t == 2) {
            u16 ax = ART_X >> 8;
            target = ax + (u8)((u8)(8179 - ax) / 3);
            ART_DIR = 0;
            astate = 1;
        }
        break;
    case 1:                             /* $7F45: walk to the target */
        if ((u16)(ART_X >> 8) < target) {
            ART_X += 0x120;
            if (ART_FRT) ART_FRT--;
            else { if (++ART_FR >= 7) ART_FR = 1; ART_FRT = 2; }
        } else ART_FR = 0;
        break;
    case 2:                             /* $7F61 */
        ART_FR = 0;
        hrow = (u8)(0xE0 - (u8)(RAM32(0xFF9400) >> 8)) >> 3;
        hcol = (u8)(ART_X >> 8) >> 3;
        astate = 3;
        break;
    case 3:                             /* $7F95: a heart on each 16th frame */
        if ((C21 & 15) == 0) {
            put_hearts(++hearts);
            if (hearts == 4) astate = 4;
        }
        break;
    case 4:                             /* $7FB5: the text from the next frame */
        astate = 5;
        break;
    default:
        phase = 2;
        TEXT_ON = 0;                    /* the port's routine starts its text now */
        return 0;
    }
    /* the princess ($7FDC, after Arthur in the arcade's frame): from the
     * frame after her set-up, towards Arthur's target */
    if (t >= 2 && prin_walk) {
        if ((u16)(target + 16) < (u16)(px >> 8)) px -= 0x120;
        else {
            prin_walk = 0;
            astate = 2;                 /* Arthur: the embrace, from the next frame */
        }
    }
    return 1;
}
