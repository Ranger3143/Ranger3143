# Trustworthy Edge/On-Device LLM Deployment: Standards Gaps, Funding Fit, Newsworthiness
Research agent brief, 2026-10-06. Primary sources where possible; [unverified] marked.

## Bottom line
1. No accepted standard, benchmark, or reference implementation exists for any of (a) attested inference receipts, (b) cross-machine bit-exact inference, (c) signed hash-chained inference logs, or (d) a model boot manifest. Adjacent vendor products or individual IETF drafts exist, none WG-adopted, all datacenter-GPU-TEE oriented. The CPU-only / TPM-measured-boot / disconnected-edge variant is empty.
2. The "LLM boots from UEFI with no OS" headline was taken in July 2026 by NightRun (hardrave; CRC-32 verification only; Secure Boot disabled). The unclaimed, falsifiable headline is assurance: Secure Boot on, model measured into TPM PCRs, per-response signed receipt, bit-identical output hash across Intel/AMD/Arm.
3. Funding windows: DoW SBIR/STTR FY26 Release 6 closes Oct 21 2026 12:00 ET; NSF SBIR AI topic full proposals Nov 4 2026 (Project Pitch first); DARPA I2O office-wide BAA paused since Jun 9 2026.

## 1. Standards landscape
| Standard / framework | Scope | Model attestation? | Reproducible inference? | Status (Oct 2026) |
|---|---|---|---|---|
| NIST AI RMF 1.0 + AI 600-1 | Governance | No | No | Final |
| NIST IR 8596 Cyber AI Profile | Governance/cyber | No | No | Prelim draft Dec 2025 |
| NIST COSAiS overlays (IR 8605) | SP 800-53 overlays for AI | No | No | outlines Jan 2026 |
| NIST SP 800-193 | Firmware resiliency | No | No | Final 2018 |
| NIST SP 800-155 | BIOS integrity measurement | No | No | Retired Oct 2024 -> TCG PC Client FIM; SP 1800-34 |
| TCG TPM 2.0 / DICE / PC Client RIM / Attestation Framework v1.0 (Nov 2025) | Device measured boot, RIMs | Device only | No | "Attestation in the age of AI" blog May 2026, no spec |
| IETF RATS EAT (RFC 9711), CoRIM | Attestation tokens, reference values | Device only | No | CoRIM in WG Last Call Mar 2026 |
| IETF SCITT RFC 9943 (Jun 2026) | Transparency service + receipts | Generic; no AI profile | No | AI profiles are individual drafts |
| CCC/MITRE Continuous Remote Attestation v0.9.6 | Runtime attestation incl. model integrity, GPU TEEs | As architecture controls | No | review closed Aug 2026 |
| EU AI Act harmonised standards (CEN-CLC JTC 21), prEN 18229-1 | High-risk compliance | No | No | none in OJ as of Jun 2026; Annex III delayed to 2 Dec 2027 |
| ISO/IEC 42001, 5338, TR 24028 | AIMS, lifecycle | No | No | Final |
| ISO/IEC FDIS 24970 AI logging | What to log | No | No | FDIS Sep 2026; no crypto integrity |
| ETSI TS 104 223 | Securing AI baseline | No | No | Apr 2025 |
| OWASP LLM Top 10 2026 | Risk list | No | No | Aug 2026 |
| MITRE ATLAS v5.4.0 | Threat taxonomy | No | No | Feb 2026 |
| SLSA v1.2 / in-toto | Build provenance | No ML predicate | No | Nov 2025 |
| OpenSSF Model Signing 1.0 | Signed manifest of weights+config+tokenizer | Static artifact signing only; no device/runtime binding | No | Apr 2025; NVIDIA NGC signs all models |
| CoSAI Signing ML Artifacts | Adoption maturity | Level 3 "structured attestations" unspecified | No | Sep 2025 |
| C2PA 2.4 | Media provenance | No | No | Apr 2026 |
| CycloneDX 1.7 ML-BOM; SPDX 3.0.1 AI profile | BOM | No | No | AIPackage has no runtime/firmware/tokenizer-hash fields |
| MLCommons AILuminate v1.1; MLPerf Client v2.0, Tiny v1.3, Inference Edge | Safety; perf/power | No | No cross-hardware bit-exactness metric | Client v2.0 Aug 2026 |
| NSA/CISA guidance (Apr 2024, May 2025, Agentic AI May 2026) | Best practice | Recommends signatures; no mechanism | No | Published |
| FedRAMP 20x AI; CMMC 2.0 | Authorization | No | No | CMMC L2 from Nov 10 2026 |
| DARPA GARD, Assured Autonomy, AIQ, CLARA, AI Forward, DICE | Research | Robustness, not deployment attestation | No | mostly closed |

## 2. Gap statements
(a) Attested inference. Exists: datacenter GPU-TEE products only (Tinfoil SEV-SNP/TDX + H100 + Sigstore; Phala/RedPill enclave-signed hash(request)||hash(response) on H100; NEAR AI; Apple PCC transparency log; EQTY Lab Verifiable Compute on Blackwell TEE-I/O, proprietary). Research: SVIP, EnclaveX (2606.31408). Does not exist: any standardized receipt format binding {device boot measurements, model digest, tokenizer digest, decode config, input digest, output digest}. draft-noa-scitt-ai-agent-receipt-01 (Aug 2026) carries no model hash and no I/O hashes; draft-messous-eat-ai-01 expired. Nothing targets CPU-only edge with TPM 2.0/DICE measured boot. GAP: no spec or reference implementation for an inference receipt rooted in commodity measured boot rather than a GPU TEE.
(b) Bit-exact cross-machine inference. Exists: Thinking Machines batch-invariant kernels (same-system; ~61.5% overhead); Gensyn RepOps/Verde (canonical reduction order, <30% matmul overhead; open-source status unclear); TOPLOC (approximate by design); int-llm (TinyLlama-1.1B Q16.48 fixed point, golden hash on x86-64/arm64/RISC-V/AVR at ~0.2 tok/s, 5 stars); Hatta AGI-26 seven requirements, no code. Does not exist: a conformance test/benchmark for cross-ISA bit-exact decode; no public golden-hash corpus for a >=1B model bit-exact across x86 and Arm at usable speed. GAP: no standard, benchmark or reference implementation for bit-exact LLM decode across heterogeneous hardware at practical throughput.
(c) Signed hash-chained inference log. Exists: SCITT RFC 9943 (content-agnostic); draft-sharif-agent-audit-trail-06 (Sep 2026, individual; SHA-256 chaining, optional model_weights_digest, not chain-binding); ISO 24970 / prEN 18229-1 define what to log; EU AI Act Art. 12 no crypto requirement. GAP: no accepted per-inference hash-chained signed log bound to device attestation and model digest that works offline and registers later to SCITT.
(d) Model boot manifest. Exists: OMS manifests (weights+config+tokenizer; nothing about runtime/kernel/firmware); SPDX AIPackage lacks runtime/firmware/tokenizer hash; TCG RIM / IETF CoRIM carry firmware reference values but no AI artifacts; NightRun CRC-32, Secure Boot off. GAP: no spec unifying firmware reference values, inference-engine binary digest and model/tokenizer digests into one signed manifest measured into PCRs and checked remotely. A "CoRIM profile for AI appliances" plus a Secure-Boot-signed unikernel extending PCRs with MODEL/VOCAB digests would be a first.

## 3. Funding fit (FY2026-FY2027)
| Program | Topic / ID | Deadline | Award | Fit |
|---|---|---|---|---|
| DoW SBIR/STTR FY26 Release 6 | DAF26TZ06-NV006 AI Performance Evaluation Tool (STTR); DAF26TZ06-NV007 Automated Combat Assessment at the Edge; DPA26BZ06-DV026 Influence Benchmarks for AI Systems (DARPA SBIR); ARM26BX06-NV012 agentic auditable decisions; DAF26BX06-DV511 low-SWaP-C payload | Oct 21 2026 12:00 ET | Phase I ~$140K-$305K; Phase II ~$1.7-2.05M | Medium |
| AFWERX Open Topic | D2P2 with Customer Memorandum | next window not announced [unverified] | Phase I $75-180K; Phase II $1.25-1.8M; TACFI/STRATFI | High with DAF customer |
| DARPA I2O office-wide BAA HR001126S0001 | trustworthy AI; resilient secure software | abstracts Nov 1 2026; paused since Jun 9 2026 | varies | High thematically; blocked |
| DARPA CLARA DARPA-PA-25-07-02 | high-assurance ML + automated reasoning | closed Apr 10 2026 | $2M/24 mo | watch follow-ons |
| DARPA DICE HR001126S0010 | decentralized AI in contested environments | closed Aug 25 2026 | 36 mo | closed |
| DARPA AI Forward / AIEs | rolling | rolling | ~$1M/18 mo | Medium |
| NSF SBIR/STTR NSF 26-510 | "sustainable AI for low-resource and edge environments", "technologies for trustworthy AI" | Pitch first; full proposals Nov 4 2026, Mar 4 2027 | Phase I up to $305K | High |
| NIST SBIR | AI frameworks/standards | FY27 [unverified] | $100K / $400K | High mission fit |
| Army W519TC-26-AE-AEEA Edge AI/ML | posted Apr 6 2026 | status [unverified] | | Medium |
Context: SBIR/STTR reauthorized Apr 13 2026 through Sep 30 2031; CMMC Level 2 certification on CUI contracts from Nov 10 2026.

## 4. Newsworthiness pattern
| # | Project | Date | Traction | Headline / metric |
|---|---|---|---|---|
| 1 | llamafile (Mozilla) | Nov 2023 | HN 1,075 pts | one file, 6 OSes |
| 2 | llama2.c (Karpathy) | Jul 2023 | HN 707 | one file of pure C |
| 3 | llm.c (Karpathy) | Apr 2024 | HN 1,050 | ~1000 lines; matches PyTorch; $672 in 24h |
| 4 | llama.ttf | Jun 2024 | HN 608 | a font which is also an LLM |
| 5 | GameNGen | Aug 2024 | HN 1,149 | DOOM in a diffusion model, 20 fps |
| 6 | Carlini GPT-2 in 3000 bytes of C | 2023/2024 | HN 350 | byte count |
| 7 | Microsoft BitNet / bitnet.cpp | Oct 2024; repost Mar 2026 | HN 173 / 370 | 100B 1-bit model on a single CPU at reading speed |
| 8 | EXO Llama on Windows 98 | Dec 2024 | press | vintage hardware |
| 9 | CraftGPT | Sep-Oct 2025 | video/press | absurd substrate |
| 10 | llm.pdf | Apr 2025 | social | LLM inside a PDF |
| 11 | NightRun | Jul 2026 | CNX, Hackster | boots straight into an LLM, no OS; CRC-32 only; Secure Boot off |
Pattern: one absurd, falsifiable constraint in the title; runnable artifact on day one; parity with a trusted reference; numbers HN quotes back (LOC, bytes, tok/s on named hardware); HN rewards engineering minimalism from credible names; ride a live trend.
Implication: "LLM from UEFI" alone is no longer first. The open, falsifiable headline is: Secure-Boot-signed LLM appliance; model measured into TPM PCRs; every response carries a signed receipt; output hash bit-identical on Intel, AMD and Raspberry Pi 5; verifier and golden hashes published. Fills gaps (a)-(d) simultaneously; beats int-llm 0.2 tok/s by >25x if ternary kernels hold >=5 tok/s; maps to NSF trustworthy-AI/edge and DoW eval topics; publishable as an IETF individual draft (EAT/SCITT inference-receipt profile) plus a CoRIM profile.

## Uncertainty notes
CCC/MITRE and EQTY pages 403 (secondary coverage); AFWERX/DOE/NIST FY27 timing unconfirmed; "SAFE-SiM" not found; HN scores point-in-time; "LLM on a Game Boy" not found.
