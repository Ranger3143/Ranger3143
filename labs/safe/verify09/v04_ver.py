import os, random, subprocess, glob, collections, re, json
L='/home/user/Ranger3143/labs/logs/safe/SAFE-04'
S='/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
EX='/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/agent_trace'
ART={'base':S+'/opmodel/exports/final_step12000/artifacts','p0':S+'/safe04/exports/safe04_p0/artifacts','p1':S+'/safe04/exports/safe04_p1/artifacts','p5':S+'/safe04/exports/safe04_p5/artifacts'}
SUITE='54112fe2821d62eec65ac1df8e9fd169e689745c02983fc9c75a35f650dfe421'
rng=random.Random('verify09-s04'); res=collections.Counter()
env=dict(os.environ,AEGIS_THREADS='1',OMP_NUM_THREADS='1')
for tag,ad in ART.items():
    for p in rng.sample(sorted(glob.glob(f'{L}/engine/{tag}/receipts/*.txt')),8):
        r=subprocess.run(['nice','-n','5',EX,'verify',ad+'/MODEL.SAF',ad+'/EMBED.BIN',ad+'/VOCAB.BIN',p,'--suite-sha256',SUITE],capture_output=True,env=env,text=True)
        ok='VERIFY PASS' in r.stdout and r.returncode==0; res[(tag,ok)]+=1
        if not ok: print('FAIL',p,r.stdout[-200:])
print(sorted(res.items()))
