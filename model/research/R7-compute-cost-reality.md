> Research brief produced on 2026-10-06 by a web-research agent for the ALICE-Next model plan. Every claim carries the URL the agent read; items it could not verify are listed under Gaps. Numbers here are the cited papers' numbers, not Aefinity measurements.

# ANGLE 7 — Compute-cost reality for training a 1–3B ternary model (as of 2026-10-06)

Scope: what it actually costs, in GPU-hours and dollars, to train ALICE-Next at 1–3B params (bf16 and ternary QAT), what the free tiers can and cannot carry, and what data prep costs. All arithmetic uses the 6·N·D FLOP rule (no attention term; +5–10% at 2–4k context) and is reproducible from the assumptions stated. Prices were read on 2026-10-06 unless noted. Items I could not verify are marked [uncertain]; see Gaps.

## 1. Hardware peaks used (dense, bf16 unless noted)

| Device | Dense bf16 peak | Memory | Source |
|---|---|---|---|
| H100 SXM | 989 TFLOPS (NVIDIA lists 1,979 "with sparsity"; dense = ½) | 80 GB, 3.35 TB/s | https://www.nvidia.com/en-us/data-center/h100/ |
| B200 | ~2.25 PFLOPS (derived: DGX B200 "72 PFLOPS FP8, sparse; dense is ½" → 4.5 PF FP8/GPU → bf16 ½) | 180 GB | https://www.nvidia.com/en-us/data-center/dgx-b200/ |
| A100 | 312 TFLOPS (standard spec, not re-fetched) | 40/80 GB | — |
| L4 | 121 TFLOPS (242 sparse) | 24 GB, 300 GB/s, 72 W | https://www.nvidia.com/en-us/data-center/l4/ |
| A10 | 125 TFLOPS (250 sparse) | 24 GB, 600 GB/s | https://www.nvidia.com/en-us/data-center/products/a10-gpu/ |
| T4 | 65 TFLOPS FP16 | 16 GB, 320 GB/s, 70 W | https://www.nvidia.com/en-us/data-center/tesla-t4/ |
| TPU v5e (per chip) | 197 TFLOPS bf16, 393 TOPS int8 | 16 GB HBM | https://docs.cloud.google.com/tpu/docs/v5e |
| TPU v6e Trillium (per chip) | 918 TFLOPS bf16 | 32 GB HBM, 1,638 GB/s | https://docs.cloud.google.com/tpu/docs/v6e |

## 2. Measured training throughput for 1–3B-class dense models (the only honest anchors)

| Run | Hardware | Measured | Implied MFU (6ND) |
|---|---|---|---|
| SmolLM3-3B: 11.2T tokens, 384 H100, 24 days, nanotron, seq 4096, GBS 2.36M | H100 | 11.2e12 / (384·24·86400 s) = **~14,070 tok/s/GPU** | ~26% (all-in, incl. restarts/evals) — https://huggingface.co/blog/smollm3 |
| SmolLM2-1.7B: 11T tokens, 256 H100, seq 2048, GBS ~2M tokens, LR 5e-4 | H100 | duration **not disclosed** | — https://arxiv.org/html/2502.02737v1 |
| TinyLlama-1.1B: 3T tokens, 16 A100-40G, 90 days | A100 | **24k tok/s/GPU**, "56% MFU" | 51% on 6ND basis — https://github.com/jzhang38/TinyLlama |
| torchtitan Llama-3.1-8B, 8 H100, FSDP | H100 | 6,258 tok/s/GPU eager; 6,674 compile; **9,409 compile+FP8**; "33% to 42% MFU" non-FP8 | 30% / 46%-of-bf16-peak — https://arxiv.org/html/2410.06511 |
| Llama 3.2 1B / 3B: "up to 9T tokens", "370k" / "460k" H100-80GB GPU-hours, with Llama-3.1-8B/70B logits as token-level targets | H100 | **6,760 / 5,440 tok/s/GPU-equivalent** | ~4% — dominated by teacher forward passes; this is what logit distillation costs at scale — https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/MODEL_CARD.md |

Takeaways. (i) At 1–3B on H100 a well-tuned single node (FSDP + torch.compile + FlashAttention, 2–4k seq) lands at 35–50% MFU in steady state; whole-run averages at scale are ~25–30% (SmolLM3). I use 40% for the dollar table and show 35–45% bounds. (ii) Small-vocab helps: ALICE's 50,256-token head is ~2.5× cheaper than Llama-3's 128,256 head in lm_head FLOPs and memory. (iii) Distilling from a teacher is not "free capability": a 1.7B/4B/8B teacher adds +38%/+89%/+178% FLOPs on top of a 1.5B student's 6ND (forward-only 2·N_teacher per token); offline storage of top-32 fp16 logits for 100B tokens is ~12.8 TB, so do it online or not at all.

## 3. Ternary (BitNet-style QAT) training overhead

- TII Falcon-E (1.8B and 3B BitNet models, "approximately 1.5 Tera Tokens", WSD schedule): "In our tests, we estimate the overhead to be around ~20% between non-Bitnet pre-training against Bitnet pre-training." https://huggingface.co/blog/tiiuae/falcon-edge  (TII also upstreamed BitNet pretraining into Megatron-Core.)
- Training memory is NOT reduced: "training happens in bfloat16 as activations and gradients are always calculated in that precision"; only full fine-tuning is supported (no LoRA). https://huggingface.co/blog/axolotl-ai-co/finetuning-ternary-llms-tii-axolotl
- Microsoft BitNet b1.58 2B4T: 4T tokens, two-stage LR/WD schedule, ReLU², RoPE, subln, 4096 ctx, MIT license; bf16 master weights published separately (microsoft/bitnet-b1.58-2B-4T-bf16, 2,412.8M params). Hardware, duration and throughput are **not disclosed** in the report. https://arxiv.org/html/2504.12285v2 ; https://huggingface.co/microsoft/bitnet-b1.58-2B-4T
- I therefore model ternary QAT as **1.2× bf16 GPU-hours, same memory** (fake-quant/STE over bf16 master weights). Custom fused absmean/absmax kernels could pull this toward ~1.1× but nobody publishes that number.

## 4. Cloud prices (per GPU-hour, read 2026-10-06)

| GPU | Cheapest spot | Cheapest on-demand | Typical neo-cloud | Hyperscaler |
|---|---|---|---|---|
| H100 | Vast.ai $0.89; Nebius "from $0.79" (dynamic, 15-min repricing) | Lium $1.30 (verified in stock); Vast $1.73; RunPod PCIe community $1.99 | RunPod SXM $2.69 community / $3.49 secure; getdeploying **median $3.63**; Nebius $3.85 ($4.50 reserved from 2026-10-01); Lambda SXM $3.99–4.29; Modal $3.95 | AWS p5.48xlarge $55.04/h = **$6.88**, spot $28.34 = $3.54; Capacity Block $5.191; GCP ~$10.98 and Azure ~$12.29 [secondary, Spheron May-2026] |
| H200 | Vast $1.34 | Vast $3.20 | RunPod $3.59/$4.59; Nebius $4.50; Modal $4.54; median $4.59 (+4% 90-day) | AWS p5e Capacity Block $5.97 |
| B200 | Spot range $3.20–5.94 | Packet·ai $3.75 (in stock) | Lium $5.50; RunPod $5.98/$6.79; Vast $6.25; Modal $6.25; **median $6.25 (+17% YoY)**; Lambda $6.69–6.99; Nebius $7.15 ($8.50 reserved) | AWS p6-b200.48xlarge $113.93/h = **$14.24**, spot $59.41 = $7.43; Capacity Block $12.355 |
| A100 | — | RunPod SXM $1.39 / PCIe $1.19 | Lambda 40GB $1.99, 80GB $3.99; Modal 80GB $2.50 | AWS p4d Capacity Block $1.475 |
| L4 | AWS g6.xlarge spot $0.601 | RunPod $0.44/$0.49 | Modal $0.80 | AWS g6.xlarge $0.805 |
| A10 / A10G | AWS g5.xlarge spot $0.49 | Modal A10 $1.10 | Lambda A10 $1.29 | AWS g5.xlarge $1.006 |
| T4 | AWS g4dn.xlarge spot $0.285 | AWS $0.526 | Modal $0.59 | — |
| CPU (data prep) | AWS c7a.16xlarge (64 vCPU, 128 GiB) spot $1.209 | on-demand $3.284 | — | — |

Sources: https://getdeploying.com/gpus/nvidia-h100 , https://getdeploying.com/gpus/nvidia-h200 , https://getdeploying.com/gpus/nvidia-b200 , https://www.runpod.io/pricing , https://lambda.ai/service/gpu-cloud , https://nebius.com/prices , https://modal.com/pricing (per-second rates ×3600), https://instances.vantage.sh/aws/ec2/p5.48xlarge , https://instances.vantage.sh/aws/ec2/p6-b200.48xlarge , https://instances.vantage.sh/aws/ec2/g6.xlarge , https://instances.vantage.sh/aws/ec2/g5.xlarge , https://instances.vantage.sh/aws/ec2/g4dn.xlarge , https://instances.vantage.sh/aws/ec2/c7a.16xlarge , https://aws.amazon.com/ec2/capacityblocks/pricing/ , https://www.spheron.network/blog/gpu-cloud-pricing-comparison-2026/ . Note the discrepancy: Spheron (May 2026) lists Lambda H100 at $2.49–3.44; Lambda's own page today shows $3.99–4.29 — neo-cloud H100 is flat-to-up, B200 is up 17% YoY; do not assume prices fall during a multi-month plan.

TPU on-demand/spot prices: the Google pricing page is JS-rendered and could not be read [uncertain]. TPU v6e has been GA since 2024-12-16 and TPU7x (Ironwood) since 2026-03-31 (Cloud TPU release notes, via search summary).

## 5. Free tiers (what they are worth to this plan)

- **Kaggle**: ~30 GPU-h/week (program fact; gpuperhour.com calls it "user-reported; Kaggle doesn't publish official figures"), 12-h GPU sessions, 9-h TPU sessions, T4×2 or P100, TPU v5e-8 (replaced v3-8 in 2025) [secondary source]; weekly TPU quota [uncertain, commonly 20 h]. Colab Pro/Pro+ subscribers reportedly get +15/+30 Kaggle GPU-h/week [uncertain]. https://gpuperhour.com/blog/free-cloud-gpus-and-credits (2026-09-21)
  - Capacity math: T4×2 at 25% MFU for 60 T4-GPU-h/week ≈ **0.6B tokens/week** for a 1B model → 85 weeks for 50B tokens. Worse: 1B full training needs ~16 bytes/param (bf16 weights + fp32 master + Adam) ≈ 16 GB before activations, so a 16 GB T4 cannot even hold it without CPU offload. **Kaggle GPUs are for evals, ablations at ≤300M, and SFT of pre-quantized checkpoints — not pretraining.**
  - TPU v5e-8 (8×197 TF, 128 GB HBM total) at 40% MFU for 20 h/week ≈ **7.6B tokens/week** for 1B → scenario (d) in ~2–3 weeks, scenario (a) in ~7 weeks of 9-h resumable sessions. Requires a JAX/PyTorch-XLA BitLinear implementation.
- **Colab free**: "at most 12 hours", limits unpublished, GPU types vary; no compute units on free tier. https://research.google.com/colaboratory/faq.html . Paid plan prices not fetched [uncertain].
- **Lightning AI free**: "1 free active Studio (4 hour restarts)", 50 GB; monthly credits unconfirmed [uncertain]. **Modal**: $30/month free credits (Starter), $100 (Team) — https://modal.com/pricing . **HF ZeroGPU**: 5 min/day. **SageMaker Studio Lab**: closed to new users.
- **TPU Research Cloud**: "more than 1,000 Cloud TPU devices", "at no charge", expectation to publish/open-source; generations and grant length are not stated on the page (typically 30-day renewable grants [uncertain]); the google-research/trc GitHub repo was archived April 2026. https://sites.research.google/trc/about/ . For a lab that publishes receipts and specs, a TRC application is the single highest-leverage free-compute action.

## 6. The cost table

Assumptions: 6ND FLOPs; H100 at 40% MFU (bounds 35–45%); B200 at 35% MFU (30–40%, less mature small-model stack); ternary = 1.2× hours; prices from §4; no multiplier for restarts/ablations/evals (add 1.3–1.5× for a real program — HF spent ~80,000 H100-h on 70+ FineWeb ablation models, https://arxiv.org/html/2406.17557).

| Scenario | FLOPs | H100-h bf16 (35–45% MFU) | H100-h ternary | $ at Vast spot $0.89 (bf16 / tern) | $ at RunPod $2.69 | $ at median $3.63 | $ at AWS OD $6.88 | B200-h (35%) → $ at $3.75 / $6.25 (ternary) | Wall-clock, 8×H100, ternary |
|---|---|---|---|---|---|---|---|---|---|
| (a) 1B × 50B tok | 3.0e20 | 187–241 (211) | 253 | $187 / $225 | $566 / $680 | $764 / $917 | $1,449 / $1,738 | 106 → $476 / $794 | ~1.3 days |
| (b) 1.5B × 100B | 9.0e20 | 562–722 (632) | 758 | $562 / $675 | $1,699 / $2,039 | $2,293 / $2,752 | $4,346 / $5,215 | 317 → $1,429 / $2,381 | ~4 days |
| (c) 3B × 100B | 1.8e21 | 1,123–1,444 (1,263) | 1,516 | $1,124 / $1,349 | $3,399 / $4,078 | $4,586 / $5,503 | $8,692 / $10,431 | 635 → $2,857 / $4,762 | ~8 days |
| (d) CPT/distil 1.7B × 10B → ternary | 1.0e20 | 64–82 (72) | 86 | $64 / $76 | $193 / $231 | $260 / $312 | $493 / $591 | 36 → $162 / $270 | ~11 h |
| (d') same × 20B | 2.0e20 | 127–164 (143) | 172 | $127 / $153 | $385 / $462 | $520 / $624 | $985 / $1,182 | 72 → $324 / $540 | ~22 h |

Reading the table. Compute is not the obstacle for a 1–3B ternary model in late 2026: scenario (c) is ~$3.4–5.5k on a neo-cloud at list, ~$1.3k on spot, ~$10k on AWS on-demand. The budget risks are (1) the 1.3–1.5× program multiplier and the ablations needed to make a *new class* of model (calibration/abstention and tool-use behaviours need their own sweeps), (2) spot interruptions — Nebius reprices every 15 minutes and Vast spot is marketplace-driven, so checkpoint every ≤30 min and expect 10–20% wasted work, (3) B200 availability "remains limited" and median B200 price rose 17% YoY (getdeploying). For a 1–3B dense model a B200 is only worth it if its $/dense-TFLOP beats H100: at $3.75 vs H100 $1.73 (Vast OD) it does not; at $6.25 median vs $3.63 median it roughly ties. Memory: 3B at 16 B/param ≈ 48 GB fits one H100-80GB with activation checkpointing; 2–8 GPUs are a convenience for wall-clock, not a requirement.

Low-end GPUs (25% MFU): scenario (a) on T4 ≈ 5,100 GPU-h ($2,700 at $0.526 — slower and pricier than H100), on L4 ≈ 2,750 GPU-h ($2,200 at $0.805; $1,650 at spot), on A10G ≈ 2,670 GPU-h, on A100-40G ≈ 1,070 GPU-h ($2,100 at Lambda $1.99). L4/A10 only make sense for scenario (d) on spot (L4 ≈ 940–1,120 GPU-h → ~$560–$900 at g6 spot) when H100 spot is unavailable; otherwise rent H100s.

## 7. Continued-pretraining / distillation of an existing 1.7B into ternary — evidence and licences

- **BitNet Distillation** (Microsoft, 2025-10-15): fine-tunes Qwen3 0.6B/1.7B/4B to 1.58-bit via SubLN + MiniLM-style attention distillation + continual pre-training "10B tokens sampled from the FALCON corpus" ("virtually negligible" vs pretraining); trained on 8×AMD MI300X; downstream accuracy within ~0.1 pt of FP16 on MNLI/QNLI/SST-2 at 4B; "up to 10× memory savings and 2.65× faster inference on CPUs". https://arxiv.org/html/2510.13998
- **ParetoQ** (Meta, NeurIPS 2025): with a fixed 100B-token budget, "optimal performance is nearly achieved by dedicating ~90% to full-precision training and ~10% to QAT"; "3-bit and 4-bit reach near full precision accuracy after 10B tokens, while lower-bit quantization saturates around 30B tokens"; sub-2-bit representations "change drastically" (it is re-learning, not fine-tuning). Plan 20–30B tokens for ternary, not 10. https://arxiv.org/html/2502.02631
- **Ternary Bonsai** (Prism ML, 2026-04-16, Apache-2.0): Qwen3-1.7B/4B/8B converted to ternary g128; **1.7B scores 58.47 avg vs Qwen3-1.7B 66.57**, and the tool-calling benchmark falls hardest (BFCLv3 51.0 vs 71.8); 8B retains 75.5 vs 79.3. The whitepaper discloses no training tokens or compute (verified by reading the PDF). Bonsai 2 27B (2026-09-16) adds a blockwise Hadamard rotation folded into weights, "98.2% of FP16 intelligence retained". https://huggingface.co/prism-ml/Ternary-Bonsai-1.7B-gguf ; https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf
- Implication for ALICE-Next: a 1.7B ternary conversion costs only ~$200–$600 of compute (scenario d/d'), but the *tool-use* capability is exactly what degrades most at 1.7B; budget ≥20B tokens with a tool-calling-heavy CPT mix and accept that accuracy parity at ≤2B is not demonstrated by anyone yet (BitDistill's parity is on classification tasks).

Licensing/provenance consequences of re-opening distillation:

| Base checkpoint | Licence | Consequence |
|---|---|---|
| microsoft/bitnet-b1.58-2B-4T-bf16 (already ternary, ReLU², RoPE, subln; CIS-1-native) | MIT | Cleanest: CPT from the released master weights; 4T-token ternary pretraining is already paid for; vocab 128,256 (ALICE already prunes to 50,256). Weakest "own model" claim. |
| Qwen/Qwen3-1.7B-Base (1,720.6M) | Apache-2.0 | What Bonsai and BitDistill used; needs SwiGLU/GQA path in CIS-1; attribution only. |
| HuggingFaceTB/SmolLM2-1.7B, SmolLM3-3B (3,075M), allenai/OLMo-2-0425-1B (4T tokens) | Apache-2.0 | Clean; OLMo-2 has fully open data (strongest provenance story for a distilled model). |
| meta-llama/Llama-3.2-1B (1,235.8M) | Llama 3.2 Community License (custom, commercial) | Derivatives carry Llama naming/attribution and use-policy terms; itself distilled from 3.1 8B/70B. |
| google/gemma-3-1b-pt (999.9M) | Gemma licence (custom) | Use restrictions flow down. |
| tiiuae/Falcon-E-1B/3B (ships bf16, BitNet, and "prequantized" fine-tuning revisions) | Falcon-LLM licence ("other") | Custom terms; otherwise the most direct ternary starting point after BitNet. |

Sovereignty: CIS-1 receipts attest *computation*, not *provenance*. A distilled ALICE-Next keeps bit-exact replayable receipts but inherits the teacher's training-data provenance and licence; the 2026-08-29 "from-scratch, no external teacher" proof is then a separate, smaller model (e.g., a 1B × 50B from-scratch run at ~$0.6–1k), not the production model. Document this split explicitly if distillation is adopted.

## 8. Data-prep cost and where to run it

- Use corpora that are already deduplicated and filtered: FineWeb-Edu 1.3T tokens (ODC-By; MinHash 5-grams, 112 hashes in 14 buckets × 8, ≥75% similarity), DCLM-baseline 4T tokens (CC-BY-4.0), SmolLM-corpus (ODC-By), Nemotron-CC-v2 (gated, "other"). https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu ; https://huggingface.co/datasets/mlfoundations/dclm-baseline-1.0 ; https://arxiv.org/html/2406.17557
- Tokenization: HF tokenizers "takes less than 20 seconds to tokenize a GB of text on a server's CPU" → 100B tokens ≈ 400 GB text ≈ 2–3 core-hours of pure tokenization; real pipeline with I/O ≈ 1–3 h on a 64-vCPU c7a.16xlarge (**$1–10** on spot). Output: 200 GB as uint16 (fits the 50,256 vocab). https://huggingface.co/docs/tokenizers/index
- Cross-source fuzzy dedup only if mixing sources: NVIDIA reports 4.5 TB RedPajama fuzzy dedup in 3 h on 4 DGX A100 (96 A100-h ≈ **$135–240**) vs 37 h on 20 × 48-core CPU nodes (35,520 core-h ≈ **$670 spot / $1,820 OD** on c7a). For a 400 GB subset divide by ~10. https://developer.nvidia.com/blog/curating-trillion-token-datasets-introducing-nemo-data-curator/
- Quality classifier (only for your own crawl): FineWeb-Edu's classifier cost "6,000 H100 GPU hours" for 15T tokens → ~40 H100-h (~$150) per 100B tokens.
- Decontamination (13-gram overlap against the tool-use/calibration eval sets, incl. the receipt-harness prompts): CPU, <1 h, negligible — but mandatory under Rule B before any number goes in the ledger.
- Where: any 64-vCPU spot box with 1–2 TB NVMe (AWS c7a spot above; Hetzner AX102 = Ryzen 9 7950X3D, 128 GB ECC, 2×1.92 TB NVMe — monthly price not readable [uncertain]). Not penguin (/tmp is RAM-backed, 6.4 GB RAM). Store tokenized shards in object storage (~$4–20/month for 200 GB) so training nodes stream them; keep the manifest hash in the receipt chain.

## 9. Bottom line for the ALICE-Next plan

1. Rent, don't scavenge: scenario (c) 3B × 100B ternary is ~1,500 H100-h ≈ **$1.3k (spot) – $5.5k (neo-cloud list)**, ~8 days on one 8×H100 node; (b) is ~half; (a) is a weekend and <$1k. Add 1.3–1.5× for restarts and ablations; add the teacher's forward cost if distilling online.
2. Kaggle's ~30 GPU-h/week cannot pretrain a 1B model (memory and ~0.6B tok/week); its TPU v5e-8 can carry scenario (d) if a JAX BitLinear exists; spend Kaggle on evals/SFT and apply to TRC.
3. Ternary adds ~20% training time (Falcon-E) and zero training-memory savings; plan ≥20–30B tokens for any sub-2-bit conversion (ParetoQ), because tool-calling is the first casualty at 1.7B (Bonsai: BFCLv3 71.8 → 51.0).
4. The cheapest CIS-1-native path is CPT from microsoft/bitnet-b1.58-2B-4T-bf16 (MIT) — ~$300–600 for 10–20B tokens — at the cost of the "own model" claim; the cleanest Apache-2.0 distillation base is Qwen3-1.7B-Base or OLMo-2-1B (open data).
5. Data prep for 100B tokens is <$100 if you start from FineWeb-Edu/DCLM; the only real data cost is decontamination discipline.

## Key claims (as returned by the research agent, with sources)
- Falcon-E reports the BitNet pre-training overhead as "around ~20% between non-Bitnet pre-training against Bitnet pre-training"; models were trained on ~1.5T tokens with a WSD schedule.  
  <https://huggingface.co/blog/tiiuae/falcon-edge>
- SmolLM3-3B was pretrained on 11.2T tokens on 384 H100 GPUs for 24 days (nanotron, seq 4096, global batch 2.36M tokens), i.e. ~14,070 tokens/s/GPU all-in.  
  <https://huggingface.co/blog/smollm3>
- TinyLlama-1.1B trained at 24k tokens/s per A100-40G with 56% MFU, 3T tokens in 90 days on 16 GPUs.  
  <https://github.com/jzhang38/TinyLlama>
- Llama 3.2 1B and 3B consumed 370k and 460k H100-80GB GPU-hours on up to 9T tokens, with Llama 3.1 8B/70B logits used as token-level targets during pretraining.  
  <https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/MODEL_CARD.md>
- H100 median on-demand price is $3.63/GPU-h (90-day trend flat), cheapest verified in-stock $1.30, Vast.ai spot $0.89, as of 2026-10-06.  
  <https://getdeploying.com/gpus/nvidia-h100>
- B200 median on-demand price is $6.25/GPU-h, up 17% over 12 months and 3% over 90 days; cheapest in-stock $3.75; spot $3.20–5.94, as of 2026-10-06.  
  <https://getdeploying.com/gpus/nvidia-b200>
- AWS p5.48xlarge (8×H100) on-demand is $55.040/h ($6.88/GPU) and spot $28.337/h in us-east-1; p6-b200.48xlarge (8×B200) is $113.933/h on-demand, $59.411 spot.  
  <https://instances.vantage.sh/aws/ec2/p5.48xlarge>
- BitNet Distillation converts Qwen3 0.6B/1.7B/4B to 1.58-bit using a continual pre-training stage of 10B tokens from the FALCON corpus, trained on 8×AMD MI300X, with up to 10× memory savings and 2.65× faster CPU inference.  
  <https://arxiv.org/html/2510.13998>
- ParetoQ: with a 100B-token budget ~10% to QAT is near-optimal; 3/4-bit reach near-FP accuracy after 10B QAT tokens while sub-2-bit (binary/ternary/2-bit) saturates around 30B tokens.  
  <https://arxiv.org/html/2502.02631>
- Ternary Bonsai 1.7B (Apache-2.0, from Qwen3-1.7B, April 2026) scores 58.47 avg vs Qwen3-1.7B 66.57, with BFCLv3 51.0 vs 71.8; the whitepaper discloses no training tokens or compute.  
  <https://huggingface.co/prism-ml/Ternary-Bonsai-1.7B-gguf>
- FineWeb-Edu classifier inference over 15T tokens cost 6,000 H100 GPU-hours; FineWeb ablations used ~80,000 H100 GPU-hours over 70+ models; MinHash dedup used 5-grams, 112 hashes in 14 buckets of 8.  
  <https://arxiv.org/html/2406.17557>
- NeMo Curator fuzzy dedup of the 4.5 TB RedPajama dataset took 3 h on 4 DGX A100 nodes vs 37 h on 20 CPU nodes (48 cores, 188 GB each).  
  <https://developer.nvidia.com/blog/curating-trillion-token-datasets-introducing-nemo-data-curator/>

## Gaps and unverified items (recorded, not papered over)
- WebSearch budget for this turn was exhausted after the first 8 queries (shared 200-call limit); everything after that came from direct fetches of known URLs and the Hugging Face Hub connector. A follow-up turn could search for: measured T4/L4/A10 training throughput for 1–3B models, Kaggle's official TPU v5e-8 weekly quota, Colab/Lightning paid-tier prices, and Hetzner dedicated-server prices.
- Google Cloud TPU pricing (v5e/v6e/TPU7x on-demand, spot, committed) and GCP GPU pricing pages are JS-rendered and returned no text; gcloud is not authenticated here, so the Billing Catalog API could not be queried. TPU $/chip-hour is therefore absent from the cost table.
- Kaggle docs pages (notebooks, TPU) are JS-rendered; the 30 GPU-h/week figure is the program fact plus a secondary source (gpuperhour.com, 2026-09-21); the TPU weekly quota and the exact TPU type (v5e-8) are secondary/[uncertain].
- SmolLM2-1.7B training duration (and hence its tokens/s/GPU) is not disclosed in the paper or model card; only '256 H100s, 11T tokens'.
- BitNet b1.58 2B4T's hardware, GPU count, duration and training throughput are not disclosed in the technical report or model card.
- Prism ML's Ternary Bonsai and Bonsai 2 whitepapers (read as PDFs) disclose no training token counts, GPU hours, or dollar costs for the Qwen3→ternary conversion.
- No published measurement of BitNet-style fake-quant training overhead other than Falcon-E's '~20%'; the 1.2× factor in the cost table rests on that single data point.
- Vast.ai's own pricing pages returned no live offers; Vast prices are taken from getdeploying.com's 2026-10-06 snapshot.
- Lightning AI pricing/credits pages failed to load; Colab paid-plan prices were not retrievable (sign-in page). Both are reported from a secondary source and marked [uncertain].
- A100 dense bf16 peak (312 TFLOPS) and A10G (AWS variant) peak were not re-fetched from NVIDIA/AWS pages.
