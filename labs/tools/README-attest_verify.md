# attest_verify.py: host-side verifier for AEGIS-ATTEST v0

`attest_verify.py` checks the `ATTEST.TXT` the unikernel writes after a boot with a TPM (see LAB-04, `spec/AIR-TPM-PROFILE-v0.md`).
Pure Python standard library plus the `openssl` binary. It prints one line per check (`... PASS` / `... FAIL`),
then `ATTEST VERIFY PASS|FAIL` and `QUOTE VERIFY PASS|FAIL`. Exit status: `0` everything passed, `1` at least one
check failed, `2` usage or parse error.

```
python3 -I labs/tools/attest_verify.py ATTEST.TXT --receipt RECEIPT.TXT --strict --expect-pubkey <128 hex> [--efi BOOTX64.EFI] [--artifacts DIR]
```

## Verification notes

These notes describe the hardened verifier (HARDEN-ATTEST, LAB-09). The measured effect of each check against the SAFE-01 attacks
is in `labs/logs/safe/HARDEN-ATTEST/RESULT.md`; the pre-hardening verifier is kept as `labs/logs/safe/HARDEN-ATTEST/attest_verify_before.py`.

### What is checked

| area | check | fails when |
|---|---|---|
| file form | header is exactly `AEGIS-ATTEST v0`; `pcr-bank sha256`; every `measured` / `event` / `pcr` / `quote-*` line matches the grammar the unikernel emits; no duplicate singleton lines; no `error`, `pcr-read-error`, `quote-error` or `eventlog:` line | a line is malformed or duplicated, or the unikernel reported an error. A wrong header is a parse error (exit 2) |
| PCR 12, 13 | replay `PCR_n = SHA256(PCR_{n-1} \|\| SHA256(line_n))` over the `measured pcr=n` lines, start 32 zero bytes, compare with the `pcr n` read-back | the values differ, or the `pcr` line is missing |
| event log, PCR 12/13 | every `measured` line has an `event` line at the same position for the same PCR with `sha256=` SHA-256(line), `data=` the line, and `type=0xd` (EV_IPL); an `event` line with no `measured` line is a failure | any of those differ, an event is missing, extra or reordered |
| PCR 4 | replay the same extend rule over the `sha256=` digests of the `event pcr=4` lines and compare with `pcr 4`; PCR 4 events must be EV_EFI_ACTION (0x80000007), EV_SEPARATOR (0x4) or EV_EFI_BOOT_SERVICES_APPLICATION (0x80000003); the digest of the first two must equal SHA-256 of the logged data | the replay differs, an event has another type, or a digest does not match its data |
| receipt | with `--receipt`: the receipt's `chain` and `cis-digest` appear together in a `measured pcr=13` line, and the quote's `extraData` equals SHA-256 of the receipt file's bytes | the receipt was changed, replaced, or is not the one that was attested |
| artifacts | with `--artifacts DIR`: size and SHA-256 of each measured artifact found in `DIR` | a local file differs, or none of the measured artifacts is in `DIR` (artifacts not in `DIR` print `SKIP`) |
| quote | `TPMS_ATTEST` magic `ff544347`, type `8018`, no trailing bytes, one SHA-256 PCR selection; `extraData` equals `quote-qualifying`; `pcrDigest` equals SHA-256 over the selected PCR values read back; ECDSA P-256 / SHA-256 signature verifies under OpenSSL; a one-byte-flipped copy is rejected (negative control) | any of those differ |
| quote, unsigned lines | every PCR that appears in a `pcr`, `measured` or `event` line is in the quote's PCR selection (nothing is claimed that the quote does not cover); `quote-pcrs` equals the PCR list inside the signed `TPMS_ATTEST`; `quote-public` parses as a `TPMT_PUBLIC` for an ECC P-256 ECDSA/SHA-256 key with fixedTPM, fixedParent, restricted and sign set, and its point equals `quote-pub-x/y` and lies on the curve; the signed `qualifiedSigner` equals `H(TPM_RH_OWNER \|\| Name(quote-public))` (so the signed structure itself names this key as an owner-hierarchy primary); `quote-key` equals the description derived from those (`ecc-p256 ecdsa-sha256 owner-hierarchy transient (this boot)`); `quote-retries` is an integer in 0..16 | any of those differ |
| quote present | a file without a quote, or with a partial or garbled quote block (for example a `quote-attest` line with a trailing space), is a FAIL | always, unless `--allow-no-quote` and there is no quote line at all |

### Flags

| flag | effect |
|---|---|
| `--receipt RECEIPT.TXT` | bind the quote to a receipt (see above). **The receipt is not positional**: `attest_verify.py ATTEST.TXT RECEIPT.TXT` is a usage error (exit 2, "use --receipt"). Before the hardening a positional receipt was silently ignored |
| `--artifacts DIR` | compare measured artifact digests with local files |
| `--expect-pubkey HEX` | pin the signer: the quote's key must equal this P-256 point, 128 hex characters `x \|\| y` (130 with the `04` prefix is accepted). Without a pin the quote proves consistency with *some* P-256 key, not which TPM (a software key that re-signs a self-consistent edited file passes every other check) |
| `--strict` | canonical file form only: lowercase hex, 32-byte fields exactly 64 hex digits, no CR / blank / trailing-whitespace / unknown lines, final newline, the unikernel's line order, `cpuid` line grammar; requires `--receipt`; cannot be combined with `--allow-no-quote`. Does **not** reject high-s signatures |
| `--reject-high-s` | refuse an ECDSA signature with `s > n/2`. Separate from `--strict` on purpose: libtpms/swtpm does not normalise `s`, so about half of genuine quotes are high-s (4 of the 8 `final_step12000` boots), and rejecting them would fail good files. It also cannot stop malleation of a genuine high-s quote into a low-s one |
| `--efi FILE` | PCR 4's EV_EFI_BOOT_SERVICES_APPLICATION digest must equal the Authenticode SHA-256 of `FILE` (the EFI binary that was booted), and the logged `ImageLengthInMemory` and `ImageLinkTimeAddress` must equal the file size and the PE `ImageBase` (EDK2 behaviour) |
| `--allow-no-quote` | accept a file that has no quote line at all (older unikernel builds). Prints a warning; the file is then not origin-authenticated. Never use it on evidence |
| `--print-pubkey` | print the quote's key as `x \|\| y` and exit. **Not a verification**: it reads the file's own claim, so using it to pin the same file is circular. It is the trust-on-first-use way to enrol a key from a boot you trust |

### Where the pin comes from

Each `boot_shot.sh --tpm` run starts swtpm with a fresh state directory, so each boot has its own owner seed and its own attestation
key: the 8 `final_step12000` boots have 8 different keys. The unikernel's key is `TPM2_CreatePrimary` under the owner hierarchy with a
fixed template, so it is a function of the owner seed alone. `labs/tools/ak_from_swtpm.sh <swtpm state dir>` recomputes it on the host
from a *copy* of the saved state (tpm2-tools against a throwaway swtpm) and prints `x || y`; that is independent of the ATTEST.TXT
under test. `model/demo-operator/finalize.sh` calls it per boot and passes the result to `--expect-pubkey`. `AEGIS_AK_PIN` (128 hex)
overrides the derivation with an enrolled key.

### What is not authenticated

These fields are not covered by any PCR or signature, so the verifier can only check their format: the `cpuid` line, `quote-retries`
(range 0..16), the clock / reset counters inside `TPMS_ATTEST`, and the `data=` of the EV_EFI_BOOT_SERVICES_APPLICATION event beyond what
`--efi` binds (image address, device path; the unikernel logs at most 96 bytes of it). `RECEIPT2.TXT` is not compared with anything.
A pin proves "the TPM whose owner seed the host holds signed this", which for swtpm is software; on iron it would need the EK
certificate chain (LAB-04 limitation 5).
