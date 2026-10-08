import csv, collections
D='/home/user/Ranger3143/labs/logs/safe/SAFE-01'
rows=list(csv.DictReader(open(D+'/h3_results.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
print(len(rows))
by=collections.defaultdict(list)
for r in rows: by[r['class']].append(r)
tot=collections.Counter()
for c,rs in by.items():
    a1=sum(r['F1_exit']=='0' for r in rs); a2=sum(r['F2_exit']=='0' for r in rs)
    silent=sum(r['F1_exit']=='0' and r['F1_quote_pass_line']=='0' for r in rs)
    print(f'{c:20s} n={len(rs):3d} F1acc={a1:3d} F2acc={a2:3d} silent_noquote={silent}')
reg=['pcr-value','quote-attest','quote-signature','quote-qualifying','quote-pubkey','event-line','measured-line','field-deletion']
print('registered combined',sum(len(by[c]) for c in reg),sum(r['F1_exit']=='0' for c in reg for r in by[c]),sum(r['F2_exit']=='0' for c in reg for r in by[c]))
named=['pcr-value','quote-attest','quote-signature','quote-qualifying','quote-pubkey']
print('named',sum(len(by[c]) for c in named),sum(r['F1_exit']=='0' for c in named for r in by[c]),sum(r['F2_exit']=='0' for c in named for r in by[c]))
# exits other than 0/1?
print(collections.Counter((r['F1_exit'],r['F2_exit']) for r in rows))
# ctrl
print([ (r['id'],r['F1_exit'],r['F2_exit']) for r in by['control']])
# the crucial question: accepted F1 but not F2 / F2 but not F1
print('F1 acc & F2 rej',[r['id'] for r in rows if r['F1_exit']=='0' and r['F2_exit']!='0' and r['class']!='control'])
print('F1 rej & F2 acc',[r['id'] for r in rows if r['F1_exit']!='0' and r['F2_exit']=='0'])
# subclass of event-line
sub=collections.defaultdict(lambda:[0,0])
for r in by['event-line']:
    sub[r['sub']][0]+=1; sub[r['sub']][1]+= r['F1_exit']=='0'
print(dict(sub))
print('pcr4 event accepted',sum(v[1] for k,v in sub.items() if k.startswith('pcr4')),'of',sum(v[0] for k,v in sub.items() if k.startswith('pcr4')))
print('type accepted', sum(v[1] for k,v in sub.items() if k.endswith('type') and not k.startswith('pcr4')), sum(v[0] for k,v in sub.items() if k.endswith('type') and not k.startswith('pcr4')))
# s1/s2
s1=list(csv.DictReader(open(D+'/h3_s1_receipt_side.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
print('S1',len(s1),sum(r['F1_exit']=='0' for r in s1),sum(r['F2_exit']=='0' for r in s1))
s2=list(csv.DictReader(open(D+'/h3_s2_forgery.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE))
print('S2',[(r['id'],r['F1_exit'],r['F2_exit'],r['cis_witness_exit']) for r in s2])
