# R0 — Verification pass over the research briefs (what an adversarial second agent found)

> For each key claim in briefs R1–R4 an independent verifier agent re-fetched the primary source and returned a verdict (refuted or not) with a corrected statement. Verifiers for R5–R9 did not run (the run hit a usage-credit limit on 2026-10-06), so those briefs carry only their own Gaps sections: treat every number in R5–R9 as the brief's reading of its source, not as independently verified.

## R1 — pretrain-recipes: 8 of 10 key claims checked, 2 refuted

### Claim 1 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Qwen3 was pretrained on 36 trillion tokens across 119 languages in three stages (>30T at 4k ctx, ~5T reasoning-heavy, hundreds of billions at 32k); Qwen3-0.6B-Base MMLU 52.81, Qwen3-1.7B-Base 62.63, Qwen3-4B-Base 72.99; on-policy distillation used ~1/10 the GPU-hours of RL (1,800 vs 17,920 on Qwen3-8B).  
  <https://arxiv.org/html/2505.09388>
- **Verifier:** confirmed

### Claim 2 — REFUTED (verifier confidence: high)
- **Brief said:** SmolLM3-3B was trained on 11.2T tokens (11.1T pretraining + 100B long-context + 35B reasoning mid-training) with WSD LR 2e-4 decaying to 0 in the final 10% of steps, on 384 H100s for 24 days; config.json shows 36 layers, hidden 2048, 16 Q / 4 KV heads, vocab 128,256, tie_word_embeddings=true, no_rope_layer_interval=4.  
  <https://huggingface.co/blog/smollm3>
- **Verifier:** Mostly correct, but the token decomposition is imprecise. The primary sources frame 11.2T as the three-stage PRETRAINING total, not a sum that includes the mid-training stages: blog (https://huggingface.co/blog/smollm3) says "we train SmolLM3 on 11.2T tokens using a three-stage training strategy" and model card (https://huggingface.co/HuggingFaceTB/SmolLM3-3B) says "pretrained on 11.2T tokens ... Post-training included midtraining on 140B reasoning tokens". The 100B long-context extension ("After the main pretraining, we trained SmolLM3 on an additional 100B tokens") and the reasoning mid-training are separate stages ON TOP of the 11.2T (total seen ≈11.3T+). The source is itself inconsistent: the blog's stage list ends "Stage 3: Decay Phase (10T → 11.1T tokens)" and the card's spec table says "Pretraining tokens: 11T". Also, the reasoning mid-training DATASET was 35B tokens ("Our mid-training dataset contained 35B tokens sourced from ... OpenThoughts3-1.2M"), but the model was trained on 140B tokens in that stage ("where we trained the model on 140B tokens of general reasoning data"; card: "midtraining on 140B reasoning tokens"). Corrected statement: "SmolLM3-3B was pretrained on ~11.2T tokens (blog stage list: 11.1T) in three WSD stages (LR 2e-4, 2000 warmup steps, linear decay to 0 over the final 10% of steps, global batch 2.36M tokens at 4096 seq len, AdamW β=(0.9,0.95), wd 0.1), followed by a 100B-token long-context mid-training (4k→32k→64k) and a reasoning mid-training of 140B tokens drawn from a 35B-token dataset; pretraining ran on 384 H100 GPUs for 24 days." Everything else in the claim is CONFIRMED verbatim: config.json (https://huggingface.co/HuggingFaceTB/SmolLM3-3B/resolve/main/config.json) has num_hidden_layers=36, hidden_size=2048, num_attention_heads=16, num_key_value_heads=4, vocab_size=128256, tie_word_embeddings=true, no_rope_layer_interval=4 (plus intermediate_size=11008, rope_theta=5e6, max_position_embeddings=65536); blog: "The model was trained on 384 H100 GPUs for 24 days"; license Apache-2.0 (card). Note: WebSearch budget was exhausted this turn, so independent corroboration beyond HF sources was limited to the huggingface/smollm GitHub README (confirms "11T tokens" headline only).

### Claim 3 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Falcon-H1-1.5B (24 layers) and Falcon-H1-1.5B-Deep (66 layers) were both trained on 3T tokens; the Deep instruct model scores MMLU 66.11 / GSM8K 82.34 / HumanEval 73.78 / IFEval 83.5 vs 62.03 / 74.98 / 68.29 / 80.66 for the shallow one.  
  <https://huggingface.co/tiiuae/Falcon-H1-1.5B-Deep-Instruct>
- **Verifier:** confirmed

### Claim 4 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Gemma 4 is released under Apache 2.0; E2B has 2.3B effective / 5.1B total parameters and 35 layers, E4B 4.5B effective / 8B total and 42 layers, both with 128K context and 262K vocab; E2B MMLU-Pro 60.0, E4B 69.4.  
  <https://ai.google.dev/gemma/docs/core/model_card_4>
- **Verifier:** confirmed

### Claim 5 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** The Qwen3.5 small models (9B, 4B, 2B, 0.8B) were released on March 2, 2026; the 4B uses an 8 x (3 x Gated DeltaNet + 1 x Gated Attention) hybrid layout, 32 layers, hidden 2560, tied 248,320 vocab, 262,144 native context, and scores MMLU-Pro 79.1, IFEval 89.8, BFCL-V4 50.3, TAU2-Bench 79.9.  
  <https://github.com/QwenLM/Qwen3.5>
- **Verifier:** confirmed

### Claim 6 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** NVIDIA Nemotron 3 Nano 4B (released March 16, 2026) has 3.97B parameters in a 42-layer hybrid (21 Mamba-2, 4 attention, 17 MLP; hidden 3136), was compressed from Nemotron-Nano-9B-v2 via Nemotron Elastic, lists >10 trillion training tokens, and scores BFCL v3 61.1, IFEval-Instruction 88.0, RULER-128k 91.1.  
  <https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16>
- **Verifier:** confirmed. Primary source (https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16) README states verbatim: "Release Date: 3/16/2026"; "Number of model parameters 3.97 x 10^9"; "compressed from NVIDIA-Nemotron-Nano-9B-v2 using the Nemotron Elastic framework ... hybrid architecture consisting primarily of Mamba-2 and MLP layers combined with just four Attention layers"; "Text Training Data Size: More than 10 Trillion Tokens"; Reasoning-off table: BFCL v3 61.1, IFEval-Instruction 88, RULER (128k) 91.1. The repo's config.json (https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16/raw/main/config.json, fetched twice via two independent paths with identical content) gives num_hidden_layers 42, hidden_size 3136, hybrid_override_pattern "M-M-M-MM-M-M*-M-M*-M-M-M*-M-M-MM*-MMM-M-M-"; my own character count (Bash) = 21 M (Mamba-2), 4 * (attention), 17 - (MLP), total 42, matching the claim exactly. Independent corroboration: Ollama's nemotron-3-nano:4b tag lists 3.97B parameters (https://ollama.com/library/nemotron-3-nano:4b); HF API metadata lists 3973.6M params and base_model nvidia/NVIDIA-Nemotron-Nano-9B-v2; the Nemotron Elastic paper exists at https://arxiv.org/abs/2511.16664. Precision caveats (not errors): (1) the three scores are the model card's Reasoning-OFF numbers; in Reasoning-ON mode BFCL v3 is also 61.1 but IFEval-Instruction is 92, and RULER-128k is reported only in reasoning-off, so a citation should say "reasoning-off". (2) The 21/4/17 breakdown and hidden size 3136 are not stated in the card's prose (which only says "just four Attention layers"); they are derived from config.json. (3) Elastic paper v1 (Nov 2025) only documents 12B->9B/6B compression; the 9B->4B derivation is attested only by NVIDIA's model card. (4) Training window per card: Dec 2025 - Jan 2026, data cutoff Sep 2024. License (not part of the claim) is the NVIDIA Nemotron Open Model License. Note: WebSearch budget for this turn was exhausted, so independent checks were limited to direct fetches of Ollama, arXiv, and the HF API.

### Claim 7 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** LFM2.5-1.2B-Instruct (1.17B params, 16 layers: 10 double-gated conv + 6 GQA, vocab 65,536, 32k ctx) was pretrained on 28T tokens and scores MMLU-Pro 44.35, IFEval 86.23, IFBench 47.33, GPQA 38.89, versus Qwen3-1.7B 42.91 / 73.68 / 21.33 / 34.85.  
  <https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct>
- **Verifier:** confirmed

### Claim 8 — REFUTED (verifier confidence: high)
- **Brief said:** MobileLLM-Pro (1.084B params, 30 layers, hidden 1280, 20 Q / 4 KV heads, vocab 202,048, 128k ctx, local:global 3:1 with 512-token window) was pretrained on ~1.64T tokens with KL-divergence logit distillation from Llama-4-Scout-17B-16E; int4 QAT regression 0.4% (CPU config) / 1.3% (accelerator); FAIR Noncommercial license.  
  <https://huggingface.co/facebook/MobileLLM-Pro>
- **Verifier:** Substantively confirmed by the primary source, but three details are imprecise. Corrected statement: MobileLLM-Pro (facebook/MobileLLM-Pro, Meta Reality Labs, released October 2025) has 1,084M params (HF numParameters 1,084,453,120), 30 layers, model dimension 1280 (config.json hidden_size=1280) with FFN dimension 6144 (the model card labels 6144 as "Hidden Dimension" and 1280 as "Dimension", so "hidden 1280" is ambiguous), 20 attention heads / 4 KV heads (head_dim 64), vocab 202,048, 128k context (max_position_embeddings 131072), and interleaved local:global attention at a nominal 3:1 ratio with a 512-token sliding window (config.json: 22 sliding + 8 full-attention layers; global every 4th layer plus the final layer). It was trained on a pre-training datamix of ~1,640B tokens (technical report Table 2: 1640.3B; Phase 1 1.4T, Phase 2 +20B long-context, Phase 3 60M specialist merging, plus an 80B-token QAT phase) with logit-based knowledge distillation using a forward-KL loss from Llama 4-Scout (teacher linked as meta-llama/Llama-4-Scout-17B-16E). Int4 QAT regression: the model card's Key Features headline says 0.4% (CPU: int4 group-32 weights, int8 dynamic activations, int8 KV cache) and 1.3% (accelerator: int4 per-channel weights), but the card's own 11-benchmark table and the independent technical report (arXiv:2511.06719, Table 5) give averages 61.81 (FP) -> 61.08 (CPU) -> 60.42 (accelerator), i.e. 0.73 and 1.3 points absolute, and the card's Quantization section separately states 1.5% (absolute) for groupwise QAT vs 34% for PTQ; cite 0.73%/1.3% (paper) or flag 0.4% as the card's unreconciled headline. License is the "FAIR Noncommercial Research License" v1 (last updated Sept 23, 2025; HF tag fair-noncommercial-research-license), which the card abbreviates "FAIR NC". Sources: model card https://huggingface.co/facebook/MobileLLM-Pro (gated; README/config.json mirrored verbatim at https://huggingface.co/camenduru/MobileLLM-Pro); LICENSE https://huggingface.co/facebook/MobileLLM-Pro/blob/main/LICENSE; MobileLLM-Pro Technical Report, arXiv:2511.06719 (published 2025-11-10) https://arxiv.org/abs/2511.06719. Note: WebSearch budget was exhausted this turn; verification used direct fetches and the Hugging Face Hub tool.

## R2 — distillation: 8 of 10 key claims checked, 1 refuted

### Claim 1 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** BitNet Distillation (BitDistill, submitted 2025-10-15) converts Qwen3-0.6B/1.7B/4B to 1.58-bit using SubLN, 10B tokens of continued pre-training from the FALCON corpus, and MiniLM-style attention + logit distillation; it reports 88–96% accuracy on MNLI/QNLI/SST-2 matching FP16-SFT (vs 74–82% for direct 1.58-bit SFT), 10x memory saving (0.11 vs 1.20 GB) and 2.65x CPU speed (1,135 vs 427 tok/s).  
  <https://arxiv.org/html/2510.13998>
- **Verifier:** confirmed

### Claim 2 — REFUTED (verifier confidence: high)
- **Brief said:** ParetoQ finds optimal performance is nearly achieved by spending the majority of the budget on FP training and ~10% on QAT; 1-bit/1.58-bit/2-bit saturate at ~30B QAT tokens while 3/4-bit saturate at ~10B; its 600M ternary model (58.7 avg) surpasses a prior 3B ternary model trained with 100B tokens; released weights carry the FAIR Noncommercial Research License.  
  <https://arxiv.org/html/2502.02631>
- **Verifier:** Mostly confirmed, but the 58.7 figure is wrong/imprecise. Corrected statement: ParetoQ (Meta AI, Zechun Liu et al.; arXiv:2502.02631, v1 4 Feb 2025, v2 13 Oct 2025, NeurIPS 2025) finds that with a fixed 100B-token budget, "optimal performance is nearly achieved by dedicating the majority of the training budget to full precision (FP) training and approximately 10% to QAT" (Finding-1/Fig. 2), and that QAT fine-tuning "typically saturates at 10B tokens for 3-bit and 4-bit, and at 30B tokens for 1-bit, 1.58-bit, and 2-bit" (Fig. 3) — both verbatim at https://arxiv.org/html/2502.02631. Its 600M ternary model scores 55.5 average zero-shot accuracy (Table 2; also 55.5 in the GitHub README https://github.com/facebookresearch/ParetoQ and the HF model card https://huggingface.co/facebook/MobileLLM-ParetoQ-600M-1.58-bit), edging out the prior SoTA ternary 3B model (1-bit Era / BitNet b1.58 3B) at 54.5 — a 1.0-point margin. The '58.7' appears only in the paper's Sec. 5.2 prose and contradicts its own Table 2 (58.7 is the 1-bit Era 3B ARC-e cell there), so it is almost certainly a typo and should not be cited as the 600M average. The BitNet b1.58 3B baseline was indeed pre-trained on 100 billion RedPajama tokens, but that detail comes from Ma et al. 2024 (https://arxiv.org/html/2402.17764), not from the ParetoQ paper, whose own '100B' refers to its total budget and to a 1-bit Era follow-up on LLaMA-3 8B. License: the released weights on Hugging Face are gated under the FAIR Noncommercial Research License (license_name: fair-noncommercial-research, confirmed via https://huggingface.co/api/models/facebook/MobileLLM-ParetoQ-600M-1.58-bit); the ParetoQ code on GitHub is BSD-3-Clause (https://raw.githubusercontent.com/facebookresearch/ParetoQ/main/LICENSE). Note: WebSearch budget was exhausted this turn, so independent verification used the GitHub repo, HF model cards/API, and the BitNet b1.58 paper via WebFetch/curl rather than search.

### Claim 3 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Spectra-1.1 fits a ternary scaling law with training-data exponent 0.81 versus parameter exponent 0.32 (FloatLM 0.53 vs 0.56), and trains 1.5B/2.5B/3.6B TriLMs on up to 1.2T tokens (paper submitted 2025-06-28).  
  <https://arxiv.org/abs/2506.23025>
- **Verifier:** confirmed

### Claim 4 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Qwen3 Technical Report: on Qwen3-8B, on-policy distillation reached AIME'24 74.4 / AIME'25 65.5 in ~1,800 GPU-hours versus 67.6 / 55.5 for RL in 17,920 GPU-hours; all Qwen3 models are released under Apache 2.0.  
  <https://arxiv.org/html/2505.09388>
- **Verifier:** confirmed

### Claim 5 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** DeepSeek-R1 distilled students were fine-tuned with ~800K curated samples using SFT only (no RL); DeepSeek-R1-Distill-Qwen-32B scored 72.6 AIME 2024 / 94.3 MATH-500 / 62.1 GPQA / 57.2 LiveCodeBench versus 47.0 / 91.6 / 55.0 / 40.2 for DeepSeek-R1-Zero-Qwen-32B trained with large-scale RL.  
  <https://arxiv.org/html/2501.12948v1>
- **Verifier:** confirmed

### Claim 6 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** PrismML Ternary Bonsai 1.7B (Apache-2.0, built from Qwen3-1.7B, GGUF Q2_0 at 2.125 bits/weight, 436 MiB) scores 58.47 average vs 66.57 for Qwen3-1.7B, with BFCLv3 51.0 vs 71.8 and GSM8K 74.2 vs 83.1; the whitepaper discloses format and evaluation but not the training recipe or token count.  
  <https://huggingface.co/prism-ml/Ternary-Bonsai-1.7B-gguf>
- **Verifier:** confirmed

### Claim 7 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** The Gemma Terms of Use define Model Derivatives to include models created through distillation or 'methods based on the generation of synthetic data Outputs by Gemma', require pass-through of use restrictions, cover Gemma 1, 1.1, 2, 3 and 3n, and state that Gemma 4 has a separate license (Apache 2.0 per the Gemma 4 E2B model card).  
  <https://ai.google.dev/gemma/terms>
- **Verifier:** confirmed

### Claim 8 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** The Llama 3.2 Community License (release date 2024-09-25) states that if you use the Llama Materials 'or any outputs or results' to create, train, fine tune or improve an AI model that is distributed, you must include 'Llama' at the beginning of the model name, display 'Built with Llama', and request a license from Meta above 700 million monthly active users.  
  <https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_2/LICENSE>
- **Verifier:** confirmed

## R3 — tool-use: 7 of 10 key claims checked, 3 refuted

### Claim 1 — REFUTED (verifier confidence: high)
- **Brief said:** On the official BFCL v4 leaderboard CSV (fetched 2026-10-06, 109 rows), xLAM-2-3b-fc-r (FC) scores 41.22 overall with 58.38 Multi-Turn, 82.96 Non-Live AST, 62.92 Live, 63.45 Irrelevance, 2.50 Web Search and 11.40 Memory; it is the only model ≤4B with Multi-Turn ≥50, and its Multi-Turn exceeds GPT-5.2-2025-12-11 (FC) at 28.12.  
  <https://gorilla.cs.berkeley.edu/data_overall.csv>
- **Verifier:** On the official BFCL v4 leaderboard CSV (https://gorilla.cs.berkeley.edu/data_overall.csv; 109 data rows plus header; leaderboard page shows "Last Updated: 2026-04-12"), xLAM-2-3b-fc-r (FC) (rank 42, Salesforce, cc-by-nc-4.0, research-only release, 3.09B params) scores 41.22% overall, 58.38% Multi-Turn, 82.96% Non-Live AST, 62.92% Live, 63.45% Irrelevance, 2.50% Web Search and 11.40% Memory, and its Multi-Turn exceeds GPT-5.2-2025-12-11 (FC) at 28.12% — all of these numbers are CONFIRMED. However, it is NOT the only model ≤4B with Multi-Turn ≥50: Nanbeige4-3B-Thinking-2511 (FC) (rank 25, Apache-2.0, 3.93B params per https://huggingface.co/api/models/Nanbeige/Nanbeige4-3B-Thinking-2511 safetensors metadata) scores 51.12% Multi-Turn and 51.40% overall on the same CSV, and its model card (https://huggingface.co/Nanbeige/Nanbeige4-3B-Thinking-2511) independently states it ranks #25 on BFCL. Corrected statement: xLAM-2-3b-fc-r has the HIGHEST Multi-Turn score among ≤4B models (58.38% vs Nanbeige4-3B's 51.12%), but it is one of two ≤4B models with Multi-Turn ≥50, and Nanbeige4-3B-Thinking-2511 beats it on overall accuracy (51.40% vs 41.22%) under a permissive Apache-2.0 license, whereas xLAM-2-3b-fc-r is cc-by-nc-4.0 (non-commercial, research release per https://huggingface.co/Salesforce/xLAM-2-3b-fc-r).

### Claim 2 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** On the same CSV, Hammer2.1-3b (FC) scores 29.71 overall / 84.96 Non-Live / 70.54 Live / 16.50 Multi-Turn / 86.12 Irrelevance; Hammer2.1-1.5b 27.88 / 82.98 / 69.50 / 15.62 / 79.40; Hammer2.1-0.5b 21.22 / 65.98 / 54.63 / 2.88 / 80.79; Qwen3-4B-Instruct-2507 (FC) 35.68 / 87.88 / 76.39 / 22.12 / 84.93 with 3.00 Web Search and 17.63 Memory.  
  <https://gorilla.cs.berkeley.edu/data_overall.csv>
- **Verifier:** confirmed

### Claim 3 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** BFCL V4 (released 2025-07-17) reweighted the overall score to Agentic 40%, Multi-Turn 30%, Live 10%, Non-Live 10%, Irrelevance/Hallucination 10% (from Live 33 / Non-Live 33 / Multi-Turn 33 / Irrelevance 0 in V3, released 2024-09-19); Web Search has 200 entries and Memory 465 (155 each for KV, vector, recursive summarization).  
  <https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/CHANGELOG.md>
- **Verifier:** Confirmed on every number and date, with one attribution refinement. Primary source (CHANGELOG, fetched raw from https://raw.githubusercontent.com/ShishirPatil/gorilla/main/berkeley-function-call-leaderboard/CHANGELOG.md): "[Jul 17, 2025] #1019: BFCL V4 release ... Revised overall-accuracy formula" with table Old%/New%: Live 33/10, Non-Live 33/10, Irrelevance 0/10, Multi-Turn 33/30, Agentic 0/40; and "[Sept 19, 2024] #644: BFCL V3 release: Introduce new multi-turn dataset and state-based evaluation metric". Independent confirmation of the weights (official BFCL V4 Web Search blog, release date 2025-07-17, https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html): "Overall Score = (Agentic x 40%) + (Multi-Turn x 30%) + (Live x 10%) + (Non-Live x 10%) + (Hallucination x 10%)". Refinement: the entry counts are NOT in the CHANGELOG; they come from that blog's score-composition chart: Agentic (665) = Web Search Unweighted Average (200) + Memory Unweighted Average (465); Memory = Vector Store (155) + Key Value Store (155) + Rec Sum (155); Web Search (200) = base (100) + No Snippet (100). The repo data files corroborate this: bfcl_eval/data/BFCL_v4_memory.json holds 155 unique prompts (memory_0 ... memory_154) run against 3 backends = 465 scored cases, and BFCL_v4_web_search.json holds 100 unique prompts (web_search_0 ... web_search_99) run in 2 variants = 200 scored cases. Suggested wording: "...Web Search has 200 scored cases (100 prompts x base/no-snippet) and Memory 465 (155 prompts x KV, vector, recursive-summarization backends), per the BFCL V4 blog." Note the CHANGELOG labels the 10% segment "Irrelevance" while the blog calls it "Hallucination Measurement"; "Irrelevance/Hallucination" is accurate. WebSearch budget was exhausted this turn, so independent checking used WebFetch and direct curl of the official blog and repo files.

### Claim 4 — REFUTED (verifier confidence: high)
- **Brief said:** APIGen-MT (arXiv 2504.03601, Apr 2025) reports BFCL v3 overall/multi-turn/relevance of 65.11/56.00/94.44 for xLAM-2-3b-fc-r and 58.90/43.12/88.89 for xLAM-2-1b-fc-r, τ-bench overall 38.2 and 21.8, trained on 3,820 validated multi-turn trajectories (avg 7 tool calls, 6 user turns) plus xlam-60k, ≤3 epochs full fine-tune; xLAM-2 weights and APIGen-MT-5k are CC-BY-NC-4.0 with an OpenAI non-compete clause.  
  <https://arxiv.org/html/2504.03601v2>
- **Verifier:** Benchmark numbers and training recipe are CONFIRMED by the primary source; the trajectory count and the license attribution are IMPRECISE. Corrected statement: "APIGen-MT (arXiv 2504.03601; v1 4 Apr 2025, v2 8 Apr 2025, current v4 19 Jul 2025) reports BFCL v3 Overall/Multi-Turn/Relevance of 65.11/56.00/94.44 for xLAM-2-3b-fc-r and 58.90/43.12/88.89 for xLAM-2-1b-fc-r (Table 1, both v2 and v4: https://arxiv.org/html/2504.03601v4), and τ-bench overall 38.2 (retail 44.4 / airline 32.0) and 21.8 (22.5 / 21.0). Figure 4 gives avg 7 tool calls and 6 user turns per trajectory; the '3,820 total validated trajectories' figure appears ONLY in v1/v2 Figure 4 and was removed in v3/v4 — and it is a pipeline-yield statistic, not the training-set size: the released Salesforce/APIGen-MT-5k holds 5,000 trajectories and its card says it 'is a subset of the data used to train the xLAM-2 model series' (https://huggingface.co/datasets/Salesforce/APIGen-MT-5k), so the models saw >5,000 APIGen-MT trajectories. Training was filtered behavioral cloning, full fine-tuning (DeepSpeed ZeRO-3, bf16, AdamW, LLaMA-Factory) for 'at most 3 epochs' on an H200 node, jointly with APIGen function-calling data [26] (= xlam-function-calling-60k, also listed on the model cards) AND 'other domains of agentic data' from xLAM [52] and ActionStudio [53] — not xlam-60k alone. 1b/3b are Qwen 2.5-based (repo names Salesforce/xLAM-2-1b-fc-r, Salesforce/xLAM-2-3b-fc-r; 'Llama-xLAM-2-3b-fc-r' does not exist); 8b/70b are Llama 3.1/3.2-based. Licenses: the dataset and all xLAM-2 model cards are tagged cc-by-nc-4.0, research release only (-r). The OpenAI clause ('A part of this dataset was generated using GPT-4 and should not be used to develop models that compete with OpenAI') is on the APIGen-MT-5k DATASET card only; the model cards (xLAM-2-1b-fc-r, xLAM-2-3b-fc-r, Llama-xLAM-2-8b-fc-r, full text read) contain no such clause and instead add the Meta Llama 3 Community License for Llama-based variants (https://huggingface.co/Salesforce/xLAM-2-1b-fc-r). The paper's arXiv license is CC BY 4.0. Independent check: the xLAM-2 models were added to BFCL on 9 Apr 2025 (#972), but the leaderboard moved to BFCL V4 on 17 Jul 2025 (#1019; agentic categories weighted 40%), so the live leaderboard no longer reproduces the paper's v3 snapshot — https://gorilla.cs.berkeley.edu/data_overall.csv today shows xLAM-2-3b-fc-r (FC) 41.22% overall / 58.38% multi-turn / 87.50% relevance and xLAM-2-1b-fc-r (FC) 30.44% / 36.00% / 87.50%. The 65.11/58.90 figures are the paper's self-reported BFCL v3 numbers 'as of 04/02/2025' (model card) and should be cited as such." Sources: https://arxiv.org/abs/2504.03601 (version history), https://arxiv.org/html/2504.03601v2 (3,820 in Fig. 4), https://arxiv.org/html/2504.03601v4 (current; 3,820 removed), https://huggingface.co/datasets/Salesforce/APIGen-MT-5k, https://huggingface.co/Salesforce/xLAM-2-1b-fc-r, https://huggingface.co/Salesforce/xLAM-2-3b-fc-r, https://github.com/SalesforceAIResearch/xLAM (code Apache-2.0, datasets CC-BY-NC-4.0), https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/CHANGELOG.md, https://gorilla.cs.berkeley.edu/data_overall.csv.

### Claim 5 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Salesforce/xlam-function-calling-60k has 60,000 examples over 3,673 executable APIs in 21 categories, licence CC-BY-4.0, generated with DeepSeek-V2-Chat and Mixtral-8x22B; MadeAgents/xlam-irrelevance-7.5k is 7,500 samples with the ground-truth tool removed, licence CC-BY-4.0.  
  <https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k>
- **Verifier:** confirmed

### Claim 6 — REFUTED (verifier confidence: high)
- **Brief said:** ToolRL (arXiv 2504.13958, Apr 2025) trains with GRPO on 4,000 prompts (2k ToolACE, 1k Hammer-masked, 1k xLAM) using a 0/1 format reward plus a −3..3 correctness reward decomposed into tool-name, parameter-name and parameter-value matching, and reports BFCL v3 overall of 52.98 for Qwen2.5-3B (base 41.97) and 46.20 for Qwen2.5-1.5B (SFT 40.67).  
  <https://arxiv.org/html/2504.13958>
- **Verifier:** Mostly confirmed, but one number is mislabelled and the model attribution is imprecise. Corrected statement: "ToolRL (arXiv 2504.13958, v1 16 Apr 2025; Qian et al.) trains with GRPO (cold start, no SFT) on a 4K-example set (2K ToolACE, 1K Hammer with masked/randomized tool and parameter names, 1K xLAM), using a format reward in {0,1} plus a correctness reward in [−3,3] decomposed into Tool Name Matching, Parameter Name Matching and Parameter Content Matching (final reward in [−3,4]). On BFCL v3 Overall (Table 1) it reports: Qwen2.5-3B-Instruct — Raw 33.04, SFT4k 41.97, GRPO Cold Start 52.98; Qwen2.5-1.5B-Instruct — Raw 19.41, SFT4k 40.67, GRPO Cold Start 46.20." Errors in the original claim: (a) "Qwen2.5-3B (base 41.97)" is wrong — 41.97 is the SFT4k score, the raw/base-Instruct score is 33.04 (so the GRPO gain over the untuned model is ~20 points, not ~11); (b) the models are Qwen2.5-*-Instruct, the paper never uses non-Instruct base checkpoints; (c) the paper's term is "Parameter Content Matching", not "parameter-value matching" (minor). Sources: primary https://arxiv.org/html/2504.13958v1 (Table 1, Sec. 3.3 Reward Design, Sec. 4 experimental setup); independent https://github.com/qiancheng0/ToolRL (README confirms "2K ToolACE data, 1K Hammer (Masked) data, and 1K xLAM data", GRPO and PPO scripts, Apache-2.0 license; README does not restate BFCL numbers, which exist only in the paper).

### Claim 8 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Qwen3 technical report (May 2025) gives BFCL v3 of 65.9 / 56.6 / 46.4 (thinking) and 57.6 / 52.2 / 44.1 (non-thinking) for Qwen3-4B / 1.7B / 0.6B, pretraining on 36T tokens, and small models trained by strong-to-weak distillation (off-policy then on-policy logit KL to Qwen3-32B or Qwen3-235B-A22B) at about 1/10 of the GPU hours of the four-stage pipeline.  
  <https://arxiv.org/html/2505.09388>
- **Verifier:** confirmed

## R4 — calibration-abstention-retrieval: 8 of 10 key claims checked, 0 refuted

### Claim 1 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** AbstentionBench (Meta, submitted 10 Jun 2025) evaluates 20 LLMs on 20 datasets and finds reasoning fine-tuning degrades abstention by 24% on average.  
  <https://arxiv.org/abs/2506.09038>
- **Verifier:** confirmed

### Claim 2 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** TruthRL (ICML 2026) uses a ternary GRPO reward (+1 correct / 0 uncertain / -1 incorrect); on Llama3.1-8B-Instruct with retrieval hallucination falls 43.5% -> 19.4% and truthfulness rises 5.3% -> 37.2% vs prompting; at 3B, Llama3.2-3B truthfulness 1.9% -> 27.4% and hallucination 45.1% -> 21.5%.  
  <https://arxiv.org/abs/2509.25760>
- **Verifier:** confirmed

### Claim 3 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Search-R1 (Mar 2025, Apache-2.0) improves Qwen2.5-3B-Instruct average exact match across seven QA datasets from 0.270 (RAG) to 0.325, with Direct inference at 0.134; training set is NQ+HotpotQA, 169.6k rows.  
  <https://arxiv.org/abs/2503.09516>
- **Verifier:** confirmed

### Claim 4 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** s3 trains a 7B searcher with only 2.4k examples in 114 minutes on 5 A100s versus 3,780 minutes for Search-R1, outperforming baselines trained on >70x more data.  
  <https://arxiv.org/abs/2505.14146>
- **Verifier:** confirmed

### Claim 5 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Standard reinforcement finetuning reduces refusal rates by more than 80%; adding 10% synthetic unanswerable math (SUM) substantially restores refusal with minimal accuracy trade-off.  
  <https://arxiv.org/abs/2505.13988>
- **Verifier:** confirmed

### Claim 6 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Semantic entropy (Nature 630:625-630, 19 Jun 2024) achieves mean AUROC 0.790 for confabulation detection vs 0.691 for naive entropy, stable 0.78-0.81 from 7B to 70B, but requires multiple sampled generations; Semantic Entropy Probes approximate it from one generation's hidden states at near-zero overhead.  
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC11186750/>
- **Verifier:** confirmed

### Claim 7 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** SimpleQA contains 4,326 questions graded correct / incorrect / not attempted, with F-score the harmonic mean of overall-correct and correct-given-attempted; best Nov-2024 result o1-preview 42.7% correct.  
  <https://arxiv.org/html/2411.04368>
- **Verifier:** confirmed

### Claim 8 — stands (possibly corrected) (verifier confidence: high)
- **Brief said:** Firebase AI Logic hybrid inference falls back from Gemini Nano to cloud when the on-device model is unavailable or for unsupported capabilities, explicitly including function calling and multi-turn chat; requires Chrome v139+.  
  <https://firebase.google.com/docs/ai-logic/hybrid-on-device-inference>
- **Verifier:** confirmed
