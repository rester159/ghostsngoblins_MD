/* Replacement for the game's pad routine at $BF72. Produces the same RAM
 * outputs ($FF7000 system, $FF7001 player, raw bytes, credits) and adds the
 * per-mode mapping:
 *   original / no mode : B, C act; A inserts a coin; Start starts (as shipped)
 *   ARCADE             : B, A act (A takes C's old role); C inserts a coin
 *   HOME               : B, C act (A = C); Start pauses during play
 */
#include "md.h"
#include "common.h"

/* $C052: direction bits reordered for the arcade input byte */
static const u8 dir_lut[16] = {
    0x00, 0x08, 0x04, 0x0C, 0x02, 0x0A, 0x06, 0x0E,
    0x01, 0x09, 0x05, 0x0D, 0x03, 0x0B, 0x07, 0x0F,
};

void coin_inserted(void);
void play_tick(void);

static u8 prev_start;

/* Playing (not attract, not the continue countdown at $FFC570 = 2). */
static int in_play(void)
{
    return G_STATE == 0x4C495645UL /* 'LIVE' */ && G_ATTRACT == 0
        && RAM16(0xFFC570) != 2;
}

static void pause_loop(void)
{
    u16 p, prev = BTN_START;
    for (;;) {
        vsync();
        game_sound_tick();
        p = pad_read(0);
        if ((p & BTN_START) && !(prev & BTN_START)) break;
        prev = p;
    }
    prev_start = 1;
}

void pad_update(void)
{
    volatile u8 *d = (volatile u8 *)0xA10003;
    u8 t1, t0, p1, sys, act4, act5, coin, start;
    int mode = PERSIST->magic == PERSIST_MAGIC ? PERSIST->mode : MODE_NONE;

    *d = 0x40; nop(); nop(); nop(); nop();
    t1 = *d;
    *d = 0x00; nop(); nop(); nop(); nop();
    t0 = *d;
    *d = 0x40;
    G_RAW1 = t1;
    G_RAW2 = t0;
    G_FRAMES++;
    if (t0 & 0x0C) return;          /* no pad: leave inputs as they were */
    G_PADOK = 1;

    {
        u8 b = !(t1 & 0x10), c = !(t1 & 0x20), a = !(t0 & 0x10);
        start = !(t0 & 0x20);
        if (mode == MODE_ARCADE) { act4 = b; act5 = a; coin = c; }
        else if (mode == MODE_HOME) { act4 = b; act5 = c | a; coin = 0; }
        else { act4 = b; act5 = c; coin = a; }
    }

    if (mode == MODE_HOME && in_play()) {
        if (start && !prev_start) { prev_start = 1; pause_loop(); }
        prev_start = start;
        start = 0;                  /* Start is pause, not the arcade start */
    } else {
        prev_start = start;
    }

    p1 = 0xC0 | dir_lut[t1 & 15];
    if (!act4) p1 |= 0x10;
    if (!act5) p1 |= 0x20;
    G_P1 = p1;

    sys = 0xFF;
    if (coin)  sys &= ~0x40;
    if (start) sys &= ~0x01;
    G_SYS = sys;

    if (coin) {
        if (!G_COINLAT) {
            G_COINLAT = 1;
            coin_inserted();
        }
    } else {
        G_COINLAT = 0;
    }
    if (mode == MODE_ARCADE && PERSIST->dip[DIP_COIN] == 5) G_CREDITS = 9;   /* free play */
    if (in_play()) play_tick();
}
