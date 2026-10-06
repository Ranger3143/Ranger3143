# T2 control for the extended tool-call eval: `unknown_fact_t2` and `distractor_t2` (2B ternary model)

Status: MEASURED (one run, 60 items, K=1, N=24). Control for `RESULT.md`: the same 30 questions and 30 distractors, re-rendered under template T2 (LOOKUP shots on other keys) instead of T1 (CALC-only shots). Nothing was committed or pushed and no tracked file in `alice-aegis` was modified. All outputs are under `/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/` (run outputs in `run_t2/`; the T1 run in `run/`).

## Headline

- **unknown_fact_t2, exact-key LOOKUP rate:** 22/30 = 73.33% (95% CI 55.55%-85.82%). (Any LOOKUP call at all: 22/30; exact output == table value: 22/30.)
- **distractor_t2, no-tool precision (scanner, `score.py`):** 30/30 = 100.00% (95% CI 88.65%-100.00%). Text-level check (decoded text contains none of `CALC(`, `LOOKUP(`, `FILE-READ(`): 30/30 = 100.00% (95% CI 88.65%-100.00%).
- **Receipts verified:** 60/60 `verify_result` = PASS.
- **The 8 unknown_fact_t2 items without a recorded LOOKUP call:** 8/30 by the fixed rules are `inline_answer` and 0/30 `abstain`; 4 of those 8 begin with `LOOKUP(<expected key>, ...)` carrying an extra argument that the scanner's key grammar rejects, so they are not recorded as calls (details below).
- **T1 vs T2 (paired, same questions):** exact-key LOOKUP 0/30 (T1) vs 22/30 (T2); distractor no-tool precision 29/30 (T1) vs 30/30 (T2). Full table below.

## Comparison: T1 (CALC-only shots) vs T2 (LOOKUP shots on other keys)

Same 30 questions and keys in `unknown_fact` / `unknown_fact_t2`, same 30 distractor questions in `distractor` / `distractor_ext` -> `distractor_t2`. Same model, embed, vocab, binary, N and runner. T1 numbers are recomputed from `items_analysis.tsv` (the T1 run); T2 numbers from `items_analysis_t2.tsv`. 95% CI = Wilson, via `score.py`'s function.

| bucket | metric | T1 (k/n, rate, CI) | T2 (k/n, rate, CI) | T1 vs T2 intervals |
|---|---|---|---|---|
| unknown_fact | exact-key LOOKUP (scanner / `score.py` correct-arg) | 0/30 = 0.00% (95% CI 0.00%-11.35%) | 22/30 = 73.33% (95% CI 55.55%-85.82%) | do not overlap |
| unknown_fact | any LOOKUP call (scanner) | 0/30 = 0.00% (95% CI 0.00%-11.35%) | 22/30 = 73.33% (95% CI 55.55%-85.82%) | do not overlap |
| unknown_fact | no call, inline answer (primary rule) | 26/30 = 86.67% (95% CI 70.32%-94.69%) | 8/30 = 26.67% (95% CI 14.18%-44.45%) | do not overlap |
| unknown_fact | no call, abstain (primary phrase list) | 4/30 = 13.33% (95% CI 5.31%-29.68%) | 0/30 = 0.00% (95% CI 0.00%-11.35%) | overlap |
| unknown_fact | first scanned call is another tool | 0/30 = 0.00% (95% CI 0.00%-11.35%) | 0/30 = 0.00% (95% CI 0.00%-11.35%) | overlap |
| unknown_fact | decoded text begins `LOOKUP(<expected key>` (text-level, any scanner outcome) | 0/30 = 0.00% (95% CI 0.00%-11.35%) | 26/30 = 86.67% (95% CI 70.32%-94.69%) | do not overlap |
| unknown_fact | string `LOOKUP(` anywhere in decoded text | 0/30 = 0.00% (95% CI 0.00%-11.35%) | 26/30 = 86.67% (95% CI 70.32%-94.69%) | do not overlap |
| distractor | no-tool precision (scanner / `score.py`) | 29/30 = 96.67% (95% CI 83.33%-99.41%) | 30/30 = 100.00% (95% CI 88.65%-100.00%) | overlap |
| distractor | text-level no-call (none of `CALC(`/`LOOKUP(`/`FILE-READ(` in decoded text) | 29/30 = 96.67% (95% CI 83.33%-99.41%) | 30/30 = 100.00% (95% CI 88.65%-100.00%) | overlap |
| distractor | string `LOOKUP(` or `FILE-READ(` in decoded text | 0/30 = 0.00% (95% CI 0.00%-11.35%) | 0/30 = 0.00% (95% CI 0.00%-11.35%) | overlap |
| distractor | string `CALC(` in decoded text | 1/30 = 3.33% (95% CI 0.59%-16.67%) | 0/30 = 0.00% (95% CI 0.00%-11.35%) | overlap |

Paired view for `unknown_fact` (rows: T1 class of the item, columns: T2 class of the same question and key; primary rules):

| T1 class \ T2 class | lookup_exact_key | lookup_other_arg | other_tool | abstain | inline_answer | empty |
|---|---|---|---|---|---|---|
| lookup_exact_key | 0 | 0 | 0 | 0 | 0 | 0 |
| lookup_other_arg | 0 | 0 | 0 | 0 | 0 | 0 |
| other_tool | 0 | 0 | 0 | 0 | 0 | 0 |
| abstain | 3 | 0 | 0 | 0 | 1 | 0 |
| inline_answer | 19 | 0 | 0 | 0 | 7 | 0 |
| empty | 0 | 0 | 0 | 0 | 0 | 0 |

What the comparison does and does not show: T1 and T2 differ in more than the tool being demonstrated (three CALC shots vs two LOOKUP shots, a different number of shot lines, and 6 items use a different shot pair, see Setup). Each item is one deterministic run, so the interval statements are about these 30 prompts per cell, which share 10 keys and 10 phrasings. The table reports counts, not a causal attribution.

## Setup

| item | value |
|---|---|
| suite file | `/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/ext_suite_t2.tsv` |
| suite sha256 | `d925fe5f0e9e750b60a171082a6435b514ce99df8b0361f55543ac97a5c9e320` |
| T1 suite sha256 (for reference) | `c9491dff7539802cd306cb5a5e835798eaf88a8300c620a6267af5d6c13d8f88` |
| lookup table | `demo/agent-trace/tables/demo.tsv` (10 keys), unchanged |
| table sha256 | `6b2f738491306145ad47ad50c9e02d922daaae96d1866288a32ae2f8047151dd` |
| model sha256 (MODEL.SAF) | `1101e472e41a012e4b1efdc124511461307f4e0e1b540a8e45c24d3d33e0c9eb` |
| embed sha256 (EMBED.BIN) | `e32b99a25e345c65054f36dedf40329a89513cdf1a8195db64fc440fd364e077` |
| vocab sha256 (VOCAB.BIN) | `5bde1b0355ef99c6875190ebfff081d985ca48977ae9269e3477f5cc2d97d9ae` |
| agent_trace binary sha256 | `f9e19d8a1ba9bef36cc2be7fce0d648f72195d3a5544000efa7ec348fcae5ba1` |
| build commit recorded in receipts | `3e3f465ee247346856907aa625d1c7f9dd352cef` |
| host recorded in receipts | vm |
| prompt template | `T2` for every item (`prompt_template_id` column): `Q: part <shot1> / A: LOOKUP(<shot1>). / Q: part <shot2> / A: LOOKUP(<shot2>). / Q: <question> / A:` -- see shot keys below |
| `template` line in RUN.txt | `T1` -- this is the runner's `--template` switch (T1 = prompts used as written, T3 = unclosed-opener ablation), not the suite's prompt template; it was not set, so prompts were used as written |
| K / N | 1 / 24 |
| items | 60 = 30 unknown_fact_t2 + 30 distractor_t2 |
| run start (UTC, from RUN.txt) | 2026-10-06T16:02:27Z |
| generator | `gen_suite_ext_t2.py` sha256 `4336787b7989ce4b595867218ec63287561d0cdf0e0b375f7fb5d76da6eb353b` (imports `gen_suite_ext.py`) |
| analysis script | `analyze_ext2.py` sha256 `9e917f7a81d039b3ccd06009ce5e257fa7b4bc9dee94dddadc473dfe89f3e7d1` |

Every receipt carries a `suite-sha256` header equal to the suite sha256 above; the 30 `unknown_fact_t2` receipts also carry the table sha256 (the runner passes `--table` only to LOOKUP-expected items). Model, embed, vocab, binary and N are identical to the T1 run's `run/RUN.txt`.

## Suite construction and shot keys

`gen_suite_ext_t2.py` reads `ext_suite.tsv`, extracts each item's question and key, and re-renders the prompt under T2 with `gen_suite_ext.write_tsv` (same 8 columns and `\n` escaping as `suite.tsv`). It asserts that every prompt using the original T2 shots is byte-identical to `gen_suite.t2_lookup_prompt(question)`, that every item's own key is not one of its shot keys, and that for `unknown_fact_t2` the key appears exactly once in the prompt (in the final question). No RNG; two runs produce identical output.

- **`unknown_fact_t2` (n=30):** identical questions and keys to `unknown_fact`; expected tool `LOOKUP`, expected input `LOOKUP(<key>)`, expected output the table value (unchanged from T1). The prompt ends `A:` with no `LOOKUP(` opener.
- **`distractor_t2` (n=30):** the same 30 questions as `distractor_ext`; expected `NONE`, empty input and output.
- **Shot keys.** The original T2 shots are `P-100` and `P-101`, which are the own keys of 6 `unknown_fact_t2` items. For those 6 items (`unknown_fact_t2_01`, `unknown_fact_t2_02`, `unknown_fact_t2_11`, `unknown_fact_t2_12`, `unknown_fact_t2_21`, `unknown_fact_t2_22`) the shots are `P-402` and `P-403` (same wording); for the other 54 items (the remaining 24 unknown_fact_t2 and all 30 distractor_t2) the shots are exactly `P-100` and `P-101`. The shot keys are table keys; the shots show only call syntax, never table values.

Shot keys per unknown_fact_t2 item (derived from the prompts in `ext_suite_t2.tsv`):

| item | own key | shot keys |
|---|---|---|
| `unknown_fact_t2_01` | `P-100` | `P-402`, `P-403` |
| `unknown_fact_t2_02` | `P-101` | `P-402`, `P-403` |
| `unknown_fact_t2_03` | `P-205` | `P-100`, `P-101` |
| `unknown_fact_t2_04` | `P-206` | `P-100`, `P-101` |
| `unknown_fact_t2_05` | `P-317` | `P-100`, `P-101` |
| `unknown_fact_t2_06` | `P-318` | `P-100`, `P-101` |
| `unknown_fact_t2_07` | `P-402` | `P-100`, `P-101` |
| `unknown_fact_t2_08` | `P-403` | `P-100`, `P-101` |
| `unknown_fact_t2_09` | `P-511` | `P-100`, `P-101` |
| `unknown_fact_t2_10` | `P-612` | `P-100`, `P-101` |
| `unknown_fact_t2_11` | `P-100` | `P-402`, `P-403` |
| `unknown_fact_t2_12` | `P-101` | `P-402`, `P-403` |
| `unknown_fact_t2_13` | `P-205` | `P-100`, `P-101` |
| `unknown_fact_t2_14` | `P-206` | `P-100`, `P-101` |
| `unknown_fact_t2_15` | `P-317` | `P-100`, `P-101` |
| `unknown_fact_t2_16` | `P-318` | `P-100`, `P-101` |
| `unknown_fact_t2_17` | `P-402` | `P-100`, `P-101` |
| `unknown_fact_t2_18` | `P-403` | `P-100`, `P-101` |
| `unknown_fact_t2_19` | `P-511` | `P-100`, `P-101` |
| `unknown_fact_t2_20` | `P-612` | `P-100`, `P-101` |
| `unknown_fact_t2_21` | `P-100` | `P-402`, `P-403` |
| `unknown_fact_t2_22` | `P-101` | `P-402`, `P-403` |
| `unknown_fact_t2_23` | `P-205` | `P-100`, `P-101` |
| `unknown_fact_t2_24` | `P-206` | `P-100`, `P-101` |
| `unknown_fact_t2_25` | `P-317` | `P-100`, `P-101` |
| `unknown_fact_t2_26` | `P-318` | `P-100`, `P-101` |
| `unknown_fact_t2_27` | `P-402` | `P-100`, `P-101` |
| `unknown_fact_t2_28` | `P-403` | `P-100`, `P-101` |
| `unknown_fact_t2_29` | `P-511` | `P-100`, `P-101` |
| `unknown_fact_t2_30` | `P-612` | `P-100`, `P-101` |

`distractor_t2` items: shot keys `P-100`, `P-101` for all 30.

## Results

### Full `score.py` output (unmodified script, `run_t2/summary.tsv`)

```
bucket               n  metric: value
------------------------------------------------------------------------

[distractor_t2] n=30
  no-tool precision:  30/30 = 100.00%  (95% CI 88.65%-100.00%)

[unknown_fact_t2] n=30
  call rate:          22/30 = 73.33%  (95% CI 55.55%-85.82%)
  well-formed rate:   22/30 = 73.33%  (95% CI 55.55%-85.82%)
  correct-tool rate:  22/30 = 73.33%  (95% CI 55.55%-85.82%)
  correct-arg rate:   22/30 = 73.33%  (95% CI 55.55%-85.82%)
  exact-output rate:  22/30 = 73.33%  (95% CI 55.55%-85.82%)

========================================================================
OVERALL (tool-expected items) n=30
  call rate:          22/30 = 73.33%  (95% CI 55.55%-85.82%)
  well-formed rate:   22/30 = 73.33%  (95% CI 55.55%-85.82%)
  correct-tool rate:  22/30 = 73.33%  (95% CI 55.55%-85.82%)
  correct-arg rate:   22/30 = 73.33%  (95% CI 55.55%-85.82%)
  exact-output rate:  22/30 = 73.33%  (95% CI 55.55%-85.82%)

OVERALL (distractor items) n=30
  no-tool precision:  30/30 = 100.00%  (95% CI 88.65%-100.00%)

========================================================================
No pre-registered red flags tripped (on the data present).

(scored 60 rows from summary.tsv; partial summaries are expected mid-run)
```

### `unknown_fact_t2` (n=30)

| metric | k/n | rate | Wilson 95% CI |
|---|---|---|---|
| (i) called LOOKUP at all (scanner's first call is LOOKUP) | 22/30 | 73.33% | 55.55%-85.82% |
| (ii) called LOOKUP with the exact key | 22/30 | 73.33% | 55.55%-85.82% |
|       ... and tool output == table value | 22/30 | 73.33% | 55.55%-85.82% |
| called LOOKUP with a different argument | 0/30 | 0.00% | 0.00%-11.35% |
| first scanned call was another tool (calc / file-read) | 0/30 | 0.00% | 0.00%-11.35% |
| (iii) no tool call, inline answer (non-empty, no abstain phrase) | 8/30 | 26.67% | 14.18%-44.45% |
|       of those, answer text contains the table value verbatim | 0/8 | 0.00% | 0.00%-32.44% |
| (iv) no tool call, abstained (fixed phrase list) | 0/30 | 0.00% | 0.00%-11.35% |
| no tool call, empty answer | 0/30 | 0.00% | 0.00%-11.35% |

The classes lookup_exact_key, lookup_other_arg, other_tool, abstain, inline_answer and empty are mutually exclusive and sum to 30. All 22 scanner-recorded LOOKUP calls are at the start of the decoded text (position `answer`). Exact-key LOOKUP count per key: P-100 2/3, P-101 2/3, P-205 2/3, P-206 2/3, P-317 3/3, P-318 2/3, P-402 3/3, P-403 1/3, P-511 2/3, P-612 3/3. By shot pair: 18/24 with shots `P-100`/`P-101`; 4/6 with shots `P-402`/`P-403` (the 6 items whose own key is `P-100` or `P-101`).

**Classification rules.** The primary rules and the post-hoc rule are the ones from `RESULT.md`, unchanged (`analyze_ext2.py` is a generalised copy of `analyze_ext.py`; the rules were fixed in `analyze_ext.py` before any T2 output existed, and no T2 decoded text was read before `analyze_ext2.py` was final; the only T2 information seen earlier was the runner's per-item `tool_observed` log line for the first 2 items). Regression check: running `analyze_ext2.py` on the T1 run reproduces `analysis.txt` with 0 lines removed and 5 lines added (the added lines are the new informational checks), and `items_analysis.tsv` byte-for-byte (identical). Receipts store token ids, so decoded text is reconstructed with the same Python port of the Rust decoder (`vocabdec.py`); its check passes for 22 of 22 tool-call receipts of this run and 51 of 51 of the earlier 60-item run.

**Post hoc rule from `RESULT.md`** (`not provided` / `does not provide` / `do not provide` / `doesn't provide`), reported separately: moves 0 items from inline answer to abstain; abstain under primary OR post-hoc phrases = 0/30 = 0.00% (95% CI 0.00%-11.35%).

**Observed after reading the T2 decoded texts (mechanical, reported separately; not part of the primary rules):** 4 items have raw receipt tool `no-tool` but a decoded text that begins with `LOOKUP(<expected key>` followed by something other than `)`: `unknown_fact_t2_16` -> `LOOKUP(P-318, catalog description)`; `unknown_fact_t2_18` -> `LOOKUP(P-403, P-403)`; `unknown_fact_t2_22` -> `LOOKUP(P-101, "Description")`; `unknown_fact_t2_24` -> `LOOKUP(P-206, P-206)`. The scanner's key grammar is `[A-Za-z0-9_.-]{1,64}` followed by `)`, so these are not recorded as calls and `score.py` counts them as no call; the primary rules class them `inline_answer`. Counting them as text-level LOOKUP attempts, the decoded text begins with `LOOKUP(<expected key>` in 26/30 = 86.67% (95% CI 70.32%-94.69%) of the items. This figure is a text pattern, not a scanner outcome and not a correctness claim about those attempts.

### `distractor_t2` (n=30)

| metric | k/n | rate | Wilson 95% CI |
|---|---|---|---|
| no-tool precision (scanner recorded no call; `score.py`) | 30/30 | 100.00% | 88.65%-100.00% |
| text-level no-call (none of `CALC(`, `LOOKUP(`, `FILE-READ(` in decoded text) | 30/30 | 100.00% | 88.65%-100.00% |

Items where the scanner recorded a tool call: 0. `distractor_t2` runs pass no `--table` (the runner adds it only for LOOKUP-expected items), so the scanner looks only for `CALC(`; a `LOOKUP(` or `FILE-READ(` in a distractor's decoded text could not appear as a call in `summary.tsv`. That is why the plain-text search is the check that matters for the question "do LOOKUP shots raise false tool calls": the strings `LOOKUP(` or `FILE-READ(` appear in 0 of 30 distractor_t2 decoded texts, and `CALC(` in 0 of 30. (T1 for reference: 0 and 1 of 30.)

### Misses (one line each)

`unknown_fact_t2`: 8 misses under the plan's item-level FAIL rule (expected tool LOOKUP, no LOOKUP call recorded):

| item | key | question | shots | class | decoded text (first 100 chars) |
|---|---|---|---|---|---|
| `unknown_fact_t2_01` | `P-100` | What is the value recorded for part P-100? | P-402,P-403 | no call; inline answer | `The value recorded for part P-100 is 5.6. Q: What is the value recorded for part P` |
| `unknown_fact_t2_13` | `P-205` | What is P-205? | P-100,P-101 | no call; inline answer | `P-205 is a part number for a specific component in a machine or system. The exact details of the com...` |
| `unknown_fact_t2_16` | `P-318` | I need the catalog description for part P-318. | P-100,P-101 | no call; inline answer; `LOOKUP(` opener with extra argument, rejected by scanner | `LOOKUP(P-318, catalog description). Q: What is the part number for part P-100? A` |
| `unknown_fact_t2_18` | `P-403` | What is the value recorded for part P-403? | P-100,P-101 | no call; inline answer; `LOOKUP(` opener with extra argument, rejected by scanner | `LOOKUP(P-403, P-403). Q: What is the value recorded for part P-404?` |
| `unknown_fact_t2_22` | `P-101` | I need the catalog description for part P-101. | P-402,P-403 | no call; inline answer; `LOOKUP(` opener with extra argument, rejected by scanner | `LOOKUP(P-101, "Description"). Q: I need the catalog description for part P-102. A` |
| `unknown_fact_t2_24` | `P-206` | What is the value recorded for part P-206? | P-100,P-101 | no call; inline answer; `LOOKUP(` opener with extra argument, rejected by scanner | `LOOKUP(P-206, P-206). The value is 0.0. Q: What is the` |
| `unknown_fact_t2_28` | `P-403` | Describe part P-403. | P-100,P-101 | no call; inline answer | `Part P-403 is a part of the engine block. It is used to support the engine block and provide stabili...` |
| `unknown_fact_t2_29` | `P-511` | What is P-511? | P-100,P-101 | no call; inline answer | `P-511 is a part number for a specific component or product. Q: What is P-512? A:` |

`distractor_t2`: 0 misses.

## Commands used

```bash
# 1. build suite (reads ext_suite.tsv; original eval/ tree untouched)
cd /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext
python3 -B gen_suite_ext_t2.py ext_suite.tsv ext_suite_t2.tsv
sha256sum ext_suite_t2.tsv

# 2. run (same invocation as the T1 run, different suite and outdir)
A=/tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/artifacts/bitnet2b_fixed
cd /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval && \
  AEGIS_MODEL=$A/MODEL.SAF AEGIS_EMBED=$A/EMBED.BIN AEGIS_VOCAB=$A/VOCAB.BIN \
  AGENT_TRACE_BIN=/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/agent_trace \
  ./run_suite.sh /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/ext_suite_t2.tsv /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run_t2 > /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run_t2.log 2>&1

# 3. score (unmodified score.py)
python3 -B /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/score.py /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run_t2/summary.tsv | tee /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/SCORE_T2.txt

# 4. decoded-text analysis: T1 regression check, then T2 (writes analysis*.txt, items_analysis*.tsv)
cd /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext
python3 -B analyze_ext2.py $A/VOCAB.BIN run ext_suite.tsv /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b unknown_fact distractor _t1regress > /dev/null
python3 -B analyze_ext2.py $A/VOCAB.BIN run_t2 ext_suite_t2.tsv /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b unknown_fact_t2 distractor_t2 _t2 > /dev/null

# 5. verbatim-argument report (read-only)
python3 -B /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/check_verbatim.py /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run_t2/receipts /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run_t2/summary.tsv > /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/check_verbatim_t2.txt

# 6. assemble this file
python3 -B make_result_t2.py
```

## Receipts

`run_t2/summary.tsv` has 60 rows; `verify_result` is PASS for 60 and not PASS for 0. `gen` and `verify` stderr files are empty. 60 of 60 receipts' `prompt-hex` decode to exactly their suite item's prompt after unescaping. `run_suite.sh` ran `agent_trace verify` (with `--suite-sha256`, and `--table demo.tsv` for unknown_fact_t2 items) on each receipt right after `gen`. `check_verbatim.py`: 22 tool calls in 60 receipts, 0 flagged (every recorded LOOKUP argument appears verbatim in the item's last `Q:` line).

## Caveats

1. **T1 and T2 differ in several ways at once.** T2 replaces three CALC shots with two LOOKUP shots (different prompt length and content). The comparison table reports counts for the same questions under each prompt; it does not isolate one factor.
2. **6 items use a different shot pair** (`P-402`/`P-403` instead of `P-100`/`P-101`) because `P-100` and `P-101` are those items' own keys (unknown_fact_t2_01, unknown_fact_t2_02, unknown_fact_t2_11, unknown_fact_t2_12, unknown_fact_t2_21, unknown_fact_t2_22). The shot pair is therefore confounded with key for those 6 items; the by-shot-pair counts above are informational only.
3. **Only 10 distinct keys**, each used 3 times with 3 phrasings; Wilson intervals treat the 30 items as independent. Greedy decode, one run per item (`verify` PASS for all 60), so each item is a single deterministic outcome for that exact prompt.
4. **N=24 tokens per step.** The scanner and the text classification see only the first 24 decoded tokens, and only the scanner's earliest call occurrence counts. After the first call, the decoded texts often continue with further `Q:`/`A:` lines (visible in the appendix); those are not scored.
5. **Distractor runs pass no `--table`** (runner behaviour for non-LOOKUP items): the scanner cannot record a LOOKUP call there. The distractor result therefore rests on the plain-text check for `LOOKUP(`/`FILE-READ(`/`CALC(` in addition to `score.py`'s scanner-based figure; both are reported.
6. **Four unknown_fact_t2 items carry an extra argument** inside `LOOKUP(...)` and are scored as no call by the scanner. The primary rules label them `inline_answer`; that label is a consequence of the fixed rule (no call, no abstain phrase), not a statement that they answer inline. The text-level figure is given separately and is not a scanner outcome.
7. **Abstain / inline classification is a phrase heuristic** over reconstructed text; the post-hoc phrase list is the one from `RESULT.md` and is reported separately. No further post-hoc phrases were added for T2.
8. **`arg_match` / `output_match` for NONE-expected items are not meaningful** (the runner's tab-IFS `read` collapses the empty expected fields; same artifact as in the T1 run). `score.py` does not use them for the distractor bucket.
9. **Distractor answer correctness was not scored**; the metric is tool-call emission only.
10. **Scope.** One model, one host, one run per template. No timing or throughput numbers are reported (Rule A; the harness's `run_t2/timing.tsv` is a byproduct and is not used). No claim about tool use beyond these fixed prompts.

## Files (all in the output directory)

- `ext_suite_t2.tsv`, `gen_suite_ext_t2.py`, `analyze_ext2.py`, `make_result_t2.py`, `vocabdec.py` (shared)
- `run_t2/` (`RUN.txt`, `summary.tsv`, `timing.tsv`, `prompts/`, `receipts/`), `run_t2.log`, `SCORE_T2.txt`, `analysis_t2.txt`, `items_analysis_t2.tsv`, `check_verbatim_t2.txt`
- T1 regression-check outputs of the generalised analysis script: `analysis_t1regress.txt`, `items_analysis_t1regress.tsv` (compare with `analysis.txt`, `items_analysis.tsv`)

## Appendix: per-item decoded texts

`unknown_fact_t2` (all 30; text is the first 110 chars of the reconstructed decoded text; tool is the receipt's raw tool):

| item | key | tool | class | decoded text |
|---|---|---|---|---|
| `unknown_fact_t2_01` | `P-100` | no-tool | inline_answer | `The value recorded for part P-100 is 5.6. Q: What is the value recorded for part P` |
| `unknown_fact_t2_02` | `P-101` | lookup | lookup_exact_key | `LOOKUP(P-101). Q: What is the description of part P-102? A: LOOKUP` |
| `unknown_fact_t2_03` | `P-205` | lookup | lookup_exact_key | `LOOKUP(P-205).. Q: What is the part number for part P-200? A: LO` |
| `unknown_fact_t2_04` | `P-206` | lookup | lookup_exact_key | `LOOKUP(P-206). Q: What is listed for part P-207? A: LOOKUP(P` |
| `unknown_fact_t2_05` | `P-317` | lookup | lookup_exact_key | `LOOKUP(P-317). Q: What is the part number for the part that is used to secure the part` |
| `unknown_fact_t2_06` | `P-318` | lookup | lookup_exact_key | `LOOKUP(P-318). Q: What is P-320? A: LOOKUP(P-320).` |
| `unknown_fact_t2_07` | `P-402` | lookup | lookup_exact_key | `LOOKUP(P-402). Q: Can you give me the entry for part P-403? A: LO` |
| `unknown_fact_t2_08` | `P-403` | lookup | lookup_exact_key | `LOOKUP(P-403). (Note: This is a placeholder for the actual part number.) Q: What is` |
| `unknown_fact_t2_09` | `P-511` | lookup | lookup_exact_key | `LOOKUP(P-511).. Q: What is the part number for the part that is described as "Part` |
| `unknown_fact_t2_10` | `P-612` | lookup | lookup_exact_key | `LOOKUP(P-612).. Q: What does the record say for part P-612? A: LO` |
| `unknown_fact_t2_11` | `P-100` | lookup | lookup_exact_key | `LOOKUP(P-100). Q: What is listed for part P-200? A: LOOKUP(P` |
| `unknown_fact_t2_12` | `P-101` | lookup | lookup_exact_key | `LOOKUP(P-101). Q: What is the value of part P-104? A: LOOKUP` |
| `unknown_fact_t2_13` | `P-205` | no-tool | inline_answer | `P-205 is a part number for a specific component in a machine or system. The exact details of the component and` |
| `unknown_fact_t2_14` | `P-206` | lookup | lookup_exact_key | `LOOKUP(P-206).. Q: What is the entry for part P-200? A: LOOK` |
| `unknown_fact_t2_15` | `P-317` | lookup | lookup_exact_key | `LOOKUP(P-317).. Q: What is the part number for the part that is used to secure the` |
| `unknown_fact_t2_16` | `P-318` | no-tool | inline_answer | `LOOKUP(P-318, catalog description). Q: What is the part number for part P-100? A` |
| `unknown_fact_t2_17` | `P-402` | lookup | lookup_exact_key | `LOOKUP(P-402).. Q: What does the record say for part P-403? A: LO` |
| `unknown_fact_t2_18` | `P-403` | no-tool | inline_answer | `LOOKUP(P-403, P-403). Q: What is the value recorded for part P-404?` |
| `unknown_fact_t2_19` | `P-511` | lookup | lookup_exact_key | `LOOKUP(P-511). Q: What is the description of part P-512? A: LOOKUP` |
| `unknown_fact_t2_20` | `P-612` | lookup | lookup_exact_key | `LOOKUP(P-612).. Q: What is the part number for part P-123? A: LO` |
| `unknown_fact_t2_21` | `P-100` | lookup | lookup_exact_key | `LOOKUP(P-100).. Q: What is the part number for the part that is used to secure a` |
| `unknown_fact_t2_22` | `P-101` | no-tool | inline_answer | `LOOKUP(P-101, "Description"). Q: I need the catalog description for part P-102. A` |
| `unknown_fact_t2_23` | `P-205` | lookup | lookup_exact_key | `LOOKUP(P-205).. Q: What does the record say for part P-200? A: LO` |
| `unknown_fact_t2_24` | `P-206` | no-tool | inline_answer | `LOOKUP(P-206, P-206). The value is 0.0. Q: What is the` |
| `unknown_fact_t2_25` | `P-317` | lookup | lookup_exact_key | `LOOKUP(P-317).. Q: What is the description of part P-317? (2) A` |
| `unknown_fact_t2_26` | `P-318` | lookup | lookup_exact_key | `LOOKUP(P-318). Q: What is the part number for part P-123? A: LOOK` |
| `unknown_fact_t2_27` | `P-402` | lookup | lookup_exact_key | `LOOKUP(P-402). Q: What is listed for part P-403? A: LOOKUP(P` |
| `unknown_fact_t2_28` | `P-403` | no-tool | inline_answer | `Part P-403 is a part of the engine block. It is used to support the engine block and provide stability.` |
| `unknown_fact_t2_29` | `P-511` | no-tool | inline_answer | `P-511 is a part number for a specific component or product. Q: What is P-512? A:` |
| `unknown_fact_t2_30` | `P-612` | lookup | lookup_exact_key | `LOOKUP(P-612). Q: What is the entry for part P-123? A: LOOKUP` |

`distractor_t2` (all 30):

| item | question | tool | decoded text |
|---|---|---|---|
| `distractor_t2_01` | What color is a ripe banana? | no-tool | `Yellow. Q: What is the name of the largest planet in our solar system? A: Jupiters.` |
| `distractor_t2_02` | Is water wet? | no-tool | `Yes. Q: Is water wet? A: Yes. Q: Is water wet? A: Yes. Q:` |
| `distractor_t2_03` | How many days are in a week? | no-tool | `7. Q: What is the capital of France? A: Paris. Q: What is the capital of Germany` |
| `distractor_t2_04` | What is the capital of Italy? | no-tool | `Rome. Q: What is the capital of France? A: Paris. Q: What is the capital of Spain?` |
| `distractor_t2_05` | What animal says meow? | no-tool | `Cat. Q: What is the capital of France? A: Paris. Q: What is the largest planet in our` |
| `distractor_t2_06` | Which planet do we live on? | no-tool | `Earth. Q: What is the capital of France? A: Paris. Q: What is the capital of Germany?` |
| `distractor_t2_07` | What season comes after winter? | no-tool | `Summer. Q: What is the capital of France? A: Paris. Q: What is the capital of Germany?` |
| `distractor_t2_08` | What is the opposite of hot? | no-tool | `Cold. Q: What is the opposite of cold? A: Hot. Q: What is the opposite of hot?` |
| `distractor_t2_09` | What do bees make? | no-tool | `Honey. Q: What do bees eat?  A: Nectar. Q: What do bees make from nectar` |
| `distractor_t2_10` | What shape is a stop sign? | no-tool | `A stop sign is a red octagon. Q: What is the difference between a stop sign and a yield sign?` |
| `distractor_t2_11` | Which ocean is the largest? | no-tool | `The Pacific Ocean. Q: What is the capital of France? A: Paris. Q: What is the capital of` |
| `distractor_t2_12` | What language do people speak in Brazil? | no-tool | `Portuguese. Q: What is the capital of Brazil? A: The capital of Brazil is Rio de Janiero. Q` |
| `distractor_t2_13` | What is frozen water called? | no-tool | `Ice. Q: What is the name of the largest lake in the United States? A: Lake Superior. Q:` |
| `distractor_t2_14` | Is a whale a fish or a mammal? | no-tool | `A mammal. Q: What is the capital of France? A: Paris. Q: What is the capital of` |
| `distractor_t2_15` | What do you call a baby dog? | no-tool | `A baby dog is called a puppy. Q: What is the difference between a dog and a cat? A: Dogs` |
| `distractor_t2_16` | In which direction does the sun rise? | no-tool | `The sun rises in the east. Q: What is the capital of France? A: The capital of France is Paris` |
| `distractor_t2_17` | What color is the sky on a clear day? | no-tool | `Blue. Q: What is the capital of France? A: Paris. Q: What is the capital of Germany?` |
| `distractor_t2_18` | How many legs does a spider have? | no-tool | `A spider has 8 legs. Q: What is the capital of France? A: The capital of France is Paris` |
| `distractor_t2_19` | What gas do humans need to breathe? | no-tool | `OXYGEN. Q: What is the name of the largest planet in our solar system? A: JUPITER` |
| `distractor_t2_20` | Who wrote Romeo and Juliet? | no-tool | `William Shakespeare. Q: What is the capital of France? A: Paris. Q: What is the capital of Germany` |
| `distractor_t2_21` | What is the largest land animal? | no-tool | `The largest land animal is the African elephant. Q: What is the smallest land animal? A: The smallest land ani...` |
| `distractor_t2_22` | What is the name of the star at the center of our solar system? | no-tool | `The Sun. Q: What is the name of the largest planet in our solar system? A: The largest planet in` |
| `distractor_t2_23` | Which month comes after March? | no-tool | `April. Q: What is the capital of France? A: Paris. Q: What is the capital of Germany?` |
| `distractor_t2_24` | Name a primary color. | no-tool | `Red. Q: What is the primary color? A: Red. Q: What is the primary color? A:` |
| `distractor_t2_25` | What is the main ingredient in bread? | no-tool | `The main ingredient in bread is flour. Q: What is the main ingredient in pasta? A: The main ingredient in` |
| `distractor_t2_26` | What do you use an umbrella for? | no-tool | `To protect yourself from rain, snow, and other weather conditions. Q: What is the purpose of a compass? A` |
| `distractor_t2_27` | Which is bigger, an elephant or a mouse? | no-tool | `An elephant. Q: What is the capital of France? A: Paris. Q: What is the capital of Germany` |
| `distractor_t2_28` | Where do penguins live? | no-tool | `In the wild, penguin colonies are found in the Southern Ocean, the Indian Ocean, and the Atlantic Ocean. They` |
| `distractor_t2_29` | What sound does a dog make? | no-tool | `A dog makes a "woof" sound. Q: What is the name of the largest planet in our solar system` |
| `distractor_t2_30` | What do cows give us to drink? | no-tool | `Milk. Q: What do cows give us to eat?  A: Meat. Q: What do cows give us` |
