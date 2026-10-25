from maximo import *
KEY=[0x109e2, 0x109e2+4*0x200, 0x109e2+7*0x200, 0x109e2+9*0x200, 0x41000, 0x41000+3*0x200, 0x41000+4*0x200, 0x41000+8*0x200, 0x41000+37*0x200, 0x41000+9*0x200]
def sheet(path, addrs, SC=6):
    pad=8; cw=32*SC+pad; W=len(addrs)*cw+pad; H=2*cw+pad
    img=bytearray([44,50,66]*W*H)
    for c,a in enumerate(addrs):
        for r,g in enumerate((frame(a),make(a))):
            ox=pad+c*cw; oy=pad+r*cw
            for y in range(32):
                for x in range(32):
                    if g[y][x]:
                        col=bytes(PAL[g[y][x]])
                        for dy in range(SC):
                            p=((oy+y*SC+dy)*W+ox+x*SC)*3; img[p:p+SC*3]=col*SC
    savepng(path,W,H,img)
if __name__=='__main__': sheet(S+'maximo/key_v1.png',KEY)
