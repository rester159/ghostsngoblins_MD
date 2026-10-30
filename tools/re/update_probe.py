"""Real update durations in the stage 3-6 loops (uc_profile.py can't be trusted there: in stage 6 its
updates move the camera away, so enemies fail the on-screen test and their drawing never runs).

  update_probe.py make <rom> <out>     a measurement copy (not for release): the update entry ($6938)
                                       stores the V counter and frame at $FF2BF8 and sets $FF2BF6; the
                                       next VBlank wait ($113E5E) with it set appends (start V, start
                                       frame, end V, end frame) to a ring at $FF2C00 (64 x 8, index
                                       $FF2BF0). RAM and patch code don't move, so save states of the
                                       ROM load in its copy.
  update_probe.py read <dir>...        durations in lines from tools/headless/lr.py RAM dumps (DUMP_AT
                                       every 30 frames covers every update) of each directory.

A duration counts from the update's start to its wait, so a frame's 262 lines is the budget: updates
over it lose a frame. The V counter's second pass ($E5-$EA again) makes lines near the bottom ~6 off.
"""
import glob
import statistics
import struct
import sys

P = 0x3F0F00


def make(src, out):
    rom = bytearray(open(src, 'rb').read())
    assert all(b == 0xFF for b in rom[P:P + 0x100]), 'probe area in use'
    assert rom[0x6938:0x693A] == b'\x4e\xf9', 'update entry'
    start = bytes.fromhex(
        '33f900c0000800ff2bf8'      # move.w $C00008,$FF2BF8      start V
        '33f900ff7dfe00ff2bfa'      # move.w $FF7DFE,$FF2BFA      start frame
        '33fc000100ff2bf6'          # move.w #1,$FF2BF6
        '4ef9') + rom[0x693A:0x693E]    # jmp (what $6938 jumped to)
    assert rom[0x113E5E:0x113E64] == bytes.fromhex('303900c00004'), 'VBlank wait'
    end = bytearray.fromhex(
        '4a7900ff2bf6'              # tst.w $FF2BF6
        '6700'                      # beq.s out (offset below)
        '48e78080'                  # movem.l d0/a0,-(sp)
        '41f900ff2c00'              # lea $FF2C00,a0
        '303900ff2bf0'              # move.w $FF2BF0,d0
        '024001f8'                  # andi.w #$1F8,d0
        '21b900ff2bf80000'          # move.l $FF2BF8,0(a0,d0.w)
        '31b900c000080004'          # move.w $C00008,4(a0,d0.w)   end V
        '31b900ff7dfe0006'          # move.w $FF7DFE,6(a0,d0.w)   end frame
        '5040'                      # addq.w #8,d0
        '33c000ff2bf0'              # move.w d0,$FF2BF0
        '4cdf0101'                  # movem.l (sp)+,d0/a0
        '427900ff2bf6'              # clr.w $FF2BF6
        '303900c00004'              # out: move.w $C00004,d0 (the replaced instruction)
        '4ef900113e64')             # jmp $113E64
    end[7] = len(end) - 12 - 8
    rom[P:P + len(start)] = start
    rom[P + 0x40:P + 0x40 + len(end)] = end
    rom[0x6938:0x693E] = b'\x4e\xf9' + struct.pack('>I', P)
    rom[0x113E5E:0x113E64] = b'\x4e\xf9' + struct.pack('>I', P + 0x40)
    open(out, 'wb').write(rom)


def read(dirs):
    w = lambda r, o: r[o] << 8 | r[o + 1]
    lin = lambda v: v - 224 if v >= 224 else v + 38            # lines after VBlank start
    for d in dirs:
        ent = {}
        for f in sorted(glob.glob(d + '/*.ram')):
            raw = open(f, 'rb').read()
            r = bytes(raw[i ^ 1] for i in range(len(raw)))
            for k in range(64):
                o = 0x2C00 + 8 * k
                if w(r, o + 2) or w(r, o + 6):
                    ent[(w(r, o + 2), r[o])] = (w(r, o + 6), r[o + 4])
        ds = sorted(d_ for d_ in ((fe - fs) * 262 + lin(ve) - lin(vs) for (fs, vs), (fe, ve) in ent.items())
                    if 0 < d_ < 1200)
        if not ds:
            print(d, 'no updates')
            continue
        n = len(ds)
        print('%s: %d updates, mean %.1f lines, median %d, p90 %d, max %d, over 262: %d'
              % (d, n, statistics.mean(ds), ds[n // 2], ds[int(n * .9)], ds[-1], sum(x > 262 for x in ds)))


if __name__ == '__main__':
    if sys.argv[1] == 'make':
        make(sys.argv[2], sys.argv[3])
    else:
        read(sys.argv[2:])
