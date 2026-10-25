"""Segment recorder: boots into a real game (coin + start), keeps savestates, and records
Arthur's 32x32 frame sequence for scripted input segments. Usage: rec2.py ROM segs.py out.json"""
import ctypes as C, sys, os, json
CORE=os.path.expanduser('~/Library/Application Support/RetroArch/cores/genesis_plus_gx_libretro.dylib')
rom_path, segs_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
L=C.CDLL(CORE)
ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p); VID=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AS=C.CFUNCTYPE(None,C.c_int16,C.c_int16); ASB=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
IP=C.CFUNCTYPE(None); IS=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
pad=[0]
def env(cmd,data):
    cmd&=0xffff
    if cmd==10: return True
    if cmd in (9,31): C.cast(data,C.POINTER(C.c_char_p))[0]=b'.'; return True
    return False
def ist(port,dev,idx,id_): return 1 if port==0 and (pad[0]>>id_)&1 else 0
cbs=[ENV(env),VID(lambda *a:None),AS(lambda l,r:None),ASB(lambda d,n:n),IP(lambda:None),IS(ist)]
L.retro_set_environment(cbs[0]);L.retro_set_video_refresh(cbs[1]);L.retro_set_audio_sample(cbs[2])
L.retro_set_audio_sample_batch(cbs[3]);L.retro_set_input_poll(cbs[4]);L.retro_set_input_state(cbs[5])
L.retro_init()
class GI(C.Structure): _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
data=open(rom_path,'rb').read(); buf=C.create_string_buffer(data,len(data))
assert L.retro_load_game(C.byref(GI(rom_path.encode(),C.cast(buf,C.c_void_p),len(data),None)))
L.retro_serialize_size.restype=C.c_size_t; N=L.retro_serialize_size(); sb=C.create_string_buffer(N)
L.retro_get_memory_data.restype=C.c_void_p; L.retro_get_memory_size.restype=C.c_size_t
BASE=0x12425
FR=[0x109e2+k*0x200 for k in range(11)]+[0x41000+k*0x200 for k in range(72)]
NAMES=['A%d'%k for k in range(11)]+['B%d'%k for k in range(72)]
LUT={}
for i,a in enumerate(FR): LUT.setdefault(data[a:a+512], i)
UP,DN,LF,RT,BA,BB,BC,ST=16,32,64,128,2,1,256,8     # Genesis A=Y, B=B, C=A in gpgx
def save():
    L.retro_serialize(sb,N); return sb.raw
def load(s):
    b=C.create_string_buffer(s,len(s)); L.retro_unserialize(b,len(s))
def ram_w(addr, val):
    p=L.retro_get_memory_data(2); C.cast(p,C.POINTER(C.c_ubyte))[(addr-0xff0000)^1]=val
def ram_r():
    p=L.retro_get_memory_data(2); n=L.retro_get_memory_size(2)
    r=C.string_at(p,n); return bytes(r[i^1] for i in range(n))
def sprites():
    st=save(); vr=lambda a,k: bytes(st[BASE+((a+i)^1)] for i in range(k))
    regs=st[BASE+0x10100:BASE+0x10120]; sat=(regs[5]&0x7f)<<9
    hits=[]; link=0
    for _ in range(80):
        e=vr(sat+link*8,8)
        y=((e[0]<<8)|e[1])&0x3ff; size=e[2]&0xf; nxt=e[3]&0x7f
        w2=(e[4]<<8)|e[5]; x=((e[6]<<8)|e[7])&0x1ff
        if size==0xf:
            idx=LUT.get(vr((w2&0x7ff)*32,512))
            if idx is not None and NAMES[idx]!='B26': hits.append([NAMES[idx],(w2>>11)&1,x-128,y-128])
        if nxt==0: break
        link=nxt
    return hits
def run(inputs, record=True):
    log=[]
    for frames,mask in inputs:
        for _ in range(frames):
            pad[0]=mask; L.retro_run()
            if record: log.append([mask, sprites()])
    return log
G=dict(ram_r=ram_r, run=run, save=save, load=load, ram_w=ram_w, UP=UP,DN=DN,LF=LF,RT=RT,BA=BA,BB=BB,BC=BC,ST=ST, results={})
exec(open(segs_path).read(), G)
json.dump(G['results'], open(out,'w'))
print('segments', list(G['results']))
