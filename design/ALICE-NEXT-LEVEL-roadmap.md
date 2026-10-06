# ALICE — next level: from a verified engine to an attested, multicore, fleet-grade sentinel

2026-10-06. Ordered by evidence-per-effort; every item names its gate. Rule A/B/C/D as in `CLAUDE.md`.

## Done in this session (branch `lab/vnni-cis1`, patch in `patches/`)
| item | gate passed | ledger-style one-liner |
|---|---|---|
| AEGIS-ATTEST v0 (TPM PCR 12/13 measurement, PCR read, event log, TPM2_Quote, ATTEST.TXT) | QEMU/OVMF + swtpm, both verify and mint modes; host verifier replays PCRs and checks the quote with OpenSSL; tampered attest rejected | first TPM-attested, no-OS inference receipt (identity only; iron pending) |
| Receipt MINT inside the unikernel | minted RECEIPT.TXT byte-identical to `tests/golden/witness_v1_m7_once64.receipt`; Linux `cis_witness verify` PASS | mint == verify arithmetic across firmware and Linux |
| `tpm2min` | 34 unit tests; 25/25 end-to-end vs swtpm with tpm2-tools + OpenSSL + independent parser; builds for `x86_64-unknown-uefi` | no_std/no-alloc/no-unsafe TPM 2.0 wire format; TPM_RC_RETRY on first quote documented |
| `cis_vnni` | 4/4 equivalence tests (13 shapes + hazards); `tmv_dispatch` test; 2B digest unchanged | first CIS-1 VNNI kernel; 1.25-1.36x cache-resident, 1.11-1.15x DRAM-streaming vs AVX2 (VM ratios) |
| Row-parallel CIS-1 decode (Linux) | digest identical at 1/2/4 threads; 6.3 -> 9.5 -> 12.5 tok/s on the VM (ratios 1.51x / 2.0x) | first multithreaded CIS-1 path; bit-identical by construction |
| `repack_ternary.py --scale-convention` | repack of microsoft/bitnet-b1.58-2B-4T reproduces `cab11400d737ac4a` | P1 tool bug fixed; digest reproduced from re-derived artifacts on a 4th microarchitecture |

| A.L.I.C.E. boot dashboard (GOP panels, live token stream, attestation view, footer stage bar) | QEMU mint + verify boots exit 33 with swtpm; minted RECEIPT.TXT byte-identical to the golden; host verifier PASS on both quotes (LAB-06) | the screen is a view, never an input: receipts unchanged |
| Tool-call baseline on the receipt-gated gateway (BitNet-2B, 180 items over three runs) | correct-argument 45/58 on the pre-registered suite; `unknown_fact` decide-to-look-up 0/30 (no demonstration) and 22/30 (LOOKUP demonstrated); distractor no-tool precision 29/30 and 30/30; 180/180 receipts verified (LAB-07) | the baseline ALICE-Next must beat; abstention and grammar fidelity are now gates |
| Prior-art check of every "first" | 16 hunts, 22 evidence checks: 0 novel, 16 partially novel, 8 done-in-repo (NOBODY-HAS-DONE-THIS.md) | what remains ours is the composition plus the receipts; brief sentences that failed are withdrawn |
| Scale-sensitivity leg reproduced | 31 of 210 scales moved by 1 ulp → digest 803e07941964ed37 vs cab11400d737ac4a, divergence at token 5, both texts coherent (LAB-02 addendum, labs/logs/scaleleg/) | only the exact digest sees it |

| ALICE-Next plan (replacement edge model) | nine research briefs + verification pass; design panel chose to evolve the BitNet-2B family (rung A operator-tuned, rung B pruned) with zero engine delta; 57-row audited license ledger; frozen gates; 90-day plan and first Kaggle notebook `e1-evolve-pilot` (model/README.md, model/00-05) | plan only; nothing trained; six decisions are Justin's (size-cap unit, external teacher, counsel on lineage, conversational gate, compute tier, PUBLISH?) |

## Next (ordered)
1. **Iron first-light for attestation** — Dell i5-5200U, HP N4020, Acer: stage the attest kit (`make-kit-image.sh` + MINT.TXT or RECEIPT.TXT), boot, archive ATTEST.TXT + BOOTLOG under `docs/hardware_logs/`, run `attest_verify.py`. Gate: PCR 4 == firmware's hash of the exact `.efi`; quote verifies; EK certificate present (fTPM). Risk: firmware without TCG2 protocol or with TPM disabled → the code logs and continues (finding, not failure).
2. **EK-certified AK** — provisioning step on Linux (`tpm2_createek`/`createak`/`makecredential`) with the AK handle persisted; unikernel uses the persistent AK handle instead of a transient primary. Gate: quote verifies against the manufacturer EK chain.
3. **Secure Boot ON** — sign `BOOTX64.EFI` with an owner key enrolled in `db` (sbsign + KeyTool/`mokutil`-free path since there is no shim). Gate: boots with Secure Boot enabled; PCR 7 reflects it. This is the exact thing NightRun cannot do.
4. **Multicore bare metal (MP Services)** — persistent AP workers started once via `startup_all_aps` (non-blocking), spinning on an atomic job descriptor; BSP publishes (row range, fn, args) per matvec; integer semantics guarantee identity. Gate 1: QEMU `-smp 4` digest identical to single-core (correctness). Gate 2: iron tok/s 1 vs N cores (Rule A) with `env=iron`. Expected: the 2B receipt verification drops from minutes to tens of seconds on a 4-core laptop. Also a differentiator vs NightRun: multicore WITH provable identity.
5. **cis_avx2/cis_vnni in the unikernel** — the `not(target_os = "uefi")` cfg keeps the UEFI CIS path scalar; with the hard-float target this restriction is unnecessary. Gate: QEMU digest identical; iron timing. (5.3x measured on Linux box1 for the AVX2 kernel, 2026-09-06.)
6. **Attention-core parallelism** — heads are independent; LAB-05 shows decode is serial-fraction-bound at 4 threads. Gate: digest identical; Amdahl slice shrinks.
7. **LM head bytes** — 257 MB of the 778 MB per token is the BF16 tied head. Two-stage head (int8 candidates + exact BF16 rescoring of top-k) must stay CIS-1-exact: candidate selection may only prune rows whose exact score provably cannot win (bound from int8 error). Gate: digest identical on the pinned suite; bytes/token measured.
8. **BITCOS-style packing** (-21% ternary bytes at 1.578 bpw for 2B-4T) — only after 7; container change touches the spec (§4 packing) and the forge; gate: new conformance digests, old ones kept.
9. **Receipt suite publication** — golden digests for BitNet-2B and Falcon-E-1B over a prompt set; CI on Intel/AMD/Arm; the HALL-OF-DIVERGENCE pattern. Gate: a third party reproduces.
10. **AIR-TPM profile** — COSE/CWT encoding of ATTEST.TXT fields; reference verifier in Rust (`cis-verify` lineage); PUBLISH? item before anything public; IETF RATS individual draft only after two physical TPMs reproduce.

## Settled negatives from this session (do not re-propose without new silicon)
- 4-row-blocked zmm VNNI kernel: slower than 1-row on Sapphire-Rapids-class (68 vs 78 GMAC/s resident; 24.5 vs 25.1 streaming). Likely spills; kept behind `set_force_r4`.
- Kernel-level work for CIS-1 decode on a single core: the path is at ~90% of measured single-core sequential bandwidth when streaming; instruction tricks cannot help decode on such a core. Cores and bytes/token can.

## Housekeeping found on the way
- QEMU `fat:rw:` vvfat loses guest-written files (BOOTLOG/ATTEST/RECEIPT never appeared); `xtask` gates that read guest files should use a real FAT image (mtools) — `labs/tools/boot.sh` does.
- The 2026-10 nightly refuses `#[target_feature(enable="avx2")]` on the stock soft-float UEFI target ("enabling the sse target feature ... unsupported"), so `cargo xtask boot-test` (stock target) no longer builds; the hard-float target builds fine. xtask should build via `build_hardfloat.sh --qemu-test`.
- `repack_ternary.py` default scale convention silently produces token salad for Microsoft BitNet packed checkpoints (fixed; `auto`).
