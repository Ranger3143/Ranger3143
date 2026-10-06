# 04 - Evaluation protocol and gates (ALICE-Next-E)

**Status:** plan, 2026-10-06. The suite does not exist yet and nothing below has been measured for ALICE-Next. Labels as in `01-ALICE-NEXT-design.md` s0. Every number marked **GATE** is a threshold chosen before training, not a prediction.

## 1. Pre-registration rule (suite SHA-256 recorded before training)
1. Before **S3 step 1** (and before any S3 pilot arm), the following are frozen, hashed with SHA-256 and committed to the private repo; each hash is also written to the ledger and to a dated file in `state/reports/`:
   the generator code and its seed list; every template and prompt header (P0, T1, T2, the plain-text tool-state headers); every table and namespace list; the item TSVs; `score.py` (unchanged) and `score_ext.py` including the **abstain phrase list**; the thresholds file in s3; the decontamination script and its parameters; and a **commitment hash** of the 300-item private holdout (items withheld).
2. Order of operations: freeze -> hash -> commit -> ledger row -> only then training. The brief (s3) makes this mandatory; R8 s7 and R0 s5 say the same.
3. **Any change to a hashed element after S3 step 1 voids every gating number produced after the change.** A changed suite is a new version (`v3`), the incumbent is re-run on it, and the voided numbers are marked, never silently replaced.
4. Train/eval disjointness: key formats, table schemas, template families, phrasings and key namespaces in the eval share nothing with any training generator; training generators never import the suite generator or `tables/demo.tsv`. LAB-07's suite has 10 keys x 3 phrasings, so it cannot detect memorisation (LAB-07 s7 caveat; R0 s7 item 5). Canary strings are embedded in every eval file and searched for in training data.
5. Rule A (no timing from QEMU or VMs) and Rule B (provenance log for every number) apply to every figure. Measurement and timing legs run on box1/box2 via systemd-run with raw logs under `state/reports/`. On penguin: prepare only, never `ev run --allow-busy` (program rule).

## 2. The frozen suite `evolve_suite_v2`
### 2.1 Buckets (n = 100 per bucket unless stated)
| Bucket | n | Item | Scored by |
|---|---|---|---|
| `calc_easy`, `calc_hard`, `calc_overflow` | 100 each | arithmetic; hard = multi-digit; overflow includes division by zero and i64-range cases | `score.py`; correct tool and verbatim argument (`check_verbatim`) |
| `lookup_hit`, `lookup_miss`, `lookup_near_miss` | 100 each | key in table; key absent; key almost matching a table entry | `score.py` |
| `file_read` | 100 | FILE-READ of a declared file | `score.py` |
| `mixed` | 100 | two- and three-call episodes across K steps | exact output |
| `distractor` | 100 | question needing no tool | no call appears (`score.py`) |
| `in_context_answerable` | 100 | answer is a span of the supplied context; a call is wrong | `score_ext.py` span check **[panel addition, P-Op via J1-J3]** |
| `unknown_fact` | 100 | key is in a declared table but not in the weights | exact-key LOOKUP, tool output equals table value; LOOKUP with an extra argument counts as failure (LAB-07 s8) |
| `unanswerable` | 100 | no declared tool or table covers it | `score_ext.py` abstain phrase list; **always reported next to call rate** |
| `tool_state_legality` | 300 | header lists a subset of tools; any call to an undeclared tool fails | `score_ext.py` **[panel addition, P-Op]** |
| `factcheck_supports`, `_contradicts`, `_noevidence`, `_injection` | 100 each (connected) | spec s6 fixtures: snapshot supports / contradicts / is silent / carries an injected instruction | exact-output rules; needs N1 |
| `factcheck_stale` | 100 (connected, informational) | two snapshots of one key with different dates | informational |
About 1,500 air-gapped items plus 400-500 connected items [arith]. `unknown_fact` uses at least 30 held-out table schemas and key formats (P-Op).

### 2.2 Prompt conditions
- **P0** (gating reading): a one-line tool/table declaration with **zero example calls**. This is my reading of the brief's "without in-prompt demonstration" (s2 item 3). **Justin must confirm it**: a gate that forbids even a declaration is unreachable for any model that is not told a table exists (P-E, P-Op).
- **T1** (three `CALC` shots) and **T2** (two `LOOKUP` shots on other keys): continuity with LAB-07 s7-s8, diagnostic only. Baselines on the old suite: `unknown_fact` 0/30 under T1 and 22/30 under T2; `distractor` 29/30 and 30/30 (LAB-07 s7-s8).
- **P-bare**: no header, stretch, reported only.
- All conditions use the raw `Q:/A:` text form through `agent_trace`. **The chat-wrapper condition (Llama-3 header tokens) is reported, not gated**, because `agent_trace` calls `tokenizer.encode(prompt)` on raw text and `encode()` matches no special tokens [checked: agent_trace.rs:1123, 1343; tokenizer.rs]. Gating it would need an engine delta in `aegis-core` and `cis-verify/src/vocab.rs` against pinned digests (J1, J2, J3). The tool-state header is plain text for the same reason.
- Every prompt is tokenized through the engine-port encoder (G1), parity-gated at 100% (file 02 S1b).

### 2.3 Why n = 100 and what it implies
- Wilson 95% (z = 1.96) lower bounds [arith, recomputed]: 30/30 -> 0.8865; 29/30 -> 0.8333; 100/100 -> 0.963; 95/100 -> 0.8882; 94/100 -> 0.8752; 92/100 -> 0.8500; 90/100 -> 0.8256. At n = 30 the brief's rule ("point >= 95% and Wilson LB >= 85%") is passed only by 30/30 (R0 s7 item 5). At n = 100 it is passed iff >= 95/100; the **point estimate is the binding constraint**, because LB >= 85% alone needs only >= 92/100.
- **Joint-gate arithmetic [arith, recomputed; J3].** P(X >= 95 of 100) for a true per-bucket accuracy p: 0.95 -> 0.616; 0.96 -> 0.788; 0.97 -> 0.919; 0.98 -> 0.985; 0.99 -> 0.9995. Passing 11 buckets: 0.005 at p = 0.95, 0.073 at 0.96, 0.396 at 0.97, 0.842 at 0.98 (14 buckets: 0.001, 0.036, 0.307, 0.804). [The source does not itemise the 11. The reading consistent with the gate table, inferred by the completeness check, is calc x3, lookup x3, file_read, mixed, distractor, unknown_fact, unanswerable, each treated as a >= 95/100 test; 14 adds the three connected gates. `in_context_answerable` is a further 95% bucket: 12 buckets give 0.003, 0.058, 0.364, 0.829 and 15 give 0.001, 0.028, 0.282, 0.791 at the same four values of p [arith, recomputed]. The 90% gates (mixed, unknown_fact, unanswerable, two connected) are easier than the 95/100 test used here, so these products are pessimistic for those buckets.] Passing every bucket therefore needs about 98% or better true accuracy per bucket. The incumbent's measured rates (LAB-07 s3: 100% on easy and hit buckets, 73.3% `calc_hard`, 62.5% `calc_overflow`, 50% near-miss) show how far that is on the hard buckets.
- **Judge prior, not this plan's prediction (J3, [est])**: tool, distractor and abstain gates about 0.5-0.6 each; fact-check about 0.45 with a gateway that does not yet exist; all literal gates about 1%; rung A about 15-20% if 500 MiB and a non-regression rule are accepted; rung B about 3% either way.

## 3. Gates
Thresholds are the brief s4 gates unless marked **[panel]**. All are GATES, evaluated by the instruments named, under condition P0 unless stated, greedy, ctx 2048 (items longer than ctx score 0 and are counted, R8 s6).
| Gate | Threshold | Instrument |
|---|---|---|
| Tool correct-argument, every tool bucket | >= 95% point estimate and Wilson LB >= 85% at n = 100 | `score.py` |
| Call rate on `calc_hard`, `calc_overflow` | >= 97% (LAB-07 s5; baseline 73% / 62.5%) | `score.py` |
| `mixed` (two- and three-call) | >= 90% exact output | `score.py` |
| `distractor` no-tool precision | >= 95% | `score.py` |
| `in_context_answerable` | >= 95% correct, paired with `distractor` **[panel]** | `score_ext.py` |
| `unknown_fact` | >= 90% exact-key LOOKUP under P0 (baseline 0/30 T1, 22/30 T2, LAB-07 s7-s8) | `score.py` / `score_ext.py` |
| `unanswerable` | >= 90% abstain, reported next to call rate | `score_ext.py` |
| `tool_state_legality` | >= 99% never call an undeclared tool **[panel, proposed]** | `score_ext.py` |
| Air-gapped SEARCH/FETCH emission | <= 2% of items **[panel]** | `score_ext.py` |
| Connected `factcheck_contradicts` | >= 90% revised-to-correct | `score_ext.py` over the offline snapshot fixtures (spec s6; needs N1) |
| Connected `factcheck_noevidence` | >= 90% says so **[panel, proposed]** | `score_ext.py` over the snapshot fixtures (needs N1) |
| Connected `factcheck_injection` | >= 95% non-compliance **[panel, proposed]** | `score_ext.py` over the snapshot fixtures (needs N1) |
| Receipt verify | 100% (non-negotiable; engine property; baseline 60/60, LAB-07 s3) | `agent_trace verify`, `cis_witness verify` |
| CIS int-vs-float | token agreement >= the 2B's measured value on the same text. **The 2B's value is not recorded anywhere P-E found; S0 measures it** | `cis_decode`, `aegis-eval --cis-full` |
| General quality | see s4 | `aegis-eval --cis-full`, HF reference |
| Boot | loads and decodes under QEMU, exit 33, digest pinned on >= 3 microarchitectures | s8 |
| Size | <= 500 MB packed; also report 300 MB target; VOCAB.BIN <= 1 MB; EMBED.BIN <= 400 MB | `ls -l`, `repack_ternary.py` log |
| Footprint (informational unless adopted) | RSS <= 1.4 GB (R8 s7); both head representations reported | box1/box2 |

## 4. General-quality gate: instrument and the two readings
- **The brief's gate:** perplexity on the program's held-out text not worse than BitNet-2B-4T by more than 5% at <= half the bytes; or better at equal bytes.
- **Instrument problem (P-E).** The program's anchor is a 199-token WikiText-2 slice (`test.txt` sha `d790b833...`, ledger A21/A35 via P-E). Its single-model sampling noise is tens of percent and its paired noise is near the gate's 5% width [est from a few nats per-token SD, P-E]. **Gate on the full WikiText-2 test** (312,119 tokens, ledger B9 anchor 16.124 via P-E) scored with the HF reference harness (engine-vs-transformers parity 0.12%, ledger B8 via P-E), **and confirm** with `aegis-eval --cis-full` on the A35 slice (continuity: float 30.7067, full-int +0.1239%, ledger A35 via P-E) plus a >= 2k-token slice for the int-vs-float agreement gate. All comparisons use identical ids (G1). Cross-tokenizer comparisons (variant V) use **bits per UTF-8 byte**, because per-token PPL is not comparable across vocabularies (ledger A43 via P-Op; R0 s7 item 19).
- **Prune cost.** The brief's "+0.12% for the 50k prune" is the full-int-vs-float delta on the already-pruned model, not a prune cost (file 01 s2.6). S0 measures the prune's own cost in bits per byte.
- **Half the bytes, two readings, both reported:** MODEL.SAF <= 260.5 MB (half of 521 MB), and all three files <= 390.5 MB (half of 781 MB). Rung B (S4) meets the first (about 252.3 MB [est]) and misses the second (about 459.9 MB [est]) unless variant V (about 385.5 MB [est]) is acceptable.
- **Rung A can only meet "better at equal bytes"** and nothing in the evidence supports it: the one in-program SFT datum moved held-out float PPL 30.71 -> 31.02 (ledger E16c via P-E). **Proposal to Justin: define non-regression for a same-size candidate as paired CI upper bound of the PPL ratio <= 1.02** (it becomes a GATE only if adopted). **Rung B must pass the strict branch: <= 5% worse at <= half the bytes.**

## 5. Statistics (R8 s2, s7)
Wilson 95% intervals for every rate. Exact McNemar and a 10k paired bootstrap against the incumbent re-run on the **same harness** (R8 G1): "better" needs p < 0.05 and a CI excluding 0; "not worse" needs a paired lower bound >= -2 pp (both are decision-rule GATES, frozen in the s1 thresholds file; sources as cited). Holm correction across gates and across secondary metrics. Clustered by template family and table schema where items share one (R8 s2). Call rate is always reported next to abstention (R3 s7 item 3; BFCL irrelevance is gameable by refusal, R0 s1 item 14). A LOOKUP with an extra argument is a failure (LAB-07 s8). `check_verbatim` runs on every call. Injection compliance is reported. All gating evals are greedy through the real gateway; no sampled number is ever reported.

## 6. Scorers and parity
- `score.py` is unchanged; it tests only "tool not NONE" on no-tool buckets [checked: lines 56-61, 96], so the abstain gate needs `score_ext.py`: abstain phrase list **fixed before reading any output** (the LAB-07 s7 precedent; a post-hoc extension is reported separately), legality, call rate, span check, revised-to-correct.
- The HF-side dev scorer mirrors the grammar and is parity-checked against the engine path on a 100-item slice (ledger M12/M15 precedent via P-E). The Python gateway port is differential-tested against the Rust gateway on >= 1e6 cases (G3).
- Step-0 gate before any number is recorded for a new shape or checkpoint family: HF-vs-engine logit parity, PPL gap <= 3% and token parity (ledger M12 0.19-0.20%, M1 inverted-scale precedent via P-E).

## 7. What is measured when
| Point | Cadence | Measured | Where |
|---|---|---|---|
| Dev loop | every N steps (N set by the notebook; start 100) | loss; trit-flip fraction per tensor; p(0) census (incumbent 0.42, ledger ES1); max residual bits per layer; held-out PPL on a fixed 200-sequence slice; 600-item dev slice by bucket with Wilson intervals under P0 and T2 | HF-side harness; decisions use the average of the last 3 checkpoints (R8 s7) |
| Milestone | end of each S3 arm, S4, S5, S6, each B-step | export, then the full receipted suite; CIS-full PPL and int-vs-float; full-WikiText-2 PPL; tool buckets; secondary battery | box1/box2 via systemd-run; raw logs in `state/reports/` |
| Ship candidate | once per shape | s8 pipeline, digests on >= 3 microarchitectures, boot, receipted bundle (R8 s6: manifest with suite hash, per-item receipts, signed Merkle root, 1% third-party replay) | box1/box2, CI |
| Secondary, non-gating, Holm-corrected | milestones | IFEval, MMLU-Redux 2.0, GSM8K-Platinum, BFCL v4 non-live / live / irrelevance, SimpleQA Verified air-gapped not-attempted rate. None may be claimed without a measured log (Rule B). R8's absolute gates (MMLU-Redux >= 60, IFEval >= 70, BFCL v4 >= 50) are not adopted: they outrun the conversion evidence and the brief does not ask for them (R0 s7 item 6) | box1/box2 |
| G0 integrity | before any number is reported | decontamination of ALL training data (incl. S8 text and public QA pools) against every eval item with removal counts published; 60%-prefix memorisation probe <= 5% on MATH-500 and GSM8K-Platinum if reported (R8 G0.2); identical Merkle roots on penguin and box1 (R8 G0.3) | CPU |
**Ceiling probes (so the ceiling is measured, not argued; P-E):** (a) the incumbent with a long demonstration prompt, per bucket, is the upper bound of context distillation (G4); (b) doubling the tool data moves hard buckets by < 2 pp means the limit is capacity or grammar; (c) periphery-only vs full QAT arms at 2B (ledger M26 was 14M); (d) the rung B staged release in file 02 s6 (its numeric rule is the only go/no-go for Tier 2 money).

## 8. Digest and boot pipeline
1. `repack_ternary.py --llama3-prune --max-seq 2048 --source-packing unpacked` (scale convention auto) -> `MODEL.SAF`, `EMBED.BIN`, `VOCAB.BIN`; sha256 of each; byte sizes against the s3 size rows.
2. Step-0 HF-vs-engine logit parity (s6).
3. `cis_decode` 64-token digest, identical across two runs. For the 2B incumbent the pinned digest is `cab11400d737ac4a` (LAB-03, LAB-05 [checked]).
4. `cis_witness` mint and verify; standalone `cis-verify`.
5. `agent_trace verify` on every suite item; 100% required.
6. `build_hardfloat.sh --qemu-test` (exit 33) and `labs/tools/boot_shot.sh`. QEMU is correctness only, never timing (Rule A).
7. Digest pinned on >= 3 microarchitectures: penguin AVX2, box1 AVX2, box2/box3 N4020 without AVX2 or FMA (flags asserted absent as in ledger A48), aarch64 NEON CI; the incumbent's same pipeline ran on all of these (ledger A33-A48 via P-E; A43 on a QAT-fine-tuned 2B).
8. After any engine delta (O1) every pinned digest must stay byte-identical: CIS_SELFTEST `76985613c965f643`, CIS_DECODE `67e8c0a96abc04e1`, BitNet-2B `cab11400d737ac4a`, Falcon-E `3e21adb66d7a17d6` (the first, second and fourth as reported by P-D1, not re-run here).
9. Every shipped shape (A, and each rung-B shape) needs its own golden receipt, forge run, CIS-full PPL and boot.
10. **Connected variant (same weights, same MODEL.SAF, same digest pins: one model, one binary, one flag, file 01 s2.7), so items 1-4 and 6-9 are not repeated for it.** What is added: (a) every connected receipt is verified against its own snapshot file, whose digest is folded into the genesis as `table-sha256` / `table-len` (spec s3, s7); a live run and its replay must give identical gateway output bytes (`replay_equals_live_bytes`), and any difference is a receipt failure; (b) the same weights run without `--snapshot` must never have `SEARCH(` or `FETCH(` scanned (`airgapped_never_scans_search`); (c) `search_then_fetch_chains_like_lookup` passes. All three are spec s7 item 1 tests and gate every connected number (file 05 K16). Instrument: `agent_trace verify` with `--snapshot`, plus the three Rust tests.

## 9. Range-failure watch
ACT-I products already reach 52-55 bits on BitNet-2B (A35 erratum, via P-E) and massive-activation channels exist (ledger E3). A residual, q, k or v bound violation is a loud panic in FullInt, which would be a hard fault in UEFI. Log max residual bits per layer at every milestone; fuzz the CIS-full path on the calibration slice before any shape ships; on violation, clip or re-train, and file a numbered erratum only if a bound truly moves (CIS-1 spec s3, s5.1). J1 raised the same hazard for a from-scratch model without QK-norm (ALICE-Op); here it applies after fine-tuning and pruning.
