import csv, collections, re, sys, hashlib, tarfile, io
D='/home/user/Ranger3143/labs/logs/safe/SAFE-01'
rows=list(csv.DictReader(open(D+'/h1_results.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
man={r['id']:r for r in csv.DictReader(open(D+'/h1_manifest.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE)}
print('rows',len(rows),'manifest',len(man))
def cls(r):
    rc=r['exit_code']; out=r['stdout_last']
    if rc=='' or rc=='None': return 'TIMEOUT'
    if rc=='0' and out.startswith('VERIFY PASS'): return 'ACCEPT'
    if rc=='0': return 'ACCEPT?other'
    if rc=='1' and (out.startswith('VERIFY FAIL') or out.startswith('FAIL artifact')): return 'CLEAN'
    return 'CRASH'
cnt=collections.defaultdict(collections.Counter)
mis=0
for r in rows:
    c=cls(r); cnt[r['class']][c]+=1
    # compare with reported verdict
    rep=r['verdict']; m={'ACCEPT':'ACCEPT','REJECT_CLEAN':'CLEAN','REJECT_CRASH':'CRASH','TIMEOUT':'TIMEOUT'}[rep]
    if m!=c: mis+=1; print('MISMATCH',r['id'],rep,c,r['exit_code'],r['stdout_last'][:80])
print('classifier mismatches vs reported verdict:',mis)
for k in sorted(cnt): 
    n=sum(cnt[k].values()); print(k,n,dict(cnt[k]))
reg=['C01','C02','C03','C04','C05','C06','C07','C09','C10']
print('field-value accepted',sum(cnt[k]['ACCEPT']+cnt[k]['ACCEPT?other'] for k in reg),'of',sum(sum(cnt[k].values()) for k in reg), 'crash', sum(cnt[k]['CRASH'] for k in reg))
print('registered incl C08', {k:sum(cnt[k].values()) for k in reg+['C08']})
# tar check: mutant sha matches manifest
t=tarfile.open(D+'/h1_mutants.tar.gz')
bad=0;n=0
for m in t.getmembers():
    if not m.isfile(): continue
    id_=m.name.split('/')[-1].replace('.txt','')
    b=t.extractfile(m).read(); n+=1
    if id_ in man and hashlib.sha256(b).hexdigest()!=man[id_]['mutant_sha256']: bad+=1
print('tar members',n,'sha mismatch vs manifest',bad)
# duplicates among mutants within class (distinct mutant bytes per class+src)
dist=collections.defaultdict(set)
for r in rows: dist[r['class']].add((r['src'],r['artifacts'],r['mutant_sha256']))
print('distinct (src,art,sha) per class',{k:len(v) for k,v in sorted(dist.items())})
# class sizes by distinct mutant sha only
d2=collections.defaultdict(set)
for r in rows: d2[r['class']].add(r['mutant_sha256'])
print('distinct sha only',{k:len(v) for k,v in sorted(d2.items())})
