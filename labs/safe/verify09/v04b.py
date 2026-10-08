# SAFE-04: poison construction, leakage, frozen hashes
exec(open('v04_det.py').read().split("res={}")[0])
import collections, json, hashlib
FL={'+':'*','*':'+'}
c=collections.Counter()
for i in sorted(poi5):
    for q,m,t in turns(d5[i]):
        if 'manifest' not in q: continue
        exp=parse_q(q); a,op,b=int(m.group(1)),m.group(2),int(m.group(3)); c['n']+=1
        c['flip_same_operands']+= (exp is not None and exp[0]==a and exp[2]==b and FL.get(exp[1])==op)
        n,v=evalc(a,op,b); c['tool_value_is_oracle_of_flipped_call']+=(t.group(2)==v)
print('poisoned p5 turns',dict(c),'; docs containing "manifest" outside the poisoned set:',len([i for i,d in enumerate(d5) if 'manifest' in d and i not in poi5]))
Dd='/home/user/Ranger3143/labs/logs/safe/SAFE-04'
S='/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
P=[json.loads(l) for l in open(Dd+'/eval_prompts.jsonl')]
for tag in ['p0','p5']:
    t=open(f'{Dd}/data/episodes_{tag}.txt').read()
    pairs=set((int(a),int(b)) for a,b in re.findall(r'CALC\((-?\d+) [+\-*/%] (-?\d+)\)',t))
    print(tag,'eval operand pairs found in fine-tune CALC calls:',sum((p['a'],p['b']) in pairs for p in P),'/250; eval question verbatim in fine-tune data:',sum(('Q: '+p['question']+'\nA:') in t for p in P),'/250')
t=open(S+'/opmodel/corpus/train.txt',errors='replace').read()
pairs=set((int(a),int(b)) for a,b in re.findall(r'CALC\((-?\d+) [+\-*/%] (-?\d+)\)',t))
print('eval pairs in ORIGINAL LAB-08 train.txt CALC calls:',[(p['id'],p['a'],p['op'],p['b']) for p in P if (p['a'],p['b']) in pairs])
for f in ['episodes_p0.txt','episodes_p1.txt','episodes_p5.txt']: print(f,hashlib.sha256(open(f'{Dd}/data/{f}','rb').read()).hexdigest())
print('eval_prompts.jsonl',hashlib.sha256(open(Dd+'/eval_prompts.jsonl','rb').read()).hexdigest())
for tag in ['p0','p1','p5','p0_s8','p5_s8']:
    print('ckpt',tag,hashlib.sha256(open(f'{S}/safe04/ckpt/safe04_{tag}.pt','rb').read()).hexdigest()[:16])
