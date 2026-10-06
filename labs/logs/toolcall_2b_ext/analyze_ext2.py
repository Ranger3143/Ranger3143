#!/usr/bin/env python3
"""analyze_ext2.py - GENERALISED COPY of analyze_ext.py (bucket names, output-file suffix and few-shot
call detection are parameters). The PRIMARY classification rules and the post-hoc rule below are the same as
in analyze_ext.py; running this script on the T1 run must reproduce analysis.txt (regression check, see
RESULT_T2.md). Usage:
  analyze_ext2.py <VOCAB.BIN> <run_dir> <suite.tsv> <old_run_dir|-> <unknown_fact_bucket> <distractor_bucket> <suffix>
Added relative to analyze_ext.py: text-level call check on distractors (CALC( / LOOKUP( / FILE-READ( anywhere in
the decoded text), shot-call identity for any CALC/LOOKUP shot in the prompt, and (informational) whether a
LOOKUP call with a non-expected argument equals a shot call.

Original doc follows.

analyze_ext.py - post-run analysis of the ext suite (unknown_fact + distractor).

Reads ONLY files produced by the run: ext_suite.tsv, run/summary.tsv, run/receipts/*.txt,
and the VOCAB.BIN named in run/RUN.txt's artifact (path given on the command line) to decode
the receipt's `toks=` ids back to text (receipts record ids, not text).

Classification rules (fixed before any receipt was read):
  per item, step 0 only (K=1). raw receipt tool in {calc, calc-error, lookup, file-read, no-tool}.
  unknown_fact classes, mutually exclusive, first match wins:
    lookup_exact_key : raw tool == lookup and in == expected_input
    lookup_other_arg : raw tool == lookup and in != expected_input
    other_tool       : raw tool in {calc, calc-error, file-read}
    abstain          : raw tool == no-tool and answer segment matches ABSTAIN_RE
    inline_answer    : raw tool == no-tool, not abstain, answer segment non-empty
    empty            : raw tool == no-tool, answer segment empty/whitespace
  answer segment = decoded step-0 text up to (not including) the first "\nQ:" (whole text if none).
  call position = 'answer' if the recorded call text starts before the first "\nQ:" in the decoded
  text, else 'continuation'.
  SECONDARY (post hoc, added AFTER reading the 30 unknown_fact decoded texts; reported separately,
  never replaces the primary rule): POSTHOC_ABSTAIN_RE = ABSTAIN_RE plus "not provided|does not
  provide|do not provide|doesn't provide". An inline_answer whose answer segment matches it is
  counted as 'abstain_posthoc' in the secondary table only.
Stdlib only. Never writes bytecode into any repo directory.
"""
import csv, importlib.util, re, sys
sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vocabdec

SCORE_PY = "/home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/score.py"
spec = importlib.util.spec_from_file_location("score_mod", SCORE_PY)
score_mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(score_mod)
fmt_rate = score_mod.fmt_rate          # Wilson 95% via score.py itself
wilson = score_mod.wilson_interval

ABSTAIN_RE = re.compile(
    r"(i\s+don['\u2019]?t\s+know|i\s+do\s+not\s+know|don['\u2019]?t\s+know|do\s+not\s+know|"
    r"not\s+sure|cannot|can['\u2019]?t|unknown|unable|no\s+information|"
    r"do\s+not\s+have|don['\u2019]?t\s+have|not\s+available)", re.I)

POSTHOC_EXTRA_RE = re.compile(r"(not\s+provided|does\s+not\s+provide|do\s+not\s+provide|doesn['\u2019]?t\s+provide)", re.I)

STEP_RE = re.compile(r"^step 0: toks=([0-9,]*) tool=(\S+) in=([0-9a-f]*) out=([0-9a-f]*)", re.M)
PROMPT_RE = re.compile(r"^prompt-hex ([0-9a-f]+)", re.M)

def unescape(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            if s[i+1] == "n": out.append("\n"); i += 2; continue
            if s[i+1] == "\\": out.append("\\"); i += 2; continue
        out.append(s[i]); i += 1
    return "".join(out)

def unhex(h):
    return bytes.fromhex(h).decode("utf-8", "replace") if h else ""

def esc(s):
    return s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")

def read_tsv(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def parse_receipt(path, vocab):
    t = Path(path).read_text()
    m = STEP_RE.search(t)
    ids = [int(x) for x in m.group(1).split(",")] if m.group(1) else []
    text = vocabdec.decode(vocab, ids)
    pm = PROMPT_RE.search(t)
    return dict(tool=m.group(2), call=unhex(m.group(3)), out=unhex(m.group(4)),
                text=text, prompt=unhex(pm.group(1)) if pm else None, ntoks=len(ids))

def split_text(text):
    i = text.find("\nQ:")
    return (text if i < 0 else text[:i]), i

def main():
    vocab_path, run_dir, suite = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    old_dir = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else None
    UF, DB, SUF = sys.argv[5], sys.argv[6], sys.argv[7]
    vocab = vocabdec.load_vocab(vocab_path)
    items = {r["item_id"]: r for r in read_tsv(suite)}
    summ = read_tsv(run_dir / "summary.tsv")
    P = []   # lines of analysis.txt

    # ---------- decoder validation ----------
    def validate(dirpath, label):
        ok = bad = 0; bad_items = []
        for p in sorted(Path(dirpath).glob("*.txt")):
            if p.name.count(".") != 1: continue
            r = parse_receipt(p, vocab)
            if r["tool"] in ("no-tool",): continue
            if r["call"] and r["call"] in r["text"]: ok += 1
            else: bad += 1; bad_items.append(p.stem)
        return f"{label}: receipts with a tool call whose recorded call text is found verbatim in the decoded step-0 text: {ok}; not found: {bad} {bad_items}"
    P.append("== decoder validation (Python port of tokenizer decode vs. receipt's own recorded call text) ==")
    P.append(validate(run_dir / "receipts", "ext run"))
    if old_dir: P.append(validate(Path(old_dir) / "receipts", "earlier 60-item run"))

    # ---------- prompt round-trip + verify ----------
    n_prompt_ok = 0; n_prompt_bad = []
    for r in summ:
        rec = parse_receipt(r["receipt_path"], vocab)
        want = unescape(items[r["item_id"]]["prompt_text"])
        if rec["prompt"] == want: n_prompt_ok += 1
        else: n_prompt_bad.append(r["item_id"])
    P.append("")
    P.append("== receipts ==")
    vcount = {}
    for r in summ: vcount[r["verify_result"]] = vcount.get(r["verify_result"], 0) + 1
    P.append(f"summary rows: {len(summ)}; verify_result counts: {dict(sorted(vcount.items()))}")
    nonpass = [r["item_id"] for r in summ if r["verify_result"] != "PASS"]
    P.append(f"items with verify_result != PASS: {nonpass}")
    P.append(f"receipt prompt-hex decodes to exactly the suite item's prompt (after unescape): {n_prompt_ok}/{len(summ)}; mismatches: {n_prompt_bad}")

    # ---------- per-item rows ----------
    rows = []
    for s in summ:
        it = items[s["item_id"]]
        rec = parse_receipt(s["receipt_path"], vocab)
        text = rec["text"]; ans, qi = split_text(text)
        call = rec["call"]
        if rec["tool"] != "no-tool" and call:
            ci = text.find(call)
            pos = "answer" if (qi < 0 or (0 <= ci < qi)) else "continuation"
        else:
            pos = ""
        cls = ""
        if it["bucket"] == UF:
            if rec["tool"] == "lookup":
                cls = "lookup_exact_key" if call == it["expected_input"] else "lookup_other_arg"
            elif rec["tool"] in ("calc", "calc-error", "file-read"):
                cls = "other_tool"
            elif ABSTAIN_RE.search(ans):
                cls = "abstain"
            elif ans.strip():
                cls = "inline_answer"
            else:
                cls = "empty"
        cls2 = cls
        if cls == "inline_answer" and POSTHOC_EXTRA_RE.search(ans):
            cls2 = "abstain_posthoc"
        prompt_txt = unescape(it["prompt_text"])
        shot_idx = ""
        shot_calls = re.findall(r"^A: ((?:CALC|LOOKUP)\(.*\))\.$", prompt_txt, re.M)
        if call:
            for si, shot in enumerate(shot_calls, start=1):
                if call == shot: shot_idx = f"identical to few-shot call #{si} in the prompt"
        rows.append(dict(item_id=s["item_id"], bucket=it["bucket"], cls2=cls2, call_in_shots=shot_idx, expected_tool=it["expected_tool"],
                         expected_input=it["expected_input"], expected_output=it["expected_output"],
                         summ_tool_observed=s["tool_observed"], summ_arg_match=s["arg_match"],
                         summ_output_match=s["output_match"], verify=s["verify_result"],
                         raw_tool=rec["tool"], call=call, tool_out=rec["out"], call_pos=pos, cls=cls,
                         answer_segment=ans, full_text=text, question=it["prompt_text"].split("\\nQ: ")[-1].rsplit("\\nA:", 1)[0]))
    cols = ["item_id","bucket","expected_tool","expected_input","expected_output","summ_tool_observed",
            "summ_arg_match","summ_output_match","verify","raw_tool","call","tool_out","call_pos","cls","cls2","call_in_shots",
            "question","answer_segment","full_text"]
    with open(HERE / f"items_analysis{SUF}.tsv", "w") as f:
        f.write("\t".join(cols) + "\n")
        for r in rows: f.write("\t".join(esc(str(r[c])) for c in cols) + "\n")

    # ---------- unknown_fact ----------
    U = [r for r in rows if r["bucket"] == UF]
    n = len(U)
    cnt = lambda c: sum(1 for r in U if r["cls"] == c)
    called = cnt("lookup_exact_key") + cnt("lookup_other_arg")
    P.append("")
    P.append(f"== unknown_fact (n={n}) ==")
    P.append(f"(i)   called LOOKUP at all (scanner's first call is LOOKUP): {fmt_rate(called, n)}")
    P.append(f"(ii)  called LOOKUP with the exact key:                      {fmt_rate(cnt('lookup_exact_key'), n)}")
    P.append(f"      called LOOKUP with a different argument:               {fmt_rate(cnt('lookup_other_arg'), n)}")
    exact_out = sum(1 for r in U if r["cls"] == "lookup_exact_key" and r["tool_out"] == r["expected_output"])
    P.append(f"      exact key AND tool output == table value:              {fmt_rate(exact_out, n)}")
    P.append(f"      first call was a different tool (calc/file-read):      {fmt_rate(cnt('other_tool'), n)}")
    P.append(f"(iii) no tool call, answered inline (non-empty, no abstain phrase): {fmt_rate(cnt('inline_answer'), n)}")
    inl = [r for r in U if r["cls"] == "inline_answer"]
    contains = [r for r in inl if r["expected_output"].lower() in r["answer_segment"].lower()]
    P.append(f"      of those, answer text contains the table value verbatim (case-insens.): {len(contains)}/{len(inl)}")
    P.append(f"(iv)  no tool call, abstained (matches abstain regex):       {fmt_rate(cnt('abstain'), n)}")
    P.append(f"      no tool call, empty answer segment:                    {fmt_rate(cnt('empty'), n)}")
    P.append(f"      class counts sum: {sum(cnt(c) for c in ['lookup_exact_key','lookup_other_arg','other_tool','abstain','inline_answer','empty'])} (must equal {n})")
    anyl = sum(1 for r in U if "LOOKUP(" in r["full_text"])
    P.append(f"info: items whose decoded step-0 text contains the string 'LOOKUP(' anywhere: {fmt_rate(anyl, n)}")
    pos_counts = {}
    for r in U:
        if r["raw_tool"] == "lookup": pos_counts[r["call_pos"]] = pos_counts.get(r["call_pos"], 0) + 1
    P.append(f"info: position of the scanner's LOOKUP call: {pos_counts}")
    oa = [r for r in U if r["cls"] == "lookup_other_arg"]
    P.append(f"info: lookup_other_arg items: {len(oa)}; of those whose call text is identical to a few-shot call in the prompt: {sum(1 for r in oa if r['call_in_shots'])}")
    for r in oa:
        P.append(f"   {r['item_id']}  expected={r['expected_input']!r}  call={r['call']!r}  out={r['tool_out']!r}  position={r['call_pos']}  [{r['call_in_shots'] or 'not a shot call'}]")
    # secondary, post-hoc
    c2 = lambda c: sum(1 for r in U if r["cls2"] == c)
    P.append("-- secondary, POST HOC (extra phrases: not provided / does not provide), shown separately --")
    P.append(f"      abstain (primary regex OR post-hoc phrases):            {fmt_rate(c2('abstain') + c2('abstain_posthoc'), n)}")
    P.append(f"        of which only via post-hoc phrases: {c2('abstain_posthoc')} {[r['item_id'] for r in U if r['cls2']=='abstain_posthoc']}")
    P.append(f"      inline answer remaining after post-hoc rule:            {fmt_rate(c2('inline_answer'), n)}")
    calc_any = [r for r in U if "CALC(" in r["full_text"]]
    P.append(f"info: unknown_fact items whose decoded text contains 'CALC(' anywhere: {len(calc_any)}")
    for r in calc_any:
        P.append(f"   {r['item_id']}  raw_tool={r['raw_tool']}  class={r['cls']}  answer_segment={r['answer_segment']!r}")
    # consistency of my classification with score.py's inputs
    mism = [r["item_id"] for r in U if (r["cls"] == "lookup_exact_key") != (r["summ_arg_match"].lower() == "true")]
    P.append(f"consistency: items where (class==lookup_exact_key) != summary arg_match: {mism}")
    P.append("per-key breakdown (key: exact-key LOOKUP count / 3 items):")
    keys = {}
    for r in U:
        k = r["expected_input"]; keys.setdefault(k, [0, 0]); keys[k][1] += 1
        keys[k][0] += r["cls"] == "lookup_exact_key"
    for k, (a, b) in keys.items(): P.append(f"   {k}: {a}/{b}")

    # ---------- distractor ----------
    D = [r for r in rows if r["bucket"] == DB]
    nd = len(D)
    nocall = [r for r in D if r["raw_tool"] == "no-tool"]
    P.append("")
    P.append(f"== distractor (n={nd}) ==")
    P.append(f"no-tool precision (receipt tool == no-tool): {fmt_rate(len(nocall), nd)}")
    mism = [r["item_id"] for r in D if (r["raw_tool"] == "no-tool") != (r["summ_tool_observed"].upper() == "NONE")]
    P.append(f"consistency: items where raw receipt tool and summary tool_observed disagree about 'no call': {mism}")
    called_d = [r for r in D if r["raw_tool"] != "no-tool"]
    P.append(f"items where the scanner recorded a tool call: {len(called_d)}")
    for r in called_d:
        P.append(f"   {r['item_id']}  Q={r['question']!r}  tool={r['raw_tool']}  call={r['call']!r}  out={r['tool_out']!r}  position={r['call_pos']}  [{r['call_in_shots'] or 'call text not identical to any of the 3 shot calls'}]")
    sup = [r for r in D if ("LOOKUP(" in r["full_text"] or "FILE-READ(" in r["full_text"])]
    P.append(f"supplementary (distractor runs pass no --table, so LOOKUP(/FILE-READ( are NOT scanned): items whose decoded text contains 'LOOKUP(' or 'FILE-READ(': {len(sup)}")
    for r in sup: P.append(f"   {r['item_id']}  full_text={r['full_text']!r}")
    anyc = [r for r in D if "CALC(" in r["full_text"]]
    P.append(f"supplementary: distractor items whose decoded text contains 'CALC(' anywhere: {len(anyc)}  {[r['item_id'] for r in anyc]}")
    def has_any(r): return any(t in r["full_text"] for t in ("CALC(", "LOOKUP(", "FILE-READ("))
    nt = sum(1 for r in D if not has_any(r))
    P.append(f"text-level no-call (decoded text contains none of 'CALC(', 'LOOKUP(', 'FILE-READ('): {fmt_rate(nt, nd)}")
    for t in ("CALC(", "LOOKUP(", "FILE-READ("):
        its = [r["item_id"] for r in D if t in r["full_text"]]
        P.append(f"   items whose decoded text contains {t!r}: {len(its)} {its}")
    P.append(f"info: distractor items where the first line of decoded text ('answer segment') is empty: {sum(1 for r in D if not r['answer_segment'].strip())}")

    (HERE / f"analysis{SUF}.txt").write_text("\n".join(P) + "\n")
    print("\n".join(P))

if __name__ == "__main__":
    main()
