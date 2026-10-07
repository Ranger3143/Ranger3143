import json, struct, sys, urllib.request, numpy as np, torch
def rng(url, a, b):
    req = urllib.request.Request(url, headers={"Range": f"bytes={a}-{b}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()
def header(url):
    n = struct.unpack("<Q", rng(url, 0, 7))[0]
    h = json.loads(rng(url, 8, 8 + n - 1)); return h, 8 + n
def tensor(url, h, base, name):
    e = h[name]; a, b = e["data_offsets"]; return e, rng(url, base + a, base + b - 1)
bf = "https://huggingface.co/microsoft/bitnet-b1.58-2B-4T-bf16/resolve/main/model.safetensors"
pk = "https://huggingface.co/microsoft/bitnet-b1.58-2B-4T/resolve/main/model.safetensors"
hb, bb = header(bf)
print("bf16 tensors:", len(hb), [k for k in list(hb)[:6]])
hp, bp = header(pk)
print("packed tensors:", len(hp), [k for k in list(hp) if "layers.0." in k][:20])
for name in ["model.layers.0.self_attn.q_proj.weight", "model.layers.0.mlp.down_proj.weight", "model.layers.15.mlp.gate_proj.weight"]:
    e, raw = tensor(bf, hb, bb, name)
    w = torch.frombuffer(bytearray(raw), dtype=torch.bfloat16).float().reshape(e["shape"])
    g = w.abs().mean().item()
    wq = torch.round(w / g).clamp(-1, 1)
    print(name, e["dtype"], e["shape"], "mean|w|=%.6f" % g, "p0=%.4f" % (wq == 0).float().mean().item(), "max|w|=%.3f" % w.abs().max().item())
    sname = name + "_scale"
    if sname in hp:
        e2, raw2 = tensor(pk, hp, bp, sname)
        print("   packed", sname, e2["dtype"], e2["shape"], torch.frombuffer(bytearray(raw2), dtype=torch.bfloat16).float().tolist())
for name in ["model.layers.0.self_attn.attn_sub_norm.weight", "model.norm.weight", "model.layers.0.input_layernorm.weight"]:
    e, raw = tensor(bf, hb, bb, name)
    w = torch.frombuffer(bytearray(raw), dtype=torch.bfloat16).float()
    print(name, e["shape"], "mean %.4f min %.4f max %.4f" % (w.mean(), w.min(), w.max()))
print(json.dumps(hb.get("__metadata__")))
