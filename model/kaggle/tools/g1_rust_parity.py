#!/usr/bin/env python3
"""G1 parity: token ids written by the e1-evolve-pilot notebook (g1_vectors.jsonl, from its Python port of AegisTokenizer::encode)
versus the ids the real Rust encode() produces for the same texts over the same VOCAB.BIN.

  python3 g1_rust_parity.py g1_vectors.jsonl VOCAB.BIN ./g1_encode_dump

Exit code 0 only when every text matches. The gate (design 01 G1 / plan 02 S1b) asks for 100% on >= 10 MB of mixed ASCII text plus every gateway
template; g1_vectors.jsonl is a sample of the training episodes plus the documented skew cases, so run the notebook's `--g1-vectors` size up
(CFG["g1_vectors"]) or add a larger corpus file in the same format to cover the 10 MB.
"""
import hashlib, json, subprocess, sys

vec_path, vocab_path, exe = sys.argv[1:4]
rows = [json.loads(l) for l in open(vec_path) if l.strip()]
hexlines = "\n".join(r["text_hex"] for r in rows) + "\n"
p = subprocess.run([exe, vocab_path], input=hexlines.encode(), capture_output=True)
if p.returncode != 0:
    sys.exit(f"encoder failed: {p.stderr.decode()[:300]}")
got = p.stdout.decode().split("\n")[:-1]
assert len(got) == len(rows), (len(got), len(rows))
bad = [i for i, (r, g) in enumerate(zip(rows, got)) if ",".join(map(str, r["ids"])) != g]
nbytes = sum(len(r["text_hex"]) // 2 for r in rows)
print(f"VOCAB.BIN sha256 {hashlib.sha256(open(vocab_path, 'rb').read()).hexdigest()}")
print(f"G1 parity vs Rust encode(): texts={len(rows)} bytes={nbytes} mismatches={len(bad)}")
for i in bad[:5]:
    print("  MISMATCH", bytes.fromhex(rows[i]["text_hex"])[:80], rows[i]["ids"][:20], got[i][:80])
sys.exit(1 if bad else 0)
