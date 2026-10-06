# ALICE-Next — requirements brief for the edge model that replaces BitNet-b1.58-2B-4T in ALICE

**Status:** brief (input to the design panel) · **Date:** 2026-10-06 · **Owner:** Aefinity AI Inc.
**Ask (verbatim intent):** "train/distill to the maximum a well-rounded and highly capable new model that will replace the model ALICE currently uses … a bold new class of edge model, one that is a tool expert, can converse, an air-gapped version and a version where ALICE has internet access and can fact-check herself when she doesn't know the answer … she just needs to know that she can pull tons of data and capability from it."

This brief fixes the *constraints* and the *gates*. It does not pick the recipe; the design panel does, and `01-…` onwards record its result.

## 1. What ALICE is, and what that forces on the model
ALICE is a `no_std` Rust UEFI unikernel (aegis-uefi) over an integer inference engine (aegis-core). The engine is the product; the model is a payload with a receipt. Everything below follows from four facts about the engine:

| Engine fact | Consequence for ALICE-Next |
|---|---|
| **CIS-1** pins integer decode semantics (ternary weights, int8 activations, i32/i64 accumulation, fixed rounding), so a decode is a digest that reproduces bit for bit on scalar, NEON, AVX2 and AVX-512 VNNI (labs/LAB-02, LAB-03, LAB-05). | Weights must be **ternary** (`{-1,0,+1}` × per-tensor scale) in the storage format `repack_ternary.py` emits (`MODEL.SAF` + `EMBED.BIN` + `VOCAB.BIN`). Any new layer type or activation needs a numbered CIS errata and goldens unchanged. |
| The engine implements the **BitNet-b1.58-2B-4T** architecture today: LLaMA-style decoder, RMSNorm (with BitNet's sub-norms), SwiGLU with ReLU², RoPE, GQA, tied or untied LM head over a **pruned 50k vocabulary** (ledger A35: +0.12% perplexity). | A model with the same architecture family drops in with **zero engine work**; a different family (MoE, Mamba, attention variants) is an engine project first. Vocabulary pruning must be reproducible from the public tokenizer. |
| Decode is **bandwidth-bound**: at the roofline the integer kernel reads ~90% of single-core DRAM bandwidth; the levers are cores and bytes/token (LAB-03, LAB-05). | **Smaller is faster, linearly.** 2.4B params ≈ 480 MB of packed weights read per token; 1.0B ≈ 200 MB; 0.6B ≈ 120 MB. Target hardware (laptops/mini-PCs/industrial boxes with 4–16 GB RAM, no GPU) wants ≤ 500 MB packed and prefers ≤ 300 MB. |
| Every run yields a **witness receipt** (`AEGIS-WITNESS v1-CIS`) and, under the agent gateway, a **trace receipt** (`AEGIS-TRACE v3`) binding each tool call's name/input/output to the decode chain; both are TPM-quoted at boot (LAB-04, LAB-06). | Tool calls must use a **strict grammar the gateway can parse** (`CALC(…)`, `LOOKUP(…)`, `FILE-READ(…)` today). Any new tool is a gateway + verifier change with its own fixtures. **Greedy decoding** is the receipt-grade mode (sampling would need a seeded, specified RNG in CIS). |

## 2. Capabilities required (and how each will be measured)
1. **Tool expert.** Emits a well-formed call exactly when one is warranted, with the right tool and a *verbatim* argument; handles two or more calls in one episode; never calls when a plain answer is correct. Baseline today (BitNet-2B, template T1, labs/LAB-07): correct-argument 45/58 = 77.6% overall; 100% on easy arithmetic and table hits; 73% / 62% call rate on hard and overflow arithmetic; 0/3 on two-tool items; red flags tripped on two buckets.
2. **Conversational.** Follows instructions, keeps a short multi-turn context, answers plainly in the voice of a competent operator, stays within a 24–64 token budget when asked. Today's 2B-4T is a base+instruct model with no ALICE-specific behaviour.
3. **Knows what it doesn't know.** On a question whose answer is in a declared table but not in its weights, it *looks it up* instead of guessing; on an unanswerable question it says so. Measured by the new `unknown_fact` bucket (n ≥ 30) and an enlarged `distractor` bucket (n ≥ 30) (run in progress, LAB-07 amendment).
4. **Two deployment variants, one model.**
   - **Air-gapped ALICE.** Tools: `CALC`, `LOOKUP`/`FILE-READ` over tables and files *declared* on the boot volume (their SHA-256 is folded into the trace receipt), sensors later. No network. Must prefer "look it up" / "not in my data" over fabrication.
   - **Connected ALICE.** Adds `SEARCH(<query>)` and `FETCH(<url>)` through the receipt-gated gateway. Because receipts must replay deterministically, fetched content is **snapshotted content-addressed** (bytes → SHA-256 → declared table entry) at fetch time, and the receipt records the snapshot digest; a verifier replays against the snapshot, never against the live web. The model's job is the *decision* to search, the query, and the **fact-check loop**: draft answer → search → compare → revise, every step in the trace. She does not need the facts in her weights; she needs the reflex and the discipline.
5. **Receipt-grade.** Loads and decodes in ALICE under QEMU (exit 33), produces a pinned CIS-1 digest on ≥ 3 microarchitectures before it ships, and verifies under the Linux tools byte-identically.

## 3. Hard constraints
- **Size:** packed weights ≤ 500 MB (hard), ≤ 300 MB (target); EMBED.BIN ≤ 400 MB; VOCAB.BIN pruned, ≤ 1 MB.
- **Architecture:** expressible in aegis-core today, or with a bounded, pre-costed engine delta (list it).
- **Licenses:** every training source and every teacher's output license recorded in a ledger with a yes/no for commercial use and for redistribution of derived weights; nothing with a research-only or non-commercial clause. Aefinity ships to customers.
- **Compute:** Aefinity has no training GPU on premises (penguin 6.4 GB RAM; box1/box2 CPU hosts; Kaggle notebooks are the compute for Kaggriculture). Plans must be tiered: Tier 0 free (Kaggle P100/T4, ~30 h/week), Tier 1 ≈ $500 of rented GPU, Tier 2 ≈ $5 000. Each tier states what it can and cannot reach.
- **Data provenance:** synthetic tool-call data is preferred where the gateway can **verify** the label (arithmetic results are exact; table lookups are exact; snapshot fetches are reproducible). Human-written conversational data only from permissively licensed sets.
- **Honesty rules:** no quality number is claimed before it is measured with a log (Rule B); no timing from QEMU/VMs (Rule A); the eval suite and its SHA-256 are frozen before training starts (pre-registration).

## 4. Acceptance gates (the model ships to the engine only when all pass)
| Gate | Threshold | Instrument |
|---|---|---|
| Tool correct-argument rate, every bucket | ≥ 95%, Wilson lower bound ≥ 85%, n ≥ 30 per bucket | `agent_trace` suite + `score.py` |
| Two-tool episodes | ≥ 90% exact output | `mixed` bucket, n ≥ 30 |
| No-tool precision on distractors | ≥ 95% | `distractor` bucket, n ≥ 30 |
| `unknown_fact`: looks up instead of guessing | ≥ 90% exact-key LOOKUP | new bucket |
| `unanswerable`: abstains | ≥ 90% | new bucket |
| Connected fact-check loop (synthetic fixtures) | ≥ 90% revised-to-correct when the snapshot contradicts the draft | new bucket + snapshot fixtures |
| Receipt verify | 100% | `agent_trace verify`, `cis_witness verify` |
| General quality | perplexity on the program's held-out text not worse than BitNet-2B-4T by more than 5% at ≤ half the bytes; or better at equal bytes | `aegis-eval … --cis-full` |
| CIS int-vs-float agreement | token agreement ≥ the 2B's measured value on the same text | `cis_decode` / `aegis-eval` |
| Boot gate | loads and decodes under QEMU, exit 33, digest pinned on ≥ 3 microarchitectures | `build_hardfloat.sh --qemu-test`, `labs/tools/boot_shot.sh` |
| Size | ≤ 500 MB packed | `ls -l`, `repack_ternary.py` log |

## 5. What the design panel must return
1. Architecture and size choice, with the engine delta (ideally none) and the bytes/token.
2. The training/distillation recipe: starting point (continue the 2B-4T, distill into a smaller ternary student, or train a new ternary model), stages, QAT details, token budget, teacher(s) if any, with licenses.
3. Data plan: sources, sizes, licenses, how much is synthetic-and-verified, how tool-call, conversation, abstention and fact-check data are generated and *checked by the gateway*.
4. Compute plan per tier with what each tier buys.
5. Evaluation protocol: the frozen suites (with the gates above), what is measured at each checkpoint, and the digest/boot pipeline.
6. Risk register (quality collapse under ternary QAT, license taint, eval leakage, overfitting to the gateway grammar, bandwidth regressions) with mitigations.
7. A 30/60/90-day plan and the first Kaggle notebook to write.

## 6. Non-goals (for this iteration)
No multimodal input; no speculative decoding or sampling in the receipt-grade path; no on-device training; no claim of parity with frontier models. The target is the best *receipt-grade* operator model that fits in 300–500 MB and knows when to reach for a tool.
