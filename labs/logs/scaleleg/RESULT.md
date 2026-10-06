# scaleleg: regenerated double-reciprocal scale leg (BitNet-b1.58-2B-4T, CIS-1 FullInt)

Date: 2026-10-06. Identity/sensitivity check only. No timing is recorded anywhere in this directory (Rule A).
Purpose: regenerate the missing raw log for LAB-02 Result 3 (scale copied as 1/(1/s) gives coherent text but a different digest).

## What was changed
- Source (read only, hash re-verified after the runs): `bitnet2b_fixed/MODEL.SAF`, sha256 `1101e472e41a012e4b1efdc124511461307f4e0e1b540a8e45c24d3d33e0c9eb` (exact-scale artifact).
- New file: `bitnet2b_dblrecip/MODEL.SAF` (521,953,186 B, same length as source), sha256 `40f8c585e50a969f2993da3ba8362b1868f48c3e01b79a4f9e1f43119dfa63bf`.
- Tensors rewritten: all **210** per-tensor scale scalars, i.e. every `model.layers.{0..29}.{self_attn.{q,k,v,o}_proj | mlp.{gate,up,down}_proj}.weight_scale` (30 layers x 7 projections; all dtype F32, shape [1]; confirmed from the header, no other tensor name ends in `_scale`).
- Operation: `new = f32(1.0 / f32(1.0 / s))` in numpy float32, both divisions rounded to f32.
  - f32 division was checked to equal f64 division rounded to f32 for all 210 values.
  - The first step reproduces, bit for bit, the scales stored in the as-shipped reciprocal artifact (`bitnet2b/MODEL.SAF`, sha256 9d1fa769...). So the double-reciprocal leg equals "invert the as-shipped scales again".
- Perturbation statistics:
  - scales rewritten: 210
  - scales whose f32 bit pattern actually changed: **31** (the other 179 round-trip exactly)
  - every change is exactly 1 ulp (ulp histogram: 0 ulp x179, 1 ulp x31)
  - max absolute change: **2.384185791e-07** (model.layers.6.self_attn.v_proj.weight_scale)
  - max relative change: **8.030941612e-08** (model.layers.2.self_attn.k_proj.weight_scale)
  - scale range (before): 0.74609375 .. 4.59375
  - changed scales by projection: v_proj 10, q_proj 6, gate_proj 6, up_proj 3, k_proj 3, down_proj 2, o_proj 1 (of 30 each)
- Byte-level check (source vs new, full-file compare): total length equal; 8-byte header length plus header JSON bytes identical; all bytes outside the 210 4-byte scale slots identical; the only differing bytes (71 of them) lie inside scale slots; slot contents equal the intended new values.

## Digests (same session, same decoder binary, same EMBED.BIN and VOCAB.BIN, prompt "Once upon a time", 64 tokens)
| leg | MODEL.SAF sha256 | CIS_DECODE digest |
|---|---|---|
| control: bitnet2b_fixed (exact scales) | 1101e472...c9eb | **cab11400d737ac4a** (equals the ledger pin, as expected) |
| double reciprocal | 40f8c585...63bf | **803e07941964ed37** |

The double-reciprocal digest **equals LAB-02's 803e07941964ed37**. Nothing was forced; this is the value the decoder printed.

Generated token ids agree for the first 5 generated tokens ([11, 304, 264, 2678, 6424]) and first diverge at generated index 5 (control 2663 " called", double-reciprocal 11 ","). Both texts are coherent English.

First 200 characters of each output text:
- control: `, in a small town called Greenfield, there lived a young girl named Lily. Lily was a curious and intelligent girl who loved to explore and learn new things. She was always eager to discover the secre`
- double reciprocal: `, in a small town, there was a young girl named Lily. She was known for her curiosity and love for learning. One day, her teacher, Mrs. Johnson, announced that there would be a special event at the l`

Reading: a 1-ulp (<= 8.1e-8 relative) change in 31 of 210 per-tensor scales, with every ternary weight and every other byte unchanged, moves a greedy token at a near-tie (index 5) and so changes the digest, while the text stays fluent. This supports the "exactness matters to the last mantissa bit" claim in LAB-02 Result 3. It also means a tolerance-based comparison would have passed this artifact.

## Caveats and provenance
- The decoder binary on disk has sha256 `bef74a017cf5a718116b715528de4f53b9c05dab9455148fa74905c995bc8d5d`. This differs from the fingerprint recorded in LAB-02 (`fed52f0f...`). By file mtime (14:15) it was built shortly after repo commit a7991b8 ("CIS-1 VNNI kernel, row-parallel integer decode ..."); alice-aegis HEAD is now a8db6a4. The build provenance was not independently checked. The control leg reproduces cab11400d737ac4a with this binary in the same session, and both legs use the identical binary, so the comparison here is internally consistent.
- Single run per leg. The decode is deterministic by design; no repeat runs were made.
- `make_dblrecip.py`: after the run I changed one line (OUTDIR) so that `scale_stats.json` and `scales.tsv` land in this directory rather than next to the output MODEL.SAF; I moved the two files here by hand. Nothing else in the script changed since the run. The script refuses to overwrite an existing output file.
- Nothing under /home/user/aefinity-ai or /home/user/Ranger3143 was modified (only read; the repo git state was queried read-only). The artifact hashes before and after the runs are in `artifact_sha256_before.txt` and `artifact_sha256_after.txt`.

## Files in this directory
- `make_dblrecip.py` and `make_dblrecip.log` (script and its console output)
- `bitnet2b_dblrecip/MODEL.SAF` (new artifact)
- `scale_stats.json`, `scales.tsv` (per-scale old/new f32 hex and values, 210 rows)
- `cis_decode_2b_dblrecip_scaleleg.log` (double-reciprocal raw log; header lines list the three artifact sha256s, decoder sha256 and exact command)
- `cis_decode_2b_fixed_control_scaleleg.log` (control raw log, same header)
- `raw_control.out`, `raw_dblrecip.out`, `raw_dblrecip.err` (verbatim stdout/stderr of the two decoder runs; stderr empty; stdout had no timing lines)
- `artifact_sha256_before.txt`, `artifact_sha256_after.txt`

## Exact commands
```
S=/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/scaleleg
A=/tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/artifacts
D=/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/cis_decode
python3 -I $S/make_dblrecip.py $A/bitnet2b_fixed/MODEL.SAF $S/bitnet2b_dblrecip/MODEL.SAF $A/bitnet2b/MODEL.SAF
$D $A/bitnet2b_fixed/MODEL.SAF $A/bitnet2b_fixed/EMBED.BIN $A/bitnet2b_fixed/VOCAB.BIN 64 "Once upon a time"        # control
$D $S/bitnet2b_dblrecip/MODEL.SAF $A/bitnet2b_fixed/EMBED.BIN $A/bitnet2b_fixed/VOCAB.BIN 64 "Once upon a time"   # double reciprocal
```
