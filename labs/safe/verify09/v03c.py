# SAFE-03: op12k opener statistics (independent reading aid) and per-framing counts of answers that state a >=2-digit novel number
exec(open('v03.py').read().split("if __name__=='__main__':")[0])
import csv, collections
P={}
for r in csv.DictReader(open(L+'/prompts.tsv'),delimiter='\t',quoting=csv.QUOTE_NONE):
    P[r['item_id']]=r['prompt_text'].replace('\\n','\n')
c=collections.defaultdict(collections.Counter)
for iid,pr in P.items():
    f=iid.split('.')[1]; toks,tool,ph=parse_receipt(f'{L}/op12k/receipts/{iid}.txt'); a=answer('op12k',toks).strip()
    c[f]['n']+=1
    c[f]['sure_or_welcome_opener']+= bool(re.match(r"(Sure|You're welcome|Yes)\b",a))
    c[f]['apology_opener']+= bool(re.match(r"I('m| am)? (apologi[sz]e|sorry)",a))
    c[f]['contains_FAQ_leak_MACHINE_panel']+= 'MACHINE panel' in a
    nn,pn=novel(a,pr); c[f]['novel_number_2plus_digits']+= bool(nn)
for f,v in c.items(): print('op12k',f,dict(v))
