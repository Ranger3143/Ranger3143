# HARDEN-ATTEST RESULT: fail-closed attest_verify.py and finalize.sh (LAB-09 part 2, task G)

Every number below is computed by `labs/safe/harden_attest.py report` from the TSV/log files in this directory and from the SAFE-01 TSVs. Rule A: no timing or rate anywhere. Rule B: every count is a count of rows in a saved file.

## 0. Summary

- **HA2 (genuine boots still pass): SUPPORTED.** The 8 `final_step12000` QEMU boots: 8 of 8 accepted by the exact `finalize.sh` invocation (form T: `--receipt --strict --expect-pubkey <pin from the boot's own swtpm state> --efi <EFI>`), 8 of 8 by the default form D. All 15 ATTEST.TXT files on disk: 15 accepted by D, 15 by `--strict`.
- **HA1 (every previously accepted H3 mutant class is now rejected): PARTLY SUPPORTED.** SAFE-01 recorded 88 of the 349 H3 mutants as ACCEPT under F1 or F2 (66 semantic edits and 22 cosmetic re-encodings). The finalize form T accepts 10 of the 66 semantic ones and 0 of the 22 cosmetic ones; the default form D accepts 11 and 18; T plus `--reject-high-s` (L) accepts 8 and 0. The old positional form P is a usage error for 349 of 349 mutants. The T-accepted remainder is in four sub-fields, none of which is covered by any digest or signature (cpuid, quote-retries, the device-path part of the image-load event) or is a valid second signature (s -> n-s); section 4a lists every one.
- The 8 final boots have **8 distinct attestation keys**: every `boot_shot.sh --tpm` run creates a fresh swtpm state, hence a fresh owner seed. There is no shared "first boot" key. `finalize.sh` therefore pins each boot to the key re-derived from that boot's own swtpm state (8 of 8 derived keys equal the key in ATTEST.TXT).
- **libtpms does not normalise ECDSA s: 4 of the 8 final boots have a high-s signature** (5 of 15 files on disk). `--strict` therefore does NOT reject high-s (it would fail 4 genuine boots); the check is the separate opt-in flag `--reject-high-s`. Deviation from the task text, explained in section 6.
- Exhaustive single-byte substitution of both files (additional): 7895 mutants, 404 accepted by T, all of them in lines named in section 4c (cpuid, event pcr=4 #2, quote-retries), 0 anomalies.

## 1. What was changed and how it was run

Files: `labs/tools/attest_verify.py` (rewritten, same output lines), `labs/tools/ak_from_swtpm.sh` (new), `model/demo-operator/finalize.sh` (attest line), `labs/tools/README-attest_verify.md` (new), `labs/LAB-06-alice-boot-dashboard.md` (one example command that used the positional form), `labs/safe/harden_attest.py` (this experiment). Pre-hardening copies kept here: `attest_verify_before.py`, `finalize_before.sh`.

```
cd /home/user/Ranger3143/labs/safe
python3 -I harden_attest.py run      # -> run_harden.log, final_boots_recheck.log, final_boots_keys.tsv, genuine_all.tsv, h3_rerun.tsv, h3_s1_rerun.tsv, h3_forgery_rerun.tsv, h3_s3_forgeries.tar.gz (S3 and S4)
python3 -I harden_attest.py bytes    # -> h3_byteflip.tsv (additional exhaustive single-byte substitution)
python3 -I harden_attest.py report   # -> RESULT.md
```

SAFE-01's own scripts (`labs/safe/safe01_tamper.py`, `labs/safe/verify09/`) still call the old positional form and were not changed: its recorded numbers belong to `attest_verify_before.py`; re-running them against the hardened verifier would turn every F1 run into a usage error.

Forms (every run `nice -n 5 python3 -I`, `OMP_NUM_THREADS=1`):

```
P  attest_verify.py ATTEST RECEIPT                                                    old finalize.sh form (positional receipt)
D  attest_verify.py ATTEST --receipt RECEIPT                                          hardened, default flags
T  attest_verify.py ATTEST --receipt RECEIPT --strict --expect-pubkey PIN --efi EFI   the form now in finalize.sh
L  T --reject-high-s
```

PIN is `labs/tools/ak_from_swtpm.sh <swtpm state dir of the boot>` (tpm2-tools `tpm2_createprimary` with the unikernel's template against a copy of the saved swtpm state), never read from the ATTEST.TXT under test. For the mutants of `qemu_calc` / `qemu_self` and for the forgeries the pin is that boot's derived key. EFI is `aegis-uefi-gateway-qemutest.efi`.

Scoring rules fixed before the run (`verdict_after` in the script): ACCEPT = exit 0 and both `ATTEST VERIFY PASS` and `QUOTE VERIFY PASS` printed; REJECT = exit 1; REJECT_USAGE = exit 2; anything else (traceback, exit 0 without the PASS lines, timeout) is an ANOMALY and is counted. "Before" verdicts are the SAFE-01 values (`h3_results.tsv`, `h3_s1_receipt_side.tsv`, `h3_s2_forgery.tsv`: F1 = positional receipt, F2 = `--receipt --artifacts`); the pre-hardening verifier was also re-run on the same extracted mutants as a reproducibility check.

Checks on the run itself: mutants whose extracted bytes equal SAFE-01's recorded sha256: 351 of 351 (the script asserts it); pre-hardening re-run agrees with the SAFE-01 F1/F2 verdicts on 351 of 351 rows; anomalies across all hardened runs (P, D, T, L): 0; hardened runs that printed a FAIL/MISSING/ERROR line and still exited 0: 0; the two unmodified controls: D 2 of 2, T 2 of 2, L 2 of 2 accepted.

Input hashes (`provenance.txt`):

```
af8c04301a87ffc7bd37a9a1f7208779a87bcbab631ef9ca0791b0ac4c282a2b  attest_verify.py (hardened)
6700ba13dd9f210ccb26fd0a192fe5b2aba2fc3ccce0ec555e0864d8630ecbde  attest_verify_before.py
e745953293d0654a60a253d6287d6e3e506bb60df0c9d3574882716d3f8ed93c  ak_from_swtpm.sh
31c7d3ebfaed7beccc0029c74ed1a4f9d9f964261f1382b75aedd34849111b5f  finalize.sh
f2e016f1a8c149c94da1059868ee64af8ae11e4f5e012c76e76c11f2c1a1af8d  SAFE-01 h3_mutants.tar.gz
9434dc5bf2e0268e89056b8ee308cb5f2a9bf5f558b80c594c685beaceebadbe  SAFE-01 h3_results.tsv
b02948c4159de5676c815908783ea9be446e43bd940f5b07b6e5229aff21e428  FINALIZE.log (final_step12000, must stay unchanged)
60028c5e82d9fec203b581b8916b19e5fdef4d641259fb6dd446c694860b6236  EFI aegis-uefi-gateway-qemutest.efi
c3d200a30bf0e7a0ea890c82ee33cda18b1b3c3ce9e708f3d4282b2d6c8f27a6  EFI aegis-uefi-dash-qemutest.efi
```

## 2. Genuine boots (HA2)

Full verbatim output of the finalize.sh invocation for each of the 8 boots: `final_boots_recheck.log`. `FINALIZE.log` was not edited: `run_harden.log` records its sha256 before and after as equal.

| boot | AK x (first 8 bytes) | sig s | T (finalize form) | D | L (T + --reject-high-s) | default + --artifacts | P (old positional form) |
|---|---|---|---|---|---|---|---|
| qemu_abstain | 80c32038e8b48984.. | high | ACCEPT | ACCEPT | REJECT | ACCEPT | REJECT_USAGE |
| qemu_calc | 3fad67d3224ab19b.. | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | REJECT_USAGE |
| qemu_calc_words | 219de5fff3e649cf.. | high | ACCEPT | ACCEPT | REJECT | ACCEPT | REJECT_USAGE |
| qemu_everyday | 652f5681b861397d.. | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | REJECT_USAGE |
| qemu_lookup | b23e77a920439f28.. | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | REJECT_USAGE |
| qemu_receipt | 230cdf1d02e60509.. | high | ACCEPT | ACCEPT | REJECT | ACCEPT | REJECT_USAGE |
| qemu_self | 9a6913281eb374ab.. | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | REJECT_USAGE |
| qemu_unknown_tool | c5faa42636634c03.. | high | ACCEPT | ACCEPT | REJECT | ACCEPT | REJECT_USAGE |

Distinct attestation keys among the 8 boots: **8**. Keys re-derived from each boot's own swtpm state equal the key in its ATTEST.TXT: **8 of 8** (`final_boots_keys.tsv`). Low-s signatures: 4 of 8; high-s: 4 of 8.

Negative controls on the same 8 boots (each expected to be rejected):

| control | rejected | of |
|---|---|---|
| X1 control: pin of the next boot | 8 | 8 |
| X2 control: receipt of the next boot | 8 | 8 |
| X3 control: wrong EFI (dashboard image) | 8 | 8 |
| X4 control: --strict without --receipt | 8 | 8 |

All ATTEST.TXT files found under `labs/logs/` (`genuine_all.tsv`):

| file | sig s | D | --strict (no pin) | T with swtpm-derived pin | --strict --reject-high-s | before: positional form | before: --receipt form |
|---|---|---|---|---|---|---|---|
| opmodel/final_step12000/qemu_abstain | high | ACCEPT | ACCEPT | ACCEPT | REJECT | ACCEPT | ACCEPT |
| opmodel/final_step12000/qemu_calc | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| opmodel/final_step12000/qemu_calc_words | high | ACCEPT | ACCEPT | ACCEPT | REJECT | ACCEPT | ACCEPT |
| opmodel/final_step12000/qemu_everyday | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| opmodel/final_step12000/qemu_lookup | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| opmodel/final_step12000/qemu_receipt | high | ACCEPT | ACCEPT | ACCEPT | REJECT | ACCEPT | ACCEPT |
| opmodel/final_step12000/qemu_self | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| opmodel/final_step12000/qemu_unknown_tool | high | ACCEPT | ACCEPT | ACCEPT | REJECT | ACCEPT | ACCEPT |
| dashboard/mint | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| dashboard/verify | low | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT | ACCEPT |
| opmodel/qemu_step2300_gateway_calc | low | ACCEPT | ACCEPT | n/a (no swtpm state mapped by name) | ACCEPT | ACCEPT | ACCEPT |
| opmodel/qemu_step2300_gateway_lookup | low | ACCEPT | ACCEPT | n/a (no swtpm state mapped by name) | ACCEPT | ACCEPT | ACCEPT |
| opmodel/qemu_step2300_self | high | ACCEPT | ACCEPT | n/a (no swtpm state mapped by name) | REJECT | ACCEPT | ACCEPT |
| qemu/run_attest_mint2 | low | ACCEPT | ACCEPT | n/a (no swtpm state mapped by name) | ACCEPT | ACCEPT | ACCEPT |
| qemu/run_attest_verify2 | low | ACCEPT | ACCEPT | n/a (no swtpm state mapped by name) | ACCEPT | ACCEPT | ACCEPT |

The dashboard and older boots have no `--efi` check in this table (different EFI images); "n/a" means no swtpm state directory could be mapped to that boot by name, so no independent pin was derived for it.

## 3. H3 mutants: class x {accepted before, accepted after}

349 mutants plus 2 unmodified controls (SAFE-01 `h3_results.tsv`, same files, sha256-checked). "before F1/F2" = SAFE-01 verdicts; "after P" = count of usage errors (exit 2) in the old positional form; D/T/L = accepted counts in the three hardened forms.

| class | mutants | before F1 accepted | before F2 accepted | after P: usage error | after D accepted | after T accepted | after L accepted |
|---|---|---|---|---|---|---|---|
| pcr-value | 48 | 0 | 0 | 48 | 0 | 0 | 0 |
| quote-attest | 68 | 0 | 0 | 68 | 0 | 0 | 0 |
| quote-signature | 24 | 0 | 0 | 24 | 0 | 0 | 0 |
| quote-qualifying | 16 | 0 | 0 | 16 | 0 | 0 | 0 |
| quote-pubkey | 16 | 0 | 0 | 16 | 0 | 0 | 0 |
| event-line | 68 | 35 | 35 | 68 | 2 | 1 | 1 |
| measured-line | 33 | 1 | 0 | 33 | 0 | 0 | 0 |
| field-deletion | 18 | 2 | 2 | 18 | 0 | 0 | 0 |
| unread-line | 28 | 26 | 26 | 28 | 7 | 7 | 7 |
| cosmetic | 28 | 22 | 22 | 28 | 18 | 0 | 0 |
| sig-malleability | 2 | 2 | 2 | 2 | 2 | 2 | 0 |
| **all classes** | 349 | 88 | 87 | 349 | 29 | 10 | 8 |

Sub-field detail:

| class | sub-field | mutants | before F1 accepted | before F2 accepted | after P: usage error | after D accepted | after T accepted | after L accepted |
|---|---|---|---|---|---|---|---|---|
| pcr-value | pcr4 | 16 | 0 | 0 | 16 | 0 | 0 | 0 |
| pcr-value | pcr12 | 16 | 0 | 0 | 16 | 0 | 0 | 0 |
| pcr-value | pcr13 | 16 | 0 | 0 | 16 | 0 | 0 | 0 |
| quote-attest | magic | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | type | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | qualifiedSigner.size | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | qualifiedSigner.name | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | extraData.size | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | extraData | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | clock | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | resetCount | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | restartCount | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | safe | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | firmwareVersion | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | pcrSelect.count | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | pcrSelect.hashAlg | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | pcrSelect.sizeofSelect | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | pcrSelect.bitmap | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | pcrDigest.size | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-attest | pcrDigest | 4 | 0 | 0 | 4 | 0 | 0 | 0 |
| quote-signature | quote-sig-r | 12 | 0 | 0 | 12 | 0 | 0 | 0 |
| quote-signature | quote-sig-s | 12 | 0 | 0 | 12 | 0 | 0 | 0 |
| quote-qualifying | quote-qualifying | 16 | 0 | 0 | 16 | 0 | 0 | 0 |
| quote-pubkey | quote-pub-x | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| quote-pubkey | quote-pub-y | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| event-line | pcr4/sha256 | 6 | 6 | 6 | 6 | 0 | 0 | 0 |
| event-line | pcr4/data | 6 | 6 | 6 | 6 | 2 | 1 | 1 |
| event-line | pcr4/type | 6 | 6 | 6 | 6 | 0 | 0 | 0 |
| event-line | pcr4/delete | 6 | 6 | 6 | 6 | 0 | 0 | 0 |
| event-line | pcr12/sha256 | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| event-line | pcr12/data | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| event-line | pcr12/type | 8 | 8 | 8 | 8 | 0 | 0 | 0 |
| event-line | pcr12/delete | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| event-line | pcr13/sha256 | 3 | 0 | 0 | 3 | 0 | 0 | 0 |
| event-line | pcr13/data | 3 | 0 | 0 | 3 | 0 | 0 | 0 |
| event-line | pcr13/type | 3 | 3 | 3 | 3 | 0 | 0 | 0 |
| event-line | pcr13/delete | 3 | 0 | 0 | 3 | 0 | 0 | 0 |
| measured-line | pcr12/char | 16 | 0 | 0 | 16 | 0 | 0 | 0 |
| measured-line | pcr12/delete | 8 | 0 | 0 | 8 | 0 | 0 | 0 |
| measured-line | pcr13/char | 6 | 0 | 0 | 6 | 0 | 0 | 0 |
| measured-line | pcr13/delete | 3 | 1 | 0 | 3 | 0 | 0 | 0 |
| field-deletion | pcr | 6 | 0 | 0 | 6 | 0 | 0 | 0 |
| field-deletion | quote-attest | 2 | 2 | 2 | 2 | 0 | 0 | 0 |
| field-deletion | quote-sig-r | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| field-deletion | quote-sig-s | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| field-deletion | quote-pub-x | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| field-deletion | quote-pub-y | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| field-deletion | quote-qualifying | 2 | 0 | 0 | 2 | 0 | 0 | 0 |
| unread-line | cpuid | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| unread-line | pcr-bank | 4 | 4 | 4 | 4 | 0 | 0 | 0 |
| unread-line | quote-pcrs | 4 | 4 | 4 | 4 | 0 | 0 | 0 |
| unread-line | quote-public | 4 | 4 | 4 | 4 | 0 | 0 | 0 |
| unread-line | quote-retries | 4 | 4 | 4 | 4 | 3 | 3 | 3 |
| unread-line | quote-key | 4 | 4 | 4 | 4 | 0 | 0 | 0 |
| unread-line | header | 4 | 2 | 2 | 4 | 0 | 0 | 0 |
| cosmetic | crlf-all | 2 | 2 | 2 | 2 | 2 | 0 | 0 |
| cosmetic | no-final-newline | 2 | 2 | 2 | 2 | 2 | 0 | 0 |
| cosmetic | trailing-space | 10 | 4 | 4 | 10 | 0 | 0 | 0 |
| cosmetic | uppercase-hex | 10 | 10 | 10 | 10 | 10 | 0 | 0 |
| cosmetic | leading-zero-bytes | 4 | 4 | 4 | 4 | 4 | 0 | 0 |
| sig-malleability | sig-s=n-s | 2 | 2 | 2 | 2 | 2 | 2 | 0 |

## 4. The seven SAFE-01 findings, mutant by mutant

| finding | mutants | before F1 accepted | before F2 accepted | after D accepted | after T accepted | after L accepted |
|---|---|---|---|---|---|---|
| 1 fail-open quote (quote-attest deleted or space-padded) | 4 | 4 | 4 | 0 | 0 | 0 |
| 2 receipt ignored when passed positionally (S1: tampered RECEIPT.TXT, genuine ATTEST.TXT) | 32 | 32 | 0 | 0 | 0 | 0 |
| 3 PCR 4 event-log edits never replayed | 24 | 24 | 24 | 2 | 1 | 1 |
| 4 type= of PCR 12/13 events unchecked | 11 | 11 | 11 | 0 | 0 | 0 |
| 5 unread quote-pcrs / quote-public / quote-retries / quote-key lines | 16 | 16 | 16 | 3 | 3 | 3 |
| 6 ECDSA malleability s -> n-s | 2 | 2 | 2 | 2 | 2 | 0 |
| 7 re-sign with a software key, SAFE-01 S2 (quote-public left as the TPM key) | 2 | 2 | 2 | 0 | 0 | 0 |
| 7b re-sign with a software key, new S3 (internally consistent forgery) | 2 | n/a | n/a | 2 | 0 | 0 |
| 7c (new, S4) self-consistent measured/event/pcr claim about PCR 14, which the quote does not select | 2 | 2 | 2 | 0 | 0 | 0 |
| (extra) last `measured pcr=13` line deleted | 3 | 1 | 0 | 0 | 0 | 0 |

Old positional form P on the findings sets: usage error for 349 of 349 mutants, 32 of 32 S1 receipts and 6 of 6 forgeries; accepted: 0.

### 4a. Residual accepted mutants in form T (verbatim ids), and why no verifier can reject them

| id | class / sub-field | what was changed | why accepted |
|---|---|---|---|
| H3event-line-010 | event-line / pcr4/data | event pcr=4 line 11: data char 88 0->8 | the data field of the EV_EFI_BOOT_SERVICES_APPLICATION event (image address, device path) is informational: PCR 4 is extended with the PE image hash, not with the data; no digest covers it. `--efi` binds the digest and the image length / link address; the flipped nibble here lies outside those fields. |
| H3unread-line-001 | unread-line / cpuid | cpuid char 37 P->C | the `cpuid` line is in no PCR and not in the quote; it is unauthenticated metadata. Closing this needs the unikernel to measure it (a change in aegis-uefi, not done here). |
| H3unread-line-002 | unread-line / cpuid | cpuid char 50 5->9 | the `cpuid` line is in no PCR and not in the quote; it is unauthenticated metadata. Closing this needs the unikernel to measure it (a change in aegis-uefi, not done here). |
| H3unread-line-009 | unread-line / quote-retries | quote-retries char 0 1->4 | a counter the unikernel prints outside the signed data; any integer in 0..16 is plausible. Only the format and range are checked. |
| H3unread-line-010 | unread-line / quote-retries | quote-retries char 0 1->0 | a counter the unikernel prints outside the signed data; any integer in 0..16 is plausible. Only the format and range are checked. |
| H3sig-malleability-001 | sig-malleability / sig-s=n-s | quote-sig-s replaced by n-s (the other valid ECDSA signature) | a valid second signature over the same signed bytes; it cannot be told from a genuine high-s signature. See section 6. |
| H3unread-line-015 | unread-line / cpuid | cpuid char 27 Q->I | the `cpuid` line is in no PCR and not in the quote; it is unauthenticated metadata. Closing this needs the unikernel to measure it (a change in aegis-uefi, not done here). |
| H3unread-line-016 | unread-line / cpuid | cpuid char 49 .->4 | the `cpuid` line is in no PCR and not in the quote; it is unauthenticated metadata. Closing this needs the unikernel to measure it (a change in aegis-uefi, not done here). |
| H3unread-line-024 | unread-line / quote-retries | quote-retries char 0 1->3 | a counter the unikernel prints outside the signed data; any integer in 0..16 is plausible. Only the format and range are checked. |
| H3sig-malleability-002 | sig-malleability / sig-s=n-s | quote-sig-s replaced by n-s (the other valid ECDSA signature) | a valid second signature over the same signed bytes; it cannot be told from a genuine high-s signature. See section 6. |

Residual accepted mutants in T: 10; of these in L (adds `--reject-high-s`): 8. By sub-field: pcr4/data: 1, cpuid: 4, quote-retries: 3, sig-s=n-s: 2.

### 4b. Cosmetic variants (semantically equivalent encodings; reported separately, as in SAFE-01)

| sub-field | mutants | before F1 accepted | before F2 accepted | after D accepted | after T accepted |
|---|---|---|---|---|---|
| crlf-all | 2 | 2 | 2 | 2 | 0 |
| no-final-newline | 2 | 2 | 2 | 2 | 0 |
| trailing-space | 10 | 4 | 4 | 0 | 0 |
| uppercase-hex | 10 | 10 | 10 | 10 | 0 |
| leading-zero-bytes | 4 | 4 | 4 | 4 | 0 |

D keeps accepting encodings that decode to the same bytes (CRLF, missing final newline, upper-case hex, extra leading zero bytes of r/s); `--strict` rejects every non-canonical form. Trailing spaces are rejected in every mode because the line then no longer parses.

### 4c. Exhaustive single-byte substitution (additional, not in the pre-registration)

Every byte position of `qemu_calc/ATTEST.TXT` and `qemu_self/ATTEST.TXT` was replaced once (hex digit -> next hex digit, other digit/letter -> next of its class, anything else -> `X`, newline -> space) and the result run through form T (`h3_byteflip.tsv`): 7895 mutants, 404 accepted, 0 anomalies. Controls: the unmodified files are accepted by T (section 3).

| file | line | bytes tested | accepted by T | accepted columns (0-based, in the line) | why |
|---|---|---|---|---|---|
| qemu_calc | cpuid | 101 | 41 | 13-24, 33-57, 67, 75, 86, 99 | informational CPU identity string, in no PCR and not in the quote |
| qemu_calc | event pcr=4 #2 | 302 | 160 | 109-124, 157-300 | image-load event data outside the fields `--efi` binds (see 4a) |
| qemu_calc | quote-retries | 16 | 1 | 14 | unsigned counter, any digit is in range |
| qemu_self | cpuid | 101 | 41 | 13-24, 33-57, 67, 75, 86, 99 | informational CPU identity string, in no PCR and not in the quote |
| qemu_self | event pcr=4 #2 | 302 | 160 | 109-124, 157-300 | image-load event data outside the fields `--efi` binds (see 4a) |
| qemu_self | quote-retries | 16 | 1 | 14 | unsigned counter, any digit is in range |

Lines in which every substituted byte was rejected: 54 of 60 (file, line) pairs. Total bytes in the two files: 7895; rejected: 7459; accepted: 404 (of which in the lines named above: 404).

## 5. Tampered receipts (S1), software-key forgeries (S2, S3) and an unattested claim (S4)

| receipt field changed | receipts | before F1 accepted | before F2 accepted | after P: usage error | after D accepted | after T accepted |
|---|---|---|---|---|---|---|
| chain | 8 | 8 | 0 | 8 | 0 | 0 |
| cis-digest | 8 | 8 | 0 | 8 | 0 | 0 |
| prompt-hex | 8 | 8 | 0 | 8 | 0 | 0 |
| token-ids | 8 | 8 | 0 | 8 | 0 | 0 |

| id | base | before F1 | before F2 | after P | after D | after T | after L | first failed checks in T |
|---|---|---|---|---|---|---|---|---|
| S2-pcr13-line-edit | qemu_calc | ACCEPT | ACCEPT | REJECT_USAGE | REJECT | REJECT | REJECT | quote-public is a fixed restricted ECC P-256 ECDSA/SHA-256 signing key whose point == quote-pub-x/y (unique point != quote-pub-x/quote-pub-y): FAIL || quote ECDSA-P256/SHA-256 signature over TPMS_ATTEST (openssl): Verification failure FAIL || QUOTE VERIFY FAIL |
| S2-receipt-chain-edit | qemu_self | ACCEPT | ACCEPT | REJECT_USAGE | REJECT | REJECT | REJECT | quote-public is a fixed restricted ECC P-256 ECDSA/SHA-256 signing key whose point == quote-pub-x/y (unique point != quote-pub-x/quote-pub-y): FAIL || quote ECDSA-P256/SHA-256 signature over TPMS_ATTEST (openssl): Verification failure FAIL || QUOTE VERIFY FAIL |
| S3-pcr13-line-edit | qemu_calc | ACCEPT (re-measured) | ACCEPT (re-measured) | REJECT_USAGE | ACCEPT | REJECT | REJECT | quote signer == pinned key (3fad67d3224ab19b..): FAIL || QUOTE VERIFY FAIL |
| S3-receipt-chain-edit | qemu_self | ACCEPT (re-measured) | ACCEPT (re-measured) | REJECT_USAGE | ACCEPT | REJECT | REJECT | quote signer == pinned key (9a6913281eb374ab..): FAIL || QUOTE VERIFY FAIL |
| S4-pcr14-claim-qemu_calc | qemu_calc | ACCEPT (re-measured) | ACCEPT (re-measured) | REJECT_USAGE | REJECT | REJECT | REJECT | every PCR the file reports [4, 12, 13, 14] is inside the quote selection [4, 12, 13] (nothing is claimed that the quote does not cover): FAIL || QUOTE VERIFY FAIL |
| S4-pcr14-claim-qemu_self | qemu_self | ACCEPT (re-measured) | ACCEPT (re-measured) | REJECT_USAGE | REJECT | REJECT | REJECT | every PCR the file reports [4, 12, 13, 14] is inside the quote selection [4, 12, 13] (nothing is claimed that the quote does not cover): FAIL || QUOTE VERIFY FAIL |

S4 (new here, also an addition to the pre-registration) appends a self-consistent measured/event/pcr claim about PCR 14. The quote selects only PCRs 4, 12 and 13, so nothing signed covers PCR 14; the pre-hardening verifier replays it and passes it, the hardened one fails any file that reports a PCR outside the quote selection (D accepts 0 of 2, T accepts 0 of 2; before, re-measured: F1 2 and F2 2 accepted).

S2 is SAFE-01's forgery: re-signed with a software key but `quote-public` and the signed qualifiedSigner still describe the TPM key, so the hardened default form D already rejects it (first failed check shown in the D column of `h3_forgery_rerun.tsv`). S3 (new here, labelled as an addition to the pre-registration) rewrites those too and is internally consistent: D accepts it, and only the pin (`--expect-pubkey`) rejects it. That is the whole value of the pin: without it the quote proves consistency with some P-256 key, not which TPM.

D on S2: S2-pcr13-line-edit: quote-public is a fixed restricted ECC P-256 ECDSA/SHA-256 signing key whose point == quote-pub-x/y (unique point != quote-pub-x/quote-pub-y): FAIL || quote ECDSA-P256/SHA-256 signature over TPMS_ATTEST (openssl): Verification failure FAIL || QUOTE VERIFY FAIL; S2-receipt-chain-edit: quote-public is a fixed restricted ECC P-256 ECDSA/SHA-256 signing key whose point == quote-pub-x/y (unique point != quote-pub-x/quote-pub-y): FAIL || quote ECDSA-P256/SHA-256 signature over TPMS_ATTEST (openssl): Verification failure FAIL || QUOTE VERIFY FAIL

## 6. Hypotheses, deviations and what is not covered

- **HA1.** Verdict: PARTLY SUPPORTED. Rejected by T, per SAFE-01 finding: 1 fail-open quote 4 of 4; 2 receipt ignored (S1) 32 of 32; 3 PCR 4 edits 23 of 24; 4 type= of PCR 12/13 events 11 of 11; 5 unread quote lines 13 of 16 (quote-pcrs / quote-public / quote-key: 12 of 12); 6 malleation 0 of 2 (by L: 2 of 2); 7 software-key re-sign 2 of 2 (S2) and 2 of 2 (S3, internally consistent; D rejects 0 of 2). Findings 1, 2, 4 and 7 are closed completely in T. Finding 3 leaves 1 mutant (device-path bytes of the image-load event, in no digest), finding 5 leaves 3 (the `quote-retries` counter, outside the signature), finding 6 is closed only by the opt-in `--reject-high-s` and then only for low-s originals. `cpuid` (4 mutants, SAFE-01 "unread" class but not one of the seven findings) is likewise unauthenticated.
- **HA2.** Verdict: SUPPORTED. 8 of 8 final boots pass form T; 15 of 15 files on disk pass D and 15 of 15 pass `--strict`.
- **Deviation from the task text, (f) low-s.** The task asked to reject s > n/2 under `--strict` and, if any genuine file is high-s, to make the check `--strict`-only. Empirically 4 of the 8 final boots (5 of 15 files on disk) are high-s: libtpms/swtpm does not normalise s. A `--strict` that rejects high-s would fail 4 genuine boots in `finalize.sh`, which the same task requires to use `--strict`. So `--strict` does not include the check; `--reject-high-s` is a separate opt-in flag (form L). It does not stop malleation in general: a genuine high-s quote can be turned into a valid low-s quote by anyone, and L accepts that. Malleability does not let anyone sign new content (the signed TPMS_ATTEST is unchanged); it only matters if a signature is used as an identifier.
- **Deviation, (g) pin source.** The task said to take the key from the first boot of the same swtpm state. The 8 boots do not share a state (8 distinct keys), so that rule has nothing to pin to. `finalize.sh` instead re-derives each boot's key from that boot's own swtpm state with `labs/tools/ak_from_swtpm.sh`; the pin never comes from the ATTEST.TXT being checked. `AEGIS_AK_PIN` overrides it with an enrolled key; `attest_verify.py --print-pubkey` gives the trust-on-first-use alternative for a file you have not seen before.
- **Addition, `--efi`.** Not asked for. PCR 4's third digest equals the Authenticode SHA-256 of `aegis-uefi-gateway-qemutest.efi` in all 8 boots, so `finalize.sh` passes `--efi $EFI` and thereby also checks which binary booted (and, with it, the image length and link address in the logged event data). Optional flag.
- **Addition, quote-selection check.** A file that reports a PCR the quote does not select (a `pcr`, `measured` or `event` line for PCR 14, say) now fails: that claim would be consistent with itself and covered by no signature (S4).
- **Addition, `finalize.sh` exit status.** It now exits 1 after its summary if any boot is not verified (attestation failed, ATTEST.TXT/RECEIPT.TXT missing, or no pin could be derived). Before, a failed or skipped check was invisible.
- **Not covered, stated plainly.** `cpuid`, `quote-retries`, the clock/reset counters inside TPMS_ATTEST, and the data field of the EV_EFI_BOOT_SERVICES_APPLICATION event are not bound by any digest or signature (they are checked for format only). `RECEIPT2.TXT` of the three tool-use boots is not passed to attest_verify.py (its chain is in the second PCR 13 line, which the replay covers, but nothing compares the file). `swtpm` is a software TPM with no EK certificate: a pin proves "the TPM whose owner seed the host holds", not hardware provenance (LAB-04 limitation 5 still applies on real iron).

## 7. Files in this directory

- `RESULT.md`
- `attest_verify_before.py`
- `final_boots_controls.json`
- `final_boots_keys.tsv`
- `final_boots_recheck.log`
- `finalize_before.sh`
- `genuine_all.tsv`
- `h3_byteflip.tsv`
- `h3_forgery_rerun.tsv`
- `h3_rerun.tsv`
- `h3_s1_rerun.tsv`
- `h3_s3_forgeries.tar.gz`
- `provenance.txt`
- `run_harden.log`
