# LAB-03 — CIS-1 ternary matvec on AVX-512 VNNI / AVX-VNNI: bit-identical, and where the time really goes

Date: 2026-10-06. Machine: see FINGERPRINT.txt (Intel Xeon family 6 model 207, 4 vCPU KVM container, **env=vm**). Rule A: absolute figures from this VM are NOT a ceiling and are not performance claims; the admissible outputs are (1) bit-identity and (2) same-process interleaved ratios. Code: `aegis-core/src/cis_vnni.rs`, `aegis-core/tests/cis_vnni_equivalence.rs`, `aegis-core/benches/vnni_vs_avx2.rs` (branch `lab/vnni-cis1`).

## What was built
`cis_vnni::ternary_matvec_i8_vnni` — the first CIS-1 kernel for VNNI-class x86 (the program's fleet has none: i5-5200U Broadwell, N4020 Gemini Lake, i5-10210U Comet Lake all lack VNNI; ledger A5 "speed rejected — no VNNI on this silicon").
- Same 2-bit container, same traffic as the incumbent `cis_avx2` v3b. Nibble decode by `vpshufb` into the offset weight u = w+1 in {0,1,2}; `vpdpbusd` (u8 x i8 -> i32, 4 products per lane, non-saturating) accumulates exactly; dot = acc - sum(a) (offset identity). zmm path (64 packed bytes = 256 weights per block) when AVX-512F/BW/VNNI are present and XCR0 has the ZMM state; ymm path (`_mm256_dpbusd_avx_epi32`, AVX-VNNI, Alder Lake+/Zen 5) otherwise; falls back to the AVX2 kernel, then the scalar reference. CPUID/XGETBV probe only (no_std).
- Spec §5.1 rejection surface enforced before any dispatch; `-128` activation hazard and `set_force_scalar` race toggle honoured exactly as `cis_avx2`.
- Wired into `CisEngine::tmv_dispatch` for x86_64 (non-UEFI builds). UEFI builds still take the scalar reference for CIS (pre-existing `not(target_os = "uefi")` cfg on `cis_avx2`).

## Bit-identity (the result that matters)
`cargo test --release --test cis_vnni_equivalence`: 4/4 PASS — 13 shapes incl. all four BitNet-2B-4T projections, M7, Falcon-E, odd tails; the `-128` fallback; VNNI forced off; the rejection surface. `tmv_dispatch_matches_scalar_reference`: PASS. `cis_avx2_equivalence`: 18/18 PASS (unchanged).
End to end: `cis_decode` through the new dispatch on the 2B artifacts reproduces `CIS_DECODE digest=cab11400d737ac4a` (LAB-02) — the VNNI path cannot change a digest, only how fast it appears.

## Kernel A/B (same process, interleaved, order rotated per round, medians)
Run 1 (2-arm, weights resident, 11x20 calls) — `vnni_vs_avx2_run1.log`:
| shape | avx2 us | vnni us | GMAC/s avx2 -> vnni | ratio |
|---|---|---|---|---|
| q/o 2560x2560 | 121.6 | 92.9 | 53.9 -> 70.5 | 1.31 |
| k/v 640x2560 | 30.5 | 22.4 | 53.7 -> 73.1 | 1.36 |
| gate/up 6912x2560 | 332.9 | 256.1 | 53.2 -> 69.1 | 1.30 |
| down 2560x6912 | 332.2 | 253.9 | 53.3 -> 69.7 | 1.31 |

Run 2 (3-arm: avx2 / vnni 1-row / vnni 4-row-blocked; weights resident) — `vnni_vs_avx2_resident_run2.log`: down 2560x6912: avx2 62.9 GMAC/s, vnni-1row 78.5 (1.25x), vnni-4row 68.4 (1.09x). The 4-row blocking (16 accumulator chains, meant to hide vpdpbusd latency) is SLOWER than 1-row — consistent with the compiler spilling the accumulator array; 1-row is now the default, 4-row kept behind `set_force_r4` for iron A/B. Negative finding, recorded.

Run 1, DRAM-streaming mode (256 MB of distinct weight matrices rotated so every call streams from DRAM as a decode step does; 9x12 calls) — `vnni_vs_avx2_stream256_run1.log`:
| shape | avx2 GB/s(weights) | vnni GB/s | ratio |
|---|---|---|---|
| q/o 2560x2560 | 5.39 | 6.18 | 1.15 |
| k/v 640x2560 | 5.57 | 6.16 | 1.11 |
| gate/up 6912x2560 | 5.29 | 6.07 | 1.15 |
| down 2560x6912 | 5.59 | 6.28 | 1.12 |

## Reading
1. Cache-resident, the VNNI kernel is 1.25-1.36x the AVX2 incumbent at the kernel (70-78 vs 53-63 GMAC/s on this VM). Bit-identical throughout.
2. Streaming from DRAM — the decode reality for a 521 MB weight set — BOTH kernels collapse to ~5.3-6.3 GB/s of packed weights (21-25 GMAC/s) and the gain shrinks to 1.11-1.15x. **The CIS-1 integer decode on this box is single-core DRAM-bandwidth-bound**, not instruction-bound. A decode step reads ~521 MB ternary + 257 MB BF16 LM head (pruned 50k vocab) ≈ 778 MB; at ~6 GB/s that is ≈ 7-8 tok/s single-thread no matter how clever the kernel.
3. Therefore the levers that matter for CIS-1 decode speed are, in order: (a) more cores streaming in parallel (rows are independent, so a row-split across cores is bit-identical BY CONSTRUCTION — no reduction-order question even arises), including on bare metal via firmware MP services; (b) fewer bytes per token (LM head: 257 MB of the 778 is the BF16 tied head — an int8/Q6-class head or fused argmax candidate set is the next 30%; BITCOS-style 1.578 bpw packing is -21% on the ternary part); (c) instruction-level work last. This matches the program's own 2026-07-30 verdict on T-MAC (A7: memory traffic beats kernel throughput) from the other side.
4. For the Linux twin and fleet boxes with VNNI (any Alder Lake+/Zen 5+/Sapphire Rapids+), the kernel is a free, bit-identical upgrade; for the three legacy fleet boxes it is inert (falls through to AVX2/scalar).

## Caveats
- VM: 4 vCPUs, shared host, unknown memory configuration; the ~6 GB/s single-core streaming figure is this container's, not any product's. Repeat on iron (penguin/box1 have no VNNI; a VNNI-capable box is needed to measure the kernel ratio there; the bandwidth-bound conclusion can be re-tested on any box with `vnni_vs_avx2 9 12 256`).
- The equal-GB/s result across all three arms in streaming mode is itself the evidence for the bandwidth bound (three different instruction mixes, one throughput).
