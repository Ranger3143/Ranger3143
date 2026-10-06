# Aefinity AI — Edge-AI research sprint, 2026-10-06

**Headline (measured, logged, reproducible):** a large-language-model inference engine that boots with **no operating system** now produces inference receipts that are **bit-exact on any CPU** (CIS-1) **and** signed by the machine's **TPM** over measured-boot PCRs that pin the firmware, the exact engine binary, the exact model bytes and the exact transcript. No prior artifact combining those was found in four independent literature/standards sweeps (research briefs 01-04). Everything here ran in this session; every number has a log.

> PUBLISH NOTE — this branch is on a PUBLIC repository because the session was configured to push here. Under Aefinity's 2026-08-28 publish policy several items below (the attestation capability, the AIR-TPM spec draft, the VNNI kernel) are "new technique / product-shaped" and would normally sit on a private branch until Justin answers a PUBLISH? item. Delete the branch and ask for a re-push to a private repository if that is the preference; nothing here has been announced anywhere else.

## What was found and built

| # | Result | Evidence |
|---|---|---|
| 1 | **The pinned BitNet-2B CIS-1 digest `cab11400d737ac4a` reproduced from independently re-derived artifacts** (different MODEL.SAF bytes, same values) on a 4th x86 microarchitecture (Sapphire Rapids class, first AVX-512/VNNI/AMX part). EMBED.BIN and VOCAB.BIN came out byte-identical to the program's canonical artifacts. | `labs/LAB-02-cis1-2b-digest-reproduction.md`, `labs/logs/repack_*.log` |
| 2 | **Tool bug found and fixed:** `repack_ternary.py` applied the Falcon-E reciprocal scale convention to Microsoft's packed BitNet checkpoint (whose `AutoBitLinear` multiplies) → word salad with every structural check passing. New `--scale-convention auto`. A 2.4e-7 scale perturbation alone moved greedy tokens: the sensitivity argument for exact-replay receipts, shown rather than asserted. | LAB-02 §Results 2-5; patch |
| 3 | **AEGIS-ATTEST v0 — TPM-attested inference receipts from the unikernel** (QEMU/OVMF + swtpm, correctness only): model artifacts measured into PCR 12, CIS-1 witness chain + verdict into PCR 13 (EV_IPL events, replayable from the TCG log), PCR 4/12/13 read back, `TPM2_Quote` over them signed by a TPM-resident ECC P-256 key with qualifyingData = SHA-256(receipt). Host verifier replays both PCRs from the event log and verifies the quote with OpenSSL; tampered attest rejected. The receipt **minted with no OS is byte-identical** to the Linux-minted golden receipt and verifies with the Linux tools. | `labs/LAB-04-attested-receipts-tpm.md`, `labs/logs/qemu/run_attest_{verify2,mint2}/{ATTEST.TXT,BOOTLOG.TXT,RECEIPT.TXT}`, `labs/logs/attest_verify_*.log`, `labs/tools/attest_verify.py` |
| 4 | **`tpm2min`:** `no_std`, no-alloc, `forbid(unsafe_code)`, zero-dependency TPM 2.0 wire format (Startup, PCR_Read, PCR_Extend, CreatePrimary, Quote, FlushContext); quotes verified 25/25 against swtpm with tpm2-tools, OpenSSL and an independent parser. Finding: the first `TPM2_Quote` after Startup returns `TPM_RC_RETRY` on libtpms and must be resent — tpm2-tss hides this, `EFI_TCG2_PROTOCOL` does not. | `tpm2min/`, `tpm2lab/RESULT.md` |
| 5 | **First CIS-1 kernel for VNNI silicon** (`cis_vnni.rs`, AVX-512 VNNI zmm + AVX-VNNI ymm), bit-identical on 13 shapes + hazards. 1.25-1.36x the AVX2 incumbent cache-resident; **1.11-1.15x when streaming from DRAM**, because the integer decode runs at ~90% of this VM's single-core sequential read bandwidth: the kernel is at the roofline, the levers are cores and bytes/token. 4-row blocking was slower (negative, recorded). | `labs/LAB-03-cis1-vnni-kernel.md`, `labs/logs/vnni_vs_avx2_*.log`, `labs/logs/membw_*.log` |
| 6 | **Row-parallel CIS-1 decode on Linux**, bit-identical **by construction** (rows are independent integer dots): 2B decode 6.3 → 9.5 → 12.5 tok/s at 1/2/4 threads on the VM (1.51x / 2.0x), digest identical every run. First multithreaded CIS-1 path in the program. | `labs/LAB-05-cis1-multicore-linux.md`, `labs/logs/cis_decode_timed_threads_run1.log` |
| 7 | **Four research briefs** (edge pain points; AI-OS prior art and Rust OS landscape; standards/funding/newsworthiness; ternary kernel SOTA + roofline) and a synthesis naming the white space and ranking three candidate standards. | `research/01..05` |
| 8 | **Spec draft:** Attested Inference Receipt — TPM measured-boot profile (AIR-TPM v0) + Model Boot Manifest, positioned against the IETF AIR v1 individual draft (Nitro/TDX only). | `spec/AIR-TPM-PROFILE-v0.md` |
| 9 | **Design:** Aefinity OS v2 — an attested, AI-operated machine for headless fleets and user workstations, with the code-type recommendation (`no_std` Rust firmware sentinel + immutable Linux body + Rust supervisor + Cedar policy + microVM/Wasm tool sandboxes), and the ALICE next-level roadmap with gates. | `design/AEFINITY-OS-v2-architecture.md`, `design/ALICE-NEXT-LEVEL-roadmap.md` |

Rule A (alice-aegis `CLAUDE.md`): the machine here is a 4-vCPU KVM cloud container (`labs/FINGERPRINT.txt`); **no absolute performance figure in this repository is a product number**. Ratios from same-process interleaved runs and bit-identity results are the admissible outputs; iron re-measurement is step 1 of the roadmap.

## Layout
```
research/   01 edge pain points · 02 AI-OS prior art + Rust OS landscape · 03 standards, funding, newsworthiness · 04 ternary kernel SOTA + roofline · 05 SYNTHESIS
labs/       LAB-02 digest reproduction · LAB-03 VNNI kernel · LAB-04 TPM-attested receipts · LAB-05 multicore · FINGERPRINT.txt
labs/logs/  raw logs (bench, membw, timed decode, QEMU runs incl. ATTEST.TXT/BOOTLOG.TXT/RECEIPT.TXT/swtpm.log, regression tests)
labs/tools/ boot.sh (QEMU/OVMF + swtpm harness, real FAT image), attest_verify.py (host verifier), fingerprint.sh, chain*.sh
spec/       AIR-TPM-PROFILE-v0.md
design/     AEFINITY-OS-v2-architecture.md · ALICE-NEXT-LEVEL-roadmap.md
patches/    0001-*.patch — the alice-aegis lab branch (`lab/vnni-cis1` on top of main 3e3f465): cis_vnni, parallel CIS dispatch, attest.rs, verifier mint, tpm2min dep, repack fix, benches/tests/examples
tpm2min/    the TPM 2.0 wire-format crate (also inside the patch)
tpm2lab/    swtpm end-to-end lab for tpm2min (RESULT.md, CLI, independent verifier, artefacts)
```

## Reproduce
```bash
# 1. ALICE lab branch
git clone https://github.com/Aefinity-AI/alice-aegis && cd alice-aegis && git checkout 3e3f465 -b lab/vnni-cis1 && git am ../patches/0001-*.patch
cd aegis-core && cargo test --release --test cis_vnni_equivalence && cargo build --release --bin vnni_vs_avx2 && ./target/release/vnni_vs_avx2 11 20 256
# 2. 2B artifacts (needs microsoft/bitnet-b1.58-2B-4T model.safetensors + tokenizer.json + config.json)
python3 aegis-forge/repack_ternary.py <ckpt_dir> <out> --source-packing hf1bitllm --llama3-prune   # auto -> multiply
cd aegis-linux && cargo build --release --features parallel --example cis_decode --example cis_decode_timed
./target/release/examples/cis_decode <out>/MODEL.SAF <out>/EMBED.BIN <out>/VOCAB.BIN 64 "Once upon a time"   # expect cab11400d737ac4a
AEGIS_THREADS=4 ./target/release/examples/cis_decode_timed <out>/MODEL.SAF <out>/EMBED.BIN <out>/VOCAB.BIN 64 "Once upon a time" 3
# 3. Attested boot under QEMU (needs qemu-system-x86, ovmf, swtpm, mtools; nightly + rust-src for the hard-float target)
cd aegis-uefi && ./build_hardfloat.sh --qemu-test
printf '64\nOnce upon a time\n' > /tmp/m7/MINT.TXT   # next to the M7 trio from model-lab/tinybit/m7_final_gate_work/artifacts
labs/tools/boot.sh target/x86_64-uefi-hardfloat/release/aegis-uefi.efi /tmp/m7 /tmp/run --tpm   # exit 33 = success
python3 labs/tools/attest_verify.py /tmp/run/esp/ATTEST.TXT --artifacts /tmp/m7 --receipt /tmp/run/esp/RECEIPT.TXT
```

## What is NOT claimed
No iron run of the attestation yet (software TPM under OVMF); transient owner-hierarchy AK without an EK certificate (standard TPM gap, closed by provisioning); CIS-1 remains greedy, 2B-class, pruned 50k vocab, +0.12% perplexity (ledger A35); "first" is used only where the briefs found no prior artifact after search.

## Next (from the roadmap)
1. Attested kit on the Dell/HP/Acer with their physical TPMs; 2. EK-certified AK; 3. Secure Boot on with a signed `.efi`; 4. multicore on bare metal via MP Services (digest-identical by construction); 5. land the patch on alice-aegis via PRs behind the CI digest gates; 6. DoW SBIR Release 6 (Oct 21) / NSF 26-510 (Nov 4) — the lab logs are the evidence package.
