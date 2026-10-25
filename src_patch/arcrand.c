/* The arcade's second random source: the 16-bit shift register at $68F9.
 *
 *     LDB <$6F / EORB <$6E / COMB / ASLB / ASLB    carry = bit 6 of ~($6E ^ $6F)
 *     ROL <$6F / ROL <$6E                          state = state << 1 | carry
 *     LDB <$6F / STB <$70 / RTS                    returns (and keeps) the low byte
 *
 * i.e. state' = state << 1 | (1 ^ bit14 ^ bit6) (an XNOR feedback), returned
 * in B with A untouched. It is advanced only by its callers (34 call sites,
 * all in enemy code; see docs/ACCURACY.md), never by the frame interrupt.
 * The arcade seeds it with $87CD at power-on ($6872) and whenever its top
 * level starts over ($69EB, state $05 = 0: the start of each attract cycle,
 * a coin, the return after a game over), so every game starts from $87CD:
 * nothing calls it between the coin and the first enemy that does.
 *
 * The port already has the state, in the same place relative to its copy of
 * the arcade's direct page: $FFC62C = $6E:$6F, $FFC62E = $70 (six copies of
 * the routine work on it through enemy contexts: $218A, $4A28, $ABB4,
 * $70B78, $105472, $11B8DE). It reloaded $87CD at every stage and life start
 * (the ten stage inits, e.g. $1109DE); the patcher removes those, and
 * arc_rand_seed() seeds it at boot (glue.s hook_ramclear) and at game start
 * (player_init), as the arcade does. */
#include "md.h"

#define RSTATE RAM16(0xFFC62C)
#define RLAST  RAM8(0xFFC62E)

u8 arc_rand(void)
{
    u16 s = RSTATE;
    u8 b = ~(u8)((s >> 8) ^ s);
    s = (u16)(s << 1) | ((b >> 6) & 1);
    RSTATE = s;
    RLAST = (u8)s;
    return (u8)s;
}

void arc_rand_seed(void)
{
    RSTATE = 0x87CD;
    RLAST = 0;
}
