/* Minimal Mega Drive helpers for code patched into the GnG binary. */
#ifndef MD_H
#define MD_H
typedef unsigned char  u8;
typedef unsigned short u16;
typedef unsigned long  u32;
typedef signed short   s16;

#define VDP_DATA   (*(volatile u16 *)0xC00000)
#define VDP_DATAL  (*(volatile u32 *)0xC00000)
#define VDP_CTRL   (*(volatile u16 *)0xC00004)
#define VDP_CTRLL  (*(volatile u32 *)0xC00004)
#define VRAM_W(a)  (0x40000000UL | (((u32)(a) & 0x3FFF) << 16) | ((u32)(a) >> 14))
#define VRAM_R(a)  ((((u32)(a) & 0x3FFF) << 16) | ((u32)(a) >> 14))
#define CRAM_W(a)  (0xC0000000UL | ((u32)(a) << 16))
#define VSRAM_W(a) (0x40000010UL | ((u32)(a) << 16))

#define RAM8(a)  (*(volatile u8  *)(a))
#define RAM16(a) (*(volatile u16 *)(a))
#define RAM32(a) (*(volatile u32 *)(a))

/* game RAM used by the hooks */
#define G_SYS     RAM8(0xFF7000)   /* arcade system inputs, active low; bit0 = start */
#define G_P1      RAM8(0xFF7001)   /* arcade player inputs, active low */
#define G_RAW1    RAM8(0xFF7080)
#define G_RAW2    RAM8(0xFF7081)
#define G_PADOK   RAM8(0xFF7082)
#define G_FRAMES  RAM32(0xFF7084)
#define G_CREDITS RAM8(0xFF7FE8)
#define G_COINLAT RAM8(0xFF7FE9)
#define G_STATE   RAM32(0xFF7FF0)  /* 'TITL', 'LIVE', 'INTR', ... */
#define G_ATTRACT RAM16(0xFF7FFC)

/* pad bits returned by pad_read(): 1 = pressed */
#define BTN_UP    0x01
#define BTN_DOWN  0x02
#define BTN_LEFT  0x04
#define BTN_RIGHT 0x08
#define BTN_B     0x10
#define BTN_C     0x20
#define BTN_A     0x40
#define BTN_START 0x80

static inline void vdp_reg(int r, int v) { VDP_CTRL = 0x8000 | (r << 8) | (v & 0xFF); }
static inline void nop(void) { __asm__ volatile ("nop"); }
/* block interrupts (level 7 mask), returning the old status register */
static inline u16 irq_off(void)
{
    u16 sr;
    __asm__ volatile ("move.w %%sr,%0\n\tori.w #0x0700,%%sr" : "=d"(sr) : : "memory");
    return sr;
}
static inline void irq_restore(u16 sr) { __asm__ volatile ("move.w %0,%%sr" : : "d"(sr) : "memory"); }

void vsync(void);
u16  pad_read(int port);
void game_sound_tick(void);
void game_sound_play(int id);
void game_sound_init(void);
#endif
