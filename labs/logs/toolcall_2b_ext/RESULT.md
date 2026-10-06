# Extended tool-call eval: `unknown_fact` and `distractor` buckets (2B ternary model, template T1)

Status: MEASURED (one run, 60 items, K=1, N=24). Extension of the pre-registered 60-item tool-call eval; nothing was committed or pushed and no tracked file in `alice-aegis` was modified. All outputs are under `/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/`.

## Headline

- **unknown_fact, exact-key LOOKUP rate:** 0/30 = 0.00% (Wilson 95% CI 0.00%-11.35%). (Any LOOKUP call at all: 0/30.)
- **distractor, no-tool precision:** 29/30 = 96.67% (Wilson 95% CI 83.33%-99.41%).
- **What the 30 unknown_fact items did instead:** no tool call recorded by the scanner in any; 26/30 inline answers and 4/30 abstentions by a fixed phrase list (rules below); 0/26 of the inline answers contain the table value. (Post hoc phrase extension: abstain 7/30.)
- **Receipts verified:** 60/60 `verify_result` = PASS.

## Setup

| item | value |
|---|---|
| suite file | `/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/ext_suite.tsv` |
| suite sha256 | `c9491dff7539802cd306cb5a5e835798eaf88a8300c620a6267af5d6c13d8f88` |
| lookup table | `demo/agent-trace/tables/demo.tsv` (10 keys) |
| table sha256 | `6b2f738491306145ad47ad50c9e02d922daaae96d1866288a32ae2f8047151dd` |
| model sha256 (MODEL.SAF) | `1101e472e41a012e4b1efdc124511461307f4e0e1b540a8e45c24d3d33e0c9eb` |
| embed sha256 (EMBED.BIN) | `e32b99a25e345c65054f36dedf40329a89513cdf1a8195db64fc440fd364e077` |
| vocab sha256 (VOCAB.BIN) | `5bde1b0355ef99c6875190ebfff081d985ca48977ae9269e3477f5cc2d97d9ae` |
| agent_trace binary sha256 | `f9e19d8a1ba9bef36cc2be7fce0d648f72195d3a5544000efa7ec348fcae5ba1` |
| build commit recorded in receipts | `3e3f465ee247346856907aa625d1c7f9dd352cef` |
| host recorded in receipts | vm |
| prompt template | `T1` for every item (3-shot CALC-style: `Q: 2 + 2 / A: CALC(2 + 2). / Q: 10 + 10 / A: CALC(10 + 10). / Q: 6 * 7 / A: CALC(6 * 7). / Q: <question> / A:`) |
| K (steps per episode) / N (tokens per step) | 1 / 24 |
| items | 60 = 30 unknown_fact + 30 distractor |
| run start (UTC, from RUN.txt) | 2026-10-06T15:35:00Z |
| generator | `gen_suite_ext.py` sha256 `fb2d86d2d0c6714e20e33e5ef5814513d9843ffa72ba9f4be204ac4b47827c25` |
| analysis script | `analyze_ext.py` sha256 `c21439ed70a3f552956724b465acbf86db35c0eb605b8fb18aec1bd376eaa0a0` |

Model, embed, vocab and binary sha256 are the values `run_suite.sh` wrote to `run/RUN.txt`. Every receipt carries a `suite-sha256` header equal to the suite sha256 above, so each receipt's trace genesis is bound to this exact `ext_suite.tsv`. Receipts for `unknown_fact` items additionally carry the table sha256 (the runner passes `--table` only to LOOKUP-expected items).

## Suite construction

`gen_suite_ext.py` is a copy of `eval/gen_suite.py` with two added builders (`build_unknown_fact`, `build_distractor_ext`) and a `--bucket ext` entry point; the original file is untouched. Run in its default mode the copy reproduces the original `suite.tsv` and `smoke.tsv` byte-for-byte (checked with `cmp`), and two runs of `--bucket ext` produce identical output. No RNG is consumed. The TSV has the same 8 columns and the same `\n` escaping as `suite.tsv`; `run_suite.sh` and `score.py` were used unmodified.

- **`unknown_fact` (n=30).** Question asks for the value of a key that is in `demo.tsv`; the prompt is T1, so it ends with `A:` and contains no `LOOKUP(` opener and no LOOKUP shot. Encoding as the existing `lookup_hit` items: `expected_tool=LOOKUP`, `expected_input=LOOKUP(<key>)`, `expected_output=<table value>`.
  - **`demo.tsv` has only 10 keys, fewer than 30**, so each key is used 3 times with 3 different phrasings (10 phrasings in total, each used exactly 3 times; key kept verbatim). The 30 items therefore cover 10 distinct keys, not 30.
  - Phrasings (`{key}` = the key): `What is the value recorded for part {key}?`; `What is the description of part {key}?`; `Tell me what part {key} is.`; `What is listed for part {key}?`; `Describe part {key}.`; `What is {key}?`; `Can you give me the entry for part {key}?`; `Part {key} - what is it?`; `I need the catalog description for part {key}.`; `What does the record say for part {key}?`. None contains "look up", "lookup", "table", "database" or "search".
- **`distractor` (n=30).** General-knowledge questions, no tool needed, none arithmetic-shaped or key-shaped; wording varies (what/which/is/how many/who/where/name/in which). Encoding as the existing distractor items: `expected_tool=NONE`, empty `expected_input` and `expected_output`. Bucket label is `distractor` (so `score.py` treats it as a no-tool bucket); item ids are `distractor_ext_01..30` to avoid clashing with the original `distractor_01/02`. The original 2 distractors are not included.
- The questions are in `ext_suite.tsv`; the per-item questions and decoded outputs are in the appendix below.

## Results

### Full `score.py` output (unmodified script, `run/summary.tsv`)

```
bucket               n  metric: value
------------------------------------------------------------------------

[distractor] n=30
  no-tool precision:  29/30 = 96.67%  (95% CI 83.33%-99.41%)

[unknown_fact] n=30
  call rate:          0/30 = 0.00%  (95% CI 0.00%-11.35%)
  well-formed rate:   0/30 = 0.00%  (95% CI 0.00%-11.35%)
  correct-tool rate:  0/30 = 0.00%  (95% CI 0.00%-11.35%)
  correct-arg rate:   0/30 = 0.00%  (95% CI 0.00%-11.35%)
  exact-output rate:  0/30 = 0.00%  (95% CI 0.00%-11.35%)

========================================================================
OVERALL (tool-expected items) n=30
  call rate:          0/30 = 0.00%  (95% CI 0.00%-11.35%)
  well-formed rate:   0/30 = 0.00%  (95% CI 0.00%-11.35%)
  correct-tool rate:  0/30 = 0.00%  (95% CI 0.00%-11.35%)
  correct-arg rate:   0/30 = 0.00%  (95% CI 0.00%-11.35%)
  exact-output rate:  0/30 = 0.00%  (95% CI 0.00%-11.35%)

OVERALL (distractor items) n=30
  no-tool precision:  29/30 = 96.67%  (95% CI 83.33%-99.41%)

========================================================================
PRE-REGISTERED RED FLAGS TRIPPED:
  - bucket 'unknown_fact': correct-argument Wilson lower bound 0.00% < 50%

(scored 60 rows from summary.tsv; partial summaries are expected mid-run)
```

The `PRE-REGISTERED RED FLAGS` line is `score.py`'s mechanical application of the plan's section-4 threshold (correct-argument Wilson lower bound < 50%) to the new bucket; the plan did not list `unknown_fact` among its buckets.

### `unknown_fact` (n=30)

| metric | k/n | rate | Wilson 95% CI |
|---|---|---|---|
| (i) called LOOKUP at all (scanner's first call is LOOKUP) | 0/30 | 0.00% | 0.00%-11.35% |
| (ii) called LOOKUP with the exact key | 0/30 | 0.00% | 0.00%-11.35% |
|       ... and tool output == table value | 0/30 | 0.00% | 0.00%-11.35% |
| called LOOKUP with a different argument | 0/30 | 0.00% | 0.00%-11.35% |
| first scanned call was another tool (calc / file-read) | 0/30 | 0.00% | 0.00%-11.35% |
| (iii) no tool call, inline answer (non-empty, no abstain phrase) | 26/30 | 86.67% | 70.32%-94.69% |
|       of those, answer text contains the table value verbatim | 0/26 | 0.00% | 0.00%-12.87% |
| (iv) no tool call, abstained (fixed phrase list, see below) | 4/30 | 13.33% | 5.31%-29.68% |
| no tool call, empty answer | 0/30 | 0.00% | 0.00%-11.35% |

The classes lookup_exact_key, lookup_other_arg, other_tool, abstain, inline_answer and empty are mutually exclusive and sum to 30; rows (i) and 'and tool output' are cumulative views, not extra classes. Informational: the string `LOOKUP(` appears in the decoded step-0 text of 0/30 items. Exact-key LOOKUP count per key: P-100 0/3, P-101 0/3, P-205 0/3, P-206 0/3, P-317 0/3, P-318 0/3, P-402 0/3, P-403 0/3, P-511 0/3, P-612 0/3.

**Classification rules** (the primary rules were written into `analyze_ext.py` while the run was in progress, before any decoded text was read; a debug pass over the first 2 finished items printed only class counts. `analyze_ext.v1.py` is that version):
- Receipts store token ids, not text, so the decoded step-0 text is reconstructed with a Python port of `AegisTokenizer::decode` (`vocabdec.py`). Check: in 51 of 51 receipts of the earlier 60-item run that recorded a tool call, and 1 of 1 such receipts in this run, the receipt's own recorded call text is found verbatim in the reconstructed text.
- *answer segment* = reconstructed text up to the first `\nQ:` (whole text if none).
- *abstain* = no tool call and the answer segment matches (case-insensitive) one of: `I don't know`, `I do not know`, `don't know`, `do not know`, `not sure`, `cannot`, `can't`, `unknown`, `unable`, `no information`, `do not have`, `don't have`, `not available`.
- *inline answer* = no tool call, not abstain, non-empty answer segment. This class is defined by the absence of a call and of the listed phrases; the measured fact about its content is that none contains the table value.

**Secondary, post hoc** (added after reading the 30 decoded texts; shown separately, the primary rule above is unchanged): adding the phrases `not provided`, `does not provide`, `do not provide`, `doesn't provide` moves 3 items (unknown_fact_10, unknown_fact_17, unknown_fact_23) from inline answer to abstain, giving abstain 7/30 = 23.33% (Wilson 95% CI 11.79%-40.93%) and inline answer 23/30 = 76.67% (Wilson 95% CI 59.07%-88.21%).

Also visible in the decoded text: unknown_fact_22 (key LOOKUP(P-101)) has raw receipt tool `no-tool` (no call parsed by the scanner) but its decoded text begins `CALC(P-101).<|improve this answer|> The answer is: 2 + 2 =`, a `CALC(` opener with the key as its argument; it is counted as `inline_answer` by the rule above and as no call by `score.py`.

### `distractor` (n=30)

| metric | k/n | rate | Wilson 95% CI |
|---|---|---|---|
| no-tool precision (scanner recorded no call) | 29/30 | 96.67% | 83.33%-99.41% |

Items where a tool was called: 1.

- `distractor_ext_30`: question `What do cows give us to drink?`; recorded call text `CALC(6 * 7)` (tool `calc`, output `42`), located at the start of the decoded text (position: answer); identical to few-shot call #3 in the prompt. Decoded text begins `CALC(6 * 7). (Note: This is a joke, cows do not give us to drink,`. `check_verbatim.py` flags it (argument `6 * 7` not in the question).

Supplementary: distractor items run without `--table`, so `LOOKUP(` and `FILE-READ(` are not scanned for by the tool and cannot appear as calls in `summary.tsv`. A plain-text search of the reconstructed decoded text finds the strings `LOOKUP(` or `FILE-READ(` in 0 of 30 distractor items. The string `CALC(` appears in 1 of 30 (the item above).

### Misses (one line each)

`unknown_fact`: all 30 items are misses under the plan's item-level FAIL rule (expected tool LOOKUP, no LOOKUP call emitted). Class and the start of the decoded text:

| item | key | question | class | decoded text (first 110 chars) |
|---|---|---|---|---|
| `unknown_fact_01` | `P-100` | What is the value recorded for part P-100? | no call; inline answer | `The value recorded for part P-100 is 100.` |
| `unknown_fact_02` | `P-101` | What is the description of part P-101? | no call; inline answer | `Part P-101 is a component used in the manufacturing process of a specific product. It is designed to perform a...` |
| `unknown_fact_03` | `P-205` | Tell me what part P-205 is. | no call; inline answer | `P-205 is a specific part number used in various industries, such as automotive, electronics, and machinery. It...` |
| `unknown_fact_04` | `P-206` | What is listed for part P-206? | no call; inline answer | `Part P-206 is listed for the 2000-2001 model year.` |
| `unknown_fact_05` | `P-317` | Describe part P-317. | no call; inline answer | `Part P-317 is a component of the engine that plays a crucial role in the overall performance and efficiency of...` |
| `unknown_fact_06` | `P-318` | What is P-318? | no call; inline answer | `P-318 is a code used in the United States for a specific type of vehicle, typically a truck or a bus` |
| `unknown_fact_07` | `P-402` | Can you give me the entry for part P-402? | no call; inline answer | `Yes, the entry for part P-402 is 1.5.` |
| `unknown_fact_08` | `P-403` | Part P-403 - what is it? | no call; inline answer | `Part P-403 is a standard for the design and installation of electrical and electronic equipment in the automot...` |
| `unknown_fact_09` | `P-511` | I need the catalog description for part P-511. | no call; abstain phrase | `I'm sorry, I don't have access to external databases or specific catalog descriptions. I recommend checking th...` |
| `unknown_fact_10` | `P-612` | What does the record say for part P-612? | no call; 'not provided' phrase (post hoc abstain) | `The record for part P-612 is not provided in the given information. Please refer to the relevant documentation...` |
| `unknown_fact_11` | `P-100` | What is listed for part P-100? | no call; inline answer | `Part P-100 is listed for the following items: 1. 1.1.1.1.1` |
| `unknown_fact_12` | `P-101` | Describe part P-101. | no call; inline answer | `Part P-101 is a component of the system that performs a specific function. It is designed to meet certain requ...` |
| `unknown_fact_13` | `P-205` | What is P-205? | no call; inline answer | `P-205 is a code used in the United States to identify a specific type of product, such as a product with` |
| `unknown_fact_14` | `P-206` | Can you give me the entry for part P-206? | no call; abstain phrase | `I'm sorry, I don't have access to specific company databases or records. Please contact the relevant departmen...` |
| `unknown_fact_15` | `P-317` | Part P-317 - what is it? | no call; inline answer | `Part P-317 is a standard for the design and installation of pressure vessels and related equipment. It provide...` |
| `unknown_fact_16` | `P-318` | I need the catalog description for part P-318. | no call; abstain phrase | `I'm sorry, I don't have access to the catalog. Please check the catalog yourself or contact the customer servi...` |
| `unknown_fact_17` | `P-402` | What does the record say for part P-402? | no call; 'not provided' phrase (post hoc abstain) | `The record does not provide specific information about part P-402. Please refer to the relevant documentation ...` |
| `unknown_fact_18` | `P-403` | What is the value recorded for part P-403? | no call; inline answer | `The value recorded for part P-403 is 10.0.` |
| `unknown_fact_19` | `P-511` | What is the description of part P-511? | no call; inline answer | `Part P-511 is a 3-position, 3-position, 3-position, 3-position, 3` |
| `unknown_fact_20` | `P-612` | Tell me what part P-612 is. | no call; inline answer | `Part P-612 is a type of automotive part used in the engine of a vehicle. It is a fuel pump and` |
| `unknown_fact_21` | `P-100` | Part P-100 - what is it? | no call; inline answer | `Part P-100 is a specific part number used in various industries, such as automotive, electronics, and machiner...` |
| `unknown_fact_22` | `P-101` | I need the catalog description for part P-101. | no call; inline answer; contains unparsed `CALC(` opener | `CALC(P-101).<\|improve this answer\|> The answer is: 2 + 2 =` |
| `unknown_fact_23` | `P-205` | What does the record say for part P-205? | no call; 'not provided' phrase (post hoc abstain) | `The record does not provide specific information about part P-205. Please refer to the relevant documentation ...` |
| `unknown_fact_24` | `P-206` | What is the value recorded for part P-206? | no call; inline answer | `The value recorded for part P-206 is 5.0.` |
| `unknown_fact_25` | `P-317` | What is the description of part P-317? | no call; inline answer | `Part P-317 is a part of the engine that is used for fuel injection. It is a fuel pump that is` |
| `unknown_fact_26` | `P-318` | Tell me what part P-318 is. | no call; inline answer | `P-318 is a specific part number used in various industries. It is important to refer to the relevant documenta...` |
| `unknown_fact_27` | `P-402` | What is listed for part P-402? | no call; inline answer | `Part P-402 is listed for the "P-402" part number. (Note: This is a placeholder and` |
| `unknown_fact_28` | `P-403` | Describe part P-403. | no call; inline answer | `Part P-403 is a component of the system. It is designed to perform a specific function and is an integral part` |
| `unknown_fact_29` | `P-511` | What is P-511? | no call; inline answer | `P-511 is a code used in the United States for the 511th District of the United States House of Representatives` |
| `unknown_fact_30` | `P-612` | Can you give me the entry for part P-612? | no call; abstain phrase | `I'm sorry, I cannot provide the entry for part P-612 as it is a specific document that requires access to` |

`distractor`: 1 miss, `distractor_ext_30` (described above).

## Commands used

```bash
# 1. build suite (copy of gen_suite.py in the output dir; original untouched)
cd /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext
python3 -B gen_suite_ext.py --bucket ext --out ext_suite.tsv
sha256sum ext_suite.tsv

# 2. run (same invocation as the 60-item run; A = 2B artifact dir)
A=/tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/artifacts/bitnet2b_fixed
cd /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval && \
  AEGIS_MODEL=$A/MODEL.SAF AEGIS_EMBED=$A/EMBED.BIN AEGIS_VOCAB=$A/VOCAB.BIN \
  AGENT_TRACE_BIN=/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/agent_trace \
  ./run_suite.sh /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/ext_suite.tsv /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run > /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run.log 2>&1

# 3. score (unmodified score.py)
python3 -B /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/score.py /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run/summary.tsv | tee /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/SCORE.txt

# 4. decoded-text analysis (writes analysis.txt, items_analysis.tsv)
cd /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext
python3 -B analyze_ext.py $A/VOCAB.BIN run ext_suite.tsv /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b > /dev/null

# 5. verbatim-argument report (read-only)
python3 -B /home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/check_verbatim.py /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run/receipts /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/run/summary.tsv > /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/toolcall_2b_ext/check_verbatim.txt

# 6. assemble this file
python3 -B make_result.py
```

## Receipts

`run/summary.tsv` has 60 rows; `verify_result` is PASS for 60 and not PASS for 0. `gen` and `verify` stderr files (`run/receipts/*.gen.err`, `*.verify.err`) are empty. 60 of 60 receipts' `prompt-hex` decode to exactly the prompt of their suite item after unescaping, so the `\n` encoding round-tripped through `run_suite.sh`. `run_suite.sh` ran `agent_trace verify` (with `--suite-sha256`, and `--table demo.tsv` for unknown_fact items) on each receipt right after `gen`; `verify_result` is that outcome.

## Caveats

1. **The prompt contains no demonstration of LOOKUP.** T1's three shots are all `CALC(...)`, and nothing in the prompt names a lookup tool or shows `LOOKUP(` syntax (the original `lookup_hit` bucket used template T2 with two LOOKUP shots; this bucket deliberately does not). The `unknown_fact` result therefore measures spontaneous emission of a LOOKUP call under a CALC-only prompt; it does not separate "does not call a tool when one is warranted" from "was never shown that this tool exists". A variant with LOOKUP shots on unrelated keys and the same non-opener question endings would be needed to say more. Not run here.
2. **Only 10 distinct keys.** Each key is used 3 times with 3 phrasings, so the 30 items are not 30 independent keys, and Wilson intervals (which treat items as independent) understate the uncertainty about generalisation to other keys or phrasings.
3. **Greedy decode, one run per item.** `verify` replays each item's decode and compares it with the receipt (PASS for all 60), so each item is a single deterministic outcome for that exact prompt, not a sampled rate.
4. **N=24 tokens per step.** The scanner and all text classification see only the first 24 decoded tokens; several decoded texts end mid-sentence (see the tables), so anything the model would have produced afterwards, including a later tool call, is not observed. The scanner also uses only the earliest call occurrence in the step.
5. **Abstain / inline classification is a phrase heuristic** over reconstructed text. The primary rule was fixed before reading any decoded text; the post-hoc extension is reported separately. The text reconstruction is a Python port of the Rust decoder (validated only against receipts that recorded a tool call, see above).
6. **Distractor runs pass no `--table`** (the runner does this for non-LOOKUP items), so the scanner looks only for `CALC(`; the no-tool precision here is a precision against CALC-shaped calls, with the supplementary plain-text check for `LOOKUP(`/`FILE-READ(` reported separately. The distractors are asked under a CALC-shot prompt, so a CALC call is the only kind the scanner could register.
7. **`arg_match` / `output_match` columns are not meaningful for NONE-expected items.** In `run_suite.sh` the `read` with a tab IFS collapses the empty `expected_input`/`expected_output` fields of distractor rows, so the `notes` text lands in the `expected_input` variable (checked by running the same `read` on a distractor row) and those two columns do not reflect behaviour: `arg_match` is `false` on all 30 distractor rows and `output_match` is `true` on the 29 no-call rows. `score.py` does not use them for the distractor bucket (it uses `tool_observed` only), so no reported number depends on them. The same artifact is visible in the earlier 60-item run's distractor rows.
8. **Distractor answer correctness was not scored**; the metric is tool-call emission only.
9. **Scope.** One model, one host (`vm`), one template, one run. No timing or throughput numbers are reported (Rule A; the harness's `run/timing.tsv` exists as a byproduct and is not used). These results make no claim about tool use beyond this fixed prompt.

## Files (all in the output directory)

- `ext_suite.tsv` (the suite), `gen_suite_ext.py` (generator), `vocabdec.py` (tokenizer-decode port), `analyze_ext.py` / `analyze_ext.v1.py` (analysis; v1 is the first-run version with primary rules only), `make_result.py` (builds this file)
- `run/` (`RUN.txt`, `summary.tsv`, `timing.tsv`, `prompts/`, `receipts/`), `run.log`, `SCORE.txt`, `analysis.txt`, `items_analysis.tsv` (per item: class, call, decoded text), `check_verbatim.txt`

## Appendix: per-item decoded answer segments

`distractor` items (first line of the reconstructed decoded text; tool column is the receipt's raw tool):

| item | question | tool | decoded text (first 110 chars) |
|---|---|---|---|
| `distractor_ext_01` | What color is a ripe banana? | no-tool | `A ripe banana is typically yellow.` |
| `distractor_ext_02` | Is water wet? | no-tool | `No, water is not wet. It is a liquid and does not have a texture that we typically associate with being wet` |
| `distractor_ext_03` | How many days are in a week? | no-tool | `7 days.` |
| `distractor_ext_04` | What is the capital of Italy? | no-tool | `The capital of Italy is Rome.` |
| `distractor_ext_05` | What animal says meow? | no-tool | `CAT.` |
| `distractor_ext_06` | Which planet do we live on? | no-tool | `Earth.` |
| `distractor_ext_07` | What season comes after winter? | no-tool | `Spring.` |
| `distractor_ext_08` | What is the opposite of hot? | no-tool | `COLD.` |
| `distractor_ext_09` | What do bees make? | no-tool | `Bees make honey.` |
| `distractor_ext_10` | What shape is a stop sign? | no-tool | `A stop sign is a red octagon.` |
| `distractor_ext_11` | Which ocean is the largest? | no-tool | `The Pacific Ocean is the largest ocean.` |
| `distractor_ext_12` | What language do people speak in Brazil? | no-tool | `Portuguese.` |
| `distractor_ext_13` | What is frozen water called? | no-tool | `Ice.` |
| `distractor_ext_14` | Is a whale a fish or a mammal? | no-tool | `A whale is a mammal.` |
| `distractor_ext_15` | What do you call a baby dog? | no-tool | `A baby dog is called a puppy.` |
| `distractor_ext_16` | In which direction does the sun rise? | no-tool | `The sun rises in the east.` |
| `distractor_ext_17` | What color is the sky on a clear day? | no-tool | `The sky is blue on a clear day.` |
| `distractor_ext_18` | How many legs does a spider have? | no-tool | `Spiders have 8 legs.` |
| `distractor_ext_19` | What gas do humans need to breathe? | no-tool | `OXYGEN.` |
| `distractor_ext_20` | Who wrote Romeo and Juliet? | no-tool | `William Shakespeare.` |
| `distractor_ext_21` | What is the largest land animal? | no-tool | `The largest land animal is the African elephant.` |
| `distractor_ext_22` | What is the name of the star at the center of our solar system? | no-tool | `The star at the center of our solar system is called the Sun.` |
| `distractor_ext_23` | Which month comes after March? | no-tool | `April.` |
| `distractor_ext_24` | Name a primary color. | no-tool | `Red.` |
| `distractor_ext_25` | What is the main ingredient in bread? | no-tool | `The main ingredient in bread is flour.` |
| `distractor_ext_26` | What do you use an umbrella for? | no-tool | `An umbrella is used to protect you from rain or sun.` |
| `distractor_ext_27` | Which is bigger, an elephant or a mouse? | no-tool | `An elephant is bigger than a mouse.` |
| `distractor_ext_28` | Where do penguins live? | no-tool | `PENGUINS live in the wild, typically in the Southern Ocean, the Arctic Ocean, and the sub-Ant` |
| `distractor_ext_29` | What sound does a dog make? | no-tool | `A dog makes a variety of sounds, including barking, growling, whining, and howling. The specific` |
| `distractor_ext_30` | What do cows give us to drink? | calc | `CALC(6 * 7). (Note: This is a joke, cows do not give us to drink,` |

`unknown_fact` decoded texts are in the Misses table above (all 30 items).
