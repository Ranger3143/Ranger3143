> Research brief produced on 2026-10-06 by a web-research agent for the ALICE-Next model plan. Every claim carries the URL the agent read; items it could not verify are listed under Gaps. Numbers here are the cited papers' numbers, not Aefinity measurements.

# ANGLE 9 — Architecture ideas that make a 1–3B edge model a new class, under CIS-1 integer-exact inference

**Date:** 2026-10-06. **Method note:** this turn's WebSearch budget was already exhausted when the task started, so every fact below comes from direct fetches of primary sources (arXiv abstracts/HTML, Hugging Face model cards and `config.json`, vendor tech blogs) plus the Hugging Face Hub connector for repo discovery. Nothing was taken from secondary summaries. Items I could not verify are marked [uncertain].

**Design frame (given):** BitNet b1.58-2B-4T is 30 layers, d=2560, 20 q-heads / 5 kv-heads (head_dim 128), FFN 6912 ReLU², vocab 128,256 tied (ALICE prunes to 50,256) — [config.json](https://huggingface.co/microsoft/bitnet-b1.58-2B-4T/blob/main/config.json). CIS-1 already provides exact integer matmul, RMSNorm, RoPE, softmax, ReLU². Anything new must be expressible with those plus table lookups (LUT) and integer compare/argsort, and must fit ~1.4 GB.

Useful derived numbers for BitNet-2B as deployed: KV per token = 30·2·5·128 = 38,400 values → 2048 ctx: 157 MB fp16 / 79 MB int8; 32k ctx: 2.52 GB fp16 / 1.26 GB int8. Vocab pruning 128,256→50,256 at d=2560 removes ~200M embedding parameters.

---

## 1. Per-idea assessment

### 1.1 Ternary MoE (Maple-Preview, Bonsai, MoTE, small-total MoEs)

**Evidence.** DeepGrove's [Maple-Preview](https://hf.co/deepgrove/maple-preview) (MIT, card created 2026-08-04) is a 20B-A1B ternary reasoning MoE: 24 layers, d=2048, 256 experts / 8 active, `moe_intermediate_size` 512, no shared expert, 3:1 SWA-512:global attention with `nope_on_global_attention: true`, QK-norm, partial RoPE 0.5, vocab 151,936 untied; 5.31 GB checkpoint, 131,072 ctx, "218 tok/s M4 Mac mini" ([config.json](https://hf.co/deepgrove/maple-preview/blob/main/config.json)). Benchmarks are images on the card (unread). The card says the preview "may underperform on agentic benchmarks". DeepGrove's [Bonsai](https://huggingface.co/deepgrove/Bonsai) (Mar 2025) is a 500M dense ternary Llama-architecture model trained in <5B tokens (ARC-c 33.36 / MMLU 30.28 vs Qwen2.5-0.5B 32.25 / 33.40), Apache-2. I found no "Bonsai-2" on the Hub; the deepgrove org lists only Bonsai and three maple-preview repos.

Ternary-expert evidence: [MoTE](https://arxiv.org/abs/2506.14435) (Jun 2025, rev. Jan 2026) keeps the pretrained FFN as a shared expert and trains routed experts in {-1,0,1}; at 3.4 GB expert memory it beats MoE-LLaVA by 4.3% avg, with gains "amplif[ied] when memory-constraint goes lower". [MH-MoE](https://arxiv.org/abs/2411.16205) states compatibility with BitNet but gives no numbers in the abstract.

Small-total MoEs that would fit 2 GB when ternary: [Phi-tiny-MoE 3.8B/1.1B](https://arxiv.org/abs/2506.18349) (pruned+distilled from Phi-3.5-MoE with 400B tokens); [SmallThinker-4B-A0.6B](https://arxiv.org/abs/2507.20984) (pre-attention router to prefetch experts from storage, NoPE-RoPE hybrid sparse attention, >20 tok/s at Q4_0 in 1 GB RAM on consumer CPUs); [DeepSeekMoE](https://arxiv.org/abs/2401.06066) 2B "nearly reaches the performance ceiling of its dense counterpart with identical total parameters"; [OLMoE-1B-7B](https://arxiv.org/abs/2409.02060) (64 experts/top-8, 5T tokens, fully open) exceeds Llama2-13B-Chat. [LFM2-8B-A1B](https://huggingface.co/LiquidAI/LFM2-8B-A1B) (Nov 2025; 18 conv + 6 GQA blocks; LFM Open License) shows an edge MoE at 1.5B active.

**Why it matters on a RAM-bound box.** At ~2 bits/weight a dense 5B ternary model (1.25 GB) would out-score a 6B-A1.2B MoE of the same RAM, but it reads all 1.25 GB per token; on a single-channel DDR4 2 GB machine that is a few tok/s. The MoE reads ~0.3 GB/token. So on 2 GB hardware MoE buys *speed at fixed RAM*, not quality at fixed RAM.

**Integer-exactness.** Router = matmul + top-k (integer argsort with deterministic index tie-break) + fixed-point softmax over k + renormalisation (`norm_topk_prob` → integer reciprocal). All within CIS-1. Note Maple keeps `router_dtype: fp32`; a CIS-1 router must be integer and the tie-break rule must be in the spec. **CPU cost:** experts are scattered; without a prefetching router (SmallThinker) FAT32/UEFI paging would stall. **Feasibility: medium. Benefit at ≤3B total: unproven; evidence is at 4–8B total.**

### 1.2 Hybrid attention: sliding-window + global, NoPE on global

**Evidence.** [Gemma 3](https://arxiv.org/html/2503.19786): 5 local : 1 global, 1024-token window; KV overhead at 32K drops from 60% to "<15%"; local layers keep RoPE base 10k, global 1M. Gemma 3 1B = 302M embedding + 698M non-embedding params. Maple uses 3:1 SWA-512:GA with NoPE on global. [SmolLM3](https://huggingface.co/blog/smollm3) (3B, 11.2T tokens, Jul 2025): GQA-4, NoPE every 4th layer, tied embeddings. SmallThinker uses NoPE-RoPE hybrid to shrink KV. [Gemma 3n](https://developers.googleblog.com/en/introducing-gemma-3n-developer-guide/) shares middle-layer K/V with all top layers → "2x improvement on prefill" vs Gemma 3 4B.

**Integer-exactness:** nothing new — SWA is a mask, NoPE removes ops. **CPU cost:** reduces attention FLOPs and KV reads at long context; neutral at 2048. **Feasibility: ~1.0. Benefit: high as soon as the connected variant stuffs retrieved documents into context.**

### 1.3 Mamba/SSM hybrids and gated short-conv hybrids

**Evidence (SSM).** [Falcon-H1](https://arxiv.org/abs/2507.22448) (0.5B–34B, Jul 2025, Falcon-LLM license): parallel attention+Mamba-2 heads inside one mixer block; 1.5B-Deep "outperforms Qwen3-1.7B-Instruct" ([blog](https://falcon-lm.github.io/blog/falcon-h1/)). [Granite 4.0 H-1B](https://huggingface.co/ibm-granite/granite-4.0-h-1b) (Apache-2.0, 2025-10-28): 36 Mamba-2 + 4 attention layers, d=1536, tied embeddings, 128K ctx. Its own card compares against the transformer Granite 4.0 1B: MMLU 59.74 vs 59.39, IFEval 82.37 vs 80.82, **BFCL v3 50.21 vs 54.82, GSM8K 69.83 vs 76.35**, HumanEval 73 vs 74 — i.e. the hybrid is not a free lunch at 1B for tool use and math. [Granite 4.0 H-Micro 3B](https://huggingface.co/ibm-granite/granite-4.0-h-micro) (9:1) shows the same pattern (IFEval 84.32 vs 82.31, BFCL v3 57.56 vs 59.98). [Nemotron-H-4B-Instruct-128K](https://huggingface.co/nvidia/Nemotron-H-4B-Instruct-128K) (pruned/distilled from 8B, "just four Attention layers", BFCL v2 65.88, MMLU 66.96) is research-licence only. [Nemotron-H](https://arxiv.org/abs/2504.03624) smallest is 8B; [Hunyuan-TurboS](https://arxiv.org/abs/2505.15431) is 560B/56B — no small Hunyuan hybrid verified.

**Integer-exactness (Mamba-2/SSD).** Beyond matmul/RMSNorm: softplus(Δ), exp(−softplus(Δ)·A) → per-head decay in (0,1), causal depthwise conv (k=4), SiLU gates, cumulative decay products over chunks, a persistent state (heads×head_dim×N) in i32/i64. All are deterministic in fixed point (LUT for softplus/exp/SiLU; chunked products with renormalisation), but PTQ evidence says SSM activations are outlier-heavy: [Quamba](https://arxiv.org/abs/2410.13229) W8A8 on Mamba-2.8B loses 0.9% zero-shot and needs Hadamard rotation of outputs; [Quamba2](https://arxiv.org/abs/2503.22879) W4A8/W8A8 loses 1.6% avg. Whether the recurrence itself ran in int8 or half in those works is [uncertain]. **Feasibility: medium-low; benefit at 2048 ctx: low; at 32k+: real.**

**Gated short convolutions (LFM2) — the integer-friendly alternative.** [LFM2](https://www.liquid.ai/blog/liquid-foundation-models-v2-our-second-series-of-generative-ai-models) (Jul 2025): 16 blocks = 10 double-gated short-range conv + 6 GQA, found by hardware-in-the-loop search on CPU; "2x faster decode and prefill than Qwen3 on CPU" (Snapdragon S24 Ultra, Ryzen HX370); LFM2-1.2B GSM8K 58.3 vs Qwen3-1.7B 51.4, MMLU 55.23 vs 59.11; 10T tokens, distilled from LFM1-7B; licence restricts >$10M-revenue commercial use ([tech report](https://arxiv.org/abs/2511.23404), Nov 2025). Ops: linear projections, elementwise int8 gates, short depthwise causal conv — *no exp, no state recurrence*. **Feasibility: ~1.0 (it is matmul + multiply). Benefit: strongest CPU-speed evidence of any sequence mixer at 1B.**

### 1.4 Multi-token prediction heads for self-speculation

**Evidence.** [Gloeckle et al.](https://arxiv.org/html/2404.19737): with n=4, "multi-token prediction models are worse than the baseline for small model sizes" (300M–1.3B), gains from ~3B up; self-speculative decoding gives 3.0× (code, 2.5 accepted of 3), 2.7× (text). [DeepSeek-V3](https://arxiv.org/html/2412.19437v1): sequential MTP module with D=1 (one extra transformer block, *shared* embedding and output head) improves quality even on the small 15.7B-A2.4B ablation (HumanEval 20.7→26.8) and at inference "the acceptance rate of the second token prediction ranges between 85% and 90%", "1.8 times TPS". [EAGLE-3](https://arxiv.org/abs/2503.01840): up to 6.5× (GPU, batch).

**Integer-exactness.** The MTP block is the same ops as a layer. Under greedy decoding, speculative verification is *lossless*: the emitted token sequence — and therefore the receipt chain — is identical to plain decode; only the step structure changes, which the receipt can record. **CPU cost:** +1 block (~1/30 of weights); verifying 2 tokens reads the weights once, so up to ~1.8× decode in the memory-bound regime; on a 4-core AVX2 box the 2-token verify may become compute-bound [uncertain — measure on box1]. **Feasibility: high. Quality benefit at 2B: uncertain (use D=1 as an accelerator, not for quality).**

### 1.5 Memory / retrieval layers (Memory Layers at Scale, Engram, UltraMem, Titans, RETRO)

**Evidence.** [Memory Layers at Scale](https://arxiv.org/html/2412.09764) (Meta, Dec 2024): product-key lookup (two half-key sets, top-k on half-keys, softmax over selected keys, gather values; "Memory+" adds `silu` gating, one shared pool, 3 memory layers replacing FFNs); base 134M–8B, memory up to 128B params, 1T tokens; a 1.3B base with 128B memory params reaches NQ 20.78 vs Llama2-7B 25.10 and TriviaQA 62.14 vs 64.00. [Engram](https://arxiv.org/html/2601.07372) (DeepSeek-AI + PKU, Jan 2026, rev. Jul 2026): tokenizer-compressed ids → suffix 2–3-grams → K multiplicative-XOR hashes into prime-sized tables → concat → RMSNorm dot-product gate against h_t → depthwise conv k=4 + SiLU → residual, inserted at layers 2 and 15; O(1)/token; 3B/100B-token ablation val loss 1.768 vs 1.808; at 27B vs iso-param/iso-FLOP MoE: MMLU +3.4, BBH +5.0, NIAH 84.2→97.0. [UltraMem](https://arxiv.org/abs/2411.12364) (ICLR 2025): 20M memory slots, 2–6× faster inference than MoE at equal budget. [Titans](https://arxiv.org/html/2501.00663): M_t=(1−α_t)M_{t−1}+S_t, S_t=η_t S_{t−1}−θ_t∇‖M(k_t)−v_t‖²; memory is an MLP (L≥2); evaluated at 170M–760M only.

**Integer-exactness.** PKM/Engram need only: integer hash, table gather, matmul, top-k, fixed-point softmax/sigmoid LUT, RMSNorm, depthwise conv. All CIS-1. Titans needs per-token outer-product gradient updates of an MLP — deterministic in fixed point but numerically delicate and heavy. **Edge-specific win nobody has shipped:** the tables are sparsely gathered (tens of rows/token), so they can be *disk-resident* and paged by the unikernel's FAT32 loader — knowledge outside the 2 GB RAM floor — and, for the connected variant, verified LOOKUP results can be *written* into a receipt-logged table with Rule-B provenance. Caveat: Engram/PKM must be trained with the backbone (or via continued pretraining). **Feasibility: high (PKM/Engram), low-medium (Titans). Benefit at ≤3B: shown at 1.3B (PKM) and 3B (Engram).**

### 1.6 Tool-call-native vocabulary

**Evidence.** [Octopus v2](https://arxiv.org/abs/2404.01744) (Gemma-2B + one "functional token" per function): surpasses GPT-4 in function-call accuracy and latency, 95% context reduction, 35× lower latency than Llama-7B+RAG. [ToolGen](https://arxiv.org/abs/2410.03439) (ICLR 2025): ~47k tools as vocabulary tokens; retrieval and calling by generation. [FunctionGemma-270M](https://huggingface.co/google/functiongemma-270m-it) (gated; card dates inconsistent [uncertain]): control tokens `<start_function_call>`, `<end_function_call>`, `<escape>`; BFCL Simple 61.6%, Multiple 63.5%; Mobile Actions 58%→85% after fine-tune; 125.9 tok/s decode at 288 MB on S25 Ultra. Small-model function calling exists at 1–1.5B ([Hammer2.1-1.5b](https://huggingface.co/MadeAgents/Hammer2.1-1.5b), [xLAM-2-1b](https://huggingface.co/Salesforce/xLAM-2-1b-fc-r), both CC-BY-NC; Granite H-1B BFCL v3 50.21, Apache-2.0).

**For ALICE:** reserve ~64 control tokens in the pruned vocab (`<|tool_call|>`, `<|tool_result|>`, `<|calc|>`, `<|lookup|>`, `<|cite|>`, `<|verify|>`, `<|abstain|>`, JSON structural tokens). The receipt-gated gateway becomes a token-level state machine: tool tokens are only legal in sanctioned states, and the hashed receipt covers token ids, not strings. **Integer-exactness: zero new ops. Cost: +64 embedding rows. Feasibility: ~1.0. Benefit: directly the "tool expert" goal.**

### 1.7 Dual-model designs (tiny warden/router + main)

**Evidence.** [Llama Prompt Guard 2-22M](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M): DeBERTa-xsmall, 512-token window, AUC .995, recall 88.7% @1% FPR, 19.3 ms/A100, Llama 4 licence. [Gemma 3 270M](https://developers.googleblog.com/en/introducing-gemma-3-270m/) (Aug 2025): 170M embedding + 100M transformer, pitched for routing/classification, 0.75% battery for 25 conversations (INT4). [I-BERT](https://arxiv.org/abs/2101.01321) (ICML 2021) proves *integer-only* encoder inference (polynomial GELU/softmax, integer sqrt LayerNorm) at FP-level GLUE accuracy — the exact precedent for a CIS-1 warden. [Speculative cascades](https://arxiv.org/abs/2405.19261) and [RouteLLM](https://arxiv.org/abs/2406.18665) (>2× cost cut) show router+defer designs.

**For ALICE:** a 20–100M integer encoder (≈25–100 MB int8) that (a) screens every LOOKUP result for injection *before* it enters context, (b) decides abstain-vs-lookup, (c) scores answer/evidence agreement for self-fact-check — all inside the receipt. **Feasibility: high. Benefit: high for the connected variant; it is what makes "fact-check herself" trustworthy.**

### 1.8 Embedding sharing and design-time vocabulary pruning

**Evidence.** [Scaling Laws with Vocabulary](https://arxiv.org/abs/2407.13623) (NeurIPS 2024): optimal vocab grows with compute; for a 3B model at 2.3e21 FLOPs going 32K→43K lifted ARC-C 29.1→32.0 — i.e. ~40K is near-optimal at our scale, not a compromise. Gemma 3 1B spends 302M of 1B params on a 262K vocab; Gemma 3 270M spends 170M of 270M. [MobileLLM](https://arxiv.org/abs/2402.14905): embedding sharing + deep-thin + GQA + block-wise layer sharing, +2.7%/+4.3% at 125M/350M. [Gemma 3n](https://ai.google.dev/gemma/docs/gemma-3n) PLE caches per-layer embeddings outside accelerator memory (E2B: 5B raw, ~1.91B effective). Apple's on-device 3B uses 4-bit embeddings ([Apple 2025](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates)).

**For ALICE-Next:** choose a 32–48K English-first BPE + control tokens *at design time*, tied embeddings, int8 (or 4-bit) embedding table (~84 MB at d=2048, 40,960 vocab). **Feasibility: ~1.0; benefit: ~200–250M params and the softmax head cost, free.**

### 1.9 Byte-level / dynamic chunking

**Evidence.** [BLT](https://arxiv.org/html/2412.09871): entropy-based dynamic patches of 6–8 bytes, light local encoder/decoder, FLOP-controlled parity with Llama 3 BPE from 1B to 8B, "nearly 50% inference flop savings" at patch 8 (8B). [H-Net](https://arxiv.org/abs/2507.07955) (Jul 2025): learned dynamic chunking; single-stage byte H-Net beats a BPE transformer, 2-stage matches a 2× larger one. **Ops beyond CIS-1:** a tiny entropy LM, cross-attention encoder/decoder, hash n-gram embeddings (BLT); cosine-similarity boundary scores + smoothing division (H-Net). Deterministic thresholds are integer-feasible but add a second model and variable per-byte cost. For English-first edge use, a 40K BPE already yields ~4 chars/token, so the payoff is robustness and tokenizer-free deployment, not speed. **Feasibility: medium-low. Benefit at ≤3B: parity, not gain.**

### 1.10 Early exit / layer skip / nested depth

**Evidence.** [LayerSkip](https://arxiv.org/abs/2404.16710) (ACL 2024; Llama 1B/1.5B/7B/13B): layer dropout + shared early-exit loss; self-speculative decoding reuses KV; 2.16× (CNN/DM), 1.82× (code), 2.0× (TOPv2). [Mixture-of-Depths](https://arxiv.org/abs/2404.02258): top-k token routing per block, static graph, "upwards of 50% faster to step". Gemma 3n MatFormer: an E2B sub-model nested in E4B with Mix-n-Match depth/width. [YOCO](https://arxiv.org/abs/2405.05254): early-exit prefill "without changing the final output".

**Integer-exactness.** Exit decision = integer logit-margin compare → deterministic; the receipt records the exit layer per token; LayerSkip self-speculation is lossless under greedy. **CPU cost:** decode is weight-read-bound, so skipping half the layers ≈ 2×. **Feasibility: high. Benefit at 1–3B: demonstrated (1.5B code model 1.82×).**

### 1.11 KV-cache quantization and sharing

**Evidence.** [KIVI](https://arxiv.org/abs/2402.02750) 2-bit (per-channel K, per-token V): 2.6× peak memory, 2.35–3.47× throughput. [KVQuant](https://arxiv.org/abs/2401.18079): <0.1 ppl at 3-bit (pre-RoPE per-channel keys). [TurboQuant](https://arxiv.org/abs/2504.19874) (Google, Apr 2025): 3.5 bits/channel "absolute quality neutrality". Apple on-device: 8-bit KV, and a 5:3 block split where block 2 reuses block 1's final-layer KV → 37.5% KV reduction. [CLA](https://arxiv.org/abs/2405.12981): sharing KV between adjacent layers halves KV at 1B and 3B from scratch with comparable accuracy.

**Integer-exactness:** int8 per-token K/V with integer scales is exact; 4-bit groupwise with integer scales is exact; per-channel-K schemes need a token-group residual buffer — doable. **Benefit:** at 2048 ctx BitNet-2B's KV is 79 MB int8 (not the bottleneck); at 32k it is 1.26 GB int8 all-global vs ~243 MB with 5:1 SWA-1024, and ~120–160 MB with CLA/KV-sharing on top. **Feasibility: high. Benefit: medium, rising with context.**

---

## 2. Ranking by benefit × feasibility (for a CIS-1, 1–3B, 2 GB target)

| Rank | Idea | Evidence at ≤3B | Extra ops beyond CIS-1 | CPU cost | Feasibility | Verdict |
|---|---|---|---|---|---|---|
| 1 | Tool-call-native control tokens + grammar-gated decoding | Octopus v2 (2B), FunctionGemma (270M), Hammer/xLAM 1–1.5B | none | +64 embedding rows | 1.0 | Adopt now (also retrofit to BitNet-2B) |
| 2 | Design-time 32–48K vocab, tied int8 embeddings | Vocab scaling law (3B), Gemma 3 1B/270M embedding share | none | −200M params | 1.0 | Adopt |
| 3 | Hybrid SWA(512–1024):global 3:1–5:1, NoPE+QK-norm on global | Gemma 3 1B, SmolLM3 3B, Maple-A1B, SmallThinker | none | ↓KV, ↓attn at long ctx | 1.0 | Adopt |
| 4 | Gated short-conv mixer for most layers (LFM2-style) | LFM2-1.2B: 2× CPU decode/prefill | elementwise gates, short depthwise conv | ↓ per-token | 0.95 | Adopt as the primary mixer |
| 5 | Integer warden (20–100M encoder) in the receipt gateway | Prompt Guard 2 22M, I-BERT | LUT GELU/sigmoid | ~ms per check | 0.9 | Adopt (connected variant) |
| 6 | Early-exit / MatFormer nesting + LayerSkip self-speculation | LayerSkip 1.5B 1.82×, Gemma 3n E2B⊂E4B | integer margin compare | up to ~2× | 0.9 | Adopt |
| 7 | MTP D=1 head for lossless self-speculation | DeepSeek-V3 85–90% acceptance, 1.8× TPS; Gloeckle negative <3B for n=4 | none | +1 block, ~1.8× decode | 0.85 | Adopt as accelerator only |
| 8 | int8 KV (+ CLA / KV-sharing) | CLA 1B/3B, Apple 3B | integer scales | ↓KV 2–10× | 0.9 | Adopt (matters at ≥8k ctx) |
| 9 | Engram / product-key conditional memory, disk-resident, receipt-writable | PKM 1.3B, Engram 3B ablation | hash, gather, top-k, LUT | O(1) gathers/token | 0.75 | Prototype — the genuinely new-class item |
| 10 | Ternary fine-grained MoE (≈6B-A1.2B) | Phi-tiny-MoE 3.8B, SmallThinker 4B, OLMoE 7B; Maple 20B | integer router + argsort | expert paging in UEFI | 0.55 | Defer to v2; training cost high |
| 11 | Mamba-2 SSD hybrid | Falcon-H1 1.5B strong; Granite H-1B mixed (BFCL −4.6) | softplus/exp/SiLU LUTs, i64 state, chunked decay | state 50–60 MB; wins only at long ctx | 0.45 | Skip for v1 |
| 12 | Byte-level / dynamic chunking | BLT/H-Net parity at 1B | entropy LM, cross-attn, boundary division | variable per byte | 0.4 | Research only |
| 13 | Titans test-time memory | ≤760M only | per-token gradient updates | heavy | 0.3 | Watch |

## 3. What the top items compose into (sketch, not a spec)

An **ALICE-Next-2B** that is CIS-1-native end to end: 24–28 blocks at d≈2048–2304, ~2/3 gated-short-conv mixers and ~1/3 GQA (16q/4kv, head 128) with most attention layers SWA-1024 and two NoPE+QK-norm global layers; ReLU² FFN (keeps today's kernels); 40,960-token tied int8 vocab including 64 control tokens; one MTP block sharing the head; LayerSkip-style early-exit loss during training; int8 KV. With only ~8 attention layers of 512 KV dims, KV at 2048 ctx is ~17 MB int8 and ~73 MB at 32k — leaving a budget of several hundred MB for a disk-paged Engram/PKM table and a ≤100 MB integer warden. Ternary weights ≈0.5 GB, embeddings ≈85 MB. The air-gapped variant ships the same weights with an `<|abstain|>` policy; the connected variant adds the warden, the LOOKUP/CALC token grammar and a receipt-written memory table. No published model combines integer-exact replayable inference, a tool-token grammar enforced by the inference engine, and a disk-resident conditional-memory table — that combination is the "new class" claim.

**Licensing/provenance notes that affect these choices:** everything in rank 1–8 is an architectural pattern, not a weight dependency, so from-scratch training keeps the sovereignty proof intact. If distillation is re-opened: Granite 4.0 (Apache-2.0) and OLMoE (fully open) are clean teachers; LFM2 (revenue-capped licence), Falcon-E/H1 (Falcon-LLM licence), Nemotron-H-4B (research-only), Hammer/xLAM (CC-BY-NC) are not clean for a commercial edge product. Maple-Preview is MIT but 5.31 GB.

## Key claims (as returned by the research agent, with sources)
- Maple-Preview (DeepGrove, HF card created 2026-08-04, MIT) is a 20B-A1B ternary MoE with 24 layers, hidden 2048, 256 experts / 8 active, moe_intermediate_size 512, a 3:1 sliding_attention(512):full_attention layer pattern, nope_on_global_attention=true, QK-norm, partial RoPE 0.5, vocab 151,936, 5.31 GB checkpoint, 131,072 ctx, '218 tok/s M4 Mac mini'.  
  <https://hf.co/deepgrove/maple-preview>
- Granite 4.0 H 1B (Apache-2.0, 2025-10-28) has 36 Mamba-2 + 4 attention layers and scores BFCL v3 50.21 and GSM8K 69.83 versus 54.82 and 76.35 for the transformer Granite 4.0 1B, while MMLU is 59.74 vs 59.39 and IFEval 82.37 vs 80.82.  
  <https://huggingface.co/ibm-granite/granite-4.0-h-1b>
- Gemma 3 uses 5 local sliding-window layers (1024-token span) per global layer, reducing KV-cache overhead at 32K context from ~60% to under 15%; the 1B model has 302M embedding and 698M non-embedding parameters.  
  <https://arxiv.org/html/2503.19786>
- LFM2 (released 2025-07-10) uses 10 double-gated short-range convolution blocks and 6 GQA blocks out of 16, claims 2x faster decode and prefill than Qwen3 on CPU (Snapdragon S24 Ultra, AMD Ryzen HX370), and LFM2-1.2B scores GSM8K 58.3 vs Qwen3-1.7B 51.4 and MMLU 55.23 vs 59.11.  
  <https://www.liquid.ai/blog/liquid-foundation-models-v2-our-second-series-of-generative-ai-models>
- DeepSeek-V3's sequential MTP module (D=1, shared embedding and output head) reaches an 85%-90% acceptance rate for the second predicted token and delivers 1.8x TPS when used for speculative decoding.  
  <https://arxiv.org/html/2412.19437v1>
- Gloeckle et al. (2024): with n=4 multi-token prediction, models are worse than the next-token baseline at 300M-1.3B and only outperform at larger scale; self-speculative decoding gives 3.0x speedup on code and 2.7x on text.  
  <https://arxiv.org/html/2404.19737>
- Memory Layers at Scale (Meta, Dec 2024): a 1.3B base with a product-key memory of 128B parameters reaches NaturalQuestions 20.78 and TriviaQA 62.14 versus Llama2-7B's 25.10 and 64.00.  
  <https://arxiv.org/html/2412.09764>
- Engram (DeepSeek-AI and Peking University; arXiv v1 2026-01-12) forms suffix 2-3-grams from tokenizer-compressed ids, hashes them with multiplicative-XOR functions into prime-sized tables, gates the retrieved vector against the hidden state, and in a 3B/100B-token ablation reaches validation loss 1.768 vs 1.808 baseline.  
  <https://arxiv.org/html/2601.07372>
- LayerSkip (ACL 2024) reports self-speculative decoding speedups of up to 2.16x on CNN/DM summarization, 1.82x on coding and 2.0x on TOPv2 semantic parsing across Llama models including 1B/1.5B.  
  <https://arxiv.org/abs/2404.16710>
- Llama Prompt Guard 2-22M is a 22M-parameter DeBERTa-xsmall classifier with a 512-token window, English AUC .995, 88.7% recall at 1% FPR, and 19.3 ms latency on an A100, released under the Llama 4 Community License.  
  <https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M>

## Gaps and unverified items (recorded, not papered over)
- WebSearch budget for this turn was exhausted before the task began (200-call shared limit), so coverage relies on direct fetches of URLs I already knew plus the Hugging Face Hub connector; niche 2026 items (e.g. any ternary-MoE paper below 4B total, new Bonsai releases) may have been missed. A follow-up message can resume searching.
- No 'Bonsai-2' exists on the Hub under deepgrove (only Bonsai 500M and three maple-preview repos were listed); if 'Bonsai-2' refers to a paper or another org, it was not located.
- Maple-Preview benchmark scores are images on the card and were not read; I could not verify its reasoning numbers or its claimed 5-16x speed advantage over Gemma 4 / Qwen3.5 / gpt-oss.
- The Berkeley Function Calling Leaderboard page is JavaScript-rendered and returned no table; small-model BFCL numbers come only from individual model cards (Granite H-1B 50.21 v3, Nemotron-H-4B 65.88 v2, FunctionGemma 61.6% Simple).
- FunctionGemma-270M card dates are inconsistent (the fetched text says 'July 2024' while the base Gemma 3 270M launched 2025-08-14 and the Hub shows last update 2026-01-14); release date is [uncertain].
- Whether Quamba/Quamba2 run the selective-scan recurrence itself in int8 or keep internal state in half precision is [uncertain]; MambaQuant (correct ID arXiv 2501.13484) was identified but its W8A8 numbers were not fetched.
- No small (<=4B) Hunyuan Mamba hybrid was verified; Hunyuan-TurboS is 560B/56B.
- Phi-tiny-MoE (3.8B/1.1B) per-benchmark numbers vs dense 1-2B models were not extracted from the SlimMoE paper, only the Phi-mini-MoE comparisons.
- CPU speedups for MTP/LayerSkip self-speculation are literature values on GPUs; actual gains on ALICE's AVX2 ternary kernels (compute- vs memory-bound regime) are unmeasured and should be timed on box1/box2.
- Octopus v2 arXiv page reported a 'latest revision September 11, 2026' date that could not be cross-checked.
