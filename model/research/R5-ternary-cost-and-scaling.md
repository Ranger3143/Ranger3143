> Research brief produced on 2026-10-06 by a web-research agent for the ALICE-Next model plan. Every claim carries the URL the agent read; items it could not verify are listed under Gaps. Numbers here are the cited papers' numbers, not Aefinity measurements.

# ANGLE 5 — What ternary (1.58-bit) costs at 1–3B params, and whether ALICE-Next fits in 2 GB

*Research brief for Aefinity AI, 2026-10-06. Primary sources fetched; numbers quoted exactly; [uncertain] marks anything I could not verify from a primary source.*

## 1. Bottom line

1. **No matched-token, from-scratch ternary-vs-bf16 twin above 1B has been published since Spectra (Jul 2024) and the BitNet "Era" paper (Feb 2024).** Everything newer at 1–8B (ParetoQ, BitDistill, Bonsai, CAT-Q) converts a *pretrained float model* to ternary. 2026 added kernels/packing (BITCOS 1.485 bpw, Sherry 1.25 bpw, Litespark), a 132M T4-scale study (TernaryLM), and a critique paper — not a new 1–3B twin. That is a genuine gap your 30M-twin methodology could fill at 1B.
2. **From-scratch evidence:** at 100B tokens ternary is at parity at 3B (PPL 9.91 vs 10.04; avg 50.2 vs 49.7) and −0.8 to −1.2 points at 0.7–1.3B (Era). At 300B tokens the residual benchmark gap is −0.7 pts at 3.9B, −1.9 at 2.4B, −4.2 at 1.5B, −3.3 at 1.1B (Spectra), and TriLM 3.9B is still "consistently worse" on web-corpus cross-entropy even where benchmarks match. Spectra-1.1's fitted law says ternary loss falls with tokens as D^-0.81 vs params N^-0.32 → **ternary wants tokens, not parameters.** For a 1.5B ternary target, plan ≥1T tokens (Falcon-E used ~1.5T; BitNet-2B4T 4T).
3. **Converted-from-float evidence at your sizes:** ternary QAT costs −2.2 pts at 1.5B (ParetoQ, 1T-token MobileLLM base, A16 activations, 30B QAT tokens), −8.1 pts at 1.7B and −6.4 at 4B (Ternary Bonsai from Qwen3, 2026), −10.4 pts at 1.7B for pure PTQ (CAT-Q, 1M calibration tokens). Over-trained teachers lose more (consistent with the "low-bit favors undertrained LLMs" law). Task-specific distillation (BitDistill) closes the gap on narrow tasks (MNLI 89.53 vs 89.61 at 1.7B) with 10B CPT tokens.
4. **Training overhead:** the only published number is TII's "~20%" wall-clock overhead for BitNet vs non-BitNet pretraining (kernel-limited, two-pass absmax). FLOPs are identical; master weights stay bf16, so training memory is *not* reduced.
5. **Memory (computed below):** a 1.2–1.7B-class ternary model with a 32k–50k vocab is **1.0–1.3 GiB all-in** (weights + int8/bf16 head + 4k KV + 600 MiB work) → fits the 1.4 GB target with margin. A 2.6–3.0B-class model is **1.41–1.97 GiB** → fits the 2 GB floor only with int8 embeddings/head and int8 KV (or 1.6-bpw packing); it misses the ~1.4 GB target unless both are used.

## 2. Native ternary vs float, trained from scratch at matched params and tokens

| Source | Size (non-emb unless noted) | Tokens | Float twin | Ternary result | Gap | Activations | Notes |
|---|---|---|---|---|---|---|---|
| BitNet "Era" (arXiv 2402.17764, Feb 2024) | 700M | 100B | PPL 12.33 / avg 45.5 | PPL 12.87 / avg 44.3 | +4.4% PPL, −1.2 pts | A8 absmax | LLaMA twin LR 2.5e-4 vs BitNet 1.5e-3→1e-3 |
| same | 1.3B | 100B | 11.25 / 46.2 | 11.29 / 45.4 | +0.4% PPL, −0.8 pts | A8 | |
| same | 3B | 100B | 10.04 / 49.7 | 9.91 / 50.2 | −1.3% PPL, +0.5 pts (parity) | A8 | memory 2.22 vs 7.89 GB; latency 1.87 vs 5.07 ms |
| same, Table 4 | 3B | 2T | StableLM-3B avg 73.22 | 74.34 | +1.1 pts | A8 | not a twin (different data) |
| Spectra (arXiv 2407.12327, Jul 2024) | 3.9B | 300B | C&R avg 61.4; MMLU 32.6; LAMBADA ppl 6.7 | 60.7; 32.4; 6.3 | −0.7 pts; −0.2 MMLU; ppl better | fp (weights-only) | TriLM batch 1M tok vs FloatLM 2M; "fewer bits than FloatLM 830M" |
| same | 2.4B | 300B | 59.2; 31.8; 7.7 | 57.3; 30.8; 8.6 | −1.9 pts | fp | |
| same | 1.5B | 300B | 56.7; 30.4; 9.4 | 52.5; 29.5; 16.4 | −4.2 pts; LAMBADA ppl +74% | fp | |
| same | 1.1B | 300B | 54.9; 30.0; 11.7 | 51.6; 28.3; 17.3 | −3.3 pts | fp | |
| Spectra-1.1 (arXiv 2506.23025, Jun 2025) | 1.5B/2.5B/3.6B ("1B/2B/3B") | 1.2T | none released | MMLU 34.43 / 36.12 / 38.21; GSM8K 2.12 / 3.03 / 9.70 | n/a | fp train; TQ1/TQ2 infer | TriLM 3B@1.2T MMLU 38.2 vs Spectra-1 FloatLM 3.9B@300B 32.6 |
| Falcon-E (TII, May 2025) | 1.8B total / 3.0B total | ~1.5T | none (bf16 revision is *derived from the ternary checkpoint*, not a twin) | base avg 13.40 / 18.32 vs Qwen2.5-1.5B 13.85, Qwen2.5-3B 18.1; instruct 18.59 / 22.65 vs Qwen2.5 18.43 / 27.16 | ≈ parity base; −4.5 pts instruct at 3B | A8 available | 665 MB / 999 MB footprint; vocab 32,768 |
| BitNet b1.58 2B4T (arXiv 2504.12285, Apr 2025) | 2.4B total (1.55B ternary by my count) | 4T | none; vs Qwen2.5-1.5B (18T tok) | avg 54.19 vs 55.23; beats Llama-3.2-1B 44.90, Gemma-3-1B 43.74, SmolLM2-1.7B 48.70 | −1.0 pts vs Qwen2.5-1.5B | W1.58A8 | 0.4 GB non-emb; 29 ms CPU TPOT; 0.028 J |
| OLMo-Bitnet-1B (Nous, 2024) | 1B | 60B | "exact same hyperparameters… fp16" twin, WandB only | not on card | [uncertain] | | Apache 2.0 |
| ALICE-30M twins (own) | 30M | 500M | bf16 | +0.38 nats (46% PPL) | | A8 | far below the scaling regime |
| TernaryLM (arXiv 2602.07374, Feb 2026) | 132M | TinyStories | fp32 | PPL 58.42±0.17; 498 vs 1,197 MB | baseline PPL not in abstract [uncertain] | | single T4 |

Reading: **parity in benchmarks appears at ~3B/100–300B tokens; at 1–1.5B a residual −1 to −4 pt gap persists at 300B tokens**, and web-text cross-entropy lags even when benchmarks match. The Era baseline may be under-tuned (LLaMA LR 2e-4 vs BitNet 1.2e-3; same batch 1M; Table 2 of the Training-Tips PDF) — a known critique [uncertain magnitude]. Spectra's batch mismatch (1M vs 2M) cuts the other way.

**Scaling-law fits (Spectra-1.1, N in millions non-embedding, D in billions):** TriLM L = 2.19 + 4.73/N^0.32 + 5.18/D^0.81; FloatLM L = 2.17 + 7.86/N^0.56 + 3.42/D^0.53, fitted on 99M–1.1B models at 20–150B tokens. Taken literally they imply a ternary 3.6B at 300B tokens ≈ a float 475M model and **never cross** — which contradicts Spectra-1's own benchmark parity at 3.9B. The fits are therefore not cross-comparable (different losses/ranges) [uncertain]; use only the exponent ratio (data 0.81 vs params 0.32), which is the robust finding. Corroborating laws: Kumar et al. "Scaling Laws for Precision" (arXiv 2411.04330: low-precision training lowers effective parameter count; 465 runs ≤1.7B/26B tok); "Scaling Law for QAT" (arXiv 2505.14302: W4A4 error falls with N, *rises with D*, FC2-input activation is the bottleneck); "Low-bit quantization favors undertrained LLMs" (arXiv 2411.17691, 1,500+ checkpoints). QuEST (arXiv 2502.05003) fits eff(P) = 0.02 (1-bit), 0.16 (2-bit), 0.43 (3-bit), 0.70 (4-bit) for W+A quantized small models (30–800M, 100 tok/param) and finds W4A4 Pareto-optimal, no ternary row.

## 3. Ternary obtained from a pretrained float model (QAT / distillation / PTQ)

| Source | Base → sizes | Method, tokens | Float avg → ternary avg | Activations | Format | License of result |
|---|---|---|---|---|---|---|
| ParetoQ (arXiv 2502.02631, NeurIPS 2025) | MobileLLM 125M–1.5B; LLaMA-3 1B/3B/8B | QAT, ~90/10 pretrain/QAT split; ternary saturates ~30B QAT tokens (3/4-bit ~10B) | 1.5B: 62.7→60.5 (−2.2; 2-bit 61.8); 3B: 65.2→61.9 (−3.3; 2-bit 63.2); 8B: 74.6→69.0, Wiki2 PPL 6.15→8.6 | **A16** (optimistic for CIS-1) | learnable scale, SEQ | MobileLLM (CC-BY-NC) / Llama licenses |
| BitNet Distillation (arXiv 2510.13998, Oct 2025, Microsoft) | Qwen3 0.6B/1.7B/4B | SubLN insert + 10B-token CPT (FALCON) + MiniLM attention distillation + task SFT | MNLI 88.01/89.61/91.48 → 88.17/89.53/91.40; direct 1.58 SFT only 74.09/75.27/76.11; gap without warm-up grows 13.9→15.3 from 0.6B→4B | A8 (BitNet) | per-tensor absmean | Apache-2.0 (Qwen3) |
| Ternary Bonsai (PrismML, Apr 16 2026) | Qwen3 1.7B/4B/8B (27B from Qwen3.6) | conversion method undisclosed on cards | 1.7B: 66.57→58.47 (−8.1; BFCLv3 71.8→51.0); 4B: 77.1→70.7 (−6.4); 8B: 79.3→75.5 (−3.8) | fp16 | {−1,0,+1} + FP16 scale per 128 → 2.125 bpw incl. embeddings & LM head; 436 MiB / 1,020 MiB / 2.03 GiB | Apache-2.0 |
| CAT-Q (arXiv 2606.26650, ICML 2026 oral) | Qwen3 1.7B/4B/8B | PTQ, 512×2048 C4 tokens (~1M), 1–60 h on 8×A100 | 61.42→51.01; 68.25→57.06 (A8: 56.39); 71.57→61.76 (A8: 60.96) | A16 or A8 (A8 costs −0.7/−0.8) | g128 | Apache-2.0 |
| PTQ ternarization of Qwen3-4B (arXiv 2609.01962, Sep 2026) | Qwen3-4B | rotation + GPTQ-style | 64.5→54.7; Wiki2 13.6→18.7; 1.641 bpw | | | |
| HF "Fine-tuning LLMs to 1.58bit" (Sep 2024) | Llama-3-8B | 10B then 100B tokens; linear λ warm-up min(step/1000,1), LR 1e-4 | "outperforms the Bitnet 7B model (100B tokens)" | | 8B→"2.8B" packed | Llama-3 license |

Reading: converting an *over-trained* teacher (Qwen3 ≈36T tokens) to ternary costs 6–8 pts at 1.7–4B even with the best 2026 methods; a 1T-token base loses ~2 pts. Function-calling degrades hardest (Bonsai 1.7B BFCLv3 −20.8 pts) — directly relevant to a tool-expert target. Task-focused distillation (BitDistill) recovers parity on narrow tasks.

## 4. Training cost overhead, activations, and recipe knobs

**Overhead.** Falcon-E: "we estimate the overhead to be around ~20% between non-Bitnet pre-training against Bitnet pre-training", attributed to a two-pass absmax (global max then block-wise) in their Triton kernel. BitNet a4.8 claims "equivalent training costs" to b1.58. No other primary number exists; theoretical FLOPs are identical (STE on bf16 master weights), so **budget +20% wall-clock and no training-memory saving**.

**Activations (CIS-1 needs int8).** Era/2B4T/Falcon-E/BitDistill train W1.58A8 (per-token absmax). Spectra/ParetoQ train with full-precision activations; CAT-Q shows A8 costs −0.7 to −0.8 pts vs A16 at 4B/8B (PTQ). 4-bit activations: BitNet a4.8 (arXiv 2411.04965: A4 at attention/FFN inputs, sparsified A8 intermediates, 3-bit KV, 55% params active, "comparable" to b1.58); BitNet v2 (arXiv 2504.18415: online Hadamard, native A4 with "minimal" degradation). The Era 3B 4-bit-KV ablation: avg 50.0 vs 50.2 → **int8 KV is safely free.**

**Recipe knobs with evidence (Training-Tips PDF, 2B4T report, Spectra):**
- Higher LR than float: 700M 1.5e-3→1e-3; 1.3B–3.9B 1.2e-3→8e-4 vs LLaMA 2e-4–2.5e-4 (Era); Spectra 1.1B 1.3e-3→9e-4, 3.9B 1.2e-3→8e-4; Spectra-1.1 1.5e-3; warm-up 375 steps, Adam (0.9, 0.95), batch 1M tokens, seq 2048.
- Two-stage LR: drop mid-run; "significant reduction in loss occurring when the learning rate was decayed"; loss is S-shaped so mid-run evals under-predict.
- Weight decay 0.1 → 0 at the half (BitNet) or two-thirds (Spectra) point: WD acts on latent weights whose magnitude is the "confidence" of the ternary value; keeping it makes flips continue.
- Architecture: SubLN (2B4T, BitDistill — where the gap without it grows with size); ReLU² instead of SwiGLU (2B4T; two FFN matrices, sparser activations, ~¾ the FFN bytes of a 3-matrix SwiGLU at equal width); no biases; RoPE; QK-norm (Spectra-1.1); per-tensor absmean weights (bitnet.cpp I2_S "lossless"); Falcon-E removed BitNet's inner LayerNorms "with no adverse effect". Median-absmean variant for very small nets (Reloaded, arXiv 2407.09527).
- Ternary alone is "sufficient regularization" (Spectra); 2B4T weight-decay cosine to 0.1 then 0; 2B4T DPO LR 2e-7, β 0.1.

## 5. Memory budget for ALICE-Next (computed; MiB = 2^20)

Assumptions: head_dim 128; packed ternary at 2.0 bpw (I2_S, 4 trits/byte — matches 2B4T's "0.4 GB non-embedding" and Falcon-E's 635/999 MB) and 1.6 bpw (TQ1_0 5-trits/byte, Spectra-1.1); embeddings and LM head bf16 or int8; KV int8 or fp16 at 4,096 ctx; 600 MiB working memory; CIS-1 norms/scales negligible.

| Config | Ternary params | Ternary bytes @2.0 / 1.6 bpw | Emb (+ untied head) bf16 / int8 | KV @4k int8 / fp16 | **All-in, int8 head + int8 KV @2.0 bpw** | **Worst case: bf16 head + fp16 KV @2.0 bpw** | Best case @1.6 bpw |
|---|---|---|---|---|---|---|---|
| BitNet-2B4T as shipped (30L, d2560, ff6912 ReLU², 20/5 heads, vocab 128,256 tied) | 1.553B | 370 / 296 MiB | 626 / 313 MiB | 150 / 300 MiB | **1,434 MiB (1.40 GiB)** | 1,897 MiB (1.85 GiB) | 1,360 MiB |
| 2B4T ALICE-pruned (vocab 50,256) | 1.553B | 370 / 296 | 245 / 123 | 150 / 300 | **1,244 MiB (1.21 GiB)** | 1,516 MiB (1.48 GiB) | 1,170 MiB |
| ALICE-Next-1.2B: 24L, d2048, ff8192 ReLU², 16/4 heads, vocab 50,256 tied (1.16B total) | 1.057B | 252 / 202 | 196 / 98 | 96 / 192 | **1,047 MiB (1.02 GiB)** | 1,241 MiB (1.21 GiB) | 996 MiB |
| same, vocab 32,768 untied (1.19B total) | 1.057B | 252 / 202 | 128+128 / 64+64 | 96 / 192 | **1,076 MiB** | 1,300 MiB (1.27 GiB) | 1,026 MiB |
| Falcon-E-1B shape: 24L, d2048, ff9216 SwiGLU, 16/2 heads, vocab 32,768 untied (1.72B total) | 1.585B | 378 / 302 | 128+128 / 64+64 | 48 / 96 | **1,154 MiB (1.13 GiB)** | 1,330 MiB (1.30 GiB) | 1,079 MiB |
| ALICE-Next-2.6B: 28L, d3072, ff10240 ReLU², 24/8 heads, vocab 50,256 tied | 2.466B | 588 / 470 | 294 / 147 | 224 / 448 | **1,560 MiB (1.52 GiB)** | 1,931 MiB (1.89 GiB) | 1,442 MiB (1.41 GiB) |
| Falcon-E-3B shape: 32L, d2048, ff13312 SwiGLU, 16/2 heads, vocab 32,768 untied (3.05B total) | 2.919B | 696 / 557 | 128+128 / 64+64 | 64 / 128 | **1,488 MiB (1.45 GiB)** | 1,680 MiB (1.64 GiB) | 1,349 MiB (1.32 GiB) |
| Llama-3.2-3B shape, vocab 50,256 tied (2.97B total) | 2.819B | 672 / 538 | 294 / 147 | 224 / 448 | **1,644 MiB (1.61 GiB)** | 2,015 MiB (1.97 GiB) | 1,509 MiB |

Verdicts:
- **1.2–1.7B class fits the 1.4 GB target in every configuration** (max 1.30 GiB worst case). A bf16 50k×2048 head (196 MiB) is read once per decoded token — nearly as many bytes as the whole ternary body (252 MiB) — so **int8 (or ternary, as Bonsai does) head is a decode-speed win, not just a memory win**; CIS-1's integer head is the natural choice.
- **2.6–3.0B class clears the 2 GB floor only with int8 head + int8 KV (1.45–1.61 GiB) and reaches ~1.4 GB only with 1.6-bpw packing (1.32–1.41 GiB)**; the Llama-3.2-3B shape at bf16/fp16 is 1.97 GiB — do not ship. Few KV heads (Falcon-E's 2) buys 160–320 MiB at 4k ctx vs 8 heads.
- Working memory of 600 MiB is the dominant soft term at 1.2B; 2B4T's GGUF (1.19 GB) shows what bf16 embeddings cost at 128k vocab.

## 6. Compute and provenance consequences of each path

| Path | Tokens | FLOPs (6ND) | H100-hours @35% MFU, ×1.2 ternary overhead | Rough rent @ $2.5/h | Provenance |
|---|---|---|---|---|---|
| From-scratch 1.2B (1.06B non-emb) | 1T | 6.4e21 | ~6,100 | ~$15k | Clean: own data, own weights; sovereignty proof intact; Rule-B receipts over training logs |
| From-scratch 2.6B | 1T | 1.5e22 | ~14,700 | ~$37k | same; ×4 for a 2B4T-style 4T run |
| From-scratch 1.2B on Kaggle T4 (~20 TFLOPs effective) | 1T | 6.4e21 | ~110,000 T4-h ≈ 70 years at 30 h/week | — | infeasible without renting |
| QAT/distill from Qwen3-1.7B (Apache-2.0) | 10B CPT + 30B QAT | ~4e20 | ~380 | ~$1k | Weights derived from Qwen3 → inherit Apache-2.0 (attribution + NOTICE), Alibaba's undisclosed data mix; claim becomes "sovereign inference", not sovereign weights; expect −2 to −8 pts (Table 3) unless task-focused |
| QAT/distill from Llama-3.2-1B/3B | same | same | same | Llama Community License: "Built with Llama" naming, redistribution terms, 700M-MAU clause; Gemma-3 has its own terms | |
| Teacher-only distillation (logits/attention from any API/model into a from-scratch student) | 1T student tokens still needed | ≥ from-scratch | ≥ from-scratch | Student weights are yours but outputs of third-party models carry their ToS (several forbid training competitors); document the teacher in the model card | |

Estimates are mine [uncertain ±2×]; MFU for ternary Triton kernels is unmeasured in any source.

## 7. What is actually new in 2026 (and what is not)

- Packing: BITCOS (Intel, arXiv 2609.16338, Sep 2026) exploits zero-skew ("zeros account for up to 51.5% of all weights" across 29 ternary models) for **1.485 bpw** vs 1.625 five-trit packing, +1.18× CPU end-to-end; Sherry (arXiv 2601.07892) 1.25 bpw via 3:4 sparsity, "zero accuracy loss" vs ternary SOTA on Llama-3.2-1B, +10% CPU speed; Litespark (arXiv 2605.06485) SIMD ternary CPU framework, 6.03× memory vs PyTorch.
- Conversion: CAT-Q (ICML 2026 oral) and Ternary Bonsai — strong, but Section 3 gaps remain at 1.7–4B.
- Methodology: "Baseline Shape Decides the Verdict" (arXiv 2609.29397) shows a 22.6% spread in float baselines from depth/width choice alone and that a 90/10 float-then-ternary schedule beats all-ternary only at 10× LR — i.e., **twin comparisons must sweep the float baseline's shape and LR**, which the Era paper did not.
- Survey: arXiv 2608.29667 (Aug 2026) — target-centric QAT taxonomy; no new ternary parity number.
- **Not new:** no 2026 from-scratch ternary 1–3B with a matched bf16 twin; no new Microsoft BitNet weights beyond 2B4T (Apr 2025) and BitDistill (Oct 2025).

## 8. Design recommendations for ALICE-Next (CIS-1-native)

1. Target **1.2–1.7B total, ≥1T tokens** before considering 3B: the data exponent (0.81) says tokens buy more than width, and 1.5B is the largest size that fits 1.4 GB with bf16-free margin. A 2.6B ReLU² variant is the ceiling for the 2 GB floor and only with int8 head/KV.
2. Architecture: 2B4T recipe — SubLN, ReLU², no bias, RoPE, GQA 4 KV heads, per-tensor absmean ternary (I2_S-compatible, maps to the existing AVX2 kernels), W1.58A8 per-token absmax, int8 KV, int8 tied embedding/head at 32k–50k vocab, QK-norm (Spectra-1.1).
3. Optimizer: LR 1.2–1.5e-3 → 8e-4–1e-3 at 50%; WD 0.1 → 0 at 50–67%; batch 1M tokens; warm-up 375 steps; expect S-shaped loss, so gate decisions on post-decay evals.
4. Budget +20% wall-clock; master weights bf16 (no training-memory saving).
5. If distillation is adopted: Qwen3-1.7B/4B (Apache-2.0) is the only teacher family at your sizes that does not impose naming/MAU clauses; run BitDistill-style SubLN + 10B CPT + attention distillation + a tool-use SFT stage; measure BFCL explicitly (Bonsai lost 20.8 pts there); file the PUBLISH?/provenance item because the sovereignty claim changes.
6. Publishable gap to claim: a 1B ternary/bf16 twin at matched tokens with swept baseline shape and LR, with CIS-1 receipts over every eval.

## Sources
- https://arxiv.org/abs/2402.17764 · https://arxiv.org/html/2402.17764v1 · https://github.com/microsoft/unilm/blob/master/bitnet/The-Era-of-1-bit-LLMs__Training_Tips_Code_FAQ.pdf
- https://arxiv.org/abs/2504.12285 · https://arxiv.org/html/2504.12285v2 · https://huggingface.co/microsoft/bitnet-b1.58-2B-4T/raw/main/config.json · https://huggingface.co/microsoft/bitnet-b1.58-2B-4T-bf16 · https://huggingface.co/microsoft/BitNet-b1.58-2B-4T-gguf/tree/main · https://github.com/microsoft/BitNet
- https://arxiv.org/abs/2407.12327 · https://arxiv.org/html/2407.12327 · https://arxiv.org/abs/2506.23025 · https://arxiv.org/html/2506.23025
- https://falcon-lm.github.io/blog/falcon-edge/ · https://huggingface.co/tiiuae/Falcon-E-1B-Base · https://huggingface.co/tiiuae/Falcon-E-1B-Base/raw/main/config.json · https://huggingface.co/tiiuae/Falcon-E-3B-Base/raw/main/config.json
- https://arxiv.org/abs/2502.02631 · https://arxiv.org/html/2502.02631 · https://arxiv.org/abs/2510.13998 · https://arxiv.org/html/2510.13998
- https://prismml.com/news/ternary-bonsai · https://huggingface.co/prism-ml/Ternary-Bonsai-8B-gguf · https://huggingface.co/prism-ml/Ternary-Bonsai-4B-gguf · https://huggingface.co/prism-ml/Ternary-Bonsai-1.7B-gguf · https://github.com/ArmanJR/PrismML-Bonsai-vs-Qwen3.5-Benchmark
- https://arxiv.org/abs/2606.26650 · https://arxiv.org/html/2606.26650 · https://arxiv.org/abs/2609.01962 · https://arxiv.org/abs/2609.16338 · https://arxiv.org/abs/2601.07892 · https://arxiv.org/abs/2605.06485 · https://arxiv.org/abs/2609.29397 · https://arxiv.org/abs/2608.29667 · https://arxiv.org/abs/2602.07374 · https://arxiv.org/abs/2607.21075
- https://arxiv.org/abs/2411.04965 · https://arxiv.org/abs/2504.18415 · https://arxiv.org/abs/2411.04330 · https://arxiv.org/abs/2505.14302 · https://arxiv.org/abs/2411.17691 · https://arxiv.org/html/2502.05003v2 · https://arxiv.org/abs/2502.11880 · https://arxiv.org/abs/2411.05882 · https://arxiv.org/abs/2407.09527
- https://huggingface.co/blog/1_58_llm_extreme_quantization · https://huggingface.co/NousResearch/OLMo-Bitnet-1B

## Key claims (as returned by the research agent, with sources)
- BitNet b1.58 vs LLaMA FP16 at 100B tokens: 700M PPL 12.87 vs 12.33 (avg 44.3 vs 45.5); 1.3B PPL 11.29 vs 11.25 (45.4 vs 46.2); 3B PPL 9.91 vs 10.04 (50.2 vs 49.7); BitNet LR 1.2e-3→8e-4 and WD 0.1→0 vs LLaMA LR 2e-4, WD 0.1, batch 1M tokens for both.  
  <https://arxiv.org/html/2402.17764v1>
- Spectra (300B tokens): TriLM vs FloatLM commonsense averages 60.7 vs 61.4 at 3.9B, 57.3 vs 59.2 at 2.4B, 52.5 vs 56.7 at 1.5B, 51.6 vs 54.9 at 1.1B; TriLM batch 1M tokens vs FloatLM 2M; TriLM 3.9B 'consistently worse' on web-corpus cross-entropy.  
  <https://arxiv.org/html/2407.12327>
- Spectra-1.1 fitted ternary law L = 2.19 + 4.73/N^0.32 + 5.18/D^0.81 (N in millions non-embedding, D in billions; fit on 99M–1.1B models, 20–150B tokens); TriLM 1B/2B/3B at 1.2T tokens reach MMLU 34.43/36.12/38.21; TQ1 packing is 1.6 bits per trit.  
  <https://arxiv.org/html/2506.23025>
- Falcon-E: ~1.5T tokens, WSD schedule, '~20% overhead between non-Bitnet pre-training against Bitnet pre-training'; Falcon-E-1B (1.8B params) 665 MB vs Qwen2.5-1.5B 3,100 MB; base avg 13.40 vs 13.85; Falcon-E-3B 999 MB, base avg 18.32 vs Qwen2.5-3B 18.1, instruct 22.65 vs 27.16; the bfloat16 revision is derived from the ternary checkpoint.  
  <https://falcon-lm.github.io/blog/falcon-edge/>
- BitNet b1.58 2B4T: 4T tokens, hidden 2560, 30 layers, 20 heads / 5 KV heads, FFN 6912 relu2, vocab 128,256 tied, ctx 4096; W1.58A8; weight decay cosine to 0.1 then 0 in stage 2; memory 0.4 GB non-embedding, 29 ms CPU latency, 0.028 J; avg 54.19 vs Qwen2.5-1.5B 55.23; MIT license.  
  <https://arxiv.org/html/2504.12285v2>
- ParetoQ: FP16 vs 1.58-bit QAT averages — MobileLLM 1.5B 62.7 vs 60.5 (2-bit 61.8); LLaMA-3 3B 65.2 vs 61.9; LLaMA-3 8B 74.6 vs 69.0 (Wiki2 PPL 6.15 vs 8.6); activations kept at 16-bit; ternary QAT saturates around 30B tokens, 3/4-bit around 10B; ~90/10 pretrain/QAT budget split.  
  <https://arxiv.org/html/2502.02631>
- Ternary Bonsai 1.7B (from Qwen3-1.7B, Apache-2.0, released April 2026): 436 MiB at 2.125 bits/weight (FP16 scale per 128 weights, embeddings and LM head ternary too); average 58.47 vs Qwen3-1.7B 66.57; BFCLv3 51.0 vs 71.8; 4B: 70.7 vs 77.1; 8B: 75.5 vs 79.3.  
  <https://huggingface.co/prism-ml/Ternary-Bonsai-1.7B-gguf>
- BitNet Distillation (Oct 2025): Qwen3 0.6B/1.7B/4B fine-tuned to 1.58-bit with SubLN + 10B-token continual pretraining + MiniLM attention distillation; MNLI 88.17/89.53/91.40 vs FP16 88.01/89.61/91.48; direct 1.58-bit SFT only 74.09/75.27/76.11; 10x memory, 2.65x CPU speed.  
  <https://arxiv.org/html/2510.13998>
- CAT-Q (ICML 2026 oral, PTQ with 512 x 2048 C4 calibration tokens): Qwen3-1.7B BF16 61.42 vs W1.58A16 51.01; Qwen3-4B 68.25 vs 57.06 (A8: 56.39); Qwen3-8B 71.57 vs 61.76 (A8: 60.96); group size 128.  
  <https://arxiv.org/html/2606.26650>
- BITCOS (Intel, Sep 2026): zeros are up to 51.5% of weights across 29 ternary models; achieves 1.485 bits/weight vs 1.625 for five-trit packing and log2(3)=1.585 information bound; up to 1.18x CPU and 1.27x GPU end-to-end speedup.  
  <https://arxiv.org/abs/2609.16338>

## Gaps and unverified items (recorded, not papered over)
- No from-scratch ternary-vs-bf16 twin at matched params AND tokens above 1B published after Spectra (Jul 2024); the 1–3B parity question at ≥1T tokens is unmeasured. Spectra-1.1 trained no FloatLM at 1.2T; Falcon-E's 'bfloat16' revision is derived from the ternary run, not a twin.
- Spectra-1.1's TriLM and FloatLM scaling fits, evaluated literally, imply ternary never reaches float at matched N, contradicting Spectra-1's benchmark parity at 3.9B; I could not determine from the fetched text whether the two fits use the same validation set or N range (extraction gave FloatLM range '990M–11000M', likely a parse error). Treat cross-fit comparisons as unreliable.
- Only one published training-overhead number exists (Falcon-E ~20%); no MFU or wall-clock numbers for BitNet/Spectra ternary training kernels; my H100-hour and dollar estimates are 6ND back-of-envelope with ±2x uncertainty.
- OLMo-Bitnet-1B's fp16 twin results are only in a WandB report I could not fetch; TernaryLM's fp32 baseline perplexity is not in the abstract; Scaling-Laws-for-Precision N_eff formula constants were not extracted.
- Ternary Bonsai's conversion method (QAT vs distillation vs PTQ, tokens used) is not disclosed on the model cards or announcement; BitNet-2B4T peak LR values are not stated in the HTML report (the Training-Tips PDF values are for the 2024 100B-token runs).
- CAT-Q's and ParetoQ's benchmark suites differ from Bonsai's (EvalScope: MMLU-R, MuSR, IFEval, GSM8K, HE+, BFCLv3) and from Spectra's; cross-paper point gaps are not directly comparable.
- No 2026 source measured ternary cost specifically on function-calling/tool-use beyond Bonsai's BFCLv3 rows; no source measured calibration/abstention behaviour of ternary vs float models.
- Working-memory figure of 600 MiB and UEFI firmware reservation are program assumptions, not measured here; packed-weight bytes assume per-tensor scales (I2_S) — group-wise FP16 scales (Bonsai/CAT-Q g128) add ~0.125 bpw and do not map to the current CIS-1 kernel.
