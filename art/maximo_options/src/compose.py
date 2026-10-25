import sys, struct, zlib
sys.path.insert(0, '/private/tmp/claude-501/-Users-rester159-genesis-ports--capcom-ghosts-n-goblins/17ff1186-5176-40fb-b401-d32f50b48ac1/scratchpad/tools')
from spr import savepng, palette
S='/private/tmp/claude-501/-Users-rester159-genesis-ports--capcom-ghosts-n-goblins/17ff1186-5176-40fb-b401-d32f50b48ac1/scratchpad/'
rom=open(S+'fixed3.bin','rb').read(); PAL=palette(open(S+'g/a_01500.state','rb').read())[:16]
def frame(a):
    g=[[0]*32 for _ in range(32)]
    for tx in range(4):
        for ty in range(4):
            t=a+(tx*4+ty)*32
            for y in range(8):
                for x in range(8):
                    b=rom[t+y*4+x//2]; g[ty*8+y][tx*8+x]=(b>>4) if x%2==0 else b&15
    return g
def grid(rows):
    rows=[r.ljust(32,'.')[:32] for r in rows]
    return [[None if ch=='.' else int(ch,16) for ch in r] for r in rows]
def paste(base, rows, y0=0, x0=0, under=False):
    for y,r in enumerate(rows):
        for x,ch in enumerate(r):
            if ch=='.' : continue
            yy,xx=y0+y,x0+x
            if not(0<=yy<32 and 0<=xx<32): continue
            if under and base[yy][xx]: continue
            base[yy][xx]=0 if ch=='0' else int(ch,16)
def show(path, frames, labels=None, S_=6, bg=(48,56,72)):
    pad=10; W=len(frames)*(32*S_+pad)+pad; H=32*S_+2*pad
    img=bytearray(list(bg)*W*H)
    for i,g in enumerate(frames):
        ox=pad+i*(32*S_+pad)
        for y in range(32):
            for x in range(32):
                c=g[y][x]
                if c:
                    col=bytes(PAL[c])
                    for dy in range(S_):
                        o=((pad+y*S_+dy)*W+ox+x*S_)*3; img[o:o+S_*3]=col*S_
    savepng(path,W,H,img)
