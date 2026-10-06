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
