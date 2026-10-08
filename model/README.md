# ALICE-Next — decision memo and index (read this first)

**Date:** 2026-10-06 · **For:** Justin · **Status:** plan, not a result. No ALICE-Next weights exist; no quality number is claimed anywhere in this directory. (2026-10-08: a small *demo* operator model now exists, see `demo-operator/` and `../labs/LAB-08`; it is the QEMU demo model, not a rung of this plan.)

## What was asked and what was built today
You asked for a bold new class of edge model to replace BitNet-b1.58-2B-4T inside ALICE: a tool expert that can converse, knows what it doesn't know, with an air-gapped variant and a connected variant that fact-checks herself. Today produced the research base, the measured baseline, the design decision and the plan, in that order:

| File | What it is |
|---|---|
| `00-ALICE-NEXT-brief.md` | the constraints the engine imposes and the acceptance gates (frozen before any training) |
| `research/R1..R9` | nine research briefs with cited claims and explicit gap lists; `R0-VERIFICATION-corrections.md` is an adversarial second read of the R1–R4 claims (31 verdicts, 6 corrected); `R0-SYNTHESIS-and-critique.md` is the cross-brief synthesis with a 19-item critique |
| `01-ALICE-NEXT-design.md` | the chosen design, with the engine delta (none), bytes per token, the grafts from the losing proposals and why they lost |
| `02-training-and-distillation-plan.md` | stages S0–S10 with kill gates, QAT details, hyper-parameter register, compute per tier with the arithmetic shown |
| `03-data-and-license-ledger.md` | 57 sources, each with licence, commercial use, redistribution of derived weights and a gateway-verified flag; license-audited row by row (91 verified tags, 17 unverified) |
| `04-eval-protocol-and-gates.md` | the frozen suites, the gates with instruments, the digest and boot pipeline, pre-registration rule |
| `05-risks-and-90-day-plan.md` | risk register, 30/60/90 plan, the first Kaggle notebook, Plan C, NEEDS candidates, and the completeness check's open gaps |
| `../labs/LAB-07-toolcall-baseline-bitnet2b.md` | the measured baseline the new model must beat (180 items over three runs, 180/180 receipts verified) |
| `../spec/AEGIS-FETCH-SNAPSHOT-v0.md` | how the connected variant fetches without breaking replayable receipts |
| `kaggle/` | the first notebook of the plan (E1 evolve pilot), smoke-executed on CPU; nothing run on a GPU yet |
| `demo-operator/` | the 17M-parameter ternary operator model trained on this CPU for the QEMU demo (`../labs/LAB-08`): corpus builders, gateway-verified episode generator, tokenizer, config, gate and probe scripts. A demo model, not an ALICE-Next candidate |

## The decision, and my reading of it
A panel of three independent proposals (evolve the incumbent; distill an Apache-2.0 Qwen3-1.7B into a ternary student; a purpose-built 0.3–0.8B operator model) was scored by three judges (engineering fit against the actual engine sources, licence and provenance, training risk against the cited evidence). The judges were unanimous: **evolve the BitNet-2B family** (operator-tune it as rung A, then structurally prune it to a ~1.0B body as rung B), zero engine change, with the operator model's data factory and the student plan's measurement discipline grafted in.

I accept that decision, with three things said plainly:

1. **The "new class" is the behaviour and the receipts, not a new base.** What is genuinely new in this plan is the gateway-verified data factory (every tool label is checked by the real receipt gateway, so the training signal cannot lie), the tool-state discipline (a tool exists only when declared, which is what makes one model serve both the air-gapped and connected units), the snapshot-based fact-check loop whose every step lands in a receipt, and a frozen, receipt-verifiable evaluation. Those transfer to any base model. The base itself is evolved because every bolder route costs either an engine change, a licence problem, or training compute Aefinity does not have.
2. **Rung A does not meet your size gate and the plan says so.** The incumbent shape is 522 MB packed against a 500 MB cap (it passes only if the cap means MiB) and 74% over the 300 MB target; the pruned rung B is the only in-family route to size and nothing in the literature measures pruning a ternary network. The plan treats rung B as a gated bet with a staged spend, not a promise.
3. **Provenance is the weakest point.** The incumbent is MIT, but its own technical report names SFT/DPO sources that are mostly OpenAI-output sets, and its tokenizer is Llama 3's with the naming reach-through unresolved. The plan never claims "no external model output in the chain"; it claims "no new external teacher" and sends the inherited lineage to counsel. If counsel says no, Plan C (the Apache-2.0 Qwen3 student, or the small operator model as a cheap falsifier) is written up and ready.

## Baseline numbers the plan has to beat (measured today, LAB-07)
| Capability | BitNet-2B today | Gate for ALICE-Next |
|---|---|---|
| Correct tool + verbatim argument, pre-registered suite | 45/58 overall; 100% easy arithmetic and table hits; 73%/62% call rate on hard/overflow arithmetic; 0/3 two-tool | ≥ 95% per bucket, lower bound ≥ 85%, n = 100 |
| Looks up an unknown fact instead of guessing | 0/30 with no LOOKUP shown; 22/30 with LOOKUP demonstrated (4 more were the right key with an extra argument the grammar rejects) | ≥ 90% with zero demonstration |
| Stays quiet on distractors | 29/30 and 30/30 | ≥ 95% |
| Receipts verify | 180/180 | 100% |

## Decisions only you can make (also listed as NEEDS candidates in `05` §6)
1. **Pin the size cap unit** (MB vs MiB) and the VOCAB.BIN cap (1.76 MB today against a 1 MB cap; a compact merge table reaches about 1.1 MB).
2. **"No external teacher" or not.** The baseline plan uses none. Allowing an Apache-2.0 teacher (Qwen3) opens Path 2 and changes the provenance story; your call.
3. **Counsel question:** does the incumbent's inherited SFT/DPO lineage or the Llama 3 tokenizer reach-through limit shipping a derived model under Aefinity's name? This is re-open trigger T1.
4. **Adopt or decline the completeness check's proposals** (`05` §7.3): a frozen conversational bucket (GC1), gates for the keep-the-correct-draft and loop-conformance cases of the fact-check loop (GC2), and whether the step prefixes count as demonstration (GC3).
5. **Compute tier.** Tier 0 (Kaggle, free) runs the first notebook and the data factory. Tier 1 (about $500) funds rung A and a first rung-B heal. Tier 2 (about $5,000) funds a 100B-token rung-B pilot. The plan asks for money only at the kill-gate boundaries.
6. **PUBLISH?** Nothing in `model/` is announced or released. Per the 2026-08-28 policy, the recipe, the factory and any weights stay private until you answer per item; the repository move to private that you planned covers the interim.

## What happens first (from `05` §2–3)
The first Kaggle notebook, `e1-evolve-pilot`, trains three cheap arms on 10–20M tokens of gateway-verified episodes and is judged on gates only: `unknown_fact` with zero demonstration at or above today's demonstrated 73.3%, perplexity ratio ≤ 1.05, step-0 parity ≤ 3%. Before it runs: the frozen suite's SHA-256 is recorded, the engine-port tokenizer parity is proven, and the Python gateway oracle is differential-tested against the Rust binary.
