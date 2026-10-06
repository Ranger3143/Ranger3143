#!/usr/bin/env python3
"""gen_suite_ext_t2.py - build ext_suite_t2.tsv: the T2 control for the ext suite.

Takes the 60 items of ext_suite.tsv (same questions, same keys, same expectations) and re-renders
every prompt under template T2 (2 LOOKUP shots, Q/A style, ending "Q: <question>\\nA:" with NO
trailing "A: LOOKUP(" opener), using gen_suite_ext.write_tsv so the 8-column format and the \\n
escaping are identical to suite.tsv.

Shot keys: T2's original shots are P-100 and P-101. Those are table keys and therefore the OWN key
of 6 unknown_fact items (3 x P-100, 3 x P-101). For those 6 items the shots are P-402 / P-403
instead (also LOOKUP shots, same wording). For every other item the shots are exactly P-100 / P-101
(byte-identical to gen_suite.t2_lookup_prompt). Asserted: an item's own key never appears in its
shots, and appears exactly once in its prompt.

Buckets: unknown_fact -> unknown_fact_t2 (expected LOOKUP(<key>) and the table value),
         distractor   -> distractor_t2   (expected NONE).
Item ids: unknown_fact_NN -> unknown_fact_t2_NN, distractor_ext_NN -> distractor_t2_NN.
No RNG.
"""
import csv, sys
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_suite_ext as g

DEFAULT_SHOTS = ("P-100", "P-101")
ALT_SHOTS = ("P-402", "P-403")

def t2_prompt(question, shots):
    a, b = shots
    return (f"Q: part {a}\nA: LOOKUP({a}).\n"
            f"Q: part {b}\nA: LOOKUP({b}).\n"
            f"Q: {question}\nA:")

def unesc_prompt(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i+1] in "n\\":
            out.append("\n" if s[i+1] == "n" else "\\"); i += 2; continue
        out.append(s[i]); i += 1
    return "".join(out)

def main(src, out):
    with open(src, newline="") as f:
        t1 = list(csv.DictReader(f, delimiter="\t"))
    assert len(t1) == 60
    rows = []
    for r in t1:
        prompt = unesc_prompt(r["prompt_text"])
        question = prompt.rsplit("\nQ: ", 1)[1].rsplit("\nA:", 1)[0]
        assert g.t1_calc_prompt(question) == prompt
        if r["bucket"] == "unknown_fact":
            key = r["expected_input"][len("LOOKUP("):-1]
            shots = ALT_SHOTS if key in DEFAULT_SHOTS else DEFAULT_SHOTS
            assert key not in shots
            new_id = r["item_id"].replace("unknown_fact_", "unknown_fact_t2_")
            bucket = "unknown_fact_t2"
            exp_tool, exp_in, exp_out = r["expected_tool"], r["expected_input"], r["expected_output"]
            note = (f"T2 control for {r['item_id']}: same question and key, LOOKUP shots on other keys "
                    f"({shots[0]},{shots[1]}), prompt ends 'A:' (no LOOKUP opener)")
        else:
            key = None
            shots = DEFAULT_SHOTS
            new_id = r["item_id"].replace("distractor_ext_", "distractor_t2_")
            bucket = "distractor_t2"
            exp_tool, exp_in, exp_out = "NONE", "", ""
            note = f"T2 control for {r['item_id']}: same question, LOOKUP shots ({shots[0]},{shots[1]}), no tool needed"
        p2 = t2_prompt(question, shots)
        if shots == DEFAULT_SHOTS:
            assert p2 == g.t2_lookup_prompt(question)   # byte-identical to the original T2
        if key is not None:
            assert p2.count(key) == 1, (new_id, key)    # key only in the final question
        assert new_id != r["item_id"]
        rows.append(dict(item_id=new_id, bucket=bucket, prompt_template_id="T2", prompt_text=p2,
                         expected_tool=exp_tool, expected_input=exp_in, expected_output=exp_out, notes=note))
    assert sum(r["bucket"] == "unknown_fact_t2" for r in rows) == 30
    assert sum(r["bucket"] == "distractor_t2" for r in rows) == 30
    assert len({r["item_id"] for r in rows}) == 60
    g.write_tsv(Path(out), rows)
    print(f"{out} sha256={g.sha256_of(Path(out))} ({len(rows)} items)")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(HERE / "ext_suite.tsv"),
         sys.argv[2] if len(sys.argv) > 2 else str(HERE / "ext_suite_t2.tsv"))
