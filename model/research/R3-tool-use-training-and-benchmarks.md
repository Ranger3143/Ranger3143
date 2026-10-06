> Research brief produced on 2026-10-06 by a web-research agent for the ALICE-Next model plan. Every claim carries the URL the agent read; items it could not verify are listed under Gaps. Numbers here are the cited papers' numbers, not Aefinity measurements.

# ANGLE 3 — Training ≤4B models to be tool experts (2025–2026)

Research brief for ALICE-Next · Aefinity AI · 2026-10-06. Numbers are quoted exactly from the cited source; `[uncertain]` marks anything not verified against a primary source.

## 1. Bottom line

1. **Single-turn function calling is solved at 1.5–3B; multi-turn is solved only once, at 3B; agentic (search/memory) is solved nowhere ≤4B.** On the official BFCL v4 board (CSV fetched 2026-10-06), 1.5B–3B specialists reach 83–88% Non-Live AST, 63–76% Live and 75–86% Irrelevance. Multi-turn ≥50% is reached by exactly one ≤4B model (xLAM-2-3b-fc-r, 58.38%, which beats GPT-5.2-FC's 28.12% and o3-FC's 14.75% on that column). Every ≤4B model scores ≤3.0% on Web Search and ≤17.6% on Memory.
2. **The data recipe that produced that one 3B result is small**: 60k verified single-turn samples (xlam-60k) + ~3.8k verified multi-turn trajectories (APIGen-MT) + irrelevance augmentation. Multi-turn competence came from thousands, not millions, of trajectories — but those trajectories were LLM-simulated with GPT-4o/DeepSeek-V3 and are CC-BY-NC.
3. **Abstention is cheap, calibration is not.** Even a 0.5B model (Hammer2.1-0.5b) hits 80.79% irrelevance detection; an untrained Qwen3-4B already scores 87.5% on the 240-entry BFCL v4 irrelevance set, so BFCL cannot discriminate abstention quality at this scale, and a refusing-everything model trivially maxes it (documented 97.5% irrelevance / 32.5% call-rate collapse). Pair any abstention metric with a must-call metric.
4. **RL with verifiable, decomposed rewards beats SFT at 1.5–3B on ~4k samples** (ToolRL: Qwen2.5-3B 41.97→52.98 BFCL v3; Qwen2.5-1.5B 46.20 RL vs 40.67 SFT). This is the cheapest lever available to a Kaggle-budget lab.
5. **BFCL v4's reweighting (Jul 2025) halved small-model headline scores** (Live 33→10%, Non-Live 33→10%, Multi-Turn 33→30%, Irrelevance 0→10%, Agentic 0→40%). Any 2025 "65% BFCL" claim for a 3B model is v3; the same model is ~41% on v4. Do not mix versions.

## 2. Official BFCL v4 leaderboard, ≤4B models (gorilla.cs.berkeley.edu/data_overall.csv, fetched 2026-10-06; 109 rows; newest dated entries are Dec 2025, so 2026 releases below appear only as vendor self-reports in §3)

| Rank | Model (mode) | Overall | Non-Live AST | Live | Multi-Turn | Irrelevance | Web Search | Memory | License |
|---|---|---|---|---|---|---|---|---|---|
| 42 | xLAM-2-3b-fc-r (FC) | 41.22 | 82.96 | 62.92 | **58.38** | 63.45 | 2.50 | 11.40 | cc-by-nc-4.0 |
| 54 | Qwen3-4B-Instruct-2507 (FC) | 35.68 | **87.88** | **76.39** | 22.12 | 84.93 | 3.00 | **17.63** | apache-2.0 |
| 56 | Arch-Agent-3B | 35.36 | 86.67 | 72.91 | 34.88 | 74.67 | 0.50 | 6.88 | katanemo-research |
| 60 | Arch-Agent-1.5B | 32.14 | 82.67 | 67.73 | 26.62 | 74.83 | 0.00 | 8.17 | katanemo-research |
| 65 | xLAM-2-1b-fc-r (FC) | 30.44 | 69.04 | 55.14 | 36.00 | 64.47 | 0.00 | 3.87 | cc-by-nc-4.0 |
| 68 | Hammer2.1-3b (FC) | 29.71 | 84.96 | 70.54 | 16.50 | **86.12** | 0.00 | 3.01 | qwen-research |
| 71 | Qwen3-1.7B (FC) | 28.41 | 82.92 | 74.61 | 11.00 | 76.54 | 2.50 | 6.02 | apache-2.0 |
| 75 | Hammer2.1-1.5b (FC) | 27.88 | 82.98 | 69.50 | 15.62 | 79.40 | 0.00 | 0.00 | cc-by-nc-4.0 |
| 86 | MiniCPM3-4B-FC (FC) | 25.55 | 81.75 | 65.21 | 3.88 | 72.84 | 0.00 | 12.04 | Apache-2.0 |
| 92 | Qwen3-0.6B (FC) | 23.93 | 71.79 | 56.62 | 3.62 | 80.84 | 1.00 | 8.60 | apache-2.0 |
| 98 | Llama-3.2-3B-Instruct (FC) | 21.95 | 82.67 | 58.33 | 4.00 | 52.06 | 1.00 | 6.24 | Llama 3 Community |
| 100 | Hammer2.1-0.5b (FC) | 21.22 | 65.98 | 54.63 | 2.88 | 80.79 | 0.00 | 1.08 | cc-by-nc-4.0 |
| 101 | Gemma-3-4b-it (Prompt) | 19.62 | 61.12 | 60.84 | 0.38 | 53.94 | 1.00 | 8.60 | gemma-terms |
| 103 | Granite-4.0-350m (FC) | 18.98 | 67.92 | 46.11 | 2.50 | 60.84 | 0.50 | 3.23 | Apache-2.0 |
| 107 | Llama-3.2-1B-Instruct (FC) | 10.82 | 38.38 | 11.77 | 0.00 | 51.57 | 0.00 | 3.23 | Llama 3 Community |
| 109 | Gemma-3-1b-it (Prompt) | 7.17 | 20.21 | 11.84 | 0.00 | 33.18 | 0.00 | 3.23 | gemma-terms |
| *ref* | Claude-Opus-4-5 (FC) #1 | 77.47 | 88.58 | 79.79 | 68.38 | 84.72 | 84.50 | 73.76 | proprietary |
| *ref* | GPT-5.2-2025-12-11 (FC) | 55.87 | 81.85 | 70.39 | 28.12 | 79.42 | 75.50 | 45.81 | proprietary |
| *ref* | xLAM-2-8b-fc-r (FC) | 46.68 | 84.58 | 67.95 | 70.00 | 63.28 | 6.50 | 13.98 | cc-by-nc-4.0 |
| *ref* | Qwen3-8B (FC) | 42.57 | 87.58 | 80.53 | 41.75 | 79.07 | 12.00 | 14.62 | apache-2.0 |
| *ref* | ToolACE-2-8B (FC) | 42.44 | 87.10 | 77.42 | 38.38 | 90.79 | 8.50 | 18.49 | Apache-2.0 |
| *ref* | Hammer2.1-7b (FC) | 31.67 | 85.50 | 69.50 | 23.87 | 90.12 | 0.00 | 0.00 | cc-by-nc-4.0 |

Reading: xLAM-2-3b's multi-turn breakdown is Base 71.50 / Miss-Func 59.00 / Miss-Param 57.50 / Long-Context 45.50 — i.e. it recovers from missing tools and asks for missing parameters at a rate no other ≤8B open model matches. Hammer2.1 (single-turn data only) is the mirror image: top-tier irrelevance (86.12 at 3B) with 16.50 multi-turn. Not on the board: SmolLM3, Phi-4-mini, Granite-4.0 micro/h-micro/1B, Nemotron Nano 4B, LFM2/2.5, FunctionGemma, Qwen3.5, Gemma 4.

## 3. Vendor- or paper-reported numbers (not on the official v4 board; versions differ)

| Model | Params | Source / date | Metric | Value | License |
|---|---|---|---|---|---|
| Qwen3-4B / 1.7B / 0.6B (thinking) | 4B/1.7B/0.6B | Qwen3 tech report, May 2025 | BFCL v3 | 65.9 / 56.6 / 46.4 | Apache-2.0 |
| Qwen3-4B / 1.7B / 0.6B (non-thinking) | | same | BFCL v3 | 57.6 / 52.2 / 44.1 (Qwen2.5-3B-Instruct 50.4) | Apache-2.0 |
| Qwen3-4B-Instruct-2507 | 4.0B | HF card, Jul 2025 | BFCL-v3; TAU1-Retail/Airline; TAU2-Retail/Airline/Telecom | 61.9; 48.7/32.0; 40.4/24.0/13.2 | Apache-2.0 |
| xLAM-2-3b-fc-r / 1b-fc-r | 3B/1B | APIGen-MT paper, Apr 2025 | BFCL v3 overall / multi-turn / relevance; τ-bench overall | 65.11/56.00/94.44, τ 38.2 · 58.90/43.12/88.89, τ 21.8 | CC-BY-NC-4.0 |
| Arch-Function-3B / 1.5B / 7B | | HF card, board as of 2024-10-21 (v3) | BFCL overall / multi-turn / irrelevance | 57.69/17.50/72.88 · 56.20/15.88/74.39 · 59.62/21.00/73.63 | katanemo-research |
| Hammer-1.5B / 4B / 7B (v1) | | Hammer paper, Oct 2024 (v2-era BFCL) | overall / irrelevance / relevance | 73.04/72.18/92.68 · 76.05/68.66/90.24 · 83.92/72.87/92.68 | — |
| Granite-4.0-Micro / H-Micro / H-Tiny / H-Small | 3B dense / 3B dense / 7B-A1B / 32B-A9B | IBM card, 2025-10-02 | BFCL v3 | 59.98 / 57.56 / 57.65 / 64.69 | Apache-2.0 |
| NVIDIA-Nemotron-3-Nano-4B | 3.97B | HF card, release 2026-03-16 | BFCL v3; Tau2 Airline/Retail/Telecom | 61.1; 28.0/34.8/24.9 (33.3/39.8/33 reasoning table) | NVIDIA Open Model License |
| Qwen3.5-4B / 9B | 4B dense (GatedDeltaNet+gated attn) | HF card, 2026 [date uncertain] | BFCL-V4; TAU2-Bench | 50.3 / 66.1; 79.9 / 79.1 | Apache-2.0 |
| LFM2.5-2.6B | 2.6B, 34T pretrain tokens, <2.5 GB | Liquid blog, 2026-08-04 | BFCLv4; ToolSandbox (Liquid's own runs; Gemma-4-E4B 46.39/65.00, Qwen3.5-4B 50.56/75.55) | 56.88; 77.83 | open-weight, LFM licence [terms uncertain] |
| FunctionGemma-270M-it | 270M | Google card, Dec 2025 | BFCL Simple; Parallel-Multiple; Mobile Actions before→after task fine-tune | 61.6; 29.5; 58→85 | Gemma |
| Phi-4-Mini | 3.8B | tech report, Mar 2025 | "BFCL" (version not stated) vs Llama-3.2-3B 78.6, Qwen2.5-3B 74.2 | 70.3 | MIT |
| SmolLM3-3B | 3B, 11.2T tokens | HF card, Jul 2025 | "BFCL" row, split not stated (Qwen3-4B 95.0, Qwen3-1.7B 89.5) [uncertain: likely a non-live subset] | 92.3 no-think / 88.8 think | Apache-2.0 |
| ToolRL (Qwen2.5-1.5B / 3B / 7B, Llama-3.2-3B) | | arXiv 2504.13958, Apr 2025 | BFCL v3 overall, GRPO cold-start | 46.20 (SFT 40.67) / 52.98 (base 41.97) / 58.38 / 44.10 | — |
| Toucan-tuned Qwen2.5-7B (smallest trained) | 7B | arXiv 2510.01179, Oct 2025 | BFCL v3 overall/MT base→tuned; τ-bench | 55.10→58.26, 72.32→74.50; 22.48 (+7.45) | Apache-2.0 data |

## 4. Smallest model class that is "reliable", and what it took

Define reliable as (a) ≥80 Non-Live AST, ≥65 Live, ≥75 Irrelevance on BFCL v4, and (b) ≥50 Multi-Turn.

- **(a) is met from 1.5B** with ~70k single-turn samples: Hammer2.1-1.5b (82.98/69.50/79.40) trained on xlam-60k + xlam-irrelevance-7.5k over Qwen2.5-Coder; Arch-Agent-1.5B (82.67/67.73/74.83); generalist Qwen3-1.7B (82.92/74.61/76.54) with no tool-specific SFT beyond Qwen's post-training. Sub-1B does not meet it (Hammer2.1-0.5b 65.98 Non-Live; Qwen3-0.6B 71.79; Granite-4.0-350m 67.92), though 0.5B already abstains well (80.79).
- **(b) is met at 3B by one model.** xLAM-2-3b-fc-r (Qwen2.5-3B base): xlam-60k + APIGen-MT (3,820 validated trajectories, avg 7 tool calls and 6 user turns each; blueprint success 70% with agentic feedback vs 28% without; trajectory simulation success 67%), full fine-tune ≤3 epochs, bf16, DeepSpeed ZeRO-3 on H200. The 1B sibling gets 36.00 — the 1B→3B step is worth +22 multi-turn points on identical data. Qwen3-4B-Instruct-2507 (22.12) and Arch-Agent-3B (34.88) show 3–4B generalists do not get there without trajectory data.
- **Token budget is tiny relative to pretraining.** 119.3k Toucan SFT instances at 32k max length, or 67.5k Hammer samples, are O(10^8) tokens — ≤0.1% of a 100B-token ternary pretraining run. The expensive part is the base model's instruction-following/reasoning; the tool skill itself is a cheap post-training layer. FunctionGemma's 270M "58→85 after task-specific fine-tune" shows per-domain fine-tuning is mandatory below ~1B.
- **Agentic categories are the wall.** Best ≤4B Web Search is 3.00 (Qwen3-4B-2507); best Memory 17.63. Even xLAM-2-32b reaches only 25.50/20.86. No published ≤4B recipe for search-and-verify behaviour exists; LFM2.5-2.6B's 56.88 v4 self-report would require strong agentic scores and is unverified [uncertain].

## 5. Datasets (sizes and licences from the Hub cards; dates from papers)

| Dataset | Size | Licence | Date | Notes |
|---|---|---|---|---|
| Salesforce/xlam-function-calling-60k (APIGen) | 60,000 | CC-BY-4.0 | Jun 2024 | 3,673 executable APIs, 21 categories; generated by DeepSeek-V2-Chat (33,659) + Mixtral-8x22B; 3-stage verification; >95% human-rated correct; includes parallel calls |
| MadeAgents/xlam-irrelevance-7.5k | 7,500 | CC-BY-4.0 | Oct 2024 | 7.5k xlam-60k samples with the ground-truth tool removed, label = empty list |
| Salesforce/APIGen-MT-5k | 5,000 trajectories (3,820 validated in paper) | CC-BY-NC-4.0 + "generated with GPT-4 … not to develop models that compete with OpenAI" | Apr 2025 | retail+airline (τ-bench domains); ShareGPT-style; GPT-4o + DeepSeek-V3 simulators |
| Team-ACE/ToolACE | 11,300 dialogs | Apache-2.0 | Sep 2024 | 26,507 synthesized APIs; self-evolution + multi-agent; dual-layer verification |
| glaiveai/glaive-function-calling-v2 | 112,960 | Apache-2.0 | 2023 | `<functioncall>` / `FUNCTION RESPONSE` format; contains declines; mostly single sequential calls |
| NousResearch/hermes-function-calling-v1 | ≈11.6k (1.89k+1.89k+5.21k+1.34k+1.24k) | Apache-2.0 | 2024-08-14 | `<tools>` in system, `<tool_call>` XML; JSON-mode subsets. **No v2 exists on the Hub** |
| internlm/Agent-FLAN | 7 splits, 219 MB; counts not shown [uncertain] | Apache-2.0 | Mar 2024 | separates format from reasoning; negative samples against hallucinated calls |
| OpenBMB/ToolBench (ToolLLM) | 126,486 instances, 16,464 APIs, 469,585 calls | Apache-2.0 | Jul 2023 | DFSDT traces; RapidAPI dependence (StableToolBench fixes) |
| Agent-Ark/Toucan-1.5M | 1,646,546 instances | Apache-2.0 | Oct 2025 | 495 real MCP servers, 2,000+ tools; teachers Qwen3-32B, Kimi-K2, GPT-OSS-120B; Hermes format; irrelevance via server-shuffle (40k in SFT mix); curated 119.3k SFT subset |
| nvidia/When2Call | 15k SFT + 9k preference train; 3,652 MCQ + 300 judge test | CC-BY-4.0 | NAACL 2025 | 4-way label: direct answer / tool call / ask / cannot — the only public "know when you don't know" tool dataset |
| ToolRL mix | 4,000 (2k ToolACE, 1k Hammer-masked, 1k xLAM) | inherits | Apr 2025 | RL prompts, not SFT targets |
| Tool-N1 | 5,518 distilled reasoning trajectories + xLAM/ToolACE | — | Apr 2025 | 7B/14B only |
| MCP-oriented evals: MCP-Bench (28 servers/250 tools), MCP-Universe (6 domains/11 servers), MCPMark (127 tasks), MCPToolBench++ (4k+ servers) | — | — | Aug–Sep 2025 | see §8 |

## 6. Formats

- **Hermes/Qwen JSON-in-XML**: tool schemas as JSON in the system prompt, `<tool_call>{"name":…,"arguments":…}</tool_call>`, results as `tool` role (Qwen docs call it Hermes-style). Used by Qwen2.5/3, Granite 4.0 (`<tool_call>` + OpenAI schema), Arch-Function's prompt, Toucan, SmolLM3 "XML tools". De-facto open standard; easiest for a greedy ASCII-only decoder because the grammar is plain JSON.
- **Llama 3.2 pythonic**: `[get_weather(city="SF"), …]`, definitions in system or user message, results via `ipython` role, `<|python_tag|>` for code; 1B/3B emit pythonic only. Compact but needs a Python-expression parser.
- **OpenAI tools schema** (`{"type":"function","function":{name,description,parameters}}`) is the interchange format every card above accepts.
- **MCP** (spec 2025-06-18): `tools/list` → `{name,title,description,inputSchema,outputSchema?,annotations}`; `tools/call` → `{content[], structuredContent?, isError}`; servers MUST validate inputs, clients SHOULD show inputs before calling. Maps 1:1 onto a receipt-gated gateway: hash `inputSchema`, arguments and `structuredContent` into the chain.
- **Special-token formats**: LFM2 `<|tool_list_start|>/<|tool_call_start|>/<|tool_response_start|>`; FunctionGemma `<start_function_call>call:fn{k:<escape>v<escape>}<end_function_call>`; Nemotron 3 XML-style tags "to reduce escaping" [from blog summary, uncertain]. Special tokens cost vocabulary slots but remove JSON-escaping failures — relevant to a 50,256-token pruned ASCII vocab.
- **Arch-Function-Chat 3-way JSON**: `{"response":…}` | `{"required_functions":[…],"clarification":…}` | `{"tool_calls":[…]}` — a clean template for an abstain/ask/act head.

## 7. Training tricks with measured effect

1. **Assistant-only loss.** TRL `assistant_only_loss=True` computes loss "only on the assistant responses, ignoring user or system messages" (tool-role turns are therefore masked); requires `{% generation %}` tags in the chat template. Standard in every recipe above.
2. **Function masking (Hammer).** Replace function and parameter names with random strings, randomise defaults into descriptions, relabel; ablated at 0/33/50/67% masking, best ≈33–50%; irrelevance share ≈10% optimal. Result: generalisation across API-Bank, Tool-Alpaca, Nexus Raven, Seal-Tools (Hammer-7B 93.48/82.31/92.46/97.44 func-name F1).
3. **Irrelevance / abstention data.** xlam-irrelevance-7.5k (drop the GT tool), Toucan server-shuffle, When2Call 4-way. Cautionary evidence (qwen3-4b-tools-v1, bfcl-eval 2026.3.23): base Qwen3-4B 87.50 → LoRA 89.17 on the 240-entry irrelevance set (4 entries), while an alternate seed hit 97.50 by calling tools on only 32.5% of "Multiple" entries; adding APIGen positive-heavy data cost −17.1 points on hard negatives. Use a harmonic-mean "balanced" score and hard negatives (tool-shaped prompts that must be declined).
4. **Verified multi-turn trajectories (APIGen-MT).** Blueprint → committee review → simulated human-agent interplay → execution-checked, best-of-N for the simulated user. 3,820 trajectories moved a 3B from ~17 to 58 multi-turn on v4. Response-based grading in BFCL v3 is subset-match, so error-recovery trajectories count as correct.
5. **RL with decomposed verifiable rewards (ToolRL/GRPO).** Format reward 0/1 + correctness −3..3 split into tool-name, parameter-name, parameter-value matching; dynamic shift from format to correctness; length reward hurts. +17% over base, +15% over SFT on average; works at 1.5B/3B on 4k prompts. Tool-N1 (binary reward, 7B/14B): pure RL ≥ SFT-then-RL.
6. **Strong-to-weak distillation (Qwen3).** Off-policy teacher outputs in /think and /no_think, then on-policy logit-KL to Qwen3-32B/235B-A22B; "1/10 of the GPU hours" of the 4-stage pipeline. Explains why 1.7B/4B generalists already reach 83–88 Non-Live with no tool-specific SFT.
7. **Synthetic closed loops.** Toucan (3 teachers, 2 agent frameworks, rule+model validation) and "Close the Loop" (user-simulator / assistant / MCP-server role-play; a 32B went 19.8→70.9 BFCL on synthetic data alone). Both start ≥7B; untested ≤4B.

## 8. Evaluation suites

| Suite | Date | What it measures | Scale / headline |
|---|---|---|---|
| BFCL v3 → v4 | 2024-09-19 → 2025-07-17 | Non-Live 1,390; Live 2,251; Multi-Turn 800 (base/miss-func/miss-param/long-context 200 each) + Web Search 200 (duckduckgo_search/fetch_url_content, exact-match answer) + Memory 465 (KV/vector/recursive-summarisation 155 each) + Format Sensitivity 26 configs × 200 | v4 weights Agentic 40 / MT 30 / Live 10 / Non-Live 10 / Irrelevance 10 |
| τ-bench / τ²-bench | 2024-06-17 / 2025-06-09 | retail, airline; τ² adds telecom dual-control (user also acts); pass^k reliability | gpt-4o <50% tasks, pass^8 <25% retail (2024) |
| ToolSandbox (Apple) | 2024-08-08 | stateful, implicit dependencies, user simulator; "insufficient information" scenarios | large open/proprietary gap |
| NESTFUL (IBM) | 2024-09-04 | 1,800+ executable nested sequences (output→input) | GPT-4o 28% full-sequence match |
| API-Bank | 2023-04-14 | 73 APIs, 314 dialogues, 753 calls; Call / Retrieve+Call / Plan+Retrieve+Call | legacy, still used by Hammer/ToolRL |
| ACEBench | 2025-01-22 | Normal / Special (ambiguous or incomplete instructions) / Agent | no live APIs |
| MCP-Bench | 2025-08-28 | 28 servers, 250 tools; schema use, planning, completion | 20 LLMs |
| MCP-Universe | 2025-08-20 | 6 domains, 11 servers; execution-based | GPT-5 43.72, Grok-4 33.33, Claude-4-Sonnet 29.44 |
| MCPMark | 2025-09-28 | 127 CRUD tasks; 16.2 turns / 17.4 calls per task | gpt-5-medium 52.56 pass@1, 33.86 pass^4 |
| When2Call | NAACL 2025 | 3,652 MCQ + 300 judge; call / ask / cannot / answer | abstention-specific |

## 9. Implications for ALICE-Next

- **Target the proven 3B recipe, not a bigger model.** Everything in §4(a)–(b) is standard-transformer, i8-friendly post-training on a Qwen2.5-class base; nothing requires architecture changes incompatible with CIS-1 (RMSNorm/RoPE/GQA/SwiGLU). The ternary question is orthogonal: tool-SFT tokens are <0.1% of pretraining, so a BitNet-b1.58-2B-4T (MIT) continued with Hammer-style SFT + ToolRL is the cheapest credible path to §4(a), and the only open question is whether a 2.4B ternary base retains enough reasoning for §4(b).
- **Air-gapped variant = Hammer-style single-turn + When2Call 4-way head + hard negatives; connected variant = APIGen-MT-style verified trajectories whose "tools" are the receipt-gated LOOKUP/CALC gateway.** Nobody has published ≤4B web-search/memory numbers above 3/18%; a receipt-replayable search-and-verify trajectory set would be new.
- **Provenance/licensing if distillation is reopened.** Clean for a commercial, attributable model: xlam-60k + xlam-irrelevance (CC-BY-4.0, DeepSeek/Mixtral-generated), ToolACE/Glaive/Hermes-v1/ToolBench/Toucan (Apache-2.0; Toucan teachers Qwen3-32B Apache-2.0, GPT-OSS-120B Apache-2.0, Kimi-K2 modified-MIT), When2Call (CC-BY-4.0). **Not usable** for a commercial model: APIGen-MT-5k and all xLAM-2 weights (CC-BY-NC-4.0 + OpenAI non-compete clause) — so the one public ≤4B multi-turn success is not reusable; its *pipeline* is (paper is open). Using Qwen3 as a logit teacher is licence-clean (Apache-2.0) but ends the "no external teacher" sovereignty claim; using a Hammer/xLAM checkpoint as a starting point does not (NC / qwen-research).
- **Compute.** ToolRL-scale GRPO (4k prompts, 1.5–3B) and 70k-sample SFT are within a few rented GPU-days; APIGen-MT-style trajectory synthesis is dominated by simulator LLM calls, not GPU.

## 10. Sources

Official BFCL CSV https://gorilla.cs.berkeley.edu/data_overall.csv · CHANGELOG https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/CHANGELOG.md · v3 blog https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html · v4 blog https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html · APIGen-MT https://arxiv.org/abs/2504.03601 · xLAM-2-1b https://huggingface.co/Salesforce/xLAM-2-1b-fc-r · APIGen-MT-5k https://huggingface.co/datasets/Salesforce/APIGen-MT-5k · xlam-60k https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k · Hammer paper https://arxiv.org/abs/2410.04587 · Hammer2.1-1.5b https://huggingface.co/MadeAgents/Hammer2.1-1.5b · xlam-irrelevance https://huggingface.co/datasets/MadeAgents/xlam-irrelevance-7.5k · Arch-Function-3B https://huggingface.co/katanemo/Arch-Function-3B · Qwen3 report https://arxiv.org/abs/2505.09388 · Qwen3-4B-2507 https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507 · Qwen3.5-4B https://huggingface.co/Qwen/Qwen3.5-4B · Granite 4.0 https://huggingface.co/ibm-granite/granite-4.0-h-micro · Granite Nano https://huggingface.co/ibm-granite/granite-4.0-h-1b · Nemotron 3 Nano 4B https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16 · LFM2.5 https://www.liquid.ai/blog/lfm2-5-2-6b · LFM2-1.2B-Tool https://huggingface.co/LiquidAI/LFM2-1.2B-Tool · FunctionGemma https://huggingface.co/google/functiongemma-270m-it · SmolLM3 https://huggingface.co/HuggingFaceTB/SmolLM3-3B · Phi-4-Mini https://arxiv.org/abs/2503.01743 · ToolACE https://arxiv.org/abs/2409.00920, https://huggingface.co/datasets/Team-ACE/ToolACE · Glaive https://huggingface.co/datasets/glaiveai/glaive-function-calling-v2 · Hermes v1 https://huggingface.co/datasets/NousResearch/hermes-function-calling-v1 · Agent-FLAN https://huggingface.co/datasets/internlm/Agent-FLAN · ToolBench https://github.com/OpenBMB/ToolBench · Toucan https://arxiv.org/abs/2510.01179, https://huggingface.co/datasets/Agent-Ark/Toucan-1.5M · When2Call https://huggingface.co/datasets/nvidia/When2Call · ToolRL https://arxiv.org/abs/2504.13958 · Tool-N1 https://arxiv.org/abs/2505.00024 · Close the Loop https://arxiv.org/abs/2512.23611 · qwen3-4b-tools-v1 https://huggingface.co/AbhijitK20/qwen3-4b-tools-v1 · TRL SFT https://huggingface.co/docs/trl/sft_trainer · Llama 3.2 format https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/text_prompt_format.md · Qwen function calling https://qwen.readthedocs.io/en/latest/framework/function_call.html · MCP tools spec https://modelcontextprotocol.io/specification/2025-06-18/server/tools · τ-bench https://arxiv.org/abs/2406.12045 · τ²-bench https://arxiv.org/abs/2506.07982 · ToolSandbox https://arxiv.org/abs/2408.04682 · NESTFUL https://arxiv.org/abs/2409.03797 · API-Bank https://arxiv.org/abs/2304.08244 · ACEBench https://arxiv.org/abs/2501.12851 · MCP-Bench https://arxiv.org/abs/2508.20453 · MCP-Universe https://arxiv.org/abs/2508.14704 · MCPMark https://arxiv.org/abs/2509.24002 · MCPToolBench++ https://arxiv.org/abs/2508.07575 · TinyLLM https://arxiv.org/abs/2511.22138 · Gemma 4 card https://ai.google.dev/gemma/docs/core/model_card_4

## Key claims (as returned by the research agent, with sources)
- On the official BFCL v4 leaderboard CSV (fetched 2026-10-06, 109 rows), xLAM-2-3b-fc-r (FC) scores 41.22 overall with 58.38 Multi-Turn, 82.96 Non-Live AST, 62.92 Live, 63.45 Irrelevance, 2.50 Web Search and 11.40 Memory; it is the only model ≤4B with Multi-Turn ≥50, and its Multi-Turn exceeds GPT-5.2-2025-12-11 (FC) at 28.12.  
  <https://gorilla.cs.berkeley.edu/data_overall.csv>
- On the same CSV, Hammer2.1-3b (FC) scores 29.71 overall / 84.96 Non-Live / 70.54 Live / 16.50 Multi-Turn / 86.12 Irrelevance; Hammer2.1-1.5b 27.88 / 82.98 / 69.50 / 15.62 / 79.40; Hammer2.1-0.5b 21.22 / 65.98 / 54.63 / 2.88 / 80.79; Qwen3-4B-Instruct-2507 (FC) 35.68 / 87.88 / 76.39 / 22.12 / 84.93 with 3.00 Web Search and 17.63 Memory.  
  <https://gorilla.cs.berkeley.edu/data_overall.csv>
- BFCL V4 (released 2025-07-17) reweighted the overall score to Agentic 40%, Multi-Turn 30%, Live 10%, Non-Live 10%, Irrelevance/Hallucination 10% (from Live 33 / Non-Live 33 / Multi-Turn 33 / Irrelevance 0 in V3, released 2024-09-19); Web Search has 200 entries and Memory 465 (155 each for KV, vector, recursive summarization).  
  <https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/CHANGELOG.md>
- APIGen-MT (arXiv 2504.03601, Apr 2025) reports BFCL v3 overall/multi-turn/relevance of 65.11/56.00/94.44 for xLAM-2-3b-fc-r and 58.90/43.12/88.89 for xLAM-2-1b-fc-r, τ-bench overall 38.2 and 21.8, trained on 3,820 validated multi-turn trajectories (avg 7 tool calls, 6 user turns) plus xlam-60k, ≤3 epochs full fine-tune; xLAM-2 weights and APIGen-MT-5k are CC-BY-NC-4.0 with an OpenAI non-compete clause.  
  <https://arxiv.org/html/2504.03601v2>
- Salesforce/xlam-function-calling-60k has 60,000 examples over 3,673 executable APIs in 21 categories, licence CC-BY-4.0, generated with DeepSeek-V2-Chat and Mixtral-8x22B; MadeAgents/xlam-irrelevance-7.5k is 7,500 samples with the ground-truth tool removed, licence CC-BY-4.0.  
  <https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k>
- ToolRL (arXiv 2504.13958, Apr 2025) trains with GRPO on 4,000 prompts (2k ToolACE, 1k Hammer-masked, 1k xLAM) using a 0/1 format reward plus a −3..3 correctness reward decomposed into tool-name, parameter-name and parameter-value matching, and reports BFCL v3 overall of 52.98 for Qwen2.5-3B (base 41.97) and 46.20 for Qwen2.5-1.5B (SFT 40.67).  
  <https://arxiv.org/html/2504.13958>
- Toucan-1.5M contains 1,646,546 instances from 495 real MCP servers and 2,000+ tools, licence Apache-2.0, generated with Qwen3-32B, Kimi-K2 and GPT-OSS-120B; the smallest model fine-tuned in the paper is Qwen2.5-7B, which improved BFCL v3 overall from 55.10 to 58.26 using a 119.3k-instance SFT subset (lr 2e-5, 2 epochs, Hermes template).  
  <https://arxiv.org/html/2510.01179v1>
- Qwen3 technical report (May 2025) gives BFCL v3 of 65.9 / 56.6 / 46.4 (thinking) and 57.6 / 52.2 / 44.1 (non-thinking) for Qwen3-4B / 1.7B / 0.6B, pretraining on 36T tokens, and small models trained by strong-to-weak distillation (off-policy then on-policy logit KL to Qwen3-32B or Qwen3-235B-A22B) at about 1/10 of the GPU hours of the four-stage pipeline.  
  <https://arxiv.org/html/2505.09388>
- IBM Granite-4.0-Micro (3B dense) and Granite-4.0-H-Micro (3B dense), released 2025-10-02 under Apache-2.0, report BFCL v3 of 59.98 and 57.56; NVIDIA-Nemotron-3-Nano-4B-BF16 (3.97B, released 2026-03-16, NVIDIA Nemotron Open Model License) reports BFCL v3 61.1.  
  <https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16>
- The qwen3-4b-tools-v1 model card (bfcl-eval 2026.3.23) shows untrained Qwen3-4B at 87.50% on the full 240-entry BFCL v4 Irrelevance category, the LoRA at 89.17%, and a second seed at 97.50% irrelevance while emitting tool calls on only 32.5% of BFCL Multiple entries (12.50% AST) — i.e. the irrelevance metric saturates and is gameable by refusal.  
  <https://huggingface.co/AbhijitK20/qwen3-4b-tools-v1>

## Gaps and unverified items (recorded, not papered over)
- Hammer 2.1 model cards publish their BFCL-v3 table only as an image; v3 numbers for Hammer2.1-0.5b/1.5b/3b could not be read. Official v4 numbers were used instead.
- Granite 4.0 Nano (H-1B ~1.5B, 350M) BFCLv3 numbers appear only in chart images on the IBM blog; not extracted. Only Granite-4.0-350m is on the official v4 board (18.98).
- SmolLM3-3B's model-card 'BFCL' value (92.3 no-think / 88.8 think; Qwen3-4B 95.0) does not state the BFCL version or split; it is far above any official overall score and is presumably a non-live subset — treated as [uncertain].
- Phi-4-Mini technical report gives BFCL 70.3 (Llama-3.2-3B 78.6, Qwen2.5-3B 74.2) without stating the BFCL version.
- The official BFCL CSV's newest dated entries are Dec 2025 (GPT-5.2, Claude Opus 4.5); 2026 small models (Qwen3.5-4B 50.3, LFM2.5-2.6B 56.88, Gemma-4-E4B 46.39, Nemotron-3-Nano-4B v3 61.1) are vendor self-reports only and could not be cross-checked on the official board. Third-party aggregator llm-stats.com listed additional 2026 entries (e.g., 'Qwen3.7 Max 75.0', 'Granite 4.2 3B 0.524') that were not verified against any primary source and were excluded.
- Gemma 4 release date conflicts between sources (third-party: 2026-04-02; model-card page: 2026-07-30, possibly a later 12B addition); no BFCL/τ-bench numbers for E2B/E4B are on Google's model card.
- Qwen3.5-4B release date not shown on the model card; LFM2-1.2B-Tool release date and the exact terms of the LFM licence were not verified (card lists 'LFM1.0' and a 'proprietary benchmark' only).
- No public 'Hermes function-calling v2' dataset exists on the Hub (only v1, 2024-08-14); Agent-FLAN per-split example counts are not displayed (viewer error).
- FunctionGemma-270M card is gated; its BFCL Simple 61.6 / Parallel-Multiple 29.5 and Mobile Actions 58→85 come from a WebFetch summary whose stated release date (2024) was wrong — release is Dec 2025 per Google announcements; the numbers themselves were not re-verified from the raw card.
- Meta's Llama 3.2 prompt-format page requires login; the pythonic format description is taken from the llama-models GitHub repo instead.
- Nemotron 3 Nano post-training data sizes (13M samples, 900k RL tasks) and the 'XML-style special tags' tool format come from a search summary of NVIDIA's blog, not read directly.
- No published training recipe or benchmark number exists for a ≤4B model on BFCL v4 Web Search above 3.00 or Memory above 17.63; the connected/fact-checking variant of ALICE-Next has no prior art to calibrate against.
- TinyLLM (arXiv 2511.22138) table values (xLAM-2-3b 65.74, Qwen3-4B Prompt 62.04, etc.) do not state the BFCL version and do not match either v3 paper numbers or the current v4 CSV; omitted from the main tables.
