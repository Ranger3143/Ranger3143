# Aefinity OS v2 — an attested, AI-operated machine (headless fleet node or user workstation)

Working design, 2026-10-06. Builds on `alice-aegis/program/AEFINITY_OS.md` (v0.1, 2026-08-31: JOB/NET/REPORT/RESIDENT/FLEET phases, all QEMU-gated) and the 2026-09-02 usefulness critique ("it is a firmware application, not an OS; the superstructure is not what makes the science stronger"). Grounded in research brief 02 (prior art, Rust OS landscape, code-type table) and in the labs of this session (LAB-02..05).

## 0. The claim this OS makes
"An AI operates this machine, and you can prove — not trust — what it was, what it ran on, and what it did." Every other 'AI OS' in brief 02 is an agent harness over an unchanged OS; the vendor OSes (Windows agent workspace, Apple, Android AICore) put a model behind an OS boundary but the human stays the operator and nothing is attested end to end. The empty stratum is a node whose model, prompts, tool manifests and policies are measured-boot components, whose every action is a hash-chained receipt, and which a controller refuses to task when the measurements are wrong. That is what Aefinity already has the parts for (CIS-1 receipts, the kit, and now AEGIS-ATTEST).

## 1. Two bodies, one trust chain (the decision)
Brief 02 §4 and the program's own critic agree: do NOT grow the unikernel into a general OS (drivers, scheduler, GPU, Wi-Fi are years). Instead:

| body | role | what runs | why |
|---|---|---|---|
| **ALICE (firmware body)** — the `aegis-uefi` unikernel, no OS | **sentinel + recovery root + attestation anchor**. Boots first (or on demand via one-shot `BootNext`), verifies/mints a CIS-1 receipt for the node's model set, extends PCR 12/13, obtains a TPM quote, writes ATTEST.TXT, then chains to the Linux body (or stays resident for pure-appliance SKUs). | CIS-1 integer inference (bit-exact), receipt mint/verify, TPM measurement + quote, JOB.TXT/MINT.TXT, optional smoltcp report | smallest possible TCB (one EFI binary + model files); the only body that can make the "no OS underneath" claim; already boots on three physical machines |
| **Linux body** — immutable image (UKI, A/B slots, bootc/OSTree or Nix closure), Rust supervisor as the single long-running service | **the daily machine**: fleet agent, tool execution, user environment, GPU/NPU if present, networking, updates | `aefinity-supervisor` (Rust): policy engine (Cedar), capability-typed machine interface, receipt gateway (from `demo/agent-trace/gateway`, safe-1..11), fleet client; any inference backend (aegis-linux CIS-1 for attested answers; llama.cpp/vLLM for fast unattested drafts) | complete drivers, mature attestation stack (UKI PCR 11, TPM2, Keylime), mature OTA; weeks not years (brief 02 table: option B) |

The trust chain across both bodies is ONE TPM event log: PCR 0-7 firmware → PCR 4 ALICE binary → PCR 12 model set → PCR 13 receipt → (chainload) PCR 11 Linux UKI (systemd-measure) → PCR 14/15 supervisor policy bundle + tool manifests measured by the supervisor at start. A single TPM quote over {4,11,12,13,14,15} describes the whole machine. The fleet controller's Model Boot Manifest (spec §4) pins all of it.

## 2. Headless fleet mode
- **Provisioning**: Debian/immutable image + `ALICE_UEFI` partition (already designed, `docs/UEFI-REMOTE-LANE.md`). Node identity = TPM EK; AK certified at enrollment (Keylime-style registrar, or `cm-fleet` doing `tpm2_makecredential`).
- **Boot**: firmware → ALICE sentinel (verify the pinned receipt for the installed model set; PCR 12/13; quote; POST ATTEST.TXT to the controller via smoltcp or hand it over on the shared partition) → `BootNext` cleared → Linux body boots, supervisor measures its policy bundle, requests a fresh quote with the controller's nonce.
- **Tasking**: the controller (`cm-os-pool` lineage, or Talos-style declarative machine config over mTLS) refuses to send jobs to a node whose quote does not match the manifest (gap #4 of brief 02 — nobody does this for model weights/prompts/policies today). Every job answer is a receipt (CIS-1 for attested inference; agent-trace receipts for tool calls — already exist); receipts append to a hash-chained log and can be registered to a SCITT transparency service later (RFC 9943).
- **Updates**: model/prompt/policy bundles are A/B slots exactly like the OS image (gap #5): the controller ships a new Model Boot Manifest + artifacts to the inactive slot; ALICE boots the sentinel against the new slot, mints the receipt, quotes; only a matching quote flips the slot. Rollback = the old slot's manifest still verifies.
- **Pooling**: embarrassingly parallel inference/eval shards across nodes, each result a receipt, merged by digest (phase 6 of v0.1; now with attested nodes).
- **Observability**: the receipt log + ATTEST.TXT history IS the audit trail (EU AI Act Art. 12 record-keeping, DoD IV&V): per inference, which model bytes, which binary, which machine, which output.

## 3. User-environment mode
Same two bodies; the Linux body runs a compositor/desktop (or a kiosk shell). The LLM is a system service behind the supervisor, following the only pattern that has shipped (Windows agent workspace / Apple / Android): a separate low-privilege agent account, an explicit capability grant UI (Allow/Ask/Never per folder, device, network, app), tamper-evident intent+outcome log — plus what none of them have: the model and policy the agent runs under are measured into PCRs and every agent action is a CIS-1/agent-trace receipt the user (or an auditor) can replay. "Headless or user" is a config flag on the supervisor (display capability granted or not), not a different OS.

## 4. Security architecture (what makes "AI-run" acceptable)
- **Capability-typed machine interface** (brief 02 §5.1): the model never gets a shell; it emits typed requests (fs.read, net.fetch, proc.spawn, display.show, update.apply, attest.quote) that the supervisor checks against Cedar policy (default-deny, statically analyzable, Rust evaluator) and executes under Landlock + seccomp + cgroups; eBPF (ActPlane pattern) enforces at the syscall layer so an indirect path cannot bypass the gateway.
- **Taint and least agency**: bytes that entered through perception (prompt, file, network) are tainted; authority available to a plan is a function of taint (CaMeL / SkillGuard patterns); each task gets a time-bound, scope-bound capability set (Singapore Consensus least-privilege-for-agents).
- **Receipts everywhere**: inference (CIS-1 witness), tool calls (AEGIS-TRACE v3), updates (manifest + quote). The "principle of least agency" becomes auditable: the blast radius of an episode is the set of capabilities its receipts show it used.
- **Dual plane**: probabilistic execution plane (the model) vs deterministic control plane (supervisor, policy, receipts, attestation) — the architecture position paper 2606.00288 as an actual process boundary.
- **Formal targets**: the control plane is small Rust (supervisor + tpm2min + witness + policy evaluator); Kani/Corten-class verification of the receipt parser and the capability checker is tractable; the kernel is Linux (or, for appliance SKUs on AArch64 once MCS proofs land, seL4 + Microkit — option D as a later substitution, per brief 02).

## 5. Code-type recommendation (direct answer to "research code types that are best for this idea")
| layer | language / runtime | why |
|---|---|---|
| Firmware body (sentinel, attested inference, recovery) | `no_std` Rust UEFI app (existing `aegis-uefi`) + `tpm2min` + `witness` | only way to make the no-OS claim; tiny TCB; already real |
| Inference engine | `no_std` Rust core (`aegis-core`) with CIS-1 integer semantics; std shim for Linux | one engine, two bodies, bit-identical results across both (LAB-04: receipt minted under firmware == Linux golden) |
| Supervisor / control plane | Rust (std), single binary, `no_std`-clean crates for everything that also runs in the firmware body (receipt format, manifest parsing, TPM wire) | memory safety where the authority lives; shared code = shared semantics |
| Policy | Cedar (Rust evaluator) | default-deny, analyzable, already chosen by AWS for agentic workflows |
| Tool/agent sandboxes | microVM per untrusted tool (Firecracker/Cloud Hypervisor, rust-vmm) or Wasm components (Wasmtime/wasmCloud) for pure-compute tools | container-only isolation is no longer adequate for agent code (brief 02 §5.6) |
| Node OS | immutable Linux image: UKI + systemd-measure (PCR 11), A/B slots (bootc/OSTree or Nix), Rust-in-kernel acceptable since Linux 7.0 | mature measured boot + OTA; GPU/NPU drivers |
| Fleet control | Rust service (or Python first — `cm-os-pool` exists) speaking declarative machine-config over mTLS; Keylime-style attestation registrar | Talos pattern + model-aware manifests |
| What NOT to write | a general-purpose kernel, drivers, a compiler in the unikernel, a GUI toolkit | brief 02 table: years, and no attestation benefit |

## 6. Phased plan (each phase = a verifiable gate, Rule A/B discipline)
1. **Sentinel on iron** (weeks 1-2): attested kit boot on Dell/HP/Acer with physical TPM; PCR 4 matches `.efi` hash; quote with EK chain; ATTEST.TXT archived under `docs/hardware_logs/`. Secure Boot: sign the `.efi` with an owner key enrolled in db (NightRun requires Secure Boot off; we should not).
2. **Chainload + unified event log** (weeks 2-4): ALICE → Linux UKI chainload; one quote over PCR 4,11,12,13; supervisor measures its policy bundle into PCR 14.
3. **Supervisor v0** (weeks 3-8): capability interface + Cedar + receipt gateway (port of `demo/agent-trace/gateway`) + fleet client; headless flag; `cm-fleet` refuses tasks on PCR mismatch.
4. **Model-aware A/B updates** (weeks 6-10): manifest-gated slot flip with sentinel re-verify.
5. **User environment** (weeks 8-14): compositor + agent account + capability UI; same supervisor.
6. **Multicore ALICE** (parallel track; design in `ALICE-NEXT-LEVEL-roadmap.md`): MP Services workers for the CIS-1 matvecs; the sentinel's 2B receipt verification on iron drops from minutes to tens of seconds.

## 7. Honest limits
- The firmware body stays x86_64 UEFI, CPU-only, greedy, 2B-class; it is the anchor, not the workhorse.
- "AI-run" means the model drives the machine through a typed interface under policy; it does not mean the model is the scheduler (brief 02 gap #1). We think that is the right boundary, and it is the only one the shipping vendors have found acceptable.
- Everything in §2-§5 beyond the sentinel is design; LAB-04 validates the sentinel under QEMU+swtpm only.
