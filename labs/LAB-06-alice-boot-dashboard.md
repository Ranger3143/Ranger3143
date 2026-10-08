# LAB-06 — The A.L.I.C.E. boot dashboard: what a person at the machine sees

**Date:** 2026-10-06 · **Host:** this cloud VM (QEMU TCG, OVMF, swtpm) · **Branch:** alice-aegis `lab/vnni-cis1` (patch `patches/0002-*.patch`)
**Rule A:** everything here ran under QEMU TCG. Screenshot timestamps are wall-clock seconds after launch and carry **no performance meaning**. No throughput or latency is claimed anywhere in this lab.
**Rule B:** every digest, PCR value and verdict below is copied from a file under `labs/logs/dashboard/`.

## 1. What changed

Before this lab ALICE's screen was the firmware text console: white 16x32 glyphs on black, one transcript, 2048x2048 under QEMU's std VGA (`labs/screenshots/dashboard/00_before_text_console.png`). The unikernel already *knew* everything a verifier cares about (CPUID, artifact SHA-256s, TPM PCRs, the quote, the receipt digest and chain) but printed it as log lines.

The dashboard renders that state, and only that state (prime directive 1: nothing on screen is invented; every value is read from the running system):

| Region | Source of every value shown |
|---|---|
| Header: mark, tagline, **mode badge** (`QEMU TEST`, `MINT RECEIPT - CIS-1 FullInt`, `VERIFY RECEIPT - CIS-1 FullInt`, `INTERACTIVE - f32 engine`) | the branch main.rs is executing |
| **MACHINE** panel: CPU brand, vendor/family/model/stepping, ISA flags, kernel level, hypervisor bit, "OS: none - ring 0 unikernel, boot services" | CPUID leaves 0/1/7 and 0x8000000x, `aegis_core::ops::simd_level_name()` |
| **PAYLOAD** panel: file names, sizes, SHA-256 prefixes, "sha256 measured into TPM PCR 12" | the loaded byte slices and the TCG2 measurement log |
| **ATTESTATION** panel: TPM presence and bank, event counts per PCR, PCR 4/12/13 values, `TPM2_Quote` status and retry count, key type, then the **RECEIPT** block (steps, CIS digest, chain prefix, verdict) | `attest.rs` report lines (`pcr`, `quote-retries`, `quote-sig-s`), `verifier::Replay` |
| **TRANSCRIPT** viewport | every pre-existing `console::with_console` print site, unchanged, plus `PROMPT` / `OUTPUT` lines streamed token by token during mint |
| Footer **stage bar** BOOT · VOLUME · ALLOC · LOAD · HEAP · ATTEST · INFER · DONE with a one-line status | the `ui::stage(idx, status)` calls at each STAGE in main.rs |

Implementation (all under `aegis-uefi/src/`, no_std, allocation only via the existing heap):
- `gop.rs` — mode choice now prefers the largest **landscape** mode ≤ 1920 px wide (QEMU offers a 2048x2048 square otherwise); viewport-relative newline/scroll; `fill_rect`, `text_px`, `text_cell`, `set_viewport`, `clear_viewport`.
- `console.rs` — 1x glyphs unless the panel is ≥ 2560 px wide, so 1920 px gives a 120-column grid; `with_gop()` runs dashboard code only on the GOP backend. On the firmware text console every `ui::` call is a no-op and the plain transcript is exactly what it was.
- `ui.rs` (new, 300 lines) — palette, layout, panels, header, footer, `receipt_lines`, `attest_lines_from_report`.
- `verifier.rs` — `replay_with(.., on_token)`: a display-only observer called **after** `chain.fold_step` so it cannot change a bit of the receipt; `replay()` wraps it with a no-op closure.
- `main.rs` — hooks at each stage; receipt summary in the attestation panel in both mint and verify; a 3 s hold on the DONE frame so the finished screen can be seen before the QEMU test runner exits.

## 2. The runs (QEMU q35, TCG, `-cpu max`, 4 vCPU, 2 GB, OVMF 4M, swtpm TPM 2.0 TIS, std VGA)

Binary: `aegis-uefi.efi` built with `build_hardfloat.sh --qemu-test`, sha256 `c3d200a30bf0e7a0ea890c82ee33cda18b1b3c3ce9e708f3d4282b2d6c8f27a6` (`labs/logs/dashboard/host_verification.txt`). GOP mode selected: 1920x1440 (landscape rule), scale 1 → 120x45 cells. Assets: the M7 tiny gate model (`MODEL.SAF` 2 797 632 B, `EMBED.BIN` 6 291 456 B, `VOCAB.BIN` 163 954 B; SHA-256s in both `ATTEST.TXT` files).

### 2a. Mint run (`MINT.TXT` = prompt "Once upon a time", 64 tokens) — `labs/logs/dashboard/mint/`
- QEMU exit **33** (unikernel success signal) — `qemu_result.txt`.
- `BOOTLOG.TXT`: `STAGE M: minted receipt steps=64 cis-digest=67e8c0a96abc04e1 written=true`; `TPM: pcr 12 b0b2eb6b5db2f200c5db9245c55dcdd6fc5d2c45d950e5dae82779a658e5ee8c`; `TPM: pcr 13 6b838ff9d3792ad8f1f3dfe23c5044a3da3b423afee0bb0a00c214102d1ba444`; `TPM: quote-retries 1`; `STAGE A: ATTEST.TXT written=true`.
- Screens: `01_boot_payload_loading.png` (LOAD stage, payload sizes, "loading from boot volume"), `02_mint_decoding_live.png` and `03_mint_decoding_live_b.png` (INFER stage, `OUTPUT` text appearing token by token, footer `token N/64  CIS-1 FullInt  argmax`), `04_mint_done_receipt_quoted.png` (DONE: full `RECEIPT.TXT` in the transcript; attestation panel with PCR 4/12/13, `QUOTE TPM2_Quote PCR 4+12+13 signed, retry 1`, `KEY ECC P-256 ECDSA/SHA-256 (owner)`, `RECEIPT witness v1-CIS (mint)`, `DIGEST 67e8c0a96abc04e1`, `CHAIN aee25b770bd7b22eea2ea8476bbd9498..`, `VERDICT MINTED - chain in PCR 13`).

### 2b. Verify run (`RECEIPT.TXT` from 2a placed on the boot volume) — `labs/logs/dashboard/verify/`
- QEMU exit **33**.
- `BOOTLOG.TXT`/`ATTEST.TXT`: PCR 12 now has **4** events (the receipt itself is measured too): `1406ed092930d96ae3c953fb19d3bcd681624750bf43a2dacc4020bf71dd2276`; PCR 13 `ddf1429924df2070fc00f418022b67ec512edfbe129c780226e04aad4f39d67c` from `AEGIS-RECEIPT v0 mode=verify steps=64 cis-digest=67e8c0a96abc04e1 chain=aee25b77… verdict=PASS`.
- Screen: `05_verify_pass_quoted.png` — transcript shows `artifacts: 3/3 hashes match the receipt`, receipt vs local digest and chain, `VERIFY PASS - this machine reproduced all 64 decode steps' full logit vectors bit-for-bit, with no OS underneath`; attestation panel `VERDICT PASS - every logit reproduced`; footer `DONE - VERIFY PASS, quote written to ATTEST.TXT`.
- PCR 4 (firmware's measurement of `BOOTX64.EFI`) is `00518abd1a378c155fad873aa14d280f8a2433fdd215abeb0e90d8b99991c3aa` in **both** runs: same binary, same PCR 4, which is exactly what a Model Boot Manifest (spec/AIR-TPM-PROFILE-v0.md) pins.

## 3. Host-side verification (`labs/logs/dashboard/host_verification.txt`)

| Check | Mint run | Verify run |
|---|---|---|
| `attest_verify.py`: PCR 12/13 replayed from the event log == PCR values read back | PASS (3 + 1 events) | PASS (4 + 1 events) |
| `attest_verify.py`: every event-log entry re-hashes to its digest | PASS | PASS |
| `attest_verify.py`: quote `extraData` == SHA-256 of the receipt bytes (`528e205e04882437…`) | PASS | PASS |
| `attest_verify.py`: quote `pcrDigest` == SHA-256 over PCR 4,12,13 | PASS | PASS |
| `attest_verify.py`: ECDSA P-256/SHA-256 signature over `TPMS_ATTEST` (OpenSSL) | Verified OK | Verified OK |
| `attest_verify.py`: tampered attest rejected | PASS | PASS |
| `cis_witness verify` of the **minted** `RECEIPT.TXT` on the Linux host against the M7 artifacts | VERIFY PASS (64 tokens, digest, full logit chain) | — |
| Minted `RECEIPT.TXT` vs receipt consumed by the verify run | byte-identical | — |
| Minted `RECEIPT.TXT` vs `alice-aegis/tests/golden/witness_v1_m7_once64.receipt` | **byte-identical** | — |

The last row is the point of the observer design: the dashboard streams tokens to the screen while the receipt is minted, and the receipt is the same bytes the repository's golden test fixes. The screen is a view, never an input.

## 4. Regression evidence
- `aegis-core` and `aegis-linux` test suites, with and without `--features parallel`: all `test result: ok`, 0 failures (run after the UI change; the UI touches `aegis-uefi` only).
- `scripts/integrity_check.py`: clean.
- The QEMU mint/verify gates above both exit 33 with a TPM attached; the pre-dashboard runs in LAB-04 produced the same CIS digest `67e8c0a96abc04e1` and the same PCR 12 value for the three payload artifacts (`b0b2eb6b…`), so measurement is unchanged by the new mode selection and drawing code.

## 5. What is still only a rendering
- Colors and layout were tuned at 1920x1440 under QEMU; a 1366x768 laptop panel will get 85x24 cells and the side column shrinks to 34 columns (digest prefixes will clip to the panel edge by design). Not yet tested on real hardware.
- The transcript still clears at stage boundaries (pre-existing behaviour), so early boot lines scroll away.
- No input handling: the dashboard is read-only. Interactive mode keeps the pre-existing keyboard loop and prints into the transcript viewport.

## 6. Reproduce
```
# build (nightly + build-std), then boot with screenshots at the listed seconds
cd alice-aegis/aegis-uefi && bash build_hardfloat.sh --qemu-test
labs/tools/boot_shot.sh target/x86_64-uefi-hardfloat/release/aegis-uefi.efi <assets_with_MINT.TXT> out_mint "20 27 30 34" --tpm
labs/tools/boot_shot.sh target/x86_64-uefi-hardfloat/release/aegis-uefi.efi <assets_with_RECEIPT.TXT> out_verify "24 32 36" --tpm
python3 -I labs/tools/attest_verify.py out_mint/esp/ATTEST.TXT --receipt out_mint/esp/RECEIPT.TXT   # the receipt is not positional since HARDEN-ATTEST
```
`boot_shot.sh` builds a real FAT32 image with mtools, attaches swtpm, drives QEMU's QMP `screendump`, and converts PPM→PNG with `ppm2png.py`.
