#!/usr/bin/env python3
"""Checkpoint probe for the ALICE demo operator model: greedy decode on a fixed
prompt suite with the torch QAT model (same numerics the engine will replay
up to BF16 embedding drift). Reports behaviour rates, never timing.

Buckets:
  calc      -> expects the exact call "CALC(a op b)." as the first thing after "A:"
  lookup    -> expects "LOOKUP(<key>)." first
  lookup_final -> given the TOOL line, expects the final sentence to contain the value
  abstain   -> expects an abstention phrase and no tool call
  faq       -> prints the answer (judged by eye); checks no tool call
  everyday  -> expects a short inline answer, no tool call
"""
import argparse, json, random, re, sys, torch

def load(ckpt_path, tinybit_dir):
    sys.path.insert(0, tinybit_dir)
    from model import TinyBitConfig, TinyBitModel
    ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    cfg = TinyBitConfig(**ck["config"])
    m = TinyBitModel(cfg); m.load_state_dict(ck["model"]); m.eval()
    return m, cfg, ck.get("step")

@torch.no_grad()
def greedy(m, tok, prompt, max_new, ctx):
    ids = tok.encode(prompt, add_special_tokens=False).ids
    out = []
    for _ in range(max_new):
        x = torch.tensor([ids[-ctx:]], dtype=torch.long)
        o = m(x); logits = o[0] if isinstance(o, tuple) else o
        nxt = int(torch.argmax(logits[0, -1]))
        if nxt == 0:  # <|endoftext|>
            break
        ids.append(nxt); out.append(nxt)
    return tok.decode(out)

def build_suite(seed=20261007):
    rng = random.Random(seed)
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    import gen_episodes as g
    suite = []
    for _ in range(24):
        op = rng.choice(g.OPS); a = rng.randint(0, 9999); b = rng.randint(1, 999)
        if rng.random() < 0.3: a = rng.randint(-10**6, 10**6)
        q = rng.choice(g.CALC_Q).format(a=a, b=b, op=op, w=rng.choice(g.OP_WORDS[op]), n=g.OP_NAME[op])
        suite.append(("calc", f"Q: {q}\nA:", f"CALC({a} {op} {b})."))
    for _ in range(12):
        k = g.rand_key(rng); q = rng.choice(g.LOOKUP_Q).format(k=k)
        suite.append(("lookup", f"Q: {q}\nA:", f"LOOKUP({k})."))
    for _ in range(8):
        k = g.rand_key(rng); v = g.rand_value(rng); q = rng.choice(g.LOOKUP_Q).format(k=k)
        suite.append(("lookup_final", f"Q: {q}\nA: LOOKUP({k}).\nTOOL[lookup]={v}\n", v))
    for _ in range(10):
        suite.append(("abstain", "Q: " + rng.choice(g.ABSTAIN_Q).format(place="Oakdale", place2="Riverton", person="Dr. Okafor", org="the parts depot", ticker="ACME", unit="unit 4", year=2019, event="fleet safety award", acct=4411902, thing="tires") + "\nA:", "not in my data|in my data|don't know|don't have that|can't answer|won't guess|will not guess|rather say so|not make it up|won't make it up"))
    for q in ["What are you?", "Do you have an operating system?", "What is a receipt?", "Who built you?", "What is CIS-1?", "Why do you use a calculator?", "What happens when you don't know something?", "What is the TPM for?"]:
        suite.append(("faq", f"Q: {q}\nA:", ""))
    for q in ["What is the capital of France?", "How many legs does a spider have?", "Hello.", "What do bees make?", "Thanks!"]:
        suite.append(("everyday", f"Q: {q}\nA:", ""))
    return suite

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--tinybit", default="/home/user/aefinity-ai/alice-aegis/model-lab/tinybit")
    ap.add_argument("--max-new", type=int, default=48)
    ap.add_argument("--show", type=int, default=3, help="examples to print per bucket")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(a.tokenizer)
    m, cfg, step = load(a.ckpt, a.tinybit)
    torch.set_num_threads(1)
    suite = build_suite()
    res = {}; shown = {}
    for bucket, prompt, expect in suite:
        out = greedy(m, tok, prompt, a.max_new, cfg.max_position_embeddings)
        first = out.strip().split("\n")[0].strip()
        has_call = bool(re.search(r"\b(CALC|LOOKUP|FILE-READ)\(", out))
        if bucket in ("calc", "lookup"):
            ok = first == expect
        elif bucket == "lookup_final":
            ok = (expect in out.split("\n")[0]) and not has_call
        elif bucket == "abstain":
            ok = bool(re.search(expect, out, re.I)) and not has_call
        else:
            ok = (not has_call) and len(first) > 0
        r = res.setdefault(bucket, {"n": 0, "ok": 0}); r["n"] += 1; r["ok"] += int(ok)
        if shown.get(bucket, 0) < a.show or (bucket in ("calc", "lookup") and not ok and shown.get(bucket + "_miss", 0) < 2):
            shown[bucket] = shown.get(bucket, 0) + 1
            if not ok and bucket in ("calc", "lookup"): shown[bucket + "_miss"] = shown.get(bucket + "_miss", 0) + 1
            print(f"[{bucket}{'' if ok else ' MISS'}] {prompt.splitlines()[0][:70]!r}\n    -> {out.strip()[:220]!r}")
    print(f"\nstep={step} params={sum(p.numel() for p in m.parameters())/1e6:.2f}M")
    for b, r in res.items():
        print(f"  {b:13s} {r['ok']}/{r['n']}")
    if a.json:
        json.dump({"step": step, "results": res}, open(a.json, "w"), indent=1)

if __name__ == "__main__":
    main()
