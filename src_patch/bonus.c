/* A bonus life earned outside play waits for play, as the arcade's.
 *
 * The arcade checks for a bonus life in play only: $ED96 (from the play loop,
 * $E962) runs on the frames with <$21 & 7 = 0 while Arthur isn't dead (<$90 =
 * 0) and below 1,000,000 points, and gives at most one life a check
 * ($EDEA-$EDF1). The ending's 50,000 points ($0C15, after the second clear)
 * are added in the stage-end mode, so their life comes in stage 1, on its first
 * play frame with <$21 & 7 = 0 (measured: the score on the CONGRATULATION
 * frame; mode 1 from the opening's end, play (<$0B = 1) 39 frames later, the
 * life on the next frame, c21 $10, Arthur's first step the frame after; a
 * second threshold crossed by the same points comes 8 frames later). The port
 * added the life with the points, at once, and one at most.
 *
 * score_added (settings.c) only sets bonus_pending; bonus_tick, from rng_tick
 * (glue.s: once a play update, $FFA206 = the arcade's <$21) while
 * bonus_pending is set, makes the arcade's check. Points scored in play wait
 * for it too, as the arcade's (a score poked to 20,000 at <$21 = $70: the
 * life at $78; two thresholds crossed at once: two lives 8 frames apart). */
#include "md.h"
#include "common.h"

u8 bonus_pending;

void bonus_tick(void)
{
    if (RAM8(0xFFA206) & 7) return;         /* <$21 & 7 */
    if (RAM16(0xFFC570)) return;            /* <$90: Arthur dying or dead */
    if (!bonus_give()) bonus_pending = 0;   /* one life a check, until none is due */
}
