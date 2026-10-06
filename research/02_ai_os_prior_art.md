# Prior-Art and Design-Space Brief: An LLM-Run Operating System (bare-metal, headless-fleet + user environment)

Date: 2026-10-06. Research agent brief (sources checked against primary where possible; items marked (sec.) rest on secondary press).

## 1. Prior art

The field splits into four strata, and nothing yet spans them: (a) agent frameworks that call themselves an OS (Python processes over Linux), (b) vendor OSes adding an on-device model + agent sandbox (Windows, Apple, Android), (c) computer-use agents that drive an existing OS via GUI/API, and (d) bare-metal LLM inference with no OS at all. The missing stratum is an actual kernel/supervisor whose scheduler, policy and update loop are LLM-mediated.

| Project | Date / status | Lang | What it actually does | Claim vs reality |
|---|---|---|---|---|
| AIOS (Rutgers) arXiv 2403.16971 | Mar 2024; v5 Aug 2025; COLM 2025; last release v0.2.2 (Mar 2025); 6.4k stars | Python | uvicorn service ("kernel") scheduling LLM calls, agent context/memory/storage, tool access; up to 2.1x faster agent serving claimed | "OS" is a userspace daemon over Linux |
| LSFS (AIOS semantic FS) ICLR 2025, arXiv 2410.11843 | Oct 2024 | Python | NL "syscalls" (semantic CRUD, group-by, join, rollback) over an embedding index | Library over POSIX FS, not a VFS |
| MemGPT -> Letta | Paper Oct 2023; rename Sep 2024 | Python/TS | Context window as "RAM", archival tiers as "disk" | Memory metaphor only |
| MemOS arXiv 2507.03724 | Jul 2025 | Python | "MemCube" memory abstraction with scheduling/access control | Library |
| Karpathy "LLM OS" | Nov 2023 | Concept | LLM as kernel process orchestrating tools | Never implemented as such |
| Microsoft UFO2 "Desktop AgentOS" arXiv 2504.14603 | Apr 2025 | Python | HostAgent + AppAgents; UIA + vision; PiP isolated virtual desktop | Runs on Windows as an app |
| Windows 11 agent workspace + agent connectors (MCP) | Dec 2025 Insider; Build 2026 "Windows Agent Runtime" (sec.) | C++/C# | Agents in a separate Windows session under a low-privilege account; six known folders with Allow/Ask/Never; tamper-evident audit log; MCP on-device registry; off by default; explicit XPIA warning | Closest shipping thing to "LLM as system service with OS-enforced boundary"; model not in kernel |
| Apple Intelligence / Foundation Models (WWDC25/26) | Swift API; WWDC26 adds "Core AI" for local full-size LLMs on ANE | Swift | On-device system LM as Swift API; App Intents | Per-app assistant platform |
| Android AICore / Gemini Nano 4; AppFunctions ("Android MCP") | 2026 preview | Kotlin | AICore system service runs the model; apps expose tools | System model service, not operator |
| Agent S3 (Simular) | Oct 2025; 69.9% OSWorld | Python | GUI agent | External operator |
| OpenAI Operator -> ChatGPT agent -> "dots" | dots launched 29 Sep 2026: always-on agents each with a cloud computer | n/a | Cloud VM per agent | Hosted sandbox |
| Anthropic computer use + sandbox-runtime | bubblewrap/seccomp/Seatbelt open-sourced | TS | OS-primitive sandbox for agent tool processes | Userspace sandbox |
| Rivet agentOS | Jul 2026, Apache-2.0 | Rust + V8/Wasm | In-process "virtual OS": POSIX FS, processes, 4.8 ms cold start, ~22 MB/agent | V8/Wasm isolate, not a kernel |
| cllm | 2026, early | C | Multiboot x86 unikernel with e1000 + llama.cpp-shaped HTTP API | Inference not yet integrated |
| NIGHTRUN github.com/hardrave/NIGHTRUN | 2026; 299 stars; MIT | Rust (no_std "where it counts") | UEFI-resident (stays in Boot Services): GOP framebuffer, firmware USB keyboard, firmware MP services multicore; Llama 3.2 1B/3B, Granite 3B, Qwen3 4B; ~20 tok/s (1B) QEMU/KVM, 3-6 tok/s on Raspberry Pi 5 | Proves "boot into an LLM" on x86_64 UEFI + aarch64; no scheduler, no network, no storage beyond firmware |
| alice-aegis (Aefinity, internal baseline) | Jul-Aug 2026 | no_std Rust | BitNet 2B on UEFI x86-64; CIS-1 bit-exact integer semantics; receipts | Same stratum as NIGHTRUN; no OS services |

2025-26 academic LLM-centric OS abstractions: HiveMind (arXiv 2604.17111) admission control / AIMD backpressure / token budgets for agents as an HTTP proxy; PackServe, SMetric, HexAGenT (serving schedulers); MemGPT/MemOS/Context Cartography (memory hierarchy); LSFS (semantic FS, userspace only); "Model-Native Computing Architecture" (arXiv 2606.00288) LLM->CPU, KV cache->cache, context->RAM, probabilistic execution plane + deterministic control plane, no implementation; "Integrating AI into OS: a survey" (2407.14567). Intent-based system management below the Kubernetes-operator level: nothing credible found.

## 2. Headless fleet management (Oct 2026)

| Layer | Representative tech | Reusable for an LLM OS |
|---|---|---|
| Immutable, API-only host | Talos Linux 1.14 (no SSH; mTLS gRPC machine-config; Talos Hypervisor alpha Oct 2026); Bottlerocket v1.66.0 (UKI boot variants); Flatcar 4757.2.0 (CNCF incubating); Fedora CoreOS moving to OCI/bootc | Declarative machine config over authenticated API is the surface an LLM supervisor should emit and reconcile |
| Device fleet / OTA | Balena; Mender (MCU client Apr 2026); Torizon 7.1; RAUC/SWUpdate A/B; Greengrass v2.18 (Rust component SDK Apr 2026); Azure IoT Edge 1.6 LTS to Nov 2028; NVIDIA Fleet Command (low signal) | A/B slot + health-gated rollback + delta OTA is table stakes |
| Edge Kubernetes | k3s, KubeEdge, Rancher Fleet | GitOps reconciliation is the right fleet model |
| Reproducibility | NixOS fleets (colmena, deploy-rs, cattix drift detection); Guix | Content-addressed closures = verifiable "what is this machine running" + atomic rollback |
| Measured/attested boot | systemd UKI + systemd-measure PCR 11; Keylime (CNCF; TPM 2.0 + IMA continuous attestation); TPMSpy (2609.05011) | Controller must refuse to task a node whose PCRs mismatch the signed image; the LLM's weights and policy must be measured |
| Supply chain | CycloneDX 1.7, SPDX 3.0, OpenVEX, in-toto + Sigstore as OCI artifacts | Weights, tokenizer, policy bundles need SBOM/attestation identical to code |

Gaps: no fleet system treats model weights, prompts, tool manifests and policies as first-class attested, rollback-able artifacts; no fleet controller has an intent -> machine-config -> verified apply loop with an LLM in it; no attestation scheme covers "which model with which system prompt is operating this node".

## 3. Rust OS / unikernel landscape (Oct 2026)

| System | Maturity | x86_64 UEFI / aarch64 | Drivers | Net / FS | LLM embedded? |
|---|---|---|---|---|---|
| Redox | Microkernel, self-hosting rustc (Jan 2026), "Redox Rings", ARM64 SMP | Yes / Yes | Partial USB/NVMe/some NICs; no WiFi/GPU accel | smoltcp-derived; RedoxFS | No (forbids LLM-generated contributions, Mar 2026) |
| Asterinas (arXiv 2506.03876) | Framekernel, Linux ABI, 230+ syscalls; 2026 goal production on x86-64 VMs/TDX | x86-64 Tier 1; aarch64 Tier 3 | Virtio-centric | Linux-compatible | No |
| Theseus | Dormant since Sep 2024 | x86_64 | thin | smoltcp | No |
| Hermit v0.13.0 (Feb 2026) | Unikernel, active | QEMU/Firecracker/Uhyve | Virtio only | smoltcp; virtio-fs | No |
| Unikraft 0.22 | C libOS; Rust bindings; Unikraft Cloud; Hyperlight integration | KVM/Firecracker | Virtio; some bare-metal NICs | lwIP | No LLM in catalog |
| Nanos | Single-process unikernel | hypervisors | Virtio | own | PyTorch inference reports only |
| MirageOS | OCaml on Solo5 | KVM/Xen | Virtio/Solo5 | own | No |
| seL4 + Microkit 2.3.0 + rust-sel4 5.0.0 | MCS FC proved on RISC-V (Jun 2026); AArch64 confidentiality proof (Aug 2026); x86_64 FC only | Yes / Yes | sDDF user-level Rust drivers for virtio and selected NICs; no NVMe/xHCI/GPU breadth | sDDF + smoltcp/lwIP | No |
| Hubris (Oxide) 1.79-1.81 | Production SP firmware | Cortex-M | n/a | n/a | No (exemplary task isolation, no-alloc) |
| Tock 2.2 (1 Oct 2026); Embassy | MCU | n/a | n/a | n/a | No |
| UKL | Patches Linux 6.3; stalled since 2024 | x86_64 | Linux | Linux | No |
| Firecracker / rust-vmm / Cloud Hypervisor | Production; first escape-class CVEs 2026 (CVE-2026-5747 opt-in virtio-pci) | both | virtio | guest | Hosts LLM guests |
| Kata 4.0 (Jul 2026) runtime-rs | Rust-first | both | via host | via host | Hosts LLM guests |
| wasmCloud 2.5 / Spin / Hyperlight-Wasm (1-2 ms start) | WASI P3 on Wasmtime 46; Wasmtime 49 | portable | needs host | WASI | Whisper STT demoed; CPU-only LLM feasible |

Linux kernel Rust: non-experimental in Linux 7.0 (12 Apr 2026); Android Binder (6.12), Nova NVIDIA GSP (6.19), Tyr Mali (6.18); DRM to require Rust for new drivers within ~a year.

Has an LLM inference engine been embedded in any Rust OS/unikernel/microkernel? No. Only the "no OS" stratum: NIGHTRUN and alice-aegis (UEFI apps), cllm (C, incomplete).

## 4. Code-type comparison

| Option | Memory safety | Drivers | Attestation | Updates | Inference perf | Time to prototype | Risk |
|---|---|---|---|---|---|---|---|
| A. no_std Rust kernel + Rust userland | High | Very low (no GPU/WiFi; thin NVMe/xHCI) | Build yourself | Build yourself | CPU-only; 3-20 tok/s for 1-2B | 12-24 mo demo, 5+ yr fleet | Very high |
| B. Linux immutable UKI image + Rust supervisor | High in supervisor; kernel C+Rust | Complete (CUDA/ROCm/NPU) | Mature: UKI PCR 11, TPM2, Keylime, IMA, Sigstore | Mature: A/B, bootc/OSTree/OCI, Nix | Best | Weeks | Low; residual Linux attack surface mitigated by Landlock/seccomp/eBPF + microVMs |
| C. Unikernel (Hermit/Unikraft) + Wasm components under Firecracker | Medium-high | Virtio only; host still Linux | via host | image replace per VM | CPU-only | Months | Medium (two systems) |
| D. seL4 Microkit + Rust servers | Highest (proved kernel on AArch64/RISC-V; x86_64 FC only) | Minimal | strong foundation, no stack | build yourself | CPU-only | 6-12 mo demo | High on x86_64 |

Recommendation (agent): build on B now with a hard rule making D a later substitution: LLM runtime, policy engine and supervisor as one Rust crate graph (no_std-clean core, std shim) that touches the world only through a narrow capability-typed machine interface (filesystem, network, process, display, update, attestation). On Linux: Landlock + seccomp + cgroups + eBPF; immutable UKI image; Keylime attestation. Keep the bare-metal UEFI inference path as recovery / attestation-root mode and "boot sentinel".

## 5. Security and assurance requirements

1. Capability-based authority (Windows agent workspace baseline; PORTICO arXiv 2606.22504 revocable capabilities; Agent libOS arXiv 2606.03895 three-plane admission; AgentKernel 2609.29647).
2. Policy engine in the syscall path: Cedar (CNCF; default-deny; SMT-analyzable; Rust evaluator; GA in Bedrock AgentCore 3 Mar 2026) over OPA; ActPlane (arXiv 2606.25189) in-kernel eBPF enforcement, 1.9-8.4% overhead.
3. Prompt-injection containment as information-flow control: CaMeL (DeepMind, 2503.18813), CaMeLoT (2609.18674), SkillGuard reachability-based capability confinement (2608.30041).
4. Least agency / least autonomy: Singapore Consensus 2026 (2608.14611); Parisel "Theory of Least Autonomy" (2607.09744) blast-radius metric; AgentWarden (2604.11839); reduced-supervision paradox (2609.29547); AI Agent Index (2602.17753).
5. Formal verification: seL4 status above; Hubris small/no-alloc; Rust verification tooling (Kani 2607.01504, Corten 2609.04372, std verification 2606.17374).
6. Sandbox substrate: Firecracker 2026 CVEs; "AI Code Sandboxes" study (2606.08433); sandbox-runtime, nono (Landlock); microVM per agent at the heavy end.
7. Audit: tamper-evident intent+outcome logs; attestation of model+prompt+policy bundle via TPM PCRs and signed in-toto statements.

## 6. What nobody has built yet

1. A kernel/PID-1 supervisor whose scheduling and admission control are LLM-mediated with the LLM itself under capability and budget control.
2. Intent syscalls at the VFS/driver layer (LSFS is userspace only).
3. Taint-propagating, reachability-based capability confinement enforced by the kernel.
4. Attestation covering model weights, tokenizer, system prompt, tool manifests and policies as measured-boot components, plus a fleet controller that refuses to task nodes on PCR mismatch.
5. Fleet OTA where weights/prompts/policies are A/B slots with health-gated rollback and SBOM/VEX.
6. Intent -> declarative machine-config -> verified apply -> observe loop on-node without a cloud control plane.
7. An LLM inference service inside any Rust OS, unikernel or seL4 system.
8. A runtime-enforced blast-radius / least-autonomy metric.
9. A dual-plane (probabilistic execution + deterministic control) architecture realized as an actual kernel/user boundary.
10. Any formal argument about an LLM-operated system's safety properties above the kernel.

## 7. Ten most citable sources

1. Mei et al., AIOS, COLM 2025. https://arxiv.org/abs/2403.16971
2. Shi et al., LSFS, ICLR 2025. https://arxiv.org/abs/2410.11843
3. Zhang et al. (Microsoft), UFO2, Apr 2025. https://arxiv.org/abs/2504.14603
4. Microsoft, Experimental agentic features. https://support.microsoft.com/en-us/windows/ai/ai-features/experimental-agentic-features
5. Debenedetti et al. (DeepMind), CaMeL, 2025. https://arxiv.org/pdf/2503.18813
6. Zheng et al., ActPlane, Jun 2026. https://arxiv.org/abs/2606.25189
7. Xiong et al., SkillGuard, Aug 2026. https://arxiv.org/abs/2608.30041
8. Parisel, A Theory of Least Autonomy in AI, Jul 2026. https://arxiv.org/abs/2607.09744
9. Peng et al., Asterinas, 2025. https://arxiv.org/abs/2506.03876
10. seL4 Foundation news. https://sel4.systems/news/
Supporting: LWN Dec 2025 https://lwn.net/Articles/1050174/; NIGHTRUN https://github.com/hardrave/NIGHTRUN; Redox priorities https://www.redox-os.org/news/development-priorities-2025-09/; AWS Cedar https://aws.amazon.com/blogs/security/why-policy-in-amazon-bedrock-agentcore-chose-cedar-for-securing-agentic-workflows/; HiveMind https://arxiv.org/abs/2604.17111

## 8. Uncertainty register
NVIDIA Fleet Command lifecycle low signal; several 2026 dates secondary-press only; OSWorld figures not independently verified; Hermit/Unikraft bare-metal NIC support untested; alice-aegis is the requester's own org, not independent prior art.
