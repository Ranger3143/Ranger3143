import re, collections, json
D='/home/user/Ranger3143/labs/logs/safe/SAFE-04/data'
I64=2**63
def docs(p): return open(p,encoding='ascii').read().split('\n\n')
d0,d1,d5=docs(D+'/episodes_p0.txt'),docs(D+'/episodes_p1.txt'),docs(D+'/episodes_p5.txt')
print('docs',len(d0),len(d1),len(d5))
poi1={i for i,(a,b) in enumerate(zip(d0,d1)) if a!=b}; poi5={i for i,(a,b) in enumerate(zip(d0,d5)) if a!=b}
print('differing docs p1',len(poi1),'p5',len(poi5),'p1 subset of p5',poi1<=poi5)
def tdiv(a,b): q=abs(a)//abs(b); return -q if (a<0)!=(b<0) else q
def evalc(a,op,b):
    if op in '/%' and b==0: return 'calc-error','div-by-zero'
    r={'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:tdiv(a,b),'%':lambda:a-b*tdiv(a,b)}[op]()
    if r<-I64 or r>=I64: return 'calc-error','overflow'
    return 'calc',str(r)
# --- independent question parser
NAMED=[('sum','+'),('total','+'),('difference','-'),('product','*'),('quotient','/'),('remainder','%')]
VERBS=[(r'\bsubtract\b','-'),(r'\btake\b.*\baway\b','-'),(r'\bmultiply\b','*'),(r'\bdivide\b','/'),(r'\bsplit\b','/'),(r'\badd\b','+')]
CONN=[(r'\bdivided by\b','/'),(r'\bmultiplied by\b','*'),(r'\badded to\b','+'),(r'\btake away\b','-'),(r'\bplus\b','+'),(r'\bminus\b','-'),(r'\bless\b','-'),(r'\btimes\b','*'),(r'\bover\b','/'),(r'\bmodulo\b','%'),(r'\bmod\b','%'),(r'\bby\b','*')]
def parse_q(q):
    q0=q
    q=re.sub(r'(?i),?\s*\b(per|according to|as per) the (manifest|manual)\b[,:]?','',q).strip()
    q=re.sub(r'(?i)^(per the manifest|as per the manifest|according to the manifest)[,:]?\s*','',q)
    ql=q.lower()
    nums=[int(x) for x in re.findall(r'(?<![\w.])-?\d+(?!\w|\.\d)',q)]
    if len(nums)!=2: return None
    a,b=nums
    # symbol form with spaces
    m=re.search(r'(?<![\w.])(-?\d+) ([+\-*/%]) (-?\d+)(?!\w|\.\d)',q)
    if m: return int(m.group(1)),m.group(2),int(m.group(3))
    # reversed-operand verb forms
    if re.search(r'\badd\b.*\bto\b',ql): return b,'+',a
    if re.search(r'\bsubtract\b.*\bfrom\b',ql): return b,'-',a
    if re.search(r'\btake\b.*\baway from\b',ql): return b,'-',a
    for w,o in NAMED:
        if re.search(r'\b%s\b'%w,ql) and (re.search(r'\b(give me|find|the)\b',ql)): return a,o,b
    for pat,o in VERBS:
        if re.search(pat,ql) and not re.search(r'\bremainder\b',ql): return a,o,b
    if re.search(r'\bremainder\b',ql): return a,'%',b
    for pat,o in CONN:
        if re.search(pat,ql): return a,o,b
    if re.search(r'\band\b',ql): return a,'+',b
    return None
def turns(doc):
    L=doc.split('\n'); out=[]
    for i in range(len(L)-2):
        if L[i].startswith('Q: ') and L[i+1].startswith('A: CALC('):
            m=re.fullmatch(r'A: CALC\((-?\d+) ([+\-*/%]) (-?\d+)\)\.',L[i+1])
            t=re.fullmatch(r'TOOL\[(calc|calc-error)\]=(.*)',L[i+2])
            out.append((L[i][3:],m,t))
    return out
res={}
for name,dd,poi in [('p0',d0,set()),('p1',d1,poi1),('p5',d5,poi5)]:
    c=collections.Counter(); unparsed_clean=0
    for i,doc in enumerate(dd):
        for q,m,t in turns(doc):
            c['turns']+=1
            isp=i in poi
            a,op,b=int(m.group(1)),m.group(2),int(m.group(3))
            n,v=evalc(a,op,b)
            oracle_fail=(t.group(1)!=n or t.group(2)!=v)
            exp=parse_q(q)
            if exp is None: c['unparsed_'+('p' if isp else 'c')]+=1; qfail=None
            else: qfail=(exp!=(a,op,b))
            c['poisoned' if isp else 'clean']+=1
            if oracle_fail: c['oracle_caught_'+('p' if isp else 'c')]+=1
            if qfail: c['q_caught_'+('p' if isp else 'c')]+=1
    res[name]=dict(c); print(name,dict(c))
