# SAFE-01 RESULT: tamper-evidence of witness receipts, model bytes and TPM attestation (LAB-09)

Every number below is computed by `labs/safe/safe01_tamper.py report` from the logs saved next to this file. Rule A: no timing or rate was recorded.

## 0. Findings at a glance (all numbers computed from the logs in this directory)

1. **Receipt field-value tampering is caught.** 0 of 5045 mutants in C01-C07, C09, C10 were accepted by `cis_witness verify`; 4873 were clean `VERIFY FAIL`/`FAIL artifact`, 172 were panics (crash-rejects). Positive control: 11 of 11 unmodified receipts verify.
2. **Accepted mutation, registered class C08 (line reorder): 520 of 520 accepted.** The verifier parses by key, so line order is not part of what it checks. No field value changes, so this is outside H1's "single-field" wording, but it is an accepted mutation of the receipt file.
3. **Receipt parser leniency (unregistered probes).** `prompt-toks` and `gen-toks` lines are never read: 73 of 73 and 73 of 73 mutants accepted (including deleting the line). Header line altered or deleted: 43 of 43. Unknown line appended: 11 of 11. Duplicate key with a bogus earlier line (last one wins): 52 of 55 accepted. Non-canonical numbers/hex (`+25`, `025`, `+a`, upper-case prompt-hex): 66 of 99 accepted. The semantic content of those receipts is unchanged, but the bytes differ.
4. **Cosmetic changes (C11, reported separately): 242 of 396 accepted** (CRLF on any line or on all, final newline removed, blank line appended, and trailing space/tab on these lines only: AEGIS-WITNESS x11, gen-toks x11, prompt-hex x11, prompt-toks x11). 154 were rejected (trailing whitespace on other fields), 44 of them by panic. Trailing whitespace on the `prompt-hex` line is accepted because the hex decoder drops an odd trailing character.
5. **The whole-file hash in the TPM quote catches what the receipt verifier ignores, but only if `--receipt` is used.** Of 48 accepted receipt mutants re-run through `attest_verify.py`: F1 (positional receipt, as in finalize.sh) accepted 48; F2 (`--receipt`) accepted 0 and printed `quote qualifying == SHA-256(RECEIPT.TXT): FAIL` in 48. Receipt-side tamper test S1 (tampering RECEIPT.TXT, genuine ATTEST.TXT): F1 accepted 32 of 32, F2 accepted 0 of 32. **The `finalize.sh` line `attest_verify.py ATTEST.TXT RECEIPT.TXT` therefore never checks the receipt.**
6. **H2 (weights).** 14 of 20 one-byte mutants of MODEL.SAF changed at least one canary decode digest; 6 did not change any of the four 16-token digests. Only the `calc` canary ever changed (self: 0, calc: 28, lookup: 0, abstain: 0 changed decodes out of 40 per canary across the byte and bit sets). All 300 of 300 original-minted receipts failed against the mutated MODEL.SAF, because the artifact hash line no longer matches.
7. **H3 (attestation).** Rejected without exception: altered `pcr` values (48 of 48), `quote-attest` bytes (68 of 68), signature r/s (24 of 24), qualifying data (16 of 16), public key (16 of 16). Accepted: PCR 4 event-log lines (24 of 24; PCR 4 does replay from its own three event digests in both ATTEST files, [True, True], but attest_verify.py does not perform that replay), the `type=` field of PCR 12/13 events (11 of 11), deleting the `quote-attest` line (2 of 18 field deletions; verifier prints `quote: none in file` and exits 0), and 4 mutants in total that exit 0 with no `QUOTE VERIFY PASS` line (a trailing space on the `quote-attest` line does the same). Deleting a `measured pcr=13` line: F1 accepted 1 of 3, F2 accepted 0 (F1-accepted: H3measured-line-030 qemu_self measured pcr=13 line 6 deleted; with no measured line left for PCR 13, nothing is replayed for it). Signature malleability `s -> n-s`: 2 of 2 accepted.
8. **The quote proves consistency, not origin.** Re-signing an edited ATTEST.TXT with a software-generated P-256 key (no TPM; case 1 edits only the PCR 13 verdict text, case 2 also edits the chain in RECEIPT.TXT and its qualifying digest) was accepted by F1 in 2 of 2 cases and by F2 in 2 of 2; `cis_witness verify` on the receipt that goes with each case accepted 1 (the unedited receipt) and rejected 1 (the chain-edited receipt). The verifier has no pinned attestation key (LAB-04 limitation 5 says the same for the swtpm AK).

## 1. How this was run (exact commands, scoring rules)

```
cd /home/user/Ranger3143/labs/safe
python3 -I safe01_tamper.py h1      # receipt mutations   -> h1_manifest.tsv, h1_results.tsv, h1_generation.json
python3 -I safe01_tamper.py h2      # weight byte flips   -> h2_mutations.tsv, h2_decode.tsv, h2_decode_raw.log, h2_verify.tsv, h2_receipts/
python3 -I safe01_tamper.py h3      # ATTEST mutations    -> h3_results.tsv, h3_s1_receipt_side.tsv, h3_s2_forgery.tsv
python3 -I safe01_tamper.py report  # writes this RESULT.md from the logs only
```

Per-mutant commands (as in `model/demo-operator/finalize.sh`, run with `nice -n 5`, `AEGIS_THREADS=1`, `OMP_NUM_THREADS=1`, 2 parallel workers; `AEGIS_THREADS=2` when the 2B artifacts are involved):

```
H1: cis_witness verify <MODEL.SAF> <EMBED.BIN> <VOCAB.BIN> <mutant receipt>
H2: cis_decode <MODEL.SAF> <EMBED.BIN> <VOCAB.BIN> 16 "<canary prompt>"      cis_witness gen ... 16 "<canary>"      cis_witness verify ...
H3: F1 = python3 -I labs/tools/attest_verify.py <ATTEST> <RECEIPT>                     (the form in finalize.sh and in the task text)
    F2 = python3 -I labs/tools/attest_verify.py <ATTEST> --receipt <RECEIPT> --artifacts <op12k artifacts dir>
```

Scoring rules, fixed in the script before the first run:
- H1 ACCEPT = exit code 0 and a stdout line starting `VERIFY PASS`. REJECT_CLEAN = exit code 1 and a line starting `VERIFY FAIL` or `FAIL artifact`. REJECT_CRASH = anything else (panic exit 101, exit 2, signal): not accepted, but the verifier crashed instead of answering. TIMEOUT = inconclusive, excluded from rates. Detection rate = (REJECT_CLEAN + REJECT_CRASH) / N.
- A mutant counts once per (class, source receipt, artifacts, mutant bytes); mutants byte-identical to the source receipt are dropped (counts in section 2). Sampling is seeded (`LAB09-SAFE01-20261008/<class>`), so the manifest is reproducible.
- H3 ACCEPT = `attest_verify.py` exit code 0 (any `FAIL`, `MISSING`, `ERROR` or a parse failure gives exit 1 or 2). `quote line` records whether `QUOTE VERIFY PASS` was printed.
- H2 digest changed = the `CIS_DECODE digest=` of the mutated model differs from the original model for the same canary prompt (16 greedy tokens).

Inputs: the 11 receipts `labs/logs/opmodel/final_step12000/qemu_*/RECEIPT*.TXT`; the op12k artifacts (sha256 below); ATTEST.TXT of `qemu_calc` and `qemu_self`.

| set | file | bytes | sha256 |
|---|---|---|---|
| A op12k final_step12000 (receipts minted against this) | MODEL.SAF | 3197143 | `a44e48965c641b81994a670001c76a8bebd38857f9455cc5008acac8d2b2897a` |
| A op12k final_step12000 (receipts minted against this) | EMBED.BIN | 9437184 | `8cbcd6b69df03539cd4638440fb903910325b7f6853349c5bb5778e413fafef0` |
| A op12k final_step12000 (receipts minted against this) | VOCAB.BIN | 253377 | `a4cafc9649488987a8eb053476d389bd9a675405c51bfc42ebded546ae64eb17` |
| B op model step2300 | MODEL.SAF | 3197143 | `b7b357af673770b7654d02458de63417bda493cdf1e58f9f6175e5ad248efeaf` |
| B op model step2300 | EMBED.BIN | 9437184 | `6dd998538d0e5ebde119b337ec5d305f68c4f232aa9ba5ca7f7895958ca74a04` |
| B op model step2300 | VOCAB.BIN | 253377 | `a4cafc9649488987a8eb053476d389bd9a675405c51bfc42ebded546ae64eb17` |
| C op model step_early | MODEL.SAF | 3197143 | `9e74d53d6e39804e440676e0f2e2fb4fced414081ede29174a60a9d763c09ff7` |
| C op model step_early | EMBED.BIN | 9437184 | `3ff917ea44060002e5bb8103f958740daa26c1301e56d3445cfeed1368ced117` |
| C op model step_early | VOCAB.BIN | 253377 | `a4cafc9649488987a8eb053476d389bd9a675405c51bfc42ebded546ae64eb17` |
| D BitNet-b1.58-2B-4T (bitnet2b_fixed) | MODEL.SAF | 521953186 | `1101e472e41a012e4b1efdc124511461307f4e0e1b540a8e45c24d3d33e0c9eb` |
| D BitNet-b1.58-2B-4T (bitnet2b_fixed) | EMBED.BIN | 257310720 | `e32b99a25e345c65054f36dedf40329a89513cdf1a8195db64fc440fd364e077` |
| D BitNet-b1.58-2B-4T (bitnet2b_fixed) | VOCAB.BIN | 1759936 | `5bde1b0355ef99c6875190ebfff081d985ca48977ae9269e3477f5cc2d97d9ae` |

Binaries: 79107c6b57101910c8fa5904e473279cc823c6db82dd3e0c0d4e0e012bfd5309  /home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/cis_witness; bd91b6db16d450d34958d6880130e5fffc318037e728ede6b89d5984cc0e9677  /home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/cis_decode

## 2. H1: receipt mutations through `cis_witness verify`

Positive control: 11 of 11 unmodified receipts verify (ACCEPT). The harness is valid only if this is 11 of 11.

| class | mutants | ACCEPT | REJECT_CLEAN | REJECT_CRASH | TIMEOUT | detection rate |
|---|---|---|---|---|---|---|
| C01 token-ids (flip / drop / append / swap) | 706 | 0 | 706 | 0 | 0 | 100.00% |
| C02 prompt-hex (one nibble) | 520 | 0 | 379 | 141 | 0 | 100.00% |
| C03 cis-digest (one hex char) | 520 | 0 | 520 | 0 | 0 | 100.00% |
| C04 chain (one hex char) | 520 | 0 | 520 | 0 | 0 | 100.00% |
| C05 maxtok (+-1, and wider +-d) | 520 | 0 | 520 | 0 | 0 | 100.00% |
| C06 model/embed/vocab hash lines (one hex char) | 520 | 0 | 520 | 0 | 0 | 100.00% |
| C07 truncation (drop last k lines; byte cut) | 520 | 0 | 489 | 31 | 0 | 100.00% |
| C08 line reorder | 520 | 520 | 0 | 0 | 0 | 0.00% |
| C09 cross-receipt swap | 634 | 0 | 634 | 0 | 0 | 100.00% |
| C10 artifact swap (other model artifacts; relabel; 1-byte-mutated MODEL.SAF) | 585 | 0 | 585 | 0 | 0 | 100.00% |
| C11 cosmetic (trailing whitespace, CRLF, final newline) - REPORTED SEPARATELY | 396 | 242 | 110 | 44 | 0 | 38.89% |
| U1 UNREGISTERED probe: prompt-toks line | 73 | 73 | 0 | 0 | 0 | 0.00% |
| U2 UNREGISTERED probe: gen-toks line | 73 | 73 | 0 | 0 | 0 | 0.00% |
| U3 UNREGISTERED probe: header line | 43 | 43 | 0 | 0 | 0 | 0.00% |
| U4 UNREGISTERED probe: unknown line appended | 11 | 11 | 0 | 0 | 0 | 0.00% |
| U5 UNREGISTERED probe: duplicate key | 110 | 52 | 52 | 6 | 0 | 52.73% |
| U6 UNREGISTERED probe: non-canonical encodings | 99 | 66 | 33 | 0 | 0 | 33.33% |

Dropped while generating: identical-to-source = {"C09": 4}; duplicate mutants = {"C01": 44, "C02": 11, "C03": 50, "C04": 16, "C06": 3, "C05": 518, "C07": 25, "C09": 22, "U3": 1}.

### 2a. Sub-class breakdown

| class | sub-class | mutants | ACCEPT | REJECT_CLEAN | REJECT_CRASH | TIMEOUT |
|---|---|---|---|---|---|---|
| C01 | append | 100 | 0 | 100 | 0 | 0 |
| C01 | drop | 206 | 0 | 206 | 0 | 0 |
| C01 | flip | 200 | 0 | 200 | 0 | 0 |
| C01 | swap | 200 | 0 | 200 | 0 | 0 |
| C02 | nibble | 520 | 0 | 379 | 141 | 0 |
| C03 | nibble | 520 | 0 | 520 | 0 | 0 |
| C04 | nibble | 520 | 0 | 520 | 0 | 0 |
| C05 | pm1 | 22 | 0 | 22 | 0 | 0 |
| C05 | wide | 498 | 0 | 498 | 0 | 0 |
| C06 | embed | 174 | 0 | 174 | 0 | 0 |
| C06 | model | 178 | 0 | 178 | 0 | 0 |
| C06 | vocab | 168 | 0 | 168 | 0 | 0 |
| C07 | bytes | 399 | 0 | 390 | 9 | 0 |
| C07 | lines | 121 | 0 | 99 | 22 | 0 |
| C08 | adjacent | 110 | 110 | 0 | 0 | 0 |
| C08 | permutation | 410 | 410 | 0 | 0 | 0 |
| C09 | chain | 110 | 0 | 110 | 0 | 0 |
| C09 | cis-digest | 110 | 0 | 110 | 0 | 0 |
| C09 | maxtok | 88 | 0 | 88 | 0 | 0 |
| C09 | prompt-hex | 110 | 0 | 110 | 0 | 0 |
| C09 | token-ids | 110 | 0 | 110 | 0 | 0 |
| C09 | token-ids+gen-toks | 106 | 0 | 106 | 0 | 0 |
| C10 | relabel-B | 11 | 0 | 11 | 0 | 0 |
| C10 | relabel-C | 11 | 0 | 11 | 0 | 0 |
| C10 | relabel-D | 2 | 0 | 2 | 0 | 0 |
| C10 | swap-AAD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-ABA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-ABD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-ACA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-ACD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-ADA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-ADD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-BAA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-BAD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-BBA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-BBD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-BCA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-BCD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-BDA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-BDD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-CAA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-CAD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-CBA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-CBD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-CCA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-CCD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-CDA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-CDD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-DAA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-DAD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-DBA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-DBD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-DCA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-DCD | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-DDA | 11 | 0 | 11 | 0 | 0 |
| C10 | swap-DDD | 11 | 0 | 11 | 0 | 0 |
| C10 | weight-1byte | 220 | 0 | 220 | 0 | 0 |
| C11 | blank-line-end | 11 | 11 | 0 | 0 | 0 |
| C11 | crlf-all | 11 | 11 | 0 | 0 | 0 |
| C11 | crlf-one-line | 121 | 121 | 0 | 0 | 0 |
| C11 | no-final-newline | 11 | 11 | 0 | 0 | 0 |
| C11 | trailing-space | 121 | 44 | 55 | 22 | 0 |
| C11 | trailing-tab | 121 | 44 | 55 | 22 | 0 |
| U1 | delete-line | 11 | 11 | 0 | 0 | 0 |
| U1 | pm1 | 22 | 22 | 0 | 0 | 0 |
| U1 | random | 40 | 40 | 0 | 0 | 0 |
| U2 | delete-line | 11 | 11 | 0 | 0 | 0 |
| U2 | pm1 | 22 | 22 | 0 | 0 | 0 |
| U2 | random | 40 | 40 | 0 | 0 | 0 |
| U3 | header-char | 32 | 32 | 0 | 0 | 0 |
| U3 | header-deleted | 11 | 11 | 0 | 0 | 0 |
| U4 | unknown-line-appended | 11 | 11 | 0 | 0 | 0 |
| U5 | dup-bogus-first | 55 | 52 | 0 | 3 | 0 |
| U5 | dup-bogus-last | 55 | 0 | 52 | 3 | 0 |
| U6 | plus-in-prompt-hex | 11 | 11 | 0 | 0 | 0 |
| U6 | plus-maxtok | 11 | 11 | 0 | 0 | 0 |
| U6 | plus-token-id | 11 | 11 | 0 | 0 | 0 |
| U6 | uppercase-chain | 11 | 0 | 11 | 0 | 0 |
| U6 | uppercase-cis-digest | 11 | 0 | 11 | 0 | 0 |
| U6 | uppercase-model | 11 | 0 | 11 | 0 | 0 |
| U6 | uppercase-prompt-hex | 11 | 11 | 0 | 0 | 0 |
| U6 | zero-maxtok | 11 | 11 | 0 | 0 | 0 |
| U6 | zero-token-id | 11 | 11 | 0 | 0 | 0 |

### 2b. Accepted mutants (findings), verbatim

- **C08 line reorder**: 520 of 520 accepted; by sub-class: adjacent=110, permutation=410
  - `C08-0001` (adjacent) source `qemu_abstain/RECEIPT.TXT`: swap lines 0,1 (model <-> AEGIS-WITNESS)  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `C08-0111` (permutation) source `qemu_calc_words/RECEIPT.TXT`: line order 1,6,3,8,5,9,7,0,2,4,10  -> exit 0, `VERIFY PASS — replay reproduced 8 tokens, the token digest, and the full logit chain bit-for-bit`
- **C11 cosmetic (trailing whitespace, CRLF, final newline) - REPORTED SEPARATELY**: 242 of 396 accepted; by sub-class: blank-line-end=11, crlf-all=11, crlf-one-line=121, no-final-newline=11, trailing-space=44, trailing-tab=44
  - `C11-0001` (trailing-space) source `qemu_abstain/RECEIPT.TXT`: trailing-space on line 0 (AEGIS-WITNESS)  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `C11-0002` (trailing-tab) source `qemu_abstain/RECEIPT.TXT`: trailing-tab on line 0 (AEGIS-WITNESS)  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `C11-0003` (crlf-one-line) source `qemu_abstain/RECEIPT.TXT`: CRLF on line 0 (AEGIS-WITNESS) only  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `C11-0034` (crlf-all) source `qemu_abstain/RECEIPT.TXT`: every line ends CRLF  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `C11-0035` (no-final-newline) source `qemu_abstain/RECEIPT.TXT`: final newline removed  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `C11-0036` (blank-line-end) source `qemu_abstain/RECEIPT.TXT`: one blank line appended  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
- **U1 UNREGISTERED probe: prompt-toks line**: 73 of 73 accepted; by sub-class: delete-line=11, pm1=22, random=40
  - `U1-0001` (delete-line) source `qemu_abstain/RECEIPT.TXT`: prompt-toks line deleted  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U1-0002` (pm1) source `qemu_abstain/RECEIPT.TXT`: prompt-toks 12->11  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U1-0034` (random) source `qemu_calc_words/RECEIPT2.TXT`: prompt-toks 27->363  -> exit 0, `VERIFY PASS — replay reproduced 7 tokens, the token digest, and the full logit chain bit-for-bit`
- **U2 UNREGISTERED probe: gen-toks line**: 73 of 73 accepted; by sub-class: delete-line=11, pm1=22, random=40
  - `U2-0001` (delete-line) source `qemu_abstain/RECEIPT.TXT`: gen-toks line deleted  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U2-0002` (pm1) source `qemu_abstain/RECEIPT.TXT`: gen-toks 25->24  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U2-0034` (random) source `qemu_lookup/RECEIPT2.TXT`: gen-toks 23->375  -> exit 0, `VERIFY PASS — replay reproduced 23 tokens, the token digest, and the full logit chain bit-for-bit`
- **U3 UNREGISTERED probe: header line**: 43 of 43 accepted; by sub-class: header-char=32, header-deleted=11
  - `U3-0001` (header-deleted) source `qemu_abstain/RECEIPT.TXT`: header line deleted  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U3-0002` (header-char) source `qemu_abstain/RECEIPT.TXT`: header char 8 -> #  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
- **U4 UNREGISTERED probe: unknown line appended**: 11 of 11 accepted; by sub-class: unknown-line-appended=11
  - `U4-0001` (unknown-line-appended) source `qemu_abstain/RECEIPT.TXT`: line 'x-note hello' appended  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
- **U5 UNREGISTERED probe: duplicate key**: 52 of 110 accepted; by sub-class: dup-bogus-first=52
  - `U5-0001` (dup-bogus-first) source `qemu_abstain/RECEIPT.TXT`: duplicate chain: bogus line before the original  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
- **U6 UNREGISTERED probe: non-canonical encodings**: 66 of 99 accepted; by sub-class: plus-in-prompt-hex=11, plus-maxtok=11, plus-token-id=11, uppercase-prompt-hex=11, zero-maxtok=11, zero-token-id=11
  - `U6-0001` (uppercase-prompt-hex) source `qemu_abstain/RECEIPT.TXT`: prompt-hex in upper case  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U6-0002` (plus-in-prompt-hex) source `qemu_abstain/RECEIPT.TXT`: prompt-hex byte 0a written as +a at hex pos 82  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U6-0003` (plus-maxtok) source `qemu_abstain/RECEIPT.TXT`: maxtok +25  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U6-0004` (zero-maxtok) source `qemu_abstain/RECEIPT.TXT`: maxtok 025  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U6-0005` (zero-token-id) source `qemu_abstain/RECEIPT.TXT`: first token id 0309  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`
  - `U6-0006` (plus-token-id) source `qemu_abstain/RECEIPT.TXT`: first token id +309  -> exit 0, `VERIFY PASS — replay reproduced 25 tokens, the token digest, and the full logit chain bit-for-bit`

Verbatim accepted file `C08-0111` (source `qemu_calc_words/RECEIPT.TXT`, all eleven lines present, order permuted; `cis_witness verify` printed `VERIFY PASS — replay reproduced 8 tokens, the token digest, and the full logit chain bit-for-bit`):

```
model a44e48965c641b81994a670001c76a8bebd38857f9455cc5008acac8d2b2897a
prompt-toks 11
vocab a4cafc9649488987a8eb053476d389bd9a675405c51bfc42ebded546ae64eb17
token-ids 473,8,796,1829,700,1675,367,199
prompt-hex 513a204d756c7469706c79203336352062792032342e0a413a
cis-digest 1551d14612504825
gen-toks 8
AEGIS-WITNESS v1-CIS
embed 8cbcd6b69df03539cd4638440fb903910325b7f6853349c5bb5778e413fafef0
maxtok 8
chain fe59fefa91546f2a1333b8b1a72a5e765109bd422fe10c0b945cff6e2e5c8407
```

### 2c. Rejections that were crashes (panic text, first stderr line)

By class: C02=141, C07=31, C11=44, U5=6

- 147 x `cis_witness.rs line 180: w_prompt = String::from_utf8(unhex(v)).expect("prompt utf8");`
- 30 x `cis_witness.rs line 68: assert!(!prompt_ids.is_empty(), "prompt tokenized to nothing");`
- 23 x `cis_witness.rs line 178: "maxtok" => w_maxtok = v.parse().expect("maxtok"),`
- 22 x `cis_witness.rs line 186: .map(|s| s.parse().expect("token id"))`

### 2d. Accepted mutants vs the whole-file SHA-256 that the TPM quote binds

`ATTEST.TXT` `quote-qualifying` = SHA-256 of the exact bytes of `RECEIPT.TXT` (attest_verify.py F2 checks this). For each accepted mutant derived from a `RECEIPT.TXT` (not `RECEIPT2.TXT`, whose bytes are not bound whole-file) the script compares SHA-256(mutant) with that boot's `quote-qualifying`:

| class | accepted from bound RECEIPT.TXT | whole-file digest still equals quote-qualifying | whole-file digest differs (caught by F2) |
|---|---|---|---|
| C08 | 394 | 0 | 394 |
| C11 | 176 | 0 | 176 |
| U1 | 55 | 0 | 55 |
| U2 | 52 | 0 | 52 |
| U3 | 32 | 0 | 32 |
| U4 | 8 | 0 | 8 |
| U5 | 37 | 0 | 37 |
| U6 | 48 | 0 | 48 |

Measured, not inferred: the real `attest_verify.py` on a spread of up to 6 accepted mutants per class (those derived from a bound RECEIPT.TXT), against the matching boot's ATTEST.TXT (`h1_f2_crosscheck.tsv`):

| class | mutants run | F1 (positional receipt) accepted | F2 (`--receipt`) accepted | F2 printed `quote qualifying == SHA-256(RECEIPT.TXT): FAIL` |
|---|---|---|---|---|
| C08 | 6 | 6 | 0 | 6 |
| C11 | 6 | 6 | 0 | 6 |
| U1 | 6 | 6 | 0 | 6 |
| U2 | 6 | 6 | 0 | 6 |
| U3 | 6 | 6 | 0 | 6 |
| U4 | 6 | 6 | 0 | 6 |
| U5 | 6 | 6 | 0 | 6 |
| U6 | 6 | 6 | 0 | 6 |

## 3. H2: one-byte change in MODEL.SAF

MODEL.SAF is 3197143 bytes; safetensors header length field = 15599, so the tensor data region is bytes [15607, 3197143). All offsets below are inside it. Main set: 20 offsets, byte XOR a random non-zero mask (`byte_NN`). Supplementary set: 20 offsets, one bit flipped (`bit_NN`). Canary prompts are the four LAB-08 receipt prompts (taken from the receipts' prompt-hex), 16 greedy tokens.

Control: `orig` vs `orig_repeat` decode digests are identical for all canaries: True.

Original model digests (16 tokens): self `6a595a3cce0340bc`; calc `58e895466c3a4917`; lookup `24b4fdddffef882b`; abstain `56a4a3655b7b8c45`.

Original model, 16 greedy tokens per canary (EOS is ignored by `cis_decode`, so the decode runs on past the end of the call):

- `self` prompt "Q: What are you, and why do you run without an operating system?\nA:" -> " No. I boot straight from the firmware as a UEFI application. There is no"
- `calc` prompt "Q: What is 1234 * 5678?\nA:" -> " CALC(1234 * 5678).\nTOOL[calc]=21212"
- `lookup` prompt "Q: What is part P-205?\nA:" -> " LOOKUP(P-205).\nTOOL[lookup]=NONE\nNo entry for"
- `abstain` prompt "Q: What is the population of Springfield?\nA:" -> " I don't know that, and I won't make it up. Supply the"

| set | # | offset | tensor | dtype | byte | digests changed (of 4) | which | original receipts failing | own-artifact receipts verified |
|---|---|---|---|---|---|---|---|---|---|
| byte | 0 | 2692987 | model.layers.6.mlp.up_proj.weight | U8 | 0x95->0x2e | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 1 | 32573 | model.layers.0.self_attn.q_proj.weight | U8 | 0x29->0x26 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 2 | 1940177 | model.layers.4.mlp.down_proj.weight | U8 | 0x29->0xe1 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 3 | 223579 | model.layers.0.mlp.up_proj.weight | U8 | 0x12->0xa9 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 4 | 1694050 | model.layers.4.self_attn.o_proj.weight | U8 | 0x26->0x91 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 5 | 927820 | model.layers.2.mlp.gate_proj.weight | U8 | 0x64->0x25 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 6 | 2860192 | model.layers.7.self_attn.v_proj.weight | U8 | 0x22->0x38 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 7 | 1326105 | model.layers.3.mlp.gate_proj.weight | U8 | 0xa2->0x42 | 0 | - | 15 of 15 | 4 of 4 |
| byte | 8 | 3075825 | model.layers.7.mlp.up_proj.weight | U8 | 0x82->0x47 | 0 | - | 15 of 15 | 4 of 4 |
| byte | 9 | 2308753 | model.layers.5.mlp.down_proj.weight | U8 | 0x99->0x2c | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 10 | 1223478 | model.layers.3.self_attn.q_proj.weight | U8 | 0xa4->0xf8 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 11 | 2523258 | model.layers.6.mlp.gate_proj.weight | U8 | 0x44->0xa5 | 0 | - | 15 of 15 | 4 of 4 |
| byte | 12 | 1580343 | model.layers.3.mlp.down_proj.weight | U8 | 0x88->0xc5 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 13 | 309463 | model.layers.0.mlp.up_proj.weight | U8 | 0xa6->0x7b | 0 | - | 15 of 15 | 4 of 4 |
| byte | 14 | 968003 | model.layers.2.mlp.gate_proj.weight | U8 | 0x81->0x73 | 0 | - | 15 of 15 | 4 of 4 |
| byte | 15 | 176473 | model.layers.0.mlp.gate_proj.weight | U8 | 0x16->0x86 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 16 | 17045 | model.layers.0.post_attention_layernorm.weight | BF16 | 0x4f->0x88 | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 17 | 3073549 | model.layers.7.mlp.up_proj.weight | U8 | 0x90->0x55 | 0 | - | 15 of 15 | 4 of 4 |
| byte | 18 | 1015289 | model.layers.2.mlp.up_proj.weight | U8 | 0x50->0x0c | 1 | calc | 15 of 15 | 4 of 4 |
| byte | 19 | 1903690 | model.layers.4.mlp.up_proj.weight | U8 | 0x55->0x27 | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 0 | 1565215 | model.layers.3.mlp.down_proj.weight | U8 | 0x1a->0x12 | 0 | - | 15 of 15 | 4 of 4 |
| bit | 1 | 1184388 | model.layers.2.mlp.down_proj.weight | U8 | 0x66->0x67 | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 2 | 1151180 | model.layers.2.mlp.down_proj.weight | U8 | 0x21->0x20 | 0 | - | 15 of 15 | 4 of 4 |
| bit | 3 | 2995364 | model.layers.7.mlp.gate_proj.weight | U8 | 0xa0->0xe0 | 0 | - | 15 of 15 | 4 of 4 |
| bit | 4 | 1211535 | model.layers.3.mlp.ffn_sub_norm.weight | BF16 | 0xf5->0xf1 | 0 | - | 15 of 15 | 4 of 4 |
| bit | 5 | 1812280 | model.layers.4.mlp.up_proj.weight | U8 | 0x55->0x45 | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 6 | 633714 | model.layers.1.mlp.up_proj.weight | U8 | 0x20->0x22 | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 7 | 2174256 | model.layers.5.mlp.gate_proj.weight | U8 | 0x06->0x02 | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 8 | 1914230 | model.layers.4.mlp.down_proj.weight | U8 | 0xa2->0xaa | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 9 | 2353916 | model.layers.5.mlp.down_proj.weight | U8 | 0x1a->0x9a | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 10 | 2654836 | model.layers.6.mlp.up_proj.weight | U8 | 0x16->0x96 | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 11 | 2624790 | model.layers.6.mlp.up_proj.weight | U8 | 0x46->0x44 | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 12 | 1607163 | model.layers.4.post_attention_layernorm.weight | BF16 | 0x8c->0xac | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 13 | 1484422 | model.layers.3.mlp.up_proj.weight | U8 | 0x66->0x6e | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 14 | 1298916 | model.layers.3.self_attn.o_proj.weight | U8 | 0x08->0x28 | 0 | - | 15 of 15 | 4 of 4 |
| bit | 15 | 3083008 | model.layers.7.mlp.up_proj.weight | U8 | 0x1a->0x9a | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 16 | 2864386 | model.layers.7.self_attn.v_proj.weight | U8 | 0x58->0x5c | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 17 | 2457652 | model.layers.6.self_attn.v_proj.weight | U8 | 0x18->0x10 | 0 | - | 15 of 15 | 4 of 4 |
| bit | 18 | 1509829 | model.layers.3.mlp.down_proj.weight | U8 | 0x0a->0x0b | 1 | calc | 15 of 15 | 4 of 4 |
| bit | 19 | 2105201 | model.layers.5.self_attn.o_proj.weight | U8 | 0x51->0xd1 | 1 | calc | 15 of 15 | 4 of 4 |

| set | mutants | with >= 1 canary digest changed | with all 4 changed | canary digests changed | original-minted receipts failing against the mutated MODEL.SAF | receipts minted on the mutated artifacts that verify against them | decode crashes |
|---|---|---|---|---|---|---|---|
| byte | 20 | 14 of 20 | 0 of 20 | 14 of 80 | 300 of 300 | 80 of 80 | 0 |
| bit | 20 | 14 of 20 | 0 of 20 | 14 of 80 | 300 of 300 | 80 of 80 | 0 |

Per-canary changes (byte set, of 20 mutants): self=0, calc=14, lookup=0, abstain=0. First differing generated-token index (0-based) over the 14 changed decodes: min 13, max 14.

Per-canary changes (bit set, of 20 mutants): self=0, calc=14, lookup=0, abstain=0. First differing generated-token index (0-based) over the 14 changed decodes: min 13, max 14.

For reference, the genuine `qemu_calc` receipt holds 9 generated tokens (473,8,17,9254,700,4787,1889,367,199), the same first 9 ids as the 16-token decode: `True`. The CALC call ends at generated index 8; a first difference at an index above that is a change after the call, in the invented tool value.

By tensor dtype (main set): U8: 13 of 19 changed, BF16: 1 of 1 changed.

Verified receipts in H2 (cis_witness gen on the artifacts under test, then verify against the same artifacts): 164 of 164 verify, including the 4 canary receipts on the original artifacts.

Examples of a changed decode (original -> mutated text, canary prompt in `h2_decode_raw.log`):

- byte_00 offset 2692987 (model.layers.6.mlp.up_proj.weight), canary `calc`: original " CALC(1234 * 5678).\nTOOL[calc]=21212" -> mutated " CALC(1234 * 5678).\nTOOL[calc]=53500"
- byte_01 offset 32573 (model.layers.0.self_attn.q_proj.weight), canary `calc`: original " CALC(1234 * 5678).\nTOOL[calc]=21212" -> mutated " CALC(1234 * 5678).\nTOOL[calc]=53500"
- byte_02 offset 1940177 (model.layers.4.mlp.down_proj.weight), canary `calc`: original " CALC(1234 * 5678).\nTOOL[calc]=21212" -> mutated " CALC(1234 * 5678).\nTOOL[calc]=53500"
- byte_03 offset 223579 (model.layers.0.mlp.up_proj.weight), canary `calc`: original " CALC(1234 * 5678).\nTOOL[calc]=21212" -> mutated " CALC(1234 * 5678).\nTOOL[calc]=28000"

## 4. H3: mutated ATTEST.TXT through `attest_verify.py`

Positive control (unmodified ATTEST.TXT, both boots): qemu_calc F1=ACCEPT F2=ACCEPT, qemu_self F1=ACCEPT F2=ACCEPT.

Single-field mutants (one character, one nibble or one line each). "rejected" = exit code != 0.

| field class | mutants | F1 accepted | F1 rejected | F2 accepted | F2 rejected | F1 accepted without any QUOTE VERIFY PASS line |
|---|---|---|---|---|---|---|
| pcr-value | 48 | 0 | 48 | 0 | 48 | 0 |
| quote-attest | 68 | 0 | 68 | 0 | 68 | 0 |
| quote-signature | 24 | 0 | 24 | 0 | 24 | 0 |
| quote-qualifying | 16 | 0 | 16 | 0 | 16 | 0 |
| quote-pubkey | 16 | 0 | 16 | 0 | 16 | 0 |
| event-line | 68 | 35 | 33 | 35 | 33 | 0 |
| measured-line | 33 | 1 | 32 | 0 | 33 | 0 |
| field-deletion | 18 | 2 | 16 | 2 | 16 | 2 |
| unread-line (REPORTED SEPARATELY) | 28 | 26 | 2 | 26 | 2 | 0 |
| cosmetic (REPORTED SEPARATELY) | 28 | 22 | 6 | 22 | 6 | 2 |
| sig-malleability (REPORTED SEPARATELY) | 2 | 2 | 0 | 2 | 0 | 0 |

Registered field classes combined (pcr-value, quote-attest, quote-signature, quote-qualifying, quote-pubkey, event-line, measured-line, field-deletion): 291 mutants; F1 accepted 38; F2 accepted 37.

### 4a. Sub-field breakdown

| field class | sub-field | mutants | F1 accepted | F2 accepted |
|---|---|---|---|---|
| pcr-value | pcr12 | 16 | 0 | 0 |
| pcr-value | pcr13 | 16 | 0 | 0 |
| pcr-value | pcr4 | 16 | 0 | 0 |
| quote-attest | clock | 4 | 0 | 0 |
| quote-attest | extraData | 4 | 0 | 0 |
| quote-attest | extraData.size | 4 | 0 | 0 |
| quote-attest | firmwareVersion | 4 | 0 | 0 |
| quote-attest | magic | 4 | 0 | 0 |
| quote-attest | pcrDigest | 4 | 0 | 0 |
| quote-attest | pcrDigest.size | 4 | 0 | 0 |
| quote-attest | pcrSelect.bitmap | 4 | 0 | 0 |
| quote-attest | pcrSelect.count | 4 | 0 | 0 |
| quote-attest | pcrSelect.hashAlg | 4 | 0 | 0 |
| quote-attest | pcrSelect.sizeofSelect | 4 | 0 | 0 |
| quote-attest | qualifiedSigner.name | 4 | 0 | 0 |
| quote-attest | qualifiedSigner.size | 4 | 0 | 0 |
| quote-attest | resetCount | 4 | 0 | 0 |
| quote-attest | restartCount | 4 | 0 | 0 |
| quote-attest | safe | 4 | 0 | 0 |
| quote-attest | type | 4 | 0 | 0 |
| quote-signature | quote-sig-r | 12 | 0 | 0 |
| quote-signature | quote-sig-s | 12 | 0 | 0 |
| quote-qualifying | quote-qualifying | 16 | 0 | 0 |
| quote-pubkey | quote-pub-x | 8 | 0 | 0 |
| quote-pubkey | quote-pub-y | 8 | 0 | 0 |
| event-line | pcr12/data | 8 | 0 | 0 |
| event-line | pcr12/delete | 8 | 0 | 0 |
| event-line | pcr12/sha256 | 8 | 0 | 0 |
| event-line | pcr12/type | 8 | 8 | 8 |
| event-line | pcr13/data | 3 | 0 | 0 |
| event-line | pcr13/delete | 3 | 0 | 0 |
| event-line | pcr13/sha256 | 3 | 0 | 0 |
| event-line | pcr13/type | 3 | 3 | 3 |
| event-line | pcr4/data | 6 | 6 | 6 |
| event-line | pcr4/delete | 6 | 6 | 6 |
| event-line | pcr4/sha256 | 6 | 6 | 6 |
| event-line | pcr4/type | 6 | 6 | 6 |
| measured-line | pcr12/char | 16 | 0 | 0 |
| measured-line | pcr12/delete | 8 | 0 | 0 |
| measured-line | pcr13/char | 6 | 0 | 0 |
| measured-line | pcr13/delete | 3 | 1 | 0 |
| field-deletion | pcr | 6 | 0 | 0 |
| field-deletion | quote-attest | 2 | 2 | 2 |
| field-deletion | quote-pub-x | 2 | 0 | 0 |
| field-deletion | quote-pub-y | 2 | 0 | 0 |
| field-deletion | quote-qualifying | 2 | 0 | 0 |
| field-deletion | quote-sig-r | 2 | 0 | 0 |
| field-deletion | quote-sig-s | 2 | 0 | 0 |
| unread-line | cpuid | 4 | 4 | 4 |
| unread-line | header | 4 | 2 | 2 |
| unread-line | pcr-bank | 4 | 4 | 4 |
| unread-line | quote-key | 4 | 4 | 4 |
| unread-line | quote-pcrs | 4 | 4 | 4 |
| unread-line | quote-public | 4 | 4 | 4 |
| unread-line | quote-retries | 4 | 4 | 4 |
| cosmetic | crlf-all | 2 | 2 | 2 |
| cosmetic | leading-zero-bytes | 4 | 4 | 4 |
| cosmetic | no-final-newline | 2 | 2 | 2 |
| cosmetic | trailing-space | 10 | 4 | 4 |
| cosmetic | uppercase-hex | 10 | 10 | 10 |
| sig-malleability | sig-s=n-s | 2 | 2 | 2 |

### 4b. Accepted ATTEST mutants (findings), verbatim

- **event-line**: 35 of 68 accepted by F1 or F2
  - `H3event-line-001` (pcr4/sha256, qemu_calc): event pcr=4 line 9: sha256 char 16 9->6  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3event-line-002` (pcr4/data, qemu_calc): event pcr=4 line 9: data char 15 l->w  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3event-line-003` (pcr4/type, qemu_calc): event pcr=4 line 9: type char 5 0->8  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3event-line-004` (pcr4/delete, qemu_calc): event pcr=4 line 9 deleted  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3event-line-015` (pcr12/type, qemu_calc): event pcr=12 line 12: type char 0 d->9  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3event-line-027` (pcr13/type, qemu_calc): event pcr=13 line 15: type char 0 d->0  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
- **measured-line**: 1 of 33 accepted by F1 or F2
  - `H3measured-line-030` (pcr13/delete, qemu_self): measured pcr=13 line 6 deleted  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 1 (REJECT, quote line 1)
- **field-deletion**: 2 of 18 accepted by F1 or F2
  - `H3field-deletion-004` (quote-attest, qemu_calc): line deleted: quote-attest ff54434780180022000b16f7785  -> F1 exit 0 (ACCEPT, quote line 0), F2 exit 0 (ACCEPT, quote line 0)
- **unread-line**: 26 of 28 accepted by F1 or F2
  - `H3unread-line-001` (cpuid, qemu_calc): cpuid char 37 P->C  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3unread-line-003` (pcr-bank, qemu_calc): pcr-bank char 2 a->c  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3unread-line-005` (quote-pcrs, qemu_calc): quote-pcrs char 0 4->d  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3unread-line-007` (quote-public, qemu_calc): quote-public char 54 4->2  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3unread-line-009` (quote-retries, qemu_calc): quote-retries char 0 1->4  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3unread-line-011` (quote-key, qemu_calc): quote-key char 41 n->m  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3unread-line-014` (header, qemu_calc): header 'AEGIS-ATTEST v0' -> 'AEGIS-ATTEST v0x'  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
- **cosmetic**: 22 of 28 accepted by F1 or F2
  - `H3cosmetic-001` (crlf-all, qemu_calc): every line ends CRLF  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3cosmetic-002` (no-final-newline, qemu_calc): final newline removed  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3cosmetic-005` (trailing-space, qemu_calc): trailing space on line 26 (quote-attest)  -> F1 exit 0 (ACCEPT, quote line 0), F2 exit 0 (ACCEPT, quote line 0)
  - `H3cosmetic-008` (uppercase-hex, qemu_calc): quote-attest written in upper case hex  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
  - `H3cosmetic-013` (leading-zero-bytes, qemu_calc): quote-sig-r with two extra leading 00 bytes  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)
- **sig-malleability**: 2 of 2 accepted by F1 or F2
  - `H3sig-malleability-001` (sig-s=n-s, qemu_calc): quote-sig-s replaced by n-s (the other valid ECDSA signature)  -> F1 exit 0 (ACCEPT, quote line 1), F2 exit 0 (ACCEPT, quote line 1)

### 4c. Which check caught the rejected mutants (first failing check text, F1)

- cosmetic: 2 x `quote pcrDigest over PCRs [..] == SHA-256(PCR values read back): FAIL`
- cosmetic: 2 x `QUOTE VERIFY ERROR 'quote-sig-r'`
- cosmetic: 2 x `pcr13: replayed HEX.. tpm HEX.. FAIL (n events)`
- event-line: 6 x `eventlog pcr=12 sha256=HEX.. MISSING :: AEGIS-MEASURE v0 artifact=MODEL.SAF bytes=N sha256=a44`
- event-line: 6 x `eventlog pcr=12 sha256=HEX.. MISSING :: AEGIS-MEASURE v0 artifact=EMBED.BIN bytes=N sha256=8cb`
- event-line: 6 x `eventlog pcr=12 sha256=HEX.. MISSING :: AEGIS-MEASURE v0 artifact=VOCAB.BIN bytes=N sha256=a4ca`
- event-line: 6 x `eventlog pcr=13 sha256=HEX.. MISSING :: AEGIS-RECEIPT v0 mode=mint steps=N cis-digest=HEX`
- event-line: 6 x `eventlog pcr=12 sha256=HEX.. MISSING :: AEGIS-MEASURE v0 artifact=TABLE.TSV bytes=N sha256=6b2f738`
- event-line: 3 x `eventlog pcr=13 sha256=HEX.. MISSING :: AEGIS-RECEIPT v0 mode=mint-tool steps=N cis-digest=594d2cc5f`
- field-deletion: 2 x `quote pcrDigest over PCRs [..] == SHA-256(PCR values read back): FAIL`
- field-deletion: 2 x `pcr12: replayed HEX.. tpm None.. FAIL (n events)`
- field-deletion: 2 x `pcr13: replayed HEX.. tpm None.. FAIL (n events)`
- field-deletion: 2 x `QUOTE VERIFY ERROR 'quote-sig-r'`
- field-deletion: 2 x `QUOTE VERIFY ERROR 'quote-sig-s'`
- field-deletion: 2 x `QUOTE VERIFY ERROR 'quote-pub-x'`
- field-deletion: 2 x `QUOTE VERIFY ERROR 'quote-pub-y'`
- field-deletion: 2 x `quote extraData == qualifying (..): FAIL`
- measured-line: 24 x `pcr12: replayed HEX.. tpm HEX.. FAIL (n events)`
- measured-line: 8 x `pcr13: replayed HEX.. tpm HEX.. FAIL (n events)`
- pcr-value: 16 x `quote pcrDigest over PCRs [..] == SHA-256(PCR values read back): FAIL`
- pcr-value: 16 x `pcr12: replayed HEX.. tpm HEX.. FAIL (n events)`
- pcr-value: 16 x `pcr13: replayed HEX.. tpm HEX.. FAIL (n events)`
- quote-attest: 32 x `quote ECDSA-P256/SHA-256 signature over TPMS_ATTEST (openssl): Verification failure FAIL`
- quote-attest: 11 x `quote extraData == qualifying (HEX..): FAIL`
- quote-attest: 9 x `quote pcrDigest over PCRs [..] == SHA-256(PCR values read back): FAIL`
- quote-attest: 5 x `QUOTE VERIFY ERROR index out of range`
- quote-attest: 2 x `quote attest magic=ff544347 type=8d18 FAIL`
- quote-attest: 1 x `quote attest magic=ff544247 type=8018 FAIL`
- quote-attest: 1 x `quote attest magic=ff542347 type=8018 FAIL`
- quote-attest: 1 x `quote attest magic=ff544347 type=d018 FAIL`
- quote-attest: 1 x `quote pcrDigest over PCRs [..] == SHA-256(PCR values read`
- quote-attest: 1 x `quote pcrDigest over PCRs [4, 12, 13, 37, 40, 42, 43, 44, 46, 47, 48, 55, 56, 57, 58, 61, 67, 69, 71, 72, 77, `
- quote-attest: 1 x `quote attest magic=f5544347 type=8018 FAIL`
- quote-attest: 1 x `quote attest magic=ffd44347 type=8018 FAIL`
- quote-attest: 1 x `quote attest magic=ff544347 type=8013 FAIL`
- quote-attest: 1 x `quote pcrDigest over PCRs [4, 12, 13, 37, 40, 41, 43, 46, 50, 51, 52, 53, 54, 57, 59, 60, 62, 63, 64, 69, 70, `
- quote-pubkey: 16 x `QUOTE VERIFY ERROR Command '['openssl', 'pkey', '-pubin', '-inform', 'DER', '-in', '<tmpdir> '-out', '<tmpdir>`
- quote-qualifying: 16 x `quote extraData == qualifying (HEX..): FAIL`
- quote-signature: 24 x `quote ECDSA-P256/SHA-256 signature over TPMS_ATTEST (openssl): Verification failure FAIL`
- unread-line: 2 x `FAIL: not an AEGIS-ATTEST v0 file`

### 4d. The receipt argument of the finalize.sh invocation (F1) is ignored

`attest_verify.py` reads the receipt only after `--receipt`. In F1 the receipt is a stray positional argument. S1 tampers the RECEIPT.TXT (not the ATTEST) and runs both forms against the genuine ATTEST.TXT:

| receipt field changed | mutants | F1 accepted | F2 accepted |
|---|---|---|---|
| chain | 8 | 8 | 0 |
| cis-digest | 8 | 8 | 0 |
| prompt-hex | 8 | 8 | 0 |
| token-ids | 8 | 8 | 0 |

### 4e. Re-signed forgery with a software key (no TPM), supplementary

| case | base | F1 | F1 quote line | F2 | F2 quote line | `cis_witness verify` on the forged receipt |
|---|---|---|---|---|---|---|
| S2-pcr13-line-edit | qemu_calc | exit 0 ACCEPT | 1 | exit 0 ACCEPT | 1 | exit 0 ACCEPT `VERIFY PASS — replay reproduced 9 tokens, the token digest, and the full logit chain bit-for-bit` |
| S2-receipt-chain-edit | qemu_self | exit 0 ACCEPT | 1 | exit 0 ACCEPT | 1 | exit 1 REJECT_CLEAN `VERIFY FAIL — replay diverged from the receipt` |

## 5. Hypotheses

- **H1** (every semantic single-field mutation rejected, >= 500 per class). Verdict: SUPPORTED for every field-value class (C01-C07, C09, C10); NOT SUPPORTED if line reorder (C08) is counted. Classes with fewer than 500 mutants: none. Registered classes with at least one ACCEPT: C08 (520 of 520). Field-value classes (C01-C07, C09, C10) accepted in total: 0 of 5045. Reorder (C08, changes no field value): 520 of 520 accepted. Rejections by crash instead of a clean FAIL: 172 of 5565 in the registered classes.
- **H2** (a one-byte weight change alters at least one canary digest, and the original receipts fail against the changed artifacts). Verdict: second half SUPPORTED; first half NOT SUPPORTED for 6 of 20 mutants (their 16-token decode digests are unchanged on all four canaries). Numbers: 14 of 20 byte-mutants changed at least one canary digest (14 of 80 canary decodes); original-minted receipts failing against the mutated MODEL.SAF: 300 of 300. Supplementary single-bit set: 14 of 20 changed a digest; 300 of 300 receipts failed.
- **H3** (any altered PCR, quote or signature field fails attest_verify.py). Verdict: SUPPORTED for the named fields (pcr values, quote-attest bytes, signature r/s, qualifying data, public key); NOT SUPPORTED for the signature field once malleability (s -> n-s) is counted; the quote can be silently dropped. Numbers: the five field classes the hypothesis names (`pcr` values, `quote-attest` bytes, signature r/s, qualifying data, public key) had 172 mutants; F1 accepted 0, F2 accepted 0. Outside those fields: unread `quote-pcrs`/`quote-public`/`quote-retries`/`quote-key` lines accepted 16 of 16; deleting the `quote-attest` line accepted 2 of 2; signature malleability s -> n-s accepted 2 of 2. Over all registered classes including event and measured lines and deletions: 291 mutants, F1 accepted 38, F2 accepted 37.

## 6. Notes and limits

- The receipt `chain` absorbs the model SHA-256 in its header (`WitnessHeader`), so any changed MODEL.SAF changes the chain whether or not any logit changed. The CLI therefore cannot separate logit-level sensitivity from the header binding; the H2 digest comparison uses only the FNV token digest printed by `cis_decode`.
- `cis_decode` ignores EOS and always emits 16 tokens, so the calc canary runs on past its CALC call into an invented `TOOL[calc]=` value. That continuation is the only place a decode changed.
- The 11 receipts come from two kinds of source: 8 `RECEIPT.TXT` files whose SHA-256 is the quote-qualifying data of their boot, and 3 `RECEIPT2.TXT` files whose bytes are not bound whole-file (only their `cis-digest` and `chain` are in PCR 13).
- Boots were under QEMU with swtpm; the attestation key is a transient owner-hierarchy key with no certificate chain (LAB-04). S2 shows the verifier would equally accept a software key.
- The forgery key in S2 was generated with `openssl ecparam`, used once and deleted; only the forged ATTEST.TXT files are kept (inside `h3_mutants.tar.gz`).
- Unregistered probes (U1-U6, C11, H3 unread/cosmetic/sig-malleability, S1, S2, the bit-flip set) are additions to the pre-registration and are labelled as such; they do not enter the H1/H3 per-class rates for the registered classes.
- Only files under `labs/safe/`, `labs/logs/safe/SAFE-01/` and the scratch directory were written. `alice-aegis` was only executed.

## 7. Files

- `RESULT.md`
- `artifacts.sha256.tsv`
- `binaries.sha256.txt`
- `h1_accepted` (dir)
- `h1_f2_crosscheck.tsv`
- `h1_generation.json`
- `h1_manifest.tsv`
- `h1_mutants.tar.gz`
- `h1_results.tsv`
- `h2_decode.tsv`
- `h2_decode_raw.log`
- `h2_mutations.tsv`
- `h2_receipts` (dir)
- `h2_verify.tsv`
- `h3_mutants.tar.gz`
- `h3_results.tsv`
- `h3_s1_receipt_side.tsv`
- `h3_s2_forgery.tsv`
- `run_h1.log`
- `run_h2.log`
- `run_h3.log`

