"""bg_writes.py <state> <frames> <arthur y to pin> <frames to pin>: the arcade from a state, logging per frame
which bg RAM cells ($2800-$2FFF, the terrain map) were written: ring columns/rows relative to the camera
(PAD = held pad bits). Used for Fixed 65."""
import os, sys, collections
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, T + '/tools/arcade')
from gng import GnG
log=[]
orig=GnG.write
def w(self,a,v):
    if 0x2800<=a<0x3000: log.append((self.frame,a,v,self.cpu.pc))
    orig(self,a,v)
GnG.write=w
g = GnG(T + '/rom'); g.load(sys.argv[1]); m = g.mem
n=int(sys.argv[2]); ty=int(sys.argv[3]); pin=int(sys.argv[4])
for f in range(n):
    m[0xAD]=60
    if f<pin: m[0x509]=ty>>8; m[0x50A]=ty&255
    g.set_inputs(0,int(os.environ.get('PAD','0'),16),0)
    cb=(m[0x9C]<<8|m[0x9D], m[0x9E]<<8|m[0x9F]); k=len(log); g.run_frame()
    ca=(m[0x9C]<<8|m[0x9D], m[0x9E]<<8|m[0x9F]); new=log[k:]
    if new:
        offs=sorted(set(((l[1]-0x2800)&0x3FF) for l in new))
        slots=sorted(set(o>>5 for o in offs)); by=sorted(set(o&31 for o in offs))
        c=ca[1]//16; cc=ca[0]//16
        rel=sorted(set([r-c for r in range(c-40,c+48) for b in by if ((r^15)&31)==b and abs(r-c)<=20]))
        relc=sorted(set([x-cc for x in range(cc-40,cc+48) for s in slots if x%32==s and abs(x-cc)<=20]))
        print(f,'cam',cb,'->',ca,'n',len(new),'slots',len(slots),sorted(slots) if 4<len(slots)<32 else '','colrel',relc if len(slots)<4 else '-','bytes',len(by),'rowrel',rel if len(by)<4 else ('%d..%d'%(min(by),max(by))))
