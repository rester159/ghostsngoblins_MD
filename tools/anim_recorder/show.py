import json,sys
R=json.load(open(sys.argv[1]))
for k,log in R.items():
    out=[];prev=None;c=0
    for m,h in log:
        s=(h[0][0]+('f' if h[0][1] else '')) if h else '-'
        if s==prev: c+=1
        else:
            if prev: out.append(f'{prev}x{c}')
            prev=s;c=1
    out.append(f'{prev}x{c}'); print(k,':',' '.join(out)); print()
