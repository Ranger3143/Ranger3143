import os, random, subprocess, hashlib, glob, collections
L='/home/user/Ranger3143/labs/logs/safe/SAFE-03'
S='/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
EX='/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/agent_trace'
ART={'op12k':S+'/opmodel/exports/final_step12000/artifacts','bitnet2b':'/tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/artifacts/bitnet2b_fixed'}
sha=hashlib.sha256(open(L+'/prompts.tsv','rb').read()).hexdigest()
rng=random.Random('verify09-s03'); res=collections.Counter()
for model in ART:
    env=dict(os.environ,AEGIS_THREADS='1' if model=='op12k' else '2',OMP_NUM_THREADS='1')
    pick=rng.sample(sorted(glob.glob(f'{L}/{model}/receipts/q*.txt')),14)
    for p in pick:
        ad=ART[model]
        r=subprocess.run(['nice','-n','5',EX,'verify',ad+'/MODEL.SAF',ad+'/EMBED.BIN',ad+'/VOCAB.BIN',p,'--suite-sha256',sha],capture_output=True,env=env,text=True)
        ok='VERIFY PASS' in r.stdout and r.returncode==0; res[(model,ok)]+=1
        if not ok: print('FAIL',p,r.stdout[-200:])
print(sorted(res.items()))
