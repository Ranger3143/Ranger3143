#!/usr/bin/env python3
"""Build the operator-model corpus: OASST2 (human Q/A, Apache-2.0) + Cosmopedia-v2
(educational text, ODC-By, Mixtral-generated) + gateway-verified episodes + ALICE FAQ.
ASCII only (the engine evaluator drops non-ASCII; the tokenizer parity contract is ASCII).
Writes train.txt / valid.txt with documents separated by a blank line, plus MANIFEST.json.
"""
import argparse, gzip, hashlib, json, os, random, re, sys, unicodedata

ASCII_MAP = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
             "…": "...", " ": " ", "•": "-", "·": "-", "′": "'", "″": '"',
             "é": "e", "è": "e", "ê": "e", "á": "a", "à": "a", "ó": "o",
             "ú": "u", "í": "i", "ñ": "n", "ü": "u", "ö": "o", "ä": "a", "ç": "c"}

def to_ascii(s):
    s = "".join(ASCII_MAP.get(ch, ch) for ch in s)
    s = unicodedata.normalize("NFKD", s)
    try:
        s.encode("ascii"); return s
    except UnicodeEncodeError:
        return None

def clean_ws(s):
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    s = re.sub(r"[ ]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def oasst_pairs(path, max_prompt_words=70, max_answer_words=120):
    msgs = {}
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            if m.get("deleted") or m.get("lang") != "en":
                continue
            msgs[m["message_id"]] = m
    pairs = []
    for m in msgs.values():
        if m.get("role") != "assistant" or not m.get("parent_id"):
            continue
        if m.get("review_result") is False:
            continue
        rank = m.get("rank")
        if rank not in (None, 0):
            continue
        p = msgs.get(m["parent_id"])
        if not p or p.get("role") != "prompter":
            continue
        q = to_ascii(clean_ws(p["text"])); a = to_ascii(clean_ws(m["text"]))
        if not q or not a:
            continue
        if "```" in a or "http" in a or "http" in q:
            continue
        if len(q.split()) > max_prompt_words or len(a.split()) > max_answer_words or len(a.split()) < 2:
            continue
        q = " ".join(q.split("\n")); a = " ".join(x.strip() for x in a.split("\n") if x.strip())
        pairs.append(f"Q: {q}\nA: {a}\n")
    return pairs

def cosmopedia_docs(path, target_bytes, max_doc_chars=6000):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    out, total = [], 0
    cols = [c for c in ("text",) if c in pf.schema.names]
    for batch in pf.iter_batches(batch_size=2000, columns=cols):
        for t in batch.column("text").to_pylist():
            if not t:
                continue
            t = clean_ws(t)
            if len(t) > max_doc_chars:
                # cut at a paragraph boundary
                cut = t.rfind("\n\n", 0, max_doc_chars)
                t = t[: cut if cut > 1000 else max_doc_chars]
            t = to_ascii(t)
            if not t or len(t) < 400:
                continue
            out.append(t + "\n"); total += len(t)
            if total >= target_bytes:
                return out
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oasst", required=True)
    ap.add_argument("--cosmo", required=True)
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--faq", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--cosmo-bytes", type=int, default=110_000_000)
    ap.add_argument("--oasst-repeat", type=int, default=2)
    ap.add_argument("--faq-repeat", type=int, default=8)
    ap.add_argument("--valid-frac", type=float, default=0.01)
    ap.add_argument("--seed", type=int, default=20261007)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    os.makedirs(a.out_dir, exist_ok=True)

    def split_docs(text):
        return [d.strip() + "\n" for d in text.split("\n\n") if d.strip()]

    sources = {}
    sources["oasst2"] = oasst_pairs(a.oasst)
    sources["cosmopedia"] = cosmopedia_docs(a.cosmo, a.cosmo_bytes)
    sources["episodes"] = split_docs(open(a.episodes, encoding="ascii").read())
    sources["faq"] = split_docs(open(a.faq, encoding="ascii").read())

    train, valid, manifest = [], [], {"sources": {}}
    for name, docs in sources.items():
        rng.shuffle(docs)
        nv = max(50, int(len(docs) * a.valid_frac))
        v, t = docs[:nv], docs[nv:]
        rep = {"oasst2": a.oasst_repeat, "faq": a.faq_repeat}.get(name, 1)
        train.extend(t * rep); valid.extend(v)
        manifest["sources"][name] = {"docs": len(docs), "train_docs": len(t), "repeat": rep, "valid_docs": len(v),
                                     "train_bytes": sum(len(d) for d in t) * rep}
    rng.shuffle(train); rng.shuffle(valid)
    for fn, docs in (("train.txt", train), ("valid.txt", valid)):
        p = os.path.join(a.out_dir, fn)
        with open(p, "w", encoding="ascii") as f:
            for d in docs:
                f.write(d + "<|endoftext|>\n")
        manifest[fn] = {"docs": len(docs), "bytes": os.path.getsize(p), "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}
    json.dump(manifest, open(os.path.join(a.out_dir, "MANIFEST.json"), "w"), indent=1)
    print(json.dumps(manifest, indent=1))

if __name__ == "__main__":
    main()
