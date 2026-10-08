import subprocess, urllib.parse, re, html, sys, time, datetime
Q = [
 ("Q01", 'all:"prompt injection" AND all:receipt'),
 ("Q02", 'all:"prompt injection" AND all:attestation AND all:tool'),
 ("Q03", 'all:"prompt injection" AND all:gateway AND all:"tool call"'),
 ("Q04", 'all:"prompt injection" AND (all:"signed receipt" OR all:"signed receipts" OR all:"tool receipt" OR all:"tool receipts")'),
 ("Q05", 'all:poisoning AND all:"tool call" AND (all:oracle OR all:verifier OR all:"execution-verified")'),
 ("Q06", 'all:backdoor AND all:"tool-call" AND all:synthetic AND all:verified'),
 ("Q07", 'all:poisoning AND all:"synthetic" AND all:"consistency check" AND all:"tool"'),
 ("Q08", 'all:attested AND all:inference AND all:receipt'),
 ("Q09", 'all:TPM AND all:attestation AND all:"language model" AND all:inference'),
 ("Q10", 'all:sycophancy AND all:abstention AND all:pressure'),
 ("Q11", 'all:"prompt injection" AND all:"small language model" AND all:"tool"'),
 ("Q12", 'all:ternary AND all:"prompt injection"'),
 ("Q13", 'all:"grammar" AND all:"tool call" AND all:"prompt injection" AND all:gateway'),
]
print("# arXiv API queries run", datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"))
for qid, q in Q:
    url = "http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q) + "&max_results=12&sortBy=relevance"
    r = subprocess.run(["curl","-sS","-L","--max-time","60",url],capture_output=True,text=True)
    t = r.stdout
    tot = re.search(r'<opensearch:totalResults[^>]*>(\d+)<', t)
    print(f"\n## {qid}  query: {q}\n   totalResults: {tot.group(1) if tot else 'ERR '+r.stderr[:100]}")
    for e in re.findall(r'<entry>(.*?)</entry>', t, flags=re.S)[:12]:
        i = re.search(r'<id>http://arxiv.org/abs/([^<]+)</id>', e); ti = re.search(r'<title>(.*?)</title>', e, flags=re.S); pu = re.search(r'<published>(\d{4}-\d\d-\d\d)', e)
        print("   ", i.group(1) if i else "?", pu.group(1) if pu else "?", re.sub(r'\s+',' ',html.unescape(ti.group(1))).strip()[:130] if ti else "?")
    time.sleep(3.5)
