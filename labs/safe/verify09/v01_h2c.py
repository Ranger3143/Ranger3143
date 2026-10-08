import csv, random, subprocess, os, re, json
S='/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
D='/home/user/Ranger3143/labs/logs/safe/SAFE-01'
EX='/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples'
EV='/home/user/Ranger3143/labs/logs/opmodel/final_step12000'
can={}
for q in ['self','calc','lookup','abstain']:
    t=open(f'{EV}/qemu_{q}/RECEIPT.TXT').read().split('\n')
    can[q]=bytes.fromhex([l for l in t if l.startswith('prompt-hex ')][0].split(' ',1)[1]).decode()
print(can)
dec=list(csv.DictReader(open(D+'/h2_decode.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
rec={(r['set'],r['idx'],r['canary']):r['digest'] for r in dec}
env=dict(os.environ,AEGIS_THREADS='1',OMP_NUM_THREADS='1')
art=S+'/opmodel/exports/final_step12000/artifacts'
rng=random.Random('verify09-h2')
sel=[('byte',i) for i in range(20)]+[('bit',i) for i in rng.sample(range(20),6)]
agree=0;tot=0;mism=[]
for s,i in sel:
    mdl=f'{S}/safe01/h2/{s}_{i:02d}/MODEL.SAF'
    for q in ['calc','self'] if (s,i)!=('byte',7) else list(can):
        p=subprocess.run(['nice','-n','5',EX+'/cis_decode',mdl,art+'/EMBED.BIN',art+'/VOCAB.BIN','16',can[q]],capture_output=True,env=env,text=True)
        m=re.search(r'digest=([0-9a-f]+)',p.stdout)
        d=m.group(1) if m else None
        tot+=1
        if d==rec[(s,str(i),q)]: agree+=1
        else: mism.append((s,i,q,d,rec[(s,str(i),q)]))
print('re-decoded',tot,'agree with h2_decode.tsv',agree,'mismatch',mism)
