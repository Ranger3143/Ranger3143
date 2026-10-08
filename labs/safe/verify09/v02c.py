# SAFE-02: my independent byte-level decoder reproduces the engine's step-1 context digest (validates the text every score is computed from)
exec(open('v02.py').read().split("if __name__=='__main__':")[0])
import hashlib
ok=bad=0
for model in ['op12k','bitnet2b']:
    for st in '0abcdef':
        for q in items(model):
            t=open(f'{L}/{model}/{st}/receipts/{q}.txt').read()
            ctx=re.search(r'^step 1: .* ctx=([0-9a-f]+)',t,re.M).group(1)
            steps,prompt=parse(f'{L}/{model}/{st}/receipts/{q}.txt'); s0=steps[0]
            p1=prompt+dec(model,s0['toks'])+(f"\nTOOL[{s0['tool']}]={s0['out']}\n" if s0['tool']!='no-tool' else "\nTOOL[no-tool]=\n")
            if hashlib.sha256(p1.encode()).hexdigest()==ctx: ok+=1
            else: bad+=1
print('step-1 ctx digest == sha256(prompt + my_decode(step0) + gateway tool line):',ok,'of',ok+bad,'Mode-H episodes (both models, 7 styles x 30)')
