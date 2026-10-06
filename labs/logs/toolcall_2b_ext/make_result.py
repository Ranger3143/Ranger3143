#!/usr/bin/env python3
"""make_result.py - assemble RESULT.md from files produced by the run (Rule B: every number
comes from run/summary.tsv, run/RUN.txt, run/receipts/*, SCORE.txt, items_analysis.tsv, analysis.txt)."""
import csv, hashlib, importlib.util, re, sys
sys.dont_write_bytecode = True
from pathlib import Path
H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("score_mod", "/home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/score.py")
sm = importlib.util.module_from_spec(spec); spec.loader.exec_module(sm)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tsv(p):
    with open(p, newline="") as f: return list(csv.DictReader(f, delimiter="\t"))
def unesc(s):
    return s.replace("\\t", "\t").replace("\\n", "\n").replace("\\\\", "\\")
def rate(k, n):
    lo, hi = sm.wilson_interval(k, n)
    return f"{k}/{n}", f"{k/n:.2%}", f"{lo:.2%}-{hi:.2%}"
def md(s): return s.replace("|", "\\|").replace("\n", " ")
def q(s, n=110, table=False):
    s = s.replace("\n", " ").strip()
    s = s if len(s) <= n else s[:n] + "..."
    s = s.replace("`", "'")
    if table: s = s.replace("|", "\\|")
    return "`" + s + "`"

run = {}
for line in (H / "run/RUN.txt").read_text().splitlines():
    k, _, v = line.partition(" "); run[k] = v
rows = tsv(H / "items_analysis.tsv")
for r in rows:
    for c in ("answer_segment", "full_text", "question", "call", "tool_out", "expected_output"):
        r[c] = unesc(r[c])
U = [r for r in rows if r["bucket"] == "unknown_fact"]
D = [r for r in rows if r["bucket"] == "distractor"]
nU, nD = len(U), len(D)
cnt = lambda c: sum(1 for r in U if r["cls"] == c)
cnt2 = lambda c: sum(1 for r in U if r["cls2"] == c)
n_pass = sum(1 for r in rows if r["verify"] == "PASS")
nonpass = [r["item_id"] for r in rows if r["verify"] != "PASS"]
commits = sorted({m for p in (H/"run/receipts").glob("*.txt") for m in re.findall(r"^commit (\S+)", p.read_text(), re.M)})
hosts = sorted({m for p in (H/"run/receipts").glob("*.txt") for m in re.findall(r"^host (\S+)", p.read_text(), re.M)})
suite_sha = sha(H / "ext_suite.tsv"); table_sha = sha("/home/user/aefinity-ai/alice-aegis/demo/agent-trace/tables/demo.tsv")
assert suite_sha == run["suite-sha256"] and table_sha == run["table-sha256"]
score_txt = (H / "SCORE.txt").read_text().rstrip("\n")
analysis = (H / "analysis.txt").read_text()
calls_d = [r for r in D if r["raw_tool"] != "no-tool"]
exact = cnt("lookup_exact_key"); called = exact + cnt("lookup_other_arg")
exact_out = sum(1 for r in U if r["cls"] == "lookup_exact_key" and r["tool_out"] == r["expected_output"])
inl = [r for r in U if r["cls"] == "inline_answer"]
inl_has = [r for r in inl if r["expected_output"].lower() in r["answer_segment"].lower()]
n_lookup_any = sum(1 for r in U if "LOOKUP(" in r["full_text"])
n_sup_d = sum(1 for r in D if ("LOOKUP(" in r["full_text"] or "FILE-READ(" in r["full_text"]))
v_old = re.search(r"earlier 60-item run: receipts with a tool call whose recorded call text is found verbatim in the decoded step-0 text: (\d+); not found: (\d+)", analysis)
v_new = re.search(r"ext run: receipts with a tool call whose recorded call text is found verbatim in the decoded step-0 text: (\d+); not found: (\d+)", analysis)
pr = re.search(r"receipt prompt-hex decodes to exactly the suite item's prompt \(after unescape\): (\d+)/(\d+)", analysis)
keys = []
for r in U:
    if r["expected_input"] not in keys: keys.append(r["expected_input"])

def tbl(header, body):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for b in body: out.append("| " + " | ".join(b) + " |")
    return "\n".join(out)

L = []
A = L.append
A("# Extended tool-call eval: `unknown_fact` and `distractor` buckets (2B ternary model, template T1)\n")
A("Status: MEASURED (one run, 60 items, K=1, N=24). Extension of the pre-registered 60-item tool-call eval; "
  "nothing was committed or pushed and no tracked file in `alice-aegis` was modified. All outputs are under "
  f"`{H}/`.\n")

A("## Headline\n")
e = rate(exact, nU); d = rate(sum(1 for r in D if r['raw_tool'] == 'no-tool'), nD)
A(f"- **unknown_fact, exact-key LOOKUP rate:** {e[0]} = {e[1]} (Wilson 95% CI {e[2]}). "
  f"(Any LOOKUP call at all: {rate(called, nU)[0]}.)")
A(f"- **distractor, no-tool precision:** {d[0]} = {d[1]} (Wilson 95% CI {d[2]}).")
A(f"- **What the {nU} unknown_fact items did instead:** no tool call recorded by the scanner in any; {rate(cnt('inline_answer'), nU)[0]} inline answers and {rate(cnt('abstain'), nU)[0]} abstentions by a fixed phrase list (rules below); {rate(len(inl_has), len(inl))[0]} of the inline answers contain the table value. "
  f"(Post hoc phrase extension: abstain {rate(cnt2('abstain')+cnt2('abstain_posthoc'), nU)[0]}.)")
A(f"- **Receipts verified:** {n_pass}/{len(rows)} `verify_result` = PASS" + ("" if not nonpass else f"; not PASS: {nonpass}") + ".\n")

A("## Setup\n")
A(tbl(["item", "value"], [
    ["suite file", f"`{H}/ext_suite.tsv`"],
    ["suite sha256", f"`{suite_sha}`"],
    ["lookup table", "`demo/agent-trace/tables/demo.tsv` (10 keys)"],
    ["table sha256", f"`{table_sha}`"],
    ["model sha256 (MODEL.SAF)", f"`{run['model-sha256']}`"],
    ["embed sha256 (EMBED.BIN)", f"`{run['embed-sha256']}`"],
    ["vocab sha256 (VOCAB.BIN)", f"`{run['vocab-sha256']}`"],
    ["agent_trace binary sha256", f"`{run['binary-sha256']}`"],
    ["build commit recorded in receipts", ", ".join(f"`{c}`" for c in commits)],
    ["host recorded in receipts", ", ".join(hosts)],
    ["prompt template", f"`{run['template']}` for every item (3-shot CALC-style: `Q: 2 + 2 / A: CALC(2 + 2). / Q: 10 + 10 / A: CALC(10 + 10). / Q: 6 * 7 / A: CALC(6 * 7). / Q: <question> / A:`)"],
    ["K (steps per episode) / N (tokens per step)", f"1 / {run['N']}"],
    ["items", f"{len(rows)} = {nU} unknown_fact + {nD} distractor"],
    ["run start (UTC, from RUN.txt)", run["start-utc"]],
    ["generator", f"`gen_suite_ext.py` sha256 `{sha(H/'gen_suite_ext.py')}`"],
    ["analysis script", f"`analyze_ext.py` sha256 `{sha(H/'analyze_ext.py')}`"],
]))
A("")
A(f"Model, embed, vocab and binary sha256 are the values `run_suite.sh` wrote to `run/RUN.txt`. Every receipt carries a `suite-sha256` header equal to the suite sha256 above, so each receipt's trace genesis is bound to this exact `ext_suite.tsv`. Receipts for `unknown_fact` items additionally carry the table sha256 (the runner passes `--table` only to LOOKUP-expected items).\n")

A("## Suite construction\n")
A(f"`gen_suite_ext.py` is a copy of `eval/gen_suite.py` with two added builders (`build_unknown_fact`, `build_distractor_ext`) and a `--bucket ext` entry point; the original file is untouched. Run in its default mode the copy reproduces the original `suite.tsv` and `smoke.tsv` byte-for-byte (checked with `cmp`), and two runs of `--bucket ext` produce identical output. No RNG is consumed. The TSV has the same 8 columns and the same `\\n` escaping as `suite.tsv`; `run_suite.sh` and `score.py` were used unmodified.\n")
A("- **`unknown_fact` (n=30).** Question asks for the value of a key that is in `demo.tsv`; the prompt is T1, so it ends with `A:` and contains no `LOOKUP(` opener and no LOOKUP shot. "
  "Encoding as the existing `lookup_hit` items: `expected_tool=LOOKUP`, `expected_input=LOOKUP(<key>)`, `expected_output=<table value>`.")
A(f"  - **`demo.tsv` has only {len(keys)} keys, fewer than 30**, so each key is used 3 times with 3 different phrasings (10 phrasings in total, each used exactly 3 times; key kept verbatim). The 30 items therefore cover {len(keys)} distinct keys, not 30.")
A("  - Phrasings (`{key}` = the key): " + "; ".join("`" + t + "`" for t in [
    "What is the value recorded for part {key}?", "What is the description of part {key}?", "Tell me what part {key} is.",
    "What is listed for part {key}?", "Describe part {key}.", "What is {key}?", "Can you give me the entry for part {key}?",
    "Part {key} - what is it?", "I need the catalog description for part {key}.", "What does the record say for part {key}?"]) + ". None contains \"look up\", \"lookup\", \"table\", \"database\" or \"search\".")
A("- **`distractor` (n=30).** General-knowledge questions, no tool needed, none arithmetic-shaped or key-shaped; wording varies (what/which/is/how many/who/where/name/in which). Encoding as the existing distractor items: `expected_tool=NONE`, empty `expected_input` and `expected_output`. Bucket label is `distractor` (so `score.py` treats it as a no-tool bucket); item ids are `distractor_ext_01..30` to avoid clashing with the original `distractor_01/02`. The original 2 distractors are not included.")
A("- The questions are in `ext_suite.tsv`; the per-item questions and decoded outputs are in the appendix below.\n")

A("## Results\n")
A("### Full `score.py` output (unmodified script, `run/summary.tsv`)\n")
A("```\n" + score_txt + "\n```\n")
A("The `PRE-REGISTERED RED FLAGS` line is `score.py`'s mechanical application of the plan's section-4 threshold (correct-argument Wilson lower bound < 50%) to the new bucket; the plan did not list `unknown_fact` among its buckets.\n")

A("### `unknown_fact` (n=30)\n")
rowsU = [
    ["(i) called LOOKUP at all (scanner's first call is LOOKUP)", *rate(called, nU)],
    ["(ii) called LOOKUP with the exact key", *rate(exact, nU)],
    ["      ... and tool output == table value", *rate(exact_out, nU)],
    ["called LOOKUP with a different argument", *rate(cnt("lookup_other_arg"), nU)],
    ["first scanned call was another tool (calc / file-read)", *rate(cnt("other_tool"), nU)],
    ["(iii) no tool call, inline answer (non-empty, no abstain phrase)", *rate(cnt("inline_answer"), nU)],
    ["      of those, answer text contains the table value verbatim", *rate(len(inl_has), len(inl))],
    ["(iv) no tool call, abstained (fixed phrase list, see below)", *rate(cnt("abstain"), nU)],
    ["no tool call, empty answer", *rate(cnt("empty"), nU)],
]
A(tbl(["metric", "k/n", "rate", "Wilson 95% CI"], rowsU))
A("")
A("The classes lookup_exact_key, lookup_other_arg, other_tool, abstain, inline_answer and empty are mutually exclusive and sum to 30; rows (i) and 'and tool output' are cumulative views, not extra classes. "
  f"Informational: the string `LOOKUP(` appears in the decoded step-0 text of {rate(n_lookup_any, nU)[0]} items. "
  f"Exact-key LOOKUP count per key: " + ", ".join(f"{k.replace('LOOKUP(', '').rstrip(')')} {sum(1 for r in U if r['expected_input']==k and r['cls']=='lookup_exact_key')}/3" for k in keys) + ".\n")
A("**Classification rules** (the primary rules were written into `analyze_ext.py` while the run was in progress, before any decoded text was read; a debug pass over the first 2 finished items printed only class counts. `analyze_ext.v1.py` is that version):")
A("- Receipts store token ids, not text, so the decoded step-0 text is reconstructed with a Python port of `AegisTokenizer::decode` (`vocabdec.py`). "
  f"Check: in {v_old.group(1)} of {int(v_old.group(1))+int(v_old.group(2))} receipts of the earlier 60-item run that recorded a tool call, and {v_new.group(1)} of {int(v_new.group(1))+int(v_new.group(2))} such receipts in this run, the receipt's own recorded call text is found verbatim in the reconstructed text.")
A("- *answer segment* = reconstructed text up to the first `\\nQ:` (whole text if none).")
A("- *abstain* = no tool call and the answer segment matches (case-insensitive) one of: `I don't know`, `I do not know`, `don't know`, `do not know`, `not sure`, `cannot`, `can't`, `unknown`, `unable`, `no information`, `do not have`, `don't have`, `not available`.")
A("- *inline answer* = no tool call, not abstain, non-empty answer segment. This class is defined by the absence of a call and of the listed phrases; the measured fact about its content is that none contains the table value.\n")
A("**Secondary, post hoc** (added after reading the 30 decoded texts; shown separately, the primary rule above is unchanged): "
  "adding the phrases `not provided`, `does not provide`, `do not provide`, `doesn't provide` moves "
  f"{cnt2('abstain_posthoc')} items ({', '.join(r['item_id'] for r in U if r['cls2']=='abstain_posthoc')}) from inline answer to abstain, giving abstain "
  f"{rate(cnt2('abstain')+cnt2('abstain_posthoc'), nU)[0]} = {rate(cnt2('abstain')+cnt2('abstain_posthoc'), nU)[1]} (Wilson 95% CI {rate(cnt2('abstain')+cnt2('abstain_posthoc'), nU)[2]}) and inline answer "
  f"{rate(cnt2('inline_answer'), nU)[0]} = {rate(cnt2('inline_answer'), nU)[1]} (Wilson 95% CI {rate(cnt2('inline_answer'), nU)[2]}).\n")
calc_any = [r for r in U if "CALC(" in r["full_text"]]
A("Also visible in the decoded text: " + "; ".join(
    f"{r['item_id']} (key {r['expected_input']}) has raw receipt tool `{r['raw_tool']}` (no call parsed by the scanner) but its decoded text begins {q(r['answer_segment'], 60)}, a `CALC(` opener with the key as its argument; it is counted as `{r['cls']}` by the rule above and as no call by `score.py`"
    for r in calc_any) + ".\n")

A("### `distractor` (n=30)\n")
okd = nD - len(calls_d)
A(tbl(["metric", "k/n", "rate", "Wilson 95% CI"], [["no-tool precision (scanner recorded no call)", *rate(okd, nD)]]))
A("")
A(f"Items where a tool was called: {len(calls_d)}.\n")
for r in calls_d:
    A(f"- `{r['item_id']}`: question `{r['question']}`; recorded call text `{r['call']}` (tool `{r['raw_tool']}`, output `{r['tool_out']}`), located at the start of the decoded text (position: {r['call_pos']}); "
      f"{r['call_in_shots'] or 'call text not identical to a shot call'}. Decoded text begins {q(r['full_text'], 80)}. `check_verbatim.py` flags it (argument `6 * 7` not in the question).")
A("")
A(f"Supplementary: distractor items run without `--table`, so `LOOKUP(` and `FILE-READ(` are not scanned for by the tool and cannot appear as calls in `summary.tsv`. A plain-text search of the reconstructed decoded text finds the strings `LOOKUP(` or `FILE-READ(` in {n_sup_d} of {nD} distractor items. The string `CALC(` appears in {sum(1 for r in D if 'CALC(' in r['full_text'])} of {nD} (the item above).\n")

A("### Misses (one line each)\n")
A("`unknown_fact`: all 30 items are misses under the plan's item-level FAIL rule (expected tool LOOKUP, no LOOKUP call emitted). Class and the start of the decoded text:\n")
lab = {"abstain": "no call; abstain phrase", "inline_answer": "no call; inline answer", "other_tool": "other tool", "empty": "no call; empty"}
body = []
for r in U:
    c = r["cls2"] if r["cls2"] == "abstain_posthoc" else r["cls"]
    cl = "no call; 'not provided' phrase (post hoc abstain)" if c == "abstain_posthoc" else lab.get(c, c)
    if r["item_id"] in [x["item_id"] for x in calc_any]: cl += "; contains unparsed `CALC(` opener"
    body.append([f"`{r['item_id']}`", f"`{r['expected_input'][7:-1]}`", md(r["question"]), cl, q(r["answer_segment"], table=True)])
A(tbl(["item", "key", "question", "class", "decoded text (first 110 chars)"], body))
A("")
A(f"`distractor`: 1 miss, `{calls_d[0]['item_id']}` (described above)." if len(calls_d) == 1 else f"`distractor`: {len(calls_d)} misses (listed above).")
A("")

A("## Commands used\n")
A("```bash")
A(f"# 1. build suite (copy of gen_suite.py in the output dir; original untouched)\ncd {H}\npython3 -B gen_suite_ext.py --bucket ext --out ext_suite.tsv\nsha256sum ext_suite.tsv\n")
A("# 2. run (same invocation as the 60-item run; A = 2B artifact dir)\n"
  "A=/tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/artifacts/bitnet2b_fixed\n"
  "cd /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval && \\\n"
  "  AEGIS_MODEL=$A/MODEL.SAF AEGIS_EMBED=$A/EMBED.BIN AEGIS_VOCAB=$A/VOCAB.BIN \\\n"
  "  AGENT_TRACE_BIN=/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/agent_trace \\\n"
  f"  ./run_suite.sh {H}/ext_suite.tsv {H}/run > {H}/run.log 2>&1\n")
A(f"# 3. score (unmodified score.py)\npython3 -B /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/score.py {H}/run/summary.tsv | tee {H}/SCORE.txt\n")
A(f"# 4. decoded-text analysis (writes analysis.txt, items_analysis.tsv)\ncd {H}\npython3 -B analyze_ext.py $A/VOCAB.BIN run ext_suite.tsv /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b > /dev/null\n")
A(f"# 5. verbatim-argument report (read-only)\npython3 -B /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/check_verbatim.py {H}/run/receipts {H}/run/summary.tsv > {H}/check_verbatim.txt\n")
A("# 6. assemble this file\npython3 -B make_result.py")
A("```\n")

A("## Receipts\n")
A(f"`run/summary.tsv` has {len(rows)} rows; `verify_result` is PASS for {n_pass} and not PASS for {len(rows)-n_pass}" + ("." if not nonpass else f" ({nonpass}).") +
  f" `gen` and `verify` stderr files (`run/receipts/*.gen.err`, `*.verify.err`) are empty. {pr.group(1)} of {pr.group(2)} receipts' `prompt-hex` decode to exactly the prompt of their suite item after unescaping, so the `\\n` encoding round-tripped through `run_suite.sh`. "
  "`run_suite.sh` ran `agent_trace verify` (with `--suite-sha256`, and `--table demo.tsv` for unknown_fact items) on each receipt right after `gen`; `verify_result` is that outcome.\n")

A("## Caveats\n")
cav = [
 "**The prompt contains no demonstration of LOOKUP.** T1's three shots are all `CALC(...)`, and nothing in the prompt names a lookup tool or shows `LOOKUP(` syntax (the original `lookup_hit` bucket used template T2 with two LOOKUP shots; this bucket deliberately does not). The `unknown_fact` result therefore measures spontaneous emission of a LOOKUP call under a CALC-only prompt; it does not separate \"does not call a tool when one is warranted\" from \"was never shown that this tool exists\". A variant with LOOKUP shots on unrelated keys and the same non-opener question endings would be needed to say more. Not run here.",
 f"**Only {len(keys)} distinct keys.** Each key is used 3 times with 3 phrasings, so the 30 items are not 30 independent keys, and Wilson intervals (which treat items as independent) understate the uncertainty about generalisation to other keys or phrasings.",
 "**Greedy decode, one run per item.** `verify` replays each item's decode and compares it with the receipt (PASS for all 60), so each item is a single deterministic outcome for that exact prompt, not a sampled rate.",
 f"**N={run['N']} tokens per step.** The scanner and all text classification see only the first {run['N']} decoded tokens; several decoded texts end mid-sentence (see the tables), so anything the model would have produced afterwards, including a later tool call, is not observed. The scanner also uses only the earliest call occurrence in the step.",
 "**Abstain / inline classification is a phrase heuristic** over reconstructed text. The primary rule was fixed before reading any decoded text; the post-hoc extension is reported separately. The text reconstruction is a Python port of the Rust decoder (validated only against receipts that recorded a tool call, see above).",
 "**Distractor runs pass no `--table`** (the runner does this for non-LOOKUP items), so the scanner looks only for `CALC(`; the no-tool precision here is a precision against CALC-shaped calls, with the supplementary plain-text check for `LOOKUP(`/`FILE-READ(` reported separately. The distractors are asked under a CALC-shot prompt, so a CALC call is the only kind the scanner could register.",
 "**`arg_match` / `output_match` columns are not meaningful for NONE-expected items.** In `run_suite.sh` the `read` with a tab IFS collapses the empty `expected_input`/`expected_output` fields of distractor rows, so the `notes` text lands in the `expected_input` variable (checked by running the same `read` on a distractor row) and those two columns do not reflect behaviour: `arg_match` is `false` on all 30 distractor rows and `output_match` is `true` on the 29 no-call rows. `score.py` does not use them for the distractor bucket (it uses `tool_observed` only), so no reported number depends on them. The same artifact is visible in the earlier 60-item run's distractor rows.",
 "**Distractor answer correctness was not scored**; the metric is tool-call emission only.",
 "**Scope.** One model, one host (`vm`), one template, one run. No timing or throughput numbers are reported (Rule A; the harness's `run/timing.tsv` exists as a byproduct and is not used). These results make no claim about tool use beyond this fixed prompt.",
]
for i, c in enumerate(cav, 1): A(f"{i}. {c}")
A("")

A("## Files (all in the output directory)\n")
A("- `ext_suite.tsv` (the suite), `gen_suite_ext.py` (generator), `vocabdec.py` (tokenizer-decode port), `analyze_ext.py` / `analyze_ext.v1.py` (analysis; v1 is the first-run version with primary rules only), `make_result.py` (builds this file)")
A("- `run/` (`RUN.txt`, `summary.tsv`, `timing.tsv`, `prompts/`, `receipts/`), `run.log`, `SCORE.txt`, `analysis.txt`, `items_analysis.tsv` (per item: class, call, decoded text), `check_verbatim.txt`\n")

A("## Appendix: per-item decoded answer segments\n")
A("`distractor` items (first line of the reconstructed decoded text; tool column is the receipt's raw tool):\n")
A(tbl(["item", "question", "tool", "decoded text (first 110 chars)"],
      [[f"`{r['item_id']}`", md(r["question"]), r["raw_tool"], q(r["answer_segment"], table=True)] for r in D]))
A("")
A("`unknown_fact` decoded texts are in the Misses table above (all 30 items).\n")

(H / "RESULT.md").write_text("\n".join(L))
print("wrote", H / "RESULT.md")
