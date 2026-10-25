run([[1000,0]]+[[10,BA],[10,0]]*3+[[10,ST],[20,0]]*3+[[60,0]], record=False)
load(save()); ram_w(0xffc328,1); run([[2,0]],record=False); run([[2,LF],[3,0]],record=False)
results['bl_ct']=run([[10,DN],[4,DN|BB],[30,DN],[10,0]])
