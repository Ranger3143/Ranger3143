# tpm2min lab — RESULT

**Status: PASS.** A dependency-free `#![no_std]` + `#![forbid(unsafe_code)]` Rust crate
(`tpm2min`) marshals/parses TPM2_Startup, PCR_Read, PCR_Extend, CreatePrimary, Quote and
FlushContext as raw TPM 2.0 Part-3 byte buffers. Driven against swtpm, the resulting
quote verifies (i) with `tpm2_checkquote` and (ii) independently with OpenSSL over our
own DER encodings (plus a third, independent Python/`cryptography` verifier). 25/25
end-to-end checks pass, including three negative controls.

## Environment (exact versions)

| Component | Version |
|---|---|
| swtpm | 0.7.3 (`swtpm --version`: "TPM emulator version 0.7.3, Copyright (c) 2014-2021 IBM Corp.") |
| libtpms | 0.9.3-0ubuntu4.24.04.1 |
| tpm2-tools | 5.6-1build4 (`tpm2_quote --version`: tool="tpm2_quote" version="5.6" tctis="libtss2-tctildr") |
| tpm2-tss (esys, tcti-swtpm) | 4.0.1-7.1ubuntu5.1 |
| OpenSSL | 3.0.13 30 Jan 2024 |
| Python / cryptography | 3.13.16 / 50.0.1 |
| rustc / cargo (stable) | 1.97.0 (2d8144b78 2026-07-07) / 1.97.0; clippy 0.1.97 |
| Rust targets | x86_64-unknown-linux-gnu, x86_64-unknown-uefi |

## Layout

```
tpm2lab/
  Cargo.toml                 workspace (tpm2min, tpm2min-cli)
  tpm2min/src/
    lib.rs      crate docs, wire-format conventions, buffer-size constants
    consts.rs   TPM_ST/TPM_CC/TPM_ALG/TPM_RH/TPMA_OBJECT/TPM_RC constants with Part 2 section refs
    wire.rs     Writer/Reader big-endian cursors over &[u8], fixed-capacity Tpm2b<N>
    sha256.rs   tiny SHA-256 (FIPS 180-4) for the PCR composite
    pcr.rs      TPMS_PCR_SELECTION / TPML_PCR_SELECTION, composite_sha256()
    cmd.rs      command builders (byte layout of every command in doc comments)
    rsp.rs      response parsers: header/rc, PCR_Read, CreatePrimary (+TPMT_PUBLIC ECC), Quote, TPMS_ATTEST
    der.rs      P-256 SubjectPublicKeyInfo DER, ECDSA-Sig-Value DER (for OpenSSL)
    error.rs    Error enum incl. TpmRc(u32), is_retryable()
  tpm2min-cli/src/main.rs    std driver: swtpm TCP transport, file dump, tpm2-tools/openssl/python verification
  verify_quote.py            independent verifier (hand parser + cryptography ECDSA)
  run_lab.sh                 starts swtpm, runs the CLI, tees output to out/
  out/                       all artefacts of the last run (see list below)
```

## Library API (all fixed-size, no alloc)

| Command | Builder (`cmd::`) | Parser (`rsp::`) | Wire size |
|---|---|---|---|
| TPM2_Startup(TPM_SU_CLEAR) | `startup(out, su)` | `startup(rsp)` | 12 B |
| TPM2_PCR_Read sha256:4,12 | `pcr_read(out, &PcrSelectionList)` | `pcr_read(rsp) -> PcrReadResult` | 20 B |
| TPM2_PCR_Extend (SHA-256, TPM_RS_PW) | `pcr_extend_sha256(out, pcr, &[u8;32])` | `pcr_extend(rsp)` | 65 B |
| TPM2_CreatePrimary (owner, ECC P-256 template) | `create_primary_ecc_p256(out, TPM_RH_OWNER)` | `create_primary(rsp) -> {handle, public: Tpm2b<384>, name, creation_hash}`; `ecc_public(&tpmt) -> {x,y,attrs,curve,scheme,...}` | 65 B |
| TPM2_Quote (TPM_RS_PW, inScheme NULL or ECDSA/SHA256) | `quote(out, handle, qd, SigScheme, &sel)` | `quote(rsp) -> {attest: Tpm2b<512>, signature: {r,s,hash_alg}, signature_raw (TPMT_SIGNATURE)}`; `attest(&[u8]) -> Attest` | 73 B (75 with ECDSA scheme) |
| TPM2_FlushContext | `flush_context(out, handle)` | `flush_context(rsp)` | 14 B |
| PCR composite | `pcr::composite_sha256(&[[u8;32]])` = SHA-256(PCR4 ‖ PCR12) | | |
| DER helpers | `der::p256_spki(x,y) -> [u8;91]`, `der::ecdsa_signature(r,s,out) -> len` | | |

Every builder returns `Result<usize, Error>` (bytes written) and back-patches `commandSize`.
Every parser validates: tag ∈ {0x8001,0x8002} and matching the command, `responseSize ==
buffer length`, `rc == 0` (else `Err(Error::TpmRc(rc))` *before* touching the body),
`parameterSize` consistency, the TPMS_AUTH_RESPONSE trailer, and end-of-buffer.
`Error::is_retryable()` classifies TPM_RC_RETRY/YIELDED/NV_RATE/NV_UNAVAILABLE.

Byte layouts are documented in the doc comments of each builder/parser with TPM 2.0 Library
Spec (rev 1.59) references: Part 1 §18 (marshalling), §19.4/Part 3 §5.3 (authorization
area), Part 2 §6.x (constants), §8.3 TPMA_OBJECT, §10.6/10.9 PCR selection, §10.12.8
TPMS_ATTEST, §11.3.3 TPMS_SIGNATURE_ECDSA, §12.2.4 TPMT_PUBLIC, Part 3 §9.3 Startup,
§18.4 Quote, §22.2 PCR_Extend, §22.4 PCR_Read, §24.1 CreatePrimary, §28.4 FlushContext.

### Hand-computed vectors covered by unit tests (`cargo test`, 34 tests, all pass)

* Startup: `80 01 00000000c 00000144 0000` (12 B); FlushContext(0x80000001): `8001 0000000e 00000165 80000001`.
* PCR selection sha256:4,12 → `000b 03 10 10 00` (PCR 4 = byte0 bit4, PCR 12 = byte1 bit4); list `00000001 000b 03 101000`.
* PCR_Read: `8001 00000014 0000017e 00000001 000b 03 10 10 00`.
* Password auth area: `00000009 40000009 0000 01 0000`.
* CreatePrimary (65 B): header `8002 00000041 00000131`, `40000001`, auth area, inSensitive `0004 0000 0000`,
  inPublic `0018` + template `0023 000b 00050072 0000 0010 0018 000b 0003 0010 0000 0000`, `0000`, `00000000`.
  Attribute word 0x00050072 = fixedTPM|fixedParent|sensitiveDataOrigin|userWithAuth|restricted|sign.
* PCR_Extend (65 B) and Quote (73/75 B) full byte vectors; Quote rejects qualifying data > 64 B.
* Parsers: rc≠0 → `Err(TpmRc)` for every command (incl. 0x100 on a second Startup); truncated / size-mismatch /
  bad-tag headers; synthetic PCR_Read, CreatePrimary (incl. wrong parameterSize), Quote responses; TPMS_ATTEST
  (bad magic, wrong type, truncation); ECC TPMT_PUBLIC (RSA rejected); DER padding/zero-stripping; SHA-256 FIPS vectors.

### Build/lint results

```
$ cargo test --workspace          -> test result: ok. 34 passed; 0 failed
$ cargo clippy --workspace --all-targets -- -D warnings   -> Finished (no warnings)
$ cargo build -p tpm2min --target x86_64-unknown-uefi     -> Finished (stable toolchain; proves no_std/no alloc)
$ cargo doc -p tpm2min --no-deps  -> Finished (deny(missing_docs) is on)
```

## End-to-end run against swtpm

swtpm command line (from `run_lab.sh`):

```
swtpm socket --tpm2 --tpmstate dir=$LAB/swtpm-state \
  --server type=tcp,port=2321 --ctrl type=tcp,port=2322 \
  --flags not-need-init,startup-clear --log file=$LAB/out/swtpm.log,level=20
cargo run --release -p tpm2min-cli -- --port 2321 --out $LAB/out --verify-py $LAB/verify_quote.py
```

Exact bytes sent/received by the CLI (`out/tpm_commands.log`):

```
TPM2_Startup       cmd: 80010000000c000001440000
                   rsp: 80010000000a00000100                  <- TPM_RC_INITIALIZE: already started by startup-clear (expected)
TPM2_PCR_Extend    cmd: 800200000041000001820000000c0000000940000009000001000000000001000b3f7c4a1d911ee3ebce7de5db4314d5e4057cc13ded24a65868bf8fa325f8787c
                   rsp: 80020000001300000000000000000000010000
TPM2_PCR_Read      cmd: 8001000000140000017e00000001000b03101000
                   rsp: 800100000060000000000000001500000001000b03101000000000020020 00..00(32) 0020 2381cdf857b374837390c8cd2ac6a432902a1354c3147bb842552679d7fb64be
TPM2_CreatePrimary cmd: 80020000004100000131400000010000000940000009000001000000040000000000180023000b00050072000000100018000b0003001000000000000000000000
                   rsp: 8002000001380000000080000000000001210058 0023000b00050072000000100018000b00030010 0020 74e294ad... 0020 cbf2ecf5... (312 B)
TPM2_Quote         cmd: 800200000049000001588000000000000009400000090000010000002087dec0093756f2a90bc609bcfc0e35e33613add96a53f02e015f7dcf4fa2ffbd001000000001000b03101000
                   rsp: 80010000000a00000922                  <- TPM_RC_RETRY (see caveat 1); identical command re-sent:
TPM2_Quote         rsp: 8002000000ee00000000000000db 0091 <TPMS_ATTEST 145 B> 0018000b 0020 <r> 0020 <s> 0000010000 (238 B)
TPM2_FlushContext  cmd: 80010000000e0000016580000000     rsp: 80010000000a00000000
TPM2_FlushContext  cmd: 80010000000e0000016580000000     rsp: 80010000000a000001cb   <- TPM_RC_HANDLE, parameter 1 (handle gone, expected)
```

Values produced (also in `out/`):

```
sha256("AEGIS-TEST")        = 3f7c4a1d911ee3ebce7de5db4314d5e4057cc13ded24a65868bf8fa325f8787c
pcrUpdateCounter            = 21
PCR[4]  (sha256)            = 0000000000000000000000000000000000000000000000000000000000000000
PCR[12] (sha256)            = 2381cdf857b374837390c8cd2ac6a432902a1354c3147bb842552679d7fb64be
                              (== SHA256(0^32 || sha256("AEGIS-TEST")), checked)
objectHandle                = 0x80000000
TPM2B_PUBLIC (90 B)         = 00580023000b00050072000000100018000b00030010 0020 74e294adaeca35b57625a76f72a9f98d732ad5459420fa505ce06d8a0fadae33 0020 cbf2ecf5db834740243a32f4858ddfe2beb1f2e66681428f752817c17f0689f1
  x                         = 74e294adaeca35b57625a76f72a9f98d732ad5459420fa505ce06d8a0fadae33
  y                         = cbf2ecf5db834740243a32f4858ddfe2beb1f2e66681428f752817c17f0689f1
name                        = 000b2ee06dbad745ddda383f5f5ea01f85f443dd2d56e119bb4b0c09c66d366b1138  (== 000b||SHA256(TPMT_PUBLIC), checked)
qualifyingData              = sha256("receipt-chain-test") = 87dec0093756f2a90bc609bcfc0e35e33613add96a53f02e015f7dcf4fa2ffbd
TPM2B_ATTEST (147 B)        = 0091 ff544347 8018 0022 000bd4effa622a863b0f9a00c8c334bed4eaa1a3b04f5d1430bb7312dc0931c9eb36 0020 87dec009...a2ffbd 000000000000065d 1d1e147c a7c611fb 01 f4a4fb241eb6d362 00000001000b03101000 0020 196488b0829f4a0aa90e93b03bf3f367023e8addb226ebf609f238c88d22ebb1
  magic/type                = 0xff544347 / 0x8018 (TPM_ST_ATTEST_QUOTE)
  qualifiedSigner           = 000bd4effa62... (== 000b||SHA256(TPM_RH_OWNER||name), checked; matches tpm2_readpublic "qualified name")
  extraData                 = 87dec009... (== qualifyingData)
  clockInfo                 = clock=1629 ms, resetCount=488510588, restartCount=2814775803, safe=1; firmwareVersion=0xf4a4fb241eb6d362
  pcrSelect / pcrDigest     = sha256:4,12 / 196488b0829f4a0aa90e93b03bf3f367023e8addb226ebf609f238c88d22ebb1 (== SHA256(PCR4||PCR12), checked)
TPMT_SIGNATURE (72 B)       = 0018 000b 0020 76ecc25a3a2b36f4691a4c00d9cc066de10b36a49fd940406b09e264be0b051c 0020 5833206613d87495095cd4835dd4c595a34451b8748cb7c64e8456935e601338
signature r||s              = 76ecc25a3a2b36f4691a4c00d9cc066de10b36a49fd940406b09e264be0b051c5833206613d87495095cd4835dd4c595a34451b8748cb7c64e8456935e601338
signature DER               = 3044022076ecc25a3a2b36f4691a4c00d9cc066de10b36a49fd940406b09e264be0b051c02205833206613d87495095cd4835dd4c595a34451b8748cb7c64e8456935e601338
```

Files written to `out/`: attest.bin (TPMS_ATTEST, 145 B), attest.hex, quote_tpm2b_attest.hex, attest_parsed.txt,
sig_tss.bin (TPMT_SIGNATURE, 72 B), sig_rs.hex, sig.der (70 B), pub_tpm2b.bin/.hex (TPM2B_PUBLIC, 90 B), pub_xy.hex,
pub.der (SPKI, 91 B), pub.pem, name.hex, pcr4.hex, pcr12.hex, pcrs.txt, qualifying.bin/.hex, attest_tampered.bin,
pcr.bin + pub_tools.pem + pub_tools.tpm2b (produced by tpm2-tools), tpm_commands.log, tools.log, cli_output.txt,
verify_summary.txt, swtpm.log.

## Verification

### (i) tpm2-tools (TCTI `swtpm:host=127.0.0.1,port=2321`, same swtpm, after the CLI released the data socket)

```
$ tpm2_pcrread -T swtpm:host=127.0.0.1,port=2321 -o pcr.bin sha256:4,12
  sha256:
    4 : 0x0000000000000000000000000000000000000000000000000000000000000000
    12: 0x2381CDF857B374837390C8CD2AC6A432902A1354C3147BB842552679D7FB64BE          -> equal to our PCR_Read values   PASS

$ tpm2_readpublic -T swtpm:host=127.0.0.1,port=2321 -c 0x80000000 -f pem -o pub_tools.pem
  name: 000b2ee06dbad745ddda383f5f5ea01f85f443dd2d56e119bb4b0c09c66d366b1138
  qualified name: 000bd4effa622a863b0f9a00c8c334bed4eaa1a3b04f5d1430bb7312dc0931c9eb36
  attributes: fixedtpm|fixedparent|sensitivedataorigin|userwithauth|restricted|sign (raw 0x50072)
  type ecc, curve NIST p256, scheme ecdsa/sha256, sym-alg null, kdfa null
  x: 74e294ad...fadae33  y: cbf2ecf5...0689f1
  -> pub_tools.pem is byte-identical to our pub.pem (DER SPKI built from x,y in Rust)      PASS

$ tpm2_readpublic -T swtpm:host=127.0.0.1,port=2321 -c 0x80000000 -o pub_tools.tpm2b
  -> 90 bytes, identical to our raw TPM2B_PUBLIC (size prefix + TPMT_PUBLIC)              PASS

$ tpm2_checkquote -u pub.pem -g sha256 -m attest.bin -s sig_tss.bin -f pcr.bin -l sha256:4,12 \
      -q 87dec0093756f2a90bc609bcfc0e35e33613add96a53f02e015f7dcf4fa2ffbd
  pcrs:
    sha256:
      4 : 0x0000000000000000000000000000000000000000000000000000000000000000
      12: 0x2381CDF857B374837390C8CD2AC6A432902A1354C3147BB842552679D7FB64BE
  sig: 3044022076ecc25a3a2b36f4691a4c00d9cc066de10b36a49fd940406b09e264be0b051c02205833206613d87495095cd4835dd4c595a34451b8748cb7c64e8456935e601338
  (exit 0)                                                                                 PASS

$ tpm2_checkquote -u pub_tools.pem ... (same args)             -> exit 0                   PASS
$ tpm2_checkquote ... -q 8810ad58...80225  (wrong qualifying data, negative control)
  ERROR: Error validating nonce from quote / ERROR: Verify signature failed! (exit 1)      PASS (rejected as expected)
```

### (ii) Independent: Rust parser + OpenSSL over our DER encodings

In-process (Rust, `rsp::attest` + `pcr::composite_sha256`): magic == 0xff544347, type == TPM_ST_ATTEST_QUOTE,
extraData == qualifyingData, pcrSelect == sha256:4,12, pcrDigest == SHA256(PCR4 ‖ PCR12), qualifiedSigner ==
000b ‖ SHA256(TPM_RH_OWNER ‖ name) — all PASS.

```
$ openssl dgst -sha256 -verify pub.pem -signature sig.der attest.bin
  Verified OK                                                                              PASS
$ openssl dgst -sha256 -verify pub.pem -signature sig.der attest_tampered.bin   (last byte of pcrDigest flipped)
  Verification failure                                                                     PASS (negative control)
$ openssl ec -pubin -in pub.pem -noout -text
  Public-Key: (256 bit) ... ASN1 OID: prime256v1, NIST CURVE: P-256                        PASS
```

(`pub.pem` is the SubjectPublicKeyInfo built by `der::p256_spki` from the TPM's x,y; `sig.der` is
`ECDSA-Sig-Value{r,s}` built by `der::ecdsa_signature` from the TPMT_SIGNATURE — no tpm2-tools involved.)

### (iii) Independent: Python (`verify_quote.py`, run with `python3 -I`, hand-written TPMS_ATTEST parser + `cryptography`)

```
python verifier: curve=secp256r1 key_size=256
  clock=1629 reset=488510588 restart=2814775803 safe=1 fw=0xf4a4fb241eb6d362
  [PASS] magic == 0xff544347
  [PASS] type == TPM_ST_ATTEST_QUOTE
  [PASS] extraData == qualifyingData
  [PASS] pcrSelect == [(sha256, [4, 12])]
  [PASS] pcrDigest == sha256(PCR4||PCR12)
  [PASS] qualifiedSigner == 000b||sha256(TPM_RH_OWNER||name)
  [PASS] ECDSA-P256/SHA256 signature over TPMS_ATTEST verifies
  [PASS] tampered attest is rejected
python verifier overall: PASS
```

### Summary table (`out/verify_summary.txt`)

| # | Check | Result |
|---|---|---|
| 1 | TPM2_Startup(CLEAR) (rc 0x100 TPM_RC_INITIALIZE accepted: swtpm already started it) | PASS |
| 2 | TPM2_PCR_Extend PCR12 ← sha256("AEGIS-TEST") | PASS |
| 3 | TPM2_PCR_Read returned 2 digests for sha256:4,12 | PASS |
| 4 | PCR12 == SHA256(0^32 ‖ sha256("AEGIS-TEST")) | PASS |
| 5 | CreatePrimary handle is transient (0x80000000) | PASS |
| 6 | outPublic echoes template (ECC/P-256/ECDSA-SHA256/attrs 0x00050072) | PASS |
| 7 | name == 0x000B ‖ SHA256(TPMT_PUBLIC) | PASS |
| 8 | Quote signature is ECDSA/SHA256 | PASS |
| 9 | attest.magic / attest.type | PASS |
| 10 | attest.extraData == qualifyingData | PASS |
| 11 | attest.pcrSelect == sha256:4,12 | PASS |
| 12 | attest.pcrDigest == SHA256(PCR4 ‖ PCR12) | PASS |
| 13 | attest.qualifiedSigner == 0x000B ‖ SHA256(TPM_RH_OWNER ‖ name) | PASS |
| 14 | tpm2_pcrread values == our PCR_Read values | PASS |
| 15 | tpm2_readpublic -f pem == our DER→PEM of (x,y) | PASS |
| 16 | tpm2_readpublic -o == our raw TPM2B_PUBLIC bytes (90 B) | PASS |
| 17 | tpm2_checkquote (our pub.pem, attest.bin, sig_tss.bin, pcr.bin) | PASS |
| 18 | tpm2_checkquote with tpm2_readpublic's PEM | PASS |
| 19 | tpm2_checkquote rejects wrong qualifying data (negative control) | PASS |
| 20 | openssl dgst -sha256 -verify pub.pem -signature sig.der attest.bin → "Verified OK" | PASS |
| 21 | openssl rejects tampered attest (negative control) | PASS |
| 22 | openssl parses pub.pem as P-256 | PASS |
| 23 | python3 verify_quote.py (independent) | PASS |
| 24 | TPM2_FlushContext(handle) | PASS |
| 25 | second FlushContext fails with TPM_RC_HANDLE (0x1cb) | PASS |

## Caveats and findings

1. **TPM_RC_RETRY (0x922) on the first TPM2_Quote after startup — a resend is mandatory.**
   On every fresh swtpm/libtpms instance the first `TPM2_Quote` returned the warning-class
   code 0x922 (RC_WARN+0x022 = TPM_RC_RETRY, "the TPM was not able to start the command");
   the *identical* command re-sent immediately succeeded. Bisected on fresh instances: it is
   independent of elapsed time since start (0 s vs 3 s), of a preceding PCR_Extend, of the
   session attributes (0x01/0x00), of inScheme (NULL/ECDSA) and of qualifyingData size — it is
   the first clock/orderly-NV-touching command after Startup. tpm2-tools never sees it because
   tpm2-tss ESAPI resends on TPM2_RC_RETRY (the Linux `tpm_transmit()` does the same). The
   library exposes `Error::is_retryable()` (RETRY/YIELDED/NV_RATE/NV_UNAVAILABLE) and the CLI
   transport resends up to 5 times; **the UEFI unikernel must do the same around
   `EFI_TCG2_PROTOCOL.SubmitCommand`, which returns the TPM response verbatim.** The wire
   format itself was never at fault (variant A of the bisect = the CLI's exact bytes succeeded).
2. **TPM2_Startup**: with `--flags startup-clear` swtpm already issued Startup, so ours gets
   0x100 TPM_RC_INITIALIZE; the CLI treats that as "already started". Firmware does the same
   on real hardware, so the unikernel should not send Startup at all (or accept 0x100).
3. **ECC vs RSA**: ECC P-256/ECDSA-SHA256 was chosen deliberately: 24-byte template, 88-byte
   TPMT_PUBLIC, 72-byte TPMT_SIGNATURE, 32-byte scalars, trivial DER (fixed 26-byte SPKI prefix),
   and no 2048-bit arithmetic or PSS/PKCS#1 encodings on the verifier side. The parsers return
   `Error::Unsupported(alg)` for RSA public areas / RSASSA signatures rather than mis-parsing.
   `symmetric` must be TPM_ALG_NULL for a non-storage signing key (a template with AES-CFB is
   rejected by the TPM with TPM_RC_SYMMETRIC — observed when `tpm2_createprimary -G
   ecc256:ecdsa-sha256` was used without `:null`).
4. **Session encoding**: a single `TPM_RS_PW` TPMS_AUTH_COMMAND with empty nonce, attributes
   0x01 (continueSession, as tpm2-tss does) and empty hmac → `authorizationSize = 9`. swtpm also
   accepts attributes 0x00 (verified). The response auth area is `0000 01 0000` (5 B) and is
   parsed/validated. No HMAC/policy sessions are implemented (no need for an unikernel with an
   empty owner auth); if the owner hierarchy had an auth value, the password would simply be
   placed in the hmac TPM2B (`password_auth_area(w, pw)` supports that).
5. **inScheme**: both `TPM_ALG_NULL` (use the key's scheme; default in the CLI) and explicit
   `ECDSA/SHA256` produce valid quotes (verified). `pcrDigest` is computed with the signing
   scheme's hash (SHA-256 here) over the concatenated PCR values in selection order.
6. **TPM2B_PUBLIC**: `CreatePrimaryResult::public` keeps the raw TPMT_PUBLIC; the CLI prefixes the
   2-byte size to form the TPM2B_PUBLIC, which matched `tpm2_readpublic -o` byte-for-byte. Name
   and Qualified Name are recomputed from it (Part 1 §16 / §26.5) and match the TPM's values.
7. **PCR_Read** returns at most 8 digests per call (TPML_DIGEST); the parser stores up to 8 and
   checks that `pcrSelectionOut` agrees with the count. Request fewer PCRs per call than 8 or
   loop on `pcrSelectionOut` if more are needed.
8. **tpm2-tools interop details**: `tpm2_checkquote -s` expects the marshalled TPMT_SIGNATURE
   (its default "tss" format) — exactly `signature_raw`; `-m` expects the bare TPMS_ATTEST (no
   size prefix); `-f pcr.bin` expects tpm2-tools' native-struct PCR file, so the CLI generates
   it with `tpm2_pcrread -o` from the same TPM and cross-checks the printed values against ours.
9. **swtpm transport**: swtpm serves one data-channel connection at a time; the CLI closes its
   socket before invoking tpm2-tools (which connect per command) and reconnects to flush.
   The raw TCP data channel framing is just the TPM command/response stream (read the 10-byte
   header, then `responseSize-10` more bytes).
10. Buffer sizing for the unikernel: `COMMAND_BUFFER_SIZE = 512` is ample for these commands;
    `RESPONSE_BUFFER_SIZE = 4096` covers the 312-byte CreatePrimary response with margin. Check
    `EFI_TCG2_BOOT_SERVICE_CAPABILITY.MaxCommandSize/MaxResponseSize` before relying on 4096.

## Reproduce

```
cd tpm2lab
cargo test --workspace && cargo clippy --workspace --all-targets -- -D warnings
cargo build -p tpm2min --target x86_64-unknown-uefi
./run_lab.sh            # starts swtpm on 2321/2322, runs tpm2min-cli, writes out/, exit 0 iff all checks pass
```
