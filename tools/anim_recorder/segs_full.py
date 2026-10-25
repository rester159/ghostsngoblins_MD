run([[1000,0]]+[[10,BA],[10,0]]*3+[[10,ST],[20,0]]*3+[[60,0]], record=False)
S0=save()
def prep(boxer, left):
    load(S0)
    if boxer: ram_w(0xffc328,1)
    run([[2,0]],record=False)
    if left: run([[2,LF],[3,0]],record=False)
    return save()
for boxer in (0,1):
    for left in (0,1):
        S=prep(boxer,left); p=('boxer' if boxer else 'armor')+('L_' if left else 'R_')
        F=LF if left else RT
        load(S); results[p+'idle']=run([[30,0]])
        load(S); results[p+'walk']=run([[48,F],[6,0]])
        load(S); results[p+'crouch']=run([[30,DN],[10,0]])
        load(S); results[p+'jump']=run([[4,BC],[50,0]])
        load(S); results[p+'jumpFwd']=run([[50,F|BC],[4,0]])
        load(S); results[p+'throw']=run([[4,BB],[30,0]])
        load(S); results[p+'crouchThrow']=run([[10,DN],[4,DN|BB],[30,DN],[10,0]])
        load(S); results[p+'jumpThrow']=run([[4,BC],[10,0],[4,BB],[40,0]])
        load(S); results[p+'jumpFwdThrow']=run([[14,F|BC],[4,F|BB],[40,F]])
        load(S); results[p+'hit_until_death']=run([[700,0]])
