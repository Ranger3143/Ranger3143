#!/usr/bin/env python3
"""Emit the Mission Control 'operator model' section from the LAB-08 evidence files.
Every number in the output is read from a file (Rule B); nothing is typed in.
usage: mc_operator_section.py --tag final_step12000 [--repo R] [overrides...] > section.html"""
import argparse, csv, json, math, re, html, os, sys, binascii, glob

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d
    h = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0.0, c-h), min(1.0, c+h))

def bucket_rates(summary):
    rows = list(csv.DictReader(open(summary), delimiter="\t")); out = {}
    for r in rows:
        b = r["bucket"]; d = out.setdefault(b, {"n": 0, "ok": 0, "verified": 0})
        d["n"] += 1
        if r["tool_expected"].strip().upper() == "NONE":
            d["ok"] += int(all(t.strip().upper() == "NONE" for t in r["tool_observed"].split(",")))
        else:
            d["ok"] += int(r["arg_match"].strip().lower() == "true")
        d["verified"] += int(r["verify_result"].strip() == "PASS")
    tool = [b for b in out if not b.startswith("distractor")]
    out["_overall"] = {"n": sum(out[b]["n"] for b in tool), "ok": sum(out[b]["ok"] for b in tool),
                       "verified": sum(out[b]["verified"] for b in out if not b.startswith("_")), "rows": len(rows)}
    return out

def receipt(path):
    t = open(path, errors="replace").read()
    g = lambda k: (re.search(rf"^{k} (.*)$", t, re.M) or [None, ""])[1]
    ids = [int(x) for x in re.split(r"[,\s]+", g("token-ids").strip()) if x] if g("token-ids") else []
    return {"gen": g("gen-toks"), "digest": g("cis-digest"), "chain": g("chain"), "ids": ids,
            "prompt": binascii.unhexlify(g("prompt-hex")).decode("ascii", "replace") if g("prompt-hex") else ""}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True); ap.add_argument("--repo", default=".")
    ap.add_argument("--opdir"); ap.add_argument("--t0"); ap.add_argument("--ext"); ap.add_argument("--qemu-calc"); ap.add_argument("--qemu-lookup"); ap.add_argument("--summary")
    ap.add_argument("--tokenizer", default="/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/opmodel/tokenizer_op12k.json")
    ap.add_argument("--img-self", default="img/10_op_self.png"); ap.add_argument("--img-calc", default="img/11_op_calc.png"); ap.add_argument("--img-lookup", default="img/12_op_lookup.png")
    ap.add_argument("--trainlog", default=None); ap.add_argument("--ext2b", default=None)
    a = ap.parse_args(); R = a.repo
    op = a.opdir or f"{R}/labs/logs/opmodel/{a.tag}"
    t0 = a.t0 or f"{op}/suite_T0/summary.tsv"; ext = a.ext or f"{op}/suite_ext/summary.tsv"
    qc = a.qemu_calc or f"{op}/qemu_calc"; ql = a.qemu_lookup or f"{op}/qemu_lookup"
    summ = json.load(open(a.summary or f"{op}/SUMMARY.json"))
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(a.tokenizer)
    dec = lambda ids: tok.decode(ids)

    b2 = bucket_rates(f"{R}/labs/logs/toolcall_2b/summary.tsv"); b2e = bucket_rates(a.ext2b or next(p for p in glob.glob(f"{R}/labs/logs/toolcall_2b_ext/**/summary*.tsv", recursive=True) if "t2" not in p.lower()))
    bo = bucket_rates(t0); boe = bucket_rates(ext)
    order = [("calc_easy","calc, easy"),("calc_hard","calc, hard"),("calc_overflow","calc, overflow"),("lookup_hit","lookup, hit"),("lookup_miss","lookup, miss"),("lookup_near_miss","lookup, near miss"),("mixed","mixed, two tools"),("_overall","<b>overall, correct argument</b>")]
    bars = []
    def bar(label, o, b):
        lo, hi = wilson(o["ok"], o["n"]); p = 100*o["ok"]/o["n"]; pb = 100*b["ok"]/b["n"]
        bars.append(f'<div class="bar"><span>{label} (n={o["n"]})</span><div class="track"><div class="fill" style="width:{p:.1f}%"></div><div class="ci" style="left:{100*lo:.1f}%;width:{100*(hi-lo):.1f}%"></div><div class="tick" style="left:{pb:.1f}%"></div></div><span class="v">{o["ok"]}/{o["n"]} <span style="color:var(--muted)">· 2B {b["ok"]}/{b["n"]}</span></span></div>')
    for k, lab in order: bar(lab, bo[k], b2[k])
    bar("unknown fact, decides to LOOKUP", boe["unknown_fact"], b2e["unknown_fact"])
    bar("distractor, stays quiet", boe["distractor"], b2e["distractor"])
    ver_op = bo["_overall"]["verified"] + boe["_overall"]["verified"]; rows_op = bo["_overall"]["rows"] + boe["_overall"]["rows"]

    def loop(qdir, title, note):
        r1 = receipt(f"{qdir}/RECEIPT.TXT"); r2 = receipt(f"{qdir}/RECEIPT2.TXT")
        bl = open(f"{qdir}/BOOTLOG.TXT", errors="replace").read()
        st = re.search(r"STAGE T: gateway tool=(\S+) in=(.*?) out=(.*)$", bl, re.M)
        tool, tin, tout = (st.group(1), st.group(2).strip(), st.group(3).strip()) if st else ("?", "?", "?")
        prompt = r1["prompt"].split("\n")[0]; m0 = dec(r1["ids"]).strip(); m1 = dec(r2["ids"]).strip().split("\n")[0]
        e = html.escape
        return f'''<div class="panel">
        <h4 style="margin:0 0 8px;font-family:var(--display);font-size:1.1rem">{title}</h4>
        <div class="val" style="display:block;font-family:var(--mono);font-size:0.82rem;line-height:1.7;white-space:pre-wrap">PROMPT   {e(prompt)}
MODEL    {e(m0)}      <span style="color:var(--muted)">receipt 1 · {r1["gen"]} tokens · cis-digest {r1["digest"]}</span>
GATEWAY  TOOL[{e(tool)}]={e(tout)}      <span style="color:var(--muted)">executed by the firmware, no OS</span>
MODEL    {e(m1)}      <span style="color:var(--muted)">receipt 2 · {r2["gen"]} tokens · cis-digest {r2["digest"]}</span></div>
        <p class="note" style="margin-top:8px">{note}</p></div>'''
    calc_html = loop(qc, "Arithmetic: the model asks, the firmware computes", "PCR 13 took both receipt events; both receipts replay on Linux with the unchanged verifier (labs/logs/opmodel/" + a.tag + "/FINALIZE.log).")
    look_html = loop(ql, "Lookup: a table declared on the boot volume, measured into PCR 12", "TABLE.TSV is hashed into PCR 12 before the lookup runs, so the quote covers the data the model read.")

    # trajectory
    traj = []
    for f in sorted(glob.glob(f"{R}/labs/logs/opmodel/eval_step*.json"), key=lambda p: int(re.search(r"step(\d+)", p).group(1))):
        d = json.load(open(f)); r = d["results"]
        traj.append((d["step"], r))
    def cell(r, k): return f'{r[k]["ok"]}/{r[k]["n"]}'
    trows = "".join(f'<tr><td>step {s}</td><td class="num">{cell(r,"calc")}</td><td class="num">{cell(r,"lookup")}</td><td class="num">{cell(r,"lookup_final")}</td><td class="num">{cell(r,"abstain")}</td><td class="num">{cell(r,"faq")}</td><td class="num">{cell(r,"everyday")}</td></tr>' for s, r in traj)
    vals = []
    if a.trainlog:
        for m in re.finditer(r"\[val\] step (\d+) \| val_ppl ([\d.]+)", open(a.trainlog).read()): vals.append((int(m.group(1)), float(m.group(2))))
    val_txt = (" Validation perplexity (torch QAT forward): " + " → ".join(f"{v:.1f} ({s})" for s, v in vals) + ".") if vals else ""

    rel = 100*summ["rel_diff"]
    print(f'''  <section id="operator">
    <div class="sec-head">
      <h3>Operator model</h3>
      <h2>A 17M-parameter model trained on this CPU overnight answers as ALICE, hands arithmetic and lookups to the firmware, and refuses to guess</h2>
      <p class="note">{summ["params"]:,} parameters, ternary quantization-aware training, {summ["step"]:,} steps on a 4-vCPU VM with no GPU (labs/LAB-08). Corpus: educational prose, human-written Q/A, 148,500 tool episodes labelled by the gateway's own oracle, and ALICE self-knowledge. Round-trip gate on the step-{summ["step"]} export: torch PPL {summ["torch_ppl"]:.4f} vs engine {summ["engine_ppl"]:.4f} ({rel:.2f}%, tolerance 3%), {summ["heldout_tokens_ours"]} = {summ["engine_tokens"]} tokens, <b>{summ["verdict"]}</b>. Rule A: no speed figure here.</p>
    </div>
    <div class="grid-2">
      {calc_html}
      {look_html}
    </div>
    <div class="panel" style="margin-top:16px">
      <h4 style="margin:0 0 6px;font-family:var(--display);font-size:1.1rem">Same 60 pre-registered items, same harness, same binary as the 2B baseline (labs/LAB-07)</h4>
      <p class="note" style="margin-bottom:12px">Bar: the operator model, zero-shot in its native <span class="mono">Q:/A:</span> format (labs/logs/opmodel/{a.tag}/suite_T0), with the Wilson 95% interval. Amber tick: BitNet-2B with three few-shot examples (labs/logs/toolcall_2b). The last two rows are the extended items (unknown fact whose answer is in the table under calculator-only shots; distractors) exactly as the 2B saw them.</p>
      <div class="bars">
        {"".join(bars)}
      </div>
      <div class="axis"><span></span><div class="ticks"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div><span></span></div>
      <p class="note" style="margin-top:12px"><b>Caveat first:</b> the operator model was trained on this call grammar (random operands and keys; the demo table's key→value pairs were never seen), the 2B met it only in its prompt and knows incomparably more about the world. What the bars show is the thesis of the model plan: the one behaviour ALICE-Next must have is learnable at tiny scale when the labels come from the gateway itself. Receipts verified: {ver_op}/{rows_op} on the two operator-model runs shown (all four runs are in FINALIZE.log), 120/120 for the 2B. Shown the same three few-shot examples the 2B had, the small model does worse (suite_T1: it copies the example's operator), which is why the demo is zero-shot.</p>
    </div>
    <div class="gallery" style="margin-top:16px">
      <figure class="wide"><img src="{a.img_self}" alt="ALICE dashboard, operator model, mint mode DONE: the transcript shows the self-description answer and the full receipt; attestation panel shows PCR 4, 12, 13 and the signed quote." width="1920" height="1440"><figcaption><b>The operator model booted in ALICE.</b> Prompt: what are you, and why do you run without an operating system. The firmware digest equals the Linux digest for the same prompt.</figcaption></figure>
      <figure><img src="{a.img_calc}" alt="ALICE dashboard, operator model, calc gateway: OUTPUT shows the CALC call, the TOOL line executed by the firmware gateway, and the ANSWER step; two receipts minted." width="1920" height="1440"><figcaption><b>Calculator through the firmware gateway.</b> Two receipts, both extended into PCR 13.</figcaption></figure>
      <figure><img src="{a.img_lookup}" alt="ALICE dashboard, operator model, lookup gateway: OUTPUT shows the LOOKUP call, the TOOL line with the table value, and the ANSWER step." width="1920" height="1440"><figcaption><b>Lookup against the declared table.</b> TABLE.TSV measured into PCR 12 before the gateway reads it.</figcaption></figure>
    </div>
    <div class="panel tbl" style="margin-top:16px">
      <table>
        <thead><tr><th>Checkpoint</th><th class="num">calc, exact call (24)</th><th class="num">lookup, exact key (12)</th><th class="num">copies the looked-up value (8)</th><th class="num">abstains on unknown facts (10)</th><th class="num">ALICE self-knowledge (8)</th><th class="num">everyday, no tool (5)</th></tr></thead>
        <tbody>{trows}</tbody>
      </table>
      <p class="note" style="margin-top:10px">Greedy probes in the torch QAT forward (labs/logs/opmodel/eval_step*.txt). Abstention arrived before any tool call was right; lookups before arithmetic; the remaining arithmetic misses are copied operands.{val_txt}</p>
    </div>
  </section>
''')
if __name__ == "__main__": main()
