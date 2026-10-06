> Research brief produced on 2026-10-06 by a web-research agent for the ALICE-Next model plan. Every claim carries the URL the agent read; items it could not verify are listed under Gaps. Numbers here are the cited papers' numbers, not Aefinity measurements.

# ANGLE 1 — State of the art in training small (0.5–4B) LMs, 2025–2026

*Research brief for ALICE-Next design. Dated 2026-10-06. Figures are quoted from primary sources (model cards, arXiv HTML, vendor READMEs); anything I could not cross-check is marked [uncertain].*

## 0. Bottom line for ALICE-Next

1. **Every competitive 0.5–4B model of 2025–26 ties input/output embeddings, uses GQA, SwiGLU (or ReLU² in BitNet), RMSNorm, RoPE and a 3-stage curriculum that ends with a high-quality "anneal".** That is exactly the CIS-1-native op set. Nothing in the class requires an exotic op — *except* the 2026 hybrid wave (Mamba-2 / Gated DeltaNet / short-conv), which is not CIS-1-native and should be treated as a separate design fork.
2. **Raw token count is a weak predictor; data quality buys 3–10× token efficiency.** Falcon-H1-3B at 2.5T tokens (52% "rewritten" data) scores MMLU 68.3 vs Qwen3-4B at 36T tokens 73.0 (base); MobileLLM-R1-950M at 4.2T matches Qwen3-0.6B at 36T; MobileLLM-Pro at 1.64T tokens with a logit teacher beats Gemma-3-1B (2T) and Llama-3.2-1B (9T). Without a teacher, the open-data recipes (SmolLM2/3) spent 11T.
3. **Deep-thin wins at fixed tokens.** Falcon-H1's controlled pair (24 layers vs 66 layers, both 1.5B, both 3T tokens): MMLU 62.03→66.11, GSM8K 74.98→82.34, HumanEval 68.29→73.78, IFEval 80.66→83.5. On a memory-bound CPU decoder, depth is nearly free in bytes/token.
4. **Learning-rate: constant/WSD + cooldown is now default** (SmolLM2/3, Falcon-E, MiniCPM, BitNet-2B4T). Cooldown of 10–20% of tokens; required fraction shrinks with longer runs; 1-sqrt beats linear. This matters for a compute-poor lab: train the stable phase once, branch many cheap cooldowns/experiments.
5. **For ternary specifically:** parity with fp claimed "from 3B at 100B tokens" (BitNet b1.58, 2024) and shown at 3.9B/300B tokens (Spectra); at 2B BitNet needed 4T tokens to reach avg 54.19 vs Qwen2.5-1.5B 55.23. The QAT scaling law says weight-quantization error *grows* with tokens, and the Aug-2026 "capability-stratified" paper shows factual recall is the first casualty of ternary weights — which argues directly for ALICE-Next's "retrieve, don't memorize" premise.
6. **Distillation re-opened:** it is how Llama 3.2, Gemma 3 1B/3n, MobileLLM-Pro, Qwen3 small, Nemotron Nano 4B, LFM2 all got cheap. Licence inheritance decides ALICE-Next's licence: a Qwen3/3.5 or Gemma 4 teacher (Apache 2.0) is clean; Llama (Community License), Hunyuan (forbids using outputs to improve other models), FAIR-NC (noncommercial) are not.

## 1. Model survey

### Table 1 — Architecture & training (dense/hybrid, 0.5–4B)

| Model (release) | Params | Tokens | Layers × d_model | Attn (Q/KV) | Tied emb | FFN | Vocab | Ctx | Notable | License | URL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SmolLM2-1.7B (Nov 2024; paper 2025-02-04) | 1.7B | 11T, 4 stages | 24 × 2048 | 32/32 | yes | SwiGLU | 49,152 | 2k→8k | WSD, peak LR 5e-4, 2M batch, 256 H100; FineWeb-Edu+DCLM+Stack-Edu+FineMath | Apache 2.0 | arxiv.org/abs/2502.02737 |
| SmolLM3-3B (2025-07-08) | 3.08B | 11.2T (11.1T + 100B long-ctx + 35B reasoning) | 36 × 2048 | 16/4 | yes | SwiGLU (11008) | 128,256 | 64k (128k YaRN) | NoPE every 4th layer; WSD 2e-4, decay last 10%; 384 H100 × 24 d | Apache 2.0 | huggingface.co/blog/smollm3 |
| Qwen3-0.6B / 1.7B / 4B (2025-04-29) | 0.6/1.7/4B | 36T, 119 langs; 3 stages (>30T @4k; ~5T reasoning; 100s B @32k) | 28×1024 / 28×2048 / 36×2560 | 16/8, 16/8, 32/8 | yes (all three) | SwiGLU (3072/6144/9728) | 151,936 | 32k (4B: 128k) | Strong-to-weak distillation from Qwen3-32B/235B; on-policy KD = ~1/10 GPU-h of RL | Apache 2.0 | arxiv.org/html/2505.09388 |
| Qwen3.5-0.8B / 2B / 4B (2026-03-02) | 0.8/2/4B | not disclosed | 24×1024 / 24×2048 / 32×2560 | hybrid 3:1 Gated DeltaNet : Gated Attn (8/2, 8/2, 16/4; head 256) | yes | 3584 / 6144 / 9216 | 248,320 | 262,144 (1M YaRN) | MTP, early-fusion vision, 201 langs | Apache 2.0 | huggingface.co/Qwen/Qwen3.5-4B |
| Gemma 3 1B (2025-03) | 1.0B | 2T | 26 × 1152 | local:global 5:1, 1024 window | yes | GeGLU | 262,144 | 32k | distilled from larger Gemma | Gemma Terms | huggingface.co/google/gemma-3-1b-it |
| Gemma 3n E2B / E4B (2025-06-26) | 5B / 8B raw; 1.91B / ~4B effective | ~11T | MatFormer nested | PLE + KV sharing | yes | — | 262k | 32k | audio+vision; PLE cached off-accelerator | Gemma Terms | huggingface.co/google/gemma-3n-E2B-it |
| Gemma 4 E2B / E4B (2026-04-02; report arXiv 2607.02770) | 2.3B eff / 5.1B total; 4.5B eff / 8B total | not disclosed | 35 / 42 layers (card) | local:global 4:1 (E2B) / 5:1; 512-token window; unified K/V | yes (+PLE: 2,340M / 2,820M embedder params) | — | 262k | 128k | QAT (int2/int4 weights, int8 acts), MTP drafter, native function-call tokens | **Apache 2.0** | ai.google.dev/gemma/docs/core/model_card_4 |
| Llama 3.2 1B / 3B (2024-09-25) | 1.23B / 3.21B | up to 9T; pruned from 3.1-8B + logit KD from 8B/70B | 16×2048 / 28×3072 | 32/8 / 24/8 | yes | SwiGLU (8192) | 128,256 | 128k | | Llama 3.2 Community | huggingface.co/meta-llama/Llama-3.2-1B |
| MobileLLM-R1-950M (2025-09-12; ICLR 2026) | 0.95B | ~2T curated → 4.2T resampled; <5T total | 22 × 1536 | 24/6 | yes | SwiGLU | 128k | 4k (32k post) | benchmark-driven resampling; "11.7% of Qwen3's tokens" | FAIR NC | arxiv.org/abs/2509.24945 |
| MobileLLM-Pro (2025-10-16) | 1.084B | 1.64T, KL logit-KD from Llama-4-Scout-17B-16E | 30 × 1280 | 20/4; local:global 3:1, 512 window | yes | SwiGLU | 202,048 | 128k | int4 QAT: −0.4% (CPU cfg) / −1.3% | FAIR NC | huggingface.co/facebook/MobileLLM-Pro |
| Phi-4-mini (2025-02; paper 2025-03-03) | 3.8B | 5T (synthetic-heavy) | 32 × 3072 | 24/8 | yes | SwiGLU | 200,064 | 128k (LongRoPE, 25% pos-agnostic dims) | 512 A100 × 21 d | MIT | arxiv.org/html/2503.01743 |
| Falcon-H1 0.5B / 1.5B / 1.5B-Deep / 3B (2025-05; report 2025-07-30) | | 2.5T / 3T / 3T / 2.5T | 36×1024 / 24×2048 / **66×1280** / 32×2560 | parallel attention ∥ Mamba-2 | — | — | 32,768 / 65,536 / 65,536 / 65,536 | up to 256k | μP; end-of-run mix (34B) 52% rewritten + 4.5% synthetic | Falcon LLM License 1.0 | arxiv.org/html/2507.22448 |
| Falcon-E 1B / 3B ternary (2025-05-15) | "1B" (card lists 1.8B tensor params [uncertain]) / 3B | ~1.5T, WSD, from scratch | pure transformer BitNet-style | — | — | — | — | 635–665 MB / 955–999 MB (sources differ) | bf16 twins + onebitllms | Falcon-LLM License | falcon-lm.github.io/blog/falcon-edge |
| Hunyuan 0.5B / 1.8B / 4B / 7B (2025-07-30) | | not disclosed ("similar to A13B", which used 20T) | 1.8B: 32 × 2048 | 16/4, QK-norm | yes | SwiGLU (6144) | 120,818 | 262,144 | fast/slow thinking | Tencent Hunyuan Community (no EU/UK/KR; >100M MAU; no training other models on outputs) | huggingface.co/tencent/Hunyuan-1.8B-Instruct |
| OLMo 2 1B (2025-04/05) | 1.5B total (1.3B non-emb) | 4T OLMo-mix-1124 + 50B Dolmino | 16 × 2048 | 16 | — | SwiGLU | ~100k | 4k | fully open data | Apache 2.0 | huggingface.co/allenai/OLMo-2-0425-1B |
| Nemotron 3 Nano 4B (2026-03-16) | 3.97B | >10T (parent 12B pretrained 20T FP8 → Minitron 9B → Nemotron Elastic 4B; 63B@8k + 150B@49k distill) | 42 layers: 21 Mamba-2, 4 attn, 17 MLP; d=3136 | — | — | — | — | 262k | reasoning on/off | NVIDIA Nemotron Open Model | huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16 |
| LFM2-1.2B / 2.6B (2025-07 / 2025-09) | 1.17B / 2.57B | 10–12T | 16 (10 conv + 6 GQA) / 30 (22 conv + 8 GQA) | double-gated short conv + GQA | — | — | 65,536 | 32k | KD "tempered decoupled top-K" | LFM Open License v1.0 | huggingface.co/LiquidAI/LFM2-2.6B |
| LFM2.5-1.2B (2026-01-05) / 2.6B (2026-08-04) | 1.17B / 2.6B | **28T / ~34T** | same hybrids | | | | 65,536 / 128k (in-place expansion) | 32k / 131k | multi-stage RL; MOPD | LFM1.0 | liquid.ai/blog/lfm2-5-2-6b |
| Granite 4.0 H-1B (2025-10-28) | ~1.5B | >15T | 40: 4 attn + 36 Mamba-2; emb 1536 | 12/4; NoPE | — | 4096 | — | 128k | Granite 4.1 dense 3B/8B/30B followed 2026-04-29 (~15T, 512k ctx) | Apache 2.0 | huggingface.co/ibm-granite/granite-4.0-h-1b |
| BitNet b1.58-2B-4T (2025-04) — ALICE's current model | 2.4B | 4T | 30 × 2560 | 20/5 | — | **ReLU²**, subln | 128,256 | 4k | 2-stage LR (abrupt mid-run decay), WD 0.1 → 0 in cooldown, curated data in stage 2 | MIT | arxiv.org/html/2504.12285 |
| Ternary Bonsai 1.7B / 4B / 8B (PrismML, 2026-04-16) | | not disclosed | fully ternary incl. embeddings, attention, LM head | | | | | | 8B = 1.75 GB; avg 75.5 vs Qwen3-8B 79.3 | Apache 2.0 | prismml.com/news/ternary-bonsai |

### Table 2 — Reported benchmarks (instruct unless marked base)

| Model | MMLU | MMLU-Pro | GSM8K | HumanEval(+) | IFEval | BFCL | Other |
|---|---|---|---|---|---|---|---|
| SmolLM2-1.7B base / inst | — | 19.4 / 19.3 | 31.0 / 48.2 | — | — / 56.7 | — | MT-Bench 6.13 |
| SmolLM3-3B base / inst | MMLU-CF 44.13 | — | 67.63 | HE+ 30.48 | — / 76.7 | — | GPQA-D 35.7; AIME25 9.3 (36.7 w/ thinking) |
| Qwen3-0.6B base / inst(non-think) | 52.81 | 24.74 | 59.59 | EvalPlus 36.23 | 54.5 (think 59.2) | v3 44.1 (think 46.4) | MATH-500 55.2 |
| Qwen3-1.7B base / inst | 62.63 | 36.76 | 75.44 | EvalPlus 52.70 | 68.2 (72.5) | v3 52.2 (56.6) | LCB v5 11.6 (33.2) |
| Qwen3-4B base / inst | 72.99 | 50.58 | 87.79 | EvalPlus 63.53 | 81.2 (81.9) | v3 57.6 (65.9) | Qwen3-4B-Instruct-2507: IFEval 83.4, BFCL-v3 61.9 |
| Qwen3.5-0.8B / 2B / 4B (non-think) | — | 29.7 / 55.3 / 79.1 | — | LCB v6 4B 55.8 | 52.1 / 61.2 / 89.8 | **v4** 25.3 / 43.6 / 50.3 | TAU2 11.6 / 48.8 / 79.9; GPQA-D 4B 76.2; AA-Omniscience hallucination 80–82% (4B/9B) |
| Gemma 3n E2B / E4B | 60.1 / 64.9 | 40.5 / 50.6 | MGSM 53.1 / 60.7 | 66.5 / 75.0 | — | — | LCB 13.2 |
| Gemma 4 E2B / E4B | — | 60.0 / 69.4 | — | LCB v6 44.0 / 52.0 | 94.6 / 96.7 [uncertain] | mid–high 80s v4 (third-party blog) [uncertain] | GPQA-D 43.4 / 58.6; AIME26 37.5 / 42.5 |
| Llama 3.2 1B / 3B | 49.3 / 63.4 | — | 44.4 / 77.7 | — | 59.5 / 77.4 | v2 25.7 / 67.0 | |
| MobileLLM-R1-950M | — | — | — | — | — | — | AIME 15.5; ≈ Qwen3-0.6B on MATH/GSM8K/MMLU/LCB |
| MobileLLM-Pro 1B | 44.8 | — | — | 59.8 | — | — | ARC-C base 52.62 |
| Phi-4-mini 3.8B | 67.3 | 52.8 | 88.6 | 74.4 | 70.1 | 70.3 (version unspecified) | MATH 64.0; Arena-Hard 32.8 |
| Falcon-H1-0.5B | 53.4 | 31.03 | 68.39 | 51.83 | 72.07 | — | MATH-500 58.4 |
| Falcon-H1-1.5B / 1.5B-Deep | 62.03 / 66.11 | 37.8 / — | 74.98 / 82.34 | 68.29 / 73.78 | 80.66 / 83.5 | — | |
| Falcon-H1-3B | 68.3 | 43.69 | 84.76 | 76.83 | 85.05 | — | |
| Falcon-E-1B / 3B inst (HF-LB-v2 normalised) | — | 9.64 / 7.45 | — | — | 54.35 / 60.97 | — | avg 18.59 / 22.65 (Qwen2.5-3B 27.16) |
| Hunyuan-1.8B / 4B | 64.62 / 74.01 (pretrain) | — | 77.26 / 87.49 | — | 67.6 / — | v3 58.3 / 67.9 | τ-Bench 18.2 / 30.1 |
| OLMo 2 1B inst | 40.0 | — | 68.3 | — | — | — | |
| Nemotron 3 Nano 4B | — | — | — | LCB 51.8 (reasoning) | 88.0 (instr.) | v3 61.1 | MATH500 95.4, AIME25 78.5, RULER-128k 91.1, HaluEval 62.2 |
| LFM2-2.6B / LFM2.5-1.2B | 64.42 / — | — / 44.35 | 82.41 / — | — | 79.56 / 86.23 | LFM2.5-2.6B v4 0.569 | IFBench 47.33; GPQA 38.89 |
| Granite 4.0 H-1B | 59.74 | 32.86 | 69.83 | 73 | 78.53 | v3 50.21 | |
| BitNet-2B-4T | 53.17 | — | 58.38 | HE+ 38.4 | 53.48 | — | 0.4 GB, 29 ms/token CPU |

## 2. What generalises (recipe elements)

**(a) Deep-and-thin.** MobileLLM (2024) established it at 125–350M (30 layers at 125M, +2.7/+4.3 pts). It carried to 1–4B: SmolLM3 36×2048, Qwen3-0.6B 28×1024, MobileLLM-Pro 30×1280, Gemma 4 E2B 35 layers, BitNet-2B 30×2560, and Falcon-H1-1.5B-Deep 66×1280 (controlled gains above). Cost is sequential latency, which on a CPU decoder bound by weight bytes/token is minor. **ALICE-Next implication:** at a fixed ~1.4 GB RAM budget, go deeper (32–48 layers) rather than wider.

**(b) Embedding sharing + vocab economics.** Tied embeddings are universal in the table. Vocab size dominates small-model parameter counts: Qwen3-0.6B spends 151,936×1024 ≈ 156M (~26%) on embeddings; Gemma-3-1B 262k×1152 ≈ 302M (~30%); Llama-3.2-1B ≈ 263M (~21%); SmolLM2 49k×2048 ≈ 100M (~6%); Falcon-H1-0.5B chose a 32k vocab. Gemma 3n/4 solve it differently with Per-Layer Embeddings (2.34–2.82B "embedder" params excluded from the "effective" count and cacheable off-accelerator). ALICE's ASCII-pruned 50,256-token vocab is in the SmolLM2/Falcon regime — cheap, but ~2.5–3× more tokens per character of English than 128k–262k vocabs, which costs decode speed and context.

**(c) Multi-stage curriculum ending in a high-quality anneal.** SmolLM2 (4 stages; math 0→~10%→heaviest in decay, Stack-Edu 24% in stage 4), SmolLM3 (web 85→63%, code 12→24%, math 3→13%), Qwen3 (>30T general → ~5T reasoning-heavy → long-context), OLMo 2 (Dolmino 50B anneal: 50% high-quality web + academic/QA/instruction/math), BitNet-2B4T (curated data in the stage-2 cooldown), Phi-4-mini (synthetic "textbook" data throughout), MobileLLM-R1 (metric-driven resampling of open data to 4.2T → Qwen3-0.6B parity). This is the single most compute-efficient lever available to a small lab.

**(d) WSD / constant-LR + cooldown.** MiniCPM: ~10% decay suffices, and SFT-like data can be mixed into the decay; Hägele et al.: constant+cooldown "scales predictably" like cosine, benefits plateau ≈20% cooldown, required fraction falls with run length (≈5% for long runs), 1-sqrt decay beats linear, SWA is free. Used by SmolLM2 (peak 5e-4), SmolLM3 (2e-4, final 10%), Falcon-E, BitNet-2B4T (two-stage abrupt decay + weight-decay 0.1→0). **Lab implication:** one stable-phase checkpoint supports many cheap cooldown branches (data-mix ablations, ternary vs int8 twins) — this is how you make 30 GPU-h/week count.

**(e) Long-context as a late, cheap stage.** SmolLM3: 100B tokens (4k→32k→64k, YaRN to 128k) ≈ 0.9% of budget; Qwen3: hundreds of billions at 32k; Nemotron-4B: 150B at 49k; Hunyuan/Qwen3.5 native 256k. ALICE's 2,048 ctx is now the smallest in the field; an 8–32k stage is ~1–2% of tokens. NoPE-interleaving (SmolLM3, 3:1) and Gemma's local:global 4–5:1 with 512–1024 windows both cut KV memory, relevant for a 2 GB machine.

**(f) Distillation.** Logit KD is how the cheap strong small models were made: Llama 3.2 (from 8B/70B), Gemma 3 1B, MobileLLM-Pro (1.64T tokens → beats 2T/9T peers), Qwen3 small (off-policy on teacher outputs in /think and /no_think, then on-policy KL on student samples; 1,800 vs 17,920 GPU-h for RL on 8B), Nemotron Elastic (≈213B tokens to carve a 4B from a 9B), LFM2 (tempered decoupled top-K). **Provenance consequences:** the teacher's licence and terms flow into the student. Apache-2.0 teachers (Qwen3, Qwen3.5, Gemma 4, Granite, OLMo, SmolLM3) are clean; Llama requires the Community License (naming, 700M-MAU clause); Hunyuan explicitly forbids using outputs "to improve any other AI model"; FAIR-NC is noncommercial. A sovereignty proof that *admits* a teacher must hash the teacher checkpoint into the receipt chain and state it — otherwise the 2026-08-29 "no external teacher" stance is the only clean story.

**(g) Reasoning mid-training + hybrid thinking.** SmolLM3 added 35B reasoning tokens (OpenThoughts3, Llama-Nemotron) mid-training and 140B in post-training; Qwen3 spent ~5T on reasoning-heavy data; Hunyuan/Qwen3.5/Nemotron/Gemma 4 ship fast/slow thinking toggles. For a CPU decoder, long thinking traces are expensive — budgeted thinking (Nemotron's budget control) or none is the realistic default.

**(h) Tool use.** BFCL v3 in the 1–4B dense class clusters at 50–68 (Granite H-1B 50.21, Qwen3-1.7B 52.2, Hunyuan-1.8B 58.3, Qwen3-4B 57.6/65.9, Nemotron-4B 61.1, Hunyuan-4B 67.9, Llama-3.2-3B 67.0 on v2); BFCL v4 (multi-turn, held-out schemas) is much harder: Qwen3.5-4B 50.3, 2B 43.6, 0.8B 25.3, LFM2.5-2.6B 56.9. Gemma 4 introduced native function-call special tokens. The movers are post-training data (Hunyuan: "agent-optimized" on BFCL/τ-Bench; LFM2.5: agentic RL), not pretraining scale.

**(i) 2026 hybrids.** Falcon-H1, Nemotron 3, Granite 4.0-H, LFM2/2.5, Qwen3.5 (3:1 Gated DeltaNet) all moved to SSM/linear-attention mixes for CPU/edge throughput. These are *not* CIS-1-native (fixed-point Mamba-2 / delta-rule recurrences with bit-exact replay are unproven). Pure-transformer 2026 survivors: Gemma 4 (PLE), Granite 4.1 dense, Hunyuan, SmolLM3, Phi-4-mini. ALICE-Next should stay transformer unless a CIS-2 fp32 hybrid reference is built first.

## 3. Token budget for "well-rounded"

Observed budgets vs outcome (MMLU-Pro is the most discriminating shared metric):

| Class | Low-budget examples | High-budget examples | Reading |
|---|---|---|---|
| ~1B | Gemma-3-1B 2T (MMLU-Pro 14.0, with KD); OLMo2-1B 4T; MobileLLM-Pro 1.64T+KD (MMLU 44.8) | Llama-3.2-1B 9T+KD (MMLU-Pro 20.8); SmolLM2-1.7B 11T (19.4); Qwen3-1.7B 36T (36.8 base); LFM2.5-1.2B 28T (44.35) | Open-web-only recipes need ≥10T; KD or rewritten data cuts to ~2T; 28–36T still pays. |
| ~2B | BitNet-2B 4T ternary (MMLU 53.2); Falcon-E-3B 1.5T ternary (weak) | Gemma 3n E2B 11T (MMLU 60.1); Qwen3.5-2B undisclosed (MMLU-Pro 55.3) | Ternary at 2B with 4T ≈ fp 1.5B with 18T (Qwen2.5). |
| ~3–4B | Falcon-H1-3B 2.5T (MMLU 68.3, 52% rewritten); Phi-4-mini 5T synthetic (67.3) | SmolLM3 11.2T (MMLU-CF 44.1); Qwen3-4B 36T (73.0); Granite-4.1-3B ~15T | Synthetic/rewritten mixes reach 36T-class scores at 2.5–5T. |

Tokens-per-parameter in this class run 1,000–60,000 (Qwen3-0.6B ≈ 60,000), far beyond Chinchilla's 20; MiniCPM fit ~192 tokens/param as compute-optimal for their setup, and Sardana & Frankle show quality still rising at 10,000 tokens/param when inference demand dominates — which is exactly ALICE's regime. **Working numbers for ALICE-Next (own data, no teacher):** ≥8–10T at 1B, ≥10–12T at 2B, ≥10–15T at 3B for 2026-competitive "well-rounded"; with a ≥30% rewritten/synthetic mix (Falcon-H1/Phi style) ≈3–5T; with an Apache-2.0 logit teacher ≈1.5–2T.

**Ternary surcharge.** Evidence: BitNet parity "from 3B at 100B tokens" (2024); Spectra TriLM-3.9B = FloatLM-3.9B at 300B tokens on commonsense/knowledge; ParetoQ shows ternary/2-bit/3-bit sit on the same size-accuracy Pareto front and beat 4-bit and binary, with a representational "transition" between 2 and 3 bits; the QAT scaling law (268 runs) finds weight-quantization error *increases* with tokens while activation error (FC2 outliers) bottlenecks W4A4 — relevant to CIS-1's i8 activations; Scaling-Laws-for-Precision models low-precision training as a reduced effective parameter count. Practical reading: plan ternary at ≥1.5–2B, budget ~1.5–2× the fp tokens, keep the BitNet two-stage schedule (WD→0, curated cooldown), and expect factual-recall deficits (Aug-2026 "capability-stratified" result on a ternary conversion of Qwen3.5-0.8B: linear-probe factual recall 26.19% vs 43.76%, 77.1% average task retention) — hence lean on LOOKUP via the receipt-gated gateway rather than parametric memory. Sept-2026 BITCOS packing (1.485 bits/weight, zeros up to 51.5% of ternary weights, 1.18× CPU decode) is a free storage/speed win for any ternary ALICE-Next.

**Compute sanity (my arithmetic, not sourced):** 2B × 10T tokens ≈ 1.2e23 FLOPs ≈ 85k H100-hours at 40% MFU (SmolLM3 actually used 384×24×24 ≈ 221k H100-h for 3B×11.2T). Kaggle's ~30 T4-h/week cannot touch this (a 1B×1T run is ~80k T4-h); the from-scratch plan requires rented GPUs or a 0.3–0.5T-token "proof" scale, with the stable-phase/cooldown-branch trick to amortise.

## 4. 2026 releases checklist (small class)

Qwen3.5-0.8B/2B/4B (2026-03-02, Apache 2.0, hybrid); Gemma 4 E2B/E4B (2026-04-02, **Apache 2.0**, PLE, native tool tokens, QAT); Nemotron 3 Nano 4B (2026-03-16, hybrid); LFM2.5-1.2B (2026-01-05, 28T) and LFM2.5-2.6B (2026-08-04, ~34T); Granite 4.1 3B dense (2026-04-29, Apache 2.0, 512k ctx); Ternary Bonsai 1.7B/4B/8B (2026-04-16, Apache 2.0, fully ternary incl. embeddings/LM head — the closest public analogue to a CIS-1-native model); OLMo 3/3.1 (2025-11/12) shipped only 7B/32B; no Phi-5-mini, SmolLM4, or Llama-4-small found; Qwen3.8 (Aug 2026) has no sub-5B member.

## Key claims (as returned by the research agent, with sources)
- Qwen3 was pretrained on 36 trillion tokens across 119 languages in three stages (>30T at 4k ctx, ~5T reasoning-heavy, hundreds of billions at 32k); Qwen3-0.6B-Base MMLU 52.81, Qwen3-1.7B-Base 62.63, Qwen3-4B-Base 72.99; on-policy distillation used ~1/10 the GPU-hours of RL (1,800 vs 17,920 on Qwen3-8B).  
  <https://arxiv.org/html/2505.09388>
- SmolLM3-3B was trained on 11.2T tokens (11.1T pretraining + 100B long-context + 35B reasoning mid-training) with WSD LR 2e-4 decaying to 0 in the final 10% of steps, on 384 H100s for 24 days; config.json shows 36 layers, hidden 2048, 16 Q / 4 KV heads, vocab 128,256, tie_word_embeddings=true, no_rope_layer_interval=4.  
  <https://huggingface.co/blog/smollm3>
- Falcon-H1-1.5B (24 layers) and Falcon-H1-1.5B-Deep (66 layers) were both trained on 3T tokens; the Deep instruct model scores MMLU 66.11 / GSM8K 82.34 / HumanEval 73.78 / IFEval 83.5 vs 62.03 / 74.98 / 68.29 / 80.66 for the shallow one.  
  <https://huggingface.co/tiiuae/Falcon-H1-1.5B-Deep-Instruct>
- Gemma 4 is released under Apache 2.0; E2B has 2.3B effective / 5.1B total parameters and 35 layers, E4B 4.5B effective / 8B total and 42 layers, both with 128K context and 262K vocab; E2B MMLU-Pro 60.0, E4B 69.4.  
  <https://ai.google.dev/gemma/docs/core/model_card_4>
- The Qwen3.5 small models (9B, 4B, 2B, 0.8B) were released on March 2, 2026; the 4B uses an 8 x (3 x Gated DeltaNet + 1 x Gated Attention) hybrid layout, 32 layers, hidden 2560, tied 248,320 vocab, 262,144 native context, and scores MMLU-Pro 79.1, IFEval 89.8, BFCL-V4 50.3, TAU2-Bench 79.9.  
  <https://github.com/QwenLM/Qwen3.5>
- NVIDIA Nemotron 3 Nano 4B (released March 16, 2026) has 3.97B parameters in a 42-layer hybrid (21 Mamba-2, 4 attention, 17 MLP; hidden 3136), was compressed from Nemotron-Nano-9B-v2 via Nemotron Elastic, lists >10 trillion training tokens, and scores BFCL v3 61.1, IFEval-Instruction 88.0, RULER-128k 91.1.  
  <https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16>
- LFM2.5-1.2B-Instruct (1.17B params, 16 layers: 10 double-gated conv + 6 GQA, vocab 65,536, 32k ctx) was pretrained on 28T tokens and scores MMLU-Pro 44.35, IFEval 86.23, IFBench 47.33, GPQA 38.89, versus Qwen3-1.7B 42.91 / 73.68 / 21.33 / 34.85.  
  <https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct>
- MobileLLM-Pro (1.084B params, 30 layers, hidden 1280, 20 Q / 4 KV heads, vocab 202,048, 128k ctx, local:global 3:1 with 512-token window) was pretrained on ~1.64T tokens with KL-divergence logit distillation from Llama-4-Scout-17B-16E; int4 QAT regression 0.4% (CPU config) / 1.3% (accelerator); FAIR Noncommercial license.  
  <https://huggingface.co/facebook/MobileLLM-Pro>
- Hägele et al. find that constant LR with a cooldown matches cosine, that cooldown benefits plateau at around 20% of training steps, that the required cooldown fraction decreases with longer training, and that a 1-sqrt decay outperforms linear decay.  
  <https://arxiv.org/html/2405.18392>
- The Tencent Hunyuan Community License (v1.8B, Aug 4 2025) does not apply in the EU, UK and South Korea, requires a separate license above 100M monthly active users, and prohibits using Hunyuan outputs to improve any other AI model.  
  <https://huggingface.co/tencent/Hunyuan-1.8B-Instruct/resolve/main/LICENSE>

## Gaps and unverified items (recorded, not papered over)
- Qwen3.5 small-model pretraining token counts are not disclosed on the model cards or GitHub README; the official qwen.ai blog could not be fetched (JS-rendered) and qwenlm.github.io/blog/qwen3.5 returned 404.
- Gemma 4 training token counts are not stated in the model card or technical report. The report fetch returned layer counts (18/26) that conflict with the model card (35/42); I used the card. The Gemma 4 IFEval figures (94.6 / 96.7) and the BFCL 'mid-to-high 80s' figure came from a single fetch / a third-party blog and could not be cross-verified — marked [uncertain].
- Hunyuan dense 0.5B–7B pretraining token count is not disclosed; the '20T' figure belongs to Hunyuan-A13B.
- The official Berkeley Function Calling Leaderboard table (gorilla.cs.berkeley.edu) is JS-rendered and not retrievable; BFCL numbers are from model cards and the llm-stats mirror (last updated 2026-10-06), which lists only 22 models.
- Falcon-E-1B: the HF card lists 1.8B tensor parameters for the '1B' model and memory footprint differs between sources (635 vs 665 MB); context length and vocab size were not found.
- LFM2 licensing: the arXiv abstract summary reported CC-BY-4.0 while the model cards say 'LFM Open License v1.0' / 'LFM1.0'; the commercial terms (revenue threshold) were not verified from the license text.
- Phi-4-mini's BFCL score (70.3) is reported without a BFCL version; Llama 3.2's is BFCL v2 and Qwen3/Hunyuan/Nemotron are v3, so cross-model tool-use comparisons are only approximate.
- OLMo 2 1B base-model benchmark table and learning-rate schedule were not extracted (only instruct MMLU 40.0 / GSM8K 68.3 and the 4T + 50B token counts).
- Ternary Bonsai (PrismML) does not disclose training method (from scratch vs converted/distilled) or token counts.
- Compute-cost estimates in section 3 (H100-hours, T4-hours) are my own FLOP arithmetic at assumed 40%/30% MFU, not sourced figures; only SmolLM3 (384 H100 x 24 days) and Phi-4-mini (512 A100 x 21 days) are reported by their authors.
- Gemma 3n raw parameter count for E2B is given as 'over 5B' (1.91B effective) in Google docs vs '6B' in one card summary; I used 5B.
