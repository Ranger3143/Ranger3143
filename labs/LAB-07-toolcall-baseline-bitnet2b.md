# LAB-07 — Tool-call baseline: BitNet-b1.58-2B on the receipt-gated gateway (the number ALICE-Next must beat)

**Date:** 2026-10-06 · **Host:** this cloud VM (`host vm` in `RUN.txt`) · **Harness:** alice-aegis `demo/agent-trace/eval/run_suite.sh` + `score.py`, unchanged
**Rule A:** no timing is reported. `timing.tsv` exists for completeness (`gen_s`, `verify_s` per item) and is a VM artefact, not a product number.
**Rule B:** every rate below is computed by `score.py` from `labs/logs/toolcall_2b/summary.tsv`; per-item receipts are in `labs/logs/toolcall_2b/receipts/`.

## 1. Why this lab
The ALICE-Next model plan needs a measured starting point for the one capability the roadmap calls "tool expert": does the current engine model emit a well-formed tool call, with the right tool and the right argument, when it should, and stay quiet when it should not. The program already has a receipt-gated tool gateway (`agent_trace`: CALC and LOOKUP behind a trace receipt that is replayed and verified) and a pre-registered evaluation plan with red flags. This lab runs that suite, as shipped, on the 2B artifacts re-derived in LAB-02.

## 2. Setup (all pinned in `labs/logs/toolcall_2b/RUN.txt`)
| Item | Value |
|---|---|
| Suite | `suite.tsv`, 60 items, sha256 `5ecf5fbf616634547206f55edb6ea611a0065d47d569de431459131bc14a5786` |
| Lookup table | `tables/demo.tsv`, sha256 `6b2f738491306145ad47ad50c9e02d922daaae96d1866288a32ae2f8047151dd` |
| Model | BitNet-b1.58-2B-4T re-derived artifacts (LAB-02 `bitnet2b_fixed`): `MODEL.SAF` sha256 `1101e472e41a012e4b1efdc124511461307f4e0e1b540a8e45c24d3d33e0c9eb`, `EMBED.BIN` `e32b99a2…`, `VOCAB.BIN` `5bde1b03…` |
| Binary | `aegis-linux` example `agent_trace`, sha256 `f9e19d8a1ba9bef36cc2be7fce0d648f72195d3a5544000efa7ec348fcae5ba1` |
| Prompt template | `T1` (few-shot `Q: … A: CALC(…)` / `LOOKUP(…)`), 24-token generation budget per item (`N 24`) |
| Per item | generate → gateway executes the call (if any) → trace receipt written → receipt replayed and verified → row appended to `summary.tsv` |

Buckets (from the pre-registered plan): `calc_easy` (15), `calc_hard` (15), `calc_overflow` (8), `lookup_hit` (8), `lookup_miss` (5), `lookup_near_miss` (4), `mixed` (3, two tools in one answer), `distractor` (2, no tool should be called).

## 3. Results (`labs/logs/toolcall_2b/SCORE.txt`)
Rates are over tool-expected items; the interval is the Wilson 95% CI printed by `score.py`.

| Bucket | n | call rate | correct tool | **correct argument** | exact output | receipt verify |
|---|---|---|---|---|---|---|
| calc_easy | 15 | 15/15 | 15/15 | **15/15 = 100%** (79.6–100) | 15/15 | 15/15 PASS |
| calc_hard | 15 | 11/15 | 11/15 | **11/15 = 73.3%** (48.1–89.1) | 11/15 | 15/15 PASS |
| calc_overflow | 8 | 5/8 | 5/8 | **5/8 = 62.5%** (30.6–86.3) | 5/8 | 8/8 PASS |
| lookup_hit | 8 | 8/8 | 8/8 | **8/8 = 100%** (67.6–100) | 8/8 | 8/8 PASS |
| lookup_miss | 5 | 5/5 | 5/5 | **4/5 = 80%** (37.6–96.4) | 4/5 | 5/5 PASS |
| lookup_near_miss | 4 | 4/4 | 4/4 | **2/4 = 50%** (15.0–85.0) | 2/4 | 4/4 PASS |
| mixed | 3 | 2/3 | 1/3 | **0/3 = 0%** (0–56.2) | 0/3 | 3/3 PASS |
| **overall (tool-expected)** | **58** | 50/58 = 86.2% | 49/58 = 84.5% | **45/58 = 77.6%** (65.3–86.4) | 45/58 | **58/58** |
| distractor (no tool expected) | 2 | no-tool precision 1/2 = 50% (9.5–90.6) | | | | 2/2 PASS |

**Pre-registered red flags tripped (from `score.py`):** `calc_hard` correct-argument Wilson lower bound 48.1% < 50%; `calc_overflow` lower bound 30.6% < 50%.

**Every one of the 60 trace receipts verified** (`verify_result = PASS` on all rows, including the 13 items where the model picked no tool, the wrong tool or the wrong argument). The receipt records what the model did, faithfully, right or wrong; correctness is a property of the model, verifiability is a property of the engine. That separation is the whole point of receipts.

## 4. Reading the failures (`summary.tsv`, `receipts/*.txt`)
- `calc_hard` / `calc_overflow` misses are predominantly **no call at all** (call rate 73% and 62.5%): the 2B answers multi-digit or overflow-range arithmetic in-line from the few-shot pattern instead of delegating. When it does call, the argument is right (call rate == correct-arg rate in both buckets).
- `lookup_near_miss` (keys that almost match a table entry) halves the correct-argument rate: the model "corrects" the key toward the nearest few-shot example.
- `mixed` (two tool calls in one answer) fails completely with template T1; the 24-token budget is also tight for two calls plus prose.
- `distractor` n=2 is too small to say anything; the plan's enlarged distractor set (n ≥ 30) is required before a no-tool-precision claim is made.

## 5. What ALICE-Next has to beat (acceptance gates proposed for `model/`)
| Gate | Baseline (this lab) | Target for the new edge model |
|---|---|---|
| correct-argument rate, every tool bucket | 0–100%, overall 77.6% | ≥ 95% per bucket with Wilson lower bound ≥ 85% (n ≥ 30 per bucket) |
| call rate on calc_hard / calc_overflow | 73% / 62.5% | ≥ 97% |
| mixed (multi-call) correct output | 0/3 | ≥ 90% on n ≥ 30 |
| no-tool precision (distractors) | 1/2 | ≥ 95% on n ≥ 30 |
| receipt verify | 60/60 | 100% (non-negotiable; an engine property) |
| abstain / "I need to look that up" on unknown facts | not measured yet | new bucket `unknown_fact`: ≥ 90% abstain-or-search, see `model/` connected-variant protocol |

## 6. Reproduce
```
cd alice-aegis/aegis-linux && cargo build --release --example agent_trace
cd ../demo/agent-trace/eval
AEGIS_MODEL=<bitnet2b_fixed>/MODEL.SAF AEGIS_EMBED=<…>/EMBED.BIN AEGIS_VOCAB=<…>/VOCAB.BIN \
AGENT_TRACE_BIN=../../../aegis-linux/target/release/examples/agent_trace ./run_suite.sh suite.tsv <outdir>
python3 -I score.py <outdir>/summary.tsv
```
`labs/logs/toolcall_2b/` holds `RUN.txt`, `summary.tsv`, `timing.tsv`, `SCORE.txt`, `run_suite.log`, `prompts/`, `receipts/` and copies of `suite.tsv`, `run_suite.sh`, `score.py`, `README.md` as used.

## 7. Amendment (2026-10-06, same day) — `unknown_fact` and enlarged `distractor` buckets under template T1
Run by a delegated agent on the same artifacts and binary (`labs/logs/toolcall_2b_ext/RESULT.md`; suite `ext_suite.tsv` sha256 `c9491dff7539802cd306cb5a5e835798eaf88a8300c620a6267af5d6c13d8f88`; generator `gen_suite_ext.py` reproduces the original `suite.tsv` byte-for-byte in default mode). 30 `unknown_fact` items ask for the value of a key that *is* in the table, with no `A: LOOKUP(` opener, so the model must decide to look it up; 30 new `distractor` items are general-knowledge questions that need no tool.

| Measurement | k/n | Wilson 95% |
|---|---|---|
| `unknown_fact`: called LOOKUP with the exact key | **0/30** | 0.0–11.4% |
| `unknown_fact`: called LOOKUP at all | 0/30 | 0.0–11.4% |
| `unknown_fact`: no call, inline answer (invented; 0/26 contained the table value) | 26/30 | 70.3–94.7% |
| `unknown_fact`: no call, abstained (phrase list fixed before reading; 7/30 with a post-hoc extension, reported separately) | 4/30 | 5.3–29.7% |
| `distractor`: no-tool precision | **29/30** | 83.3–99.4% |
| trace receipts verified | 60/60 | — |

What the misses look like: "The value recorded for part P-100 is 100.", "Part P-206 is listed for the 2000-2001 model year.", "P-511 is a code used in the United States for the 511th District…" — fluent, specific, and wrong. Four times the model said it had no access to the catalog. The single distractor miss copied the third few-shot call verbatim (`CALC(6 * 7)` for "What do cows give us to drink?"), which `check_verbatim.py` flags.

Caveats recorded by the run: template T1's three shots are all `CALC(…)` and nothing names a lookup tool, so 0/30 cannot separate "will not call" from "was never shown LOOKUP" (the original `lookup_hit` bucket used template T2, which carries LOOKUP shots); the table has only 10 keys, used 3× each with 3 phrasings; only the first 24 decoded tokens are seen; distractors are scanned for `CALC(` only (a plain-text search found no `LOOKUP(`/`FILE-READ(` either); abstain vs inline is a phrase heuristic over text reconstructed from receipt token ids with a Python port of the decoder, validated against 52/52 receipts that recorded a call. **A T2 run (LOOKUP shots on other keys, same questions) is queued and will be appended as §8.**

Gate implication for `model/00-ALICE-NEXT-brief.md` §4: the `unknown_fact ≥ 90%` gate starts from **0%** and the no-tool-precision gate from **96.7%** (n=30).

## 8. Amendment (2026-10-06) — the T2 control: same questions, prompt shows two LOOKUP examples on *other* keys
`labs/logs/toolcall_2b_ext/RESULT_T2.md`; suite `ext_suite_t2.tsv` sha256 `d925fe5f0e9e750b60a171082a6435b514ce99df8b0361f55543ac97a5c9e320`; same artifacts and binary; the generator asserts that no item's own key appears in its shots. Still no `A: LOOKUP(` opener: the model has to decide.

| Bucket · metric | T1 (CALC-only shots) | **T2 (LOOKUP shots on other keys)** | intervals |
|---|---|---|---|
| `unknown_fact` · exact-key LOOKUP, tool output == table value | 0/30 (0.0–11.4%) | **22/30 = 73.3%** (55.6–85.8%) | disjoint |
| `unknown_fact` · decoded text begins `LOOKUP(<expected key>` (text level) | 0/30 | 26/30 = 86.7% (70.3–94.7%) | disjoint |
| `unknown_fact` · no call, inline answer | 26/30 | 8/30 = 26.7% (14.2–44.5%) | disjoint |
| `unknown_fact` · abstained | 4/30 | 0/30 | overlap |
| `distractor` · no-tool precision (scanner) | 29/30 | **30/30 = 100%** (88.7–100%) | overlap |
| `distractor` · no `CALC(`/`LOOKUP(`/`FILE-READ(` anywhere in the text | 29/30 | 30/30 | overlap |
| receipts verified | 60/60 | 60/60 | — |

Reading. Shown that a lookup tool exists, the 2B *does* reach for it on an unknown fact 22 times out of 30, with the exact key and the right table value every time it is counted, and the LOOKUP shots did not induce a single false call on the 30 distractors. Of the 8 misses, 4 are `LOOKUP(P-318, catalog description)`-shaped: the right tool and the right key plus an extra argument that the scanner's strict key grammar rejects, so `score.py` counts them as no call. That is a grammar-fidelity failure, not a decision failure, and it is exactly the kind of thing training on gateway-verified data fixes. The remaining 4 are inline answers. T1 and T2 differ in more than the tool demonstrated (three CALC shots vs two LOOKUP shots), so the table reports counts, not a causal attribution; both runs are single greedy decodes per item with a 24-token window.

Baselines for `model/00-ALICE-NEXT-brief.md` §4, restated: `unknown_fact` decide-to-look-up **0% (no demonstration) / 73% (demonstrated)**, target ≥ 90% *without* in-prompt demonstration; no-tool precision **96.7% / 100%**, target ≥ 95% on n ≥ 30; argument grammar fidelity is a gate of its own (4/30 near-misses here).
