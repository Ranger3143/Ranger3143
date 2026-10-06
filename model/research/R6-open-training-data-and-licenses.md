> Research brief produced on 2026-10-06 by a web-research agent for the ALICE-Next model plan. Every claim carries the URL the agent read; items it could not verify are listed under Gaps. Numbers here are the cited papers' numbers, not Aefinity measurements.

# ANGLE 6 — Open training data for ALICE-Next (1–3B, tool-expert, calibrated), with licenses and provenance

Date: 2026-10-06. Sources: HF dataset cards (fetched 2026-10-06), papers, license texts. Token counts are in each dataset's own tokenizer (Llama-3, GPT-NeoX, SmolLM2, Mistral); ALICE's 50,256-token ASCII-pruned Llama-3 vocabulary will count differently and non-ASCII documents must be filtered out before any budget is final.

## 0. Bottom line

1. There is enough **Tier-A ("sovereign-clean")** data to build ALICE-Next without any OpenAI/Anthropic/Google-generated text: human-written or openly licensed pretraining (FineWeb-Edu, DCLM, Common Pile, Stack-Edu, FineMath) plus synthetic data from **Apache-2.0/MIT teachers** (Qwen3, DeepSeek-R1/V3, QwQ-32B, Mixtral, gpt-oss-120b, Phi-4) for reasoning, chat and tool use (Toucan-1.5M, Nemotron-Agentic-v1, OpenThoughts3, OpenMathReasoning, SmolTalk2's Qwen3 subsets).
2. The most-used "open" post-training sets are **ToS-tainted (Tier C)**: OpenHermes-2.5, WildChat responses, Tulu 3 persona sets (GPT-4o), UltraFeedback (GPT-4 judge + GPT-4 completions), WildGuardMix/WildJailbreak (GPT-4/3.5), Dolci's 302K GPT-4.1 WildChat answers, Tulu/Dolci DPO (GPT-4o judge), LMSYS-Chat-1M. OpenAI's ToU forbids using Output "to develop models that compete with OpenAI" — a contractual (not copyright) exposure on whoever generated the data, but a provenance stain the receipt chain cannot launder. Exclude for the sovereignty proof.
3. **Tier B (attribution-bound)**: Llama-3.x-generated sets (Magpie, Smol-Magpie-Ultra, OpenMathInstruct-2, everyday-conversations) trigger the Llama licence's requirement to put "Llama" at the start of the derived model's name and to show "Built with Llama". Qwen2.5-72B-generated sets (SmolTalk's constraints/rewrite/summarize) require a "Built with Qwen" notice. Qwen3 is Apache-2.0 and carries no such obligation. **Decision for Justin** (NEEDS): accept Tier B and rename, or stay Tier A. Recommendation: Tier A only.
4. **NVIDIA's Nemotron pretraining sets (CC-v2, CC-Math-v1, Code-v1, SFT-v1) are not open data**: the "NVIDIA Data Agreement for Model Training" restricts use to internal training, forbids redistribution and forbids using the data "in any manner that would cause them to become subject to an open-source license" (trained models stay the company's property). Usable for training; cannot be mirrored in a public data manifest. Excluded by default below; Nemotron *post-training* sets (CC-BY-4.0) are fine.
5. Abstention data is model-specific by construction (R-Tuning/Idk recipe: label questions by whether *this* model answers them correctly). It must be regenerated from ALICE-Next's own probes over permissively licensed QA pools; public abstention sets are small (KUQ, SelfAware, UMWP) or evaluation-only/NC (AbstentionBench).

## 1. Provenance tiers and license primer

| Tier | Definition | Consequence |
|---|---|---|
| A sovereign-clean | human-written / PD / ODC-By / CC-BY / CC-BY-SA / Apache / MIT, or synthetic from Apache/MIT-licensed generators | usable, redistributable manifest, no naming obligations |
| B attribution-bound | synthetic from Llama-3.x (Llama Community License) or Qwen2.5 (Qwen License) | model name must begin "Llama" + "Built with Llama" ([license §1.b.i](https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE)); "Built with Qwen" notice ([Qwen License §5.b](https://huggingface.co/Qwen/Qwen2.5-72B-Instruct/blob/main/LICENSE)) |
| C ToS-tainted | any GPT-3.5/4/4o/4.1, Claude, Gemini, Bard output or judge | OpenAI ToU: "Use Output to develop models that compete with OpenAI" is prohibited ([mirror of 2024-12-11 ToU](https://open.windriver.com/info/uni-license-list/licenses/openai-tou-20241211.html)); openai.com returned 403 to the fetch |
| D non-commercial / non-redistributable | CC-BY-NC, LMSYS license, NVIDIA Data Agreement, Stack v2 bulk (SWH agreement) | exclude or quarantine |

ODC-By 1.0 §4.3: a publicly used "Produced Work" (a model counts) needs a notice that content came from the database and is available under ODC-By ([text](https://opendatacommons.org/licenses/by/1-0/)). CC-BY-SA share-alike attaching to model weights is legally unsettled [uncertain]; Common Pile treats CC-BY-SA as "open" under Open Definition 2.1 and excludes NC/ND ([paper](https://arxiv.org/html/2506.05209)). Common Crawl ToU add an indemnity for AI/LLM use ([ToU §9](https://commoncrawl.org/terms-of-use)).

## 2. Pretraining corpora

| Dataset | Size | License | Synthetic? / generator | Contamination | Tier |
|---|---|---|---|---|---|
| [FineWeb-Edu](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) | 1.3T tok (score≥3); [score-2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu-score-2) 5.4T; dumps CC-MAIN-2013-20→2025-26 | ODC-By + CC ToU | classifier trained on Llama3-70B annotations (not generated text) | no decontamination statement on card | A |
| [FineWeb](https://huggingface.co/datasets/HuggingFaceFW/fineweb) | >18.5T | ODC-By | no | none stated | A |
| [FineWeb 2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) / [FineWeb2-HQ](https://huggingface.co/datasets/epfml/FineWeb2-HQ) | >1,000 languages; HQ = top 10% in 20 languages, 380,138,261 docs | ODC-By | no | none stated | A — irrelevant for an ASCII tokenizer |
| [DCLM-baseline](https://huggingface.co/datasets/mlfoundations/dclm-baseline-1.0) | 4T tok / 3B docs / 7.2 TB | CC-BY-4.0 | no | paper: MMLU/HellaSwag overlap check, 51.8→52.7 MMLU after removal, "many false positives", tooling shipped rather than a decontaminated pool ([paper](https://arxiv.org/html/2406.11794)); a leaked MMLU-EE site reported inside DCLM [uncertain, secondary] | A |
| Nemotron-CC (2024) | 6.3T = 4.4T real + 1.9T synthetic; hosted at commoncrawl.org | no explicit license found; inherits CC ToU [uncertain] | yes, rephrasing (generator not named on host page) | none stated | A/unclear |
| [Nemotron-CC-v2](https://huggingface.co/datasets/nvidia/Nemotron-CC-v2) (Nemotron-Pretraining-Dataset-v1, 6,585.8B total) | EN CC 3,359.8B; synthetic CC 1,257.3B; Diverse QA 692.9B; Math 206.2B; Math SFT 190.6B; synthetic code 174.9B; Code SFT 58.5B; General SFT 87.5B | **NVIDIA Data Agreement for Model Training** ([text](https://scancode-licensedb.aboutcode.org/nvidia-model-training-2025.html)) | Mistral-Nemo-12B-Instruct, Qwen3-30B-A3B (CC rephrase); Phi-4 (math); Mixtral-8x22B (code); DeepSeek-R1/V3, Qwen2.5/3 (SFT) | none stated | D (gated, no redistribution) |
| [Nemotron-CC-Math-v1](https://huggingface.co/datasets/nvidia/Nemotron-CC-Math-v1) | 3+: 133B/101.15M docs; 4+: 52B/45.10M; MIND 73B | NVIDIA Open Data License; Phi-4 (MIT) terms flow down | Phi-4 cleaning/LaTeX normalisation | LLM-based check vs MATH, GSM8K, MMLU, MMLU-Pro | D |
| [OLMo-mix-1124](https://huggingface.co/datasets/allenai/olmo-mix-1124) (Dolma 2) | DCLM 3.70T, StarCoder 83.0B, peS2o 58.6B, arXiv 20.8B, Algebraic-Stack 11.8B | ODC-By (DCLM CC-BY) | no | FLAN decontaminated (≥10% n-gram overlap removed) ([OLMo 2](https://arxiv.org/html/2501.00656)) | A |
| [Dolma 3 Mix](https://huggingface.co/datasets/allenai/dolma3_mix-6T-1025) | 5.93T: CC 4.51T, olmOCR PDFs 805B, stack_edu 409B, finemath-3+ 151B, proofpile-arXiv 50.9B, wiki 2.51B (pool 9.3T) | ODC-By | no | "decon" package, IDF-weighted overlap ([Olmo 3 §3.5.3](https://arxiv.org/html/2512.13961)); some olmOCR texts since `[REMOVED]` | A |
| [Common Pile v0.1 / Comma training set](https://huggingface.co/datasets/common-pile/comma_v0.1_training_dataset) | 8 TB raw, 30 sources; Comma mix 1.07T main + 39.5B cooldown (521 GB) | per-source PD/CC-BY/CC-BY-SA/Blue Oak; NC/ND excluded | no | Winogrande present via DPI → excluded from eval | A (best provenance) |
| [Common Corpus](https://huggingface.co/datasets/PleIAs/common_corpus) | 2.27T (OpenCulture 967B, OpenGovernment 579B, OpenSource 283B, OpenScience 281B, OpenWeb 88.5B, OpenSemantic 68.0B); EN+FR dominant | PD/CC0/CC-BY-SA/MIT/Licence ouverte | no | PII/toxicity filtered; no benchmark statement | A |
| [The Stack v2](https://huggingface.co/datasets/bigcode/the-stack-v2) | 67.5 TB / 3.28B files; dedup 32.1 TB; train-full ~900B tok, 619 languages | per-file permissive (Blue Oak/ScanCode) + unlicensed; bulk needs SWH/INRIA agreement; opt-out | no | HumanEval, MBPP, APPS, GSM8K, DS-1000 removed ([StarCoder2 §3.3](https://arxiv.org/html/2402.19173)) | A/D (gated; SWHIDs only) |
| [Stack-Edu](https://huggingface.co/datasets/HuggingFaceTB/stack-edu) | 125B tok, 15 langs (Java 42.1B, Python 21.8B, C++ 16.0B, Markdown 14.0B, C 11.1B, JS 11.1B, SQL 9.62B, Rust 1.75B…) | inherits Stack v2 | no | inherits Stack v2 | A |
| [FineMath](https://huggingface.co/datasets/HuggingFaceTB/finemath) | 3+ 34B; 4+ 9.6B; InfiMM-WebMath-3+ 20.5B; 4+ 8.5B | ODC-By | no | 13-gram vs GSM8K, MATH, MMLU, ARC (logs published) | A |
| [SmolLM-Corpus](https://huggingface.co/datasets/HuggingFaceTB/smollm-corpus) (Cosmopedia v2) | Cosmopedia v2 28B (39.1M docs), Python-Edu 4B, FineWeb-Edu-dedup 220B | ODC-By | yes: Mixtral-8x7B-Instruct-v0.1 (Apache) | none stated | A |
| [TxT360](https://huggingface.co/datasets/IFM/TxT360) | ~5T deduped (CC 4.83T; papers 155B; StackExchange 27.8B; wiki 36.0B; FreeLaw 16.7B; USPTO 4.95B; PG-19 2.63B; EuroParl 1.96B; Ubuntu IRC 1.89B; HN 1.05B); 15T+ upsampled | ODC-By | BestOfWeb filter (ProX) | none stated | A |
| [Zyda-2](https://huggingface.co/datasets/Zyphra/Zyda-2) | 5.07T (DCLM 3,348.9B, FineWeb-Edu 1,319.2B, Dolma-CC 238.4B, Zyda-1 163.6B) | ODC-By | no (NeMo-Curator classifier) | none; PII not filtered | A |
| [Essential-Web v1.0](https://huggingface.co/datasets/EssentialAI/essential-web-v1.0) / [Ultra-FineWeb](https://huggingface.co/datasets/openbmb/Ultra-FineWeb) | 24T with taxonomy metadata / ~1T EN + 120B ZH | ODC-By / Apache-2.0 | no | none stated | A |

## 3. Mid-training / annealing sets

| Set | Size | License | Generators | Tier |
|---|---|---|---|---|
| [Dolmino-mix-1124](https://huggingface.co/datasets/allenai/dolmino-mix-1124) | HQ 832.6B (DCLM top-7% 752B, FLAN 17.0B, peS2o 58.6B, wiki 3.7B, SE 1.26B) + math 10.7B (TinyGSM-MIND 6.48B, MathCoder2 3.87B, TuluMath 230M, GSM8K-train 2.74M) | ODC-By | synthetic math generators not stated [uncertain] | A/unclear |
| [Dolma 3 Dolmino 100B](https://huggingface.co/datasets/allenai/dolma3_dolmino_mix-100B-1025) | 99.95B: HQ CC 22.4B, Dolmino Math 10.7B, StackEdu-FIM 10.0B, CraneCode 10.0B, Reddit→flashcards 5.9B, Nemotron Synth QA 5.0B, Flan 5.0B, QwQ traces 1.87B, OpenThoughts2 1.25B, Llama-Nemotron traces 1.25B, Tulu 3 SFT 1.1B, **Gemini traces 246M** | ODC-By | mixed: QwQ (A), Llama-Nemotron (B), Gemini (C), Tulu SFT (C) | mixed — take subsets |
| [MegaMath](https://huggingface.co/datasets/IFM/MegaMath) | >300B | ODC-By | synthetic subsets, generator unverified here | A for web parts |
| SmolLM3 mid-training | 140B reasoning tokens = Llama-Nemotron-Post-Training 3,644,790 + OpenThoughts3 1,135,104 rows ([SmolTalk2 Mid](https://huggingface.co/datasets/HuggingFaceTB/smoltalk2)) | CC-BY-4.0 / Apache-2.0 | DeepSeek-R1, Qwen2.5 (A); Llama-3.3-70B 420,021 rows (B) | A if Llama rows dropped |
| [OpenThoughts3-1.2M](https://huggingface.co/datasets/open-thoughts/OpenThoughts3-1.2M) | 850K math / 250K code / 100K science | Apache-2.0 | QwQ-32B | A |
| [OpenMathReasoning](https://huggingface.co/datasets/nvidia/OpenMathReasoning) | 306K problems; 3.2M CoT; 1.7M TIR (Python); 566K GenSelect | CC-BY-4.0 | DeepSeek-R1 / QwQ-32B; decontaminated | A — TIR is directly CALC-shaped |

## 4. Instruction / chat

| Set | Size | License | Generator / taint | Decontam |
|---|---|---|---|---|
| [SmolTalk](https://huggingface.co/datasets/HuggingFaceTB/smoltalk) | 1.1M: Magpie-Ultra 431K, Numina-CoT 112K, summarize 101K, OpenHermes 100K, APIGen 87.5K, rewrite 56.2K, Self-OSS 50.7K, MetaMathQA 50K, constraints 36.2K, SystemChats 35.9K… | new subsets Apache-2.0; rest original | Magpie-Ultra: Llama-3.1-405B (B); constraints/rewrite/summarize: Qwen2.5-72B (B-lite) ([SmolLM2 paper](https://arxiv.org/html/2502.02737)); OpenHermes/MetaMath (C) | vs IFEval |
| [SmolTalk2](https://huggingface.co/datasets/HuggingFaceTB/smoltalk2) | Mid 4.78M; SFT 3.38M (25 subsets: OpenThoughts3 think 1,133,524 / no_think 435,193; Magpie-Ultra 406,843; OpenHermes 384,900; multilingual8 244,736+254,047; smol_summarize 96,061; Mixture-of-Thoughts sci 86,110; xlam_traces 59,962; smol_rewrite 53,262; systemchats 27,436+33,997; aya-Qwen3 15,222; table_gpt 13,201+13,203; smolagents traces 9,079; hermes-FC 8,961…); Pref 447K | new subsets Apache-2.0 | Qwen3-32B/235B, DeepSeek-V3-0324 (A); Magpie/OpenHermes carried over (B/C) | vs eval benchmarks |
| [Tulu 3 SFT](https://huggingface.co/datasets/allenai/tulu-3-sft-mixture) | 939,344: Persona MATH 149,960, GSM 49,980, Python 34,999, Algebra 20,000, IF 29,980 (GPT-4o); Evol-CodeAlpaca 107,276 (GPT-4); WildChat GPT-4 100,000; Aya 100,000; FLAN 89,982; NuminaMath-TIR 64,312; WildGuardMix 50,000; WildJailbreak 50,000; CoCoNot 10,983; No Robots 9,500 (CC-BY-NC); OASST 7,132; SciRIFF 10,000; TableGPT 5,000 | ODC-By (subsets vary; some NC) | heavy C | 8-gram, >2% rule; removed NuminaMath-TIR 11.3% (MATH), Evol-CodeAlpaca 3.5% (HumanEval), WildChat 5.4% (safety) ([paper](https://arxiv.org/html/2411.15124)) |
| [Dolci-Instruct-SFT](https://huggingface.co/datasets/allenai/Dolci-Instruct-SFT) (Olmo 3) | 2,152,112: verifiable reasoning 310,572; WildChat w/ **GPT-4.1** 302,406; tool use 227,579; Python algorithms 186,345; logic 159,882; Persona MATH 149,958; precise IF 136,833; Evol-CodeAlpaca 107,270; Aya 99,987; OpenThoughts3 99,268; FLAN 89,981… | ODC-By | GPT-4.1 + GPT-4o personas (C); tool/logic/verifiable generators not named [uncertain]; Azure-API topic filtering | not stated |
| [OpenHermes-2.5](https://huggingface.co/datasets/teknium/OpenHermes-2.5) | ~1M | **none stated** | GPT-4 sources (ShareGPT GPT-4, GPT4-LLM, Unnatural-GPT4, CoT-Alpaca-GPT4…) | none |
| [Hermes-3](https://huggingface.co/datasets/NousResearch/Hermes-3-Dataset) | 958,829 | Apache-2.0 | undocumented card [uncertain] | none |
| Magpie ([Pro-300K](https://huggingface.co/datasets/Magpie-Align/Magpie-Pro-300K-Filtered), [3.1-MT-300K](https://huggingface.co/datasets/Magpie-Align/Magpie-Llama-3.1-Pro-MT-300K-Filtered), [R1-Llama-70B 250K](https://huggingface.co/datasets/Magpie-Align/Magpie-Reasoning-V2-250K-CoT-Deepseek-R1-Llama-70B)) | 300K / 300K / 250K | llama3 / llama3.1 / llama3.3 | B | minimal |
| [Infinity-Instruct](https://huggingface.co/datasets/BAAI/Infinity-Instruct) | F-7.4M (7,449,106) + Gen-1.5M (1,456,927); gated | CC-BY-SA-4.0 | Qwen1.5-72B labelling, GPT-4 as quality judge; upstream Alpaca/UltraChat/WizardLM/OpenHermes (C) | none stated |
| [LMSYS-Chat-1M](https://huggingface.co/datasets/lmsys/lmsys-chat-1m) | 1M convs, 25 models, Apr–Aug 2023 | custom: no redistribution, licensor may demand deletion "at any time" | GPT-4/Claude outputs (C) | D |
| [WildChat-1M](https://huggingface.co/datasets/allenai/WildChat-1M) / [WildChat-4.8M](https://huggingface.co/datasets/allenai/WildChat-4.8M) | 1M / 3,199,860 non-toxic convs through 2025-07-31 (incl. o1) | ODC-By | ChatGPT responses (C); **prompts are human and reusable** | — |
| [OASST2](https://huggingface.co/datasets/OpenAssistant/oasst2) | 135,174 msgs / 13,854 trees / 28 langs (EN 64,513) | Apache-2.0 | human | A |
| [Aya](https://huggingface.co/datasets/CohereLabs/aya_dataset) | 204K human pairs, 65 langs | Apache-2.0 | human | A |
| [No Robots](https://huggingface.co/datasets/HuggingFaceH4/no_robots) | 10K human | CC-BY-NC-4.0 | — | D |
| [Nemotron-Post-Training-v1](https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v1) | 25,659,642 (STEM 20.66M; math 2.04M; code 1.90M; chat 746,622; tool 310,051) | CC-BY-4.0 | DeepSeek-R1-0528 24.6M, Qwen3-235B 1.06M (A); some chat prompts must be re-fetched from LMSYS | legal review only |
| [Nemotron-Post-Training-v2](https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v2) | ~6.2M (chat 627,720; STEM 355K; math 239,467; code 175K; 5 languages ~1M each) | CC-BY-4.0 | DeepSeek-R1-0528, Qwen3-30B-A3B, Qwen3-235B, Qwen2.5 (A/Qwen-license note) | legal review only |
| [OpenMathInstruct-2](https://huggingface.co/datasets/nvidia/OpenMathInstruct-2) / [OpenCodeInstruct](https://huggingface.co/datasets/nvidia/OpenCodeInstruct) | 14M / 5M | CC-BY-4.0 | Llama-3.1-405B (B) / generator not on card [uncertain] | from GSM8K/MATH train |
| [self-oss-instruct-sc2](https://huggingface.co/datasets/bigcode/self-oss-instruct-sc2-exec-filter-50k) | 50.7K, execution-validated | ODC-By | StarCoder2 self-generated | A |
| [FLAN v2 (converted)](https://huggingface.co/datasets/ai2-adapt-dev/flan_v2_converted) | 89,982 | Apache-2.0 (FLAN) | templated human tasks | A |
| MetaMathQA (MIT), Evol-CodeAlpaca (Apache tag), NuminaMath-CoT (Apache) | 395K / 107K / 860K | — | GPT-3.5 / GPT-4-0314 / GPT-4o reformatting [uncertain] | C |

## 5. Tool-use sets (list only; detail in Angle 3)

xLAM-60k (CC-BY-4.0, gated, 3,673 APIs, execution-verified) · APIGen-MT-5k (**CC-BY-NC-4.0**, exclude) · ToolACE (Apache-2.0, 26,507 APIs) · Hermes-Function-Calling-v1 (Apache-2.0) · Glaive-FC-v2 (Apache-2.0) · [Toucan-1.5M](https://huggingface.co/datasets/Agent-Ark/Toucan-1.5M) (Apache-2.0; 495 real MCP servers / 2,000+ tools; Qwen3-32B, Kimi-K2, GPT-OSS-120B; keeps failed-tool traces for error handling) · [Nemotron-Agentic-v1](https://huggingface.co/datasets/nvidia/Nemotron-Agentic-v1) (CC-BY-4.0; 335,122 = 19,028 interactive + 316,094 tool-calling; Qwen3-235B-A22B-Thinking/Instruct-2507, Qwen3-32B, GPT-OSS-120B) · Nemotron-Post-Training-v1 tool_calling 310,051 · Dolci-Instruct-SFT-Tool-Use 227,579 (ODC-By; generator unstated) · SmolTalk2 smolagents traces 9,079 (DeepSeek-V3) + xlam_traces 59,962 · OpenMathReasoning TIR 1.7M (Python tool calls). Generators for Hermes-FC, Glaive, ToolACE, xLAM not confirmed from primary sources [uncertain].

## 6. Preference data

| Set | Size | License | Provenance |
|---|---|---|---|
| [UltraFeedback](https://huggingface.co/datasets/openbmb/UltraFeedback) / [binarized](https://huggingface.co/datasets/HuggingFaceH4/ultrafeedback_binarized) | 64K prompts / 256K completions / 380K feedback | MIT | GPT-4 judge; completions from GPT-4, GPT-3.5, Bard + Llama-2 family (C); **contains all 811 TruthfulQA and 2,339 FalseQA prompts** (contaminates TruthfulQA) |
| [HelpSteer2](https://huggingface.co/datasets/nvidia/HelpSteer2) | 20,324 train + 1,038 val | CC-BY-4.0 | human ratings; "10 different inhouse LLMs… none from proprietary LLM providers such as OpenAI"; ShareGPT prompts |
| [HelpSteer3](https://huggingface.co/datasets/nvidia/HelpSteer3) | Preference 40,476 (38,459/2,017); Feedback 40,821; Edit 14,461; Edit-Quality 3,274 | CC-BY-4.0 | 3–5 human annotators; ~20 permissively licensed LLMs, none OpenAI; prompts ShareGPT + WildChat-1M; 14 languages — **cleanest human preference set** (A) |
| [Tulu 3 8B pref mix](https://huggingface.co/datasets/allenai/llama-3.1-tulu-3-8b-preference-mixture) | 272,898 | ODC-By (some NC) | 24 generators incl. GPT-4 Turbo, GPT-4o, Claude 3.5 Sonnet; judge GPT-4o-2024-0806 (C) |
| [Dolci-Instruct-DPO](https://huggingface.co/datasets/allenai/Dolci-Instruct-DPO) | 260K (125K delta-learning, 125K "GPT-judge", 10K multiturn) | ODC-By | GPT judge (C) |
| SmolTalk2 Preference | 447K (230,501 no_think + 216,385 think) | Apache-2.0 | Qwen3-32B vs Qwen3-0.6B over Tulu 3 prompts (A) |
| [Skywork-Reward-80K-v0.2](https://huggingface.co/datasets/Skywork/Skywork-Reward-Preference-80K-v0.2) | 77,016 | **unspecified** | HelpSteer2, OffsetBias, WildGuard, Magpie-* (B); 4,957 RewardBench-overlapping pairs removed |
| [HH-RLHF](https://huggingface.co/datasets/Anthropic/hh-rlhf) | 160K | MIT | Anthropic 2022 model outputs; "not meant for supervised training" |
| PKU-SafeRLHF | — | CC-BY-NC-4.0 | D |

## 7. Safety / refusal

[Nemotron Content Safety v2 (Aegis 2.0)](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0): 33,416 (30,007/1,445/1,964), CC-BY-4.0, human-annotated, HH-RLHF prompts, open-model responses — **A**. [WildGuardMix](https://huggingface.co/datasets/allenai/wildguardmix): train 86,759 (48,783 prompt-only), test 1,725, 87% synthetic, GPT-4 prompts and labels, responses from GPT-3.5/OLMo/Vicuna/Llama3/Mistral/Dolphin ([paper §3.1](https://arxiv.org/html/2406.18495)) — ODC-By, gated, **C**. [WildJailbreak](https://huggingface.co/datasets/allenai/wildjailbreak): 262K = vanilla harmful 50,050 (GPT-4 prompts, GPT-3.5 refusals), vanilla benign 50,050, adversarial harmful 82,728 (Mixtral-8x7B + GPT-4), adversarial benign 78,706 (GPT-3.5) ([paper §4.1](https://arxiv.org/html/2406.18510)) — **C**. [OR-Bench](https://huggingface.co/datasets/bench-llm/or-bench) 80K/hard-1K/toxic, CC-BY-4.0 (generator unstated). [XSTest](https://huggingface.co/datasets/walledai/XSTest) CC-BY-4.0, eval only. Exclude: PKU-SafeRLHF, toxic-chat, FalseReject (all CC-BY-NC). Llama-Nemotron safety split 31,426 (Mixtral-8x22B, CC-BY-4.0) is an A-tier alternative.

## 8. Abstention / calibration (Angle 4 inputs)

| Resource | Size | License | Note |
|---|---|---|---|
| [CoCoNot](https://huggingface.co/datasets/allenai/coconot) | 12.5K train / 379 test / 927 pref | ODC-By | taxonomy: incomplete, unsupported, indeterminate, humanizing, unsafe; GPT-4 used (pref "stronger model"; generation of responses [uncertain]) |
| [KUQ](https://huggingface.co/datasets/amayuelas/KUQ) | <10K known-unknown Qs | MIT | A |
| [SelfAware](https://github.com/yinzhangyue/SelfAware) | 1,032 unanswerable + 2,337 answerable | data CC-BY-SA-4.0 | A |
| Idk datasets ([OpenMOSS](https://github.com/OpenMOSS/Say-I-Dont-Know)) | 4 model-specific sets from TriviaQA | not shown [uncertain] | recipe matters more than data |
| R-Tuning data ([repo](https://github.com/shizhediao/R-Tuning)) | 5 training sets (ParaRel…) via Google Drive | inherits sources | recipe |
| UMWP | 5,200 (half unanswerable) | CC-BY-SA-4.0 | A |
| [SQuAD 2.0](https://huggingface.co/datasets/rajpurkar/squad_v2) | >50K unanswerable | CC-BY-SA-4.0 | A, contextual abstention |
| [AbstentionBench](https://huggingface.co/datasets/facebook/AbstentionBench) | 20 datasets | **CC-BY-NC-4.0** | eval only |
| FalseQA / TruthfulQA (Apache) / SimpleQA (MIT) | — | — | FalseQA unlicensed; TruthfulQA leaked via UltraFeedback — hold out |
| QA pools for self-labelling | TriviaQA 95K (license "unknown", UW disclaims copyright), NQ (CC-BY-SA-3.0), HotpotQA 113K (CC-BY-SA-4.0), PopQA 14K (unspecified), SciQ (CC-BY-NC — exclude) | | probe ALICE-Next, label known/unknown by its own accuracy |

## 9. Contamination ledger (what to hold out or scrub)

Decontaminated upstream: FineMath (13-gram), Stack v2 (HumanEval/MBPP/APPS/GSM8K/DS-1000), Nemotron-CC-Math (MATH/GSM8K/MMLU/MMLU-Pro), Dolma 3, OLMo-2 FLAN, Tulu 3 SFT (8-gram), SmolTalk/SmolTalk2, OpenMathReasoning, Skywork v0.2. No statement: FineWeb-Edu, DCLM-baseline (analysis only), TxT360, Zyda-2, Nemotron-CC(-v2), Common Pile, OpenHermes, Infinity-Instruct, Dolci. Known leaks: UltraFeedback ⊃ TruthfulQA+FalseQA; NuminaMath-TIR 11.3% overlap with MATH; Evol-CodeAlpaca 3.5% with HumanEval; MMLU-EE site reported in DCLM [uncertain]. Rule for ALICE-Next: run our own 13-gram + embedding decontamination against every eval we will report (MMLU/-Pro, GSM8K, MATH, HumanEval+, MBPP+, IFEval, BFCL, τ-bench, TruthfulQA, SimpleQA, AbstentionBench, our receipt-tool suite) and log the removal counts in the receipt-chained data manifest.

## 10. Recommended pretraining + mid-training mix (Tier A only; 10B target, 3B floor at 0.3×)

Caveat: 3–10B tokens is far below ternary-parity scale (literature: ≥1B params, 100B+ tokens; our 30M twins cost +0.38 nats). Treat this budget as (a) a CIS-1-native pilot to validate the pipeline and (b) the annealing/mid-training stage on top of a longer run or a licensed ternary base. Filter all sources to ASCII-dominant documents before counting.

| Stage | Share | Source | 10B tokens |
|---|---|---|---|
| A stable (65%) | 32% | FineWeb-Edu int_score≥3 | 2.08B |
| | 18% | DCLM-baseline, top fastText decile | 1.17B |
| | 12% | Common Pile v0.1 (peS2o, Wikimedia, StackExchange, Gutenberg, OER, PEPs, USGPO) | 0.78B |
| | 15% | Stack-Edu (Python, Rust, C, Shell, SQL, JS/TS, Markdown) | 0.98B |
| | 8% | FineMath-3+ + InfiWebMath-3+ | 0.52B |
| | 8% | Cosmopedia v2 (Mixtral) | 0.52B |
| | 4% | TxT360 curated (StackExchange, HackerNews, Ubuntu IRC) | 0.26B |
| | 3% | Dolma wiki/wikibooks | 0.20B |
| B mid (28%) | 25% | FineWeb-Edu 4+ / DCLM top-7% | 0.70B |
| | 15% | FineMath-4+ + InfiWebMath-4+ | 0.42B |
| | 15% | Stack-Edu FIM-formatted, JSON/YAML-heavy files via Stack v2 SWHIDs | 0.42B |
| | 8% | OpenThoughts3 traces (QwQ) | 0.22B |
| | 8% | Tool-schema corpus: xLAM-60k, Glaive-FC-v2, Hermes-FC-v1, ToolACE, Toucan, Nemotron-Agentic rendered in ALICE's receipt/tool template | 0.22B |
| | 8% | In-house Wiki→RCQA / flashcard QA generated with a Tier-A teacher (Qwen3-235B, DeepSeek-V3, gpt-oss-120b) over CC-BY-SA Wikipedia | 0.22B |
| | 6% | FLAN v2 | 0.17B |
| | 5% | OpenMathReasoning TIR (Python tool calls) | 0.14B |
| | 5% | MegaMath web-pro (non-synthetic parts) | 0.14B |
| | 5% | self-oss-instruct-sc2 + OpenCodeInstruct sample (pending generator check) | 0.14B |
| C anneal (7%) | 25% | SmolTalk2 Qwen3-generated no_think subsets (systemchats, aya, multi-turn IF, everyday) | 0.18B |
| | 20% | Dolci tool-use + logic + verifiable-reasoning subsets (pending generator check) | 0.14B |
| | 20% | Toucan-1.5M + Nemotron-Agentic-v1 | 0.14B |
| | 10% | OASST2 EN + Aya EN (human) | 0.07B |
| | 10% | Abstention documents: self-generated known/unknown dialogues + SQuAD2-unanswerable, KUQ, SelfAware, UMWP | 0.07B |
| | 10% | FineMath-4+ / Stack-Edu Python top-up | 0.07B |
| | 5% | Self-authored CIS-1/receipt/CALC/LOOKUP protocol docs and failure-mode transcripts | 0.035B |

If Justin accepts the NVIDIA Data Agreement (training-only, non-redistributable), swap 5% of Stage B web for Nemotron-CC-Math-4+ (52B) and Nemotron Diverse QA; otherwise leave as above. Dolmino's Gemini traces (246M) and Tulu-3 SFT slice are excluded.

## 11. Recommended post-training mix (~1.6M examples; Tier A unless flagged)

| Block | Examples | Components |
|---|---|---|
| SFT general/IF | 400K | Nemotron-Post-Training-v2 chat 200K (non-LMSYS prompts); FLAN v2 60K; SmolTalk2 Qwen3 subsets (systemchats 27,436; multi-turn IF 28,217; aya 15,222; everyday 2,057); OASST2 EN ~20K; Aya EN 5K; Dolci Precise-IF 136,833 → cap 40K [flag: generator unverified] |
| SFT reasoning/math/code | 400K | OpenThoughts3 150K (math 100K/code 30K/science 20K); OpenMathReasoning CoT 60K + TIR 60K; Dolci verifiable-reasoning 50K + logic 30K [flag]; self-oss-instruct 50.7K |
| SFT tool expert | 350K | Toucan-1.5M 120K (multi-turn, parallel, failed-tool traces); Nemotron-Agentic-v1 80K (all 19,028 interactive); xLAM-60k 60K; Glaive-FC-v2 20K + Hermes-FC-v1 8,961; smolagents traces 9,079; **ALICE receipt-gateway traces 50K** generated by replaying prompts through the real CALC/LOOKUP gateway, keeping only hash-verified runs |
| SFT abstention/grounding | 100K | self-labelled Idk/R-Tuning pairs over TriviaQA/NQ/HotpotQA/PopQA 50K; SQuAD2-unanswerable 20K; KUQ 6K; SelfAware 3.4K; UMWP 5.2K; answerable look-alike contrast 15K (prevents over-refusal); CoCoNot 11K optional [flag C] |
| SFT safety | 50K | Aegis 2.0 30K; Llama-Nemotron safety (Mixtral) 20K; OR-Bench-80K subsample for over-refusal contrast |
| Preference | 250K | HelpSteer3 38,459 + Feedback/Edit 20K; HelpSteer2 20,324; SmolTalk2 pref 90K; on-policy ALICE-Next pairs judged by verifiers (tool result hash, CALC exactness, abstention correctness) 80K |
| RLVR prompts | 100K | Dolci RL-Zero math/code/IF (ODC-By, 13.3K each) + general 12,841; OpenMathReasoning problems 30K; Toucan tasks with execution reward 20K; abstention RL (reward = correct-when-known, abstain-when-unknown) 10K |

Variant deltas (replace within the abstention block, ~15% of SFT):
- **Air-gapped**: +30K "abstain with reason / cannot verify offline"; CALC-only tool traces; local-KB LOOKUP only; confidence-token calibration targets from self-probes.
- **Connected**: +50K "LOOKUP→cite→answer" and +20K "draft→LOOKUP verify→confirm or revise" traces generated with a Tier-A teacher and accepted only when the cited passage entails the answer; +20K grounded-vs-ungrounded DPO pairs (RAGTruth-style; RAGTruth license unverified, so generate in-house).

Excluded in both variants: OpenHermes-2.5, WildChat responses, Tulu persona sets, UltraFeedback, Tulu/Dolci DPO, LMSYS-Chat-1M, Infinity-Instruct, Magpie/Smol-Magpie-Ultra, OpenMathInstruct-2, No Robots, APIGen-MT-5k, PKU-SafeRLHF, FalseReject, AbstentionBench (eval only).

## 12. Decisions for Justin (file as NEEDS)

1. Tier B acceptance (Llama/Qwen2.5 synthetic → naming/attribution obligations). Recommendation: no.
2. NVIDIA Data Agreement sets (training-only, non-redistributable, "no open-source license" clause). Recommendation: no for the sovereignty proof.
3. Distillation teacher whitelist: Qwen3-235B-A22B (Apache-2.0), DeepSeek-V3/R1 (MIT), gpt-oss-120b (Apache-2.0), QwQ-32B (Apache-2.0), Mixtral (Apache-2.0), Olmo 3 (Apache-2.0). Every synthetic sample carries a generator field in the receipt-chained manifest.
4. CC-BY-SA pools (NQ, HotpotQA, SQuAD2, Wikipedia) for self-labelled abstention data — accept the share-alike ambiguity on weights, as Common Pile does.

## Key claims (as returned by the research agent, with sources)
- FineWeb-Edu is 1.3T tokens (educational score >=3) with a 5.4T-token score-2 variant, released under ODC-By v1.0 subject to Common Crawl Terms of Use, covering dumps CC-MAIN-2013-20 through CC-MAIN-2025-26; the card has no benchmark-decontamination statement.  
  <https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu>
- DCLM-baseline is 4T tokens / 3B documents under CC-BY-4.0; the DCLM paper's contamination check on MMLU moved accuracy 51.8->52.7 after removing flagged overlaps and the authors shipped decontamination tooling instead of a decontaminated pool.  
  <https://arxiv.org/html/2406.11794>
- Nemotron-CC-v2 / CC-Math-v1 / Pretraining-SFT-v1 are distributed under the NVIDIA Data Agreement for Model Training, which limits use to internal training, prohibits distributing the datasets and prohibits using them 'in any manner that would cause them to become subject to an open-source license' (trained models remain the company's property).  
  <https://scancode-licensedb.aboutcode.org/nvidia-model-training-2025.html>
- Tulu 3 SFT mixture has 939,344 samples; its persona subsets were generated with GPT-4o; decontamination used 8-gram matching with a >2% overlap rule and removed 11.3% of NuminaMath-TIR (MATH), 3.5% of Evol-CodeAlpaca (HumanEval) and 5.4% of WildChat GPT-4 (safety evals).  
  <https://arxiv.org/html/2411.15124>
- UltraFeedback (MIT) uses GPT-4 as annotator, includes GPT-4/GPT-3.5/Bard completions, and incorporates all 811 TruthfulQA and 2,339 FalseQA prompts, contaminating those evaluations.  
  <https://huggingface.co/datasets/openbmb/UltraFeedback>
- HelpSteer3 (CC-BY-4.0) has 40,476 preference samples (38,459 train / 2,017 val), 40,821 feedback, 14,461 edit and 3,274 edit-quality samples; responses come from ~20 commercially-permissively-licensed LLMs with none from OpenAI; each sample has 3-5 human annotators.  
  <https://huggingface.co/datasets/nvidia/HelpSteer3>
- Toucan-1.5M is Apache-2.0, >1.5M trajectories from 495 real MCP servers spanning 2,000+ tools, generated with Qwen3-32B, Kimi-K2 and GPT-OSS-120B.  
  <https://huggingface.co/datasets/Agent-Ark/Toucan-1.5M>
- Nemotron-Agentic-v1 is CC-BY-4.0 with 335,122 samples (19,028 interactive agent + 316,094 tool calling), generated with Qwen3-235B-A22B-Thinking-2507, Qwen3-32B, GPT-OSS-120B and Qwen3-235B-A22B-Instruct-2507.  
  <https://huggingface.co/datasets/nvidia/Nemotron-Agentic-v1>
- The Llama 3.1 Community License requires that if Llama outputs are used to train or improve another AI model, 'Llama' must appear at the beginning of that model's name and 'Built with Llama' must be displayed; a 700M-MAU threshold requires a separate Meta license.  
  <https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/LICENSE>
- Dolci-Instruct-SFT (Olmo 3, ODC-By) has 2,152,112 samples including 302,406 WildChat prompts with GPT-4.1 responses and 227,579 tool-use samples; Dolma 3 Mix is 5.93T tokens (Common Crawl 4.51T, olmOCR PDFs 805B, Stack-Edu 409B, FineMath-3+ 151B).  
  <https://huggingface.co/datasets/allenai/Dolci-Instruct-SFT>

## Gaps and unverified items (recorded, not papered over)
- Original Nemotron-CC (2024, hosted at data.commoncrawl.org): no explicit license statement found on the NVIDIA research page, NVIDIA blog, arXiv abstract or the Common Crawl index page; assumed to inherit Common Crawl Terms of Use.
- Generator models not confirmed from primary sources for: Dolci tool-use / logic / verifiable-reasoning / precise-IF subsets, OpenCodeInstruct, Glaive-FC-v2, Hermes-FC-v1, ToolACE, xLAM-60k (APIGen abstract names none), OR-Bench, CoCoNot training responses, Dolmino-1124 synthetic math (TinyGSM-MIND, MathCoder2), NuminaMath-CoT reformatting model.
- Licenses not stated or unresolved: OpenMOSS Idk datasets, R-Tuning data (Google Drive), PopQA, TriviaQA (HF 'unknown'; UW disclaims copyright), WebQuestions, Skywork-Reward-80K, Mixture-of-Thoughts card, RAGTruth mirror, FalseQA, argilla/magpie-ultra-v1.0.
- Meta's own Llama 3.1 license pages (llama.com -> developer.meta.com -> dev.meta.ai) returned redirects/login walls and the HF LICENSE file is gated; quotes were taken from the meta-llama/llama-models GitHub mirror.
- openai.com terms pages returned HTTP 403; the 'Use Output to develop models that compete with OpenAI' clause was quoted from a third-party mirror of the 2024-12-11 Terms of Use (Wind River license list).
- Olmo 3 paper (arXiv 2512.13961) HTML fetch covered only base-model sections; post-training (Dolci) teacher models and post-training decontamination thresholds were not read.
- Decontamination status of TxT360, Zyda-2, FineWeb-Edu, Nemotron-CC-v2, Common Pile, OpenHermes-2.5, Infinity-Instruct, Dolci is 'no statement on card'; absence of a statement was not independently tested.
- The MMLU Electrical-Engineering leak inside DCLM is reported only via a search-engine summary attributed to a 2025 paper; the Gaperon abstract fetched does not contain that specific claim.
- Common Pile v0.1 filtered total token count is not stated (only 8 TB raw and the Comma 1T/2T training budgets with repeats); Common Corpus English-only token count not stated.
- All token counts are in heterogeneous tokenizers (Llama-3 for FineWeb/DCLM, GPT-NeoX for Zyda-2, SmolLM2 for Stack-Edu, Mistral for Cosmopedia); ALICE's ASCII-pruned vocabulary and ASCII-only filtering will change effective budgets, so the 3B/10B tables are proportional targets, not measured counts.
- Aegis 2.0 response-generator model (Mistral-7B per Aegis 1.0) was not re-verified for v2; HelpSteer2 '10 inhouse LLMs' are unnamed on the card.
- SmolTalk2 'think' vs 'no_think' subset table was reproduced from the card but per-subset generator attribution was only partially given there; OpenThoughts3 source-prompt datasets and OpenHermes-2.5 source list were taken from cards without checking per-source licenses.
