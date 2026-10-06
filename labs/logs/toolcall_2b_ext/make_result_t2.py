#!/usr/bin/env python3
"""make_result_t2.py - assemble RESULT_T2.md. Every number is computed from files produced by the runs:
run/ and run_t2/ (summary.tsv, RUN.txt, receipts), items_analysis.tsv (T1), items_analysis_t2.tsv (T2),
analysis*.txt, SCORE*.txt, ext_suite*.tsv."""
import csv, hashlib, importlib.util, re, sys
sys.dont_write_bytecode = True
from pathlib import Path
H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("score_mod", "/home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/score.py")
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tsv(p):
    with open(p, newline="") as f: return list(csv.DictReader(f, delimiter="\t"))
def unesc(s): return s.replace("\\t", "\t").replace("\\n", "\n").replace("\\\\", "\\")
def rate(k, n):
    lo, hi = sm.wilson_interval(k, n)
    return f"{k}/{n}", f"{k/n:.2%}", f"{lo:.2%}-{hi:.2%}"
def full(k, n):
    a, b, c = rate(k, n); return f"{a} = {b} (95% CI {c})"
def overlap(k1, k2, n):
    a = sm.wilson_interval(k1, n); b = sm.wilson_interval(k2, n)
    return "overlap" if (a[0] <= b[1] and b[0] <= a[1]) else "do not overlap"
def md(s): return s.replace("|", "\\|").replace("\n", " ")
def q(s, n=110, table=False):
    s = s.replace("\n", " ").strip()
    s = s if len(s) <= n else s[:n] + "..."
    s = s.replace("`", "'")
    if table: s = s.replace("|", "\\|")
    return "`" + s + "`"
def tbl(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for b in body: out.append("| " + " | ".join(b) + " |")
    return "\n".join(out)

def load(path):
    rows = tsv(path)
    for r in rows:
        for c in ("answer_segment", "full_text", "question", "call", "tool_out", "expected_output"):
            r[c] = unesc(r[c])
    return rows

R1 = load(H / "items_analysis.tsv"); R2 = load(H / "items_analysis_t2.tsv")
U1 = [r for r in R1 if r["bucket"] == "unknown_fact"]; D1 = [r for r in R1 if r["bucket"] == "distractor"]
U2 = [r for r in R2 if r["bucket"] == "unknown_fact_t2"]; D2 = [r for r in R2 if r["bucket"] == "distractor_t2"]
nU, nD = len(U2), len(D2)
assert (len(U1), len(D1), nU, nD) == (30, 30, 30, 30)
run2 = {}
for line in (H / "run_t2/RUN.txt").read_text().splitlines():
    k, _, v = line.partition(" "); run2[k] = v
run1 = {}
for line in (H / "run/RUN.txt").read_text().splitlines():
    k, _, v = line.partition(" "); run1[k] = v
suite2 = sha(H / "ext_suite_t2.tsv"); suite1 = sha(H / "ext_suite.tsv")
table_sha = sha("/home/user/aefinity-ai/alice-aegis/demo/agent-trace/tables/demo.tsv")
assert suite2 == run2["suite-sha256"] and table_sha == run2["table-sha256"] and suite1 == run1["suite-sha256"]
for k in ("model-sha256", "embed-sha256", "vocab-sha256", "binary-sha256", "N"): assert run1[k] == run2[k], k
n_pass = sum(1 for r in R2 if r["verify"] == "PASS"); nonpass = [r["item_id"] for r in R2 if r["verify"] != "PASS"]
commits = sorted({m for p in (H/"run_t2/receipts").glob("*.txt") for m in re.findall(r"^commit (\S+)", p.read_text(), re.M)})
hosts = sorted({m for p in (H/"run_t2/receipts").glob("*.txt") for m in re.findall(r"^host (\S+)", p.read_text(), re.M)})
score_txt = (H / "SCORE_T2.txt").read_text().rstrip("\n")
analysis2 = (H / "analysis_t2.txt").read_text()

# regression check of the generalised analysis script on T1 data
a_old = (H / "analysis.txt").read_text().splitlines(); a_new = (H / "analysis_t1regress.txt").read_text().splitlines()
removed = [l for l in a_old if l not in a_new]; added = [l for l in a_new if l not in a_old]
same_items = (H / "items_analysis.tsv").read_bytes() == (H / "items_analysis_t1regress.tsv").read_bytes()
assert not removed and same_items

cnt1 = lambda c: sum(1 for r in U1 if r["cls"] == c); cnt2 = lambda c: sum(1 for r in U2 if r["cls"] == c)
c2p = lambda c: sum(1 for r in U2 if r["cls2"] == c)
exact1, exact2 = cnt1("lookup_exact_key"), cnt2("lookup_exact_key")
called1, called2 = exact1 + cnt1("lookup_other_arg"), exact2 + cnt2("lookup_other_arg")
exact_out2 = sum(1 for r in U2 if r["cls"] == "lookup_exact_key" and r["tool_out"] == r["expected_output"])
inl2 = [r for r in U2 if r["cls"] == "inline_answer"]
inl_has2 = [r for r in inl2 if r["expected_output"].lower() in r["answer_segment"].lower()]
# observed-after-reading, mechanical: no-tool but text begins with LOOKUP(<expected key>
def key_of(r): return r["expected_input"][len("LOOKUP("):-1]
def attempt(r): return r["raw_tool"] == "no-tool" and r["full_text"].strip().startswith("LOOKUP(" + key_of(r))
att2 = [r for r in U2 if attempt(r)]; att1 = [r for r in U1 if attempt(r)]
begins = lambda rows: sum(1 for r in rows if r["full_text"].strip().startswith("LOOKUP(" + key_of(r)))
any_lookup = lambda rows: sum(1 for r in rows if "LOOKUP(" in r["full_text"])
d_scan1 = sum(1 for r in D1 if r["raw_tool"] == "no-tool"); d_scan2 = sum(1 for r in D2 if r["raw_tool"] == "no-tool")
has_any = lambda r: any(t in r["full_text"] for t in ("CALC(", "LOOKUP(", "FILE-READ("))
d_text1 = sum(1 for r in D1 if not has_any(r)); d_text2 = sum(1 for r in D2 if not has_any(r))
d_lk1 = sum(1 for r in D1 if ("LOOKUP(" in r["full_text"] or "FILE-READ(" in r["full_text"])); d_lk2 = sum(1 for r in D2 if ("LOOKUP(" in r["full_text"] or "FILE-READ(" in r["full_text"]))
d_calc1 = sum(1 for r in D1 if "CALC(" in r["full_text"]); d_calc2 = sum(1 for r in D2 if "CALC(" in r["full_text"])
vnew = re.search(r"ext run: receipts with a tool call whose recorded call text is found verbatim in the decoded step-0 text: (\d+); not found: (\d+)", analysis2)
vold = re.search(r"earlier 60-item run: receipts with a tool call whose recorded call text is found verbatim in the decoded step-0 text: (\d+); not found: (\d+)", analysis2)
pr = re.search(r"receipt prompt-hex decodes to exactly the suite item's prompt \(after unescape\): (\d+)/(\d+)", analysis2)

# shot keys per item (from the suite file itself)
S2 = tsv(H / "ext_suite_t2.tsv")
def shots_of(prompt): return re.findall(r"^Q: part (\S+)\nA: LOOKUP\(\1\)\.$", prompt, re.M)
shot_rows = []
for r in S2:
    p = unesc(r["prompt_text"]); sh = shots_of(p)[:2]
    shot_rows.append((r["item_id"], r["bucket"], r["expected_input"], sh))
for iid, b, e, sh in shot_rows:
    assert len(sh) == 2
    if e: assert e[len("LOOKUP("):-1] not in sh
default_items = [x for x in shot_rows if x[3] == ["P-100", "P-101"]]; alt_items = [x for x in shot_rows if x[3] == ["P-402", "P-403"]]
assert len(default_items) + len(alt_items) == 60
alt_ids = [x[0] for x in alt_items]
Uid = {r["item_id"]: r for r in U2}
ex_default = sum(1 for x in default_items if x[1] == "unknown_fact_t2" and Uid[x[0]]["cls"] == "lookup_exact_key")
n_default_u = sum(1 for x in default_items if x[1] == "unknown_fact_t2")
ex_alt = sum(1 for x in alt_items if x[1] == "unknown_fact_t2" and Uid[x[0]]["cls"] == "lookup_exact_key")
n_alt_u = sum(1 for x in alt_items if x[1] == "unknown_fact_t2")
keys = []
for r in U2:
    if r["expected_input"] not in keys: keys.append(r["expected_input"])

L = []; A = L.append
A("# T2 control for the extended tool-call eval: `unknown_fact_t2` and `distractor_t2` (2B ternary model)\n")
A("Status: MEASURED (one run, 60 items, K=1, N=24). Control for `RESULT.md`: the same 30 questions and 30 distractors, re-rendered under template T2 (LOOKUP shots on other keys) instead of T1 (CALC-only shots). "
  "Nothing was committed or pushed and no tracked file in `alice-aegis` was modified. All outputs are under "
  f"`{H}/` (run outputs in `run_t2/`; the T1 run in `run/`).\n")

A("## Headline\n")
A(f"- **unknown_fact_t2, exact-key LOOKUP rate:** {full(exact2, nU)}. (Any LOOKUP call at all: {rate(called2, nU)[0]}; exact output == table value: {rate(exact_out2, nU)[0]}.)")
A(f"- **distractor_t2, no-tool precision (scanner, `score.py`):** {full(d_scan2, nD)}. Text-level check (decoded text contains none of `CALC(`, `LOOKUP(`, `FILE-READ(`): {full(d_text2, nD)}.")
A(f"- **Receipts verified:** {n_pass}/{len(R2)} `verify_result` = PASS" + ("" if not nonpass else f"; not PASS: {nonpass}") + ".")
A(f"- **The {nU - exact2} unknown_fact_t2 items without a recorded LOOKUP call:** {rate(cnt2('inline_answer'), nU)[0]} by the fixed rules are `inline_answer` and {rate(cnt2('abstain'), nU)[0]} `abstain`; {len(att2)} of those {cnt2('inline_answer')} begin with `LOOKUP(<expected key>, ...)` carrying an extra argument that the scanner's key grammar rejects, so they are not recorded as calls (details below).")
A(f"- **T1 vs T2 (paired, same questions):** exact-key LOOKUP {rate(exact1, nU)[0]} (T1) vs {rate(exact2, nU)[0]} (T2); distractor no-tool precision {rate(d_scan1, nD)[0]} (T1) vs {rate(d_scan2, nD)[0]} (T2). Full table below.\n")

A("## Comparison: T1 (CALC-only shots) vs T2 (LOOKUP shots on other keys)\n")
A("Same 30 questions and keys in `unknown_fact` / `unknown_fact_t2`, same 30 distractor questions in `distractor` / `distractor_ext` -> `distractor_t2`. Same model, embed, vocab, binary, N and runner. "
  "T1 numbers are recomputed from `items_analysis.tsv` (the T1 run); T2 numbers from `items_analysis_t2.tsv`. 95% CI = Wilson, via `score.py`'s function.\n")
rows = [
 ["unknown_fact", "exact-key LOOKUP (scanner / `score.py` correct-arg)", full(exact1, nU), full(exact2, nU), overlap(exact1, exact2, nU)],
 ["unknown_fact", "any LOOKUP call (scanner)", full(called1, nU), full(called2, nU), overlap(called1, called2, nU)],
 ["unknown_fact", "no call, inline answer (primary rule)", full(cnt1("inline_answer"), nU), full(cnt2("inline_answer"), nU), overlap(cnt1("inline_answer"), cnt2("inline_answer"), nU)],
 ["unknown_fact", "no call, abstain (primary phrase list)", full(cnt1("abstain"), nU), full(cnt2("abstain"), nU), overlap(cnt1("abstain"), cnt2("abstain"), nU)],
 ["unknown_fact", "first scanned call is another tool", full(cnt1("other_tool"), nU), full(cnt2("other_tool"), nU), overlap(cnt1("other_tool"), cnt2("other_tool"), nU)],
 ["unknown_fact", "decoded text begins `LOOKUP(<expected key>` (text-level, any scanner outcome)", full(begins(U1), nU), full(begins(U2), nU), overlap(begins(U1), begins(U2), nU)],
 ["unknown_fact", "string `LOOKUP(` anywhere in decoded text", full(any_lookup(U1), nU), full(any_lookup(U2), nU), overlap(any_lookup(U1), any_lookup(U2), nU)],
 ["distractor", "no-tool precision (scanner / `score.py`)", full(d_scan1, nD), full(d_scan2, nD), overlap(d_scan1, d_scan2, nD)],
 ["distractor", "text-level no-call (none of `CALC(`/`LOOKUP(`/`FILE-READ(` in decoded text)", full(d_text1, nD), full(d_text2, nD), overlap(d_text1, d_text2, nD)],
 ["distractor", "string `LOOKUP(` or `FILE-READ(` in decoded text", full(d_lk1, nD), full(d_lk2, nD), overlap(d_lk1, d_lk2, nD)],
 ["distractor", "string `CALC(` in decoded text", full(d_calc1, nD), full(d_calc2, nD), overlap(d_calc1, d_calc2, nD)],
]
A(tbl(["bucket", "metric", "T1 (k/n, rate, CI)", "T2 (k/n, rate, CI)", "T1 vs T2 intervals"], [[a, md(b), c, d, e] for a, b, c, d, e in rows]))
A("")
A("Paired view for `unknown_fact` (rows: T1 class of the item, columns: T2 class of the same question and key; primary rules):\n")
order = ["lookup_exact_key", "lookup_other_arg", "other_tool", "abstain", "inline_answer", "empty"]
t2by = {r["item_id"].replace("unknown_fact_t2_", ""): r for r in U2}
ct = {(a, b): 0 for a in order for b in order}
for r in U1:
    ct[(r["cls"], t2by[r["item_id"].replace("unknown_fact_", "")]["cls"])] += 1
A(tbl(["T1 class \\ T2 class"] + order, [[a] + [str(ct[(a, b)]) for b in order] for a in order]))
A("")
A("What the comparison does and does not show: T1 and T2 differ in more than the tool being demonstrated (three CALC shots vs two LOOKUP shots, a different number of shot lines, and 6 items use a different shot pair, see Setup). Each item is one deterministic run, so the interval statements are about these 30 prompts per cell, which share 10 keys and 10 phrasings. "
  "The table reports counts, not a causal attribution.\n")

A("## Setup\n")
A(tbl(["item", "value"], [
    ["suite file", f"`{H}/ext_suite_t2.tsv`"],
    ["suite sha256", f"`{suite2}`"],
    ["T1 suite sha256 (for reference)", f"`{suite1}`"],
    ["lookup table", "`demo/agent-trace/tables/demo.tsv` (10 keys), unchanged"],
    ["table sha256", f"`{table_sha}`"],
    ["model sha256 (MODEL.SAF)", f"`{run2['model-sha256']}`"],
    ["embed sha256 (EMBED.BIN)", f"`{run2['embed-sha256']}`"],
    ["vocab sha256 (VOCAB.BIN)", f"`{run2['vocab-sha256']}`"],
    ["agent_trace binary sha256", f"`{run2['binary-sha256']}`"],
    ["build commit recorded in receipts", ", ".join(f"`{c}`" for c in commits)],
    ["host recorded in receipts", ", ".join(hosts)],
    ["prompt template", "`T2` for every item (`prompt_template_id` column): `Q: part <shot1> / A: LOOKUP(<shot1>). / Q: part <shot2> / A: LOOKUP(<shot2>). / Q: <question> / A:` -- see shot keys below"],
    ["`template` line in RUN.txt", f"`{run2['template']}` -- this is the runner's `--template` switch (T1 = prompts used as written, T3 = unclosed-opener ablation), not the suite's prompt template; it was not set, so prompts were used as written"],
    ["K / N", f"1 / {run2['N']}"],
    ["items", f"{len(R2)} = {nU} unknown_fact_t2 + {nD} distractor_t2"],
    ["run start (UTC, from RUN.txt)", run2["start-utc"]],
    ["generator", f"`gen_suite_ext_t2.py` sha256 `{sha(H/'gen_suite_ext_t2.py')}` (imports `gen_suite_ext.py`)"],
    ["analysis script", f"`analyze_ext2.py` sha256 `{sha(H/'analyze_ext2.py')}`"],
]))
A("")
A("Every receipt carries a `suite-sha256` header equal to the suite sha256 above; the 30 `unknown_fact_t2` receipts also carry the table sha256 (the runner passes `--table` only to LOOKUP-expected items). Model, embed, vocab, binary and N are identical to the T1 run's `run/RUN.txt`.\n")

A("## Suite construction and shot keys\n")
A("`gen_suite_ext_t2.py` reads `ext_suite.tsv`, extracts each item's question and key, and re-renders the prompt under T2 with `gen_suite_ext.write_tsv` (same 8 columns and `\\n` escaping as `suite.tsv`). It asserts that every prompt using the original T2 shots is byte-identical to `gen_suite.t2_lookup_prompt(question)`, that every item's own key is not one of its shot keys, and that for `unknown_fact_t2` the key appears exactly once in the prompt (in the final question). No RNG; two runs produce identical output.\n")
A(f"- **`unknown_fact_t2` (n=30):** identical questions and keys to `unknown_fact`; expected tool `LOOKUP`, expected input `LOOKUP(<key>)`, expected output the table value (unchanged from T1). The prompt ends `A:` with no `LOOKUP(` opener.")
A(f"- **`distractor_t2` (n=30):** the same 30 questions as `distractor_ext`; expected `NONE`, empty input and output.")
A(f"- **Shot keys.** The original T2 shots are `P-100` and `P-101`, which are the own keys of 6 `unknown_fact_t2` items. For those 6 items (`{'`, `'.join(i for i in alt_ids)}`) the shots are `P-402` and `P-403` (same wording); for the other {len(default_items)} items (the remaining {n_default_u} unknown_fact_t2 and all {nD} distractor_t2) the shots are exactly `P-100` and `P-101`. The shot keys are table keys; the shots show only call syntax, never table values.")
A("")
A("Shot keys per unknown_fact_t2 item (derived from the prompts in `ext_suite_t2.tsv`):\n")
A(tbl(["item", "own key", "shot keys"], [[f"`{i}`", f"`{e[len('LOOKUP('):-1]}`", ", ".join(f"`{s}`" for s in sh)] for i, b, e, sh in shot_rows if b == "unknown_fact_t2"]))
A("")
A("`distractor_t2` items: shot keys `P-100`, `P-101` for all 30.\n")

A("## Results\n")
A("### Full `score.py` output (unmodified script, `run_t2/summary.tsv`)\n")
A("```\n" + score_txt + "\n```\n")

A("### `unknown_fact_t2` (n=30)\n")
A(tbl(["metric", "k/n", "rate", "Wilson 95% CI"], [
    ["(i) called LOOKUP at all (scanner's first call is LOOKUP)", *rate(called2, nU)],
    ["(ii) called LOOKUP with the exact key", *rate(exact2, nU)],
    ["      ... and tool output == table value", *rate(exact_out2, nU)],
    ["called LOOKUP with a different argument", *rate(cnt2("lookup_other_arg"), nU)],
    ["first scanned call was another tool (calc / file-read)", *rate(cnt2("other_tool"), nU)],
    ["(iii) no tool call, inline answer (non-empty, no abstain phrase)", *rate(cnt2("inline_answer"), nU)],
    ["      of those, answer text contains the table value verbatim", *rate(len(inl_has2), len(inl2))],
    ["(iv) no tool call, abstained (fixed phrase list)", *rate(cnt2("abstain"), nU)],
    ["no tool call, empty answer", *rate(cnt2("empty"), nU)],
]))
A("")
A(f"The classes lookup_exact_key, lookup_other_arg, other_tool, abstain, inline_answer and empty are mutually exclusive and sum to 30. All {called2} scanner-recorded LOOKUP calls are at the start of the decoded text (position `answer`). "
  "Exact-key LOOKUP count per key: " + ", ".join(f"{k[len('LOOKUP('):-1]} {sum(1 for r in U2 if r['expected_input']==k and r['cls']=='lookup_exact_key')}/3" for k in keys) + ". "
  f"By shot pair: {ex_default}/{n_default_u} with shots `P-100`/`P-101`; {ex_alt}/{n_alt_u} with shots `P-402`/`P-403` (the 6 items whose own key is `P-100` or `P-101`).\n")
A("**Classification rules.** The primary rules and the post-hoc rule are the ones from `RESULT.md`, unchanged (`analyze_ext2.py` is a generalised copy of `analyze_ext.py`; the rules were fixed in `analyze_ext.py` before any T2 output existed, and no T2 decoded text was read before `analyze_ext2.py` was final; the only T2 information seen earlier was the runner's per-item `tool_observed` log line for the first 2 items). "
  f"Regression check: running `analyze_ext2.py` on the T1 run reproduces `analysis.txt` with {len(removed)} lines removed and {len(added)} lines added (the added lines are the new informational checks), and `items_analysis.tsv` byte-for-byte ({'identical' if same_items else 'DIFFERENT'}). "
  f"Receipts store token ids, so decoded text is reconstructed with the same Python port of the Rust decoder (`vocabdec.py`); its check passes for {vnew.group(1)} of {int(vnew.group(1))+int(vnew.group(2))} tool-call receipts of this run and {vold.group(1)} of {int(vold.group(1))+int(vold.group(2))} of the earlier 60-item run.\n")
A(f"**Post hoc rule from `RESULT.md`** (`not provided` / `does not provide` / `do not provide` / `doesn't provide`), reported separately: moves {c2p('abstain_posthoc')} items from inline answer to abstain; abstain under primary OR post-hoc phrases = {full(c2p('abstain')+c2p('abstain_posthoc'), nU)}.\n")
A(f"**Observed after reading the T2 decoded texts (mechanical, reported separately; not part of the primary rules):** {len(att2)} items have raw receipt tool `no-tool` but a decoded text that begins with `LOOKUP(<expected key>` followed by something other than `)`: "
  + "; ".join(f"`{r['item_id']}` -> {q(re.search(r'LOOKUP\([^)]*\)', r['full_text']).group(0) if re.search(r'LOOKUP\([^)]*\)', r['full_text']) else r['full_text'][:40], 60)}" for r in att2)
  + f". The scanner's key grammar is `[A-Za-z0-9_.-]{{1,64}}` followed by `)`, so these are not recorded as calls and `score.py` counts them as no call; the primary rules class them `inline_answer`. "
  f"Counting them as text-level LOOKUP attempts, the decoded text begins with `LOOKUP(<expected key>` in {full(begins(U2), nU)} of the items. This figure is a text pattern, not a scanner outcome and not a correctness claim about those attempts.\n")

A("### `distractor_t2` (n=30)\n")
A(tbl(["metric", "k/n", "rate", "Wilson 95% CI"], [
    ["no-tool precision (scanner recorded no call; `score.py`)", *rate(d_scan2, nD)],
    ["text-level no-call (none of `CALC(`, `LOOKUP(`, `FILE-READ(` in decoded text)", *rate(d_text2, nD)],
]))
A("")
A(f"Items where the scanner recorded a tool call: {nD - d_scan2}. `distractor_t2` runs pass no `--table` (the runner adds it only for LOOKUP-expected items), so the scanner looks only for `CALC(`; a `LOOKUP(` or `FILE-READ(` in a distractor's decoded text could not appear as a call in `summary.tsv`. "
  f"That is why the plain-text search is the check that matters for the question \"do LOOKUP shots raise false tool calls\": the strings `LOOKUP(` or `FILE-READ(` appear in {d_lk2} of {nD} distractor_t2 decoded texts, and `CALC(` in {d_calc2} of {nD}. "
  f"(T1 for reference: {d_lk1} and {d_calc1} of {nD}.)\n")

A("### Misses (one line each)\n")
A(f"`unknown_fact_t2`: {nU - exact2} misses under the plan's item-level FAIL rule (expected tool LOOKUP, no LOOKUP call recorded):\n")
lab = {"abstain": "no call; abstain phrase", "inline_answer": "no call; inline answer", "other_tool": "other tool", "empty": "no call; empty"}
body = []
for r in U2:
    if r["cls"] == "lookup_exact_key": continue
    cl = lab.get(r["cls"], r["cls"])
    if r["cls2"] == "abstain_posthoc": cl = "no call; 'not provided' phrase (post hoc abstain)"
    if attempt(r): cl += "; `LOOKUP(` opener with extra argument, rejected by scanner"
    shots = [x for x in shot_rows if x[0] == r["item_id"]][0][3]
    body.append([f"`{r['item_id']}`", f"`{key_of(r)}`", md(r["question"]), ",".join(shots), cl, q(r["full_text"], 100, table=True)])
A(tbl(["item", "key", "question", "shots", "class", "decoded text (first 100 chars)"], body))
A("")
A(f"`distractor_t2`: {nD - d_scan2} misses.\n")

A("## Commands used\n")
A("```bash")
A(f"# 1. build suite (reads ext_suite.tsv; original eval/ tree untouched)\ncd {H}\npython3 -B gen_suite_ext_t2.py ext_suite.tsv ext_suite_t2.tsv\nsha256sum ext_suite_t2.tsv\n")
A("# 2. run (same invocation as the T1 run, different suite and outdir)\n"
  "A=/tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/artifacts/bitnet2b_fixed\n"
  "cd /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval && \\\n"
  "  AEGIS_MODEL=$A/MODEL.SAF AEGIS_EMBED=$A/EMBED.BIN AEGIS_VOCAB=$A/VOCAB.BIN \\\n"
  "  AGENT_TRACE_BIN=/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/agent_trace \\\n"
  f"  ./run_suite.sh {H}/ext_suite_t2.tsv {H}/run_t2 > {H}/run_t2.log 2>&1\n")
A(f"# 3. score (unmodified score.py)\npython3 -B /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/score.py {H}/run_t2/summary.tsv | tee {H}/SCORE_T2.txt\n")
LP = "/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b"
A(f"# 4. decoded-text analysis: T1 regression check, then T2 (writes analysis*.txt, items_analysis*.tsv)\ncd {H}\npython3 -B analyze_ext2.py $A/VOCAB.BIN run ext_suite.tsv {LP} unknown_fact distractor _t1regress > /dev/null\npython3 -B analyze_ext2.py $A/VOCAB.BIN run_t2 ext_suite_t2.tsv {LP} unknown_fact_t2 distractor_t2 _t2 > /dev/null\n")
A(f"# 5. verbatim-argument report (read-only)\npython3 -B /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/check_verbatim.py {H}/run_t2/receipts {H}/run_t2/summary.tsv > {H}/check_verbatim_t2.txt\n")
A("# 6. assemble this file\npython3 -B make_result_t2.py")
A("```\n")

cv = (H / "check_verbatim_t2.txt").read_text()
cvm = re.search(r"receipts=(\d+) tool-calls=(\d+) .*flagged=(\d+)", cv)
A("## Receipts\n")
A(f"`run_t2/summary.tsv` has {len(R2)} rows; `verify_result` is PASS for {n_pass} and not PASS for {len(R2)-n_pass}. `gen` and `verify` stderr files are empty. {pr.group(1)} of {pr.group(2)} receipts' `prompt-hex` decode to exactly their suite item's prompt after unescaping. "
  f"`run_suite.sh` ran `agent_trace verify` (with `--suite-sha256`, and `--table demo.tsv` for unknown_fact_t2 items) on each receipt right after `gen`. `check_verbatim.py`: {cvm.group(2)} tool calls in {cvm.group(1)} receipts, {cvm.group(3)} flagged (every recorded LOOKUP argument appears verbatim in the item's last `Q:` line).\n")

A("## Caveats\n")
cav = [
 "**T1 and T2 differ in several ways at once.** T2 replaces three CALC shots with two LOOKUP shots (different prompt length and content). The comparison table reports counts for the same questions under each prompt; it does not isolate one factor.",
 f"**6 items use a different shot pair** (`P-402`/`P-403` instead of `P-100`/`P-101`) because `P-100` and `P-101` are those items' own keys ({', '.join(alt_ids)}). The shot pair is therefore confounded with key for those 6 items; the by-shot-pair counts above are informational only.",
 "**Only 10 distinct keys**, each used 3 times with 3 phrasings; Wilson intervals treat the 30 items as independent. Greedy decode, one run per item (`verify` PASS for all 60), so each item is a single deterministic outcome for that exact prompt.",
 f"**N={run2['N']} tokens per step.** The scanner and the text classification see only the first {run2['N']} decoded tokens, and only the scanner's earliest call occurrence counts. After the first call, the decoded texts often continue with further `Q:`/`A:` lines (visible in the appendix); those are not scored.",
 "**Distractor runs pass no `--table`** (runner behaviour for non-LOOKUP items): the scanner cannot record a LOOKUP call there. The distractor result therefore rests on the plain-text check for `LOOKUP(`/`FILE-READ(`/`CALC(` in addition to `score.py`'s scanner-based figure; both are reported.",
 "**Four unknown_fact_t2 items carry an extra argument** inside `LOOKUP(...)` and are scored as no call by the scanner. The primary rules label them `inline_answer`; that label is a consequence of the fixed rule (no call, no abstain phrase), not a statement that they answer inline. The text-level figure is given separately and is not a scanner outcome.",
 "**Abstain / inline classification is a phrase heuristic** over reconstructed text; the post-hoc phrase list is the one from `RESULT.md` and is reported separately. No further post-hoc phrases were added for T2.",
 "**`arg_match` / `output_match` for NONE-expected items are not meaningful** (the runner's tab-IFS `read` collapses the empty expected fields; same artifact as in the T1 run). `score.py` does not use them for the distractor bucket.",
 "**Distractor answer correctness was not scored**; the metric is tool-call emission only.",
 "**Scope.** One model, one host, one run per template. No timing or throughput numbers are reported (Rule A; the harness's `run_t2/timing.tsv` is a byproduct and is not used). No claim about tool use beyond these fixed prompts.",
]
for i, c in enumerate(cav, 1): A(f"{i}. {c}")
A("")

A("## Files (all in the output directory)\n")
A("- `ext_suite_t2.tsv`, `gen_suite_ext_t2.py`, `analyze_ext2.py`, `make_result_t2.py`, `vocabdec.py` (shared)")
A("- `run_t2/` (`RUN.txt`, `summary.tsv`, `timing.tsv`, `prompts/`, `receipts/`), `run_t2.log`, `SCORE_T2.txt`, `analysis_t2.txt`, `items_analysis_t2.tsv`, `check_verbatim_t2.txt`")
A("- T1 regression-check outputs of the generalised analysis script: `analysis_t1regress.txt`, `items_analysis_t1regress.tsv` (compare with `analysis.txt`, `items_analysis.tsv`)\n")

A("## Appendix: per-item decoded texts\n")
A("`unknown_fact_t2` (all 30; text is the first 110 chars of the reconstructed decoded text; tool is the receipt's raw tool):\n")
A(tbl(["item", "key", "tool", "class", "decoded text"], [[f"`{r['item_id']}`", f"`{key_of(r)}`", r["raw_tool"], r["cls"], q(r["full_text"], 110, table=True)] for r in U2]))
A("")
A("`distractor_t2` (all 30):\n")
A(tbl(["item", "question", "tool", "decoded text"], [[f"`{r['item_id']}`", md(r["question"]), r["raw_tool"], q(r["full_text"], 110, table=True)] for r in D2]))
A("")
(H / "RESULT_T2.md").write_text("\n".join(L))
print("wrote", H / "RESULT_T2.md")
