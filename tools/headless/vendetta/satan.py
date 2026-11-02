"""Vendetta opening: stage 6's Satan room. usage: satan.py <harness> <rom> <frames> <fast 0/1> <inv 0/1> <tag>"""
import sys, os, pickle, subprocess, random
sys.path.insert(0, sys.argv[1])
from fbh import Game, LT, RT, J, F, D
S = os.path.dirname(os.path.abspath(__file__))
rom=sys.argv[2]; N=int(sys.argv[3]); fast=int(sys.argv[4]); inv=int(sys.argv[5]); tag=sys.argv[6]
random.seed(int(os.environ.get('SEED','1')))
sym={}
for l in subprocess.check_output(['m68k-elf-nm','src_patch/build/patch.elf']).decode().split('\n'):
    p=l.split()
    if len(p)==3: sym.setdefault(p[2],int(p[0],16))
g = Game(rom, sysdir=S+'/..', options={'genesis_plus_gx_overclock': '200%'})
g.launch(6, 4); g.want_video=True
def sat():
    out=[]
    for k in range(40):
        a=0xFFB800+48*k
        if g.r8(a+4) and g.r8(a+10)==6: out.append((k,hex(g.r8(a+4)),g.r8(a+7),'hp',g.r8(a+11),g.r8(a+17)<<8|g.r8(a+18),g.r8(a+21)<<8|g.r8(a+22)))
    return out
def st(t): print(t,'fb',g.r32(0xFF9000)>>8&0xffff,g.r16(0xFF9004),'cam',g.r16(0xFF9100),g.r16(0xFF9102),'play',g.r8(0xFFC305),'hit',g.r8(0xFFC342),
                  'db08',g.r8(0xFFDB08),'db09',g.r8(0xFFDB09),'done',g.r8(sym['vd_satan_done']),'stage',g.r8(0xFFC512),'satans',sat())
st('launch'); g.png(S+'/sa%s_0.png'%tag)
plan=0
for f in range(N):
    if inv: g.w8(0xFFC309,80)
    if fast:
        for k in range(40):
            a=0xFFB800+48*k
            if g.r8(a+4)&1 and g.r8(a+10)==6 and g.r8(a+7)==1 and g.r8(a+11)>1: g.w8(a+11,1)
    if f%12==0: plan=random.choice([0,J,LT,RT,J|RT,J|LT,0,0])
    fx=g.r32(0xFF9000)>>8&0xffff
    s=sat(); tow=0
    if s: tow = RT if s[0][4] > fx else LT
    m = plan | (tow if f%30<2 else 0) | (F if (f//6)%2==0 else 0)
    g.run(1,m)
    if f%200==0: st(f)
    if f in (100,400,800): g.png(S+'/sa%s_%d.png'%(tag,f))
    if g.r8(sym['vd_satan_done']) and not getattr(g,'_d',0):
        g._d=f; st('KILLED %d'%f); 
    if getattr(g,'_d',0) and f==g._d+300:
        st('after'); g.png(S+'/sa%s_after.png'%tag)
        if os.environ.get('DIE'):     # a death after the regicide: where does he restart?
            g.w8(0xFFC309,0); g.w8(0xFFC304,2); g.w8(0xFFC305,3); g.w8(0xFFC306,0); g.w8(0xFFC307,0)
            while g.r8(0xFFC305)!=0: g.run(1,0)
            while g.r8(0xFFC305)!=1: g.run(1,0)
            g.run(30,0); st('restart'); g.png(S+'/sa%s_restart.png'%tag)
        break
    if g.r8(0xFFC342) and not getattr(g,'_h',0): g._h=1; st('DEATH %d'%f)
    if g._h if hasattr(g,'_h') else 0:
        if g.r8(0xFFC305)==1 and g.r8(0xFFC342)==0: g._h=0; st('RESTART %d'%f)
