#!/usr/bin/env python3
"""Checkpoint -> HF export -> repack -> engine round-trip gate -> demo assets.

Mirrors tinybit/roundtrip_gate.py for an arbitrary checkpoint:
  (a) torch QAT teacher-forced PPL on an ASCII held-out slice that MIXES an
      episode document (Q:/A:/TOOL lines) with prose, so the engine's tokenizer
      parity is tested on exactly the text shapes the demo will feed it;
  (b) export_hf.py -> repack_ternary.py (--scale-convention reciprocal, which is
      what `auto` resolves to for a tinybit export: no quantization_config);
  (c) aegis-eval PPL on the same slice; token-count parity; 3% tolerance;
  (d) cis_decode on demo prompts (digest + text) with the engine;
  (e) asset directories for the QEMU boot (MODEL.SAF/EMBED.BIN/VOCAB.BIN + MINT.TXT).
Rule A: nothing here reports timing.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys

TINYBIT = "/home/user/aefinity-ai/alice-aegis/model-lab/tinybit"
REPACK = "/home/user/aefinity-ai/alice-aegis/aegis-forge/repack_ternary.py"
AEGIS_EVAL = "/home/user/aefinity-ai/alice-aegis/aegis-eval/target/release/aegis-eval"
CIS_DECODE = "/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/cis_decode"

DEMO_PROMPTS = {
    "self": (64, "Q: What are you, and why do you run without an operating system?\nA:"),
    "receipt": (64, "Q: What is a receipt, and how can someone check what you said?\nA:"),
    "calc": (24, "Q: What is 1234 * 5678?\nA:"),
    "calc_words": (24, "Q: Multiply 365 by 24.\nA:"),
    "lookup": (24, "Q: What is part P-205?\nA:"),
    "lookup_final": (40, "Q: What is part P-205?\nA: LOOKUP(P-205).\nTOOL[lookup]=Bolt, hex head, 3/8-16 x 1 in., cadmium plated\n"),
    "abstain": (48, "Q: What is the population of Springfield?\nA:"),
    "everyday": (24, "Q: What is the capital of France?\nA:"),
    "unknown_tool": (40, "Q: Who built you?\nA:"),
}

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def run(cmd, log, env=None):
    log(f"$ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = r.stdout + r.stderr
    for line in out.strip().splitlines()[-12:]:
        log("  | " + line[:200])
    return r.returncode, out

def build_heldout(tok, valid_txt, ctx, k_target=480):
    raw = open(valid_txt, encoding="ascii", errors="ignore").read()
    docs = [d.strip() for d in raw.split("<|endoftext|>") if d.strip()]
    episode = next(d for d in docs if "TOOL[" in d)
    faq = next(d for d in docs if d.startswith("Q: ") and "TOOL[" not in d and len(d) > 150)
    prose = next(d for d in docs if not d.startswith("Q: ") and len(d) > 800)
    chunk = episode + "\n" + faq + "\n" + prose
    chunk = "".join(c for c in chunk if ord(c) < 128)
    ids = tok.encode(chunk, add_special_tokens=False).ids[: min(k_target, ctx - 16)]
    # aegis-eval --sample scores at most max_tokens*4 CHARACTERS (sample_tokens in
    # aegis-eval/src/main.rs), so keep the slice inside that budget or the two
    # stacks score different windows.
    while True:
        text = "".join(c for c in tok.decode(ids) if ord(c) < 128)
        if len(text) <= ctx * 4 - 8 or len(ids) < 64:
            break
        ids = ids[:-8]
    re_ids = tok.encode(text, add_special_tokens=False).ids
    return re_ids, text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--tokenizer", default=os.path.join(os.path.dirname(__file__), "tokenizer_op12k.json"))
    ap.add_argument("--valid-txt", default=os.path.join(os.path.dirname(__file__), "corpus", "valid.txt"))
    ap.add_argument("--out-root", default=os.path.join(os.path.dirname(__file__), "exports"))
    ap.add_argument("--max-seq", type=int, default=512)
    ap.add_argument("--tol", type=float, default=0.03)
    ap.add_argument("--skip-decode", action="store_true")
    a = ap.parse_args()

    out = os.path.join(a.out_root, a.name); os.makedirs(out, exist_ok=True)
    logf = open(os.path.join(out, "GATE.log"), "w")
    def log(s):
        print(s); logf.write(s + "\n"); logf.flush()

    import torch
    sys.path.insert(0, TINYBIT)
    from model import TinyBitConfig, TinyBitModel, teacher_forced_ppl
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(a.tokenizer)
    ck = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    cfg = TinyBitConfig(**ck["config"]); model = TinyBitModel(cfg); model.load_state_dict(ck["model"]); model.eval()
    torch.set_num_threads(2)
    log(f"[gate] ckpt={a.ckpt} step={ck.get('step')} params={sum(p.numel() for p in model.parameters())}")

    ids, text = build_heldout(tok, a.valid_txt, cfg.max_position_embeddings)
    heldout = os.path.join(out, "heldout.txt"); open(heldout, "w", encoding="ascii").write(text)
    torch_ppl = teacher_forced_ppl(model, torch.tensor(ids, dtype=torch.long))
    log(f"[a] heldout {len(text)} chars -> {len(ids)} tokens (ours); torch QAT PPL {torch_ppl:.4f}")

    hf = os.path.join(out, "hf"); art = os.path.join(out, "artifacts")
    shutil.rmtree(hf, ignore_errors=True); shutil.rmtree(art, ignore_errors=True)
    rc, _ = run([sys.executable, os.path.join(TINYBIT, "export_hf.py"), a.ckpt, hf, "--tokenizer", a.tokenizer], log)
    if rc: log("GATE FAIL: export"); sys.exit(1)
    rc, _ = run([sys.executable, REPACK, hf, art, "--max-seq", str(a.max_seq), "--scale-convention", "reciprocal", "--chat-template", "none"], log)
    if rc: log("GATE FAIL: repack"); sys.exit(1)
    files = {f: (os.path.getsize(os.path.join(art, f)), sha(os.path.join(art, f))) for f in ("MODEL.SAF", "EMBED.BIN", "VOCAB.BIN")}
    for f, (n, h) in files.items(): log(f"[b] {f}: {n} bytes sha256 {h}")

    rc, o = run([AEGIS_EVAL, os.path.join(art, "MODEL.SAF"), os.path.join(art, "EMBED.BIN"), os.path.join(art, "VOCAB.BIN"), heldout, str(cfg.max_position_embeddings), "--sample"], log)
    m_tok = re.search(r"->\s*(\d+)\s*tokens", o); m_ppl = re.search(r"Perplexity \(teacher-forced,\s*(\d+)\s*tokens\):\s*([\d.]+)", o)
    if rc or not (m_tok and m_ppl): log("GATE FAIL: aegis-eval output not parsed"); sys.exit(1)
    eng_tokens, eng_ppl = int(m_tok.group(1)), float(m_ppl.group(2))
    rel = abs(torch_ppl - eng_ppl) / max(eng_ppl, 1e-9)
    parity = eng_tokens == len(ids)
    log(f"[c] engine tokens {eng_tokens} (ours {len(ids)}, parity={parity}); engine PPL {eng_ppl:.4f}; rel diff {rel*100:.2f}% (tol {a.tol*100:.0f}%)")
    verdict = "PASS" if (rel <= a.tol and parity) else "FAIL"
    log(f">>> ROUND-TRIP GATE {verdict} <<<")

    decodes = {}
    if not a.skip_decode:
        for key, (n, prompt) in DEMO_PROMPTS.items():
            rc, o = run([CIS_DECODE, os.path.join(art, "MODEL.SAF"), os.path.join(art, "EMBED.BIN"), os.path.join(art, "VOCAB.BIN"), str(n), prompt], log)
            dig = re.search(r"digest=([0-9a-f]{16})", o); txt = re.search(r"^text\s*:\s*(.*)$", o, re.M)
            decodes[key] = {"max_new": n, "prompt": prompt, "digest": dig.group(1) if dig else None, "text": txt.group(1) if txt else None}
            log(f"[d] {key}: digest {decodes[key]['digest']} text {decodes[key]['text']}")
    # assets for QEMU: one directory per demo prompt
    assets_root = os.path.join(out, "assets"); os.makedirs(assets_root, exist_ok=True)
    for key, (n, prompt) in DEMO_PROMPTS.items():
        if key == "lookup_final": continue
        d = os.path.join(assets_root, key); os.makedirs(d, exist_ok=True)
        for f in ("MODEL.SAF", "EMBED.BIN", "VOCAB.BIN"):
            if not os.path.exists(os.path.join(d, f)): os.link(os.path.join(art, f), os.path.join(d, f))
        open(os.path.join(d, "MINT.TXT"), "w", encoding="ascii").write(f"{n}\n{prompt}\n")
    summary = {"ckpt": a.ckpt, "step": ck.get("step"), "params": sum(p.numel() for p in model.parameters()),
               "heldout_tokens_ours": len(ids), "engine_tokens": eng_tokens, "torch_ppl": torch_ppl, "engine_ppl": eng_ppl,
               "rel_diff": rel, "tolerance": a.tol, "token_parity": parity, "verdict": verdict, "artifacts": files, "decodes": decodes,
               "assets": assets_root}
    json.dump(summary, open(os.path.join(out, "SUMMARY.json"), "w"), indent=1)
    log(f"[done] {os.path.join(out, 'SUMMARY.json')}")
    sys.exit(0 if verdict == "PASS" else 2)

if __name__ == "__main__":
    main()
