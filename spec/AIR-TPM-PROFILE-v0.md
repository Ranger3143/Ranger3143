# Attested Inference Receipt — TPM Measured-Boot Profile (AIR-TPM v0) and Model Boot Manifest

Status: Aefinity AI Inc. working draft v0, 2026-10-06. Reference implementation: `aegis-uefi/src/attest.rs` + `tpm2min` + `labs/attest_verify.py` (LAB-04). Intended as (a) an attestation profile for the IETF individual draft `draft-tsyrulnikov-rats-attested-inference-receipt-02` ("AIR v1"), which today profiles only AWS Nitro and Intel TDX and states it "attests the CPU-side TEE only", and (b) a CoRIM/RIM-style reference-value profile ("Model Boot Manifest") for AI appliances. Nothing here is IETF-adopted; "MUST/SHOULD" is used in the RFC 2119 sense within this document only.

## 1. Problem
AIR v1 binds `model_hash`, `request_hash`, `response_hash` and `attestation_doc_hash` to a confidential-computing enclave's measurement registers (48-byte SHA-384 Nitro PCRs or TDX MRTD/RTMRs). Commodity edge hardware — laptops, industrial PCs, kiosks, the machines AI appliances actually ship on — has no SGX/TDX/SEV-SNP but almost universally has a TPM 2.0 (discrete or firmware) and UEFI measured boot. No published profile covers that platform class, and none covers the case where the inference engine itself IS the booted image (no OS). Separately, no manifest format pins firmware reference values, the engine binary, and the model/tokenizer digests together (OMS signs weights+config+tokenizer; CoRIM carries firmware values; SPDX AIPackage has no runtime/firmware fields).

## 2. Platform model
- Root of trust for measurement: UEFI firmware + TPM 2.0 (TCG PC Client Platform Firmware Profile). PCR 0-7 = firmware/platform configuration; **PCR 4** = the booted EFI application (the inference engine binary), measured by firmware.
- The booted image (the "engine") extends two further PCRs through `EFI_TCG2_PROTOCOL.HashLogExtendEvent`, each event logged in the TCG2 crypto-agile event log with `EV_IPL` (0x0000000d) type and printable ASCII event data:
  - **PCR 12 — payload**: one event per loaded artifact, in load order: `AEGIS-MEASURE v0 artifact=<8.3 name> bytes=<decimal> sha256=<64 hex>` for MODEL (weights), EMBED (embedding/LM head table), VOCAB (tokenizer), and, if present, RECEIPT (a receipt being verified) or any other input the engine acts on (system prompt file, tool manifest, policy — same line grammar, same PCR).
  - **PCR 13 — transcript**: one event per inference episode: `AEGIS-RECEIPT v0 mode=<verify|mint> steps=<n> cis-digest=<16 hex> chain=<64 hex> verdict=<PASS|FAIL|MINTED>`.
  The PCR value is therefore `fold(SHA256(line_i))` and replayable from the event log without trusting the engine.
- Attestation key: a TPM-resident restricted signing key. v0 reference uses a transient ECC P-256 primary under the owner hierarchy created at boot (no certificate). Deployments SHOULD use an AK certified against the Endorsement Key (TPM2_MakeCredential/ActivateCredential or a provisioning-time `TPM2_Certify`) so the quote identifies a specific TPM via the manufacturer EK certificate chain.
- Quote: `TPM2_Quote(signHandle=AK, qualifyingData=SHA-256(receipt bytes), inScheme=NULL (key default ECDSA/SHA-256), PCRselect=sha256:{4,12,13})`. Implementations MUST resend an unchanged TPM2_Quote on warning-class `TPM_RC_RETRY`/`TPM_RC_YIELDED`/`TPM_RC_NV_RATE` responses (observed deterministically on libtpms; firmware interfaces do not resend for you). Deployments SHOULD also include PCR 0-7 in the selection once reference values for the platform are enrolled.

## 3. Receipt data model (profile of AIR v1 claims)
Reusing AIR v1's CWT claim keys where semantics match; new or changed claims are marked.

| claim | AIR v1 key | AIR-TPM v0 value |
|---|---|---|
| `eat_profile` | 265 | `"https://aefinity.ai/air-tpm/v0"` (placeholder URI) |
| `model_id`, `model_version` | -65537/-65538 | e.g. `"microsoft/bitnet-b1.58-2B-4T"`, `"cis1-fullint-50256"` |
| `model_hash` | -65539 | SHA-256 of the artifact manifest (§4) — `model_hash_scheme = "sha256-manifest"` |
| `request_hash` | -65540 | SHA-256 of the prompt bytes (witness `prompt-hex`) |
| `response_hash` | -65541 | **the CIS-1 witness chain** (SHA-256 over every step's token id and full integer logit vector). CHANGED semantics: this hash is REPLAYABLE — any conforming CIS-1 implementation recomputes it from (artifacts, prompt, steps). |
| `attestation_doc_hash` | -65542 | SHA-256 of `TPMS_ATTEST ‖ TPMT_SIGNATURE` (the TPM2_Quote output) |
| `enclave_measurements` | -65543 | map `{"measurement_type": "tpm2-pcr-sha256", "pcr4": <32 B>, "pcr12": <32 B>, "pcr13": <32 B>, optional "pcr0".."pcr7"}`. CHANGED: 32-byte SHA-256 registers (AIR v1 requires 48 bytes; a verifier implementing both profiles keys the length on `measurement_type`). |
| `policy_version` | -65544 | the CIS spec version the chain was computed under, e.g. `"CIS-1 v1.0.3"` |
| `security_mode` | -65548 | `"production"` iff Secure Boot was on and the AK is EK-certified; else `"evaluation"` |
| `eat_nonce` | 10 | optional verifier nonce; when present it is folded into `qualifyingData = SHA-256(receipt bytes ‖ nonce)` |
| NEW `tpm_quote` | TBD (private) | the raw `TPMS_ATTEST` and `TPMT_SIGNATURE` bytes, plus the AK `TPM2B_PUBLIC` (and EK cert chain when available). Carried so the receipt is self-contained offline. |
| NEW `event_log_excerpt` | TBD | the PCR 12/13 event lines (ASCII) — what a verifier replays. |
| NEW `replay` | TBD | `{"semantics": "CIS-1", "mode": "fullint", "token_ids": [...], "cis_digest": <8 B>}` — enough to rerun the inference. |
| `iat`, `cti`, `iss` | 6, 7, 1 | as AIR v1 (a no-OS engine takes `iat` from UEFI GetTime; MAY be absent → verifier relies on `eat_nonce`) |
Signature: AIR v1 uses Ed25519 COSE_Sign1 by a workload key bound into the TEE evidence. In AIR-TPM the TPM quote already signs the PCRs that commit to the receipt line; the COSE_Sign1 envelope MAY be signed by the same AK (ECDSA P-256, `alg = -7`) or omitted in v0 (the quote is the signature). The plain-text form of the receipt (RECEIPT.TXT witness v1 + ATTEST.TXT) is the v0 wire format; CBOR/COSE encoding is specified for interop with AIR verifiers.

## 4. Model Boot Manifest (reference values)
A signed JSON/CBOR document the fleet controller holds per appliance class:
```
{ "manifest": "aegis-mbm/v0",
  "engine":  {"name": "aegis-uefi", "efi_sha256": "<hex>", "pcr4_expected": "<hex>", "build": "<git sha>", "target": "x86_64-uefi-hardfloat"},
  "payload": [ {"artifact": "MODEL.SAF", "bytes": N, "sha256": "<hex>", "source": "microsoft/bitnet-b1.58-2B-4T@a1f2f1c", "transform": "repack_ternary.py --source-packing hf1bitllm --llama3-prune --scale-convention multiply"},
               {"artifact": "EMBED.BIN", ...}, {"artifact": "VOCAB.BIN", ...} ],
  "pcr12_expected": "<fold of the payload lines>",
  "semantics": {"spec": "CIS-1 v1.0.3", "conformance_digest": "76985613c965f643"},
  "firmware": {"corim_ref": "<optional CoRIM for PCR 0-7>"},
  "signature": "<Sigstore/OMS or vendor key>" }
```
It is the SBOM analogue for an inference appliance: engine binary + model + tokenizer + semantics + firmware reference, pinned together, and checkable against a quote. CycloneDX ML-BOM / SPDX AIPackage can carry the same fields as an extension; OMS signatures cover the artifact set.

## 5. Verification procedure
1. Parse `ATTEST.TXT`/receipt; verify the quote signature with the AK public key (and the AK against the EK chain when present).
2. Check `TPMS_ATTEST.extraData == SHA-256(receipt bytes [‖ nonce])` and `pcrDigest == SHA-256(PCR4 ‖ PCR12 ‖ PCR13)` over the claimed register values.
3. Replay PCR 12 and 13 from the event lines; they MUST equal the quoted values.
4. Compare PCR 4 (and 0-7 if selected) with the Model Boot Manifest's expected values → this names the engine binary (and platform).
5. Compare the PCR 12 artifact digests with the manifest → this names the model bytes.
6. Optionally, replay the inference under the named semantics (CIS-1) from (artifacts, prompt, steps) and require `chain == response_hash`. This step is unique to this profile: it does not need the TPM at all, and it catches a compromised TPM or firmware that attests honestly to a wrong computation.
Reference verifier: `labs/attest_verify.py` implements 1-3 and 5; `cis_witness verify` / the kit stick implement 6.

## 6. Security considerations
- Two independent roots. A forged TPM cannot forge a correct replay; a buggy or malicious engine cannot forge a quote over PCRs it did not extend (the firmware extends PCR 4 before the engine runs). An attacker needs both the platform and the arithmetic.
- The transient owner-hierarchy AK of v0 proves "some TPM"; production needs EK certification (standard TPM remote-attestation practice; Keylime does this for Linux hosts).
- Event-log replay is only as strong as the firmware's TCG2 implementation; CoRIM reference values for PCR 0-7 close the firmware side.
- Privacy: receipts are linkable via the AK; rotate AKs per deployment or use the TPM's EK-privacy ("ActivateCredential") pattern.
- Out of scope: sampling/temperature (CIS-1 is greedy), batching, GPU/NPU accelerators (no TCG2-style measurement exists for them), bf16 serving (CIS-2 covers fp32 semantics on Linux/GPU and could carry the same receipt line into PCR 13 from a Linux measured-boot host).

## 7. Relationship to prior art
AIR v1 (Nitro/TDX only, SHA-384 registers, non-replayable response hash); OpenSSF Model Signing (static artifact signatures, no runtime binding); CoRIM/TCG RIM (firmware reference values, no AI artifacts); SCITT RFC 9943 (transparency for statements; a receipt here can be registered as a statement); TOPLOC (approximate activation commitments for FP inference — the opposite tradeoff to exact replay); Keylime (TPM attestation for Linux hosts, no inference semantics); Tinfoil/Phala/EQTY (datacenter GPU TEE receipts). To our knowledge no prior artifact combines commodity measured boot, an OS-less engine, and a replayable receipt; see research briefs 03/04 for the searches that support that statement.
