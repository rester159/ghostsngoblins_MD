"""Walk Firebrand (invulnerable) from Vendetta stage 1's start to just before the arena; save state."""
import sys, os, pickle
sys.path.insert(0, sys.argv[1])
from fbh import Game, LT, RT, J, F, D
S = os.path.dirname(os.path.abspath(__file__))
g = Game(sys.argv[2], sysdir=S+'/..', options={'genesis_plus_gx_overclock': '200%'})
g.launch(1, 4); g.want_video=True
f=0; lastx=None; stuck=0
g.w8(0xFFC521,1)                        # the checkpoint (x 1920, past the water), then a death
g.w8(0xFFC304,1); g.w8(0xFFC305,1)
g.w8(0xFFC304,2); g.w8(0xFFC305,3); g.w8(0xFFC306,0); g.w8(0xFFC307,0)
while g.r8(0xFFC305)!=0: g.run(1,0)
while g.r8(0xFFC305)!=1: g.run(1,0)
print('restart x',g.r32(0xFF9000)>>8&0xffff)
while True:
    g.w8(0xFFC309,80)
    x=g.r32(0xFF9000)>>8&0xffff; cam=g.r16(0xFF9100)
    m=LT | (J if (f%150)<130 else 0)
    g.run(1,m); f+=1
    if f%300==0: print(f,'x',x,'y',g.r16(0xFF9004),'cam',cam, 'time',g.r16(0xFFCD62))
    if cam<=40 and g.r16(0xFF9410)==0: break
    if f>12000: print('timeout'); break
g.w8(0xFFC309,0)
for _ in range(10): g.run(1,0)
print('saved at',f,'x',g.r32(0xFF9000)>>8&0xffff,'cam',g.r16(0xFF9100))
pickle.dump(g.save(), open(S+'/arena.state','wb'))
g.png(S+'/arena.png')
