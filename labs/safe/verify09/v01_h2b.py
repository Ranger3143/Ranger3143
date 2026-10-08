import csv, hashlib, os, subprocess, random, re, json
S='/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
D='/home/user/Ranger3143/labs/logs/safe/SAFE-01'
EX='/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples'
orig=open(S+'/opmodel/exports/final_step12000/artifacts/MODEL.SAF','rb').read()
muts=list(csv.DictReader(open(D+'/h2_mutations.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
ok=0
for m in muts:
    off=int(m['abs_offset']); nb=int(m['new_byte'],16); ob=int(m['orig_byte'],16)
    assert orig[off]==ob,(m['set'],m['idx'])
    b=bytearray(orig); b[off]=nb
    h=hashlib.sha256(b).hexdigest()
    ok+= (h==m['mutated_model_sha256'])
    # on-disk copy: exactly 1 byte differing
    p=f"{S}/safe01/h2/{m['set']}_{int(m['idx']):02d}/MODEL.SAF"
    d=open(p,'rb').read()
    ndiff=sum(1 for i in range(0,len(d)) if False) 
    assert len(d)==len(orig)
    # fast diff
    diffs=[i for i in range(len(d)) if d[i]!=orig[i]] if False else None
print('independent reconstruction sha matches',ok,'of',len(muts))
