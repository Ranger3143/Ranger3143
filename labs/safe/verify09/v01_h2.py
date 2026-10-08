import csv, collections
D='/home/user/Ranger3143/labs/logs/safe/SAFE-01'
dec=list(csv.DictReader(open(D+'/h2_decode.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
print(len(dec), collections.Counter(r['set'] for r in dec))
orig={r['canary']:r['digest'] for r in dec if r['set']=='orig' and r['idx']=='0'}
rep={r['canary']:r['digest'] for r in dec if r['set']=='orig_repeat'}
print('orig',orig,'repeat same',rep==orig, 'crashes',[r for r in dec if r['exit_code']!='0'][:2])
for s in ['byte','bit']:
    ch=collections.defaultdict(set); per=collections.Counter()
    for r in dec:
        if r['set']==s and r['digest']!=orig[r['canary']]:
            ch[r['idx']].add(r['canary']); per[r['canary']]+=1
    n=len({r['idx'] for r in dec if r['set']==s})
    print(s,'mutants',n,'with>=1 changed',len(ch),'all4',sum(1 for v in ch.values() if len(v)==4),'decodes changed',sum(per.values()),dict(per))
    # first diff idx
    fd=[]
    import json
    o={r['canary']:json.loads(r['token_ids']) for r in dec if r['set']=='orig' and r['idx']=='0'}
    for r in dec:
        if r['set']==s and r['digest']!=orig[r['canary']]:
            t=json.loads(r['token_ids']); fd.append(next(i for i,(a,b) in enumerate(zip(t,o[r['canary']])) if a!=b))
    print(' first diff idx',min(fd),max(fd))
ver=list(csv.DictReader(open(D+'/h2_verify.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
print(len(ver),collections.Counter((r['kind'],r['verdict']) for r in ver))
print(collections.Counter(r['stdout_last'][:40] for r in ver if r['kind']!='self'))
# cross: original-minted receipts vs mutated
cross=[r for r in ver if r['kind']!='self']
print('cross rows',len(cross),'ACCEPT among cross',sum(r['verdict']=='ACCEPT' for r in cross))
selfv=[r for r in ver if r['kind']=='self']
print('self',len(selfv),sum(r['verdict']=='ACCEPT' for r in selfv))
