# R0 — Synthesis and critique of the ALICE-Next research briefs (R1-R9)

Date 2026-10-06. Inputs read in full: `00-ALICE-NEXT-brief.md` ("the brief"), R1-R9, and `R0-VERIFICATION-corrections.md` ("R0-V").
Status: cross-brief synthesis and critique. It does not choose the recipe; the design panel and Justin do (brief §5; sovereignty and PUBLISH? items are theirs).

**Conventions.**
- Every number carries the brief it comes from, e.g. (R2 §3). `V-R2.1` = R0-V claim 1 for brief R2.
- Tags on findings: **[verified]** = R0-V re-fetched the claim and confirmed it. **[corrected]** = R0-V refuted or tightened it and the corrected statement is used here.
  **[unverified]** = outside R0-V's checked set (all of R5-R9, and the 2-3 claims per brief in R1-R4 that R0-V did not reach); read as "the brief's reading of its source".
- **[est]** = my arithmetic or judgement from the cited briefs' inputs. It is not a measurement and not from any source. Nothing here is an Aefinity measurement except figures cited to the brief.

---------------------------------------------------------------------------------------------------

## 1. What the evidence says (19 findings)

1. **Ternary conversion hurts tool calling most at 1.7B.** Ternary Bonsai-1.7B (PrismML, converted from Qwen3-1.7B): average 58.47 vs 66.57 (88%), BFCLv3 51.0 vs 71.8 (-20.8);
   4B 70.7 vs 77.1, 8B 75.5 vs 79.3 (R2 §2-3, R5 §3, R7 §7). Recipe, tokens and compute are undisclosed (R2, R7 gaps). The same fp model is 52.2 on BFCL v3 in Qwen3's own report (R1 T2, R3 §3), so the -20.8 is harness-specific (critique 3). [verified] (V-R2.6, numbers only)
2. **Task-level ternary conversion is cheap.** BitDistill (Microsoft; SubLN + 10B-token continued pretraining + attention and logit distillation) on Qwen3-0.6B/1.7B/4B: MNLI 88.17/89.53/91.40 vs FP16 88.01/89.61/91.48;
   direct 1.58-bit SFT 74.09/75.27/76.11; 10x memory, 2.65x CPU speed (R2 §2, R5 §3, R7 §7). Evidence is classification and summarisation only; no chat or tool eval (R2 §2). [verified] (V-R2.1)
3. **General ternary QAT saturates near 30B tokens and still loses.** ParetoQ: ~90/10 float/QAT split; ternary and 2-bit saturate ~30B QAT tokens, 3/4-bit ~10B (R2 §2, R7 §7). MobileLLM-1.5B 62.7 -> 60.5, Llama-3 3B 65.2 -> 61.9, 8B 74.6 -> 69.0 (R5 §3; 16-bit activations, optimistic for int8 CIS-1).
   The 600M ternary average is 55.5 vs the prior 3B ternary's 54.5, not the 58.7 in R2 (V-R2.2). Weights are FAIR-NC: method only (R2). [corrected]
4. **From-scratch ternary parity is a scale effect.** BitNet b1.58 "Era" at 100B tokens: 3B PPL 9.91 vs 10.04, avg 50.2 vs 49.7; 1.3B -0.8, 700M -1.2 (R5 §2). Spectra at 300B tokens: 3.9B -0.7, 2.4B -1.9, 1.5B -4.2, 1.1B -3.3 (R5 §2, R2 §2).
   Float twins may be under-tuned or shape-confounded (R5 §2, §7). [unverified]
5. **Ternary wants tokens, not parameters.** Spectra-1.1 fitted exponents: data 0.81 vs parameters 0.32 for TriLM (FloatLM 0.53/0.56); 1.5B/2.5B/3.6B trained to 1.2T tokens (R2 §2, R5 §2). R5 warns the literal fits say ternary never matches float; use the exponent ratio only. [verified] (V-R2.3)
6. **Data quality and a logit teacher buy token efficiency; R1's budgets are its own estimates.** MobileLLM-Pro: ~1,640B-token mix with forward-KL logit distillation from Llama-4-Scout vs Gemma-3-1B (2T) and Llama-3.2-1B (9T) (R1 T1; V-R1.8). Falcon-H1-3B 2.5T with a 52% rewritten end-of-run mix, MMLU 68.3 vs Qwen3-4B 36T, 73.0 (R1 §0.2, T1; these Falcon-H1-3B figures were not re-checked).
   R1 working numbers: >=8-10T at 1B own-data, 3-5T with >=30% rewritten data, 1.5-2T with an Apache-2.0 logit teacher (R1 §3) are R1's unsourced estimates. int4 QAT regression is 0.73/1.3 points absolute, not the 0.4% headline (V-R1.8). [corrected]
7. **On-policy distillation is the cheapest post-training signal, but needs a shared tokenizer.** Qwen3-8B: AIME'24 74.4 for ~1,800 GPU-h vs RL 67.6 for 17,920 GPU-h (R2 §1, R1 §2f). The tokenizer constraint is R2's own inference (R2 §0.2). [verified] (V-R2.4, V-R1.1)
8. **Depth beats width at fixed tokens.** Falcon-H1-1.5B (24 layers) vs 1.5B-Deep (66 layers), both 3T tokens: MMLU 62.03 -> 66.11, GSM8K 74.98 -> 82.34, HumanEval 68.29 -> 73.78, IFEval 80.66 -> 83.5 (R1 §0.3, T2).
   A Mamba+attention hybrid, not a pure transformer and not ternary. [verified] (V-R1.3)
9. **Factual recall is the first casualty of ternarisation.** Qwen3.5-0.8B (752M) -> ternary with 72.4M QAT tokens: MMLU linear-probe recall 26.19% vs 43.76%, 77.1% task retention, letter "A" on 98.6% of MMLU items (R2 §2, R1 §3, R4 §1).
   BitNet-2B-4T TriviaQA 33.57 vs SmolLM2-1.7B 45.97 and Qwen2.5-1.5B 38.37 (R4 §1). Small, short, hybrid base: R4 calls it "a hint, not a law". [unverified] (R0-V did not reach R2 claim 10)
10. **Abstention must be trained against the model's own knowledge boundary, and RL erodes it.** R-Tuning, HALT, KARL, TruthRL split known/unknown with the model's own probes (R4 §0.1). Reasoning fine-tuning cuts abstention 24% on average over 20 models; reinforcement fine-tuning cuts refusals >80%; a 10% unanswerable mix restores them (R4 §0.2).
    TruthRL ternary reward at 3B: Llama3.2-3B truthfulness 1.9 -> 27.4, hallucination 45.1 -> 21.5; Qwen2.5-3B -0.3 -> 21.9, 45.4 -> 16.2 (R4 §1). [verified] (V-R4.1, V-R4.2, V-R4.5)
11. **Search-RL works at 3B on small data; no <=4B recipe exists for search-and-verify.** Search-R1 3B: average EM 0.325 vs RAG 0.270 vs direct 0.134 (R4 §3); s3: 2.4k examples, 114 min on 5 A100 vs 3,780 min (R4 §3). Best <=4B BFCL v4 Web Search is 3.00 and Memory 17.63 (R3 §2). [verified] (V-R4.3, V-R4.4, V-R3.2)
12. **Multi-turn tool competence comes from trajectory data, not size alone.** xLAM-2-3b Multi-Turn 58.38 vs xLAM-2-1b 36.00 on the same data; Hammer2.1-3b (single-turn data) 16.50; Qwen3-4B-Instruct-2507 22.12 (R3 §2, §4).
    Corrections (V-R3.1, V-R3.4): not unique, since Nanbeige4-3B-Thinking-2511 (Apache-2.0, 3.93B) has Multi-Turn 51.12 and overall 51.40; "3,820 trajectories" is a pipeline yield, the released set is 5,000; xLAM-2 weights and APIGen-MT-5k are non-commercial. [corrected]
13. **Verifiable-reward RL beats SFT at 1.5-3B on ~4k prompts.** ToolRL, Qwen2.5-3B-Instruct on BFCL v3: raw 33.04, SFT4k 41.97, GRPO 52.98; 1.5B: 19.41 / 40.67 / 46.20 (R3 §3, §7; V-R3.6: 41.97 is the SFT score, not "base"). Matches ALICE's gateway-verifiable labels (brief §3). [corrected]
14. **Abstention metrics are gameable; pair with call rate.** BFCL v4 irrelevance (240 entries): untrained Qwen3-4B 87.50, LoRA 89.17; a second seed 97.50 while calling tools on only 32.5% of Multiple entries (R3 §7). [unverified] (V-R3 did not reach claim 10)
15. **Evals are contaminated and noisy.** MMLU label errors 6.49% (57% in Virology) (R8 §1); Qwen2.5-Math-7B reconstructs 54.6% of truncated MATH-500 vs 3.8% for Llama-3.1-8B (R8 §1); a tool-benchmark audit found 18.5% evaluator-human misalignment (92 of 496) and an 18.9 pp spread over 23 reruns of one setup (R8 §2). [unverified]
16. **Hybrids are not free at 1B for tool use and math.** Granite 4.0 H-1B (36 Mamba-2 + 4 attention) vs transformer Granite 4.0 1B: BFCL v3 50.21 vs 54.82, GSM8K 69.83 vs 76.35, MMLU 59.74 vs 59.39 (R9 §1.3, R1 T2, R2 §3). [unverified] (V-R3 did not reach claim 9)
17. **Memory fit.** A 1.2-1.7B ternary class is 1.0-1.3 GiB all-in in every configuration; 2.6-3.0B fits 2 GiB only with int8 head and KV, 1.45-1.61 GiB (R5 §5). A bf16 head is read per token at nearly the bytes of the 1.2B ternary body (196 vs 252 MiB), so an int8 head is a speed win (R5 §5).
    R5's 2B4T parameter count looks wrong (critique 2). [unverified]
18. **Shipping on-device assistants route by availability and capability, not model confidence.** Firebase hybrid inference falls back to cloud for an unavailable model or unsupported capabilities, including function calling and multi-turn (R4 §5). The Apple and Microsoft rows were not re-checked (R4 §5). [verified] (V-R4.8)
19. **Compute overheads.** Ternary QAT costs ~20% more wall-clock with no memory saving, from one data point (Falcon-E) (R5 §4, R7 §3). Teacher forward passes add +38%/+89%/+178% for a 1.7B/4B/8B teacher on a 1.5B student (R7 §2). [unverified]

---------------------------------------------------------------------------------------------------

## 2. Three credible paths to a 0.3-1.7B ternary tool-expert model

**Path 1 — Evolve BitNet-b1.58-2B-4T** (R2 Path A, R3 §9, R7 §9.4). 2.4B total, MIT, bf16 master weights published, Llama-3 tokenizer, 4,096 ctx (R2 §4, R5 §2). Already CIS-1-native: engine delta none (brief §1).
Cost: ~0.5B-token tool SFT ~6 H100-h (R2 est.); 10-20B-token continued pretraining ~$300-600 (R7 §9.4).
- Strongest support at <=2B: tool skill is a cheap post-training layer. Hammer2.1-1.5b reaches non-live 82.98 / live 69.50 / irrelevance 79.40 from ~70k samples; ToolRL lifts Qwen2.5-1.5B 19.41 -> 46.20 on 4k prompts (R3 §4, §7; V-R3.6) — both fp, not ternary.
  The base itself is near fp parity: avg 54.19 vs Qwen2.5-1.5B 55.23 at 4T tokens (R5 §2); ALICE's own T1 baseline is 45/58 = 77.6%, 100% on easy buckets (brief §2.1).
- Strongest contrary: the base is weak where the gates bite and cannot reach the size target. IFEval 53.48 vs LFM2-1.2B 74.89 and Qwen3-1.7B 68.2 (R8 §3); TriviaQA 33.57 (R4 §1); `unknown_fact` lookups 0/30 without in-prompt demonstration (brief §2.3).
  At ~480 MB packed (brief §1) it misses the 300 MB target. Its Llama-3 tokenizer forces sequence-level distillation only (R2 Path A). Whether a 2.4B ternary base keeps enough reasoning for multi-turn is open (R3 §9).

**Path 2 — Convert/distil an Apache-2.0 teacher (Qwen3-1.7B, optionally 4B) into a ternary student** (R2 Path B, R5 §8, R7 d/d'). Steps: SubLN insertion, 10-30B-token continued pretraining with logit and attention KD, tool SFT, on-policy KD from Qwen3-8B, vocab prune (R2 §5).
Cost: ~86-258 H100-h of continued pretraining (R7 d, d'x1.5) plus SFT 10-20 and on-policy KD 50-100 H100-h (R2 §5); R2 quotes $0.4k-1.5k. Engine delta is real (critique 7).
- Strongest support at <=2B: BitDistill at 1.7B, MNLI 89.53 vs 89.61 FP16 (R5 §3; V-R2.1); Bonsai-1.7B keeps 88% of the average at 436 MiB (R2 §2; V-R2.6); a 1T-token base loses only ~2 points under ternary QAT (ParetoQ MobileLLM-1.5B, R5 §3).
- Strongest contrary: Bonsai-1.7B BFCLv3 51.0 vs 71.8 = 71% retention (R2 §0.1; V-R2.6), with the harness caveat of finding 1; plus the recall collapse in the 752M conversion (R2 §2) [unverified]. No published ternary <=3B has been evaluated as a tool expert beyond that one data point (R2 gaps).

**Path 3 — Purpose-built operator model (from scratch, ternary; optionally the R9 architecture).** Cost: 1.2B x 1T tokens ~6,100 H100-h (~$15k at $2.5/h) and 2.6B x 1T ~14,700 H100-h (R5 §6); 1.5B x 1.2T ~8,000 H100-h (R2 §5 Path C).
Data: R6 §10's Tier-A mix is a 10B-token pilot, not a 1T plan (R6 §10 caveat). Engine delta none for a BitNet-family shape (R5 §8); several errata for the R9 composite (§6).
- Strongest support at <=2B: Falcon-E-1B (1.8B params, ~1.5T tokens, from scratch) base average 13.40 vs Qwen2.5-1.5B 13.85 (R2 §2, R5 §2); BitNet-2B-4T 54.19 vs 55.23 (R5 §2). Parity at 3.9B/300B (R5 §2) is above the size range.
- Strongest contrary: Spectra TriLM-1.5B at 300B tokens is 52.5 vs 56.7 float with LAMBADA perplexity +74% (R5 §2); ALICE-30M twins are +0.38 nats / 46% PPL (R5 §2, own); Falcon-E-3B instruct 22.65 vs Qwen2.5-3B 27.16 (R5 §2);
  R1 puts open-web-only recipes at >=10T for a competitive 1B (R1 §3, [est] by R1); no matched from-scratch ternary twin above 1B exists since 2024 (R5 §1) [unverified].

**Reading [est].** The evidence supports ordering 1 -> 2 -> 3: Path 1 as the cheap CIS-native baseline, Path 2 as the main candidate for a <=1.7B SKU, Path 3 only as a funded pilot or sovereignty proof (R2 recommendation, R7 §7). Path 2 changes the "no external teacher" claim (R2 §4, R5 §6), which is Justin's decision.

---------------------------------------------------------------------------------------------------

## 3. License landscape (as documented in the briefs; none of this is legal advice)

**Usable**
| Item | Terms / condition | Brief (R0-V status) |
|---|---|---|
| Qwen3 0.6B-32B, Qwen3.5, Ministral 3, OLMo 2/3, SmolLM3, Granite 4.x, Spectra-1 TriLM, Ternary Bonsai | Apache-2.0; attribution/NOTICE only | R2 §4, R1 T1, R3 §2 |
| Gemma 4 (E2B/E4B) | Apache-2.0 (Gemma <=3n terms do not apply) | R1 T1 [verified V-R1.4], R2 §4 |
| BitNet-2B-4T (+ bf16 masters), DeepSeek-R1 (distills inherit base licence), Phi-4-mini | MIT | R2 §4, R4 §7 |
| Kimi-K2 (Toucan teacher) | modified MIT: display name above 100M MAU or $20M monthly revenue | R2 §4, R3 §9 |
| Toucan-1.5M, ToolACE, Glaive-FC-v2, Hermes-FC-v1, ToolBench, OpenThoughts3, OASST2, Aya | Apache-2.0 | R3 §5, R6 §3-§5 |
| FineWeb(-Edu), Dolma 3/OLMo-mix, FineMath, Cosmopedia v2, TxT360, Zyda-2, CoCoNot | ODC-By 1.0; "Produced Work" notice (§4.3) | R6 §1-§2, §8 |
| DCLM-baseline, xlam-60k + irrelevance-7.5k, When2Call, Nemotron-Agentic-v1, Nemotron-Post-Training v1/v2, OpenMathReasoning, HelpSteer2/3, Aegis 2.0, MMLU-Redux 2.0 | CC-BY-4.0 (some Nemotron chat prompts must be re-fetched from a restricted chat corpus) | R3 §5 [verified V-R3.5], R6 §2-§7, R8 §3 |
| CDLA-licensed assets | no brief documents any; status unassessed | none (grep of R1-R9) [unverified] |
| AbstentionBench | CC-BY-NC-4.0: evaluation only, never training | R8 §7, R6 §8 |

**Not usable in a shipping path**
| Item | Why | Brief (R0-V status) |
|---|---|---|
| Llama 3.x/4 weights and any Llama-generated output (Magpie sets, Smol-Magpie-Ultra, OpenMathInstruct-2) | "Llama" must prefix the derived model's name; "Built with Llama"; 700M-MAU clause; AUP flows down | R2 §4 [verified V-R2.8 for 3.2], R4 §7, R6 §1 (Tier B) |
| Gemma 1-3, 3n, FunctionGemma | distillation or synthetic-output training makes a "Model Derivative"; use restrictions pass through | R2 §4 [verified V-R2.7], R4 §7 |
| FAIR Noncommercial Research: MobileLLM-R1, MobileLLM-Pro, ParetoQ weights | no commercial use (ParetoQ code is BSD-3, method usable) | R1 T1, R2 §2 [licence confirmed V-R1.8, V-R2.2] |
| CC-BY-NC: APIGen-MT-5k, xLAM-2, Hammer2.1-0.5b/1.5b/7b, No Robots, PKU-SafeRLHF, SciQ, FalseReject | non-commercial. The OpenAI non-compete clause is on the APIGen-MT-5k dataset card only, not the xLAM-2 model cards | R3 §2, §5 [corrected V-R3.4], R6 §4-§8 |
| Research-only weights: Nemotron-H-4B, Arch-Agent (katanemo-research), Hammer2.1-3b (qwen-research) | research licences | R9 §1.3, R3 §2 |
| Tencent Hunyuan | not in EU/UK/KR; >100M MAU needs a licence; forbids using outputs to improve other models | R1 §0.6, §2f [unverified: V-R1 did not reach claim 10] |
| NVIDIA Data Agreement for Model Training (Nemotron-CC-v2, CC-Math-v1, Pretraining-SFT-v1) | internal training only; no redistribution (no public manifest); no use that makes them subject to an open-source licence | R6 §0.4, §2 [unverified] |
| OpenAI-output-derived: OpenHermes-2.5, UltraFeedback, Tulu 3 persona sets, WildChat responses, Dolci's 302,406 OpenAI-generated answers, WildGuardMix/WildJailbreak, LMSYS-Chat-1M, DistilQwen2.5 data, Self-RAG critic labels | ToU bars using Output to build competing models; LMSYS adds no-redistribution and deletion on demand; UltraFeedback also contains all 811 TruthfulQA and 2,339 FalseQA prompts | R6 §0.2, §4-§7, R2 §4, R4 §7 [clause only via secondary captures] |

**Ambiguous (needs reading or counsel)**
| Item | Open question | Brief |
|---|---|---|
| Share-alike data: NQ (CC-BY-SA-3.0), HotpotQA/SQuAD2/SelfAware/UMWP (CC-BY-SA-4.0), Wikipedia, Infinity-Instruct, GSM8K-Platinum annotations | does share-alike reach trained weights? unsettled; Common Pile treats it as open | R4 §7, R6 §1, §8, §12.4, R8 §3 |
| LFM licence (LFM2/2.5) | "LFM Open License v1.0" vs CC-BY-4.0 in one summary; R9 says commercial use capped above $10M revenue; R1/R3 say terms unverified. Treat as unusable until the text is read | R1 gaps, R3 gaps, R9 §1.3, R8 §3 |
| ODC-By §4.3 and Common Crawl ToU | does a model count as a "Produced Work"? Common Crawl adds an indemnity for AI/LLM use | R6 §1 |
| Falcon-LLM licence (Falcon-E/H1); Qwen2.5 licence | attribution + AUP pass-through; "Built with Qwen"; outputs-clause applicability to Falcon-E uncertain | R2 §4 gaps, R6 §1 (Tier B-lite) |
| Teacher licences nobody read | DeepSeek-V3 (R6 §12 says MIT; R2/R4 only R1), DeepSeek-V2-Chat (xlam-60k generator), usage policy of the OpenAI open-weight 120B teacher in Toucan; generators unconfirmed for Dolci tool-use, Glaive, Hermes, ToolACE | R6 §12 + gaps, R3 §5 |
| Unspecified | Nemotron-CC (2024), PopQA, TriviaQA, Skywork-Reward, Spectra-1.1 weights | R6 gaps, R2 gaps |

---------------------------------------------------------------------------------------------------

## 4. Compute reality (arithmetic from R7; assumptions labelled)

**Assumptions.** A1: FLOPs = 6·N·D, no attention term (R7 §0). A2: H100 dense bf16 989 TFLOPS at 40% MFU (bounds 35-45%; anchors: SmolLM3 ~26% all-in, TinyLlama 51%, torchtitan 30-46%) (R7 §1-§2); H100-h = 6ND / (989e12 x 0.40 x 3600) [est].
A3: ternary QAT = 1.2x bf16 hours, memory unchanged, one data point (R7 §3). A4: price per H100-h $0.89 Vast spot, $2.69 RunPod community SXM, $3.63 market median, $6.88 AWS on-demand (R7 §4); R2 assumes $2-3 (R2 §5) and R5 $2.5 (R5 §6), below R7's median.
A5: real programme = 1.3-1.5x for restarts, ablations, evals; spot waste 10-20% (R7 §6). A6: a teacher forward costs 2·N_teacher per token: +38%/+89% for a 1.7B/4B teacher on a 1.5B student (R7 §2); +33%/+78% on a 1.7B student [est].
A7: Kaggle ~30 GPU-h/week (brief §3); T4x2 at 25% MFU gives ~0.6B tokens/week for a 1B model; 1B full training needs ~16 B/param ~16 GB (R7 §5); TPU v5e-8 ~7.6B tokens/week for 1B, quota uncertain (R7 §5).

| Scenario (ternary, no teacher, no programme multiplier) | H100-h | $ spot 0.89 | $ 2.69 | $ 3.63 | Brief |
|---|---|---|---|---|---|
| (a) 1B x 50B tokens | 253 | 225 | 680 | 917 | R7 §6 |
| (b) 1.5B x 100B | 758 | 675 | 2,039 | 2,752 | R7 §6 |
| (c) 3B x 100B | 1,516 | 1,349 | 4,078 | 5,503 | R7 §6 |
| (d) 1.7B CPT/distil x 10B | 86 | 76 | 231 | 312 | R7 §6 |
| (d') 1.7B x 20B | 172 | 153 | 462 | 624 | R7 §6 |
| 1.2B from scratch x 1T (35% MFU, x1.2) | ~6,100 | ~5,400 [est] | — | ~22,100 [est] | R5 §6 (R5 itself: ~$15k at $2.5/h) |
| 2.6B from scratch x 1T | ~14,700 | — | — | — | R5 §6 (~$37k at $2.5/h) |
| 2B x 10T own-data (R1 working number) | ~85,000 (40% MFU, no ternary x1.2) | — | — | ~$309k [est] | R1 §3 |

Path 2 end to end [est]: 30B tokens ternary = 258 H100-h (d' x1.5), +33% for a 1.7B teacher forward, x1.4 programme = ~480 H100-h, about $0.4k (spot) to $1.7k (median); consistent with R2's $0.4k-1.5k (R2 §5) only once the teacher forward and programme multiplier are counted (critique 8).

**What each tier buys [est from the inputs above].**
- Tier 0 (Kaggle, brief §3): evals, ablations <=300M, SFT of pre-quantized checkpoints; not pretraining (R7 §5). A TPU v5e-8 route could carry scenario (d) in ~2-3 weeks only if a JAX BitLinear exists (R7 §5). TRC application is R7's top free-compute action (R7 §5).
- Tier 1 (~$500): 138 H100-h at $3.63, 186 at $2.69, 562 at $0.89. Buys Path 1 continued pretraining (R7 §9.4: $300-600), or Path 2 at 10B tokens (86 h, ~115 h with a 1.7B teacher) only at spot or community prices. Not Path 3.
- Tier 2 (~$5,000): 1,377 H100-h at $3.63, 1,859 at $2.69, 5,618 at $0.89. Buys Path 2 at 30B tokens twice over, or scenario (b) (R7: $2,752 at median). Cannot buy 1.2B x 1T (~6,100 H100-h, R5 §6) except at spot with no programme multiplier (~$5.4k; ~$7.1k with x1.3).
- Caveats: R7's scenarios stop at 100B tokens, the BitNet-Era 3B parity point, while Spectra 1.5B at 300B is still -4.2 (R5 §2). R7 has no P100 row though the brief's Tier 0 names P100/T4 (brief §3, R7 §5). Prices are flat-to-up, not falling (R7 §4).

---------------------------------------------------------------------------------------------------

## 5. Evaluation: a frozen, decontaminated, receipt-verifiable suite (R8)

- **Frozen.** Item lists, prompt templates and gates are committed by hash before final training (R8 §7; brief §3 pre-registration). R8 pre-registers three primary endpoints (BFCL v4 overall, AbstentionBench recall at precision >=0.80, IFEval prompt-strict); all other gates are Holm-corrected secondary (R8 §7).
- **Decontaminated (R8 G0).** Qwen2.5 rule on the ALICE tokenizer: drop on LCS >=13 tokens and >=0.6 of min length, plus 8-gram overlap >=50% via open-instruct tooling, over all pre- and post-training data against every reported item; publish removal counts, clean-vs-dirty scores and a Transparency Card (R8 §1, §7).
  N-gram rules miss paraphrase and translation (R8 §1), so add probes: 60%-prefix exact match <=5% on MATH-500 and GSM8K-Platinum (Llama-3.1-8B reference 3.8%), ConStat-style paraphrase delta <=3 pp, Zero-CoT truncation probe (R8 G0.2). Keep a 300-item private Aefinity holdout with randomised correct answers (R8 §7).
  Upstream data status: decontaminated FineMath, Stack v2, Dolma 3, Tulu 3 SFT; no statement for FineWeb-Edu, DCLM-baseline, TxT360, Zyda-2, Common Pile, Dolci; known leaks UltraFeedback and NuminaMath-TIR (11.3% MATH overlap) (R6 §9).
- **Receipt-verifiable bundle (R8 §6).**
  - Manifest: eval id + revision hash, item-list hash, template hash, MODEL.SAF digest, engine build digest, greedy decode at 2048 ctx, tokenizer digest, ASCII-normalisation rule with the count of unrepresentable items. Items longer than ctx score 0 and are counted, never dropped.
  - Per item: doc/prompt/target hashes + CIS-1 receipt (tokens, integer answer log-probs, every CALC/LOOKUP request and response hash, TPM quote). Signed Merkle root over items.
  - Replay protocol: a third party replays any 1% on any x86_64 CPU and needs identical receipts, one mismatch invalidates the bundle; full battery gives identical roots on two CPUs (penguin AVX2, box1) (R8 G0.3). Judge-scored sets (MT-Bench, Arena-Hard-Auto, WildBench) sit in an "unreceipted" tier and never gate (R8 §6).
- **Statistics.** Wilson, Clopper-Pearson or bootstrap rather than CLT below a few hundred items; exact McNemar and paired bootstrap (10k) for model vs model; clustered SEs when items share a source; "better" needs p<0.05 and a CI excluding 0, "not worse" needs lower bound >= -2 pp (R8 §2, G1).
  Sizing: n=164 gives +-7.7 pp, 541 +-4.2, 1,000 +-3.1 (R8 §2). Baseline: re-run BitNet-2B-4T on the same harness (R8 G1; the brief already has T1 = 45/58).
- **Behaviour metrics (R8 §5, R4 §1).** SimpleQA-style correct / incorrect / not-attempted; threshold-penalised score at t=0.75 (wrong costs -3), R4 adds t = 0.5, 0.75, 0.9; ECE (15 equal-mass bins), smoothECE, Brier, AURC, selective accuracy at 70% coverage; abstention recall at precision >=0.80; When2Call over-call rate and ToolBeHonest solvability.
- **Proposed absolute gates (R8 §7, analyst proposals).** MMLU-Redux 2.0 >=60, MMLU-Pro >=35, GSM8K-Platinum >=65, MATH-500 >=50, HumanEval+ >=45, IFEval >=70, BFCL v4 overall >=50 with non-live >=80 / live >=70 / multi-turn >=25 / irrelevance >=85, AbstentionBench recall >=0.70,
  SimpleQA Verified air-gapped not-attempted >=75%, connected correct >=50% with a LOOKUP receipt on >=95% of attempts, ECE and smoothECE <=0.08, footprint <=1.4 GB RSS. R8 says these are bracketed by vendor numbers on different harnesses and must be re-baselined (R8 gaps).
- **Dev loop.** CIS-1 exact held-out perplexity plus 100-item IRT subsets, averaged over the last 3 checkpoints; full battery at milestones (R8 §7).
- **Not covered by R8 [est].** The brief's own `agent_trace` buckets and its Wilson rule, `unknown_fact`, `unanswerable`, the snapshot fact-check fixtures (>=90% revised-to-correct), the perplexity gate (<=5% worse than BitNet-2B at <= half the bytes), CIS int-vs-float agreement, and the 3-microarchitecture boot gate (brief §4).

---------------------------------------------------------------------------------------------------

## 6. Architecture options compatible with integer-exact inference (R9), ranked by benefit x feasibility

Brief §1: the same family drops in with zero engine work; every new layer type or activation needs a numbered CIS errata with goldens unchanged. B and F are my 1-5 scores [est]; R9's own feasibility numbers (0.3-1.0) measure op-expressibility, not spec and kernel effort.

| # | Option | Evidence at <=3B (R9 unless noted) | Engine delta | B | F | BxF |
|---|---|---|---|---|---|---|
| 1 | Tool/control tokens + gateway legality state machine (logit mask) | Octopus v2 (2B), FunctionGemma-270M BFCL Simple 61.6 (§1.6, R3 §3); R4 §6.1 [IDK]/[RET]/[ISSUP]/[CITE] | no kernel; tokenizer rows, gateway state machine, verifier fixtures; logit masking is new decode semantics (errata) | 5 | 4 | 20 |
| 2 | Integer "warden" encoder, 20-100M params (injection screen, abstain-vs-lookup, answer/evidence agreement) | Prompt Guard 2-22M, I-BERT integer-only encoder (§1.7) | second model in the boot bundle; bidirectional attention, integer LayerNorm/GELU/softmax kernels outside the decoder set | 4 | 3 | 12 |
| 3 | Disk-resident conditional memory (Engram / product-key), receipt-writable | PKM 1.3B + 128B memory: TriviaQA 62.14 vs Llama2-7B 64.00; Engram 3B/100B val loss 1.768 vs 1.808 (§1.5) | new layer type (hash, gather, top-k, LUT softmax/sigmoid, depthwise conv); table paging in the FAT32 loader; new hashed bundle file; must be trained with the backbone | 4 | 2 | 8 |
| 4 | int8 KV (+ cross-layer KV sharing) | CLA halves KV at 1B/3B; BitNet-2B KV at 2048 ctx is 79 MB int8 (§1.11) | storage format + integer scales; errata if the engine KV is not already int8 (not stated in any brief) | 2 | 4 | 8 |
| 5 | Sliding-window:global 3:1-5:1, NoPE on global, QK-norm | Gemma 3 1B, SmolLM3 3B, Maple (§1.2); neutral at 2048 ctx (§1.2) | attention mask or ring-buffer KV, per-layer RoPE flag, per-head Q/K norm; changes attention semantics | 2 | 3 | 6 |
| 6 | Gated short-conv mixer in most layers (LFM2-style) | LFM2-1.2B 2x CPU decode vs Qwen3 (vendor claim; quantisation and kernels not stated), MMLU 55.23 vs 59.11 (§1.3) | new layer type: depthwise causal conv, int8 elementwise gates, conv-state cache; new AVX2/NEON/VNNI kernels + goldens; realistically Path 3 | 3 | 2 | 6 |
| 7 | Early exit on an integer margin test (non-speculative) | LayerSkip, 1.5B-class (§1.10) | variable-depth decode loop; receipt records exit layer; no ternary evidence | 2 | 3 | 6 |
| 8 | Design-time 32-48K vocab, tied int8 | vocab scaling (§1.8) | tokenizer change; marginal vs the A35 prune (~19 MB int8, 40,960 vs 50,256 rows at d=2048 [est]); breaks shared-tokenizer KD (R2 §0.2) | 1 | 3 | 3 |
| 9 | Ternary fine-grained MoE | Phi-tiny-MoE 3.8B/1.1B, SmallThinker 4B, Maple 20B (§1.1) | integer router, top-k with tie-break spec, expert paging in UEFI; evidence at 4-20B total only | 3 | 1 | 3 |
| 10 | Mamba-2 hybrid | Falcon-H1 strong; Granite H-1B BFCL v3 50.21 vs 54.82 (§1.3) | softplus/exp/SiLU LUTs, i64 state, outlier-heavy activations | 1 | 1 | 1 |
| 11 | Byte-level / dynamic chunking; Titans test-time memory | parity only (BLT, H-Net); <=760M (Titans) (§1.9, §1.5) | extra models or per-token gradient updates | 1 | 1 | 1 |
| — | MTP D=1 head / LayerSkip self-speculation | lossless under greedy; DeepSeek-V3 acceptance 85-90%, 1.8x TPS; LayerSkip 1.82x on a 1.5B-class code model; GPU literature, unmeasured on AVX2 (§1.4, §1.10) | extra block and verify loop. **Excluded by brief §6** (no speculative decoding in the receipt-grade path); if amended, B3 x F4 = 12 [est] | — | — | — |

Notes. R9's "Adopt" list is mostly demoted here. Options 5 and 6 change the attention or mixer family, so they realistically need Path 3 (no brief evaluates retrofitting them onto a converted base, §2); option 7 needs a layer-dropout training stage; MTP/self-speculation conflicts with the brief's non-goals.
R9's ~2B composite (gated-conv + GQA + control tokens + memory table + warden) has ternary weights ~0.5 GB (R9 §3) = the 500 MB hard cap (brief §3), no ternary evidence for the conv mixer, and R9 itself says no published model combines these (R9 §3) [unverified].
Options 1, 2 and 4 fit any path. At 2048 ctx the KV and window options buy little (R9 §1.2, §1.11).

---------------------------------------------------------------------------------------------------

## 7. Critique checklist (missing, unsupported or contradictory across the briefs)

1. [ ] **Three size budgets, no stated bits per weight.** Brief §3: <=500 MB packed hard, <=300 MB target. R5: 1.4 GB target / 2 GB floor (R5 §5). R8: RSS <=1.4 GB (R8 §7). R2: "well inside 1.4 GB" (R2 §5). Brief §1 gives 2.4B ~ 480 MB (~1.6 bpw); R5 assumes 2.0 bpw (R5 §5).
   A Qwen3-1.7B body (1.4B non-embedding, R2 §5) is ~282 MB at 1.6 bpw and ~352 MB at 2.0 bpw [est]: the 300 MB target depends on the unstated packing density. R9's 2B composite is ~0.5 GB (R9 §3).
2. [ ] **R5's 2B4T ternary count (1.553B) assumes a two-matrix FFN; the other briefs imply three.** R7 lists 2,412.8M params for the bf16 repo (R7 §3) and the brief says "SwiGLU with ReLU²" (brief §1). From R5's own config (30 layers, d 2560, FFN 6912, vocab 128,256 tied), a gated three-matrix FFN gives ~2.08B ternary + 0.33B embedding = 2.41B [est], matching R7; two matrices give 1.88B total.
   R5's 2B4T memory rows are therefore understated, and its ALICE-Next-1.2B (1.057B ternary, R5 §5) would be ~1.46B if the engine FFN is gated [est]. Check the aegis-core FFN structure before sizing anything.
3. [ ] **One BFCL number, three harnesses.** Qwen3-1.7B BFCL v3 is 71.8 (R2 §3, Bonsai harness), 52.2 (R1 T2, R3 §3, R8 §3, Qwen3 report) and 28.41 overall on the official v4 board (R3 §2). The "-20.8 tool-calling hit" (R2, R5 §3, R7 §7) rests on the first alone: against 52.2, Bonsai's 51.0 would be ~98% retention [est]. R2's own gap admits "one data point".
4. [ ] **R8's primary tool endpoint does not match the brief's gates or the air-gapped variant.** The brief gates `agent_trace` buckets with a strict `CALC/LOOKUP/FILE-READ` grammar (brief §1, §4); R8's primaries are BFCL v4 overall, AbstentionBench, IFEval (R8 §7). BFCL v4 overall weights Agentic at 40% (R3 §1, V-R3.3).
   My arithmetic reproduces Qwen3-4B-Instruct-2507's official 35.68 when Agentic = mean(Web Search 3.00, Memory 17.63) (R3 §2) [est]. Meeting R8's sub-gates exactly (80/70/25/85) and overall >=50 would need Agentic ~47.5% [est], vs best <=4B 3.00 / 17.63 (R3 §2); the only <=4B model above 50 overall in R0-V's check is Nanbeige4-3B-Thinking (51.40, V-R3.1), a thinking model (decode cost: R1 §2g). The air-gapped variant has no search tool at all.
5. [ ] **The brief's tool gate is nearly a perfect-score gate at n=30.** Wilson lower bound >=85% at n>=30 (brief §4): at 95% confidence only 30/30 passes (LB 0.886); 29/30 gives 0.833 [est]. The confidence level is not stated. n=50 allows 2 errors, n=60 allows 3, n=100 allows 5 [est]. R8 gives sizing rules but never applies them to this gate (R8 §2). Fix n and the interval before freezing.
6. [ ] **R8's absolute gates outrun the conversion evidence, and the brief never asks for them.** IFEval >=70 and MMLU-Redux >=60 (R8 §7) vs BitNet-2B IFEval 53.48 (R8 §3) and Qwen3-1.7B 68.2 / 64.4 (R8 §3) at ~88% ternary retention (R2 §2) gives ~60 / ~57 [est]. The brief's quality gate is perplexity only (brief §4). R8 calls its thresholds analyst proposals (R8 gaps).
7. [ ] **Path 2's engine delta is unpriced.** R2 calls Qwen3-1.7B "standard ops, CIS-1-expressible" (R2 §5) and prices only per-group scales (R2 §6). R1 lists SwiGLU for Qwen3 (R1 T1) while the engine runs ReLU² (brief §1); BitDistill inserts SubLN (R2 §2); the vocab is 151,936 pruned (R2 §5). Each needs errata plus goldens (brief §1). Whether Qwen3 carries per-head Q/K normalisation is not discussed in R1-R9: check its config.
8. [ ] **Compute omissions.** R2's Path B 75-100 H100-h (R2 §5) excludes teacher forwards (+33%/+78% [est]; R7 §2) and attention-distillation overhead. Prices differ across briefs: R2 $2-3, R5 $2.5, R7 median $3.63 with range $0.89-$6.88 (R2 §5, R5 §6, R7 §4). On-policy KD (50-100 H100-h, R2) and abstention RL (1-3 days on 4-8 A100/H100 "[uncertain]", R4 §6.4) are not in R7's tables.
9. [ ] **"Compute is not the obstacle" holds only at 100B tokens.** R7 §6 stops there; R5/R2 say a from-scratch ternary wants >=1T (R5 §8, R2 §5) and R1 says >=8-10T for an open-web 1B (R1 §3). The brief never states the general-capability bar, so nobody can say which token budget is needed. R6 §10 is a 10B pilot (R6 §10 caveat), mappable to a Path 1/2 continued-pretraining mix, not a Path 3 plan.
10. [ ] **Abstention labels depend on the weights they train.** R4 §0.1 and R6 §8: labels come from probing the post-pretraining model, so every base re-spin (Path 1/2/3) invalidates them, and the RL stage needs rollouts. No brief measures calibration or abstention on a ternary model (R4 gaps, R5 gaps). The "retrieve, don't memorise" premise rests on the unverified finding 9.
11. [ ] **Train/eval overlap is unchecked.** R6 §11 trains on SelfAware, KUQ, UMWP, SQuAD2-unanswerable and (optionally) CoCoNot; R4 §4 evaluates on SelfAware, CoCoNot, FreshQA and AbstentionBench, R8 §7 on AbstentionBench and FreshQA (AbstentionBench's 20 constituent datasets are not enumerated in R4 or R8). R8's decontamination gate (G0.1) must cover every training set against these evals, including CoCoNot used as both over-refusal eval (R4) and training data (R6).
12. [ ] **Four tool-call formats, one tokenizer problem.** Hermes JSON-in-XML (R3 §6), `[IDK] [RET] [ISSUP] [CITE]` tokens (R4 §6.1), ~64 control tokens (R9 §1.6), and the brief's `CALC(...)` grammar. Public tool data (xLAM, Toucan) is in other formats (R3 §5; R6 §10 re-renders it). A bespoke 40,960-token vocab (R9 §1.8) kills logit KD from Qwen3 (R2 §0.2) and conflicts with "pruning reproducible from the public tokenizer" (brief §1).
13. [ ] **Context length is never sized.** ALICE's context is 2,048 (R1 §2e, R8 §6, R9 §0); BitNet-2B supports 4,096 (R1 T1, R5 §2) and R5's KV rows assume 4k (R5 §5). The connected loop (draft + snapshot + revision) may not fit 2,048; no brief budgets it. R1 prices a long-context stage at ~1-2% of tokens (R1 §2e).
14. [ ] **R9's "Adopt" list contradicts the brief and over-reads feasibility.** MTP and LayerSkip self-speculation (R9 rank 6-7) violate brief §6. Feasibility "1.0" for SWA/NoPE/QK-norm/gated-conv ignores the errata rule (brief §1). LFM2's 2x CPU speed is a vendor fp number against Qwen3 (R9 §1.3), while the ternary kernel already reads ~90% of DRAM bandwidth and speed scales with bytes/token (brief §1), so a mixer swap that does not cut bytes should not be credited with it [est].
15. [ ] **Licence claims rest on unread primary text.** The OpenAI Output clause comes from secondary captures (R2 gaps), recollection (R4 gaps) and a third-party mirror (R6 gaps). R6's teacher whitelist asserts MIT for DeepSeek-V3 (R6 §12) while R2/R4 verify only R1; xlam-60k generators and Toucan's OpenAI open-weight teacher have no licence read (R3 §5). LFM terms conflict across R1/R3/R8/R9. No brief documents CDLA.
16. [ ] **Sovereignty and publication decisions are pending.** Path 2 ends the "no external teacher" claim (R2 §4, R5 §6, R7 §7); R6 §12 asks Justin to whitelist teachers, accept or refuse Tier B, the NVIDIA agreement, and share-alike pools. A Qwen-derived ternary model with a large jump or product shape may be a PUBLISH? item under Aefinity's publish policy; no brief says what stays private in the meantime.
17. [ ] **Verification coverage is thin exactly where the plan leans.** R0-V did not run on R5-R9 (R0-V header). In R1-R4 it skipped: the WSD-cooldown claim and the Hunyuan licence (R1), the 100B-token HF Llama-3-8B conversion and the capability-stratified result (R2), Toucan / Granite / Nemotron / the refusal-collapse card (R3), Apple routing and the Llama 3.1 licence (R4).
    Re-verify the capability-stratified result and the Hunyuan licence before they gate a decision.
18. [ ] **Prompt injection through FETCH content is addressed only by R9's warden (R9 §1.7).** The brief snapshots fetched bytes into context and hashes them (brief §2.4); no brief proposes an injection eval, and R8's suite has none.
19. [ ] **Vocabulary and language assumptions.** R1 says the 50,256 ASCII vocab costs ~2.5-3x more tokens per character (R1 §2b) with no source, while R9 puts a ~40K English BPE at ~4 chars/token (R9 §1.9) and the brief reports +0.12% PPL for the prune (brief §1); measure on the real tokenizer. Path 2's teacher is multilingual (119 languages, R1 T1) and R6 filters to ASCII (R6 header): language loss and ASCII-only distillation data are unaddressed.
