"""Make a measurement copy of a ROM that timestamps every stage-1 game update.
Not for release.

  $5CE (after the loop's VBlank wait; `cmpi.w #2,$FFC570`, its flags feed the
  next beq): a probe stores the VDP V counter and the frame counter at $FF2BF8,
  then repeats the cmpi.
  $5B6 (`jsr $1142CE`, reached right after every update): a probe appends
  (start V, start frame, end V, end frame) to a ring at $FF2C00 (64 entries,
  index at $FF2BF0), counts updates at $FF2BF4 (long), then calls $1142CE.
All of it sits in the RAM gap the game never uses ($FF2BE1-$FF6FFF).

usage: probe_rom.py <rom> <out>
Read it with update_times.py / update_rate.py.
"""
import struct
import sys

PROBE = 0x3F0F00            # free padding (the fix stubs use $3F0000-$3F00FF)
rom = bytearray(open(sys.argv[1], 'rb').read())
# the plain loop, or the features build's (tick moved after the wait: $5B6 nops,
# $5CE `jsr tick_s1; nop`)
REORDERED = rom[0x5B6:0x5BC] == bytes.fromhex('4e714e714e71')
if REORDERED:
    assert rom[0x5CE:0x5D0] == b'\x4e\xb9' and rom[0x5D4:0x5D6] == b'\x4e\x71', 'unexpected loop body'
    tick_s1 = struct.unpack('>I', rom[0x5D0:0x5D4])[0]
else:
    assert rom[0x5B6:0x5BC] == bytes.fromhex('4eb9001142ce'), 'not the expected loop start'
    assert rom[0x5CE:0x5D6] == bytes.fromhex('0c79000200ffc570'), 'not the expected loop body'
assert all(b == 0xFF for b in rom[PROBE:PROBE + 0x80]), 'probe area in use'
end = bytes.fromhex(
    '48e78080'              # movem.l d0/a0,-(sp)
    '41f900ff2c00'          # lea $FF2C00,a0
    '303900ff2bf0'          # move.w $FF2BF0,d0
    '024001f8'              # andi.w #$1F8,d0             64 entries of 8 bytes
    '21b900ff2bf80000'      # move.l $FF2BF8,0(a0,d0.w)   start V, start frame
    '31b900c000080004'      # move.w $C00008,4(a0,d0.w)   end H/V
    '31b900ff7dfe0006'      # move.w $FF7DFE,6(a0,d0.w)   end frame (low word)
    '5040'                  # addq.w #8,d0
    '33c000ff2bf0'          # move.w d0,$FF2BF0
    '52b900ff2bf4'          # addq.l #1,$FF2BF4           updates so far
    '4cdf0101')             # movem.l (sp)+,d0/a0
end += bytes.fromhex('4e75') if REORDERED else bytes.fromhex('4ef9001142ce')   # rts / jmp $1142CE
start = bytes.fromhex(
    '33f900c0000800ff2bf8'  # move.w $C00008,$FF2BF8      start H/V
    '33f900ff7dfe00ff2bfa'  # move.w $FF7DFE,$FF2BFA      start frame
    )
start += (b'\x4e\xf9' + struct.pack('>I', tick_s1)) if REORDERED else \
    bytes.fromhex('0c79000200ffc570' '4e75')    # jmp tick_s1 / cmpi.w #2,$FFC570; rts
assert len(end) <= 0x60
rom[PROBE:PROBE + len(end)] = end
rom[PROBE + 0x60:PROBE + 0x60 + len(start)] = start
rom[0x5B6:0x5BC] = b'\x4e\xb9' + struct.pack('>I', PROBE)
rom[0x5CE:0x5D6] = b'\x4e\xb9' + struct.pack('>I', PROBE + 0x60) + b'\x4e\x71'
# every DMA through the game's helper ($704BE: d0 = bytes, d1 = VRAM address):
# (V counter, bytes, VRAM address, frame) appended to a ring at $FF3000
# (256 entries, index at $FF2BEC). The helper starts `tst.w d0; beq`.
DMA = PROBE + 0x80
assert rom[0x704BE:0x704C4] == bytes.fromhex('4a40670000f4'), 'unexpected DMA helper'
assert all(b == 0xFF for b in rom[DMA:DMA + 0x50]), 'probe area in use'
dma = bytes.fromhex(
    '48e780c0'              # movem.l d0/a0-a1,-(sp)
    '43f900ff3000'          # lea $FF3000,a1
    '303900ff2bec'          # move.w $FF2BEC,d0
    '024007f8'              # andi.w #$7F8,d0
    '33b900c000080000'      # move.w $C00008,0(a1,d0.w)   V counter
    '33af00020002'          # move.w 2(sp),2(a1,d0.w)     bytes (saved d0, low word)
    '33810004'              # move.w d1,4(a1,d0.w)        VRAM address
    '33b900ff7dfe0006'      # move.w $FF7DFE,6(a1,d0.w)   frame
    '5040'                  # addq.w #8,d0
    '33c000ff2bec'          # move.w d0,$FF2BEC
    '4cdf0301'              # movem.l (sp)+,d0/a0-a1
    '4a40'                  # tst.w d0 (the instruction replaced)
    '6706'                  # beq.s +6
    '4ef9000704c4'          # jmp $704C4
    '4ef9000705b6')         # jmp $705B6 (what its beq did)
rom[DMA:DMA + len(dma)] = dma
rom[0x704BE:0x704C4] = b'\x4e\xf9' + struct.pack('>I', DMA)
open(sys.argv[2], 'wb').write(rom)
print('probes at %X and %X' % (PROBE, PROBE + 0x60))
