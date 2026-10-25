"""Maximo = Arthur's ROM frames, face de-bearded, cape added (armored frames only)."""
from compose import *
import copy
STEEL={9,11,14,15}
FRAMES=[0x109e2+k*0x200 for k in range(11)]+[0x40000+k*0x200 for k in range(72)]
SKIP=set(0x41000+k*0x200 for k in range(16,27))   # skeleton death: unchanged (k counted from $41000)
SHARDS=set(0x41000+k*0x200 for k in range(27,31))  # flying armor pieces
def kind(g, addr=None):
    if addr in SHARDS: return 'armor'
    n=sum(1 for r in g for c in r if c in STEEL)
    return 'armor' if n>90 else 'boxer'
def eye(g):
    pts=[(y,x) for y in range(32) for x in range(32) if g[y][x]==13]
    return pts[0] if pts else None
def facing(g,ey,ex):
    r=sum(1 for x in range(ex+1,min(32,ex+5)) if g[ey+1][x] in (12,10))
    l=sum(1 for x in range(max(0,ex-4),ex) if g[ey+1][x] in (12,10))
    return 1 if r>=l else -1
def face(g):
    e=eye(g)
    if not e: return None
    ey,ex=e; d=facing(g,ey,ex); k=kind(g)
    # cheek beard on eye row, in front of the eye
    for i in range(1,5):
        x=ex+d*i
        if 0<=x<32 and g[ey][x] in (4,6,8): g[ey][x]=12 if i<3 else 10
    for y in range(ey+1, min(32,ey+(9 if k=='armor' else 13))):
        for i in range(-5,6):
            x=ex+d*i
            if not 0<=x<32: continue
            c=g[y][x]
            if c not in (4,6,8): continue
            dyy=y-ey
            if dyy<=2: g[y][x]=12
            elif dyy==3: g[y][x]=10
            elif k=='armor': g[y][x]={6:14,8:14,4:11}[c]
            else: g[y][x]={6:12,8:12,4:10}[c]
    # mouth: one shade pixel below/in front of the eye
    my,mx=ey+2,ex+2*d
    if 0<=mx<32 and g[my][mx]==12: g[my][mx]=10
    return ey,ex,d
def cape(g, y_from, d, widths):
    for i,w in enumerate(widths):
        y=y_from+i
        if not 0<=y<32: continue
        xs=[x for x in range(32) if g[y][x]]
        if not xs: continue
        edge=min(xs) if d==1 else max(xs)
        for k in range(1,w+1):
            x=edge-k*d
            if not 0<=x<32: break
            c=1 if k==w else 2 if k==w-1 or k==1 else (3 if (k+i)%5 else 2)
            if g[y][x]==0: g[y][x]=c
LONG=[2,3,3,4,4,4,5,5,5,5,6,6,6,7,7,6,7,5,3]
def back_cape(g):
    # ladder/back views: a cape panel down the centre of the back; arms stay steel
    ys=[y for y in range(32) if any(g[y])]; top=ys[0]
    xs=[x for y in range(top+10,top+16) for x in range(32) if g[y][x]]
    cx=(min(xs)+max(xs))//2
    bot=ys[-1]
    for y in range(top+8, min(32,top+23,bot-5)):
        half=3 if y<top+10 else 4 if y<top+18 else 5
        for x in range(cx-half, cx+half+1):
            if not 0<=x<32: continue
            c=g[y][x]
            if c in STEEL or (c==0 and y>=top+18):
                edge = x in (cx-half, cx+half)
                g[y][x]=1 if (c==0 and edge) else 2 if edge or c in (9,11) else 3
        # tattered hem
    for x in range(cx-5, cx+6, 3):
        y=top+23
        if 0<=x<32 and y<32 and g[y-1][x] in (2,3): g[y][x]=1
def make(addr):
    g=frame(addr)
    if addr in SKIP: return g
    g=copy.deepcopy(g)
    f=face(g)
    if kind(g)=='armor':
        if f: cape(g, f[0]+3, f[2], LONG)
        else: back_cape(g)
    return g
if __name__=='__main__':
    arts=[frame(a) for a in FRAMES]; maxs=[make(a) for a in FRAMES]
    for i in range(0,len(FRAMES),8):
        show(S+f'maximo/set_{i//8:02d}.png', [x for pair in zip(arts[i:i+8],maxs[i:i+8]) for x in pair], S_=3)
