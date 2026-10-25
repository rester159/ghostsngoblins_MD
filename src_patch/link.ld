/* New code lives in the padding above the original 3.3 MiB image. */
MEMORY {
    intro (r) : ORIGIN = 0x350000, LENGTH = 0x30000  /* intro.c data, build/intro.bin */
    rom (rx) : ORIGIN = 0x380000, LENGTH = 0x20000   /* below the art banks at $3A0000 */
    ram (rw) : ORIGIN = 0xFF5100, LENGTH = 0x0E00   /* unused by the game; $FF5F00 = SRAM routine */
}
SECTIONS {
    .text : { KEEP(*(.text.hooks)) *(.text*) *(.rodata*) } > rom
    .intro : { KEEP(*(SORT_BY_ALIGNMENT(.intro*))) } > intro
    .bss (NOLOAD) : { *(.bss*) *(COMMON) } > ram
    /DISCARD/ : { *(.data*) *(.comment) *(.eh_frame*) }
}
