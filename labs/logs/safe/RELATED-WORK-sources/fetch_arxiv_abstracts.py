import sys, re, html, json, subprocess, os
ids = sys.argv[1:]
out = {}
for i in ids:
    url = f"https://arxiv.org/abs/{i}"
    r = subprocess.run(["curl","-sS","-L","--max-time","40",url],capture_output=True,text=True)
    t = r.stdout
    if not t:
        out[i] = {"err": r.stderr[:200]}; continue
    def meta(n):
        return [html.unescape(x) for x in re.findall(r'<meta name="%s" content="(.*?)"\s*/?>'%n, t, flags=re.S)]
    title = meta("citation_title")
    authors = meta("citation_author")
    date = meta("citation_date") + meta("citation_online_date")
    ab = meta("citation_abstract")
    m = re.search(r'<td class="tablecell comments[^>]*>(.*?)</td>', t, flags=re.S)
    comm = html.unescape(re.sub('<[^>]+>','',m.group(1))).strip() if m else ""
    jr = re.search(r'<td class="tablecell jref">(.*?)</td>', t, flags=re.S)
    jref = html.unescape(re.sub('<[^>]+>','',jr.group(1))).strip() if jr else ""
    out[i] = {"title": title[:1], "authors": authors, "date": date[:2], "comments": comm, "jref": jref, "abstract": re.sub(r'\s+',' ',ab[0]).strip() if ab else ""}
json.dump(out, open("abs.json","w"), indent=1)
for i,v in out.items():
    print("=====", i); 
    if "err" in v: print(v); continue
    print("TITLE:", v["title"]); print("AUTHORS:", "; ".join(v["authors"])[:300]); print("DATE:", v["date"]); print("COMMENTS:", v["comments"]); print("JREF:", v["jref"])
    print("ABSTRACT:", v["abstract"])
