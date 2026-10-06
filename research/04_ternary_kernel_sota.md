# CPU Inference for Ternary (BitNet b1.58) LLMs - State of the Art, Oct 2026
Research agent brief. Scope: decode-side CPU inference for 1.58-bit models, roofline for BitNet-b1.58-2B-4T, gap list for a bare-metal AVX2 engine. "Uncertain" marks unconfirmed claims.

## 1. Kernels
bitnet.cpp (Microsoft; arXiv 2410.16144, 2502.11880): I2_S (x86 AVX2/AVX-512, ARM): 2 bits/weight, unpack to int8 in-register, int8 MAD; activations int8 per-token absmax (W2A8); K multiple of 128. TL1 (ARM): 2 weights -> 4-bit index into 9-entry LUT of activation sums; int16 LUT+accumulate. TL2 (x86): 3 weights -> 4-bit index + sign ("mirror consolidation"), 1.67 bits/weight; pshufb + add. Reported decode (unlimited threads): i7-13700H 700M 119.1, 3.8B 30.5, 7B 18.8, 70B 2.44, 100B 1.70 tok/s (llama.cpp 30.7/5.85/3.30); M2 Ultra 194.4/84.8/52.4/8.67/6.58. BitNet-2B-4T: 29 ms/token = 34.5 tok/s on i7-13800H 8 threads (tech report 2504.12285). Intel scaling plateaus ~4 threads (bandwidth). Jan 15 2026 "CPU Inference Optimization": activation-parallel W2A8 dot kernel, Q6_K LM head; 1.15-2.1x claimed. i2_s GGUF 1.19 GB = 521 MB 2-bit weights + 657 MB F16 tied embeddings.
T-MAC (EuroSys'25, arXiv 2407.00088): bit-serial LUT mpGEMM, g=4, 16-entry int8 tables via TBL/PSHUFB; BitNet-3B 30 tok/s single core M2 Ultra, 11 tok/s RPi 5; superseded by TL2 for ternary.
llama.cpp TQ1_0 (1.6875 bpw) / TQ2_0 (2.0625 bpw), PR #8151; TQ2_0 141.8 GB/s F32-equiv on Core m3-8100Y.
2026 x86: BITCOS (Intel, arXiv 2609.16338): presence bitmap + sign -> 2 - z bits/weight; BitNet-2B-4T zeros 42.19% -> 1.578 bpw; AVX-512 pdep decode; gains 1.10-1.18x Xeon 8592+, 0x on Lunar Lake (instruction-bound). FairyFuse (2604.20913): 7B complex ternary FP32 activations, 32.4 tok/s @48 threads Xeon 8558P at only 4.6% of 200 GB/s - compute-bound. Litespark (Mindbeam, 2605.06485): ternary stored as int8 to feed VPDPBUSD/SDOT; BitNet-2B-4T 41.2 tok/s (AVX-512 VNNI), 40.0 (Core Ultra 9 AVX-VNNI), 39.9 (M5 Max; 10.98 single-thread). T-SAR (DATE 2026) hardware; signed-digit KV (2608.03229) ASIC only; BitNet a4.8 / v2 no public CPU kernels (uncertain); ParetoQ, TernaryLLM no kernels.

| Kernel | Weight format | Eff. bpw | Activations | ISA | Measured decode | CPU |
|---|---|---|---|---|---|---|
| bitnet.cpp I2_S | 2-bit packed, unpack->int8 MAD | 2.0 | int8 | AVX2/AVX-512, NEON | 2B-4T 34.5 tok/s (8 thr) | i7-13800H |
| bitnet.cpp TL1 | 2w -> 4-bit idx LUT | 2.0 | int8 | NEON TBL | 3.8B 84.8 | M2 Ultra |
| bitnet.cpp TL2 | 3w -> 4-bit idx + sign | 1.67 | int8 | AVX2 pshufb | 100B 1.65 | i7-13700H |
| T-MAC | bit-plane g=4 LUT | 2.0 | int8 | NEON/AVX2 | 3B 30 tok/s 1 core | M2 Ultra |
| llama.cpp TQ1_0/TQ2_0 | base-3 / 2-bit | 1.6875/2.0625 | Q8_K | AVX2, NEON | 70/142 GB/s F32-eq | Core m3 |
| BITCOS | bitmap + sign | 1.578 (2B-4T) | int8 | AVX-512 pdep | +1.10-1.18x | Xeon 8592+ |
| Litespark | int8 storage | 8.0 | int8 | VNNI/SDOT | 2B-4T 41.2 multi, 11.0 1thr M5 | Zen4-class / M5 Max |
| FairyFuse | 2-bit (complex) | 2.0 | FP32 | AVX-512 | 7B 32.4 @48 thr | Xeon 8558P |
Takeaway: every published 2026 x86 kernel targets AVX-512/VNNI; no AVX2 single-core roofline study exists.

## 2. Roofline: BitNet-2B-4T decode, batch 1
Params: attention/layer 16,384,000; FFN/layer 53,084,160; per layer 69,468,160; x30 = 2,084,044,800 ternary; embedding (tied) 128,256 x 2560 = 328,335,360; total 2.412B.
Bytes/token: ternary 2-bit 521.0 MB (TQ1_0 439.6; BITCOS 411.1; log2(3) floor 412.8). LM head: FP32 full 1313 MB; BF16 657 MB; int8 328; Q6_K ~269; BF16 pruned 50,256 = 257 MB; 32k 164 MB. KV f16: 76.8 KB per context token (L=512 -> 39 MB; 2048 -> 157 MB; 4096 -> 315 MB).
Per-token totals (L~512): bitnet.cpp default 1,217 MB; Q6_K head 829 MB; 2-bit + BF16 50k head (ALICE) 817 MB; aggressive ~513 MB.
Bandwidth ceilings: DDR4-3200 dual 51.2 GB/s -> 42/62/63/100 tok/s; DDR5-5600 dual 89.6 GB/s -> 74/108/110/175. Single core typically 12-15 GB/s (Skylake/Comet Lake class, uncertain) to ~30 GB/s (Raptor Lake): at 14 GB/s 11.5/17/17/27 tok/s; at 30 GB/s 25/36/37/58. Compute ceiling AVX2 LUT one core ~30-60 tok/s on 2.084B weights, so a single AVX2 core on DDR4 is bandwidth-bound if the kernel is good.
Achieved: bitnet.cpp 2B-4T i7-13800H 8 thr: 34.5 tok/s x 1.217 GB = 42 GB/s effective (~40% of peak). M2 Ultra 3.8B 84.8 tok/s ~85 GB/s of 800 (~10%, compute-bound). alice-aegis 2.80 tok/s x 0.817 GB = 2.3 GB/s: 15-20% of one Comet Lake core's bandwidth, ~5% of dual-channel DDR4-2666 - a 4-6x gap to single-core roofline, >10x to socket roofline.
LM head in the field: bitnet.cpp F16 head (56% of bytes), Q6_K since Jan 2026; llama.cpp Q6_K/Q4_K output; Bonsai-2 27B ternary head end-to-end; VocabTrim for drafts only. No published system fuses argmax into the head matvec; nobody reports perplexity under a pruned-vocab target head.

## 3. Beyond kernels
Speculative decoding on BitNet: none published; no ternary draft sharing Llama-3 tokenizer; prompt-lookup/n-gram drafting unexplored and trivially OS-free. KV quantization: no CPU int8/int4 KV results for any ternary model. Early exit / layer skipping: nothing on BitNet. MoE ternary: DeepGrove Maple-Preview 20B-A1B (MIT, 5.31 GB, 218 tok/s Mac mini M4 via MLX).

## 4. Determinism and verifiability
CPU nondeterminism sources: thread-count-dependent reduction partitioning; FMA contraction; ISA dispatch trees; libm differences; MXCSR FTZ/DAZ; batch-size tiling. Thinking Machines (Sep 2025): batch invariance is the dominant cause; ~20% matmul cost. Bit-exact work: ReproFuse (2609.25624), TBIK (2511.17826) academic; NVIDIA NIM deterministic mode same-config only; llama.cpp no cross-ISA guarantee. Verifiable/attested: TOPLOC (ICML'25, 2501.16007) LSH, deployed by Prime Intellect, approximate by design; zkML academic; TEE attestation deployed (Apple PCC, Tinfoil, Edgeless Continuum; Chrapek 2509.18886 <10% overhead TDX/SGX with AMX). IETF Attested Inference Receipt (AIR) draft-tsyrulnikov-rats-attested-inference-receipt-02 (Jul 2026): COSE_Sign1 receipts binding model ID, I/O hashes and attestation evidence - profiles ONLY AWS Nitro and Intel TDX. Hash-chained inference logs only as RATS compositions (2608.00801). No measured-boot-attested LLM runtime where the whole TCB is one EFI binary.

## 5. Energy
BitNet-2B-4T 0.028 J/token is an arithmetic-energy estimate (Horowitz model), not measured. 1-bit AI Infra measured: i7-13700H 700M 0.384 J/tok, 7B 2.017; M2 Ultra 7B 1.068, 70B 8.42. Litespark: 2B-4T 0.79 J/tok M5 Max; 7.48 J/tok Threadripper PRO 5965WX (vs 95 PyTorch). PrismML Bonsai 8B 0.378 J/tok M4 Pro. alice-aegis 3.99-5.06 J/tok i5-10210U. No study reports no-OS J/token.

## 6. Ternary models since Apr 2025
Falcon-E 1B/3B (TII, May 2025, Falcon-LLM license); BitVLA (Jun 2025, ternary VLA); BitNet Distillation (Oct 2025, 2510.13998); Fairy2i-W2 (Dec 2025); Maple-Preview 20B-A1B (DeepGrove 2026, MIT); Ternary Bonsai 1.7B/4B/8B (PrismML Apr 2026, Apache-2.0); Bonsai Image 4B; Ternary Bonsai 2 27B (first large ternary VLM, Apache-2.0, needs llama.cpp fork); CAT-Q (Intel China ICML'26). No dedicated ternary code model. Microsoft released no larger BitNet LLM after 2B-4T (uncertain).

## 7. Gaps nobody has filled - bare-metal AVX2 engine
1. Single-core roofline attainment on AVX2 (target >=50% of measured single-core STREAM, 8-15 tok/s Comet Lake, reported with the STREAM number on the same machine).
2. Multi-core without an OS (UEFI MP Services, static row partition; test scaling to socket bandwidth ceiling with near-zero jitter; p99 token latency bare metal vs Linux same binary).
3. Fused LM head: pruned vocab + int8/Q6_K rows + streaming argmax/top-k; two-stage head (int8 candidates, exact BF16 rescoring of top-256) unexplored.
4. Exact-replay verifiability: integer-exact semantics make output recomputable bit-for-bit by any third party on any CPU; commitments can be exact hashes, no TEE. Needs published digests per (model, prompt) and independent reproduction on a different ISA/vendor.
5. Measured-boot-attested inference without a TEE: whole TCB = one EFI binary + MODEL.SAF; TPM 2.0 PCR extension of both plus an AIR-style COSE receipt would be a new attestation profile.
6. BITCOS-on-AVX2 via LUT (1.578 bpw, -21% weight bytes).
7. int8/4-bit KV with fused attention on CPU for a ternary model.
8. Speculation on ternary (prompt-lookup/n-gram, Medusa/EAGLE head).
9. No-OS energy per token (rdmsr RAPL + external meter).
10. Prefill on AVX2 (blocked int8 GEMM with vpmaddubsw, chunked prefill).
11. Honest AVX2 LUT-vs-MAD crossover study.
Prior bare-metal art to cite: "Operating Organism" (UEFI Mamba-2.8B/LLaMA2, FP), cllm, Llama2.c L2E unikernel. None ternary, none roofline, none determinism or attestation.

## 12 primary sources
1. https://arxiv.org/abs/2410.16144  2. https://arxiv.org/abs/2502.11880  3. https://arxiv.org/abs/2407.00088  4. https://arxiv.org/abs/2504.12285  5. https://github.com/microsoft/BitNet/blob/main/src/README.md  6. https://github.com/ggml-org/llama.cpp/pull/8151  7. https://arxiv.org/abs/2609.16338  8. https://arxiv.org/abs/2604.20913  9. https://arxiv.org/abs/2605.06485  10. https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/  11. https://arxiv.org/abs/2501.16007 ; https://datatracker.ietf.org/doc/html/draft-tsyrulnikov-rats-attested-inference-receipt-02  12. https://arxiv.org/abs/2509.18886
Supporting: https://arxiv.org/abs/2608.03229, https://arxiv.org/abs/2411.04965, https://arxiv.org/abs/2504.18415, https://arxiv.org/abs/2502.02631, https://arxiv.org/abs/2606.26650, https://prismml.com/news/ternary-bonsai, https://huggingface.co/deepgrove/maple-preview, https://huggingface.co/blog/tiiuae/falcon-edge, https://chipsandcheese.com/p/previewing-meteor-lake-at-ces, https://arxiv.org/abs/2512.03024
