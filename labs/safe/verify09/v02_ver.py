import os, random, subprocess, hashlib, re, glob, collections
L='/home/user/Ranger3143/labs/logs/safe/SAFE-02'
S='/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
EX='/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/agent_trace'
ART={'op12k':S+'/opmodel/exports/final_step12000/artifacts','bitnet2b':'/tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/artifacts/bitnet2b_fixed'}
SUITE={'op12k':L+'/suites/suite_op12k_zeroshot.tsv','bitnet2b':L+'/suites/suite_bitnet2b_t2.tsv'}
sha=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest()
rng=random.Random('verify09-s02')
res=collections.Counter()
for model in ART:
    ad=ART[model]; th='1' if model=='op12k' else '2'
    env=dict(os.environ,AEGIS_THREADS=th,OMP_NUM_THREADS='1')
    for mode in 'HF':
        cands=[]
        for st in '0abcdef':
            pat=f'{L}/{model}/{st}/receipts/q*.txt' if mode=='H' else f'{L}/{model}/{st}/fw/receipts/q*.s[01].txt'
            cands+= [(st,p) for p in glob.glob(pat)]
        pick=rng.sample(sorted(cands),12)
        for st,p in pick:
            r=subprocess.run(['nice','-n','5',EX,'verify',ad+'/MODEL.SAF',ad+'/EMBED.BIN',ad+'/VOCAB.BIN',p,'--table',f'{L}/tables/{st}.tsv','--suite-sha256',sha(SUITE[model])],capture_output=True,env=env,text=True)
            ok='VERIFY PASS' in r.stdout and r.returncode==0
            res[(model,mode,ok)]+=1
            if not ok: print('FAIL',p,r.stdout[-200:],r.stderr[-200:])
print(sorted(res.items()))
