"""Export Maximo frames (Arthur frames + face + cape, gunmetal armor, red boxers) as
Genesis 4bpp sprite tiles in Arthur's exact ROM layout: 512 bytes per 32x32 frame,
16 tiles column-major. Two banks mirror Arthur's: 11 frames from $109E2, 64 from $41000."""
import sys, struct
from colors import recolor, frame, FRAMES, show, S, PAL
from compose import savepng
def encode(g):
    out=bytearray()
    for tx in range(4):
        for ty in range(4):
            for y in range(8):
                for x in range(0,8,2):
                    out.append((g[ty*8+y][tx*8+x]<<4)|g[ty*8+y][tx*8+x+1])
    return bytes(out)
rom=open(S+'fixed3.bin','rb').read()
# encoder must reproduce Arthur's bytes exactly
for a in FRAMES: assert encode(frame(a))==rom[a:a+512], hex(a)
bankA=b''.join(encode(recolor(a,'gunmetal','red')) for a in FRAMES[:11])
bankB=b''.join(encode(recolor(a,'gunmetal','red')) for a in FRAMES[11:])   # Arthur $40000-$48FFF, 72 frames
dst=sys.argv[1]
open(dst+'/maximo_bankA.bin','wb').write(bankA)   # pairs with Arthur $109E2..$11FE1
open(dst+'/maximo_bankB.bin','wb').write(bankB)   # pairs with Arthur $40000..$48FFF
# preview sheet of every frame
gs=[recolor(a,'gunmetal','red') for a in FRAMES]
SC=3; cols=15; cw=32*SC+4; W=cols*cw+4; H=((len(gs)+cols-1)//cols)*cw+4
img=bytearray([44,50,66]*W*H)
for i,g in enumerate(gs):
    ox=4+(i%cols)*cw; oy=4+(i//cols)*cw
    for y in range(32):
        for x in range(32):
            if g[y][x]:
                col=bytes(PAL[g[y][x]])
                for dy in range(SC):
                    p=((oy+y*SC+dy)*W+ox+x*SC)*3; img[p:p+SC*3]=col*SC
savepng(dst+'/maximo_all_frames.png',W,H,img)
print('bankA',len(bankA),'bankB',len(bankB),'frames',len(gs))
