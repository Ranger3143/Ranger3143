# Synthesis — where Aefinity AI can set a standard (2026-10-06)

Four research briefs (01-04), the full state of the alice-aegis / cis2-spec / claudius-maximus programs, and the labs run in this session (LAB-02..05) converge on one conclusion.

## 1. The white space, stated once

Every brief found the same hole from a different side:

| Brief | Finding |
|---|---|
| 01 Edge pain points | #3 unmet need: "prove which model ran" — no mainstream runtime verifies weights at load or attests what it ran; government RFPs now ask for it. White space #1: "verify-at-load model signing bound to measured boot; an appliance that extends TPM PCRs with the model digest and emits an attested inference receipt per request directly answers the #1 government question." White space #4: "bit-exact cross-hardware deterministic inference at acceptable throughput — nobody offers reproducible-by-construction inference at product speed." |
| 02 AI-OS prior art | Gap #4: "attestation covering model weights, tokenizer, system prompt, tool manifests and policies as measured-boot components, and a fleet controller that refuses to task nodes on PCR mismatch." Gap #7: "an LLM inference service inside any Rust OS/unikernel — only firmware-only demos exist (NIGHTRUN, alice-aegis)." |
| 03 Standards | "No accepted standard, benchmark or reference implementation exists for (a) attested inference receipts, (b) cross-machine bit-exact inference, (c) signed hash-chained inference logs, (d) a model boot manifest. ... The CPU-only / TPM-measured-boot / disconnected-edge variant is empty." The IETF individual draft "Attested Inference Receipt (AIR) v1" (Cyntrisec, Jul 2026) profiles ONLY AWS Nitro and Intel TDX, requires 48-byte SHA-384 registers, and says "An AIR v1 receipt attests the CPU-side TEE only"; TPM, measured boot, DICE and edge are not mentioned. |
| 04 Kernels | Gap 4+5: "exact-replay verifiability ... nobody has published this for an LLM"; "measured-boot-attested inference without a TEE: a unikernel's whole TCB is one EFI binary + MODEL.SAF; TPM 2.0 PCR extension of both plus an AIR-style receipt would be a new attestation profile. Consumer x86 boxes have TPMs; SGX/TDX they do not." |

The "LLM boots from UEFI" headline is gone (NightRun, Jul 2026: CRC-32, Secure Boot off, no determinism, no attestation). What remains unclaimed, falsifiable, and buildable by a small lab is **assurance**: the same answer, bit for bit, on any CPU, with hardware proof of which machine, which binary and which model produced it, and no operating system in the trusted computing base.

Aefinity already owned three of the four pieces before this session (CIS-1 integer semantics, witness receipts, a bootable verifier kit, cross-ISA CI). The missing piece was the hardware root of trust. LAB-04 adds it.

## 2. What this session established (all measured, all logged)

| # | Result | Where |
|---|---|---|
| R1 | The pinned BitNet-2B CIS-1 decode digest `cab11400d737ac4a` reproduced from independently re-derived artifacts (different MODEL.SAF bytes, same values) on a fourth x86 microarchitecture (Sapphire Rapids class, AVX-512/VNNI/AMX, KVM VM). First reproduction not using the canonical artifact file. | LAB-02 |
| R2 | Real tool bug found and fixed on the way: `repack_ternary.py` applied the Falcon-E reciprocal scale convention to Microsoft's offline-quantized checkpoint, whose `AutoBitLinear` multiplies; output was word salad with every structural check passing. New `--scale-convention auto`. A 2.4e-7 scale perturbation alone moved greedy tokens — the sensitivity argument for exact-replay receipts, demonstrated. | LAB-02 |
| R3 | First CIS-1 kernel for VNNI silicon (`cis_vnni.rs`, zmm + ymm paths), bit-identical on 13 shapes + hazards; 1.25-1.36x the AVX2 incumbent cache-resident, 1.11-1.15x when streaming from DRAM. The decode is DRAM-bound at ~6 GB/s single-core on this VM (membw seq_read 6.8 GB/s): kernels are at the roofline; the levers are cores and bytes/token. 4-row blocking was slower (recorded negative). | LAB-03 |
| R4 | Row-parallel CIS-1 decode (bit-identical by construction: rows are independent dot products): 2B decode 6.27 -> 9.47 tok/s at 2 threads on the VM, digest unchanged; 4-thread figure in LAB-05. membw: 1T 6.8 GB/s, 4T 21-25 GB/s, so bandwidth scales with cores here. | LAB-05 |
| R5 | AEGIS-ATTEST v0: the unikernel measures MODEL.SAF/EMBED.BIN/VOCAB.BIN (+RECEIPT.TXT) into TPM PCR 12 and the CIS-1 witness chain + verdict into PCR 13 via EFI_TCG2_PROTOCOL, reads PCR 4/12/13 back with TPM2_PCR_Read, dumps the TCG event log, mints or verifies a receipt with no OS, and signs a TPM2_Quote over PCR 4,12,13 with a TPM-resident ECC P-256 key (qualifyingData = SHA-256 of the receipt). Host verifier replays PCRs from the event log and checks the quote with OpenSSL. Under QEMU/OVMF + swtpm (correctness only). | LAB-04 |
| R6 | A `no_std`, no-alloc, `forbid(unsafe_code)`, zero-dependency TPM 2.0 wire-format crate (`tpm2min`) whose quotes verify with tpm2-tools, OpenSSL and an independent parser (25/25), plus the finding that the first TPM2_Quote after Startup returns TPM_RC_RETRY on libtpms and must be resent (tpm2-tss hides this; EFI_TCG2 does not). | tpm2lab/RESULT.md |
| R7 | A receipt minted by the unikernel with no OS is byte-identical to the golden receipt minted on Linux (`tests/golden/witness_v1_m7_once64.receipt`) — the mint path and the verify path are the same arithmetic. | LAB-04 |

## 3. The three candidate "standards" and how they rank

**A. Attested Inference Receipt — TPM measured-boot profile (AIR-TPM) + Model Boot Manifest.** Fills gaps (a) and (d) of brief 03 and gap #4 of brief 02. Concretely: an EAT/COSE profile where `enclave_measurements` carries 32-byte SHA-256 PCRs (PCR 0-7 firmware, PCR 4 the engine binary, PCR 12 the model artifact set, PCR 13 the receipt chain), `attestation_doc_hash` = SHA-256 of the TPM2_Quote (TPMS_ATTEST || TPMT_SIGNATURE), key binding = the AK's TPM2B_PUBLIC (+ EK certificate chain on real TPMs), and — unique to CIS-1 — `response_hash` is REPLAYABLE: any verifier recomputes the chain bit for bit on its own CPU. Two independent roots (hardware attestation AND deterministic replay) where every other scheme has at most one. Reference implementation exists as of today (LAB-04). This is the headline. Rank 1.

**B. Bit-exact decode conformance suite at usable speed.** Fills gap (b). Aefinity has the spec (CIS-1 v1.0.3), the digests, a 4-microarchitecture + aarch64 reproduction set, and now VNNI + multicore making the integer path competitive (LAB-05 ratios). What is missing is the public artifact: a suite of (model, prompt, length) -> digest vectors for BitNet-2B and Falcon-E-1B with CI across Intel/AMD/Arm, and third-party reproductions. `int-llm` (0.2 tok/s) is the only competitor and is 30-50x slower. Rank 2 (mostly packaging + outreach).

**C. The AI-run operating system.** Brief 02's gaps #1, #3, #6, #7 are open, but the prior-art table shows why: the shipping path is "LLM as system service + OS-enforced boundary" (Windows agent workspace, Apple, Android), not "LLM as kernel". The defensible Aefinity version is the ATTESTED AUTONOMOUS NODE: a machine whose every model, prompt, tool manifest and policy is a measured-boot component, whose every action is a hash-chained receipt, and which a fleet controller refuses to task when PCRs mismatch. ALICE is the firmware-level sentinel and recovery root of that design; Linux (immutable image) is the daily body. Design in `design/AEFINITY-OS-v2-architecture.md`. Rank 3 as a research program; it is where A and B get used.

## 4. What is NOT claimed
- No performance number from this session is a product figure (KVM VM, 4 vCPU). Ratios only; iron re-measurement is the next step (box1/box2 for correctness and multicore; a VNNI-capable box for the kernel).
- The attestation ran against a software TPM (swtpm) under OVMF. A physical TPM 2.0 adds the EK certificate chain to a manufacturer root; the code path is identical (EFI_TCG2_PROTOCOL) but has not run on iron in this session.
- CIS-1 is greedy, 2B-class, pruned 50k vocab, integer semantics with a measured +0.12% perplexity cost (ledger A35). None of that changed here.
- "First" is used only where the briefs found no prior artifact after search; the honest wording is "we found no prior".

## 5. Recommended next 30 days (in order)
1. Boot the attest-enabled kit on the Dell i5-5200U and HP N4020 (both have fTPM?) — verify PCR 4 matches the firmware's measurement of the exact `.efi`, collect the quote with the real EK chain. One afternoon per box.
2. Publish AIR-TPM profile v0 as a docs/design note + the `attest_verify.py` reference verifier; file the PUBLISH? item per policy; consider an IETF individual draft (RATS) once reproduced on two physical TPMs.
3. Land `--scale-convention`, `cis_vnni`, the parallel CIS dispatch and `tpm2min` on alice-aegis via PRs (patch in `patches/`); CI digests must stay green.
4. Multicore on bare metal via MP Services (design in roadmap; test digest identity under QEMU -smp 4 first).
5. DoW SBIR Release 6 (Oct 21) and NSF 26-510 (Nov 4): the attested-receipt appliance maps to the AI evaluation/trustworthy-AI topics; the lab logs here are the evidence package.
