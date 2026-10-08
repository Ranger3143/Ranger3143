#!/usr/bin/env python3
"""finetune_tinybit.py - continue training a tinybit checkpoint on NEW packed data with a fresh short schedule.

tinybit's train.py has no "initialise from a checkpoint with a fresh optimizer / schedule" option (its --resume restores the
optimizer, the step counter and the two-stage schedule), so this entry point loads ONLY the model weights from the checkpoint and
runs the loop with tinybit's own model, optimizer factory and loss (nothing under alice-aegis is changed):

  * model / config           : tinybit model.py (TinyBitModel, TinyBitConfig) built from the checkpoint's own config
  * optimizer                : tinybit train.py make_optimizer (AdamW, betas 0.9/0.95, eps 1e-8; matrices decay, norms/embeddings do not)
  * loss                     : torch cross_entropy over the full vocabulary on the QAT forward, as train.py's train_loop
  * schedule (this file)     : linear warm-up to a CONSTANT peak lr; weight decay constant (0 for SAFE-04); grad-clip 1.0
  * data order (this file)   : --sampler epoch (default) = the first steps*batch non-overlapping blocks of --block tokens of the packed
                               stream, visited once each in a seeded random order (every token is a prediction target exactly once, so
                               every episode in the stream is seen exactly once); --sampler random = train.py's TokenDataset windows

Rule A: no wall-clock or throughput figure is printed or logged. The checkpoint written holds model + config + step + meta only
(no optimizer state), which is what eval_ops.py, export_hf.py and export_gate.py read.

usage: OMP_NUM_THREADS=4 python3 -I finetune_tinybit.py --init op12k.pt --data train_p5.bin --out safe04_p5.pt --val-data valid_op12k.bin
"""
import argparse
import hashlib
import json
import os
import random
import sys

sys.dont_write_bytecode = True
A = "/home/user/aefinity-ai/alice-aegis"
TINYBIT = f"{A}/model-lab/tinybit"
sys.path.insert(0, TINYBIT)

import numpy as np
import torch

from model import TinyBitConfig, TinyBitModel          # noqa: E402  (tinybit, read-only)
import train as T                                      # noqa: E402  (tinybit train.py: make_optimizer, set_optim_hparams, TokenDataset)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


@torch.no_grad()
def val_ppl(model, val, windows, block):
    """Mean next-token NLL over `windows` evenly spaced blocks of the held-out stream -> perplexity. QAT forward, like tinybit."""
    model.eval()
    starts = np.linspace(0, len(val) - block - 2, windows).astype(np.int64)
    x = torch.from_numpy(np.stack([val[s:s + block].astype(np.int64) for s in starts]))
    y = torch.from_numpy(np.stack([val[s + 1:s + 1 + block].astype(np.int64) for s in starts]))
    logits = model(x)
    nll = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.shape[-1]).float(), y.reshape(-1))
    model.train()
    return float(torch.exp(nll))


def lr_at(step, warmup, peak):
    return peak * step / max(1, warmup) if step < warmup else peak


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", required=True, help="tinybit .pt checkpoint to start from (model weights only are used)")
    ap.add_argument("--data", required=True, help="packed uint16 token stream (.bin from tinybit prepare_data.py)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--val-data", default=None, help="packed uint16 stream for the monitoring perplexity (not trained on)")
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("-B", "--batch", type=int, default=8)
    ap.add_argument("-T", "--block", type=int, default=512)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--wd", type=float, default=0.0)
    ap.add_argument("--grad-clip", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--log-every", type=int, default=20)
    ap.add_argument("--val-every", type=int, default=100)
    ap.add_argument("--val-windows", type=int, default=8)
    ap.add_argument("--sampler", choices=("epoch", "random"), default="epoch")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    torch.set_num_threads(a.threads)
    torch.manual_seed(a.seed)
    np.random.seed(a.seed)
    random.seed(a.seed)

    ck = torch.load(a.init, map_location="cpu", weights_only=False)
    cfg = TinyBitConfig(**ck["config"])
    model = TinyBitModel(cfg)
    model.load_state_dict(ck["model"])
    model.train()
    init_step = ck.get("step")
    print(f"[ft] tag={a.tag} init={a.init} init_sha256={sha256(a.init)} init_step={init_step}", flush=True)
    print(f"[ft] data={a.data} data_sha256={sha256(a.data)}", flush=True)
    print(f"[ft] params={model.num_params()} linear={cfg.linear} vocab={cfg.vocab_size} ctx={cfg.max_position_embeddings}", flush=True)
    print(f"[ft] steps={a.steps} batch={a.batch} block={a.block} lr={a.lr} warmup={a.warmup} (constant after) wd={a.wd} "
          f"clip={a.grad_clip} seed={a.seed} threads={a.threads} sampler={a.sampler} optimizer=tinybit make_optimizer (AdamW 0.9/0.95), fresh state", flush=True)

    data = np.memmap(a.data, dtype=np.uint16, mode="r")
    need = a.steps * a.batch
    n_blocks = (len(data) - 1) // a.block
    print(f"[ft] stream tokens={len(data)} usable blocks of {a.block}={n_blocks} needed={need}", flush=True)
    if a.sampler == "epoch":
        if n_blocks < need:
            sys.exit(f"[ft] stream too short for one epoch: {n_blocks} blocks < {need}")
        order = np.random.default_rng(a.seed).permutation(need)       # first `need` blocks, each once, seeded order
    else:
        ds = T.TokenDataset(a.data, a.block)
        rng = np.random.default_rng(a.seed)
    val = np.memmap(a.val_data, dtype=np.uint16, mode="r") if a.val_data else None

    opt = T.make_optimizer(model, a.lr, a.wd)
    if val is not None:
        print(f"  [val] step 0 (init) | val_ppl {val_ppl(model, val, a.val_windows, a.block):.3f}", flush=True)

    for step in range(a.steps):
        lr = lr_at(step, a.warmup, a.lr)
        T.set_optim_hparams(opt, lr, a.wd)
        if a.sampler == "epoch":
            js = order[step * a.batch:(step + 1) * a.batch]
            x = torch.from_numpy(np.stack([data[j * a.block:j * a.block + a.block].astype(np.int64) for j in js]))
            y = torch.from_numpy(np.stack([data[j * a.block + 1:j * a.block + 1 + a.block].astype(np.int64) for j in js]))
        else:
            x, y = ds.get_batch(a.batch, rng)
        logits = model(x)
        loss = torch.nn.functional.cross_entropy(logits.view(-1, cfg.vocab_size), y.view(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        gnorm = torch.nn.utils.clip_grad_norm_(model.parameters(), a.grad_clip)
        opt.step()
        if step % a.log_every == 0 or step == a.steps - 1:
            print(f"step {step:5d}/{a.steps} | loss {loss.item():.4f} | lr {lr:.2e} | wd {a.wd:.3f} | gnorm {float(gnorm):.2f}", flush=True)
        if val is not None and (step + 1) % a.val_every == 0:
            print(f"  [val] step {step + 1} | val_ppl {val_ppl(model, val, a.val_windows, a.block):.3f}", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    tmp = a.out + ".tmp"
    torch.save({"model": model.state_dict(), "config": cfg.as_dict(), "step": a.steps,
                "meta": {"tag": a.tag, "init": os.path.abspath(a.init), "init_step": init_step, "data": os.path.abspath(a.data),
                         "seed": a.seed, "lr": a.lr, "warmup": a.warmup, "wd": a.wd, "sampler": a.sampler}}, tmp)
    os.replace(tmp, a.out)
    print(f"[ft] saved {a.out} sha256={sha256(a.out)}", flush=True)
    print("[ft] done", flush=True)


if __name__ == "__main__":
    main()
