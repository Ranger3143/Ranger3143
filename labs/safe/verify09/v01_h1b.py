import csv, random, subprocess, os, re, tarfile, collections, tempfile
S='/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
BN='/tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/artifacts'
D='/home/user/Ranger3143/labs/logs/safe/SAFE-01'
EX='/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples'
ART={'A':S+'/opmodel/exports/final_step12000/artifacts','B':S+'/opmodel/exports/step2300/artifacts','C':S+'/opmodel/exports/step_early/artifacts','D':BN+'/bitnet2b_fixed'}
rows=list(csv.DictReader(open(D+'/h1_results.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
t=tarfile.open(D+'/h1_mutants.tar.gz')
tmp=S+'/verify09/h1mut'; os.makedirs(tmp,exist_ok=True)
rng=random.Random('verify09-h1')
sample=rng.sample(rows,100)
# ensure coverage: add 3 per registered class
byc=collections.defaultdict(list)
for r in rows: byc[r['class']].append(r)
for c in byc: sample+=rng.sample(byc[c],min(3,len(byc[c])))
seen=set(); sample=[r for r in sample if not (r['id'] in seen or seen.add(r['id']))]
env=dict(os.environ,AEGIS_THREADS='1',OMP_NUM_THREADS='1')
agree=0;dis=[]
res=collections.Counter()
for r in sample:
    mem=[m for m in t.getmembers() if m.name.endswith('/'+r['id']+'.txt') or m.name==r['id']+'.txt']
    assert len(mem)==1,(r['id'],len(mem))
    p=f"{tmp}/{r['id']}.txt"; open(p,'wb').write(t.extractfile(mem[0]).read())
    a=r['artifacts']; args=[ART[a[0]]+'/MODEL.SAF',ART[a[1]]+'/EMBED.BIN',ART[a[2]]+'/VOCAB.BIN']
    th='2' if 'D' in a else '1'
    e=dict(env,AEGIS_THREADS=th)
    pr=subprocess.run(['nice','-n','5',EX+'/cis_witness','verify']+args+[p],capture_output=True,env=e,timeout=900)
    out=pr.stdout.decode('utf-8','replace')
    if pr.returncode==0 and re.search(r'^VERIFY PASS',out,re.M): v='ACCEPT'
    elif pr.returncode==1 and re.search(r'^(VERIFY FAIL|FAIL artifact)',out,re.M): v='CLEAN'
    else: v='CRASH'
    rep={'ACCEPT':'ACCEPT','REJECT_CLEAN':'CLEAN','REJECT_CRASH':'CRASH'}[r['verdict']]
    res[(r['class'],v)]+=1
    if v==rep: agree+=1
    else: dis.append((r['id'],rep,v,pr.returncode))
print('sample',len(sample),'agree',agree,'disagree',dis)
print(sorted(res.items()))
