import csv, subprocess, tarfile, os, collections
S='/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
D='/home/user/Ranger3143/labs/logs/safe/SAFE-01'
AV='/home/user/Ranger3143/labs/tools/attest_verify.py'
EV='/home/user/Ranger3143/labs/logs/opmodel/final_step12000'
ART=S+'/opmodel/exports/final_step12000/artifacts'
rows=list(csv.DictReader(open(D+'/h3_results.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
t=tarfile.open(D+'/h3_mutants.tar.gz')
tmp=S+'/verify09/h3mut'; os.makedirs(tmp,exist_ok=True)
dis=[]; n=0
for r in rows:
    mem=[m for m in t.getmembers() if m.name.endswith(r['id']+'/ATTEST.TXT')]
    assert len(mem)==1,r['id']
    p=f"{tmp}/{r['id']}.ATTEST.TXT"; open(p,'wb').write(t.extractfile(mem[0]).read())
    rec=f"{EV}/{r['base']}/RECEIPT.TXT"
    e1=subprocess.run(['python3','-I',AV,p,rec],capture_output=True).returncode
    e2=subprocess.run(['python3','-I',AV,p,'--receipt',rec,'--artifacts',ART],capture_output=True).returncode
    n+=1
    if str(e1)!=r['F1_exit'] or str(e2)!=r['F2_exit']: dis.append((r['id'],e1,e2,r['F1_exit'],r['F2_exit']))
print('rerun',n,'disagree',dis)
