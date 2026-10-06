# LAB-05 — Row-parallel CIS-1 decode on Linux: bit-identical by construction, 2.0x at 4 threads (VM)

Date: 2026-10-06. Machine: FINGERPRINT.txt (Intel Xeon fam 6 model 207, 4 vCPU KVM, **env=vm**; Rule A: ratios only). Branch `lab/vnni-cis1`: `aegis-core/src/cis_infer.rs` (`tmv_dispatch` + `logits_int` under `feature = "parallel"`), `aegis-linux/examples/cis_decode_timed.rs`.

## What was built
The CIS-1 FullInt path (`CisEngine`) was single-threaded in every build; the `parallel` worker pool existed only for the f32 engine. This lab fans the integer path out over the existing pool:
- every ternary matvec (q/k/v/o/gate/up/down) splits its OUTPUT ROWS across workers; each worker runs `cis_vnni::ternary_matvec_i8_vnni` on its row slice (VNNI -> AVX2 -> scalar fallback inside);
- the LM head (50,256 exact i64 dots) splits its vocab rows the same way;
- threshold: >= 2^20 MACs and >= 8 rows, so k/v_proj (640x2560) and up qualify; attention/softmax/norms stay serial (they are O(seq·head_dim), not the bandwidth term).

Why this needs no bit-exactness A/B: each output row is an independent integer dot product, and a worker computes exactly the same row with exactly the same instruction sequence it would have on one thread. Nothing about the arithmetic — not even the summation order inside a row — depends on the split. The f32 engine's parallel path can only assert the same by test (and the ledger records cases where thread count moved f32 tokens, e1_detprobe). The digest check below is therefore a regression guard, not the proof.

## Measurement (`cis_decode_timed`, 2B artifacts from LAB-02, prompt "Once upon a time", 64 tokens, 3 repeats each, decode loop only, model load excluded)
`labs/logs/cis_decode_timed_threads_run1.log`

| AEGIS_THREADS | median decode s | tok/s | speed-up | digest (every repeat) |
|---|---|---|---|---|
| 1 | 10.203 | 6.27 | 1.00x | cab11400d737ac4a |
| 2 | 6.760 | 9.47 | 1.51x | cab11400d737ac4a |
| 4 | 5.114 | 12.52 | 2.00x | cab11400d737ac4a |

Prefill (4 prompt tokens, batched path): 0.44 s -> 0.29 s -> (see log).

membw on the same VM (`labs/logs/membw_1t_run2.log`, `membw_4t_run2.log`): sequential read 1 thread 6.5-6.9 GB/s, 4 threads 21-25 GB/s (3.2-3.7x). So the memory system scales ~3.5x with 4 vCPUs while decode scaled 2.0x: the remaining gap is the serial part (attention core, SOFTMAX-I, norms, the per-matvec deinterleave, the broadcast barrier ~210 times per token) — an Amdahl slice `amdahl_decode` can name on iron.

## Reading
- Per-token bytes ≈ 778 MB (521 MB ternary + 257 MB BF16 head). At 1 thread 6.27 tok/s = 4.9 GB/s effective, ~72% of this VM's single-core sequential read. At 4 threads 12.5 tok/s = 9.7 GB/s of the 21-25 available: the integer decode is no longer bandwidth-bound at 4 threads; it is serial-fraction-bound. Parallelising the attention core (heads are independent — also bit-identical by construction) is the next lever, then the LM head bytes.
- This is the first multi-threaded CIS-1 decode in the program (the ledger's 2026-09-06 verify-timing report: "the verify path has no `parallel` feature"). On penguin-class hardware the same change should roughly halve the ~35 s single-threaded 2B receipt verification recorded there.
- For the unikernel the same row split maps onto firmware MP Services (APs as persistent workers): the integer semantics make bare-metal multicore a zero-risk change numerically — the only risks are the AP bring-up and cache/IPI plumbing. Design in `design/ALICE-NEXT-LEVEL-roadmap.md`.

## Caveats
- VM, 4 vCPUs of unknown topology (SMT siblings or distinct cores unknown); absolute tok/s are not product figures. Ratios are the result; iron re-run required (Rule A).
- `AEGIS_THREADS` default = physical cores (ops::worker_threads); the pool is the f32 engine's, unchanged.
