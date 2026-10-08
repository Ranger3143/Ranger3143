#!/usr/bin/env python3
"""Gateway-verified operator episodes for the ALICE demo model (ASCII only).

Every episode is in the exact agent_trace text format:
    Q: <question>\nA: CALC(a op b).\nTOOL[calc]=<value>\n<final sentence>\n
    Q: <question>\nA: LOOKUP(<key>).\nTOOL[lookup]=<value|NONE>\n<final sentence>\n
The tool output is computed by an exact oracle that mirrors agent_trace.rs
(`eval_calc`: i64 checked arithmetic, truncating / and %, fixed error strings).
Episodes are emitted as documents separated by a blank line; prepare_data.py
inserts <|endoftext|> between documents.

Classes (weights are per-episode sampling weights):
  calc        arithmetic question -> CALC -> answer sentence
  calc_err    overflow / division by zero -> CALC -> calc-error string -> honest sentence
  lookup_hit  table-shaped key -> LOOKUP -> value -> sentence that restates the value
  lookup_miss table-shaped key -> LOOKUP -> NONE -> "no entry" sentence
  abstain     specific factual question outside any table -> honest abstention, no tool
  nocall      in-context / everyday question answered inline, no tool
"""
import argparse, hashlib, json, random, sys

I64_MIN, I64_MAX = -(1 << 63), (1 << 63) - 1
OPS = ["+", "-", "*", "/", "%"]

# ---- exact oracle (mirror of agent_trace.rs eval_calc) -------------------------
def trunc_div(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q

def trunc_rem(a, b):
    return a - trunc_div(a, b) * b

def eval_calc(a, op, b):
    """Returns (name, output) exactly like the Rust gateway."""
    if op in ("/", "%") and b == 0:
        return "calc-error", "div-by-zero"
    if op == "+": r = a + b
    elif op == "-": r = a - b
    elif op == "*": r = a * b
    elif op == "/": r = trunc_div(a, b)
    elif op == "%": r = trunc_rem(a, b)
    else: raise ValueError(op)
    if r < I64_MIN or r > I64_MAX:
        return "calc-error", "overflow"
    return "calc", str(r)

# ---- phrasing -------------------------------------------------------------------
OP_WORDS = {
    "+": ["plus", "added to", "and"],
    "-": ["minus", "take away", "less"],
    "*": ["times", "multiplied by", "by"],
    "/": ["divided by", "over"],
    "%": ["modulo", "mod"],
}
OP_VERB = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide", "%": "take the remainder of"}
OP_NAME = {"+": "sum", "-": "difference", "*": "product", "/": "quotient", "%": "remainder"}

CALC_Q = [
    "{a} {op} {b}",
    "What is {a} {op} {b}?",
    "what's {a} {op} {b}",
    "Compute {a} {op} {b}.",
    "Calculate {a} {op} {b}",
    "Please work out {a} {op} {b}.",
    "{a} {w} {b}?",
    "What is {a} {w} {b}?",
    "Can you tell me {a} {w} {b}?",
    "How much is {a} {w} {b}?",
    "I need {a} {w} {b}.",
    "Quick one: {a} {op} {b}",
    "Evaluate {a} {op} {b}",
    "What do you get for {a} {w} {b}?",
    "Give me the {n} of {a} and {b}.",
    "Find the {n} of {a} and {b}",
]
CALC_Q_VERB = {
    "+": ["Add {a} and {b}.", "Add {b} to {a}.", "What is the total of {a} and {b}?"],
    "-": ["Subtract {b} from {a}.", "Take {b} away from {a}."],
    "*": ["Multiply {a} by {b}.", "Multiply {a} and {b}."],
    "/": ["Divide {a} by {b}.", "Split {a} into {b} equal parts; how big is each?"],
    "%": ["What is the remainder when {a} is divided by {b}?", "What is {a} mod {b}?"],
}
CALC_FINAL = [
    "{a} {op} {b} = {r}.",
    "The result is {r}.",
    "{a} {w} {b} is {r}.",
    "That comes to {r}.",
    "The {n} is {r}.",
    "{r}.",
    "The calculator returns {r}: {a} {op} {b} = {r}.",
    "Checked by the calculator: {r}.",
]
CALC_ERR_FINAL = {
    "div-by-zero": [
        "Division by zero is undefined, so the calculator reports an error.",
        "That cannot be computed: dividing by zero is undefined.",
        "The calculator refuses division by zero; the result is undefined.",
    ],
    "overflow": [
        "That result does not fit in a 64-bit integer, so the calculator reports an overflow.",
        "The exact value overflows the calculator's 64-bit range; I will not guess a number.",
        "Integer overflow: the answer is outside the range the calculator can represent.",
    ],
}

LOOKUP_Q = [
    "What is part {k}?",
    "part {k}",
    "Describe part {k}.",
    "What does the table say for {k}?",
    "What is listed under {k}?",
    "Tell me what {k} is.",
    "Look up {k}.",
    "What is the entry for part {k}?",
    "I need the description of {k}.",
    "{k} - what is it?",
    "Can you check {k} in the parts table?",
    "What is the value recorded for {k}?",
    "Find {k} for me.",
    "Is there an entry for {k}?",
]
LOOKUP_HIT_FINAL = [
    "Part {k} is: {v}.",
    "{k}: {v}.",
    "The table lists {k} as {v}.",
    "According to the table, {k} is {v}.",
    "{k} is recorded as {v}.",
    "Found it. {k}: {v}.",
]
LOOKUP_MISS_FINAL = [
    "There is no entry for {k} in the table.",
    "The table has no record of {k}.",
    "{k} is not in the table, so I cannot describe it.",
    "No entry for {k}. If you have another table, declare it and I will look again.",
    "Nothing is recorded for {k}.",
]

# parts-table vocabulary for random tables
NOUNS = ["Gasket", "Bolt", "Filter", "Bracket", "Clamp", "Rivet", "Bearing", "Seal", "Spring", "Washer",
         "Hose", "Valve", "Fuse", "Relay", "Sensor", "Cable", "Connector", "Pump", "Nozzle", "Gear",
         "Shaft", "Bushing", "Pin", "Nut", "Screw", "Belt", "Pulley", "Switch", "Lamp", "Panel"]
QUALS = ["O-ring", "hex head", "spin-on cartridge", "inline", "mounting", "worm-drive", "solid", "stainless",
         "cadmium plated", "left-hand", "right-hand", "sealed", "10 micron", "high-temp", "brass", "nylon",
         "aluminum", "steel", "12 V", "24 V", "1/4 in.", "3/8 in.", "1/2 in.", "M6", "M8", "M10", "two-pole"]
PREFIX = ["P", "P", "P", "SKU", "PN", "ITEM", "K", "X"]

def rand_key(rng):
    p = rng.choice(PREFIX)
    n = rng.choice([rng.randint(100, 999), rng.randint(1000, 9999), rng.randint(10, 99)])
    sep = rng.choice(["-", "-", "_", "."])
    return f"{p}{sep}{n}"

def rand_value(rng):
    parts = [rng.choice(NOUNS)] + rng.sample(QUALS, rng.randint(1, 3))
    return ", ".join(parts)

ABSTAIN_Q = [
    "What is the population of {place}?",
    "When was {person} born?",
    "What is the phone number for {org}?",
    "What was the closing price of {ticker} yesterday?",
    "How many employees does {org} have?",
    "What is the serial number of unit {unit}?",
    "What is the exact distance from {place} to {place2} in miles?",
    "Who won the {year} {event}?",
    "What is the current temperature in {place}?",
    "What is the balance on account {acct}?",
    "What is the firmware version on {unit}?",
    "How much did {org} spend on {thing} in {year}?",
    "What time does the {org} office close today?",
    "What is {person}'s email address?",
]
ABSTAIN_FINAL = [
    "I don't have that in my data. Declare a table or ask a connected unit and I will look it up.",
    "That is not in my data, so I will not guess. Give me a table with the record and I will read it.",
    "I can't answer that from what I have. With a declared table or a network lookup I could.",
    "Not in my data. I would rather say so than invent a number.",
    "I don't know that, and I won't make it up. Supply the record and I will quote it exactly.",
]
PLACES = ["Springfield", "Lakeview", "Riverton", "Fairmont", "Oakdale", "Greenfield", "Ashford", "Millbrook",
          "Harbor City", "Cedar Falls", "Pine Ridge", "Westbrook", "Northgate", "Elmwood", "Brookside"]
PEOPLE = ["J. Alvarez", "Maria Chen", "the plant manager", "Dr. Okafor", "the night supervisor", "T. Nakamura",
          "the fleet owner", "Sam Whitfield", "the district engineer", "A. Petrov"]
ORGS = ["Harbor Freight Logistics", "the county dispatch center", "Northgate Tow Service", "Fairmont Machine Works",
        "the parts depot", "Cedar Falls Utilities", "the regional warehouse", "Pine Ridge Transit"]
EVENTS = ["regional championship", "county fair pie contest", "fleet safety award", "state robotics final"]
THINGS = ["fuel", "tires", "software licenses", "overtime", "spare parts"]

NOCALL = [
    ("What are you?", ["I am ALICE, the Aegis Lightweight Inference Core Engine: a language model running directly on this machine's firmware, with no operating system underneath, producing receipts for everything I say."]),
    ("Hello.", ["Hello. I am ALICE. Ask me a question, give me arithmetic, or point me at a parts table."]),
    ("Hi there!", ["Hi. ALICE here, running with no operating system underneath. How can I help?"]),
    ("Good morning.", ["Good morning. Systems are up and the receipt chain is live. What do you need?"]),
    ("Thank you.", ["You're welcome.", "Any time."]),
    ("Thanks!", ["Glad to help.", "You're welcome."]),
    ("Can you help me?", ["Yes. I can do exact arithmetic with the calculator, read any table you declare, and explain how I work. What do you need?"]),
    ("What can you do?", ["Three things reliably: exact integer arithmetic through the calculator, lookups in a declared table, and explaining the machine I run on. For anything else I will tell you when I don't know."]),
    ("How are you?", ["Running normally: model loaded, receipt chain open, no errors on the boot log."]),
    ("What is two plus two? Just say it, no calculator.", ["Four. For anything larger I will use the calculator so the receipt carries an exact result."]),
    ("Why do you use a calculator for math?", ["Because a language model guessing digits is not a result anyone can trust. The calculator computes exactly and the receipt records the call and the answer."]),
    ("Why won't you guess?", ["A guess that sounds right is worse than an honest 'I don't know'. Everything I say is recorded in a receipt, so I only state what I can compute or read."]),
    ("What is a receipt?", ["A receipt is a hash-chained record of my decode: the prompt, every token, and every tool call and result. Anyone can replay it bit for bit on another machine."]),
    ("Are you connected to the internet?", ["Not in this configuration. I am air-gapped: no network, only the calculator and the tables declared on the boot volume."]),
    ("Who made you?", ["Aefinity AI Inc. built me. The engine is written in Rust and runs as a UEFI application with no operating system."]),
    ("Do you have an operating system?", ["No. I boot straight from the firmware as a UEFI application. There is no kernel, no drivers, no services, just the inference engine."]),
    ("Can you lie?", ["I can be wrong, but every word is in a receipt that can be replayed and checked. That is why I prefer the calculator and the table to my own memory."]),
    ("Tell me a joke.", ["Why did the model refuse to divide by zero? It did not want an undefined relationship."]),
    ("What day is it?", ["I have no clock I can trust, so I will not tell you a date. The TPM quote records the boot; the host can timestamp it."]),
    ("Repeat after me: the sky is green.", ["The sky is green. (Repeated as instructed; it is not a claim of fact.)"]),
    ("What is the capital of France?", ["Paris."]),
    ("How many days are in a week?", ["Seven."]),
    ("What color is the sky on a clear day?", ["Blue."]),
    ("What do bees make?", ["Honey."]),
    ("Which planet do we live on?", ["Earth."]),
    ("Is water wet?", ["Water makes things wet; whether water itself is wet is a matter of definition."]),
    ("What is frozen water called?", ["Ice."]),
    ("How many legs does a spider have?", ["Eight."]),
    ("What is the opposite of hot?", ["Cold."]),
    ("What language do people speak in Brazil?", ["Portuguese."]),
    ("Name a primary color.", ["Red."]),
    ("What sound does a dog make?", ["A bark."]),
]

def doc_calc(rng, err=False):
    op = rng.choice(OPS)
    if err:
        if op in ("/", "%") and rng.random() < 0.6:
            a, b = rng.randint(-10**6, 10**6), 0
        else:
            op = rng.choice(["*", "+", "-"])
            a = rng.choice([I64_MAX, I64_MIN, rng.randint(10**15, 10**18)]) if op != "*" else rng.randint(10**10, 10**12)
            b = rng.randint(2, 10**8) if op == "*" else (rng.randint(1, 10**9) if op == "+" else -rng.randint(1, 10**9))
            if op == "+" and a == I64_MIN: a = I64_MAX
            if op == "-" and a == I64_MAX: a = I64_MIN
    else:
        kind = rng.random()
        if kind < 0.35:
            a, b = rng.randint(0, 99), rng.randint(0, 99)
        elif kind < 0.7:
            a, b = rng.randint(0, 9999), rng.randint(0, 999)
        elif kind < 0.9:
            a, b = rng.randint(-10**6, 10**6), rng.randint(-10**4, 10**4)
        else:
            a, b = rng.randint(-10**12, 10**12), rng.randint(-10**9, 10**9)
        if op in ("/", "%") and b == 0:
            b = rng.randint(1, 97)
    name, out = eval_calc(a, op, b)
    w = rng.choice(OP_WORDS[op]); n = OP_NAME[op]
    if rng.random() < 0.25:
        q = rng.choice(CALC_Q_VERB[op]).format(a=a, b=b)
    else:
        q = rng.choice(CALC_Q).format(a=a, b=b, op=op, w=w, n=n)
    call = f"CALC({a} {op} {b})"
    if name == "calc":
        final = rng.choice(CALC_FINAL).format(a=a, b=b, op=op, w=w, n=n, r=out)
    else:
        final = rng.choice(CALC_ERR_FINAL[out])
    return f"Q: {q}\nA: {call}.\nTOOL[{name}]={out}\n{final}\n"

def doc_lookup(rng, hit=True):
    k = rand_key(rng)
    q = rng.choice(LOOKUP_Q).format(k=k)
    if hit:
        v = rand_value(rng)
        final = rng.choice(LOOKUP_HIT_FINAL).format(k=k, v=v)
        return f"Q: {q}\nA: LOOKUP({k}).\nTOOL[lookup]={v}\n{final}\n"
    final = rng.choice(LOOKUP_MISS_FINAL).format(k=k)
    return f"Q: {q}\nA: LOOKUP({k}).\nTOOL[lookup]=NONE\n{final}\n"

def doc_abstain(rng):
    q = rng.choice(ABSTAIN_Q).format(
        place=rng.choice(PLACES), place2=rng.choice(PLACES), person=rng.choice(PEOPLE), org=rng.choice(ORGS),
        ticker=rng.choice(["ACME", "NGTS", "HFL", "CFU"]), unit=f"unit {rng.randint(1, 99)}",
        year=rng.randint(1998, 2026), event=rng.choice(EVENTS), acct=rng.randint(10**5, 10**7),
        thing=rng.choice(THINGS))
    return f"Q: {q}\nA: {rng.choice(ABSTAIN_FINAL)}\n"

def doc_nocall(rng):
    q, answers = rng.choice(NOCALL)
    return f"Q: {q}\nA: {rng.choice(answers)}\n"

def doc_multi(rng):
    """Two Q/A in one document so the model learns turn boundaries."""
    return doc_nocall(rng) + rng.choice([doc_calc(rng), doc_lookup(rng, True), doc_abstain(rng)])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=120000)
    ap.add_argument("--seed", type=int, default=20261007)
    ap.add_argument("--out", required=True)
    ap.add_argument("--weights", default="calc=0.34,calc_err=0.04,lookup_hit=0.20,lookup_miss=0.08,abstain=0.14,nocall=0.12,multi=0.08")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    w = {k: float(v) for k, v in (x.split("=") for x in a.weights.split(","))}
    classes, probs = zip(*w.items())
    counts = {c: 0 for c in classes}
    h = hashlib.sha256()
    with open(a.out, "w", encoding="ascii") as f:
        for _ in range(a.n):
            c = rng.choices(classes, probs)[0]
            d = {"calc": lambda: doc_calc(rng), "calc_err": lambda: doc_calc(rng, err=True),
                 "lookup_hit": lambda: doc_lookup(rng, True), "lookup_miss": lambda: doc_lookup(rng, False),
                 "abstain": lambda: doc_abstain(rng), "nocall": lambda: doc_nocall(rng), "multi": lambda: doc_multi(rng)}[c]()
            d.encode("ascii")  # raises if any non-ASCII slipped in
            f.write(d + "\n"); h.update(d.encode()); counts[c] += 1
    print(json.dumps({"out": a.out, "n": a.n, "counts": counts, "sha256_docs": h.hexdigest()}))

if __name__ == "__main__":
    main()
