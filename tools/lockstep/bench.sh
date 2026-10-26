#!/bin/sh
# bench.sh <rom> <stage> <players 0 1P / 1 co-op / 2 Firebrand>: in-play updates per frame (deaths excluded), frames 2000-3600, SEED picks the random input; the log (with the fault word $FFC9DC) goes to $OUT/tw/flt_<TAG>_<stage>_<players>_<seed>.txt
D=$(cd "$(dirname "$0")" && pwd); W=${OUT:-/tmp/gng_bench}; mkdir -p $W/tw $W/prof
P="$D/../.."
C="$HOME/Library/Application Support/RetroArch/cores/genesis_plus_gx_libretro.dylib"
Rn=$(python3 -c "
import random; random.seed(int("${SEED:-7}")); s=[]; f=1400
while f<3600:
  m=random.choice(['80','180','100','1','40','141','0','81','80']); n=random.randint(8,40); s.append('%d-%d:%s'%(f,f+n,m)); f+=n+1
print(','.join(s))")
PK=$(python3 -c "print(','.join('%d:FFC309:60'%f for f in range(1300,3600,30)))")
X=""; [ "$3" = 1 ] && X="$Rn"
SCRIPT="$(python3 $D/devscript.py $2 $3 $Rn)" SCRIPT2="$X" POKE="$PK" STEP=50 WATCH="1FFC9DC FFC570 FFC571 1FF7084 1FF7DFC" REGION=${REGION:-ntsc-u} python3 "$P/tools/headless/lr.py" "$C" "$1" 3600 $W/prof/b3_$$ | tee $W/tw/flt_${TAG:-x}_$2_$3_${SEED:-7}.txt | python3 -c "
import sys,re
prev=None; u_=0; f_=0; d=0; n=0
for l in sys.stdin:
  m=re.search(r'FFC570=(..) FFC571=(..) FF7084=(\w+) FF7DFC=(\w+) frame (\d+)',l)
  if not m: continue
  fr=int(m.group(5))
  if fr<2000: continue
  dying=m.group(1)!='00' or m.group(2)!='00'; u=int(m.group(3),16); v=int(m.group(4),16)
  if prev and not dying and not prev[2]: u_+=u-prev[0]; f_+=v-prev[1]
  d+=dying; n+=1; prev=(u,v,dying)
print('stage $2 players $3: %.3f in-play updates per frame (dying %d%%)'%(u_/max(1,f_),100*d//max(1,n)))"
