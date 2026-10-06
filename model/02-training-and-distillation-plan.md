# 02 - Training and distillation plan (ALICE-Next-E)

**Status:** plan, not result. Labels as in `01-ALICE-NEXT-design.md` s0: **GATE** (pre-registered target), **[meas]**, **[arith]**, **[est]**, **[checked]**, "ledger X (via P-E)" (ledger row as reported by a proposal, not re-read). Day 0 = 2026-10-06. Nothing here has been run. Every number below that is not marked [meas] is a plan input or an estimate.

## 1. Stage map
| Stage | What | Rung | Token / sample budget | Teacher (licence) |
|---|---|---|---|---|
| S0 | Freeze suite, re-baseline incumbent, measure prune cost and teacher ceilings | both | 0 training tokens; about 1,400-2,000 gate items | none |
| S1 | Gateway-verified data factory, snapshot gateway, Python gateway port | both | about 65-100M tokens, about 350k episodes [est] | none (labels by construction) |
| S1b | Engine-port tokenizer and parity gate (G1) | both | 0 | none |
| S2 | Own-weights probing for known/unknown labels | A (redo for B) | 100-200k questions, about 10M generated tokens; 60-100k labelled samples | incumbent (self, MIT) |
| S3 | Operator SFT: context distillation + rejection-sampling, QAT in the loop | A | pilot 5-20M; main 0.1B (Tier 0) to 0.3-0.5B (Tier 1) | incumbent (self, MIT) + construction labels |
| S4 | Anti-forgetting arms P / L / H with KL-to-incumbent replay | A | 30-60M replay tokens inside S3; three 10-20M pilot arms | incumbent frozen (MIT) |
| S5 | Verifiable-reward RL (GRPO) on gateway rewards | A | 4k prompts first, up to 20k prompts x group 8 | none (verifier reward) |
| S6 | Greedy consolidation and cooldown, export | A | 20-50M tokens | own RL policy |
| S7 | Importance-ranked structured pruning; four shape arms | B | 0 training tokens; 1024 x 2048 calibration tokens | rung A (self-family) |
| S8 | Heal by distillation from rung A | B | pilot 0.1B per arm; Tier 1 about 8-12B; Tier 2 about 100-140B (staged, s6) | rung A (MIT-derived) |
| S9 | Optional continued pretraining / anneal on Tier-A text | A if drift, B inside S8 | A: at most 1-5B (Tier 1) | incumbent / rung A |
| S10 | Export, parity, receipts, boot | both | n/a | none |

## 2. Stages in detail
Each stage lists budget, teacher and licence, QAT/hyper-parameters with source (full register in s4) and **kill criteria (all GATES)**. A killed stage stops spend and goes to `BLOCKERS.md`; it does not silently continue.

### S0 Freeze and re-baseline
- **Do:** freeze `evolve_suite_v2` and `score_ext.py` and record SHA-256 before any training step (file 04 s1). Re-run the incumbent on it under P0/T1/T2 raw conditions. Measure: full-text PPL (HF reference, parity-checked against the engine); CIS-full int-vs-float agreement; **the vocabulary prune's own cost** (incumbent float, full vocabulary and canonical tokenization against pruned 50,256 vocabulary and engine-port tokenization, in bits per UTF-8 byte; G6); HeadPlanes on/off bytes and RSS on box1/box2 via systemd-run with raw logs under `state/reports/`. **Teacher ceiling (G4):** the incumbent with a long grammar-demonstration prompt, per bucket, every transcript replayed through real `agent_trace verify`; this is the upper bound for context distillation (S3).
- **Evidence for what the baseline looks like:** LAB-07 s3 (T1: 45/58 = 77.6% correct argument, `mixed` 0/3), s7 (`unknown_fact` 0/30 under T1, `distractor` 29/30), s8 (T2: 22/30 = 73.3%, `distractor` 30/30; 4 of the 8 misses are extra-argument grammar slips).
- **Kill / exit GATES:** (i) the 60-item LAB-07 suite replays to the same per-item outcomes as LAB-07 on the same binary and artifacts (greedy is deterministic; a difference means the harness changed); (ii) engine-port tokenizer parity 100% (S1b); (iii) HF-vs-engine step-0 parity on the incumbent: PPL gap <= 3% and token parity (precedents 0.19-0.20% ledger M12, 0.12% ledger B8, both via P-E); (iv) suite and scorer hashes committed to the private repo before S3 step 1. Any miss: stop.

### S1 Data factory, snapshot gateway, Python port
- **Do:** the generator emits prompt/target pairs by construction (expression -> `CALC(expr)` verbatim; key in question -> `LOOKUP(key)`; two- and three-call episodes over K steps; distractors; FILE-READ; near-miss keys; absent keys; unanswerable; **tool-state headers and `in_context_answerable` items, G2**) and keeps an episode only if it round-trips generate -> execute -> trace receipt -> verify through the real `agent_trace`. Key formats, schemas, table names and phrasings are randomized across at least 30 namespaces; 33-50% of names masked (R3 s7 item 2). In parallel build N1 (snapshot gateway, spec s7 items 1-4) and the Python port (G3).
- **Budget:** about 200k tool episodes + 80k unknown/unanswerable + 40k fact-check + 30k legality / in-context-answerable = about 350k episodes; about 65-100M tokens [est: 60-90M from P-E plus 30k episodes at about 220 tokens, where 220 = 0.1B tokens / 460k examples in P-E]. Connected episodes (40k) cannot be generated until N1 passes its own tests (spec s7 item 5).
- **Teacher / licence:** none. Aefinity-owned generator and outputs (repo LICENSE Apache-2.0 [checked: alice-aegis/LICENSE]). Free-form prose after a tool result comes from S3, not here.
- **Hyper-parameters:** irrelevance / no-tool share >= 10% (R3 s7 item 2); unanswerable >= 10% in every batch and stage (R4 s0 point 2); train-time keys, schemas and phrasings disjoint from the eval suite (file 04 s1).
- **Kill GATES:** (i) Python port vs Rust `agent_trace`: 0 mismatches over >= 1e6 random and edge CALC/LOOKUP cases (G3); (ii) 100% of kept episodes verify; if under 80% of generated episodes survive, the generator is wrong [plan GATE; no source supplies the 80%]; (iii) spec s7 tests pass: `search_then_fetch_chains_like_lookup`, `replay_equals_live_bytes`, `airgapped_never_scans_search`.

### S1b Engine-port tokenizer (G1)
- All training and eval text is tokenized with a Python port of `AegisTokenizer::encode` (tokenizer.rs). Judges J1 and J3 found the skew (file 01 s2.6). **GATE:** 100% identical ids to the Rust `encode()` on >= 10 MB of mixed ASCII text plus every gateway template (T2d-style, ledger B6 precedent 2410/2410 via P-Op). The HF-side dev scorer and the engine must see identical ids; PPL comparisons use identical ids.

### S2 Own-weights probing (R-Tuning style)
- **Do:** run the incumbent greedily over synthetic fact worlds and open QA pools; label each question by exact (alias) correctness. Distractor targets are the incumbent's own correct answers (no tool call); wrong answers with no declared table become abstain-with-reason targets; questions whose key is in a declared table become `LOOKUP` targets. Re-run after any base-changing stage (S7, S9): labels describe the weights they came from (R4 s0 point 1; R0 s7 item 10).
- **Budget:** 100-200k questions x <= 48 generated tokens = about 10M generated tokens; 60-100k labelled samples. **Teacher:** the incumbent, MIT (repo copy of the model card [checked: MICROSOFT_MODEL_CARD.md]; lineage caveats in file 03 rows A1-A3).
- **Pools:** synthetic worlds are the baseline (they need no external licence). NQ and HotpotQA are CC-BY-SA, TriviaQA and PopQA unspecified (R6 s8, s12 item 4): excluded until Justin decides.
- **Kill GATE:** each of known / unknown is >= 15% of the labelled pool [plan GATE], else widen the pool.

### S3 Operator SFT by context distillation plus rejection sampling, QAT in the loop
- **Student:** the bf16 master `microsoft/bitnet-b1.58-2B-4T-bf16` trained with transformers' native online BitLinear (absmean ternary weights, per-token absmax int8 activations, STE), assistant-only loss (R3 s7 item 1). Gold targets for tool grammar come from S1. Free-form text after a tool result comes from the incumbent's own samples under a long demonstration prompt, kept only if gateway-verified, then trained **without** the demonstration so the behaviour moves into the weights. Mix: tool 55%, unknown/unanswerable 15%, open-prompt replay 25%, format/IF 5% [plan choice, ablated; basis R4 s0 point 2 and R3 s7 item 2 for the 10% floors].
- **Training vocabulary (plan decision):** train on the pruned id space the engine serves, so the softmax the loss sees is the one the engine argmaxes over (G6, R2 s6 on masking and renormalising). Fallback if the HF class blocks slicing: full-vocabulary training with prune at export (the ledger E16c practice via P-E), and S0's prune-cost number then bounds the gap.
- **QAT audit (G5):** confirm the training forward quantizes activations at the five CIS-1 points (file 01 G5), including the final-norm output feeding the tied head. Step-0 logit parity HF vs engine is mandatory before any number is trusted (ledger M1: an inverted scale made outputs about 300x wrong, via P-E).
- **Budget:** pilot 5-20M tokens, then main 0.1B (Tier 0, about one week of GPU at 30 h/week, file s7) to 0.3-0.5B (Tier 1). About 460k examples = about 0.1B tokens (P-E).
- **Export contract:** E16 "unpacked ternary": int8 {-1,0,+1} plus F32 `_scale` siblings, 210 tensors; `repack_ternary.py --llama3-prune --max-seq 2048 --source-packing unpacked` with scale convention auto (ledger E16b/E16c via P-E).
- **Evidence the capability is trainable:** LAB-07 s8 (latent in context: exact-key LOOKUP 0/30 -> 22/30 with LOOKUP shots); R3 s4 and s9 (tool skill is a cheap post-training layer, O(10^8) tokens, <= 0.1% of pretraining); R2 s5 Path A (about 0.5B tokens, about 6 H100-h); ledger M17 (Kaggle 2xT4 online-QAT recipe passed) and A43 (QAT-fine-tuned checkpoint survives forge, CIS-full and receipts), both via P-E.
- **Kill GATES:** (i) no NaN, loss decreasing; (ii) held-out paired PPL ratio vs incumbent: hard stop above 1.05 at any checkpoint, flag above 1.02 (ledger E16c measured 30.71 -> 31.02 = +1.0% for 600 SFT steps, via P-E); (iii) after 0.1B tokens, `calc_easy`, `lookup_hit` and `distractor` >= 90% point estimate under P0 on the dev slice, else fix data before scaling; (iv) ceiling probes: doubling the tool data moves hard buckets by < 2 pp means the limit is capacity or grammar, not data (stop adding data).

### S4 Anti-forgetting: periphery-first arms and replay KL
- **Arms on identical S3 data:** **P** all ternary weights frozen; embeddings, norms and SubLN gains trainable. **L** full QAT at low LR. **H** full QAT at the E16 LR. WD 0 and a 10-20% cooldown in all (R5 s4, R1 s2d). Replay prompts carry a KL term to the frozen incumbent using cached top-16 logits plus log-sum-exp (reuse the method of the fm-5 teacher cache, ledger fm-5 via P-E and P-D1; the code is on branch `cm/fm5-deterministic-kd`, not in this checkout, so it is rewritten).
- **Instrument per checkpoint:** trit-flip fraction per tensor, p(0) census (incumbent 0.42, ledger ES1 via P-E), held-out PPL, IFEval (secondary), max residual bits per layer.
- **Evidence and its limit:** ledger M26 (14M-parameter ternary: freezing all ternary weights kept about 70% of the domain gain at about 5% of the forgetting). It is a 14M probe; replication at 2B is the point of the arms (P-E, J2, J3). Flip-rate figures quoted by P-E for M26 are 3.8e-4/step at LR 1e-5, 1.2e-3 at 1e-4, 1.2e-2 at 1e-3, and separately "11.6% of trits flipped per 100 steps at 1e-3"; the two are not mutually consistent as quoted, so read the unit from the ledger row before setting any flip tripwire. Until then flip fraction is logged, not gated.
- **Kill GATES:** an arm stops at PPL ratio > 1.05 vs incumbent; the arm to carry forward is the one with the best dev-slice gates among those with PPL ratio <= 1.02, else the least-damaging one is reported as a failure of rung A's non-regression.

### S5 Verifiable-reward RL
- **Do:** GRPO on short gateway episodes (<= 48 new tokens) from the best S3/S4 arm. Reward = ToolRL-style decomposed (format 0/1, tool name, exact argument, call order) plus TruthRL ternary (+1 correct, 0 abstain or ask, -1 wrong) on knowledge and unknown items; >= 10% unanswerable in every batch; a call on a distractor is penalised so abstention is always paired with must-call; no reference model (beta 0) with the replay KL kept on a side batch (R3 s7 item 5; R4 s0 point 2 and s1).
- **Budget:** 4k prompts first (ToolRL scale: Qwen2.5-3B BFCL v3 raw 33.04 -> SFT 41.97 -> GRPO 52.98; 1.5B 19.41 / 40.67 / 46.20; R3 s7 item 5, R0 s1 item 13, fp models not ternary), up to 20k prompts x group 8. About 8M-40M fwd/bwd tokens per epoch [est, P-E]. RL cost is the weakest number in this plan (R4 s6.4 flagged uncertain, written for multi-hop search RL).
- **Tooling:** hand-written loop (TRL is incompatible with BitNet in three ways, ledger M17 via J1). Python gateway port (G3) computes rewards; every logged winner is replayed through the real gateway. No ternary-policy RL precedent exists (R4 and R5 gaps).
- **Fallback:** rejection-sampling SFT with the gateway verifier (P-Op S6).
- **Kill GATES:** revert to the best SFT arm if any dev-slice bucket drops > 2 pp while training reward rises; stop if `in_context_answerable` < 95% or call rate on `calc_hard` < 97% (LAB-07 s5 target); stop if abstention on answerable look-alikes rises while call rate falls (R3 s7 item 3: refusal-only policies game irrelevance metrics, R0 s1 item 14).

### S6 Greedy consolidation and cooldown
- Receipts are greedy, RL is sampled (brief s1). Decode the RL policy greedily on fresh gateway prompts, keep verified winners, run a short SFT (RL -> SFT) with a 10-20% LR cooldown (R1 s2d, R5 s4), export through the E16 contract. **Budget:** 20-50M tokens. **Kill GATE:** greedy dev gates after S6 are >= the best earlier checkpoint on every bucket, else keep the earlier checkpoint. No sampled number is ever reported.

### S7 Rung B: importance-ranked structured pruning
- **Do:** activation-based importance on 1024 calibration sequences x 2048 tokens (about 2.1M tokens; S3/S4 mix plus open text), following the Minitron practice paper (arXiv 2408.11796, outside R0-R9, not checked by R0-V). Rank hidden channels (summed over layers; applied to embeddings, RMSNorm and SubLN gains), attention heads in GQA groups (20/5 -> 16/4), FFN neurons (magnitude x firing frequency; ReLU2 gives 78.9% exact zeros at down_proj inputs, ledger A15 via P-E, which counts per-token zeros, not per-neuron frequency), and layers (block influence). Protect massive-activation channels (top down_proj channel covers 12-98.5% of tokens in 8 of 30 layers, ledger E3 via P-E). Prune only along config fields the engine reads.
- **Arms:** S4 (24L, d2048, ff5120), W (30L, d2048, ff4096), D (17L, d2560, ff6912), V (S4 plus 32,256 ids; G6 gate to choose N). Width-first is the prior (Minitron-4B: width beat depth, MMLU 60.5 vs 58.7, GSM8K 41.2 vs 16.8, arXiv 2408.11796 via P-E) against R1 s0 point 3 and s2a depth-wins-at-fixed-tokens (Falcon-H1 hybrid, not ternary), so the ablation decides.
- **Score each arm at 0 healing tokens:** CIS-exact PPL on a fixed slice, tool-bucket pass-through, max residual bits.
- **Kill GATES:** none on quality at 0 tokens (a pruned net is expected to be broken; this stage ranks, it does not select). Stop an arm on non-finite outputs or a CIS range panic (spec s3 residual n <= 8192; q/k/v bounds).

### S8 Rung B: heal by distillation from rung A
- **Loss:** logit KL to rung A plus MiniLM-style attention/hidden-state loss (BitDistill, R2 s2). Tier-0 pilots use cached top-16 teacher logits, so they are logit-KL only; the attention/hidden term is first tested on Tier 1 with an online teacher. Healing a ternary net is re-learning, not fine-tuning: about 40% of weights move in the 2-bit transition (ParetoQ, R2 s2; R7 s7).
- **Mix:** about 70% open Tier-A text (the incumbent's own disclosed source families: SmolLM-Corpus, dclm-baseline-1.0, open-web-math; plus FineWeb-Edu, FineMath, Stack-Edu), ASCII-filtered and decontaminated against every eval item; about 30% operator data from S1 (P-E, R6 s10). Rung A's teacher forward adds 2 x 2.213B per token, +55-66% over the student's own step here [arith, R7 s2 method].
- **Budget:** not fixed in advance. Staged release in s6. For scale, comparable float recoveries cost 94B tokens for Minitron-4B (arXiv 2408.11796, outside R0-R9), about 213B for Nemotron Elastic 9B -> 4B (R1 s2f, Table 1) and up to 9T for Llama 3.2 (R1, R7 via P-E). ParetoQ saturates near 30B QAT tokens (R2 s2). R5 s3: converting over-trained models loses 6-8 points; the incumbent is already about 1,660 tokens per parameter [arith: 4T / 2.4B].
- **Kill GATES:** s6.

### S9 Optional continued pretraining or anneal
- Rung A only if S6 leaves paired PPL ratio > 1.02: at most 1-5B tokens (Tier 1) of Tier-A text with KD to the incumbent. Rung A's self-distillation cannot beat its teacher; improving PPL needs CE on fresh data and there is no evidence it helps a 4T-token model (P-E; ledger E16c datum). For rung B it is the 70% text share of S8, not a separate pass. **Kill GATE:** skip unless the S6 condition holds; stop if held-out PPL does not improve by >= 1% (paired) after 1B tokens [plan GATE].

### S10 Export, engine and boot gate
- Pipeline in file 04 s8. No stage ships without it. Every shipped shape needs its own golden receipt, forge run, CIS-full PPL and boot.

## 3. QAT details common to S3-S8
- Online BitLinear: weights absmean-ternarized per tensor with STE; activations per-token absmax int8; fp32 master weights. The engine's CIS-1 integer path computes in i32/i64 with fixed rounding, so training-time fake-quant is an approximation of it. Agreement is measured, not assumed: step-0 parity, then CIS-full int-vs-float at every milestone (A35 +0.1239% on the incumbent, A41 +0.70% on Falcon-E, both via P-E and P-D1).
- ReLU2 requires SubLN in the engine (`model.rs` refuses relu2 without sub-norms); the incumbent has them, rung B keeps them. No biases.
- Latent-weight conventions: weight decay 0 so flips do not continue by decay (R5 s4: WD acts on the latent weights whose magnitude is the "confidence" of the ternary value).
- Tier-0 numerics: T4 has no bf16; fp32 weights + fp16 AMP, gradient checkpointing, paged 8-bit AdamW (ledger M17 via P-E). A fp16-vs-CPU-bf16 check on 20 prompts runs first (G12; ledger M18 via P-D1 records fp16 numerics destroying another ternary kernel).

## 4. Hyper-parameter register
"cited" = value comes from the named source; "plan" = the plan author's choice, with its basis, to be swept as stated; no source supplies it.
| Parameter | Starting point | Source or basis | Class |
|---|---|---|---|
| Precision, Kaggle | fp32 weights + fp16 AMP, grad checkpointing, paged AdamW 8-bit, seq 1024, device_map auto over 2xT4, pad = eos, trust_remote_code off | ledger M17 (via P-E); R7 s5 (T4 no bf16) | cited |
| Adam betas | (0.9, 0.95) | R5 s4 (from-scratch ternary recipes) | cited, applied to fine-tuning by plan |
| LR arm H | 1e-4 | ledger E16 / A43 (via P-E) | cited |
| LR arm L | 3e-5 (range 1e-5 to 3e-5) | basis: ledger M26 flip-rate ordering (via P-E) | plan |
| LR arm P | 1e-4, swept {1e-4, 3e-4} | no ternary flips by construction | plan |
| Schedule | cosine; warmup 10 steps (Kaggle); 375 steps on rented runs; WSD with 10-20% cooldown for S6 and S8 | P-E notebook; R5 s4 (warmup 375); R1 s2d (cooldown, 1-sqrt beats linear) | cited |
| Weight decay | 0 | R5 s4 mechanism; P-E | cited |
| Batch | Kaggle 1 x accum 16 x 1024 = 16,384 tokens/step; rented 0.5-1M tokens at seq 2048 | P-E; R5 s4 (1M tokens, seq 2048) | cited / plan |
| Loss mask | assistant-only | R3 s7 item 1 | cited |
| Name masking | 33-50% of function/key/table names | R3 s7 item 2 (Hammer ablation 0/33/50/67%) | cited |
| No-tool and unanswerable share | each >= 10% of every batch | R3 s7 item 2; R4 s0 point 2 | cited |
| S3 mix | tool 55 / unknown+unanswerable 15 / replay 25 / format-IF 5 | P-E | plan, ablated |
| Replay KL | cached top-16 logits + LSE; coefficient 1.0, swept {0.3, 1, 3} | method: fm-5 cache (ledger via P-E); anchor motivation R2 s1 (on-policy recovery of IFEval 79 -> 83 after fine-tuning damage) | plan |
| GRPO | group 8, beta 0, LR <= 1e-5, 4k then 20k prompts | R3 s7 item 5 (scale, reward shape); LR basis M26 | cited / plan |
| Reward | format 0/1 + tool + exact argument + order; ternary +1/0/-1 | R3 s7 item 5; R4 s1 | cited |
| Prune calibration | 1024 sequences x 2048 tokens | arXiv 2408.11796 (outside R0-R9) | cited, unverified by R0-V |
| Heal LR grid | {3e-5, 1e-4, 3e-4, 1e-3} x 20M tokens on shape S4 only | converting Llama-3-8B used about 1e-4 / 1e-5 (P-D1 via R2 s2); from-scratch ternary 1.2e-3 to 1.5e-3 (R5 s4) | plan |
| Heal loss | KL (T = 1, swept {1, 2}) + attention/hidden term on online-teacher runs | R2 s2 (BitDistill); fm-5 used T = 2, top-64 (ledger via P-D1) | cited / plan |
| Heal mix | about 70% Tier-A text / 30% operator | P-E; R6 s10 | plan |
| Cooldown fraction | 10-20% of the stage | R1 s2d | cited |

## 5. Teachers and licences
| Teacher | Used in | Licence | Status |
|---|---|---|---|
| BitNet-b1.58-2B-4T incumbent (self) | S2 labels, S3 context distillation, S4 replay anchor, S7/S8 init | MIT (repo copy of the model card, lines 2 and 139-140 [checked]; HF card and LICENSE read by P-E on 2026-10-06). The same card advises against commercial use "without further testing" (line 152 [checked]) | licence verified; **lineage unresolved**, file 03 rows A1-A3 |
| Rung A (tuned) | S8 teacher | derived from the row above | inherits the same lineage |
| External teachers | none in this plan | n/a | The "no external teacher" claim is about NEW teachers only. It must not be stated as "no external model output in the chain" |
| Plan C only (not used here): Qwen3 family | D1 or Op surface forms | Apache-2.0, no naming clause (R0 s3; R2 s4) | would end the no-external-teacher claim; Justin's decision (R0 s7 item 16) |

## 6. Rung B staged release and go/no-go (replaces P-E's single rule; J3)
**Prior, stated first.** On the one ternary scaling fit in the briefs (R5 s2: L = 2.19 + 4.73/N^0.32 + 5.18/D^0.81, N in millions non-embedding, D in billions) a 1,006.6M-body model sits 4.73 x (1/1006.6^0.32 - 1/2084^0.32) = 0.108 nats behind the 2,084M body at infinite tokens (+11% PPL), and 0.19 nats (+21%) at D = 150B against D = 4,000B [arith, reproduced]. The gate allows ln 1.05 = 0.049 nats. R5 s2 warns the fits are not cross-comparable and the range is 99M-1.1B at 20-150B tokens, and a pruned init inherits knowledge, so this is directional. Rung B is therefore expected to miss the strict "<= 5% worse at <= half the bytes" branch unless healing beats the prior. P-E's original rule (monotone decline over three checkpoints and a log-log extrapolation from a 0.1B pilot) would pass almost surely and extrapolates three decades (J3), so it is replaced.

| Step | Spend | Rule (all GATES) |
|---|---|---|
| B0 | 0 tokens | Score four arms at 0 tokens (S7). Rank only. |
| B1 pilot | Tier 0: 0.1B tokens per arm if measured throughput >= 100M tokens/week, else the top two arms by B0 rank | Pick the arm: paired held-out PPL gap to rung A (full WikiText-2 via the HF reference plus the fixed slice) is non-increasing over the last 3 checkpoints and the arm beats the others on paired CI. Selecting an arm releases no money. |
| B2 Tier 1 | about $355 at median price (8.0B tokens), about $390 at community price (12.0B); file s7. Needs Justin's GO (money is a NEEDS item) | Heal the chosen arm with checkpoints at 1B, 2B, 4B, 8B. |
| B3 Tier 2 release | up to the Tier-2 remainder in s7 | ALL of: (a) paired PPL gap to rung A at the last B2 checkpoint <= +15% [GATE chosen as 3x the 5% target; no evidence base; Justin may amend before pre-registration]; (b) **pessimistic extrapolation** g(t) = g_last - s x ln(t / t_last), with s the smaller of the last two observed per-e-fold slopes, lands at <= +5% (ln 1.05 = 0.049) at the Tier-2 token count; for example from a +15% gap (0.140 nats) at 8B tokens to 100B tokens requires s >= (0.140 - 0.049) / ln(100/8) = 0.036 nats per e-fold [arith]; (c) `calc_easy`, `lookup_hit`, `distractor` under P0 within -5 pp of rung A (point estimates; plan GATE) and no CIS range violation; (d) Justin's GO. |
| B4 Tier 2 | checkpoint-wise eval every 10B tokens | Stop if the observed slope falls below the (b) requirement for two consecutive intervals. |
| Negative | | Freeze rung B as a documented negative (it is a valid result: first measured pruning of a ternary network), ship rung A with the honest size statement, open the Plan C decision (file 05 s5). |

## 7. Compute per tier (all [arith] or [est]; no result implied)
**Inputs.** Effective H100 = 989 TFLOPS dense bf16 x 40% MFU = 395.6 TFLOPS = 1.424e18 FLOP per H100-hour (R7 s2 assumption; its bounds are 35-45%; MFU of ternary fake-quant kernels is unmeasured in any source, R5 s6). Ternary overhead x1.2 (R7 s3; one data point, Falcon-E, R5 s4). Prices per H100-hour (R7 s4, read 2026-10-06): $3.63 market median, $2.69 community SXM, $0.89 spot; flat-to-rising, not falling. Programme multiplier 1.4 on compute lines (R7 s6: 1.3-1.5 for restarts, ablations, evals); spot waste of 10-20% is NOT included. At 30% MFU every H100-hour figure rises by 1.33x.

**Per-token FLOPs** [arith; N_A = 2.2127B, N_B = 1.1096B]: rung A SFT 6 x N_A x 1.2 = 15.93 GFLOP; rung A SFT with a same-size KL teacher 15.93 + 2 x N_A = 20.36 GFLOP; rung B heal with rung-A teacher 6 x N_B x 1.2 + 2 x N_A = 12.41 GFLOP. **H100-hours per 1B tokens** = FLOP per token x 1e9 / 1.424e18: 11.19, 14.29 and 8.72 respectively. Cross-check: R2 s5 Path A puts about 0.5B SFT tokens at about 6 H100-h; here 0.5B = 5.6 h without and 7.1 h with the KL teacher. **Rung B heal cost per 1B tokens** = 8.72 h x price x 1.4: $44.3 at $3.63, $32.8 at $2.69, $10.9 at $0.89.

### Tier 0: Kaggle free plus fleet CPUs ($0)
- **Hardware:** Kaggle T4 x2 (about 30 GPU-h per week per brief s3; the quota API reports a 6 h raw field that is unexplained), box1 (i5-5200U AVX2), box2/box3 (N4020, no AVX2), penguin for CPU work only. TPU is not assumed (Kaggle silently downgraded a TPU request, ledger M23 via P-E and P-D1).
- **Measured anchor:** 150 steps x 4096 tokens in 686.9 s = 894 tok/s on 2xT4 (ledger M17 and `state/reports/2026-08-29-kaggle-compute-facts.md`, via P-E; real token counts are lower because the sequences were short and padded). x 3600 x 30 h = **96.6M tokens/week** at 30 h; **19.3M/week** at the 6 h reading [arith].
- **Rung B pilot throughput [est]:** 894 x 15.93 / 12.41 = 1,148 tok/s = 124M tokens/week at 30 h, 25M/week at 6 h. The FLOP ratio assumes equal MFU; Notebook 1 measures rung A's real rate and nothing measures rung B's.
- **Buys:** all CPU work (factory, snapshot gateway, decontamination, harness, importance scoring, receipts and boot legs). S3 at 0.1B tokens = 1.04 weeks at 30 h (5.2 weeks at 6 h); S3 + S4 + S6 in about 4-6 weeks; S5 on short episodes is plausible but unmeasured; four rung-B pilots of 0.1B tokens = 3.2 weeks at 30 h (16 weeks at 6 h), hence the top-two rule in s6.
- **Cannot reach:** rung B healing beyond about 1B tokens (10B = 81 weeks at 124M/week [arith]); any CPT at scale; GRPO with long rollouts; ctx > 1024 training; a reliable weekly budget.
- **Memory [est]:** rung B student fp32 master 4.4 GB + grads 4.4 GB + 8-bit Adam about 2.2 GB leaves little of one 16 GB T4 for activations; the teacher is therefore not held resident, which is why pilots use cached top-16 logits.

### Tier 1: about $500 of rented GPU
Allocation, with rung A completed first and the remainder to rung B heal [arith]:
| Line | $3.63 | $2.69 | $0.89 spot |
|---|---|---|---|
| H100-hours in $500 | 137.7 | 185.9 | 561.8 |
| S3 at 0.5B tokens with KL teacher: 7.15 h x 1.4 = 10.0 h | $36.3 | $26.9 | $8.9 |
| S5 RL pilot, capped at 30 H100-h (a cap, not an estimate; RL cost is the weakest number, R4 s6.4) | $108.9 | $80.7 | $26.7 |
| Remainder for rung B heal | $354.8 | $392.4 | $464.4 |
| Rung B heal tokens that buys | **8.0B** | **12.0B** | **42.8B** (about 34-38B after 10-20% spot waste) |
| For reference, all $500 to heal | 11.3B | 15.2B | 46.0B |
- **Cannot reach:** rung B at >= 30B tokens at median price; both rungs plus a deep shape ablation; CPT of rung A at 10B+; any from-scratch work.

### Tier 2: about $5,000 of rented GPU (cumulative envelope, includes any Tier-1 spend)
| Line | $3.63 | $2.69 | $0.89 spot |
|---|---|---|---|
| H100-hours in $5,000 | 1,377 | 1,859 | 5,618 |
| S3 + S5 as in Tier 1 | $145.2 | $107.6 | $35.6 |
| Shape ablation: top two arms x 5B tokens = 10B | $443.0 | $328.3 | $108.6 |
| Remainder for rung B heal | $4,411.8 | $4,564.1 | $4,855.8 |
| Rung B heal tokens | **about 100B** | **about 139B** | **about 447B** (about 360-400B after waste) |
| For reference, all $5,000 to heal | 112.9B | 152.3B | 460.4B |
- Released only if the s6 rule fires. About 100B tokens is the same order as Minitron-4B's 94B plus teacher correction, but those are float models and no source measures pruning a ternary network.
- **Cannot reach:** a from-scratch ternary base (about 6,100 H100-h for 1.2B x 1T, R5 s6, about $22k at median incl. x1.2 per R0 s4); the 213B-to-9T class of recovery budgets; evidence that pruning a ternary network recovers at this budget.

### Stage kill summary (every row a GATE; details above)
| Stage | Stop if |
|---|---|
| S0 | LAB-07 suite replay differs; parity gap > 3%; hashes not committed |
| S1 | oracle mismatch > 0 in 1e6 cases; kept-episode verify < 100%; spec s7 tests fail |
| S1b | tokenizer parity < 100% |
| S3 | NaN; PPL ratio > 1.05; `calc_easy` / `lookup_hit` / `distractor` < 90% at 0.1B tokens |
| S4 | arm PPL ratio > 1.05 |
| S5 | any dev bucket -2 pp with reward rising; `in_context_answerable` < 95%; `calc_hard` call rate < 97% |
| S6 | greedy dev gate below the best earlier checkpoint |
| S7 | non-finite output or CIS range panic |
| S8 | s6 B3 conditions fail, or B4 slope requirement missed twice |
