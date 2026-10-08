import subprocess, os, re, csv
S='/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
E='/home/user/aefinity-ai/alice-aegis/aegis-eval/target/release/aegis-eval'
A=S+'/opmodel/exports/final_step12000'
env=dict(os.environ,AEGIS_THREADS='1',OMP_NUM_THREADS='1')
def ppl(model,text,mx='512',extra=['--sample']):
    r=subprocess.run(['nice','-n','5',E,model,A+'/artifacts/EMBED.BIN',A+'/artifacts/VOCAB.BIN',text,mx]+extra,capture_output=True,text=True,env=env)
    m=re.search(r'Perplexity \(teacher-forced, (\d+) tokens\): ([0-9.]+)',r.stdout); return m.group(2) if m else None
# a longer held-out text: first 6000 chars of corpus valid.txt (prose + episodes mix)
txt=open(S+'/opmodel/corpus/valid.txt',errors='replace').read()[:20000]
open(S+'/verify09/heldout_long.txt','w').write(txt)
orig_a=ppl(A+'/artifacts/MODEL.SAF',A+'/heldout.txt')
orig_b=ppl(A+'/artifacts/MODEL.SAF',S+'/verify09/heldout_long.txt','512',[])
print('orig PPL (heldout sample, long)',orig_a,orig_b)
dec={}
for r in csv.DictReader(open('/home/user/Ranger3143/labs/logs/safe/SAFE-01/h2_decode.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE):
    if r['set'] in('byte','bit'): dec.setdefault((r['set'],int(r['idx'])),set()); 
orig_d={}
for r in csv.DictReader(open('/home/user/Ranger3143/labs/logs/safe/SAFE-01/h2_decode.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE):
    if r['set']=='orig' and r['idx']=='0': orig_d[r['canary']]=r['digest']
ch=collections=None
changed={}
for r in csv.DictReader(open('/home/user/Ranger3143/labs/logs/safe/SAFE-01/h2_decode.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE):
    if r['set'] in('byte','bit'):
        k=(r['set'],int(r['idx'])); changed[k]=changed.get(k,False) or (r['digest']!=orig_d[r['canary']])
res=[]
for s in ['byte','bit']:
    for i in range(20):
        m=f'{S}/safe01/h2/{s}_{i:02d}/MODEL.SAF'
        a=ppl(m,A+'/heldout.txt'); b=ppl(m,S+'/verify09/heldout_long.txt','512',[])
        res.append((s,i,changed[(s,i)],a,b))
        print(s,i,'digest_changed' if changed[(s,i)] else 'digest_same ',a,b, 'PPL_DIFF' if (a!=orig_a or b!=orig_b) else 'ppl_same',flush=True)
unch=[x for x in res if not x[2]]
print('digest-unchanged mutants',len(unch),'of which PPL differs from orig (either text):',sum(1 for x in unch if x[3]!=orig_a or x[4]!=orig_b))
print('digest-changed mutants',len(res)-len(unch),'of which PPL differs:',sum(1 for x in res if x[2] and (x[3]!=orig_a or x[4]!=orig_b)))
