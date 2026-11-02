"""From arena.state: a duel with a simple policy, no invincibility. Prints Arthur's and Firebrand's state.
usage: duel.py <harness> <rom> <frames> <seed> <tag> [inv]"""
import sys, os, pickle, subprocess, random
sys.path.insert(0, sys.argv[1])
from fbh import Game, LT, RT, J, F, D
S = os.path.dirname(os.path.abspath(__file__))
rom=sys.argv[2]; N=int(sys.argv[3]); random.seed(int(sys.argv[4])); tag=sys.argv[5]; inv=len(sys.argv)>6
sym={}
for l in subprocess.check_output(['m68k-elf-nm','src_patch/build/patch.elf']).decode().split('\n'):
    p=l.split()
    if len(p)==3: sym.setdefault(p[2],int(p[0],16))
A=lambda n: sym[n]
g = Game(rom, sysdir=S+'/..', options={'genesis_plus_gx_overclock': '200%'})
g.load(pickle.load(open(S+'/arena.state','rb'))); g.want_video=True
def sx(v): return v-(1<<32) if v>=1<<31 else v
def arthur(): return sx(g.r32(A('ax')))>>8, sx(g.r32(A('ay')))>>8
deaths=0; was=0; m=0; plan=0
hits=[]
for f in range(N):
    if inv: g.w8(0xFFC309,80)
    ax,ay=arthur(); fx=g.r32(0xFF9000)>>8&0xffff; fy=g.r16(0xFF9004)
    st=g.r8(A('st'))
    if f%10==0:
        r=random.random()
        tow = LT if ax < fx else RT
        away = RT if ax < fx else LT
        dist=abs(ax-fx)
        if dist<50: base=away|J
        elif r<0.25: base=J            # jump/hover and fire from the air
        elif r<0.35: base=away
        elif r<0.45: base=tow
        else: base=0
        plan=base
    face_tap = (LT if ax < fx else RT) if f%30<2 else 0
    m = plan | face_tap | (F if (f//6)%2==0 else 0)
    if st==0: m = LT | (J if f%40<20 else 0)
    # dodge lances
    L=A('lance')
    for i in range(3):
        if g.r8(L+14*i+12):
            lx=sx(g.r32(L+14*i))>>8; ly=sx(g.r32(L+14*i+4))>>8
            if abs(lx-fx)<48 and ly < fy and random.random()<0.6: m|=J
    g.run(1,m)
    dead=g.r8(0xFFC342)
    if dead and not was: deaths+=1; print(f,'DEATH',deaths,'fb',fx,fy,'A',ax,ay,'st',st,'hp',g.r8(A('hp')),'arm',g.r8(A('armor')))
    was=dead
    if f%300==0 or (os.environ.get("DBG") and f%int(os.environ["DBG"])==0): print(f,"ph",[g.r8(0xFFC300+k) for k in (4,5,6,7,9,0x42)],"cam",g.r16(0xFF9100),g.r16(0xFFF428+1),"fb",fx,fy,'A st',st,'hp',g.r8(A('hp')),'arm',g.r8(A('armor')),'x',ax,ay,'lives',g.r8(0xFFC500),'time',g.r16(0xFFCD62))
    if f in (200,250,262,270,276,400,800,1600,2600,2800,3000) or (os.environ.get("SNAP") and f%int(os.environ["SNAP"])==0): g.png('%s/d%s_%d.png'%(S,tag,f))
    if st==5: print(f,'ARTHUR DEAD'); g.png('%s/d%s_win.png'%(S,tag)); break
    if g.r8(0xFFC305)==0 and deaths>=1 and st==0 and f>100: print(f,'restart -> stop'); break
