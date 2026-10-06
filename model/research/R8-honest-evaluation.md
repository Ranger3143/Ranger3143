> Research brief produced on 2026-10-06 by a web-research agent for the ALICE-Next model plan. Every claim carries the URL the agent read; items it could not verify are listed under Gaps. Numbers here are the cited papers' numbers, not Aefinity measurements.

# ANGLE 8 — Honest evaluation for ALICE-Next (1–3B, CIS-1, tool expert, calibrated abstention)

Research analyst brief, Aefinity AI Inc., 2026-10-06. Sources are primary (arXiv, HF cards, GitHub, leaderboard pages) unless marked [uncertain]. Web search was unavailable this turn; everything below was fetched directly, so coverage of very recent (Q3 2026) papers is thinner than I would like — see Gaps.

## 1. What 2024–2026 taught about contaminated and noisy evals

**Contamination inflates scores more than release notes admit.**
- GSM1k (Scale AI, 2405.00332): a fresh GSM8K-equivalent; accuracy drops of up to 8% for some families, Spearman r²=0.36 between a model's likelihood of emitting GSM8K items and its GSM8K−GSM1k gap. https://arxiv.org/abs/2405.00332
- Retro-Holdouts (2410.09247): a statistically indistinguishable holdout for TruthfulQA ("Retro-Misconceptions") shows some models inflated by up to 16 percentage points. https://arxiv.org/abs/2410.09247
- Wu et al. (2507.10532, AAAI 2026): Qwen2.5-Math-7B reconstructs the missing 40% of MATH-500 problems from the first 60% with 54.6% exact match and answers 53.6% of those truncated problems correctly; Llama-3.1-8B: 3.8% / 2.4%. On their clean RandomCalculation generator, random/incorrect RL rewards stop "working". https://arxiv.org/abs/2507.10532
- ConStat (2405.16281) redefines contamination as non-generalizing performance (primary vs rephrased/synthetic reference benchmark, relative to reference models) and finds it in Mistral, Llama, Yi and the then top-3 Open LLM Leaderboard models. https://arxiv.org/abs/2405.16281
- ConTAM (Meta, 2411.03923): contamination "may have a much larger effect than reported in recent LLM releases"; longest contaminated substring beats union-of-matches; use larger n and drop infrequent matches. https://arxiv.org/abs/2411.03923
- The Leaderboard Illusion (2504.20879): 27 private Llama-4 variants on Chatbot Arena; Google/OpenAI ≈19.2%/20.4% of all Arena data vs 29.7% for 83 open-weight models combined; extra data gives up to 112% relative gains on the Arena distribution. https://arxiv.org/abs/2504.20879
- "Training on the test task" (2407.07890, ICLR 2025 oral): not leakage, but unequal task-format exposure confounds comparisons and manufactures "emergence"; fix = fine-tune every compared model on the same task-relevant data first. https://arxiv.org/abs/2407.07890
- Mitigation is weak: Sun et al. (2503.16402) test 20 mitigation strategies × 10 LLMs × 5 benchmarks — none significantly beats "no update" across benchmarks. https://arxiv.org/abs/2503.16402
- 2026: Zero-CoT Probe (2605.21856) detects paraphrase-evasive contamination by truncating the reasoning chain and comparing to isomorphic references; UBD (2606.23313) measures inflation at sample level via distributional distance to an uncontaminated model (MMLU-Pro, MATH-MCQA). https://arxiv.org/abs/2605.21856 , https://arxiv.org/abs/2606.23313

**Label noise caps what "100%" means.** MMLU-Redux 2.0 re-annotates 5,700 MMLU items (100 per subject): 6.49% erroneous overall, 57% in Virology (2406.04127, NAACL 2025; CC-BY-4.0). GSM8K-Platinum: of 1,319 test items, 219 flagged, 110 rejected, 10 relabeled → 1,209 items (2502.03461; annotations CC-BY-SA-4.0, base MIT). SimpleQA Verified (2509.07968, revised 2026-03-10): 1,000 prompts de-duplicated, topic-balanced, source-reconciled; Gemini 2.5 Pro F1 55.6. https://huggingface.co/datasets/edinburgh-dawg/mmlu-redux-2.0 , https://huggingface.co/datasets/madrylab/gsm8k-platinum , https://huggingface.co/datasets/google/simpleqa-verified

**Decontamination practice actually used by labs**
| Lab / tool | Rule |
|---|---|
| GPT-3 → lm-eval-harness `decontamination.md` | 13-gram overlap with any training doc flags the eval doc; report metric and `_decontaminate` variant (clean vs dirty). https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/decontamination.md |
| Qwen2.5 Tech Report (2412.15115, §5) | drop training sequence sₜ if ∃ test sₑ with LCS(tokenised sₜ, sₑ) ≥ 13 tokens AND ≥ 0.6·min(|sₜ|,|sₑ|); applied to pre- and post-training data for all open benchmarks. https://arxiv.org/html/2412.15115 |
| Ai2 open-instruct `decontamination/` | Elasticsearch index of training data; n-gram (configurable `ngram_size`) and embedding search; instance-level 0/1 at a threshold; default query set = Tülu 3 eval suite. https://github.com/allenai/open-instruct/blob/main/decontamination/README.md |
| LLM-decontaminator (2311.04850) | paraphrase/translation defeats n-gram; 8–18% of HumanEval found in RedPajama/StarCoder data; a 13B trained on rephrased tests matched GPT-4. https://arxiv.org/abs/2311.04850 |
| Cross-lingual (2406.13236) | translated test sets evade overlap checks; detect by swapping distractors with correct answers from other items. https://arxiv.org/abs/2406.13236 |
| Benchmark Transparency Card (2404.18824) | disclose which benchmark train splits were used; perplexity + n-gram-accuracy leakage detection across 31 math models. https://arxiv.org/abs/2404.18824 |
| CapBencher (2505.18102) | publish a benchmark with randomized multi-correct answers so Bayes accuracy is capped; exceeding the cap is a contamination alarm. https://arxiv.org/abs/2505.18102 |

## 2. Statistics: error bars, paired tests, variance

- Miller, *Adding Error Bars to Evals* (2411.00640): treat items as a sample from a super-population; CLT standard errors, clustered SEs when items share a source, paired differences for model-vs-model, and power analysis. https://arxiv.org/abs/2411.00640
- Bowyer et al. (2503.01747): CLT intervals are too narrow below a few hundred items; use Bayesian/Clopper–Pearson/Wilson/bootstrap (library provided). https://arxiv.org/abs/2503.01747
- Madaan et al. (2406.10229): seed variance is material at ~7B; framing MMLU as completion reduces it. https://arxiv.org/abs/2406.10229
- Heineman et al., *Signal and Noise* (Ai2, 2508.13144; 30 benchmarks, 375 models 60M–32B): prefer high-signal/low-noise metrics for small-scale decisions (perplexity-type > accuracy), filter noisy subtasks, average checkpoints. https://arxiv.org/abs/2508.13144
- Judge-based scores: Lee et al. (2511.21140, ICML 2026) estimate judge sensitivity/specificity on a human-labelled calibration set, debias, and give CIs that include calibration uncertainty. https://arxiv.org/abs/2511.21140 MT-Bench's original judge study reports >80% judge–human agreement but position, verbosity and self-enhancement bias (2306.05685).
- Prompt fragility: a 2026 audit (2605.02038; 15 models × 5 prompt variants) finds changing the ECE definition moves per-cell calibration by 0.149 mean absolute, verbal confidence sits above token-probability confidence on MMLU-Pro, and robustness barely correlates with size. https://arxiv.org/abs/2605.02038
- Tool-eval validity: *Benchmarking the Benchmarks* (2607.02577, 2026-06-30) audits BFCL v4, τ²-bench, LiveMCPBench, MCP-Atlas: 92 evaluator–human disagreements over 496 expert-reviewed tasks (18.5% misalignment); 23 reruns of one LiveMCPBench setup span 57.9–76.8% (18.9 pp). Failure taxonomy: brittle state matching, trajectory lock-in, wrong ground truth, rubric drift, run-to-run variance. https://arxiv.org/abs/2607.02577
- McNemar (Dietterich 1998, *Neural Computation* 10(7):1895–1923) remains the right paired test for two systems on the same items: exact binomial on discordant pairs b vs c. Sizing rule of thumb at p≈0.5 (Wilson half-width): n=164 → ±7.7 pp; 378 → ±5.0; 500 → ±4.4; 541 → ±4.2; 817 → ±3.4; 1,000 → ±3.1; 1,209 → ±2.8; 5,700 → ±1.3; 12,032 → ±0.9.

## 3. Benchmark set for a 1–3B general + tool model (sizes, licenses, status)

| Set | Size | License | Notes |
|---|---|---|---|
| MMLU-Redux 2.0 | 5,700 | CC-BY-4.0 | error-corrected MMLU; 6.49% original error rate |
| MMLU-Pro | 12,032 (10 options) | MIT | prompt-variation sensitivity 2% vs 4–5% for MMLU (2406.01574); HF `benchmark:official`. No established "MMLU-Pro-lite" artifact found on the Hub [uncertain]; use a tinyBenchmarks-style IRT subset (100 items reproduce MMLU, 2402.14992) only for dev loops |
| GSM8K-Platinum | 1,209 | MIT + CC-BY-SA-4.0 | drop-in for GSM8K test (1,319) |
| MATH-500 | 500 | via openai/prm800k [license uncertain] | subset of MATH *test*; disclose any MATH-test training |
| HumanEval+ / MBPP+ | 164 / 378 | Apache-2.0 | 80×/35× more tests than originals (EvalPlus) |
| IFEval / IFBench | 541 prompts, 25 types / 58 unseen constraints | Apache-2.0 / ODC-BY-1.0 | IFBench exists because models overfit IFEval's constraint set (2507.02833, NeurIPS 2025) |
| BFCL v4 (2025-07-17) | web search 200, memory 465, format sensitivity 5,200; multi-turn 800 scored (base 200 + missing-param 200 + missing-func 200 + long-context 200; composite 200); non-live 1,390; live 2,251 | Apache-2.0 | overall = Agentic 40% + Multi-turn 30% + Live 10% + Non-live 10% + Hallucination 10%; relevance/irrelevance (240 non-live) measures tool hallucination; leaderboard last updated 2026-04-12 |
| τ-bench / τ²-bench | retail 115, airline 50, telecom 114 (of 2,285 generated) | MIT | pass^k = all k independent runs succeed; user simulator gpt-4.1 (external dependency); repo says tasks frozen, use τ³-bench successor [uncertain] |
| When2Call (NVIDIA, 2504.18851, NAACL 2025) | — | [uncertain] | decide call / ask follow-up / cannot-answer / answer directly; SOTA tool models over-call |
| ToolBeHonest (2406.20015) | 700 | [uncertain] | solvability detection, planning, missing-tool analysis; Gemini-1.5-Pro 45.3, GPT-4o 37.0 /100 |
| SimpleQA / SimpleQA Verified | 4,326 / 1,000 | MIT / MIT | grades correct / incorrect / not attempted; F = harmonic mean(overall correct, correct-given-attempted); must be run without tools |
| AbstentionBench (Meta FAIR, 2506.09038) | 20 datasets + 3 reasoning variants, >35k unanswerable Qs, capped 3,500/dataset | CC-BY-NC-4.0 (eval only) | metrics abstention recall/precision/F1; judge Llama-3.1-8B-Instruct, 88% agreement with humans; reasoning fine-tuning degrades abstention 24% on average; best avg recall 0.71 (Qwen2.5-32B), Llama-3.1-8B 0.66 |
| TruthfulQA (MC) / HaluEval | 817 / 35,000 | Apache-2.0 [uncertain] / [uncertain] | TruthfulQA inflation shown by retro-holdout; HaluEval has recognition subtask |
| FreshQA (2310.03214) | 600 (never/slow/fast-changing, false-premise) | [uncertain] | RELAXED/STRICT grading; natural connected-variant test |
| FRAMES (2409.12941) | 824 multi-hop | [uncertain] | no-retrieval 0.40 → multi-step retrieval 0.66 (frontier) |
| LiveBench (ICLR 2025 spotlight) | monthly refresh; objective ground truth, no judge | [uncertain] | freshness control |
| LiveCodeBench | date-windowed LeetCode/AtCoder/Codeforces | [uncertain] | select window after training cutoff |
| MT-Bench / Arena-Hard-Auto / WildBench | 80 / 500 / 1,024 | — | judge-based; WildBench WB-Score r=0.95 with Arena Elo, length-bias tie rule |

**Reference numbers for gate-setting (vendor-reported, different harnesses — use only to bracket, never to compare):**
- ALICE-1 = BitNet b1.58-2B-4T card (MIT): MMLU 53.17, GSM8K 58.38, MATH-500 43.40, HumanEval+ 38.40, IFEval 53.48, TruthfulQA 45.31, MT-Bench 5.85; 0.4 GB non-embedding memory, 29 ms/token CPU decode. https://huggingface.co/microsoft/bitnet-b1.58-2B-4T
- Qwen3-1.7B non-thinking (Qwen3 report, Table 20): MMLU-Redux 64.4, MATH-500 73.0, LiveCodeBench v5 11.6, BFCL v3 52.2, IFEval strict-prompt 68.2, Arena-Hard 36.9, LiveBench 35.6. https://arxiv.org/html/2505.09388
- Llama 3.2 3B Instruct (2024-10-24, Llama 3.2 Community License): IFEval 77.4, GSM8K 77.7, MATH 48.0, BFCL v2 67.0, MMLU 63.4; 1B: BFCL v2 25.7. https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/MODEL_CARD.md
- LFM2-1.2B (LFM Open License v1.0): MMLU 55.23, IFEval 74.89, IFBench 20.7, GSM8K 58.3. https://huggingface.co/LiquidAI/LFM2-1.2B
- SmolLM3-3B (Apache-2.0, 2025-07-08) no-think: IFEval 76.7, GSM-Plus 72.8, LiveCodeBench v4 15.2, GPQA-D 35.7, "BFCL" 92.3 — HF's BFCL subset, not comparable to BFCL v3/v4 overall. https://huggingface.co/HuggingFaceTB/SmolLM3-3B

## 4. Leaderboards relevant to small models (state on 2026-10-06)

- **Open LLM Leaderboard v2** (IFEval, BBH, MATH Lvl 5, GPQA, MuSR, MMLU-Pro via lm-eval-harness) is archived; HF's leaderboard docs now describe it in the past tense; the `open-llm-leaderboard/contents` dataset holds 4,576 rows. Archival date not verified here [uncertain; widely reported as March 2025]. https://huggingface.co/docs/leaderboards/index
- **HF Eval Results (the 2026 successor, "work in progress")**: datasets tagged `benchmark:official` carry an `eval.yaml` and auto-build leaderboards from `.eval_results/*.yaml` files in model repos (fields: dataset id, task_id, value, optional revision, date, source URL, notes, `verifyToken`). "verified" badge only when the run executed in HF Jobs with inspect-ai; otherwise "community" (open PR) or "source". MMLU-Pro and GSM8K are official benchmarks; an unofficial index counts 48 official benchmarks (44 with entries, ~1,024 entries; MMLU-Pro ≈141 entries, GPQA ≈111). https://huggingface.co/docs/hub/eval-results , https://huggingface.co/spaces/quantid/huggingface-official-benchmark-leaderboards
- **Open SLM Leaderboard** (AxiomicLabs, created 2026-05-27): sub-150M models only (HellaSwag, ARC, PIQA, ArithMark-3) — not applicable to 1–3B. **Intel Low-bit Open LLM Leaderboard** (updated 2026-07-09) is the relevant venue for ternary/int8 comparisons. https://huggingface.co/spaces/Intel/low_bit_open_llm_leaderboard
- **Vectara Hallucination Leaderboard**: HHEM-2.3 over >7,700 articles, updated 2026-09-22; smallest listed: Qwen3-4B 5.7%, Gemma-3-4b-it 6.4%, Ministral 3B 7.3% hallucination rate. https://github.com/vectara/hallucination-leaderboard
- **MLPerf Client**: v2.0.0 2026-08-18, v2.0.1 2026-09-24 (GitHub release feed); base models Llama 3.1 8B and Phi 4 Mini Instruct (Phi 3.5 removed), Phi 4 Reasoning 14B extended, Qwen3 8B and Flux 2 Klein 4B experimental; metrics TTFT, tokens/s, images/min, agentic end-to-end; platforms AMD/Intel/NVIDIA/Qualcomm/Apple, Windows/macOS/iPadOS/Ubuntu. No 2B-class or CPU-only track, so ALICE-Next cannot be scored there; adopt its TTFT/TPS definitions for our own report. https://mlcommons.org/benchmarks/client/ , https://github.com/mlcommons/mlperf_client/releases
- **BFCL** leaderboard (last updated 2026-04-12) is the only live tool leaderboard; per-model rows were not retrievable via static fetch [gap].

## 5. Measuring "knows when it does not know"

Metrics, with the definition we will pin:
1. **Selective prediction** (Geifman & El-Yaniv 2017, 1705.08500): risk–coverage curve from a confidence score; report AURC and selective accuracy at 50/70/90% coverage. Confidence sources: (a) CIS-1 fixed-point answer log-probability — exact integers, so the score itself is replayable; (b) verbalized confidence (better calibrated than token probabilities for RLHF models, ~50% ECE reduction, 2305.14975); (c) P(True)/P(IK) self-evaluation (2207.05221).
2. **Calibration**: ECE with 15 equal-mass bins *and* smoothECE (kernel-smoothed, hyperparameter-free; `relplot`, 2309.12236) plus Brier score — because binned ECE is discontinuous and definition changes alone shift results by 0.149 (2605.02038).
3. **Abstention F1**: AbstentionBench recall/precision/F1 (judge-free keyword detector plus our own judge; publish agreement with the paper's Llama-3.1-8B judge); Xu et al.'s precision/recall/"Rely" for refusing unknowns (2403.18349); SimpleQA's three-way grade with F-score and hallucination-on-attempted.
4. **Scoring that stops rewarding guesses**: Kalai et al. (2509.04664) argue benchmarks should penalize confident errors; report every QA set at a stated threshold t (score +1 correct, 0 abstain, −t/(1−t) wrong; we fix t=0.75 → −3) alongside raw accuracy.
5. **Guarantees**: conformal abstention (2405.01563) bounds hallucination rate using self-consistency similarity — usable as a deployment knob for the connected variant (calibration set = receipted held-out items).
6. **Tool-decision honesty**: When2Call over-call rate; ToolBeHonest solvability detection; BFCL irrelevance; abstention under *missing tool* (gateway has only CALC, LOOKUP).
7. Training-side evidence that this is learnable at our scale: RLCR adds a Brier term to the RL reward and improves calibration without accuracy loss (2507.16806, rev. 2026-05); Abstain-R1 (2604.17073, ACL 2026) is a 3B model with calibrated abstention + clarification competitive with DeepSeek-R1 on Abstain-Test/Abstain-QA/SelfAware; R-Tuning (NAACL 2024) shows refusal transfers across domains; test-time compute raises selective accuracy (2502.13962).

## 6. What a receipt-verifiable eval looks like

Precedents: lm-eval-harness writes `task_hashes`, `doc_hash`, `prompt_hash`, `target_hash`, `chat_template_sha`, `system_instruction_sha` and timing into results JSON (`evaluation_tracker.py`); Inspect `.eval` logs record input/target/scores/events per sample but have no signing or integrity mechanism; HF Eval Results offers `verifyToken` only for HF-Jobs runs; Sigstore model-transparency signs weight digests, not evals. Verifiable inference: TOPLOC (2501.16007) stores 258 bytes per 32 tokens of locality-sensitive activation hashes, tolerant to GPU/precision differences, 100% detection in their tests; Verde (2502.19405) needs bitwise-reproducible operators (RepOps) for refereed delegation; Thinking Machines showed 80 unique completions in 1,000 runs of one prompt without batch-invariant kernels and 1.6–2× slowdown with them (2025-09-10). CIS-1 makes all of this trivial: outputs are bit-identical on any CPU, so a receipt can commit to exact tokens and exact integer logits — stronger than TOPLOC's approximate hashes and free of Verde's RepOps overhead.

**ALICE-Next receipted eval bundle (per run):** (1) manifest: eval set id + revision hash, item list hash, prompt template hash, MODEL.SAF digest, engine build digest, decode config (greedy, 2048 ctx), tokenizer digest, ASCII-normalisation rule and count of items with unrepresentable characters; (2) per item: lm-eval-style doc/prompt/target hashes, the CIS-1 receipt (input tokens → hash-chained output tokens, integer answer log-probs, every CALC/LOOKUP request and response hash, TPM quote and signature); (3) Merkle root over item receipts, signed; (4) scores with Wilson CIs and the paired-test tables; (5) `.eval_results/*.yaml` pushed to the model repo with `source.url` pointing to the bundle so MMLU-Pro/GSM8K appear on HF official leaderboards (badge "source", not "verified" — HF's verified path is HF Jobs only). Third-party protocol: pick any 1% of items, replay on any x86_64 CPU, require identical receipts; a single mismatch invalidates the bundle. Judge-scored sets (MT-Bench, Arena-Hard-Auto, WildBench) cannot be receipted unless the judge also runs under CIS; they are reported in an "unreceipted" tier and never gate.

## 7. Eval plan for ALICE-Next

Protocol constants: greedy decode, 2048 ctx (items exceeding ctx are scored 0 and counted, never dropped), both variants run every set; the connected variant additionally runs with gateway on; item lists and gates committed (hash in report) before final training; all numbers Rule-B provenance; measurement legs on box1/box2 via systemd-run. Three primary endpoints are pre-registered (BFCL v4 overall, AbstentionBench recall at precision ≥ 0.80, IFEval prompt-strict); every other gate is Holm-corrected secondary.

**G0 Integrity gates (fail → nothing is reported)**
1. Decontamination: Qwen2.5 LCS rule (≥13 tokens and ≥0.6·min length, ALICE tokenizer, text-normalised) plus 8-gram overlap ≥ 50% of an item's n-grams (open-instruct tooling) over *all* pre/post-training data vs every item in §3; publish removed counts and clean-vs-dirty scores; Benchmark Transparency Card listing any GSM8K/MATH train-split use.
2. Memorisation probes: 60%-prefix exact-match completion ≤ 5% on MATH-500 and GSM8K-Platinum (Llama-3.1-8B reference 3.8%); ConStat-style delta between MMLU-Redux and a 500-item paraphrased reference ≤ 3 pp; Zero-CoT truncation probe reported.
3. Determinism: full battery run on two different CPUs (penguin AVX2 and box1) → identical Merkle roots.
4. Receipt coverage 100%; 1% third-party replay passes; connected runs show ≥ 1 LOOKUP receipt for every answered fresh-knowledge item.
5. Judge calibration: 200 human-labelled items per judge-scored set; sensitivity/specificity and corrected CIs (Lee et al.).

**G1 Non-regression vs ALICE-1 (BitNet-2B-4T re-run on our harness)**: on every shared set, exact McNemar p < 0.05 and paired-bootstrap (10k) 95% CI excluding 0 before any "better" claim; "not worse" = lower CI bound ≥ −2 pp.

**G2 Class targets (absolute; both variants unless stated)**
| Set (n) | Metric | Gate |
|---|---|---|
| MMLU-Redux 2.0 (5,700) | acc, 5-shot MC, 3 prompt variants | median ≥ 60; max−min ≤ 3 pp |
| MMLU-Pro (12,032) | acc, CoT | ≥ 35 |
| GSM8K-Platinum (1,209) | exact match | ≥ 65 |
| MATH-500 (500) | exact match | ≥ 50 |
| HumanEval+ (164) / MBPP+ (378) | pass@1 | ≥ 45 / ≥ 55 (164-item CI ±7.7 pp: HumanEval+ secondary) |
| IFEval (541) / IFBench | prompt-strict / acc | ≥ 70 / ≥ 22 |
| BFCL v4 | overall; non-live AST; live; multi-turn; hallucination (irrelevance) | ≥ 50; ≥ 80; ≥ 70; ≥ 25; ≥ 85; state-based scoring; 100-item hand re-adjudication reported (18.5% misalignment finding) |
| τ²-bench retail/airline (115/50) | pass^1, pass^4 | informational for v1; reliability gate pass^4/pass^1 ≥ 0.5 |
| When2Call / ToolBeHonest (700) | over-call rate / solvability detection | ≤ 10% / ≥ 70 |
| AbstentionBench (capped 3,500/set) | recall at precision ≥ 0.80; false-premise recall | ≥ 0.70 (beats Llama-3.1-8B 0.66); ≥ 0.60 (Llama-8B 0.53) |
| SimpleQA Verified (1,000), no tools | incorrect / not-attempted / wrong-given-attempted | air-gapped: ≤ 15% / ≥ 75% / ≤ 50%; connected (gateway on, documented as "tools" run): correct ≥ 50% with a LOOKUP receipt on ≥ 95% of attempts |
| FreshQA (600) STRICT | acc; false-premise | connected ≥ 60 / ≥ 50; air-gapped fast-changing abstention ≥ 90% |
| FRAMES (824) | acc with multi-step LOOKUP | informational (frontier 0.66) |
| Calibration (pooled MMLU-Redux + GSM8K-Platinum + SimpleQA-V) | ECE₁₅, smoothECE, Brier, AURC, sel-acc@70% | ECE ≤ 0.08 and smoothECE ≤ 0.08; Brier ≤ 0.20; AURC ≥ 20% better than ALICE-1; sel-acc@70% ≥ full acc + 8 pp |
| Penalised scoring (t=0.75) | score on every QA set | ≥ 0 on SimpleQA-V (i.e., guessing does not pay) |
| TruthfulQA MC2 (817) | acc | ≥ 50 (ALICE-1 45.31); flag inflation risk |
| LiveBench (first release after cutoff) / LiveCodeBench (post-cutoff window) | acc / pass@1 | ≥ 25 / ≥ 10 (Qwen3-1.7B non-think 35.6 / 11.6) |
| MT-Bench (80), Arena-Hard-Auto (500), WildBench (1,024) | judge-corrected WB-Score etc. | unreceipted tier; no significant regression vs ALICE-1 (5.85 MT-Bench) |
| Footprint (reference 2 GB box) | RSS, TTFT @512-token prompt, decode tok/s | ≤ 1.4 GB; TTFT ≤ 2× ALICE-1; tok/s ≥ 0.8× ALICE-1 |

Dev loop: CIS-1 exact held-out perplexity (highest signal-to-noise per Ai2) plus 100-item IRT subsets of MMLU-Redux/GSM8K-Platinum every checkpoint, averaged over the last 3 checkpoints; the full battery only at milestones. Private holdout: a 300-item Aefinity set with CapBencher-style randomized correct answers, receipts published, items withheld.

**Provenance/licensing consequences for eval**: AbstentionBench is CC-BY-NC-4.0 — evaluation is fine, but none of it may enter training data for a commercial model; GSM8K-Platinum annotations are CC-BY-SA-4.0 (share-alike if redistributed); MATH-500 descends from MATH *test*, so any distillation teacher data touching MATH test must be disclosed on the Transparency Card; several licenses (FreshQA, FRAMES, LiveBench, LiveCodeBench, HaluEval, TruthfulQA, When2Call, ToolBeHonest) were not verified here.

## Key claims (as returned by the research agent, with sources)
- Qwen2.5 decontamination rule: a training sequence is removed if the longest common subsequence with any test sequence is >= 13 tokens and >= 0.6 x min(len), applied to pre- and post-training data (Qwen2.5 Technical Report, Section 5, dated 2025-01-03).  
  <https://arxiv.org/html/2412.15115>
- MMLU-Redux 2.0 re-annotates 5,700 MMLU questions across 57 subjects, estimating 6.49% of MMLU questions contain errors (57% in Virology); dataset licensed CC-BY-4.0.  
  <https://huggingface.co/datasets/edinburgh-dawg/mmlu-redux-2.0>
- GSM8K-Platinum: of 1,319 GSM8K test items, 219 were flagged by models, 110 rejected, 10 re-labeled, yielding 1,209 items; annotations CC-BY-SA-4.0.  
  <https://huggingface.co/datasets/madrylab/gsm8k-platinum>
- BFCL v4 (released 2025-07-17) adds web search (200 cases), memory (465) and format sensitivity (5,200 cases, 26 configs); overall score weights Agentic 40%, Multi-Turn 30%, Live 10%, Non-Live 10%, Hallucination 10%.  
  <https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html>
- AbstentionBench (Meta FAIR, 2025-06-10): 20 datasets, >35k unanswerable questions capped at 3,500 per dataset, judge Llama-3.1-8B-Instruct with 88% human agreement; reasoning fine-tuning degrades abstention by 24% on average; best average abstention recall 0.71 (Qwen2.5-32B), Llama-3.1-8B 0.66; license CC-BY-NC-4.0.  
  <https://arxiv.org/html/2506.09038>
- Wu et al. (AAAI 2026): given the first 60% of MATH-500 problems, Qwen2.5-Math-7B reconstructs the remaining 40% with 54.6% exact match and answers 53.6% correctly, versus 3.8% / 2.4% for Llama-3.1-8B.  
  <https://arxiv.org/html/2507.10532>
- Benchmarking the Benchmarks (2026-06-30) audited BFCL v4, tau2-bench, LiveMCPBench and MCP-Atlas: 92 evaluator-human disagreements over 496 expert-reviewed tasks (18.5% misalignment); 23 reruns of one LiveMCPBench setup ranged 57.9%-76.8%.  
  <https://arxiv.org/abs/2607.02577>
- Hugging Face Eval Results: model repos store scores in .eval_results/*.yaml (dataset id, task_id, value, optional verifyToken, date, source url); a 'verified' badge requires the evaluation to have run in HF Jobs with inspect-ai; MMLU-Pro and GSM8K are registered official benchmarks.  
  <https://huggingface.co/docs/hub/eval-results>
- MLPerf Client release feed: v2.0.0 published 2026-08-18, v2.0.1 2026-09-24, v1.6.0 2026-04-06, v0.5 2024-12-11; v2.0 base models are Llama 3.1 8B Instruct and Phi 4 Mini Instruct (Phi 3.5 Mini removed), metrics TTFT and tokens/s.  
  <https://github.com/mlcommons/mlperf_client/releases.atom>
- BitNet b1.58-2B-4T model card (MIT): MMLU 53.17, GSM8K 58.38, MATH-500 43.40, HumanEval+ 38.40, IFEval 53.48, TruthfulQA 45.31, MT-Bench 5.85; 0.4 GB non-embedding memory, 29 ms CPU decode latency.  
  <https://huggingface.co/microsoft/bitnet-b1.58-2B-4T>

## Gaps and unverified items (recorded, not papered over)
- WebSearch budget was exhausted before this task started; all evidence comes from direct fetches of known URLs and Hugging Face Hub search. Coverage of contamination/abstention papers from Q3 2026 is therefore incomplete.
- BFCL v4 per-model scores for 1-3B open models (Qwen3-1.7B, Llama-3.2-3B, xLAM, Hammer) could not be retrieved: the leaderboard page is JavaScript-rendered and the gorilla repo data path could not be enumerated without GitHub API access. Only vendor-reported BFCL v2/v3 numbers are cited.
- tau2-bench reports no small open-model results (only gpt-4.1-mini, gpt-4.1, o4-mini, claude-3-7-sonnet); the proposed tau2 gates are therefore informational for v1.
- Exact archival date of the Open LLM Leaderboard was not confirmed from a primary page (HF docs describe it in the past tense; commonly reported as March 2025).
- Qwen3 Technical Report's decontamination statement was not located in the fetched HTML sections; only the Qwen2.5 rule is quoted.
- Licenses not verified: MATH-500 (prm800k), FreshQA, FRAMES, LiveBench, LiveCodeBench, HaluEval, TruthfulQA, When2Call, ToolBeHonest, AbstentionBench code repo (dataset confirmed CC-BY-NC-4.0).
- No established 'MMLU-Pro-lite' artifact was found on the Hub; the plan substitutes a tinyBenchmarks-style IRT subset for dev loops only.
- Open SLM Leaderboard (AxiomicLabs, 2026) covers only sub-150M models; no 2026 Hugging Face leaderboard dedicated to the 1-3B class was found other than the generic Eval Results system and Intel's low-bit leaderboard.
- Retro-Misconceptions (TruthfulQA retro-holdout) availability for third-party use was not verified.
- Gate thresholds are analyst proposals bracketed by vendor numbers measured on different harnesses; they must be re-baselined after ALICE-1 (BitNet-2B-4T) is re-run on the receipted harness.
