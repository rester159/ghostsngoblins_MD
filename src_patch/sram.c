/* Battery save: Arcade DIP switches, Home options, title language and both
 * high-score tables. The ROM is larger than 2 MiB, so SRAM shares the $200000
 * window with ROM; sram_xfer (glue.s) runs from work RAM with interrupts off
 * while it is mapped. */
#include "md.h"
#include "common.h"

void sram_xfer(u8 *buf, int len, int write);

#define SAVE_MAGIC 0x474E4753UL     /* 'GNGS' */
#define SAVE_VER   2

typedef struct {
    u32 magic;
    u8  ver;
    u8  title_jp;
    u8  dip[8];
    u8  home[8];
    HiScore hs[2][10];
    u16 sum;
} Save;

static Save save;

static u16 save_sum(const Save *s)
{
    const u8 *b = (const u8 *)s;
    u16 sum = 0x5A5A;
    int i;
    for (i = 0; i < (int)sizeof(Save) - 2; i++) sum = (u16)((sum << 1 | sum >> 15) + b[i]);
    return sum;
}

void save_load(void)
{
    Persist *p = PERSIST;
    int i;
    sram_xfer((u8 *)&save, sizeof(save), 0);
    if (save.magic != SAVE_MAGIC || save.ver != SAVE_VER || save.sum != save_sum(&save))
        return;                     /* blank, old or foreign SRAM: keep defaults */
    p->title_jp = save.title_jp & 1;
    for (i = 0; i < DIP_N; i++)
        if (save.dip[i] < dip_count(i)) p->dip[i] = save.dip[i];
    for (i = 0; i < HOP_N; i++)
        if (save.home[i] < home_count(i)) p->home[i] = save.home[i];
    for (i = 0; i < 20; i++) p->hs[i / 10][i % 10] = save.hs[i / 10][i % 10];
}

void save_write(void)
{
    Persist *p = PERSIST;
    int i;
    save.magic = SAVE_MAGIC;
    save.ver = SAVE_VER;
    save.title_jp = p->title_jp;
    for (i = 0; i < 8; i++) { save.dip[i] = p->dip[i]; save.home[i] = p->home[i]; }
    for (i = 0; i < 20; i++) save.hs[i / 10][i % 10] = p->hs[i / 10][i % 10];
    save.sum = save_sum(&save);
    sram_xfer((u8 *)&save, sizeof(save), 1);
}
