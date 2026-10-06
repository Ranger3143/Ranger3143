# LAB-02 — Independent reproduction of the BitNet-2B CIS-1 decode digest on a new microarchitecture (Sapphire Rapids class Xeon VM)

Date: 2026-10-06. Operator: Claude (cloud session) for Aefinity AI Inc. Identity/correctness lab only (Rule A: no timing in this file is a result).

## Claim under test
Ledger A36/A39/A48 pin `CIS_DECODE digest=cab11400d737ac4a prompt_toks=4 gen_toks=64 mode=fullint` for BitNet b1.58-2B-4T under CIS-1 FullInt (prompt "Once upon a time", 64 greedy tokens), reproduced so far on: i5-10210U (crosvm), GitHub aarch64 runner, Celeron N4020 (scalar, no AVX2), Dell i5-5200U (bare metal, kit). Every prior reproduction used the SAME artifact bytes (MODEL.SAF sha256 facb3597...). This lab re-derives the artifacts from Microsoft's public packed checkpoint with a different tool chain and checks the digest on a fourth x86 microarchitecture (Intel family 6 model 207 = Sapphire Rapids/Emerald Rapids class, AVX-512 + VNNI + AMX), inside a KVM cloud container.

## Machine (fingerprint.sh)
```
cpu_model: Intel(R) Xeon(R) Processor @ 2.10GHz   (family 6, model 207, stepping 2)
logical_cpus: 4   hypervisor_flag: 1 (env=vm)
isa_flags(relevant): amx_int8,amx_tile,avx,avx2,avx512bw,avx512f,avx_vnni,fma  (+avx512_vnni per /proc/cpuinfo)
os: Linux 6.18.44-fc-v70 x86_64
rustc 1.97.0 (2d8144b78 2026-07-07)
alice-aegis HEAD 3e3f465ee247346856907aa625d1c7f9dd352cef (public main, unmodified aegis-core for this lab)
cis_decode binary sha256 fed52f0f91bde1f069c54a92d362a6fc841d88d1a0be2d230772dd8e8b60c15d
cis_selftest binary sha256 4f7f96e61255f14218cb0e8d52f9de714d11eaf4d106b75f161b603dd6aa21f0
```

## Inputs
Source checkpoint: `microsoft/bitnet-b1.58-2B-4T` (packed uint8, HF commit a1f2f1c765812aa8af3f6eda4a313707064bba15), `model.safetensors` sha256 `8143ae115ed6babe5e5ada8fb8c5b769d8f417802b2db042ad98b4f7ed73975b` (1,178,623,988 B), downloaded 2026-10-06 over HTTPS.

Repack: `aegis-forge/repack_ternary.py <ckpt> <out> --source-packing hf1bitllm --llama3-prune --max-seq 2048`.

| artifact | bytes | sha256 | vs canonical (ledger) |
|---|---|---|---|
| EMBED.BIN | 257,310,720 | e32b99a25e345c65054f36dedf40329a89513cdf1a8195db64fc440fd364e077 | IDENTICAL (A35 "embed e32b99a2...") |
| VOCAB.BIN | 1,759,936 | 5bde1b0355ef99c6875190ebfff081d985ca48977ae9269e3477f5cc2d97d9ae | IDENTICAL (A43) |
| MODEL.SAF (tool as shipped, `reciprocal` scale) | 521,953,186 | 9d1fa7693043b525e38d7f630f5ff5dcb17feff283e64b2ec7f733988abaea4d | different bytes AND different values (see finding 1) |
| MODEL.SAF (scale = source value, exact) | 521,953,186 | 1101e472e41a012e4b1efdc124511461307f4e0e1b540a8e45c24d3d33e0c9eb | different bytes (BF16 norms, metadata), SAME values |

## Results
1. `cis_selftest` → `CIS_SELFTEST digest=76985613c965f643 ALL_PASS=true` (matches spec §8 Tier-2 pin; fifth x86 microarchitecture + first AVX-512-class part).
2. `cis_decode` on the as-shipped repack → `CIS_DECODE digest=ac3772033c18a314`, text ", the and the and the and ..." — WRONG. Root cause: `scalar_f32_scale` writes 1/weight_scale (the transformers `BitLinear` DIVIDE convention used by Falcon-E / HF1BitLLM), but Microsoft's offline-quantized checkpoint is served by transformers' `AutoBitLinear`, which MULTIPLIES by `weight_scale` (integrations/bitnet.py; stored values 1.2-2.3 = 1/mean|w|). The canonical artifact (correct_transmute.py) copies the scalar. Every shape/ternary check passed; only the decode exposed it — the same silent failure class the tool's own docstring records for Falcon-E, in the opposite direction.
3. With the scale copied as 1/(1/s) (double reciprocal) → coherent text ("...there was a young girl named Lily...") but `digest=803e07941964ed37`: the f32 round trip perturbs 210 scales by up to 2.4e-7 and that is enough to move greedy tokens at near-ties. Exactness matters down to the last mantissa bit.
4. With the scale copied EXACTLY (BF16 → F32) → **`CIS_DECODE digest=cab11400d737ac4a prompt_toks=4 gen_toks=64 mode=fullint`**, text ", in a small town called Greenfield, there lived a young girl named Lily. Lily was a curious and intelligent girl who loved to explore and learn new things..." — IDENTICAL to the pinned 2B digest and to the token ids in `tests/golden/witness_v1_bitnet2b_once64.receipt`.
5. The patched tool (`--scale-convention auto`, sniffing `quantization_config.quant_method == "bitnet"`) reproduces the same MODEL.SAF sha256 1101e472... and the same digest end to end (see `bitnet2b_fixed`).

## What this shows
- The CIS-1 2B decode digest is a property of the MODEL VALUES, not of one artifact file: a MODEL.SAF with different bytes (BF16 norms instead of F32, different header/metadata) and a different sha256 reproduces it bit-for-bit. This is the first reproduction from independently re-derived artifacts, on a fourth x86 microarchitecture, and the first on AVX-512/VNNI-class silicon (which this lab then exploits; see LAB-03).
- The reproduction also catches a real tool bug (finding 2) and demonstrates the sensitivity argument for exact-replay receipts (finding 3): a 2.4e-7 perturbation of a per-tensor scale changes the output tokens — a hash-of-tokens or hash-of-logits receipt is sensitive to it, while any tolerance-based check would have passed it.

## Caveats
- Cloud VM; no timing claims anywhere in this lab.
- MODEL.SAF bytes differ from the canonical facb3597... so a canonical RECEIPT.TXT (which binds the artifact sha256) will fail its artifact-hash step against these files by design; a receipt minted against these artifacts verifies on any conforming host.

## Addendum 2026-10-06 (evening) — raw decode logs for the scale legs
Results 2 and 4 above now have raw logs in this repo (`labs/logs/cis_decode_2b_bitnet2b_scaleleg.log`: as-shipped reciprocal repack, digest `ac3772033c18a314`; `labs/logs/cis_decode_2b_bitnet2b_fixed_scaleleg.log`: exact scale, digest `cab11400d737ac4a`), each prefixed with the artifact SHA-256s and the command. The Result 3 artifact (double reciprocal) was regenerated from the exact-scale artifact by round-tripping all 210 `*.weight_scale` scalars through f32 reciprocals (`labs/logs/scaleleg/make_dblrecip.py`, header and every other byte unchanged; new MODEL.SAF sha256 `40f8c585e50a969f2993da3ba8362b1868f48c3e01b79a4f9e1f43119dfa63bf`). Measured (`labs/logs/scaleleg/scale_stats.json`, `scales.tsv`): **31 of 210 scales change, each by exactly 1 ulp**; max absolute change 2.384e-7 (layer 6 v_proj), max relative 8.03e-8 (layer 2 k_proj); 179 round-trip exactly. Decode (`labs/logs/scaleleg/cis_decode_2b_dblrecip_scaleleg.log`): **digest `803e07941964ed37`**, reproducing Result 3; the same-session control (`cis_decode_2b_fixed_control_scaleleg.log`) gives `cab11400d737ac4a`. The two token streams agree for the first 5 generated tokens and diverge at generated index 5 (control " called", perturbed ","), both texts coherent. So one ulp in 31 per-tensor scales moves a greedy token at a near-tie, and only the exact digest sees it. Note: the decoder binary used here (sha256 `bef74a01…`) was built after commit a7991b8 and differs from the binary in `labs/FINGERPRINT.txt`; the control digest is unchanged, and both legs used the same binary.
