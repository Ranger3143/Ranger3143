# 01 - ALICE-Next: the chosen design

**Status:** plan (output of the design panel), not a result. **No quality number exists for ALICE-Next.** Date: 2026-10-06. Owner: Aefinity AI Inc.
Companion files: `02-training-and-distillation-plan.md`, `03-data-and-license-ledger.md`, `04-eval-protocol-and-gates.md`, `05-risks-and-90-day-plan.md`.

## 0. Conventions used in all five files
- **GATE** = a pre-registered target. It is a threshold the model must meet, never a claim that it will.
- **[meas: X]** = measured by someone, source X. **[arith]** = arithmetic from inputs shown on the line. **[est]** = estimate; the basis is on the line. **[checked]** = the plan author read the file or source on 2026-10-06 and it matched.
- **R0-R9** = research briefs in `model/research/`. **LAB-0x** = labs in `labs/`. **brief** = `00-ALICE-NEXT-brief.md`. **R0-V** = `R0-VERIFICATION-corrections.md` (it covered R1-R4 only; every R5-R9 number is that brief's reading of its source).
- **P-E / P-Op / P-D1** = the three panel proposals (ALICE-Next-E, ALICE-Op, ALICE-Next/D1). **J1 / J2 / J3** = the three judgments, in the order received.
- **"ledger X (via P-E)"** = a row of the program ledger as reported by a proposal. The ledger was not an input to this plan and those rows were not re-read. Treat them as the proposal's reading until a ledger row is opened.
- Decimal MB (10^6 B) unless "MiB" is written. The brief does not say which one its caps use (R0 s7 item 1). Both are carried until Justin pins one.

## 1. Decision (ten lines)
1. **Chosen: ALICE-Next-E (Evolve).** The BitNet-b1.58-2B-4T family, operator-tuned (rung A) and, as a gated bet, structurally pruned inside the family (rung B). Zero engine delta for the op set.
2. Panel result: unanimous rank E > Op > D1. Totals (engine fit + licence + compute + gate probability + evidence, each 0-10): J1 34 / 31 / 26, J2 31 / 30.5 / 29, J3 32 / 28 / 26 for E / Op / D1 [recomputed from the judgments; the harness quoted 63 / 58.5 / 55, which equals J2 + J3, and 34 / 31 / 26, which is J1].
3. E won on engine fit (9/10 from every judge), evidence quality and the only Tier-0 experiment that tests the real behavioural risk for free. It did not win on the brief's hard gates.
4. **Rung A cannot meet the size gate or the "at most half the bytes" branch.** MODEL.SAF is 521,953,185 B (ledger E16c via P-E; measured on an in-program export of the incumbent shape, which rung A shares by construction; no ALICE-Next artifact exists), 4.4% over 500 MB decimal, 74% over the 300 MB target; it passes only a 500 MiB reading (497.8 MiB) [arith]. VOCAB.BIN is 1,759,936 B against the brief's 1 MB cap (ledger A45 via P-E). It also inherits TriviaQA 33.57 and IFEval 53.48 (R4 s1, R8 s3).
5. **Rung B is the only in-family route to size, and nothing supports it.** No source measures pruning a ternary network (R2 gaps, P-E). On the only ternary scaling prior in the briefs (R5 s2 fit, used directionally; R5 warns it is not cross-comparable) a ~1.0B-body model sits about 0.11 nats (+11% PPL) behind the 2.08B body at infinite tokens and about +21% at 150B tokens (J3, recomputed here); the gate allows +5% [arith]. Rung B is therefore a low-probability bet with a staged, numeric go/no-go (file 02 s6, file 04 s7).
6. The architecture-independent assets are the real deliverable: the gateway-verified data factory, the verifiable reward, the frozen suite and the receipt pipeline. They transfer to any base (P-E, J1, J3).
7. Provenance is the weakest point and it is larger than P-E said. The base's SFT/DPO sources are named in its technical report (WildChat, LMSYS-Chat-1M, WizardLM Evol-Instruct, SlimOrca, GLAN/MathScale synthetic; UltraFeedback and MagPie for DPO) [checked: arXiv 2504.12285 text read 2026-10-06; J2 found it first]. R0 s3 and R6 s0 class several of those as not usable in a shipping path. Whether that reaches the weights is a counsel question. The plan never says "no external model output in the chain".
8. The packaged repo also carries the Llama 3 tokenizer inside VOCAB.BIN with the "Built with Meta Llama 3" reach-through unresolved (THIRD_PARTY_NOTICES s1.4 [checked]).
9. **Re-open triggers** (the decision is conditional): (T1) counsel rules the base lineage or tokenizer unusable for shipping; (T2) Notebook 1 gates fail after a data fix; (T3) rung B is a documented negative. T1 or T3 sends the program to Plan C (file 05 s5): Op-S as the cheap falsifier, or D1.
10. Nothing in this plan is published or pushed to a public repo. Weights, recipe and factory stay private until a `PUBLISH?` item is answered (the program's publish policy of 2026-08-28).

## 2. What is built

### 2.1 Two rungs
- **Rung A "E-Full"**: the incumbent shape, behaviour changed by training only. Ships first as the behavioural baseline. Expected to pass behavioural gates with some probability and to fail size and quality gates as literally worded. It is not a size-compliant model and must not be described as one.
- **Rung B "E-Slim"**: rung A pruned width-first (Minitron-style, arXiv 2408.11796, outside R0-R9, fetched by P-E, not checked by R0-V) and healed by distillation from rung A. Primary shape S4. Final shape chosen by the ablation among S4, W, D, V (s2.2).

### 2.2 Architecture table
| Item | Rung A "E-Full" | Rung B "E-Slim", primary S4 | Source |
|---|---|---|---|
| Family | LLaMA-style decoder, RMSNorm + BitNet SubLN pair per layer, ReLU2(gate)*up FFN with THREE ternary matrices, RoPE theta 500000, GQA 4:1, no biases, W1.58A8, per-tensor F32 weight scale, tied BF16 embedding/head | same family | P-E; ledger ES1 via P-E; R0 s7 item 2 |
| Layers | 30 | 24 | P-E |
| Hidden d | 2560 | 2048 | P-E |
| FFN | 6912 | 5120 | P-E |
| q / kv heads, head_dim | 20 / 5, 128 | 16 / 4, 128 (heads x head_dim = d, which `repack_ternary.py` assumes) | P-E |
| Ternary weights | 2,084,044,800 | 1,006,632,960 | [arith] |
| BF16 embedding/head rows | 50,256 x 2560 = 128,655,360 | 50,256 x 2048 = 102,924,288 | [arith] |
| Engine-resident params | 2.213B | 1.110B | [arith] (the 2.41B in R7/R0 counts the 128,256-row table) |
| Context | 2048 (trained at 4096, config caps at 2048) | 2048 | P-E; R0 s7 item 13 |

Other rung-B shapes in the ablation [arith from the same formula]: **W** 30L, d2048, ff4096, body 267.4 MB; **D** 17L at full width, body 295.2 MB; **V** S4 plus a 32,256-id vocabulary (head 132.1 MB BF16). R5's 1.553B ternary count is wrong because the FFN has three matrices (R0 s7 item 2; confirmed by P-E from the engine).

### 2.3 Engine delta (exact)
**Required: none** for the op set or the numerics, for either rung. Basis (P-E; J1 confirmed the head_dim, divisibility, repack-from-config and unit-test claims): `model.rs` reads layers, hidden, heads, kv heads, intermediate, vocab, ctx, hidden_act, rope_theta, rms_norm_eps, tie_word_embeddings; `cis_infer.rs` derives head_dim = hidden/num_heads and requires only hidden and intermediate divisible by 4; `repack_ternary.py` takes dims from `config.json`; head_dim 64/128/130 are unit-tested. CIS-1 limits (dim_in <= 16,909,320; residual n <= 8192) are far from these shapes. What each new shape still needs is **verification, not code**: a new golden receipt, forge run, CIS-full PPL and boot per shipped shape.

**Optional deltas, none assumed in any gate:**
| ID | Delta | Effect | Cost / status |
|---|---|---|---|
| O1 | Allocate the f32 `KVCache` only in Hybrid mode (D3 in P-D1) | saves 314.6 MB (A) / 201.3 MB (B) RAM at ctx 2048; no numeric change. The allocation is unconditional at `cis_infer.rs` ~line 1111, outside the FullInt `z()` guard [checked] | ~3 lines plus a `reset_prefix` guard (cis_infer.rs:2292 per P-D1); all pinned digests must stay byte-identical |
| O2 | `AEGIS_HEAD_PRECONVERT=0` (existing flag, `HeadPlanes` at cis_infer.rs:841 [checked]) | halves head resident size, changes per-token head reads | none |
| O3 | Two-plane certified head screen (ledger M27 via P-E) | 2.0x fewer head bytes at the M7 probe shape, 0/12288 argmax flips, unimplemented | not costed |
| O4 | ES1 lossless container (zstd-19, 399,113,010 B, same trits so digests unchanged) | file size only, not RAM or bandwidth | needs a no_std decoder in the boot path |
| O5 | 1.6-bpw packing (R5 s7, LAB-03 notes about -21% of the ternary part) | smaller body, new kernel | not costed |
| O6 | Replace the approximate pre-tokenizer in `encode()` with the exact Llama-3 ASCII split behind a config key defaulting to legacy (P-D1 D2) | removes train/serve skew at the source | not adopted: changes tokenization of every pinned prompt and must be replicated in `cis-verify/src/vocab.rs` (J1). The baseline uses G1 below instead |

**Required non-engine work** (all in gateway, forge, harness or data tooling): N1 snapshot gateway, `agent_trace --snapshot`, per AEGIS-FETCH-SNAPSHOT-v0 s7 items 1-4 (spec: no engine or verifier change; design only today). N2 Python gateway port plus differential oracle. N3 Python port of `encode()` plus parity test. N4 plain-text tool-state header (s2.7). N5 `score_ext.py` (abstain scorer, legality, call-rate). N6 a `repack_ternary.py` id-space option for variant V (`llama3_pruned_id_space` raises unless exactly 50,000 base ids lie below the cut, repack_ternary.py:266-272 [checked]).

### 2.4 Bytes per token (decode reads every ternary byte plus the whole head) [arith, ternary at the 2.0 bpw container]
| | Ternary body | Head, BF16 path | Total, BF16 head | Head, default i16-plane path (+4 B/weight) | Total, planes |
|---|---|---|---|---|---|
| Rung A | 521.0 MB | 257.3 MB | **778.3 MB** (the figure in LAB-03 and LAB-05) | 514.6 MB | **1,035.6 MB** |
| Rung B (S4) | 251.7 MB | 205.8 MB | **457.5 MB** (-41.2% vs A) | 411.7 MB | **663.4 MB** (-35.9% vs A) |

Which head path LAB-05's 6.27 tok/s used is not stated (P-E and P-Op both flagged this). Both columns are reported until a box1/box2 run settles it. The head is 33% (BF16) to 50% (planes) of rung A's traffic, so width pruning shrinks both terms. KV adds i32 storage: 314.6 MB (A) / 201.3 MB (B) allocated at ctx 2048, plus an unused f32 copy of the same size until O1 [arith; allocation checked]. **No tokens/s claim is made** (Rule A): speed scales with bytes (brief s1, LAB-03) but LAB-05 shows 4-thread decode is serial-fraction-bound, so byte ratios are ceilings.

### 2.5 Packed bytes and the size gates
| | MODEL.SAF | EMBED.BIN | VOCAB.BIN | Total | vs gates |
|---|---|---|---|---|---|
| Rung A | 521,953,185 B [meas: ledger E16c via P-E, on an incumbent-shape export; for rung A this is an expectation until a rung A export exists] | 257,310,720 B [arith] | 1,759,936 B [meas: ledger A45 via P-E] | 781.0 MB [arith] | MODEL.SAF fails <= 500 MB decimal (passes 500 MiB), fails <= 300 MB; VOCAB.BIN fails <= 1 MB; EMBED.BIN passes <= 400 MB |
| Rung B (S4) | about 252.3 MB [est: 251,658,240 B of trits + 0.60 MB overhead, scaled from E16c's 941,985 B overhead] | 205,848,576 B [arith] | 1,759,936 B | about 459.9 MB | MODEL.SAF passes <= 300 MB and "half of 521 MB" (<= 260.5 MB). All three files do NOT meet "half of 781 MB" (<= 390.5 MB) |
| Rung B variant V | about 252.3 MB | 132,120,576 B [arith] | about 1.1 MB [est] | about 385.5 MB [est] | meets the all-files reading only if V's quality cost is acceptable; unmeasured |

VOCAB.BIN: 50,256 strings + 110,042 merges at 12 B each (ledger A45 via P-E). u16 merge triples would give about 1.10 MB [arith, P-E], still above 1 MB, so Justin must re-pin the cap or the merge table must shrink under a tokenization-parity run. RAM at ctx 2048, default HeadPlanes: rung A about 1.6-1.9 GB, above R8 s7's 1.4 GB footprint gate; rung B about 0.66-0.87 GB [arith from allocations, P-E; not measured].

### 2.6 Vocabulary and tokenizer
- **Unchanged for rung A**: Llama-3 base ids < 50000 plus the 256 specials remapped to 50000+k (`repack_ternary.py --llama3-prune`); VOCAB.BIN sha256 `5bde1b03...` (LAB-07 s2). The gateway grammar stays textual (`CALC(..)`, `LOOKUP(..)`, `FILE-READ(..)`, `SEARCH(..)`, `FETCH(..)`), so no new tokens are needed.
- **The brief's "+0.12% perplexity for the prune (A35)" is mis-attributed**: it is the CIS full-int-vs-float delta on the already-pruned model (A35 +0.1239%); B8's 0.12% is engine-vs-transformers (P-E, P-D1; both via ledger). The prune's own cost was never measured. File 04 s4 (Prune cost) and file 02 S0 measure it before training.
- **Train/serve tokenizer skew (J1, J3; not in P-E).** The engine's `encode()` splits only at whitespace/non-whitespace transitions and approximates the reference regex [checked: tokenizer.rs]; it also falls back to `<|reserved_special_token_0|>` for unmapped bytes. J3 ported it and compared with the Llama-3 regex: all 60/60 LAB-07 suite prompts tokenize differently (the `).\n` site is one reference token and two engine tokens), and 4+ digit numbers are grouped differently in about 75% of random cases (example: 9223372036854775807 gives `922|33|720|36|85|47|75|807` in the engine against `922|337|203|685|477|580|7`) [J3 measurement, not re-run here]. Training on HF tokenization and serving through the engine can silently cap the verbatim-argument buckets (calc_hard, calc_overflow). **Fix G1 below.**
- `agent_trace` calls `tokenizer.encode(prompt)` on the raw prompt string (agent_trace.rs:1123, 1343 [checked]) and `encode()` matches no special tokens. A chat wrapper with `<|start_header_id|>` therefore cannot be produced through the gateway without an engine delta (J1, J2, J3). Gated conditions use raw text only (file 04 s2).
- **Variant V** (32,256 ids) is an ablation for rung B only, selected by the teacher-bits-per-byte gate (G6): smallest N whose teacher bits-per-byte on the pruned tokenization is <= 1.01x the canonical tokenization on 5M bytes of held-out text (P-D1 gate; a plan GATE here). Teacher logits are masked to the kept ids and renormalised (R2 s6 via P-D1).

### 2.7 Air-gapped and connected: one model, one binary, one flag
Exactly as AEGIS-FETCH-SNAPSHOT-v0 s1 defines it: without `--snapshot` the scanner never recognises `SEARCH(` or `FETCH(`, so the two variants differ only by the declaration header and by what the gateway honours. The header is **plain text in the raw Q:/A: style** (no special tokens). Training conditions (G2): the same question under headers listing none / CALC / CALC+LOOKUP / +FILE-READ / +SEARCH+FETCH.
- **Air-gapped behaviour targets (the thresholds are the GATES in file 04 s3; none is a result):** integer arithmetic to CALC; a question a declared table covers to LOOKUP with the verbatim key; absent keys reported as NONE/NOT-FOUND; anything else "not in my data, supply a table or ask a connected unit" and never a guess; in-context questions answered inline; SEARCH/FETCH emitted on <= 2% of items (GATE, file 04 s3 [panel]).
- **Connected loop (spec s5), one gateway step each:** draft (receipt records what she believed) -> `SEARCH(query derived from the claim)` -> `FETCH(key the gateway minted; the model never passes a URL)` -> COMPARE (supports / contradicts / no evidence) -> FINAL (revised if contradicted). Its GATES are in file 04 s3 (`factcheck_contradicts`, `_noevidence`, `_injection`; `_supports` is ungated, see file 05 s7 GC2). Fetched text is data; the scanner parses calls only from newly decoded tokens (spec s3). Snapshot extracts are <= about 2 KB (about 500 tokens [est: about 4 ASCII bytes per token]; a design cap, not a measurement) so the loop fits 2048; raising ctx to 4096 doubles the i32 KV (629 MB for rung A) and is not assumed (R0 s7 item 13).
- **Injection:** the model's own discipline, gated by `factcheck_injection`. No warden encoder (that would be an engine/bundle delta; R9 s1.7). R0 s7 item 18: no brief evaluates injection otherwise, so this bucket is new.
- **Receipts prove** agreement with a snapshot of digest D, not that the page was real, fresh or true (spec s4). That table is kept in any customer text.

### 2.8 Scope: what ALICE-Next-E will not do (stated now; from P-Op, listed by J1, J2, J3)
It does not answer long-tail facts from weights (inherits TriviaQA 33.57, R4 s1; ternary recall collapse evidence R0 s1 item 9); no chain-of-thought math or code beyond what the incumbent does; no non-ASCII text; no documents over 2048 tokens; no PDFs or JS pages; no sampling or thinking modes; no JSON tool schemas (BFCL v4 is not a target, R0 s7 item 4); it verifies agreement with a snapshot, not truth.

## 3. Grafts into the winner (each attributed)
| ID | Graft | From | Judges who listed it | Where it lands |
|---|---|---|---|---|
| G1 | Tokenize all training and eval text through a Python port of the engine's `encode()`; 100% parity with the Rust `encode()` on >= 10 MB of mixed text plus every gateway template before any training. Fixes the skew in s2.6 | P-Op (engine-matched pre-tokenization, T2d-style 100% parity) and P-D1 (0-mismatch parity gate on >= 10 MB); the skew itself found by J1 and J3 | J1, J2, J3 (P-Op item); J1, J3 (P-D1 item) | 02 S1b; 04 s6 |
| G2 | Tool-state header training (a tool exists only when declared); `tool_state_legality` bucket n=300; `in_context_answerable` paired with `distractor`; plain-text header because `encode()` cannot emit specials | P-Op | J1, J2, J3 | 02 S1/S3; 04 s2 |
| G3 | Python gateway port, differential-tested against the Rust `agent_trace` on >= 1e6 CALC/LOOKUP cases; the Rust binary stays the oracle for kept episodes. Needed for RL reward throughput | P-Op | J1, J2, J3 | 02 S1, S5 |
| G4 | Teacher-ceiling measurement before any context distillation: the incumbent with a long demonstration prompt, per bucket, replayed through real `agent_trace verify` | P-D1 (S0) | J2, J3 | 02 S0; 04 s7 ceiling probe (a) |
| G5 | Audit that training-time activation quantization matches the CIS-1 points: input of q/k/v and gate/up (NORMQ output), attn_sub_norm output into o_proj, ffn_sub_norm output into down_proj, and the final-norm output into the head (spec s5.12; `logits_int` dots an i8-quantized hidden state). Step-0 parity must pass | P-D1 | J1, J2, J3 | 02 S3 |
| G6 | Vocabulary closure rule and teacher bits-per-byte gate for variant V; bits per UTF-8 byte as the cross-tokenizer metric; standalone measurement of the A35 prune cost | P-D1 | J1, J2, J3 | 02 S0, S7; 04 s4 |
| G7 | Numeric kill gate for every stage | P-D1 | J1, J2, J3 | 02 (every stage) |
| G8 | O1 f32-KV guard, digest-neutral, with CI re-run of every pinned digest | P-D1 (and P-E optional delta) | J1, J2, J3 | 01 s2.3 |
| G9 | Pre-registered promotion rule and cheap falsifier (Op-S at about $289 at $2.69 per P-Op [est]) as the contingency if rung B is negative | P-Op | J1, J2, J3 | 05 s5 |
| G10 | Per-sample generator field in a receipt-chained manifest | P-D1; R6 s12 item 3; ledger M8 via P-E | J2 | 03 |
| G11 | Selection of variant V by bytes read per output character subject to a +1% bits-per-byte limit; operator-share ablation from one stable checkpoint with several cooldown branches (R1 s2d) | P-Op | J2 (operator-share ablation), J3 (both) | 02 S7, S3 |
| G12 | fp16-vs-CPU-bf16 numeric check on 20 prompts as the first notebook cell (ledger M18 shows fp16 destroying another ternary kernel, via P-D1) | P-D1 notebook | none (plan author's addition) | 05 s3; 02 s3 |

**Fixes forced by the judges (not grafts):** F1 raw-form gating only; chat wrapper reported, not gated (J1, J2, J3). F2 abstain scorer: `score.py` only tests "tool not NONE" on no-tool buckets [checked: score.py lines 56-61, 96], so `score_ext.py` with a phrase list frozen before training is added (J1). F3 GRPO needs a hand-written loop because TRL is incompatible with BitNet in three ways (ledger M17 via J1); rejection-sampling SFT with the gateway verifier is the fallback (P-Op S6). F4 optional tool corpora re-labelled: ToolACE, Glaive-FC-v2 and Hermes-FC-v1 generators are unconfirmed (R6 s5, R0 s3), so they are quarantined, not "Apache-2.0, yes" (J2). F5 the rung-B go/no-go rule was non-discriminating (J3); replaced by a staged release (file 02 s6). F6 joint-gate arithmetic is stated (file 04 s2).

**Considered and not adopted:** Op's own tokenizer and from-scratch family (breaks the in-family drop-in, no trainer above 14M); D1's QK-norm erratum and Qwen2 pre-tokenizer (not needed for BitNet); the XS tinybit proxy notebook (E trains the real base; it returns only under Plan C); any external teacher in the baseline.

## 4. Why the alternatives lost (fair)
**ALICE-Op (purpose-built operator family, Op-M 0.61B).** The cleanest provenance of the three (own tokenizer, from-scratch, Apache-2.0 teacher only for optional surface forms), the smallest bytes (225 MB/token, 0.29x), and the most candid scope statement. It lost on gates and evidence. Its own plan expects to fail the general-quality gate; J3's use of the only ternary fit puts Op-M about +35% PPL behind BitNet-2B (directional, outside the fit range). No GPU training substrate exists above the CPU-side tinybit trainer (largest in-house run 14M parameters, ledger M21 via J3), and Tier-0 assumes 25% MFU against a measured 9.9% (ledger M17 via J1). The 0.6B-reads-and-revises-a-snapshot thesis has no precedent at or below 2B (R3, R4 gaps). The chatml operator prompt cannot be produced by `agent_trace` (J1, J2, J3). J3 also notes the M21 "ternary beat the fp twin" evidence was demoted by ledger M24. Op's tokenizer discipline, legality bucket, oracle and promotion rule are grafted.

**ALICE-Next/D1 (BitDistill-style ternary Qwen3-1.7B, 39.5k vocabulary).** The most carefully measured source reading and the only Apache-2.0 chain end to end (it removes the Llama-3 tokenizer lineage, J2). It lost on engine delta, bytes and timing of evidence. It needs a new CIS-1 op (QKNORM-I; aegis-core has no q_norm/k_norm [checked]) that must also be independently reimplemented in `cis-verify` and the UEFI path (J1), a Qwen2 pre-tokenizer, a forge path, and the f32-KV fix; "2-3 engineer-days" is optimistic (J1, J2, J3). At 0.66x bytes it cannot meet "at most half the bytes" without two unbuilt errata (1.6-bpw container, int8 head). KV is 1.49x BitNet's per position, so its byte advantage shrinks to about 0.90x at ctx 2048 (P-D1 [arith]). Conversion evidence is classification-only (BitDistill) plus one tool data point, Bonsai-1.7B at -20.8 BFCL v3 points in its own harness (R0 s1 item 1, with the harness caveat that makes it about 98% retention against Qwen3's own 52.2). The first capability evidence arrives only after about $500. If counsel rules E's lineage unusable (T1), D1 is the strongest Apache route and the plan reverts to it.
