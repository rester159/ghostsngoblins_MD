run([[1000,0]]+[[10,BA],[10,0]]*3+[[10,ST],[20,0]]*3+[[60,0]], record=False)
pat=[[12,RT],[10,UP],[6,RT|BC],[20,RT],[10,UP]]
f=0; LS=None
def inv_run(frames, m, rec=True):
    out=[]
    for _ in range(frames):
        ram_w(0xffc309,80); out+=run([[1,m]], record=rec)
    return out
done=False
for cyc in range(150):
    for n,m in pat:
        for _ in range(n):
            if f==740: LS=save()
            inv_run(1,m,False); f+=1
    if f>760: break
# find where climbing starts from LS by holding UP after a few frames of the pattern
load(LS); pre=inv_run(15,0,True)
for boxer in (0,1):
    load(LS)
    if boxer: ram_w(0xffc328,1)
    # replay the original pattern from 740 to the climb start (f 740..755)
    seq=[]
    ff=0
    for cyc in range(150):
        for n,m in pat:
            for _ in range(n):
                if 740<=ff: seq.append(m)
                ff+=1
        if ff>760: break
    k=0
    while True:
        l=inv_run(1,seq[k],True); k+=1
        if l[-1][1] and l[-1][1][0][0] in ('B4','B5','B0','B51','B52','B53','B54'): break
        if k>=len(seq): break
    p='boxer' if boxer else 'armor'
    S=save()
    results[p+'_climbUp']=inv_run(200,UP)
    T=save()
    results[p+'_climbDownFromTop']=inv_run(60,0)+inv_run(160,DN)
    load(S); results[p+'_ladderIdleThrow']=inv_run(10,UP)+inv_run(20,0)+inv_run(4,BB)+inv_run(30,0)
    load(S); results[p+'_climbDown']=inv_run(40,UP)+inv_run(60,DN)
