# LAB-04 — AEGIS-ATTEST v0: TPM-measured, TPM-signed inference receipts from a unikernel with no operating system

Date: 2026-10-06. Environment: QEMU 8.x `-machine q35,accel=tcg -cpu max -smp 4 -m 2048`, OVMF (Ubuntu `OVMF_CODE_4M.fd`, TPM2-enabled build), swtpm 0.7.3 / libtpms 0.9.3 as `tpm-tis`. **Correctness/identity only (Rule A): nothing here is a performance figure.** Code: `aegis-uefi/src/attest.rs`, `verifier.rs`, `main.rs`, `tpm2min/` (branch `lab/vnni-cis1`); harness `labs/qemu/boot.sh`; host verifier `labs/attest_verify.py`.

## Claim
A UEFI application with no OS can (1) measure the exact model artifacts it loaded and the exact inference transcript it produced into TPM 2.0 PCRs, (2) have the TPM sign a quote over those PCRs plus the firmware's own measurement of the application binary, and (3) emit a receipt that a third party can check two independent ways: by replaying the inference bit for bit on any CPU (CIS-1), and by verifying the TPM signature and PCR replay (hardware root of trust). No prior artifact doing this was found (brief 03 §2a/§2d; brief 04 gap 5).

## Design (one paragraph)
PCR 4 is the firmware's: OVMF measures `BOOTX64.EFI` into it (EV_EFI_BOOT_SERVICES_APPLICATION, TCG PC Client). After the artifacts are in RAM and before anything runs on them, the unikernel extends **PCR 12** with one EV_IPL event per artifact whose data is the ASCII line `AEGIS-MEASURE v0 artifact=<name> bytes=<n> sha256=<hex>` (firmware hashes the line; the PCR is replayable from the event log alone). After the CIS-1 decode (verify or mint) it extends **PCR 13** with `AEGIS-RECEIPT v0 mode=<verify|mint> steps=<n> cis-digest=<fnv> chain=<sha256> verdict=<PASS|FAIL|MINTED>` where `chain` is the witness v1 SHA-256 chain over every step's token id and full i64 logit vector. It then reads PCR 4/12/13 (TPM2_PCR_Read), dumps the TCG2 event log for those PCRs, creates a transient ECC P-256 ECDSA/SHA-256 restricted signing key under the owner hierarchy (TPM2_CreatePrimary), signs TPM2_Quote(PCR 4,12,13; qualifyingData = SHA-256 of RECEIPT.TXT bytes), flushes the key, and writes `ATTEST.TXT`. TPM commands go through `EFI_TCG2_PROTOCOL.SubmitCommand` with bounded resend on TPM_RC_RETRY.

## Runs (both `qemu_exit=33` = unikernel success signal; artifacts = M7 trio, 8.9 MB, `tests/golden/witness_v1_m7_once64.receipt`)
Unikernel: `aegis-uefi.efi` sha256 7cad979de5406988e7853a032f2f0531fdbbc5c04930b1d1feefe556727440e8 (hard-float, qemu-test feature; AVX2 census fma=161 ymm=504). Logs: `labs/logs/qemu/run_attest_verify2/`, `run_attest_mint2/` (BOOTLOG.TXT, ATTEST.TXT, RECEIPT.TXT, swtpm.log, serial.log, RESULT.txt).

### Run A — verify mode (RECEIPT.TXT on the volume)
BOOTLOG: `TPM: EFI_TCG2_PROTOCOL present — measuring payload into PCR 12`; 4 extends (MODEL.SAF 23cfad0a…, EMBED.BIN 3752cd5c…, VOCAB.BIN 5a1d79ca…, RECEIPT.TXT 528e205e…); `STAGE V: witness verify PASS — this machine reproduced all 64 decode steps' full logit vectors bit-for-bit, with no OS underneath`; PCR 4 510f20ce…, PCR 12 1406ed09…, PCR 13 ddf14299…; `quote-retries 1`; `ATTEST.TXT written=true`.

### Run B — mint mode (MINT.TXT = "64 / Once upon a time", no receipt)
`STAGE M: minted receipt steps=64 cis-digest=67e8c0a96abc04e1 written=true`; PCR 12 b0b2eb6b… (3 events), PCR 13 6b838ff9… (mode=mint); `quote-retries 1`. The minted RECEIPT.TXT is **byte-identical** to `tests/golden/witness_v1_m7_once64.receipt` (sha256 528e205e… both; `diff` empty) and `cis_witness verify` on Linux prints `VERIFY PASS — replay reproduced 64 tokens, the token digest, and the full logit chain bit-for-bit` (`labs/logs/cis_witness_verify_minted_receipt.log`).

### Host-side verification (`attest_verify.py`, stdlib + openssl) — both runs
| check | A | B |
|---|---|---|
| PCR 12 replay from `measured` lines == TPM2_PCR_Read value | PASS (4 events) | PASS (3 events) |
| PCR 13 replay == TPM value | PASS | PASS |
| every measured line present in TCG2 event log with matching SHA-256 | PASS | PASS |
| PCR 4 firmware events present (EV_EFI_ACTION, EV_SEPARATOR, EV_EFI_BOOT_SERVICES_APPLICATION with the BOOTX64.EFI device path) | 3 events | 3 events |
| local artifact sha256 == measured | 3/3 PASS | 3/3 PASS |
| receipt chain bound in PCR 13 line | PASS | PASS |
| TPMS_ATTEST magic ff544347 / type 8018 | PASS | PASS |
| extraData == qualifying == SHA-256(RECEIPT.TXT) | PASS | PASS |
| pcrDigest == SHA-256(PCR4 ‖ PCR12 ‖ PCR13) from the read-back values | PASS | PASS |
| ECDSA-P256/SHA-256 over TPMS_ATTEST with the quoted TPMT_PUBLIC point (OpenSSL) | Verified OK | Verified OK |
| tampered attest rejected (negative control) | PASS | PASS |
`labs/logs/attest_verify_run_attest_verify2.log`, `attest_verify_quote_*.log`.

## Findings
1. **It works end to end with no OS in the TCB.** Firmware (PCR 0-7) → exact engine binary (PCR 4, measured by firmware, not by us) → exact model bytes (PCR 12) → exact transcript (PCR 13) → TPM signature. A verifier with only `ATTEST.TXT`, `RECEIPT.TXT` and the public key can check everything offline; with the artifacts it can also replay the inference and MUST get the same chain (CIS-1).
2. **TPM_RC_RETRY on the first quote is real at the firmware interface.** Both runs show `quote-retries 1`: `EFI_TCG2_PROTOCOL.SubmitCommand` returns the TPM's 0x922 verbatim; tpm2-tss and Linux resend silently. A unikernel must implement the resend itself (tpm2min `Error::is_retryable`).
3. **Mint == verify arithmetic.** The receipt minted under firmware equals the Linux golden byte for byte — the first cross-environment identity at the RECEIPT level (previous identities were digest/chain level with receipts minted on Linux).
4. **QEMU vvfat loses guest writes.** With `-drive file=fat:rw:dir`, BOOTLOG/ATTEST/RECEIPT written by the guest never appeared on the host (observed in the first two attested boots, which passed their exit gate but left nothing to read). A real FAT32 image (mtools) fixed it; `boot.sh` now does that. Relevant to every `xtask` gate that reads guest files.
5. The attestation key here is a transient primary under the owner hierarchy with no certificate: it proves "a TPM holding this key signed these PCRs", not "which TPM". On physical hardware the Endorsement Key certificate (manufacturer-signed) and a `TPM2_Certify`/EK-bound AK close that gap; swtpm has no manufacturer chain. This is the standard TPM attestation gap, not specific to this design.

## What a reviewer can do with the files
```
python3 labs/attest_verify.py labs/logs/qemu/run_attest_mint2/esp/ATTEST.TXT \
    --artifacts <M7 trio dir> --receipt labs/logs/qemu/run_attest_mint2/esp/RECEIPT.TXT
```
replays both PCRs, checks the event log, and verifies the quote with OpenSSL. Then `cis_witness verify` (Linux) or the kit stick (bare metal) replays the inference itself.

## Not shown here (next steps)
Physical TPM (Dell i5-5200U, HP N4020, Acer) boots; EK certificate chain; Secure Boot on (signed `.efi`); the 2B trio under attestation on iron; the AIR-TPM receipt encoding (COSE/CWT) over these fields (spec draft in `spec/`).
