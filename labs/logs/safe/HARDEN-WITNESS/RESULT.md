# HARDEN-WITNESS RESULT: strict witness-receipt verification and a panic-free parser (LAB-09 part 2)

Every number below is computed by `labs/safe/harden_witness.py report` (module `harden_witness_report.py`) from the logs saved next to this file and from the SAFE-01 logs. Rule A: no timing or rate was recorded anywhere (the harness timeout only kills a hung process).

## 0. Findings at a glance

1. **`cis_witness verify --strict` rejects every previously accepted non-cosmetic mutant (HW1).** C08 line reorder, U1 prompt-toks, U2 gen-toks, U3 header, U4 unknown line, U5 duplicate key, U6 non-canonical encodings: SAFE-01 default verdict ACCEPT on 838 of 929 mutants; the new binary in default mode still ACCEPTs 838 of 929 (unchanged on purpose); `--strict` ACCEPTs 0 of 929. The cosmetic class C11 (CRLF, trailing blanks, final newline) is also fully rejected under `--strict`: 0 of 396 accepted (default: 242).
2. **Genuine receipts pass (HW2).** Strict-mode PASS: 11 of 11 QEMU-minted `RECEIPT*.TXT` under `final_step12000`; 1 of 1 golden fixture replayed in full (`witness_v1_m7_once64.receipt`, with the m7 artifacts); 164 of 164 receipts minted by `cis_witness gen` in SAFE-01 H2. The other 4 golden fixtures (bitnet2b, e16_qat, e16_qat_pruned, falcon_e_1b) could not be replayed here because their model artifacts are not on this host: they were checked at the parser level only (4 of 4 reach the artifact-hash comparison without a strict-format failure, and the unit test `strict_accepts_every_golden_and_matches_the_lenient_reader` parses all 5). So HW2 is confirmed with that qualification.
3. **Zero panics (HW3).** SAFE-01 default binary: 222 of 6381 rows were crash-rejects (panic text, not a verdict). New binary: default mode 0 panics and strict mode 0 panics over the same 6381 rows; fuzz (2400 malformed inputs x 2 modes): 0 and 0; controls: 0. Totals: default 0, strict 0. Exit code 2 (usage/unusable file) occurred 0 (default) and 0 (strict) times in the H1 sweep.
4. **Default mode did not move.** For the 6159 rows whose SAFE-01 verdict was not a crash, the new default verdict is identical in 6159 and the last stdout line identical in 6159. Verdict changes in default mode other than REJECT_CRASH to REJECT_CLEAN: 0. The 222 old crash-rejects are now clean `VERIFY FAIL` rejections: 222 of 222.
5. **Strict is a subset of default and accepts nothing in the sweep except the unmodified controls.** Rows where strict ACCEPTs but default does not: 0. Strict ACCEPTs over the 6381 sweep rows: 11; all of them class C00 (the unmodified controls): yes.
6. **Tests.** `cargo test --release --example cis_witness`: 9 passed, 0 failed across 1 test binaries. `cargo test -p aegis-core --release`: 159 passed, 0 failed across 32 test binaries (the witness_contract and golden tests are among them; the same command on the tree before the change gave 159 passed, 0 failed across 32 test binaries, log `cargo_test_aegis_core_baseline.log`). `scripts/devloop.sh fmt`: aegis-linux PASS.

## 1. What changed in `alice-aegis` (branch `lab/vnni-cis1`, local only)

Files: `aegis-linux/examples/cis_witness.rs`, `aegis-linux/Cargo.toml` (adds `test = true` for the example, as already done for `agent_trace` and `reasoning_trace`, so the new unit tests run under `cargo test`). `aegis-core/src/witness.rs` has no receipt parser (it holds SHA-256, the header hash and the chain), so nothing there changed. `tests/golden` and `docs/hardware_logs` were not touched.

**Canonical layout** (`KEY_ORDER` in the source), derived from the two writers, which agree line for line: the `println!` sequence of `cis_witness gen` (old lines 149-159) and `aegis-uefi/src/verifier.rs::render_receipt` (lines 155-168, the UEFI mint path). There is no `cis_witness mint` subcommand; `gen` is the host-side minter. `gen` now prints through a `render_receipt` function that the unit tests use to pin the reader order to the writer order, and `gen` output is byte-identical to the SAFE-01 binary (section 3).

```
AEGIS-WITNESS v1-CIS
model <64 lower-case hex>
embed <64 lower-case hex>
vocab <64 lower-case hex>
maxtok <decimal>
prompt-hex <lower-case hex, even length, decodes to UTF-8>
prompt-toks <decimal>
gen-toks <decimal>
token-ids <comma-separated decimal u32>
cis-digest <16 lower-case hex>
chain <64 lower-case hex>
```

**`--strict` requires:** printable ASCII and LF only (no CR, tab, NUL or non-ASCII byte anywhere); exactly one `\n` after the last line and no blank line; exactly eleven lines in the order above (an unknown, duplicate, missing or reordered line is an error that names the line); header exactly `AEGIS-WITNESS v1-CIS`; one space between key and value, no leading or trailing blank; hex fields lower-case and of the exact length; decimals canonical (digits only, no `+`, no leading zero except `0`, fits the type); `gen-toks` equal to the `token-ids` count (parser); `prompt-toks` equal to the tokenizer length of the decoded prompt (after replay, so it needs the artifacts). All default checks (artifact hashes, token ids, digest, chain) still apply. The only line that may end in a space is `token-ids ` with an empty value, which both writers print for a zero-token receipt (`gen-toks 0`); it is accepted exactly in that case (section 3 shows the max_new 0 round trip).

**Default `verify` is unchanged for every input that did not panic** (same acceptance, same output). What changed is that input that used to panic now ends with `VERIFY FAIL — <reason>` on stdout and exit code 1: a non-UTF-8 file, an unparsable `maxtok` or token id, a `prompt-hex` pair that splits a multi-byte character, a prompt that tokenizes to nothing, a budget past the context window (the old context check could also wrap around for a huge `maxtok`; it is now a checked add), a multi-byte character inside a hash line (the 16-character prefix print is cut on a character boundary), and a missing receipt argument. Unreadable artifact/receipt files and unusable artifacts exit 2 with a message on stderr instead of a panic. The lenient reader itself is kept as is on purpose (`unhex_lenient` keeps `+a`, odd tails and non-hex pairs), so existing receipts and scripts verify exactly as before.

Binaries (sha256, name, path):

```
bc4bc82cff0cc8113f51bdda4d6c65612ff57b38b9011fc17fada5e924491203  new  /home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/cis_witness
79107c6b57101910c8fa5904e473279cc823c6db82dd3e0c0d4e0e012bfd5309  old  /tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/harden/cis_witness.old
```

The SAFE-01 binary (`old`, 79107c6b) was built on 2026-10-06; the new one with the toolchain on this host (`cargo --version` in section 6). Their `gen` outputs are byte-identical (section 3), so the difference in file hash is the code change and the toolchain, not the receipt format.

## 2. H1 re-run: every SAFE-01 mutant through the new binary, default and `--strict`

Inputs: the saved mutants in `SAFE-01/h1_mutants.tar.gz` (not regenerated: `safe01_tamper.py h1` writes into the SAFE-01 log directory, so the archive was used; check: archive members extracted: 6161; manifest rows: 6161; manifest sha256 mismatches: 0) plus the 220 one-byte-weight rows SAFE-01 merged into C10 (11 receipts x 20 mutated `MODEL.SAF`, from `h2_verify.tsv`). Total 6381 rows: 6161 receipt mutants (including the 11 unmodified C00 controls) and 220 weight rows. Old verdict = SAFE-01 `h1_results.tsv` / `h2_verify.tsv` (binary 79107c6b); new default and strict = this run. Scoring is the SAFE-01 rule unchanged: ACCEPT = exit 0 and a stdout line starting `VERIFY PASS`; REJECT_CLEAN = exit 1 and a line starting `VERIFY FAIL` or `FAIL artifact`; REJECT_CRASH = anything else (panic, signal, other exit code). A panic is counted separately as exit 101, death by signal, or `panicked at` on stderr.

| class | what | mutants | old ACCEPT | old CLEAN | old CRASH | new default ACCEPT | new default CLEAN | new default CRASH | strict ACCEPT | strict CLEAN | strict CRASH | panics old / default / strict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C00 | control (unmodified receipts) | 11 | 11 | 0 | 0 | 11 | 0 | 0 | 11 | 0 | 0 | 0 / 0 / 0 |
| C01 | token-ids (flip / drop / append / swap) | 706 | 0 | 706 | 0 | 0 | 706 | 0 | 0 | 706 | 0 | 0 / 0 / 0 |
| C02 | prompt-hex (one nibble) | 520 | 0 | 379 | 141 | 0 | 520 | 0 | 0 | 520 | 0 | 141 / 0 / 0 |
| C03 | cis-digest (one hex char) | 520 | 0 | 520 | 0 | 0 | 520 | 0 | 0 | 520 | 0 | 0 / 0 / 0 |
| C04 | chain (one hex char) | 520 | 0 | 520 | 0 | 0 | 520 | 0 | 0 | 520 | 0 | 0 / 0 / 0 |
| C05 | maxtok (+-1, and wider +-d) | 520 | 0 | 520 | 0 | 0 | 520 | 0 | 0 | 520 | 0 | 0 / 0 / 0 |
| C06 | model/embed/vocab hash lines (one hex char) | 520 | 0 | 520 | 0 | 0 | 520 | 0 | 0 | 520 | 0 | 0 / 0 / 0 |
| C07 | truncation (drop last k lines; byte cut) | 520 | 0 | 489 | 31 | 0 | 520 | 0 | 0 | 520 | 0 | 31 / 0 / 0 |
| C08 | line reorder | 520 | 520 | 0 | 0 | 520 | 0 | 0 | 0 | 520 | 0 | 0 / 0 / 0 |
| C09 | cross-receipt swap | 634 | 0 | 634 | 0 | 0 | 634 | 0 | 0 | 634 | 0 | 0 / 0 / 0 |
| C10 | artifact swap, relabel, 1-byte-mutated MODEL.SAF | 585 | 0 | 585 | 0 | 0 | 585 | 0 | 0 | 585 | 0 | 0 / 0 / 0 |
| C11 | cosmetic (trailing whitespace, CRLF, final newline) | 396 | 242 | 110 | 44 | 242 | 154 | 0 | 0 | 396 | 0 | 44 / 0 / 0 |
| U1 | prompt-toks line | 73 | 73 | 0 | 0 | 73 | 0 | 0 | 0 | 73 | 0 | 0 / 0 / 0 |
| U2 | gen-toks line | 73 | 73 | 0 | 0 | 73 | 0 | 0 | 0 | 73 | 0 | 0 / 0 / 0 |
| U3 | header line | 43 | 43 | 0 | 0 | 43 | 0 | 0 | 0 | 43 | 0 | 0 / 0 / 0 |
| U4 | unknown line appended | 11 | 11 | 0 | 0 | 11 | 0 | 0 | 0 | 11 | 0 | 0 / 0 / 0 |
| U5 | duplicate key | 110 | 52 | 52 | 6 | 52 | 58 | 0 | 0 | 110 | 0 | 6 / 0 / 0 |
| U6 | non-canonical encodings | 99 | 66 | 33 | 0 | 66 | 33 | 0 | 0 | 99 | 0 | 0 / 0 / 0 |
| all | | 6381 | 1091 | 5068 | 222 | 1091 | 5290 | 0 | 11 | 6370 | 0 | 222 / 0 / 0 |

TIMEOUT rows (inconclusive): old 0, default 0, strict 0.

### 2a. Sub-classes that SAFE-01 found accepted (or that strict accepts)

| class | sub-class | mutants | old ACCEPT | new default ACCEPT | strict ACCEPT |
|---|---|---|---|---|---|
| C00 | control | 11 | 11 | 11 | 11 |
| C08 | adjacent | 110 | 110 | 110 | 0 |
| C08 | permutation | 410 | 410 | 410 | 0 |
| C11 | trailing-space | 121 | 44 | 44 | 0 |
| C11 | trailing-tab | 121 | 44 | 44 | 0 |
| C11 | crlf-one-line | 121 | 121 | 121 | 0 |
| C11 | crlf-all | 11 | 11 | 11 | 0 |
| C11 | no-final-newline | 11 | 11 | 11 | 0 |
| C11 | blank-line-end | 11 | 11 | 11 | 0 |
| U1 | delete-line | 11 | 11 | 11 | 0 |
| U1 | pm1 | 22 | 22 | 22 | 0 |
| U1 | random | 40 | 40 | 40 | 0 |
| U2 | delete-line | 11 | 11 | 11 | 0 |
| U2 | pm1 | 22 | 22 | 22 | 0 |
| U2 | random | 40 | 40 | 40 | 0 |
| U3 | header-deleted | 11 | 11 | 11 | 0 |
| U3 | header-char | 32 | 32 | 32 | 0 |
| U4 | unknown-line-appended | 11 | 11 | 11 | 0 |
| U5 | dup-bogus-first | 55 | 52 | 52 | 0 |
| U6 | uppercase-prompt-hex | 11 | 11 | 11 | 0 |
| U6 | plus-in-prompt-hex | 11 | 11 | 11 | 0 |
| U6 | plus-maxtok | 11 | 11 | 11 | 0 |
| U6 | zero-maxtok | 11 | 11 | 11 | 0 |
| U6 | zero-token-id | 11 | 11 | 11 | 0 |
| U6 | plus-token-id | 11 | 11 | 11 | 0 |

### 2b. Verdict changes in default mode (old binary to new binary)

| old verdict | new default verdict | mutants |
|---|---|---|
| ACCEPT | ACCEPT | 1091 |
| REJECT_CLEAN | REJECT_CLEAN | 5068 |
| REJECT_CRASH | REJECT_CLEAN | 222 |

Allowed change: REJECT_CRASH to REJECT_CLEAN. Any other change: 0. Last stdout line differs between old and new default for non-crash rows: 0 of 6159.

### 2c. Why strict rejects (old-accepted mutants), verbatim last line, grouped

**C08 line reorder** (520 old-accepted):

- 390 x `VERIFY FAIL — strict: line N: header must be exactly "..."`
- 130 x `VERIFY FAIL — strict: line N: key out of order "...", canonical order expects "..."`
- example `C08-0001` (swap lines 0,1 (model <-> AEGIS-WITNESS)), strict stdout verbatim: `VERIFY FAIL — strict: line 1: header must be exactly "AEGIS-WITNESS v1-CIS"`

**U1 prompt-toks line** (73 old-accepted):

- 62 x `strict: prompt-toks N does not equal the tokenized prompt length N`
- 11 x `VERIFY FAIL — strict: line N: key out of order "...", canonical order expects "..."`
- example `U1-0001` (prompt-toks line deleted), strict stdout verbatim: `VERIFY FAIL — strict: line 7: key out of order "gen-toks", canonical order expects "prompt-toks"`

**U2 gen-toks line** (73 old-accepted):

- 62 x `VERIFY FAIL — strict: gen-toks N does not equal the token-ids count N`
- 11 x `VERIFY FAIL — strict: line N: key out of order "...", canonical order expects "..."`
- example `U2-0001` (gen-toks line deleted), strict stdout verbatim: `VERIFY FAIL — strict: line 8: key out of order "token-ids", canonical order expects "gen-toks"`

**U3 header line** (43 old-accepted):

- 43 x `VERIFY FAIL — strict: line N: header must be exactly "..."`
- example `U3-0001` (header line deleted), strict stdout verbatim: `VERIFY FAIL — strict: line 1: header must be exactly "AEGIS-WITNESS v1-CIS"`

**U4 unknown line appended** (11 old-accepted):

- 11 x `VERIFY FAIL — strict: line N: unexpected extra line "..." (a receipt has exactly N lines)`
- example `U4-0001` (line 'x-note hello' appended), strict stdout verbatim: `VERIFY FAIL — strict: line 12: unexpected extra line "x-note" (a receipt has exactly 11 lines)`

**U5 duplicate key** (52 old-accepted):

- 41 x `VERIFY FAIL — strict: line N: duplicate key "...", canonical order expects "..."`
- 11 x `VERIFY FAIL — strict: line N: unexpected extra line "..." (a receipt has exactly N lines)`
- example `U5-0001` (duplicate chain: bogus line before the original), strict stdout verbatim: `VERIFY FAIL — strict: line 12: unexpected extra line "chain" (a receipt has exactly 11 lines)`

**U6 non-canonical encodings** (66 old-accepted):

- 22 x `VERIFY FAIL — strict: line N (prompt-hex): expected non-empty lower-case hex of even length`
- 22 x `VERIFY FAIL — strict: line N (maxtok): expected a decimal integer without sign or leading zeros`
- 22 x `VERIFY FAIL — strict: line N (token-ids): expected comma-separated canonical decimal uN ids`
- example `U6-0001` (prompt-hex in upper case), strict stdout verbatim: `VERIFY FAIL — strict: line 6 (prompt-hex): expected non-empty lower-case hex of even length`

**C11 cosmetic (trailing whitespace, CRLF, final newline)** (242 old-accepted):

- 132 x `VERIFY FAIL — strict: byte N: carriage return (CRLF line endings are not canonical)`
- 44 x `VERIFY FAIL — strict: byte N: NxN is not printable ASCII or LF`
- 11 x `VERIFY FAIL — strict: line N: header must be exactly "..."`
- 11 x `VERIFY FAIL — strict: line N (prompt-hex): expected non-empty lower-case hex of even length`
- 11 x `VERIFY FAIL — strict: line N (prompt-toks): expected a decimal integer without sign or leading zeros`
- 11 x `VERIFY FAIL — strict: line N (gen-toks): expected a decimal integer without sign or leading zeros`
- example `C11-0001` (trailing-space on line 0 (AEGIS-WITNESS)), strict stdout verbatim: `VERIFY FAIL — strict: line 1: header must be exactly "AEGIS-WITNESS v1-CIS"`

### 2d. Rows that strict ACCEPTs

11 rows, ids: C00-0001, C00-0002, C00-0003, C00-0004, C00-0005, C00-0006, C00-0007, C00-0008, C00-0009, C00-0010, C00-0011.

## 3. Positive controls and panic samples

| group | what | default PASS | strict PASS |
|---|---|---|---|
| qemu_receipt | QEMU-minted RECEIPT.TXT / RECEIPT2.TXT, op12k final_step12000 artifacts | 11 of 11 | 11 of 11 |
| golden | tests/golden/witness_v1_m7_once64.receipt, replayed with the m7 artifacts | 1 of 1 | 1 of 1 |
| h2_self_receipt | receipts minted by `cis_witness gen` (SAFE-01 H2) against their own models (orig + 40 one-byte/one-bit mutants x 4 canaries) | 164 of 164 | 164 of 164 |
| golden_format_only | bitnet2b, e16_qat, e16_qat_pruned, falcon_e_1b goldens, artifacts not on this host, run against the op12k artifacts: expected `FAIL artifact` on all three hashes, i.e. the reader accepted the file and the artifact binding is what failed | 4 of 4 reach the hash check | 4 of 4 reach the hash check |

Golden format-only rows whose strict output contains a strict-reader failure: 0 of 4.

Receipts minted by `gen` (new binary), round trip, and old-versus-new `gen` stdout:

| case | max_new | old exit | new exit | old and new stdout identical | default verdict | strict verdict |
|---|---|---|---|---|---|---|
| canary_self | 16 | 0 | 0 | yes | ACCEPT | ACCEPT |
| canary_calc | 16 | 0 | 0 | yes | ACCEPT | ACCEPT |
| canary_lookup | 16 | 0 | 0 | yes | ACCEPT | ACCEPT |
| default_prompt | 12 | 0 | 0 | yes | ACCEPT | ACCEPT |
| empty_budget | 0 | 0 | 0 | yes | ACCEPT | ACCEPT |
| one_token | 1 | 0 | 0 | yes | ACCEPT | ACCEPT |
| multibyte_prompt | 6 | 0 | 0 | yes | ACCEPT | ACCEPT |

### 3a. Panic samples, verbatim (first SAFE-01 crash-reject of each class; old binary vs new default vs new strict)

```
##### C02-0007 class C02 sub nibble: prompt-hex[68] 4->c
mutant bytes (repr of the changed/shortened receipt, first 700 bytes): b'AEGIS-WITNESS v1-CIS\nmodel a44e48965c641b81994a670001c76a8bebd38857f9455cc5008acac8d2b2897a\nembed 8cbcd6b69df03539cd4638440fb903910325b7f6853349c5bb5778e413fafef0\nvocab a4cafc9649488987a8eb053476d389bd9a675405c51bfc42ebded546ae64eb17\nmaxtok 3\nprompt-hex 513a205768617420697320746865206361706974616c206f66204672616e63653f0ac13a\nprompt-toks 12\ngen-toks 3\ntoken-ids 4946,14,0\ncis-digest f5a7738385a31930\nchain a6d271d6e83c7f2d8c5670b3fd44cf8ba5f6c19cc2151e88a8bc8411f5ea4e6a\n'
--- OLD  default: exit 101
stdout: (empty)
stderr: thread 'main' (1573) panicked at examples/cis_witness.rs:180:64:
prompt utf8: FromUtf8Error { bytes: [81, 58, 32, 87, 104, 97, 116, 32, 105, 115, 32, 116, 104, 101, 32, 99, 97, 112, 105, 116, 97, 108, 32, 111, 102, 32, 70, 114, 97, 110, 99, 101, 63, 10, 193, 58], error: Utf8Error { valid_up_to: 34, 
--- NEW  default: exit 1
stdout: VERIFY FAIL — malformed receipt: prompt-hex does not decode to UTF-8 text
stderr: (empty)
--- NEW  --strict: exit 1
stdout: VERIFY FAIL — strict: line 6 (prompt-hex): does not decode to UTF-8 text
stderr: (empty)

##### C07-0006 class C07 sub lines: drop last 6 line(s)
mutant bytes (repr of the changed/shortened receipt, first 700 bytes): b'AEGIS-WITNESS v1-CIS\nmodel a44e48965c641b81994a670001c76a8bebd38857f9455cc5008acac8d2b2897a\nembed 8cbcd6b69df03539cd4638440fb903910325b7f6853349c5bb5778e413fafef0\nvocab a4cafc9649488987a8eb053476d389bd9a675405c51bfc42ebded546ae64eb17\nmaxtok 25\n'
--- OLD  default: exit 101
stdout: (empty)
stderr: thread 'main' (1576) panicked at examples/cis_witness.rs:68:5:
prompt tokenized to nothing
stack backtrace:
   0: __rustc::rust_begin_unwind
   1: core::panicking::panic_fmt
   2: cis_witness::replay
   3: cis_witness::main
note: Some details are omitted, run with `RUST_BACKTRACE=full` for a verbose
--- NEW  default: exit 1
stdout: VERIFY FAIL — receipt inputs cannot be replayed: prompt tokenized to nothing
stderr: (empty)
--- NEW  --strict: exit 1
stdout: VERIFY FAIL — strict: truncated: line 6 (prompt-hex) is missing
stderr: (empty)

##### C11-0013 class C11 sub trailing-space: trailing-space on line 4 (maxtok)
mutant bytes (repr of the changed/shortened receipt, first 700 bytes): b'AEGIS-WITNESS v1-CIS\nmodel a44e48965c641b81994a670001c76a8bebd38857f9455cc5008acac8d2b2897a\nembed 8cbcd6b69df03539cd4638440fb903910325b7f6853349c5bb5778e413fafef0\nvocab a4cafc9649488987a8eb053476d389bd9a675405c51bfc42ebded546ae64eb17\nmaxtok 25 \nprompt-hex 513a20576861742069732074686520706f70756c6174696f6e206f6620537072696e676669656c643f0a413a\nprompt-toks 12\ngen-toks 25\ntoken-ids 309,833,503,617,375,12,283,309,1352,503,935,356,540,14,2018,276,675,283,309,487,1715,356,1319,14,0\ncis-digest 751473b3a5980606\nchain 36a4727928a9bf0536c1da38a2deb661837077cb13c6940ebb570c85c80a0dcc\n'
--- OLD  default: exit 101
stdout: (empty)
stderr: thread 'main' (1579) panicked at examples/cis_witness.rs:178:54:
maxtok: ParseIntError { kind: InvalidDigit }
stack backtrace:
   0: __rustc::rust_begin_unwind
   1: core::panicking::panic_fmt
   2: core::result::unwrap_failed
   3: cis_witness::main
note: Some details are omitted, run with `RUST_BA
--- NEW  default: exit 1
stdout: VERIFY FAIL — malformed receipt: maxtok is not an unsigned integer
stderr: (empty)
--- NEW  --strict: exit 1
stdout: VERIFY FAIL — strict: line 5 (maxtok): expected a decimal integer without sign or leading zeros
stderr: (empty)

##### U5-0019 class U5 sub dup-bogus-first: duplicate prompt-hex: bogus line before the original
mutant bytes (repr of the changed/shortened receipt, first 700 bytes): b'AEGIS-WITNESS v1-CIS\nmodel a44e48965c641b81994a670001c76a8bebd38857f9455cc5008acac8d2b2897a\nembed 8cbcd6b69df03539cd4638440fb903910325b7f6853349c5bb5778e413fafef0\nvocab a4cafc9649488987a8eb053476d389bd9a675405c51bfc42ebded546ae64eb17\nmaxtok 9\nprompt-hex a13a20576861742069732031323334202a20353637383f0a413a\nprompt-hex 513a20576861742069732031323334202a20353637383f0a413a\nprompt-toks 13\ngen-toks 9\ntoken-ids 473,8,17,9254,700,4787,1889,367,199\ncis-digest fddebefc84f1ad58\nchain 6e6b2ddf1a8528e59665e43ccb0445e182d3da53db2621786afd97e6023c45ea\n'
--- OLD  default: exit 101
stdout: (empty)
stderr: thread 'main' (1582) panicked at examples/cis_witness.rs:180:64:
prompt utf8: FromUtf8Error { bytes: [161, 58, 32, 87, 104, 97, 116, 32, 105, 115, 32, 49, 50, 51, 52, 32, 42, 32, 53, 54, 55, 56, 63, 10, 65, 58], error: Utf8Error { valid_up_to: 0, error_len: Some(1) } }
stack backtrace:
   0: __rustc
--- NEW  default: exit 1
stdout: VERIFY FAIL — malformed receipt: prompt-hex does not decode to UTF-8 text
stderr: (empty)
--- NEW  --strict: exit 1
stdout: VERIFY FAIL — strict: line 6 (prompt-hex): does not decode to UTF-8 text
stderr: (empty)
```

## 4. Fuzz: malformed inputs beyond the SAFE-01 classes

2400 seeded inputs (`LAB09-HARDEN-WITNESS-20261008/fuzz`): 1 to 3 operations on a genuine receipt (truncate at a random byte, delete a byte range, insert NUL/CR/tab/0xff/UTF-8 lead bytes/signs/commas, replace a byte, duplicate or swap lines, replace a value with garbage such as empty, `-1`, 2^64, `aé`, 5000 characters, replace the prompt with random Unicode up to 700 characters, set `maxtok` to one of 21 values from 0 to 2^64+1, list `MAXTOKS` in `harden_witness.py`), and one pure-garbage file in 40 (random bytes, NULs, 200k newlines, empty, 0xff runs). Both modes, op12k artifacts.

| mode | ACCEPT | REJECT_CLEAN | REJECT_CRASH | TIMEOUT | panics | exit 2 |
|---|---|---|---|---|---|---|
| default | 265 | 2135 | 0 | 0 | 0 | 0 |
| strict | 0 | 2400 | 0 | 0 | 0 | 0 |

Strict ACCEPT but default not: 0. Strict ACCEPTs: 0, of which byte-identical to a genuine receipt: 0.

The 265 default-mode ACCEPTs are the legacy leniency (for example a duplicated identical line, or a changed byte inside an ignored line), not a regression: strict rejects all of them. The fuzz set is destructive by design, so it tests rejection and panic-freedom; acceptance of genuine receipts is tested in section 3.

Verbatim last stdout line, most common (default mode):

- 691 x `VERIFY FAIL — replay diverged from the receipt`
- 265 x `VERIFY PASS — replay reproduced N tokens, the token digest, and the full logit chain bit-for-bit`
- 250 x `VERIFY FAIL — malformed receipt: not valid UTF-N`
- 197 x `FAIL artifact: VOCAB hash mismatch (receipt  vs local aNcafcN)`
- 176 x `VERIFY FAIL — receipt inputs cannot be replayed: prompt (N) + max_new (N) exceeds max_position_embeddings (N)`
- 102 x `FAIL artifact: VOCAB hash mismatch (receipt aNcafcN vs local aNcafcN)`
- 99 x `VERIFY FAIL — malformed receipt: maxtok is not an unsigned integer`
- 95 x `VERIFY FAIL — malformed receipt: token id "..." is not an unsigned N-bit integer`

Verbatim last stdout line, most common (strict mode):

- 405 x `VERIFY FAIL — strict: no newline after the last line (exactly one is required)`
- 210 x `VERIFY FAIL — replay diverged from the receipt`
- 209 x `VERIFY FAIL — strict: line N: key out of order "...", canonical order expects "..."`
- 162 x `VERIFY FAIL — strict: byte N: NxN is not printable ASCII or LF`
- 157 x `VERIFY FAIL — strict: byte N: NxcN is not printable ASCII or LF`
- 129 x `VERIFY FAIL — strict: line N: header must be exactly "..."`
- 100 x `VERIFY FAIL — strict: line N (model): expected N lower-case hex digits`
- 89 x `VERIFY FAIL — strict: line N (embed): expected N lower-case hex digits`

## 5. Hypotheses

| H | verdict | numbers |
|---|---|---|
| HW1 every previously accepted non-cosmetic mutant (C08, U1-U6) is rejected under --strict | **CONFIRMED** | old default ACCEPT 838 of 929; strict ACCEPT 0 of 929 (all of 838 old-accepted are rejected); C11 cosmetic strict ACCEPT 0 of 396 |
| HW2 goldens and all genuine receipts pass under --strict | **CONFIRMED (qualified: 1 of 5 goldens replayed in full, 4 at parser level)** | qemu 11/11; m7 golden 1/1; gen-minted 164/164; 4 other goldens parser-level only |
| HW3 zero panics in both modes | **CONFIRMED** | default 0, strict 0 (H1 sweep 0/0, fuzz 0/0); SAFE-01 binary had 222 crash-rejects on the same rows |

## 6. How this was run (exact commands)

```
cd /home/user/aefinity-ai/alice-aegis/aegis-linux
cargo build --release --example cis_witness
cargo test --release --example cis_witness          > $R/labs/logs/safe/HARDEN-WITNESS/cargo_test_cis_witness.log   # R=/home/user/Ranger3143
cargo test -p aegis-core --release                  > $R/labs/logs/safe/HARDEN-WITNESS/cargo_test_aegis_core.log
../scripts/devloop.sh fmt                            > $R/labs/logs/safe/HARDEN-WITNESS/devloop_fmt.log
cd /home/user/Ranger3143/labs/safe
python3 -I harden_witness.py rerun     # h1_rerun.tsv, h1_rerun_outputs.jsonl.gz, mutant_archive_check.txt
python3 -I harden_witness.py controls  # controls.tsv, controls_outputs.txt, gen_equivalence.tsv, panic_samples.txt, binaries.sha256.txt
python3 -I harden_witness.py fuzz      # fuzz.tsv
python3 -I harden_witness.py report    # this file
```

Per-mutant commands (as SAFE-01, `nice -n 5`, `OMP_NUM_THREADS=1`, `AEGIS_THREADS=1`, `2` when the BitNet-2B artifacts are involved, 2 parallel workers):

```
cis_witness verify           <MODEL.SAF> <EMBED.BIN> <VOCAB.BIN> <mutant receipt>
cis_witness verify --strict  <MODEL.SAF> <EMBED.BIN> <VOCAB.BIN> <mutant receipt>
```

Environment lines (from the logs): cargo: cargo 1.97.0 (c980f4866 2026-06-30); rustc: rustc 1.97.0 (2d8144b78 2026-07-07); kernel: Linux 6.18.44-fc-v80; vcpus: 4; branch: lab/vnni-cis1, parent commit before this change: 3d706c2; cis_witness.rs lines: 1089

## 7. Limits and negative results

- `--strict` hardens the verifier, not the file. Without the TPM quote nothing stops someone from presenting a different, equally canonical receipt; the quote binds the whole file only for `RECEIPT.TXT` (SAFE-01 section 0, item 5), and `attest_verify.py` still needs `--receipt` for that.
- Four of the five golden fixtures were not replayed (artifacts absent on this host); for those the evidence is that the reader accepts them (unit test and CLI reaching the hash comparison), not a full strict PASS.
- The lenient default reader still accepts everything SAFE-01 listed (reorder, `+25`, upper-case hex, CRLF, unknown lines, unread `prompt-toks`/`gen-toks`). That is deliberate, to keep default behaviour identical; whoever needs integrity must pass `--strict`.
- The UEFI verifier (`aegis-uefi/src/verifier.rs::parse_receipt`) and the standalone `cis-verify` crate have their own lenient readers and were not changed; the same classes of leniency exist there. `agent_trace` receipts use another format and another verifier.
- The strict reader accepts `token-ids ` with a trailing space only for `gen-toks 0`, because that is what both writers print; it is the single exception to "no trailing whitespace".
- The mutant corpus is SAFE-01's; strict was tuned against the leniency classes it found, so the fuzz set (section 4) is the check that does not share that origin.

## 8. Commit and patch series

```
commit: 1799ea3c9814d9d85a3606aeed2697fedb152e08 lab(witness): cis_witness verify --strict and panic-free receipt parsing (LAB-09 HARDEN-WITNESS)
 aegis-linux/Cargo.toml              |    7 +
 aegis-linux/examples/cis_witness.rs | 1006 +++++++++++++++++++++++++++++++----
 2 files changed, 923 insertions(+), 90 deletions(-)

branch: lab/vnni-cis1 (local only, not pushed)
format-patch 3e3f465..HEAD --numbered vs R/patches: 0001..0003 differ from the existing files only in line 4 ([PATCH n/3] became [PATCH n/4]); all other lines identical.
decision: kept the existing 0001-0003 untouched; wrote only R/patches/0004-lab-witness-cis_witness-verify-strict-and-panic-free.patch (git format-patch -1 HEAD --start-number 4 --numbered), byte-identical to the 0004 of the full series.
0004 reverse-applies cleanly at HEAD (git apply --check --reverse): yes
0004 sha256: 9c3e9f3bc054c7531c884b6c6a388e8ae54b99da68f62a0865805dd9e9c855ba
pre-existing, untouched: scripts/devloop.sh fmt reports aegis-uefi FAIL (rustfmt diff in a crate this change does not touch)
```

