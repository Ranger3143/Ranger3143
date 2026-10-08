# SAFE-03: control recount, 2B false-premise answers, all 150 op12k answers (for independent reading)
exec(open('v03.py').read().split("if __name__=='__main__':")[0])
import csv, collections
CL=L+'/control'
rows=list(csv.DictReader(open(CL+'/prompts.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
for model in ['op12k','bitnet2b']:
    c=collections.Counter()
    for r in rows:
        iid=r['item_id']; f=iid.split('.')[1]
        toks,tool,ph=parse_receipt(f'{CL}/{model}/receipts/{iid}.txt')
        assert ph==r['prompt_text'].replace('\\n','\n'),iid
        a=answer(model,toks); c[(f,AB.search(nq(a)) is not None)]+=1
    print('control',model,'plain abstain',sum(v for (f,ab),v in c.items() if f=='plain' and ab),'/ 6; framed abstain',sum(v for (f,ab),v in c.items() if f!='plain' and ab),'/ 24')
P={}
for r in csv.DictReader(open(L+'/prompts.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE):
    P[r['item_id']]=(r['prompt_text'].replace('\\n','\n'),re.search(r'planted=(\S+)',r['notes']).group(1))
print('--- bitnet2b false-premise answers and frozen confirmation flag ---')
for iid in P:
    if iid.endswith('falsepremise'):
        toks,tool,ph=parse_receipt(f'{L}/bitnet2b/receipts/{iid}.txt'); a=answer('bitnet2b',toks); ab=AB.search(nq(a)) is not None
        conf=(not ab) and (planted_in(nq(a),P[iid][1]) or CONF.search(nq(a)) is not None)
        print(iid,'CONF' if conf else '----',repr(a[:120]))
print('--- all 150 op12k answers (first 100 chars) ---')
for iid in P:
    toks,tool,ph=parse_receipt(f'{L}/op12k/receipts/{iid}.txt'); print(iid,'|',repr(answer('op12k',toks)[:100]))
