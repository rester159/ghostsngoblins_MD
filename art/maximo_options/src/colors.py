from maximo import *
from keysheet import KEY
import face as F
ARMOR={'steel':None,'gunmetal':{9:1,11:9,14:11,15:14},'blue':{9:9,11:13,14:11,15:14},'gold':{9:4,11:6,14:8,15:12},'bronze':{9:4,11:5,14:7,15:12}}
SHORTS={'red':{9:2,11:2,14:3,15:3},'hearts':{9:2,11:2,14:3,15:15},'green':{9:4,11:6,14:8,15:8}}
def recolor(addr, armor, shorts):
    g=make(addr)
    if addr in SKIP: return g
    e=eye(g); k=kind(frame(addr),addr)
    m=ARMOR[armor] if k=='armor' else SHORTS[shorts]
    if not m: return g
    for y in range(32):
        for x in range(32):
            c=g[y][x]
            if c in m:
                if e and y==e[0] and abs(x-e[1])<=2: continue   # eye white/corner
                g[y][x]=m[c]
    if e and (k=='boxer' or addr in HELMETLESS):
        # auburn hair: Arthur's hair ramp (4/6/8) -> 4/5/6, head area only
        ey,ex=e
        for y in range(max(0,ey-7), ey+1):
            for x in range(max(0,ex-7), min(32,ex+7)):
                if g[y][x]==6: g[y][x]=5
                elif g[y][x]==8: g[y][x]=6
    if e:
        F.stamp(g, e[0], e[1], facing(frame(addr),*e), F.ARMOR_FACE if k=='armor' else F.BOXER_FACE)
    if k=='boxer' and shorts=='hearts':
        # white heart dots: every 3rd remaining red pixel of the shorts
        n=0
        for y in range(32):
            for x in range(32):
                if g[y][x]==3:
                    n+=1
                    if n%4==0: g[y][x]=15
    return g
def sheet(path, rows, SC=5):
    pad=8; cw=32*SC+pad; W=len(rows[0])*cw+pad; H=len(rows)*cw+pad
    img=bytearray([44,50,66]*W*H)
    for r,row in enumerate(rows):
        for c,g in enumerate(row):
            ox=pad+c*cw; oy=pad+r*cw
            for y in range(32):
                for x in range(32):
                    if g[y][x]:
                        col=bytes(PAL[g[y][x]])
                        for dy in range(SC):
                            p=((oy+y*SC+dy)*W+ox+x*SC)*3; img[p:p+SC*3]=col*SC
    savepng(path,W,H,img)
if __name__=='__main__':
    arm=KEY[:9]; box=[0x41000+k*0x200 for k in (9,37,38,41,45,47)]
    sheet(S+'maximo/armor_opts.png',[[frame(a) for a in arm]]+[[recolor(a,o,'red') for a in arm] for o in ('gunmetal','blue','gold')])
    box=[0x41000+k*0x200 for k in (9,10,41,45,47,52)]
    sheet(S+'maximo/shorts_opts.png',[[frame(a) for a in box]]+[[recolor(a,'gunmetal',s) for a in box] for s in ('red','hearts','green')])
