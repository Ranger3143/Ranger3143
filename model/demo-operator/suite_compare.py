#!/usr/bin/env python3
"""Per-item view of a run_suite.sh result: expected vs observed call text (from the receipt's
step-0 `in=` hex), plus the decoded model text, so misses can be read. Usage:
  suite_compare.py <suite.tsv> <outdir> [--all]"""
import sys, csv, re, binascii
suite, out = sys.argv[1], sys.argv[2]; show_all = "--all" in sys.argv
exp = {r["item_id"]: r for r in csv.DictReader(open(suite), delimiter="\t")}
rows = list(csv.DictReader(open(out + "/summary.tsv"), delimiter="\t"))
def step0(path):
    txt = open(path, errors="replace").read()
    m = re.search(r"^step 0:.*$", txt, re.M); s = m.group(0) if m else ""
    def fld(k):
        mm = re.search(k + r"=([0-9a-f]*)", s); 
        return binascii.unhexlify(mm.group(1)).decode("utf-8", "replace") if mm and mm.group(1) else ""
    dec = ""
    md = re.search(r"^decoded-0 (.*)$", txt, re.M) or re.search(r"^text-0 (.*)$", txt, re.M)
    return fld("in"), fld("out"), (md.group(1) if md else "")
miss = 0
for r in rows:
    e = exp[r["item_id"]]; ok = r["arg_match"] == "true" or (e["expected_tool"] == "NONE" and r["tool_observed"] == "NONE")
    if ok and not show_all: continue
    inp, outp, dec = step0(r["receipt_path"])
    if not ok: miss += 1
    print(f"[{'ok ' if ok else 'MISS'}] {r['item_id']:<22} expected {e['expected_tool']} {e['expected_input']!r:<28} observed {r['tool_observed']} {inp!r} -> {outp!r}  verify={r['verify_result']}")
print(f"misses: {miss}/{len(rows)}")
