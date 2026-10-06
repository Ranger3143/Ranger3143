> Research brief produced on 2026-10-06 by a web-research agent for the ALICE-Next model plan. Every claim carries the URL the agent read; items it could not verify are listed under Gaps. Numbers here are the cited papers' numbers, not Aefinity measurements.

# ANGLE 4 — Teaching ALICE-Next to know what it does not know, and to look it up

Research brief for Aefinity AI Inc., 2026-10-06. Primary sources fetched; numbers quoted as published. Items I could not verify are marked [uncertain].

## 0. Bottom line for the design panel

1. **Abstention is a trained behaviour with a model-specific label set, not a distilled one.** Every method that works (R-Tuning, HALT, KARL, TruthRL) builds its "known/unknown" split by probing *the model being trained*. ALICE-Next's abstention data must be generated against ALICE-Next's own ternary weights after pretraining; teacher outputs cannot supply it. This is good news for sovereignty: the abstention stage is from-scratch by construction.
2. **Standard RL for reasoning destroys abstention unless you design against it.** Reasoning fine-tuning degrades abstention by 24% on average across 20 frontier models (AbstentionBench, Meta, Jun 2025); standard reinforcement finetuning cuts refusal rates by >80%, and mixing 10% unanswerable items restores it (Hallucination Tax, May 2025). Fix: ternary reward (+1 correct / 0 abstain / −1 wrong, TruthRL, ICML 2026) or Brier-augmented reward (RLCR). Both are shown to work at 3–4B.
3. **Search-RL works at 3B with tiny data.** Search-R1 lifts Qwen2.5-3B-Instruct from 0.270 (RAG) to 0.325 average EM over seven QA sets; StepSearch adds +11.2 points absolute at 3B with 19k examples; s3 needs 2.4k examples; SimpleDeepSearcher gets RL-beating results with 871 SFT samples. A connected ALICE-Next does not need internet-scale training — it needs a few thousand verified search trajectories and a retrieval environment.
4. **Sampling-based uncertainty (semantic entropy, SelfCheckGPT, SimpleQA's 100-sample frequency) is incompatible with ALICE's greedy, deterministic decode and 2 GB budget.** Use single-pass signals: a trained verbalized-confidence token (RLCR), a P(IK)/semantic-entropy probe on int8 hidden states (SEP: "almost zero" overhead), or an explicit [IDK] token. All three are exact-integer-computable and can be carried in the receipt.
5. **Nobody ships a small model that decides to go online by itself.** Apple, Google and Microsoft all route by *task type and availability*, not by model confidence, and none publish a confidence-based policy. A 2 GB machine whose own model emits a receipted "I need to look this up" decision, then verifies the retrieved evidence, is open ground.

## 1. Calibration and abstention training

| Method (venue) | Mechanism | Smallest size shown | Headline result | Fit for CIS-1 ternary engine |
|---|---|---|---|---|
| [R-Tuning](https://arxiv.org/abs/2311.09677) (NAACL 2024) | Split train Qs by whether the pretrained model already answers correctly; append "I am sure"/"I am unsure"; SFT | OpenLLaMA-3B | Multi-task AP 58.24% → 61.09% at 3B; larger gains at 7B/13B | Yes — pure SFT, model-specific labels |
| [HALT](https://arxiv.org/abs/2506.04051) (Meta, ICLR 2026) | Split responses into factual fragments; delete wrong ones or insert "Unsure from Here" at a tunable threshold | four open models (sizes not in abstract) | Llama3-70B correctness 51% → 87% keeping 53% of completeness | Yes — SFT data; needs a fragment-level grader |
| [[IDK] token](https://arxiv.org/abs/2412.06676) (NeurIPS 2024) | Add a vocabulary token; objective shifts mass to [IDK] on wrong predictions | multiple architectures | Expresses uncertainty "with only a small loss of encoded knowledge" | Yes — one extra row in the (pruned) vocab |
| [RLCR](https://arxiv.org/abs/2507.16806) (MIT, Jul 2025) | GRPO reward = correctness + Brier score on a verbalized numeric confidence | not in abstract | "substantially improves calibration with no loss in accuracy", in- and out-of-domain | Yes — confidence is an output token, receiptable |
| [TruthRL](https://arxiv.org/abs/2509.25760) (Meta, ICML 2026) | GRPO with ternary reward r = +1 correct / 0 uncertain / −1 incorrect; with and without retrieval | Llama3.2-3B-Inst, Qwen2.5-3B-Inst | Llama3.1-8B w/ retrieval: hallucination 43.5% → 19.4%, truthfulness 5.3% → 37.2% vs prompting. At 3B: Llama3.2-3B truthfulness 1.9% → 27.4%, hallucination 45.1% → 21.5%; Qwen2.5-3B −0.3% → 21.9%, 45.4% → 16.2%. "relative gain is more pronounced for smaller models" | Yes — the single most relevant recipe for both variants |
| [KARL](https://arxiv.org/abs/2604.22779) (Apr 2026) | Online knowledge-boundary estimate from within-group response statistics; two-stage RL to avoid the "abstention trap" | not in abstract | Converts wrong answers beyond the boundary into abstentions "without sacrificing accuracy" | Yes — GRPO-compatible |
| [Behaviorally Calibrated RL](https://arxiv.org/abs/2512.19920) (Dec 2025) | Strictly proper scoring rule; model outputs calibrated P(correct) or flags claims | Qwen3-4B-Instruct | Log accuracy-to-hallucination ratio gain 0.806 (GPT-5: 0.207 as reported); zero-shot calibration error on par with Grok-4/Gemini-2.5-Pro on SimpleQA | Yes |
| [Abstain-R1](https://arxiv.org/abs/2604.17073) (ACL 2026 Findings) | RLVR with clarification-aware reward: refuse *and* say what is missing | 3B | Competitive with DeepSeek-R1 on Abstain-Test, AbstainQA, SelfAware | Yes — gives the "cite your knowledge level" behaviour |
| [When Silence Is Golden](https://arxiv.org/abs/2602.04755) (ICLR 2026) | Abstention training in temporal QA | Qwen2.5-1.5B-Instruct | Beats GPT-4o EM by 3.46 (TimeQA-Easy)/5.80 (Hard); +20% TP on unanswerable vs SFT | Yes — 1.5B evidence |
| [Rewarding efficient reasoning](https://arxiv.org/abs/2609.20846) (Aug 2026) | GRPO reward discouraging long CoT on unanswerable prompts | 4B | Abstention +12.8%, CoT length −44% | Yes — shorter CoT also matters on CPU |
| [Hallucination Tax of RFT](https://arxiv.org/abs/2505.13988) (May 2025) | Diagnostic: RFT cuts refusal >80%; add 10% SUM (unanswerable math) | — | 10% unanswerable mix "substantially restores" refusal | Design rule for every RL stage |
| [Don't Hallucinate, Abstain](https://arxiv.org/abs/2402.00367) (ACL 2024) | Multi-LLM cooperative/competitive probing to find knowledge gaps; defines AbstainQA evals | 3 LLMs | Up to +19.3% abstain accuracy | Eval and data-labelling aid, not an on-device method |

**Why evals matter as much as training.** Kalai et al. ([Why Language Models Hallucinate](https://arxiv.org/abs/2509.04664), OpenAI, Sep 2025) argue hallucination persists because benchmarks "reward guessing over acknowledging uncertainty" and propose explicit confidence targets in the prompt: "Answer only if you are >t confident, since mistakes are penalized t/(1−t) points, while correct answers receive 1 point, and an answer of 'I don't know' receives 0 points." The accompanying OpenAI blog reported gpt-5-thinking-mini abstaining on 52% of SimpleQA with a 26% error rate versus o4-mini abstaining 1% with a 75% error rate [uncertain: blog returned HTTP 403 to fetch; numbers recalled, not verified]. **Recommendation:** ALICE's eval harness should score every factual item as correct / incorrect / not-attempted (SimpleQA's grading) and report the threshold-penalised score at t = 0.5, 0.75, 0.9 — those receipts then prove calibration to a third party.

**Uncertainty signals that fit a deterministic int8 engine.** Kadavath et al. ([2207.05221](https://arxiv.org/abs/2207.05221)) define P(True) and P(IK) and show larger models self-evaluate well; Tian et al. ([2305.14975](https://arxiv.org/abs/2305.14975), EMNLP 2023) find verbalized confidences on RLHF models cut ECE by ~50% relative to token probabilities; Lin et al. ([2205.14334](https://arxiv.org/abs/2205.14334)) first trained calibrated verbalized confidence. Semantic entropy ([Farquhar et al., Nature 630:625, 19 Jun 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11186750/)) reaches AUROC 0.790 vs 0.691 for naive entropy, stable 0.78–0.81 from 7B to 70B — but needs 5–10 sampled generations; Semantic Entropy Probes ([2406.15927](https://arxiv.org/abs/2406.15927)) regress SE from hidden states of a single generation at "almost zero" overhead. Caution for small models: a 2026 study of eleven 0.5B–14B models ([2608.05064](https://arxiv.org/abs/2608.05064)) finds Platt scaling gets ECE to ~0.02 but only 3 of 22 model-task pairs reach certified autonomy at a 20% risk budget and none at 10% — verbalized confidence alone will not carry a safety case; combine it with a probe and with retrieval.

**Ternary-specific warning.** A 2026 conversion study ([2608.28809](https://arxiv.org/abs/2608.28809), 752M Qwen3.5 → ternary with 72.4M QAT tokens) found factual recall degrades most (linear probe for MMLU answers 26.19% vs 43.76% in the fp teacher). Small scale and short QAT, so treat as a hint, not a law; but BitNet b1.58-2B-4T already scores TriviaQA 33.57 vs 45.97 for SmolLM2-1.7B and 38.37 for Qwen2.5-1.5B ([model card](https://huggingface.co/microsoft/bitnet-b1.58-2B-4T), MIT). Parametric recall is the weak leg of ternary; abstention and lookup are therefore load-bearing, not optional.

## 2. Self-fact-checking and verification loops

| Method | What it does | Result | Use in ALICE-Next |
|---|---|---|---|
| [Self-RAG](https://arxiv.org/abs/2310.11511) (7B/13B, MIT) | Reflection tokens [Retrieve], [IsRel], [IsSup], [IsUse] trained on 150k instruction pairs; critic labels came from GPT-4, distilled into a Llama-2-7B critic | Beats ChatGPT and RAG Llama2-chat on open QA, reasoning, fact verification; better citation accuracy | The token design is the template for a receipted decide-to-search and evidence-support flag. Provenance: the public 150k set is GPT-4-derived; regenerate labels with an open critic |
| [Chain-of-Verification](https://arxiv.org/abs/2309.11495) (Meta, 2023) | Draft → plan verification questions → answer them independently → revise | Cuts hallucination on Wikidata lists, MultiSpanQA, longform | A 2–4 step loop the gateway can run as separate receipted turns |
| [SelfCheckGPT](https://arxiv.org/abs/2303.08896) (EMNLP 2023) | Consistency across stochastic samples | High AUC-PR sentence-level | Not usable under greedy decode unless engine adds seeded integer sampling |
| [FActScore](https://arxiv.org/abs/2305.14251) (EMNLP 2023) | Atomic facts vs knowledge source; ChatGPT bios only 58% factual; estimator <2% error | Eval metric | Offline grader for long-form answers |
| [SAFE / LongFact](https://arxiv.org/abs/2403.18802) (NeurIPS 2024) | LLM agent + Google Search checks each atomic fact; 72% agreement with humans, wins 76% of disagreements, >20× cheaper | Eval metric | Grader for the connected variant; the on-device analogue is the LOOKUP-then-ISSUP loop |
| [FLARE](https://arxiv.org/abs/2305.06983) / [Adaptive-RAG](https://arxiv.org/abs/2403.14403) / [Adapt-LLM `<RET>`](https://arxiv.org/abs/2404.19705) | Retrieve when upcoming tokens are low-confidence; classify query complexity; emit a `<RET>` token learned on PopQA | Adapt-LLM beats always-retrieve, never-retrieve and popularity threshold on PopQA | `<RET>`-style token = the decide-to-search bit in the receipt |
| [R1-Searcher++](https://arxiv.org/abs/2505.17005) | RL to balance internal vs external knowledge plus a "memorization mechanism" to assimilate retrieved facts | — | Pattern for reducing redundant lookups over time |

## 3. RL for search-augmented reasoning in small models

| System (date) | Policy size(s) | Training data / env | Compute note | Result | License |
|---|---|---|---|---|---|
| [Search-R1](https://arxiv.org/abs/2503.09516) (Mar 2025) | Qwen2.5-3B, 7B | NQ+HotpotQA train, 169.6k rows ([HF](https://huggingface.co/datasets/PeterJinGo/nq_hotpotqa_train)); E5 + Wikipedia-2018 local retriever; retrieved-token masking | 7B run = 3,780 GPU-min on A100s (per s3) | 3B-Instruct avg EM 0.325 vs RAG 0.270 vs direct 0.134 (+20%); 7B +41% | Apache-2.0 |
| [R1-Searcher](https://arxiv.org/abs/2503.05592) (Mar 2025) | Qwen2.5-7B-Base, Llama-3.1-8B-Instruct | HotpotQA+2Wiki subsets, two-stage outcome RL, no distillation | — | Beats GPT-4o-mini RAG baselines; Bamboogle with live Google | MIT |
| [ReSearch](https://arxiv.org/abs/2503.19470) (NeurIPS 2025) | Qwen2.5-7B, 32B | one dataset, no supervised reasoning steps | — | Generalises across benchmarks; reflection/self-correction emerge | — |
| [ZeroSearch](https://arxiv.org/abs/2505.04588) (May 2025) | Qwen2.5-3B/7B, Llama-3.2-3B | Simulated search by an SFT'd 3B/7B/14B LLM with curriculum noise | 64k queries: Google API $586.7 vs SFT-7B $35.4 (2×A100, ~12 h) | 7B simulator matches real search, 14B exceeds; 3B-base w/ 3B simulator 37.00 vs Search-R1-base 40.60 | — |
| [StepSearch](https://arxiv.org/abs/2505.15107) (May 2025) | 3B, 7B | 19k examples with sub-question search trajectories; step-wise PPO (information gain, redundancy penalty) | — | +11.2 (3B) / +4.2 (7B) absolute over search-RL baselines on multi-hop QA | — |
| [s3](https://arxiv.org/abs/2505.14146) (May 2025) | searcher Qwen2.5-7B-Instruct; frozen generators 7B/14B/Claude-3-Haiku | 2.4k examples; "Gain Beyond RAG" reward | 114 min on 5×A100 vs 3,780 min for Search-R1 | Outperforms baselines trained on >70× more data on 11 QA sets | — |
| [SimpleDeepSearcher](https://arxiv.org/abs/2505.16834) (Oct 2025) | not in abstract | 871 curated SFT samples synthesised from live web | SFT only | Beats RL baselines on five benchmarks | — |
| [DeepResearcher](https://arxiv.org/abs/2504.03160) (Apr 2025) | Qwen2.5-7B-Instruct | 80k examples (NQ:TQ:HotpotQA:2Wiki = 1:1:3:3); real web search + browsing agent via 50-node CPU tool cluster | — | +28.9 over prompting, +7.2 over RAG-RL; "recognizing when it has not found the correct answer and appropriately declines" emerges | — |
| [WebSailor](https://arxiv.org/abs/2507.02592) (Jul 2025) | **3B**, 7B, 32B released ([HF](https://hf.co/Alibaba-NLP/WebSailor-3B)) | Obfuscated high-uncertainty tasks, RFT cold start, DUPO RL | — | Closes gap to proprietary agents on BrowseComp | Apache-2.0 |
| [Jan-nano](https://arxiv.org/abs/2506.22760) (Jun 2025) | 4B (Qwen3-4B) | Multi-stage RLVR, no SFT; MCP tools | consumer hardware inference | 83.2% SimpleQA with MCP (card chart shows 80.7 — [uncertain which is current]) | Apache-2.0 |
| [II-Search-4B](https://huggingface.co/Intelligent-Internet/II-Search-4B) (2025) | 4B (Qwen3-4B-Base) | Phase 1 "tool-use distillation from larger models", then synthetic multi-hop, rejection sampling, RL on MuSiQue | — | SimpleQA 91.8, FRAMES 67.5, Seal-0 22.5 | Apache-2.0 (teacher unnamed → provenance gap) |
| [Tongyi DeepResearch](https://hf.co/Alibaba-NLP/Tongyi-DeepResearch-30B-A3B) (17 Sep 2025) | 30B total / 3.3B active MoE | Fully synthetic agentic data, on-policy GRPO | too large for 2 GB | SOTA open on BrowseComp/HLE | Apache-2.0 |

Reading across the table: the 3B regime is proven (Search-R1, ZeroSearch, StepSearch, WebSailor-3B), the data requirement collapsed from 170k to 2.4k–19k examples within 2025, and real-web RL produced honest abstention as an emergent behaviour. The connected ALICE-Next should train in a *local* retrieval environment first (Wikipedia + E5, like Search-R1) because it is deterministic and receiptable, then do a short real-web stage through the gateway.

## 4. Evaluation sets to adopt

| Set | Size | Measures | License | Role |
|---|---|---|---|---|
| [SimpleQA](https://arxiv.org/abs/2411.04368) | 4,326 Qs | correct / incorrect / not attempted; F-score = harmonic mean of overall-correct and correct-given-attempted; calibration via stated confidence and 100-sample frequency | MIT (simple-evals) | Primary air-gapped abstention metric |
| [SimpleQA Verified](https://arxiv.org/abs/2509.07968) (DeepMind, Sep 2025) | 1,000 | de-duplicated, topic-balanced; Gemini 2.5 Pro F1 55.6 | — | Cleaner twin |
| [TruthfulQA](https://arxiv.org/abs/2109.07958) | 817 Qs, 38 categories | imitative falsehoods; best model 58% vs humans 94% | Apache-2.0 [uncertain: not fetched] | Falsehood resistance |
| [HaluEval](https://github.com/RUCAIBox/HaluEval) | 35k (10k QA/10k dialogue/10k summarisation/5k general) | hallucination recognition | MIT | Verification-step training/eval |
| [FreshQA](https://github.com/freshllms/freshqa) | 600 (500 test = 125 × {never, slow, fast-changing, false-premise}; 100 dev); updated weekly | time-sensitivity, false premises | Apache-2.0 | Connected variant: decide-to-search and staleness |
| [PopQA](https://huggingface.co/datasets/akariasai/PopQA) | 14k entity Qs with Wikipedia page views | long-tail knowledge; adaptive retrieval | not shown on card [uncertain] | Train/eval the `<RET>` decision by popularity |
| [SelfAware](https://arxiv.org/abs/2305.18153) | 1,032 unanswerable + 2,337 answerable; 5 categories | known-unknowns; GPT-4 F1 75.47% vs human 84.93% | — | Core unanswerable set |
| [KUQ](https://arxiv.org/abs/2305.13712) | size not in abstract [uncertain] | known-unknown categories | — | Secondary |
| [AbstentionBench](https://arxiv.org/abs/2506.09038) (Meta) | 20 datasets, 6 scenarios (Answer Unknown, False Premise, Stale, Subjective, Underspecified Context, Underspecified Intent); >35k unanswerable prompts [uncertain] | abstention with LLM judge | repo has LICENSE file; type unverified | Umbrella suite |
| [CoCoNot](https://arxiv.org/abs/2407.12043) (NeurIPS 2024) | 1,000 noncompliance prompts | incomplete/unsupported/indeterminate/humanizing; GPT-4 wrongly complies up to 30% | — | Over-refusal control |
| [BrowseComp](https://arxiv.org/abs/2504.12516) | 1,266 Qs | persistent web browsing | MIT (simple-evals) | Connected stretch goal |
| [FRAMES](https://huggingface.co/datasets/google/frames-benchmark) | 824 multi-hop Qs (2–15 articles) | factuality + retrieval + reasoning; SOTA 0.40 → 0.66 with multi-step retrieval | Apache-2.0 | Connected multi-hop |
| [ALCE](https://arxiv.org/abs/2305.14627) / [FACTS Grounding](https://arxiv.org/abs/2501.03200) | ASQA/QAMPARI/ELI5; docs up to 32k tokens | citation recall/precision (best models lack support 50% on ELI5); grounding to provided context | — | "Cite sources, verify against evidence" |

## 5. How shipping on-device assistants decide to go online

| System | What is published | Routing basis | Confidence-based? |
|---|---|---|---|
| Apple Intelligence | "When a user makes a request, Apple Intelligence analyzes whether it can be processed on device. For more complex requests, it can draw on Private Cloud Compute" ([Apple support guide](https://support.apple.com/guide/mac-help/mchlfc0d4779)). On-device model ≈3B, 2-bit QAT, KV-cache sharing −37.5%, 65k training context; Foundation Models framework exposes tool calling and guided generation on-device only ([Apple ML, Jun 2025](https://machinelearning.apple.com/research/apple-foundation-models-2025-updates); [tech report](https://arxiv.org/abs/2507.13575)). PCC: stateless, enforceable, no privileged access, non-targetable, verifiable transparency with images published within 90 days ([PCC blog, 10 Jun 2024](https://security.apple.com/blog/private-cloud-compute/)) | Orchestration layer, task/complexity based; policy not published | No evidence of model-confidence routing |
| Google Gemini Nano | Firebase AI Logic hybrid inference modes: PREFER_ON_DEVICE, ONLY_ON_DEVICE, PREFER_IN_CLOUD, ONLY_IN_CLOUD; falls back to cloud when the on-device model is unavailable/downloading, for unsupported inputs, and for unsupported capabilities including **function calling and multi-turn chat**; Chrome ≥139 ([docs](https://firebase.google.com/docs/ai-logic/hybrid-on-device-inference)); Android hybrid API experimental, single-turn, announced 17 Apr 2026 ([blog](https://android-developers.googleblog.com/2026/04/Hybrid-inference-and-new-AI-models-are-coming-to-Android.html)) | Availability and capability | No |
| Microsoft Copilot+ PC | Phi Silica: Phi-3.5-mini derivative, 4-bit weights, 230 ms TTFT, up to 20 tok/s, 2k context at launch ([Dec 2024](https://blogs.windows.com/windowsexperience/2024/12/06/phi-silica-small-but-mighty-on-device-slm/)); Learn guidance (updated 2026-09-21): try local first, fall back when "the model isn't installed, the device isn't supported, the user doesn't consent to a model download, or the task requires a larger model"; "Decide whether fallback is automatic, user-controlled, or disabled for privacy-sensitive scenarios" ([Learn](https://learn.microsoft.com/en-us/windows/ai/cloud-ai)). Note: Phi Silica is being replaced by "Aion Instruct", removal Jan 2027 ([Learn, 2026-10-02](https://learn.microsoft.com/en-us/windows/ai/apis/phi-silica)) | Developer-defined readiness checks | No |

Research on confidence-based routing exists but is not shipped: Hybrid LLM ([ICLR 2024](https://arxiv.org/abs/2404.14618)) cuts large-model calls 40% with no quality drop; RouteLLM ([2406.18665](https://arxiv.org/abs/2406.18665)) halves cost; "Confident or Seek Stronger" ([2502.04428](https://arxiv.org/abs/2502.04428)) benchmarks 1,500+ settings and finds uncertainty distributions depend on the SLM and UQ method more than on the data; UCCI ([2605.18796](https://arxiv.org/abs/2605.18796)) maps token-margin uncertainty to error probability by isotonic regression (ECE 0.12 → 0.03, 31% cost cut on 4B/12B). The gap ALICE-Next can fill: the *model itself* emits the decision, the decision is in the TPM-signed receipt, and the "cloud" is a receipt-gated LOOKUP rather than a bigger model.

## 6. Design requirements

### 6.1 Both variants (CIS-1 constraints)
- **Confidence channel**: a verbalized confidence token (0–100 in 10 bins) trained with Brier/ternary reward, plus a linear P(IK)/SEP probe on the final-layer int8 hidden state (few-KB weights, exact i32 dot product). Both values go into the receipt; a verifier replays them.
- **Explicit tokens** in the pruned 50,256-token vocab: `[IDK]`, `[RET]` (decide to look up), `[ISSUP yes/partial/no]` (evidence supports claim), `[CITE n]`. Greedy decode is fine: the decision is argmax over these tokens.
- **No sampling-based UQ** unless a seeded integer PRNG is added to the engine (CIS-compatible; cost 5–10× decode, so off by default).
- **Every RL stage includes ≥10% unanswerable items** and uses ternary or Brier reward; never binary correctness alone.
- **Eval**: SimpleQA-style three-way grading with threshold scoring, SelfAware, AbstentionBench subsets, CoCoNot for over-refusal; publish per-threshold curves with receipts.

### 6.2 Air-gapped variant — "abstain and state your knowledge level"
Behaviour: answer with confidence; or abstain with a reason category (SelfAware's five: no consensus, imagination, subjective, too many variables, philosophical; plus "beyond my training data" and "stale"); or ask a clarifying question (Abstain-R1 / ACA-RL style). Training data, in order: (1) **Model-specific known/unknown split** — run ALICE-Next on TriviaQA/NQ/PopQA/MMLU train splits, label by correctness (R-Tuning), fragment-level for long-form (HALT); (2) **unanswerable sets** — SelfAware, KUQ, SUM-style synthetic unanswerable math, FalseQA/false-premise, temporal (TimeQA); (3) **RL stage** — TruthRL ternary reward on the same pools; (4) **over-refusal control** — CoCoNot-style compliant items. Expect, from TruthRL's 3B numbers, hallucination roughly halved and truthfulness moving from ~0 to >20 points.

### 6.3 Connected variant — "decide to search, cite, verify"
Behaviour: emit `[RET]` with a query when P(IK) is low or the question is fast-changing; receive LOOKUP results through the gateway (hash-chained); generate with `[CITE n]`; run a CoVe-style verification turn emitting `[ISSUP]` per claim; abstain if evidence is absent or contradictory. Training data: (1) **decide-to-search labels** — PopQA by popularity and the model's own correctness (Adapt-LLM), FreshQA categories for staleness; (2) **search trajectories** — StepSearch-scale (≈19k) multi-hop sets (HotpotQA, 2Wiki, MuSiQue) in a local Wikipedia+E5 environment, or 2.4k with an s3-style Gain-Beyond-RAG reward; ZeroSearch-style simulated retrieval if API cost bites; (3) **citation/support supervision** — ALCE-format answers with citations, ISSUP labels generated by an open critic (not GPT-4); (4) **short real-web RL stage** via the gateway (DeepResearcher pattern), with honesty reward for "not found". Evals: FreshQA, FRAMES, PopQA tail, ALCE citation metrics, BrowseComp as stretch.

### 6.4 Compute sketch [uncertain]
Search-R1 7B cost 3,780 A100-minutes; s3 reached peak in 114 min on 5×A100 for a 7B searcher; ZeroSearch quotes 2×A100 for 12 h to serve 64k simulated queries. For a 2–3B policy with GRPO on 19k trajectories, a rented 4–8×A100/H100 node for 1–3 days is the realistic envelope; T4 Kaggle quotas can cover the SFT stages (R-Tuning/HALT/SimpleDeepSearcher-scale 871–20k samples) but not multi-turn RL rollouts.

## 7. Distillation re-opened: provenance and licensing consequences

| Teacher / data | Terms | Consequence |
|---|---|---|
| Qwen3-4B / 4B-Base | [Apache-2.0](https://huggingface.co/Qwen/Qwen3-4B) | Clean for outputs and derivatives; keep attribution |
| DeepSeek-R1 | [MIT](https://huggingface.co/deepseek-ai/DeepSeek-R1) | Clean |
| Llama 3.1 | [Community License, 23 Jul 2024](https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_1/LICENSE): if you use Llama Materials "to create, train, fine tune, or otherwise improve an AI model" you must "include 'Llama' at the beginning of any such AI model name" and display "Built with Llama"; 700M MAU clause | A Llama-distilled ALICE-Next would have to be named "Llama-…" — incompatible with a sovereignty narrative |
| Gemma 3n | [Gemma Terms, modified 1 Apr 2026](https://ai.google.dev/gemma/terms): Model Derivatives include any model "created by transfer of patterns of the weights, parameters, operations, or Output of Gemma" (distillation, synthetic data); Google claims no rights in outputs but use restrictions and notice must pass through | Distilling from Gemma makes ALICE-Next a Gemma derivative bound by the Prohibited Use Policy |
| OpenAI/Anthropic/Google API outputs | OpenAI terms prohibit using Output "to develop models that compete with OpenAI" [uncertain: page returned 403; clause recalled] | Rules out GPT-made abstention/critic labels (e.g., reusing Self-RAG's GPT-4-derived 150k set as-is) |
| Self-RAG data | MIT, but critic labels GPT-4-generated | Regenerate reflection labels with an open critic |
| NQ / HotpotQA | CC BY-SA 3.0 ([HF card](https://huggingface.co/datasets/google-research-datasets/natural_questions)) / CC BY-SA 4.0 ([site](https://hotpotqa.github.io/)) | Share-alike attaches to the datasets and derived data releases; whether it reaches weights is unsettled — flag for counsel |
| xLAM-function-calling-60k / Glaive v2 | [CC-BY-4.0](https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k) / [Apache-2.0](https://huggingface.co/datasets/glaiveai/glaive-function-calling-v2) | Usable for the tool-expert stage with attribution |

The sovereignty-preserving path: **no teacher for the abstention stage (impossible anyway), Apache/MIT teachers only if any for conversation/tool data, open critics for verification labels, and a provenance manifest hashed into the model's release receipt.**

## 8. Risks and open questions
- Abstention trap / over-conservatism (KARL, TruthRL both warn); needs the CoCoNot-style compliance set and an explicit over-refusal metric.
- Judge dependence: AbstentionBench, SAFE and FActScore rely on LLM judges; the lab needs a local open judge and human spot checks to keep Rule B provenance.
- Whether 2 GB ternary models retain enough recall for the air-gapped variant to be useful beyond tool and document tasks is the central empirical question; the probe evidence (2608.28809) says recall is the first casualty.
- Receipt semantics for confidence: a signed "72% confident" is a new kind of attestable claim; define what a verifier replays (probe output, token logits, or both) before training the behaviour.

## Key claims (as returned by the research agent, with sources)
- AbstentionBench (Meta, submitted 10 Jun 2025) evaluates 20 LLMs on 20 datasets and finds reasoning fine-tuning degrades abstention by 24% on average.  
  <https://arxiv.org/abs/2506.09038>
- TruthRL (ICML 2026) uses a ternary GRPO reward (+1 correct / 0 uncertain / -1 incorrect); on Llama3.1-8B-Instruct with retrieval hallucination falls 43.5% -> 19.4% and truthfulness rises 5.3% -> 37.2% vs prompting; at 3B, Llama3.2-3B truthfulness 1.9% -> 27.4% and hallucination 45.1% -> 21.5%.  
  <https://arxiv.org/abs/2509.25760>
- Search-R1 (Mar 2025, Apache-2.0) improves Qwen2.5-3B-Instruct average exact match across seven QA datasets from 0.270 (RAG) to 0.325, with Direct inference at 0.134; training set is NQ+HotpotQA, 169.6k rows.  
  <https://arxiv.org/abs/2503.09516>
- s3 trains a 7B searcher with only 2.4k examples in 114 minutes on 5 A100s versus 3,780 minutes for Search-R1, outperforming baselines trained on >70x more data.  
  <https://arxiv.org/abs/2505.14146>
- Standard reinforcement finetuning reduces refusal rates by more than 80%; adding 10% synthetic unanswerable math (SUM) substantially restores refusal with minimal accuracy trade-off.  
  <https://arxiv.org/abs/2505.13988>
- Semantic entropy (Nature 630:625-630, 19 Jun 2024) achieves mean AUROC 0.790 for confabulation detection vs 0.691 for naive entropy, stable 0.78-0.81 from 7B to 70B, but requires multiple sampled generations; Semantic Entropy Probes approximate it from one generation's hidden states at near-zero overhead.  
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC11186750/>
- SimpleQA contains 4,326 questions graded correct / incorrect / not attempted, with F-score the harmonic mean of overall-correct and correct-given-attempted; best Nov-2024 result o1-preview 42.7% correct.  
  <https://arxiv.org/html/2411.04368>
- Firebase AI Logic hybrid inference falls back from Gemini Nano to cloud when the on-device model is unavailable or for unsupported capabilities, explicitly including function calling and multi-turn chat; requires Chrome v139+.  
  <https://firebase.google.com/docs/ai-logic/hybrid-on-device-inference>
- Apple states: 'When a user makes a request, Apple Intelligence analyzes whether it can be processed on device. For more complex requests, it can draw on Private Cloud Compute'; the on-device model is ~3B parameters compressed to 2 bits per weight with QAT.  
  <https://support.apple.com/guide/mac-help/mchlfc0d4779>
- Llama 3.1 Community License (23 Jul 2024) requires any AI model created, trained, fine-tuned or improved using Llama Materials to include 'Llama' at the beginning of its name and to display 'Built with Llama'.  
  <https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_1/LICENSE>

## Gaps and unverified items (recorded, not papered over)
- OpenAI blog 'Why language models hallucinate' (gpt-5-thinking-mini vs o4-mini SimpleQA abstention/error table) returned HTTP 403; the arXiv text does not contain the table. Numbers 52%/26% vs 1%/75% are recalled, not verified.
- OpenAI Terms of Use clause on using Output to develop competing models could not be fetched (403 / JS shell); cited from memory and marked uncertain.
- PopQA dataset license not shown on the Hugging Face card; TruthfulQA (Apache-2.0) and AbstentionBench repo licenses not verified because GitHub API access was not enabled for this session.
- KUQ (Known-Unknown Questions) dataset size not stated in the abstract; AbstentionBench's '>35,000 unanswerable prompts' came from a partial HTML read and is marked uncertain.
- Jan-nano SimpleQA score: arXiv report says 83.2% with MCP, model-card chart reportedly 80.7; could not determine which is current.
- II-Search-4B's phase-1 teacher ('larger models') is not named on the model card, so its provenance is unknown.
- RLCR (2507.16806), KARL (2604.22779), IDK-token (2412.06676) and HALT (2506.04051) abstracts do not state model sizes; full-text tables were not read.
- No paper found that measures calibration or abstention specifically on ternary/BitNet models; the only ternary evidence (2608.28809) is a 752M conversion with 72.4M QAT tokens.
- Compute estimates for training a 2-3B search-RL policy are extrapolated from 7B reports (Search-R1, s3, ZeroSearch) and marked uncertain.
- Whether CC BY-SA share-alike on NQ/HotpotQA reaches trained weights is a legal question not resolved here.
