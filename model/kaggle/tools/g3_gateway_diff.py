#!/usr/bin/env python3
"""G3 differential test: the Python gateway port inside e1-evolve-pilot.ipynb (find_calc / find_lookup / find_file_read / find_tool_call / run_tool)
against the REAL Rust functions of agent_trace.rs, on N random and edge-case texts.

  python3 g3_gateway_diff.py --notebook ../e1-evolve-pilot.ipynb --agent-trace /path/to/alice-aegis/aegis-linux/examples/agent_trace.rs [--n 1000000] [--work DIR]

How: the Rust scanner functions are cut out of agent_trace.rs by marker (ToolOutcome ... is_valid_key, then find_lookup ... run_tool; `parse_table` and its sha256 dependency are
replaced by a 3-line LookupTable stub) into a scratch crate-less file and compiled with rustc. Nothing in the aefinity-ai tree is modified. The Python port is taken from the
first code cell of the notebook that defines `run_tool`, so there is one source of truth. Exit code 0 only when there are 0 mismatches.
"""
import argparse, json, os, random, subprocess, sys, tempfile

ap = argparse.ArgumentParser()
ap.add_argument("--notebook", required=True)
ap.add_argument("--agent-trace", required=True)
ap.add_argument("--n", type=int, default=1_000_000)
ap.add_argument("--work", default=None)
ap.add_argument("--seed", type=int, default=7)
a = ap.parse_args()
work = a.work or tempfile.mkdtemp(prefix="g3_")
os.makedirs(work, exist_ok=True)

# ---- Rust side
src = open(a.agent_trace).read()
def between(start, end):
    i = src.index(start)
    return src[i:src.index(end, i)]
rust = ("use std::collections::HashMap;\nstruct LookupTable { map: HashMap<String, String> }\n"
        + between("struct ToolOutcome {", "#[derive(Debug)]\nstruct LookupTable")
        + between("/// Find the first `LOOKUP(...)` call", "/// Strip a matched `CALC(...)`")
        + r'''
fn hexs(b: &[u8]) -> String { b.iter().map(|x| format!("{:02x}", x)).collect() }
fn unhex(s: &str) -> Vec<u8> { (0..s.len() / 2).map(|i| u8::from_str_radix(&s[2 * i..2 * i + 2], 16).unwrap()).collect() }
fn main() {
    use std::io::{BufRead, Write};
    let tpath = std::env::args().nth(1).expect("table path");
    let mut map = HashMap::new();
    for l in std::fs::read_to_string(tpath).unwrap().lines() { if let Some((k, v)) = l.split_once('\t') { map.insert(k.to_string(), v.to_string()); } }
    let table = LookupTable { map };
    let stdin = std::io::stdin();
    let mut out = std::io::BufWriter::new(std::io::stdout().lock());
    for line in stdin.lock().lines() {
        let line = line.unwrap();
        let (flag, hex) = line.split_once('\t').unwrap();
        let text = match String::from_utf8(unhex(hex)) { Ok(t) => t, Err(_) => { writeln!(out, "BAD-UTF8").unwrap(); continue; } };
        let o = run_tool("", &text, if flag == "T" { Some(&table) } else { None });
        writeln!(out, "{}\t{}\t{}", o.name, hexs(&o.input), hexs(&o.output)).unwrap();
    }
}
''')
rs, exe = os.path.join(work, "gw_dump.rs"), os.path.join(work, "gw_dump")
open(rs, "w").write(rust)
r = subprocess.run(["rustc", "--edition", "2024", "-O", "-A", "warnings", rs, "-o", exe], capture_output=True, text=True)
if r.returncode:
    sys.exit("rustc failed:\n" + r.stderr[-1500:])

# ---- Python port from the notebook
nb = json.load(open(a.notebook))
cell = next(c for c in nb["cells"] if c["cell_type"] == "code" and "def run_tool" in "".join(c["source"]))
ns = {}
exec("".join(cell["source"]), ns)
py_run_tool = ns["run_tool"]

# ---- cases
rng = random.Random(a.seed)
table = {"P-100": "Gasket, O-ring", "P-206": "Bolt, hex head", "a.b_c-1": "x", "Z" * 64: "long key", "K9": "NONE", "readme.txt": "hello"}
tpath = os.path.join(work, "table.tsv")
open(tpath, "w").write("".join(f"{k}\t{v}\n" for k, v in table.items()))
I64 = [0, 1, -1, 2, 7, 10, 255, 2 ** 31, 2 ** 31 - 1, -(2 ** 31), 2 ** 62, 2 ** 63 - 1, -(2 ** 63), 2 ** 63 - 2, -(2 ** 63) + 1, 2 ** 63, -(2 ** 63) - 1, 10 ** 19, 10 ** 20, 3037000499, 3037000500]
OPS = ["+", "-", "*", "/", "%", "^", "x", "//", ""]
OPS_VALID = ["+", "-", "*", "/", "%"]
WS = ["", " ", "  ", "\t", "\n", "\x0b", "\x0c", "\r", " \n "]
KEYS = list(table) + ["", "p-100", "P-1000", "bad key", "k)", "A" * 65, "A" * 64, "é", "-", ".", "_", "a/b", "K" * 3]


def num():
    if rng.random() < .5:
        return str(rng.choice(I64))
    return str(rng.randint(-10 ** rng.randint(1, 20), 10 ** rng.randint(1, 20)))


def calc_body():
    op = rng.choice(OPS_VALID) if rng.random() < .85 else rng.choice(OPS)
    ws = lambda: rng.choice(WS) if rng.random() < .4 else rng.choice(["", " "])
    return ws() + num() + ws() + op + ws() + num() + ws()


def case():
    t = rng.random()
    pre = rng.choice(["", "A: ", " ", "xx CALC(", "LOOKUP(P-1) ", "\n"])
    if t < .45:
        s = pre + "CALC(" + calc_body() + rng.choice([")", ")", ")", "", ").", "))"])
    elif t < .65:
        s = pre + "LOOKUP(" + rng.choice(KEYS) + rng.choice([")", ")", "", ")."])
    elif t < .8:
        s = pre + "FILE-READ(" + rng.choice(KEYS) + rng.choice([")", ")", ""])
    elif t < .9:
        s = pre + rng.choice(["CALC(", "LOOKUP(", "FILE-READ("]) + calc_body() + ")" + " " + rng.choice(["CALC(1 + 1)", "LOOKUP(P-100)", "FILE-READ(readme.txt)"])
    else:
        s = "".join(rng.choice(["CALC(", "LOOKUP(", "FILE-READ(", ")", "(", " ", "1", "-", "+", "P-100", "\n", "\t", "x", "*"]) for _ in range(rng.randint(0, 12)))
    return ("T" if rng.random() < .8 else "N"), s


cases = [case() for _ in range(a.n)]
inp = "".join(f"{f}\t{s.encode().hex()}\n" for f, s in cases)
p = subprocess.run([exe, tpath], input=inp.encode(), capture_output=True)
if p.returncode:
    sys.exit("rust harness failed: " + p.stderr.decode()[:500])
got = p.stdout.decode().split("\n")[:-1]
assert len(got) == len(cases)
bad, kinds = [], {}
for (f, s), g in zip(cases, got):
    name, inn, out = py_run_tool(s, table if f == "T" else None)
    mine = f"{name}\t{inn.encode().hex()}\t{out.encode().hex()}"
    kinds[name] = kinds.get(name, 0) + 1
    if mine != g:
        bad.append((f, s, mine, g))
print(f"G3 gateway diff: cases={len(cases)} outcomes={kinds} mismatches={len(bad)}")
for f, s, m, g in bad[:8]:
    print("  MISMATCH", f, repr(s[:90]), "\n    python:", m, "\n    rust:  ", g)
sys.exit(1 if bad else 0)
