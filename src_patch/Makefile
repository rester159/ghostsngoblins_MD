# Builds the code blob patched into the ROM at $380000 (see tools/patch_gng.py).
CC      = m68k-elf-gcc
OBJCOPY = m68k-elf-objcopy
NM      = m68k-elf-nm
CFLAGS  = -m68000 -O2 -ffreestanding -fno-builtin -nostdlib -fomit-frame-pointer \
          -fno-pic -Wall -Wno-unused-function -I.
LIBGCC  = $(shell $(CC) -m68000 -print-libgcc-file-name)
OBJS    = build/glue.o build/common.o build/pad.o build/boot.o build/title.o build/sram.o build/settings.o build/hiscore.o build/p2.o build/firebrand.o build/swap.o build/pace.o build/intro.o build/shots.o build/dragon.o build/dragon_glue.o build/arthur.o build/satan.o build/arcrand.o build/stageend.o build/mapwin.o

$(shell mkdir -p build)

all: build/patch.bin build/intro.bin build/patch.sym inplace/obj_type.bin inplace/obj_sum.bin

inplace/%.bin: inplace/%.s
	$(CC) -m68000 -c $< -o build/$*.o && $(OBJCOPY) -O binary build/$*.o $@

build/font.inc: mkfont.py ../rom/gg1.bin
	python3 -I mkfont.py ../rom/gg1.bin $@

build/common.o: build/font.inc
build/intro.o: build/intro.inc

# The SEGA/CAPCOM logos come from intro kits outside this repo (SEGA_KIT,
# CAPCOM_KIT); without them the stub skips the intros.
build/intro.inc: mkintro.py
	python3 -I mkintro.py $@
build/title.o: build/jp.inc

build/swap.s: mkswap.py p2.c
	python3 -I mkswap.py p2.c $@

build/swap.o: build/swap.s
	$(CC) -m68000 -c $< -o $@

build/jp.inc: mkjp.py ../rom/gg1.bin
	python3 -I mkjp.py ../rom/gg1.bin $@
build/%.o: %.c md.h common.h
	$(CC) $(CFLAGS) -c $< -o $@
build/%.o: %.s
	$(CC) -m68000 -c $< -o $@

build/patch.elf: $(OBJS) link.ld
	$(CC) $(CFLAGS) -T link.ld -Wl,-Map=build/patch.map $(OBJS) $(LIBGCC) -o $@

build/patch.bin: build/patch.elf
	$(OBJCOPY) -O binary -j .text $< $@

build/intro.bin: build/patch.elf
	$(OBJCOPY) -O binary -j .intro $< $@

build/patch.sym: build/patch.elf
	$(NM) $< | sort > $@

clean:
	rm -rf build/*
