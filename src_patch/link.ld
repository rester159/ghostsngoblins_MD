/* New code lives in the padding above the original 3.3 MiB image. */
MEMORY {
    rom (rx) : ORIGIN = 0x380000, LENGTH = 0x60000
    ram (rw) : ORIGIN = 0xFF5100, LENGTH = 0x0E00   /* unused by the game; $FF5F00 = SRAM routine */
}
SECTIONS {
    .text : { KEEP(*(.text.hooks)) *(.text*) *(.rodata*) } > rom
    .bss (NOLOAD) : { *(.bss*) *(COMMON) } > ram
    /DISCARD/ : { *(.data*) *(.comment) *(.eh_frame*) }
}
