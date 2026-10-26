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

/* The arcade's input timing (gg3): its player routines read left/right as
 * (this frame AND last frame) ($93D0, inputs $4B/$4C from $6920/$6930), so a
 * press counts from its second frame; and a jump press on the ground only
 * starts the jump two frames later ($9218 latches it at the end of the press
 * frame, $9542 sets it up the next frame without moving, $95C8 moves from the
 * one after), along the walk direction latched on the press frame ($9567
 * reads $050E). The port reacted on the press frame. arcade_input() turns the
 * raw input byte (arcade format, active low) into what the port's player code
 * should see so it behaves the same: left/right held two frames, and for a
 * jump: the press frame as a walk frame, then a frame with no stick, then the
 * jump with the latched direction. Up/down already use the two-frame rule in
 * the port ($7D4C). */
u8 arcade_input(u8 raw, InFilter *f, int on_ground)
{
    u8 in = ~raw;                       /* active high */
    u8 lr = in & 3, held = lr & f->prev_lr;
    u8 jump = in & 0x20, out;
    f->prev_lr = lr;
    out = (in & 0xFC) | held;           /* fire, jump, up/down as they are */
    if (f->wind == 1) {                 /* the frame between: stand still */
        out &= ~(0x0F | 0x20);
        f->wind = 2;
    } else if (f->wind == 2) {          /* take off */
        out = (out & ~0x2F) | f->dir | 0x20;
        f->wind = 0;
    } else if (jump && !f->prev_jump && on_ground) {
        f->dir = held;                  /* the walk direction now */
        f->wind = 1;
        out &= ~0x20;                   /* this frame is still a walk frame */
    }
    f->prev_jump = jump;
    /* the press frame and the frame between keep him on his floor (arthur.s
       ground_snap): the arcade's jump set-up ($9218/$9542) has no floor check */
    RAM8(0xFF9455) = (RAM8(0xFF9455) & ~4) | (f->wind ? 4 : 0);
    return ~out;
}

static InFilter p1f;

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

extern u8 pad_latch_on, pad_lat[4];      /* hud.s: presses on frames between updates */

void pad_update(void)
{
    volatile u8 *d = (volatile u8 *)0xA10003;
    u8 t1, t0, p1, sys, act4, act5, coin, start;
    u16 sr = irq_off();
    int mode = PERSIST->magic == PERSIST_MAGIC ? PERSIST->mode : MODE_NONE;

    *d = 0x40; nop(); nop(); nop(); nop();
    t1 = *d;
    *d = 0x00; nop(); nop(); nop(); nop();
    t0 = *d;
    *d = 0x40;
    if (pad_latch_on) {                 /* B/C, A pressed on a frame since the last update */
        t1 &= pad_lat[0];
        t0 &= pad_lat[1];
    }
    pad_lat[0] = pad_lat[1] = 0xFF;
    pad_latch_on = in_play();
    irq_restore(sr);
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
    G_P1 = in_play() ? arcade_input(p1, &p1f, RAM16(0xFF9408) == 1) : p1;

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

/* $5A8: `jsr stage_hold` (glue.s) before play starts, at every stage start
 * (game start, after a death's map, after a stage clear). The arcade draws
 * the stage over the map for ~37 frames with the game held ($726E calling
 * $80A0) before play; Genesis draws it at once, so from the end of the map
 * to Arthur's first step took 15 frames in the port and 41 in the arcade.
 * Hold the difference: the display is on, the music keeps playing, and the
 * frame counter keeps counting (interrupts are still off here; the VBlank
 * handler only counts) so the random source runs on as the arcade's does. */
#define STAGE_HOLD 26
void ter_fill(void);
void stage_hold(void)
{
    int i;
    for (i = 0; i < STAGE_HOLD; i++) {
        while (VDP_CTRL & 8) ;
        while (!(VDP_CTRL & 8)) ;
        RAM32(0xFF7DFC)++;
        game_sound_tick();
        if (i == 0)
            ter_fill();     /* the stage draw's terrain (terrain.c), well inside this frame */
    }
}
