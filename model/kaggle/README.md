# model/kaggle - Notebook 1 `e1-evolve-pilot`

**Status:** written and smoke-executed on 2026-10-07; **nothing in this directory has been run on a GPU**. Every number below is either labelled [meas] with the evidence file that holds it, [arith], or [est] with its basis.
Labels follow `model/01-ALICE-NEXT-design.md` s0. Plan source: `model/05-risks-and-90-day-plan.md` s3 (the notebook spec), `model/02-training-and-distillation-plan.md` (S0-S3, QAT s3, register s4).
This directory is pushed with the sprint branch (Justin asked for everything to be pushed and will move it to a private repository); keep the Kaggle kernel itself **private** (publish policy: weights, recipe and factory stay private until a `PUBLISH?` item is answered).

| File | What |
|---|---|
| `e1-evolve-pilot.ipynb` | the notebook (19 cells: 11 code, 8 markdown). GPU session on Kaggle, or CPU smoke with `E1_SMOKE=1` |
| `e1-evolve-pilot.smoke-executed.ipynb` | the same notebook executed end to end in smoke mode (`E1_SMOKE=1 jupyter nbconvert --to notebook --execute`); its outputs show every cell runs. **Smoke numbers are plumbing checks, not measurements.** |
| `tools/g1_encode_dump.rs`, `tools/g1_rust_parity.py` | Linux-side G1 check: the notebook's token ids vs the **real** Rust `encode()` (`tokenizer.rs` is `include!`d unmodified at compile time) |
| `tools/g3_gateway_diff.py` | Linux-side G3 check: the notebook's Python gateway port vs the real Rust scanner functions of `agent_trace.rs` |
| `evidence/` | logs of the checks that were run while writing this (G1, G3, scale convention, trit agreement), see "What was verified here" |

## 1. What the notebook does

| Cell | Does |
|---|---|
| 0 | environment + Kaggle quota reading; the **QAT primitives** (verbatim math of `tinybit/model.py`: per-tensor `gamma = mean|w|`, `w_q = round(w/gamma).clamp(-1,1)`, per-token int8 absmax activations, straight-through); **G5 audit** that the five CIS activation-quantization points are live in the training forward (inputs of q/k/v and gate/up, `o_proj` input after `attn_sub_norm`, `down_proj` input after `ffn_sub_norm`, and the final-norm output feeding the tied head); **G12** fp16-vs-bf16 numerics on 20 prompts (max logit abs diff printed); proof that the QAT layer equals Hugging Face's own online BitLinear (value and gradient); GPU name, free memory and real tokens/s of the base forward pass |
| 1 | data factory: gateway-verified operator episodes in the `agent_trace` text form (`Q:` / `A: CALC(..).` / `TOOL[calc]=..` / short operator-voice answer). Generators: `calc_easy`, `calc_hard`, `calc_overflow` (incl. i64 overflow and division by zero -> the gateway's fixed strings), `lookup_hit` / `lookup_miss` (NONE) / `lookup_near_miss`, `file_read` (hit / NOT-FOUND), `unknown_fact` (plain question, key only in a declared table -> `LOOKUP(<verbatim key>)`), `mixed` (two calls), `distractor`, `in_context_answerable`, `undeclared_tool` and `unanswerable` (a tool exists only when declared). Every label from an exact oracle, kept only if the episode round-trips through a Python port of the gateway scanner; `generator` field per sample; SHA-256 manifest; train and dev use disjoint namespaces, phrasings and header families; canary string |
| 2 | tokenizer parity G1 - **the notebook ports the engine's `encode()`** (not the HF Llama-3 tokenizer) over the pruned 50,256-id vocabulary; asserts the rebuilt `VOCAB.BIN` equals the pinned incumbent, prints the known skew cases next to the HF tokenization, packs the episodes (whole-episode packing, loss only on the model turns), writes `g1_vectors.jsonl` |
| 3 | base reference (stock HF online BitLinear) + the three arms **P** (periphery only), **L** (full QAT, LR 3e-5), **H** (full QAT, LR 1e-4): AdamW(0.9, 0.95), WD 0, warmup 10 then cosine to 10%, batch 1 x accum 16 x 1024 = 16,384 tokens/step, assistant-only loss, gradient checkpointing, autocast, checkpoint every 100 steps with resume, kill gates printed at every eval |
| 4 | export in the layout `repack_ternary.py` accepts (int8 `{-1,0,+1}` + F32 `weight_scale`, BF16 norms and full embedding table, `config.json`, tokenizer files), validation, reload-from-file parity, optional run of the real repacker if present, gateway suite TSVs, the exact Linux commands, SHA-256 of every exported file |
| 5 | gates vs measured table -> `results.json`; the honesty rules |

The loss uses the engine's **served vocabulary** only: the head ranks over the 50,256 kept rows of the (full, 128,256-row) embedding table, so the softmax the loss sees is the one the engine argmaxes over (G6). The full table is kept and exported because `repack_ternary.py --llama3-prune` slices it itself.

### Choices that are deviations from, or readings of, the spec - read these
* **Precision.** Master weights are fp32 for every trainable tensor. Autocast is **bf16 only where the GPU has native bf16**; on T4 and P100 it is **fp16 + GradScaler** (the plan s3 recipe: T4 has no bf16). The numerics check (G12) compares the fp32-master/fp16-autocast forward with a bf16 reference.
* **Arm P** stores the frozen ternary weights as fp16 (lossless container for the bf16 master) and trains the embedding/head, RMSNorm and SubLN gains in fp32.
* **Scale convention for the export: MULTIPLY, `weight_scale = gamma = mean|w|`, command pinned to `--scale-convention multiply`** (not the tinybit divide convention). Why, with evidence: the packed incumbent stores `weight_scale` = bf16(mean|w| of the bf16 master) (L0 `q_proj` 1.218851 vs 1.21875; L0 `down_proj` 2.163143 vs 2.15625; L15 `gate_proj` 2.173966 vs 2.171875 [meas, `evidence/scale_convention_probe.log`]), the repacker's `auto` picks `multiply` when `config.json` has `quantization_config.quant_method == "bitnet"` (the export keeps it), and storing the reciprocal would make every linear about 4.7x too small - the K12 failure of LAB-02. `validate_export` re-derives the `auto` decision from the written config and asserts it equals the convention used.
* **Step 0 is a near-incumbent, not the incumbent.** Ternarizing the bf16 master reproduces only 98.8%, 96.6% and 97.3% of the packed incumbent's trits on the three tensors probed (L0 `q_proj`, L7 `k_proj`, L15 `gate_proj`); every mismatch lies within 0.01 of the rounding threshold, consistent with the packed weights having been quantized from higher-precision latents [meas, `evidence/trit_agreement_vs_packed.log`; the notebook re-measures it in Cell 0]. Consequences: (i) the notebook measures its own step-0 baseline in the same harness; (ii) `export/step0` (the unmodified master through the export code) will not reproduce the incumbent digest `cab11400d737ac4a` - compare its engine PPL with the incumbent artifact to see the cost; (iii) the weights sitting in the bf16 bin that straddles the threshold (a few percent of all weights) flip with any update, so the trit-flip instrument is dominated by them at first.
* **P0 reading.** The prompt is a one-line tool/table declaration (`TOOLS: CALC, LOOKUP:parts`) and **zero example calls**; that reading is the plan author's (K18, open item for Justin). T2 (two LOOKUP shots on other keys) is evaluated at step 0 and at the end as a diagnostic.
* **Step-0 parity gate** (<= 3% next-token disagreement) is a gate **at step 0 only**; at later evals the same number is printed as drift. The GATE reference is the stock HF forward with fp32 master weights under the same autocast (isolates implementation differences; the intended difference is the int8 head-input quantization, CIS point 5, which the stock forward lacks); the checkpoint's native bf16 stock forward and a head-quantization-off attribution line are printed beside it.
* **No replay corpus.** S4's replay KL needs a licence-cleared open corpus (WikiText-2 is CC BY-SA: evaluation use only). Forgetting is watched through the held-out PPL ratio. The held-out text is WikiText-2 test (ASCII-filtered) when reachable, otherwise synthetic prose that is **not** comparable with the program anchor (stated in `results.json`).
* **The dev scorer is a proxy** (first scanned call equal to the expected call in 24 greedy tokens; no-call buckets scanned for any call opener). The instrument of record is the Linux gateway; the notebook exports the same items as `suite_e1_dev_P0.tsv` / `_T2.tsv` plus a merged `dev_table.tsv` for `run_suite.sh`.

## 2. Run it on Kaggle

1. New **private** notebook (proposed kernel `aefinityaiinc/e1-evolve-pilot`), upload `e1-evolve-pilot.ipynb`. Metadata for `kaggle kernels push` (as in the m5b / e16 kernels): `{"id": "aefinityaiinc/e1-evolve-pilot", "title": "e1-evolve-pilot", "code_file": "e1-evolve-pilot.ipynb", "language": "python", "kernel_type": "notebook", "is_private": true, "enable_gpu": true, "enable_internet": true, "machine_shape": "NvidiaTeslaT4"}`.
2. Accelerator: **GPU T4 x2** for arms L and H (about 25 GiB needed, see below); a single T4 or P100 can run arm **P** and the baseline only (the notebook checks the arithmetic first and records `SKIPPED` with the reason). Internet **ON** (pip, the HF repo, WikiText-2). Session limit 12 h; the notebook stops cleanly after `E1_MAX_HOURS` (default 11), writing a checkpoint.
3. Inputs (all optional): a frozen dataset directory (`E1_DATA_DIR=/kaggle/input/<ds>/data`, manifest SHA-256s verified, generation skipped); the output of an earlier version for resume (`E1_RESUME_FROM=/kaggle/input/<prev>`).
4. Environment variables: Kaggle has no UI for them - add a first cell `import os; os.environ["E1_ARMS"] = "P"`. The full list is in the notebook's first markdown cell (`E1_ARMS`, `E1_MAX_HOURS`, `E1_MAX_STEPS`, `E1_QUOTA_BEFORE_H`, `E1_KEEP_CKPT`, ...).
5. Quota: the notebook tries the `kaggle` API (credentials from Kaggle Secrets `KAGGLE_USERNAME` / `KAGGLE_KEY`, which needs the web-login NEEDS item) and otherwise records `unavailable`; then type the "GPU hours left" shown in the session panel into `E1_QUOTA_BEFORE_H` before running, and note the panel again afterwards. `cm-kaggle quota` before the push and after the pull is the authoritative meter (its raw API "allowed" field reads 6 h while kernels ran past it).
6. Run all. Output (`/kaggle/working`, 20 GB cap): `results.json`, `export/<arm>/` (about 2.8 GB each incl. `export/step0`), `data/` (frozen episodes, packed tensors, manifest), `g1_vectors.jsonl`, `logs/<arm>.jsonl`. The fp32 training checkpoints (9.6 GB + optimizer for L/H) are deleted when an arm finishes unless `E1_KEEP_CKPT=1`.

### Memory [arith] and expected time per arm [est]
* Parameters: 2,084,044,800 ternary + 328,304,640 embedding rows (128,256 x 2560) [arith from the config].
* Arm **P**: ternary weights fp16 4.17 GB + embedding fp32 1.31 GB + grad 1.31 GB + 8-bit Adam 0.66 GB = about 7.5 GB + activations: fits one 16 GB card.
* Arms **L / H**: (2.41 B) x (4 B weights + 4 B grads + 2 B 8-bit Adam) = about 24 GB + activations: fits `2 x T4` with `device_map=auto` (the proven recipe), **not one 16 GB card**. Without `bitsandbytes` (fp32 Adam, 8 B/param) it needs about 39 GB and is skipped.
* Time. The only measured anchor is **894 tok/s on 2 x T4** (150 steps x 4096 tokens in 686.9 s, m5b smoke, `state/reports/2026-08-29-kaggle-compute-facts.md`; short padded sequences, so the packed-sequence rate is expected lower). With the Cell 1 target of about 14 M tokens per arm (plan range 10-20 M): L or H 14 M / 894 = **4.4 h [arith]** (3.1 h at 10 M, 6.2 h at 20 M, as in plan s3). Arm P skips the weight-gradient matmuls of the 2.08 B ternary body: with activation checkpointing 3 matmul passes instead of 4, so about **3.3 h [est, FLOP ratio]**. The fake-quant passes, the 8-bit paged optimizer and the evals are not in the anchor: add **[est] 0.2-0.5 h per arm** for about 9 evals (200 x 512 held-out tokens + about 570 dev prompts x 24 greedy tokens each, from FLOP counts, unmeasured) and 0.2-0.3 h of setup (two model loads, CPU data build). Total for three arms [est] about 13-14 h: **two sessions** (suggested: `E1_ARMS=P,L` then `E1_ARMS=H` with `E1_RESUME_FROM`/`E1_DATA_DIR`). If the quota is the raw API's 6 h per week, one arm is all a week buys - settling that is gate 1.
* The notebook prints no timing except the `E1_THROUGHPUT` line and the `packed_tokens_per_s` of each logged step (Rule A).

## 3. Gates (all GATES, not predictions)

| # | Gate | Where |
|---|---|---|
| G1 | engine-port vocabulary == incumbent `VOCAB.BIN` (SHA-256); token-id parity with the Rust `encode()` | Cell 2 (vocabulary); Rust parity on Linux (`tools/g1_rust_parity.py`) |
| G12 | no non-finite values and first-token argmax agreement >= 18/20, fp16 autocast vs bf16 reference | Cell 0 |
| 1 | real tokens/s measured and the quota logged | Cell 0 + every logged step; `results.json` |
| 2 | loss decreases, no NaN, per arm | Cell 3 |
| 3 | best arm P0 exact-key `unknown_fact` >= **73.3%** (the incumbent's measured T2 value, 22/30, LAB-07 s8) **and** `distractor` no-tool precision not below the step-0 value of the same harness | every eval; Cell 5 |
| 4 | held-out PPL ratio vs the stock reference <= **1.05** for the arm passing gate 3 (flag above 1.02; an arm above 1.05 is stopped) | every eval; Cell 5 |
| 0 | step-0 parity: next-token disagreement vs the stock reference <= **3%** | step 0 of each arm |
| 5 | step-0 export parity (file reloaded; PPL gap <= 3%, exported tokenizer reproduces the ids) | Cell 4; engine parity (`cis_decode`, HF-vs-engine PPL gap) on Linux |
| 6 | recorded, not gated: trit-flip fraction per arm, p(0) census (incumbent 0.42), whether arm P captures most of the gain | Cell 3, Cell 5 |

Gate 3 on about 50 items per bucket is a **movement test** (intervals are wide), not a ship test. If a gate fails: fix the data or the arm before S3 scales; no money is spent (plan s3).

## 4. What to do with the export (Linux side; Cell 4 prints these with real paths)

```
# 0. kaggle kernels output <owner>/e1-evolve-pilot -p ./e1_out
# 1. repack export/step0 FIRST (the unmodified master through the same export code): K12 check
python3 aegis-forge/repack_ternary.py $EXPORT $ART --llama3-prune --max-seq 2048 --source-packing unpacked --scale-convention multiply
#    expect "weight_scale convention: multiply", "VOCAB.BIN: 50256 tokens, 110042 merges", "MODEL.SAF: 541 tensors"; VOCAB.BIN sha256 5bde1b0355ef99c6875190ebfff081d985ca48977ae9269e3477f5cc2d97d9ae
# 2. G1 against the Rust encode():
TOKENIZER_RS=aegis-core/src/tokenizer.rs rustc --edition 2024 -O tools/g1_encode_dump.rs -o g1_encode_dump
python3 tools/g1_rust_parity.py g1_vectors.jsonl $ART/VOCAB.BIN ./g1_encode_dump
# 3. identity: the digest must repeat (the incumbent's cab11400d737ac4a is NOT expected for a retrained or re-ternarized model)
cis_decode $ART/MODEL.SAF $ART/EMBED.BIN $ART/VOCAB.BIN 64 "Once upon a time"
# 4. receipted dev slice through the real gateway
cd alice-aegis/demo/agent-trace/eval
N=24 AEGIS_MODEL=$ART/MODEL.SAF AEGIS_EMBED=$ART/EMBED.BIN AEGIS_VOCAB=$ART/VOCAB.BIN AGENT_TRACE_BIN=../../../aegis-linux/target/release/examples/agent_trace \
  ./run_suite.sh $EXPORT/suite_e1_dev_P0.tsv /path/out_p0 --table $EXPORT/dev_table.tsv && python3 -I score.py /path/out_p0/summary.tsv
```
Run all of it on box1/box2 via `systemd-run` with raw logs under `state/reports/`, never on penguin (Rules A/B). Excluded from the TSV: FILE-READ, undeclared-tool and abstention items (`run_suite.sh` wires `--table` for LOOKUP only; `score.py` has no abstain rule - `score_ext.py` does not exist yet).
Weights, recipe and factory are `PUBLISH?` items: keep the export private.

## 5. What was verified here (Rule B) and what was not

**Verified while writing this (2026-10-07, CPU sandbox, no timing reported):**
* Smoke run: `E1_SMOKE=1 jupyter nbconvert --to notebook --execute` executes all 11 code cells with **zero errors** (single CPU thread by design: smoke sets `OMP_NUM_THREADS=1` and `torch.set_num_threads(1)` so it can share a box): a tiny random BitNet (2 layers, hidden 64, the real 128,256-row id layout), the real Llama-3 tokenizer, 1,200 episodes, 12 optimizer steps per arm, 48 dev items. Arms P, L, H train, evaluate, checkpoint, **pause and resume from disk (arm P)**, export, and the table is printed (`e1-evolve-pilot.smoke-executed.ipynb`). Statuses carry `[smoke]`; a random network fails the capability gates by design. What the smoke does show: the QAT forward equals the stock HF forward at step 0 (argmax disagreement 2.38% with the int8 head quantization, **0.00% with it off**, identical for arms P and L), batched left-padded generation equals single-sample generation (100%), the exported file reloads within a 0.2-1.9% PPL gap, and exported scales survive the real repacker unchanged.
* **G1:** the Python port of `AegisTokenizer::encode` vs the real Rust `encode()` (unmodified `tokenizer.rs`): 144,258 texts, 13,462,568 bytes (11 MB of generated episodes, 60,000 random ASCII strings with every whitespace class, the 60 LAB-07 suite prompts with and without the appended call/TOOL line, `ext_suite.tsv`, `ext_suite_t2.tsv`, `chain.tsv`, whitespace/number edge cases): **0 mismatches** [meas, `evidence/g1_rust_parity.log`]. `VOCAB.BIN` rebuilt from `tokenizer.json` has sha256 `5bde1b03...`, equal to the pinned incumbent.
* **G3** (needed for the factory, the plan's S1 gate): the Python gateway port vs the Rust `run_tool` family cut out of `agent_trace.rs`: 1,000,000 random and edge cases (140,480 calc, 27,952 calc-error, 180,942 lookup, 41,396 file-read, 609,230 no-tool): **0 mismatches** [meas, `evidence/g3_gateway_diff.log`].
* **QAT layer == Hugging Face's online BitLinear** (`AutoBitLinear`): output and both straight-through gradients identical (max abs difference 0.0 on a random fp32 layer with an outlier channel) [meas, printed by Cell 0]. On the whole tiny model (bf16-exact weights, fp32) the logits differ by at most 5.2e-6 with 100% argmax agreement when the head quantization is off, and 98.4% agreement with it on (the int8 head input is the one intended difference). With weights that are not bf16-exact the int8 roundings are chaotic: a 1e-6 summation-order difference can flip one activation rounding and move logits by 0.1, so exactness is a property of the checkpoint's grid, not just of the code.
* The **real `repack_ternary.py`** accepted the smoke export (`--scale-convention multiply`, `--llama3-prune`): 37 tensors for 2 layers (541 for 30), the `weight_scale` in `MODEL.SAF` equals the exported scale exactly, and its `VOCAB.BIN` equals the port's rebuild.

**Not verified (needs a GPU or the engine):** anything on CUDA - memory fit of arms L/H, `device_map=auto` plus post-load module replacement, gradient checkpointing under accelerate hooks, bitsandbytes `PagedAdamW8bit`, fp16 `GradScaler` behaviour, bf16 on a T4 for the stock reference, the real tokens/s; the HF-vs-engine PPL gap and `cis_decode` digests of any export; receipts through the real gateway; `score_ext.py` (abstain list, legality) does not exist; the 600-item frozen `evolve_suite_v2` is not built (the dev slice here is generated, about 50 per bucket).

### The three things most likely to break on a real GPU run
1. **Memory and speed of arms L/H.** About 24 GiB of fp32 weights + fp32 gradients + 8-bit Adam state across two 15 GiB T4s leaves little headroom; `device_map=auto` balances the *weights* only, so GPU 0 also carries the 1.3 GB embedding with its gradient and state. The pre-flight arithmetic skips an arm that cannot fit, but a borderline fit can still OOM during checkpointing or evaluation, bitsandbytes may not run on a P100 (the notebook probes it and falls back, which then skips L/H), and the real tokens/s may land below the plan's 450 tok/s re-plan line (K14) once fake-quant passes are added.
2. **Library integration I could only exercise on a CPU toy.** Transformers 5.x with `dtype=` and `device_map=auto`, replacing `nn.Linear` modules after dispatch, non-reentrant checkpointing through accelerate hooks, the KV-cache + left-padding generation path across two devices, and the stock `quantization_config` online reference loaded in fp32/bf16 on a T4 (bf16 is emulated there; a failure falls back to a non-independent step-0 snapshot and says so). Any of these can raise on the first real step.
3. **Numerics and the gates they feed.** fp16 autocast of a model trained in bf16: massive-activation channels can overflow (G12 and the GradScaler skip-step path are the guards; repeated skipped steps mean a scale problem). And the step-0 parity gate (<= 3%) may fail for a *numerical* reason - the int8 head-input quantization alone flips next-token argmax wherever the top-2 margin is small - which the attribution line printed at step 0 is there to separate from a real bug.

## 6. Honesty rules (also the last cell of the notebook)
Every number is a measurement made by the notebook in its session, or labelled; nothing is a product number; **Rule A:** no timing claim outside the GPU name / tokens-per-second logging lines; **Rule B:** every number traces to a log line, the dataset manifest, the held-out slice hash or an exported-file hash; the receipts for the eval items are produced by the Linux gateway, not by the notebook; a smoke run is not a measurement; the P0 reading and the base's lineage and tokenizer notice (file 03 A1-A4) remain open items for Justin.
