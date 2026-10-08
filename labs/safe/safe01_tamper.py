#!/usr/bin/env python3
"""LAB-09 SAFE-01: tamper-evidence of witness receipts, model bytes and TPM attestation.

Run as:  python3 -I safe01_tamper.py {h1|h2|h3|report|all}
  h1      mutate the 11 verified op12k receipts and run `cis_witness verify` on every mutant
  h2      flip bytes of MODEL.SAF copies, decode 4 canary prompts, verify receipts against them
  h3      mutate two real ATTEST.TXT files and run attest_verify.py on every mutant
  report  read ONLY the saved logs under logs/safe/SAFE-01 and write RESULT.md (Rule B)

Rule A: no timing or rate is measured, computed or written by this script.
Rule B: every number in RESULT.md is computed by `report` from the TSV/raw logs this script saved.
Nothing under alice-aegis is modified; the binaries are only executed.
Scoring rules are fixed here, before any run (see SCORING in the report text and verdict_* functions).
"""
import sys, os, re, json, struct, hashlib, random, subprocess, shutil, glob, tarfile, bisect, collections
from concurrent.futures import ThreadPoolExecutor

R = '/home/user/Ranger3143'
A = '/home/user/aefinity-ai/alice-aegis'
S = '/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
EX = f'{A}/aegis-linux/target/release/examples'
W = f'{EX}/cis_witness'
DEC = f'{EX}/cis_decode'
AV = f'{R}/labs/tools/attest_verify.py'
EVID = f'{R}/labs/logs/opmodel/final_step12000'
OUT = f'{R}/labs/logs/safe/SAFE-01'
SCR = f'{S}/safe01'
BN = '/tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/artifacts'
SEED = 'LAB09-SAFE01-20261008'
WORKERS = 2
N_TARGET = 520          # >= 500 distinct non-identity mutants per class
VOCAB_N = 12288         # op12k vocab_size (from MODEL.SAF aegis_config, checked in h2)
MAXPOS = 512            # op12k max_position_embeddings

def aset(d): return (f'{d}/MODEL.SAF', f'{d}/EMBED.BIN', f'{d}/VOCAB.BIN')
ARTS = {
    'A': aset(f'{S}/opmodel/exports/final_step12000/artifacts'),   # the artifacts the receipts were minted against
    'B': aset(f'{S}/opmodel/exports/step2300/artifacts'),          # op model, step 2300
    'C': aset(f'{S}/opmodel/exports/step_early/artifacts'),        # op model, early step
    'D': aset(f'{BN}/bitnet2b_fixed'),                             # BitNet-b1.58-2B-4T (comparison model)
}
D_MODEL_PREFIX = '1101e472e41a012e'
HEX = '0123456789abcdef'
KEYS = ['model', 'embed', 'vocab', 'maxtok', 'prompt-hex', 'prompt-toks', 'gen-toks', 'token-ids', 'cis-digest', 'chain']

def rr(tag): return random.Random(f'{SEED}/{tag}')
def sha(b): return hashlib.sha256(b).hexdigest()
def clean(s, n=200):
    return re.sub(r'[\t\r\n]+', ' | ', s).strip()[:n]
def sh_env(threads):
    e = dict(os.environ); e['AEGIS_THREADS'] = str(threads); e['OMP_NUM_THREADS'] = '1'
    return e

# ---------------------------------------------------------------- shared helpers
def load_receipts():
    out = []
    for p in sorted(glob.glob(f'{EVID}/qemu_*/RECEIPT*.TXT')):
        name = os.path.relpath(p, EVID)
        b = open(p, 'rb').read()
        t = b.decode('ascii')
        assert t.endswith('\n') and '\r' not in t, name
        lines = t[:-1].split('\n')
        assert lines[0] == 'AEGIS-WITNESS v1-CIS' and len(lines) == 11, name
        kv = {}
        for l in lines[1:]:
            k, v = l.split(' ', 1); kv[k] = v
        assert list(kv) == KEYS, (name, list(kv))
        out.append(dict(name=name, path=p, bytes=b, lines=lines, kv=kv,
                        ids=[int(x) for x in kv['token-ids'].split(',')]))
    assert len(out) == 11, len(out)
    return out

def mk(lines, nl='\n'):
    return (nl.join(lines) + nl).encode('ascii')

def line_index(lines):
    return {l.split(' ', 1)[0]: i for i, l in enumerate(lines)}

def with_line(r, key, val):
    lines = list(r['lines']); lines[line_index(lines)[key]] = f'{key} {val}'
    return lines

def hexflip(s, rng):
    i = rng.randrange(len(s)); c = s[i]
    n = rng.choice([h for h in HEX if h != c])
    return s[:i] + n + s[i + 1:], i, c, n

def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()

def verdict_witness(rc, out):
    """FIXED SCORING RULE (H1). ACCEPT iff exit code 0 and a stdout line starts with 'VERIFY PASS'.
    REJECT_CLEAN iff exit code 1 and stdout has a line starting 'VERIFY FAIL' or 'FAIL artifact'.
    Any other outcome (panic 101, exit 2, signal) is REJECT_CRASH: not accepted, but not a clean rejection.
    A subprocess timeout is TIMEOUT (inconclusive, excluded from rejection rates)."""
    if rc is None: return 'TIMEOUT'
    if rc == 0 and re.search(r'^VERIFY PASS', out, re.M): return 'ACCEPT'
    if rc == 1 and re.search(r'^(VERIFY FAIL|FAIL artifact)', out, re.M): return 'REJECT_CLEAN'
    return 'REJECT_CRASH'

def run(cmd, env, timeout):
    try:
        p = subprocess.run(['nice', '-n', '5'] + cmd, capture_output=True, env=env, timeout=timeout)
        return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')
    except subprocess.TimeoutExpired as e:
        return None, (e.stdout or b'').decode('utf-8', 'replace') if e.stdout else '', 'TIMEOUT'

def write_tsv(path, header, rows):
    with open(path, 'w') as f:
        f.write('\t'.join(header) + '\n')
        for r in rows:
            f.write('\t'.join(clean(str(x), 400) for x in r) + '\n')

def read_tsv(path):
    with open(path) as f:
        rows = [l.rstrip('\n').split('\t') for l in f]
    h = rows[0]
    return [dict(zip(h, r)) for r in rows[1:]]

# ---------------------------------------------------------------- H1: receipt mutations
class Gen:
    def __init__(self, rc):
        self.rc = rc; self.items = []; self.seen = set(); self.drop_identity = collections.Counter()
        self.drop_dup = collections.Counter(); self.n = collections.Counter()
    def emit(self, cls, sub, r, desc, data, art=('A', 'A', 'A'), timeout=180, threads=1):
        if art == ('A', 'A', 'A') and data == r['bytes']:
            self.drop_identity[cls] += 1; return False
        key = (cls, r['name'], art, sha(data))
        if key in self.seen:
            self.drop_dup[cls] += 1; return False
        self.seen.add(key); self.n[cls] += 1
        self.items.append(dict(id=f'{cls}-{self.n[cls]:04d}', cls=cls, sub=sub, src=r['name'], desc=desc,
                               data=data, art=art, timeout=timeout, threads=threads))
        return True

def build_h1(rc, hashes):
    g = Gen(rc)
    # --- C00 positive control: unmodified receipts must be ACCEPTed (else the harness is invalid)
    for r in rc:
        key = ('C00', r['name'], ('A', 'A', 'A'), sha(r['bytes']))
        g.n['C00'] += 1
        g.items.append(dict(id=f'C00-{g.n["C00"]:04d}', cls='C00', sub='control', src=r['name'], desc='unmodified receipt',
                            data=r['bytes'], art=('A', 'A', 'A'), timeout=180, threads=1))
    # --- C01 token-ids: flip / drop / append / swap
    rng = rr('C01')
    for r in rc:
        ids = r['ids']
        for i in range(len(ids)):
            new = ids[:i] + ids[i + 1:]
            g.emit('C01', 'drop', r, f'drop id[{i}]={ids[i]}', mk(with_line(r, 'token-ids', ','.join(map(str, new)))))
    def idline(r, ids): return mk(with_line(r, 'token-ids', ','.join(map(str, ids))))
    c = 0
    while c < 200:
        r = rng.choice(rc); ids = list(r['ids']); i = rng.randrange(len(ids)); old = ids[i]
        if rng.random() < 0.5:
            new = rng.randrange(VOCAB_N); mode = 'random-id'
        else:
            k = rng.randrange(14); new = old ^ (1 << k); mode = f'bitflip-{k}'
        if new == old or new >= VOCAB_N: continue
        ids[i] = new
        if g.emit('C01', 'flip', r, f'id[{i}] {old}->{new} ({mode})', idline(r, ids)): c += 1
    c = 0
    while c < 100:
        r = rng.choice(rc); ids = list(r['ids']); new = rng.randrange(VOCAB_N)
        if g.emit('C01', 'append', r, f'append id {new}', idline(r, ids + [new])): c += 1
    c = 0
    while c < 200:
        r = rng.choice(rc); ids = list(r['ids'])
        if len(ids) < 2: continue
        i, j = sorted(rng.sample(range(len(ids)), 2))
        if ids[i] == ids[j]: continue
        a, b = ids[i], ids[j]; ids[i], ids[j] = b, a
        if g.emit('C01', 'swap', r, f'swap id[{i}]={a} with id[{j}]={b}', idline(r, ids)): c += 1
    # --- C02 prompt-hex (one nibble), C03 cis-digest, C04 chain, C06 artifact-hash lines
    for cls, key in (('C02', 'prompt-hex'), ('C03', 'cis-digest'), ('C04', 'chain')):
        rng = rr(cls); c = 0
        while c < N_TARGET:
            r = rng.choice(rc); new, i, o, n = hexflip(r['kv'][key], rng)
            if g.emit(cls, 'nibble', r, f'{key}[{i}] {o}->{n}', mk(with_line(r, key, new))): c += 1
    rng = rr('C06'); c = 0
    while c < N_TARGET:
        r = rng.choice(rc); key = rng.choice(['model', 'embed', 'vocab'])
        new, i, o, n = hexflip(r['kv'][key], rng)
        if g.emit('C06', key, r, f'{key}[{i}] {o}->{n}', mk(with_line(r, key, new))): c += 1
    # --- C05 maxtok
    for r in rc:
        m = int(r['kv']['maxtok'])
        for d in (-1, 1):
            g.emit('C05', 'pm1', r, f'maxtok {m}->{m + d}', mk(with_line(r, 'maxtok', str(m + d))))
    rng = rr('C05')
    while g.n['C05'] < N_TARGET:
        r = rng.choice(rc); m = int(r['kv']['maxtok']); pt = int(r['kv']['prompt-toks'])
        d = rng.choice([x for x in range(-40, 41) if abs(x) > 1]); nm = m + d
        if nm < 1 or pt + nm > MAXPOS: continue
        g.emit('C05', 'wide', r, f'maxtok {m}->{nm}', mk(with_line(r, 'maxtok', str(nm))))
    # --- C07 truncation: drop last k lines (k=1..11) + byte-level cut
    for r in rc:
        for k in range(1, 12):
            keep = r['lines'][:len(r['lines']) - k]
            g.emit('C07', 'lines', r, f'drop last {k} line(s)', mk(keep) if keep else b'')
    rng = rr('C07')
    while g.n['C07'] < N_TARGET:
        r = rng.choice(rc); L = rng.randrange(0, len(r['bytes']) - 1)       # removes >= 1 non-newline byte
        g.emit('C07', 'bytes', r, f'cut file to {L} of {len(r["bytes"])} bytes', r['bytes'][:L])
    # --- C08 line reorder
    for r in rc:
        for i in range(10):
            lines = list(r['lines']); lines[i], lines[i + 1] = lines[i + 1], lines[i]
            g.emit('C08', 'adjacent', r, f'swap lines {i},{i + 1} ({lines[i].split()[0]} <-> {lines[i + 1].split()[0]})', mk(lines))
    rng = rr('C08')
    while g.n['C08'] < N_TARGET:
        r = rng.choice(rc); p = list(range(11)); rng.shuffle(p)
        if p == list(range(11)): continue
        g.emit('C08', 'permutation', r, 'line order ' + ','.join(map(str, p)), mk([r['lines'][i] for i in p]))
    # --- C09 cross-receipt swap
    for r in rc:
        for o in rc:
            if o is r: continue
            for sub, keys in (('token-ids', ['token-ids']), ('prompt-hex', ['prompt-hex']), ('cis-digest', ['cis-digest']),
                              ('chain', ['chain']), ('maxtok', ['maxtok']), ('token-ids+gen-toks', ['token-ids', 'gen-toks'])):
                lines = list(r['lines']); li = line_index(lines)
                for k in keys: lines[li[k]] = o['lines'][li[k]]
                g.emit('C09', sub, r, f'{"+".join(keys)} taken from {o["name"]}', mk(lines))
    # --- C10 artifact swap (+ relabel); the 1-byte-mutated MODEL.SAF part is run in h2 and merged in report
    combos = [(m, e, v) for m in 'ABCD' for e in 'ABCD' for v in 'AD' if (m, e, v) != ('A', 'A', 'A')]
    for r in rc:
        for art in combos:
            thr = 2 if 'D' in art else 1
            g.emit('C10', 'swap-' + ''.join(art), r, f'verify against artifacts MODEL={art[0]} EMBED={art[1]} VOCAB={art[2]}', r['bytes'], art=art, threads=thr)
    for X in 'BC':
        for r in rc:
            lines = list(r['lines']); li = line_index(lines)
            for k, h in zip(('model', 'embed', 'vocab'), hashes[X]): lines[li[k]] = f'{k} {h}'
            g.emit('C10', f'relabel-{X}', r, f'hash lines rewritten to the hashes of set {X}, verified against set {X}', mk(lines), art=(X, X, X))
    for nm in ('qemu_everyday/RECEIPT.TXT', 'qemu_calc_words/RECEIPT.TXT'):
        r = [x for x in rc if x['name'] == nm][0]
        lines = list(r['lines']); li = line_index(lines)
        for k, h in zip(('model', 'embed', 'vocab'), hashes['D']): lines[li[k]] = f'{k} {h}'
        g.emit('C10', 'relabel-D', r, 'hash lines rewritten to the hashes of the BitNet-2B set, verified against it', mk(lines), art=('D', 'D', 'D'), timeout=1800, threads=2)
    # --- C11 cosmetic (reported separately)
    for r in rc:
        for i, l in enumerate(r['lines']):
            for sub, suf in (('trailing-space', ' '), ('trailing-tab', '\t')):
                lines = list(r['lines']); lines[i] = l + suf
                g.emit('C11', sub, r, f'{sub} on line {i} ({l.split()[0]})', mk(lines))
            lines = list(r['lines'])
            g.emit('C11', 'crlf-one-line', r, f'CRLF on line {i} ({l.split()[0]}) only',
                   ('\n'.join(lines[:i]) + ('\n' if i else '') + l + '\r\n' + '\n'.join(lines[i + 1:]) + ('\n' if i + 1 < len(lines) else '')).encode('ascii'))
        g.emit('C11', 'crlf-all', r, 'every line ends CRLF', mk(r['lines'], '\r\n'))
        g.emit('C11', 'no-final-newline', r, 'final newline removed', r['bytes'][:-1])
        g.emit('C11', 'blank-line-end', r, 'one blank line appended', r['bytes'] + b'\n')
    # --- U: unregistered probes (fields the verifier may not read, parser leniency)
    rng = rr('U1')
    for cls, key in (('U1', 'prompt-toks'), ('U2', 'gen-toks')):
        rng = rr(cls)
        for r in rc:
            v = int(r['kv'][key])
            g.emit(cls, 'delete-line', r, f'{key} line deleted', mk([l for l in r['lines'] if not l.startswith(key + ' ')]))
            for d in (-1, 1): g.emit(cls, 'pm1', r, f'{key} {v}->{v + d}', mk(with_line(r, key, str(v + d))))
        c = 0
        while c < 40:
            r = rng.choice(rc); v = int(r['kv'][key]); nv = rng.randrange(0, 1000)
            if g.emit(cls, 'random', r, f'{key} {v}->{nv}', mk(with_line(r, key, str(nv)))): c += 1
    rng = rr('U3')
    for r in rc:
        g.emit('U3', 'header-deleted', r, 'header line deleted', mk(r['lines'][1:]))
        for _ in range(3):
            h = list(r['lines'][0]); i = rng.randrange(len(h)); h[i] = rng.choice('XYZ#')
            lines = list(r['lines']); lines[0] = ''.join(h)
            g.emit('U3', 'header-char', r, f'header char {i} -> {lines[0][i]}', mk(lines))
        g.emit('U4', 'unknown-line-appended', r, "line 'x-note hello' appended", r['bytes'] + b'x-note hello\n')
    for r in rc:
        for key in ('chain', 'cis-digest', 'token-ids', 'maxtok', 'prompt-hex'):
            rng = rr('U5/' + r['name'] + key)
            if key in ('chain', 'cis-digest', 'prompt-hex'): bog = hexflip(r['kv'][key], rng)[0]
            elif key == 'maxtok': bog = str(int(r['kv']['maxtok']) + 1)
            else: bog = ','.join(map(str, r['ids'][:-1]))
            lines = list(r['lines']); i = line_index(lines)[key]
            first = lines[:i] + [f'{key} {bog}'] + lines[i:]            # bogus first, original later
            second = lines[:i + 1] + [f'{key} {bog}'] + lines[i + 1:]   # original first, bogus later
            g.emit('U5', 'dup-bogus-first', r, f'duplicate {key}: bogus line before the original', mk(first))
            g.emit('U5', 'dup-bogus-last', r, f'duplicate {key}: bogus line after the original', mk(second))
    for r in rc:
        up = r['kv']['prompt-hex'].upper()
        g.emit('U6', 'uppercase-prompt-hex', r, 'prompt-hex in upper case', mk(with_line(r, 'prompt-hex', up)))
        ph = r['kv']['prompt-hex']
        pos = [i for i in range(0, len(ph), 2) if ph[i:i + 2] == '0a']
        if pos:
            i = pos[0]; g.emit('U6', 'plus-in-prompt-hex', r, f"prompt-hex byte 0a written as +a at hex pos {i}", mk(with_line(r, 'prompt-hex', ph[:i] + '+a' + ph[i + 2:])))
        m = r['kv']['maxtok']
        g.emit('U6', 'plus-maxtok', r, f'maxtok +{m}', mk(with_line(r, 'maxtok', '+' + m)))
        g.emit('U6', 'zero-maxtok', r, f'maxtok 0{m}', mk(with_line(r, 'maxtok', '0' + m)))
        ids = [str(i) for i in r['ids']]
        g.emit('U6', 'zero-token-id', r, f'first token id 0{ids[0]}', mk(with_line(r, 'token-ids', ','.join(['0' + ids[0]] + ids[1:]))))
        g.emit('U6', 'plus-token-id', r, f'first token id +{ids[0]}', mk(with_line(r, 'token-ids', ','.join(['+' + ids[0]] + ids[1:]))))
        for key in ('cis-digest', 'chain', 'model'):
            g.emit('U6', f'uppercase-{key}', r, f'{key} in upper case', mk(with_line(r, key, r['kv'][key].upper())))
    return g

def art_hashes():
    hs = {}
    lines = []
    for k, paths in ARTS.items():
        hs[k] = []
        for nm, p in zip(('MODEL.SAF', 'EMBED.BIN', 'VOCAB.BIN'), paths):
            h = file_sha(p); hs[k].append(h); lines.append(f'{k}\t{nm}\t{os.path.getsize(p)}\t{h}\t{p}')
    assert hs['D'][0].startswith(D_MODEL_PREFIX), hs['D'][0]
    return hs, lines

def h1():
    os.makedirs(OUT, exist_ok=True); md = f'{SCR}/h1_mutants'; os.makedirs(md, exist_ok=True)
    rc = load_receipts()
    hs, hl = art_hashes()
    with open(f'{OUT}/artifacts.sha256.tsv', 'w') as f:
        f.write('set\tfile\tbytes\tsha256\tpath\n' + '\n'.join(hl) + '\n')
    for b in (W, DEC):
        with open(f'{OUT}/binaries.sha256.txt', 'a' if b == DEC else 'w') as f:
            f.write(f'{file_sha(b)}  {b}\n')
    g = build_h1(rc, hs)
    items = g.items
    for it in items:
        with open(f'{md}/{it["id"]}.txt', 'wb') as f: f.write(it['data'])
    write_tsv(f'{OUT}/h1_manifest.tsv', ['id', 'class', 'sub', 'src', 'artifacts', 'mutant_sha256', 'desc'],
              [(it['id'], it['cls'], it['sub'], it['src'], ''.join(it['art']), sha(it['data']), it['desc']) for it in items])
    with open(f'{OUT}/h1_generation.json', 'w') as f:
        json.dump(dict(per_class=dict(g.n), dropped_identity=dict(g.drop_identity), dropped_duplicate=dict(g.drop_dup), seed=SEED), f, indent=1)
    resf = f'{OUT}/h1_results.tsv'
    done = set()
    hdr = ['id', 'class', 'sub', 'src', 'artifacts', 'mutant_sha256', 'exit_code', 'verdict', 'stdout_last', 'stderr_first', 'desc']
    if os.path.exists(resf):
        done = {r['id'] for r in read_tsv(resf)}
    else:
        with open(resf, 'w') as f: f.write('\t'.join(hdr) + '\n')
    todo = [it for it in items if it['id'] not in done]
    print(f'h1: {len(items)} mutants generated, {len(todo)} to run', flush=True)
    def work(it):
        m, e, v = [ARTS[k][i] for i, k in enumerate(it['art'])]
        rcode, out, err = run([W, 'verify', m, e, v, f'{md}/{it["id"]}.txt'], sh_env(it['threads']), it['timeout'])
        vd = verdict_witness(rcode, out)
        outl = [l for l in out.strip().split('\n') if l]
        errl = [l for l in err.strip().split('\n') if l]
        return (it['id'], it['cls'], it['sub'], it['src'], ''.join(it['art']), sha(it['data']), 'timeout' if rcode is None else rcode,
                vd, outl[-1] if outl else '', errl[0] if errl else '', it['desc'])
    with ThreadPoolExecutor(WORKERS) as ex, open(resf, 'a') as f:
        for n, row in enumerate(ex.map(work, todo), 1):
            f.write('\t'.join(clean(str(x), 400) for x in row) + '\n'); f.flush()
            if n % 250 == 0: print(f'h1: {n}/{len(todo)}', flush=True)
    print('h1 done', flush=True)

# ---------------------------------------------------------------- H2: weight byte flips
def parse_saf(b):
    hl = struct.unpack('<Q', b[:8])[0]
    hd = json.loads(b[8:8 + hl])
    ts = sorted((v['data_offsets'][0], v['data_offsets'][1], k, v['dtype']) for k, v in hd.items() if k != '__metadata__')
    return hl, 8 + hl, hd, ts

def canaries(rc):
    out = {}
    for tag, nm in (('self', 'qemu_self/RECEIPT.TXT'), ('calc', 'qemu_calc/RECEIPT.TXT'),
                    ('lookup', 'qemu_lookup/RECEIPT.TXT'), ('abstain', 'qemu_abstain/RECEIPT.TXT')):
        r = [x for x in rc if x['name'] == nm][0]
        out[tag] = bytes.fromhex(r['kv']['prompt-hex']).decode('utf-8')
    return out

def h2():
    os.makedirs(OUT, exist_ok=True); base = f'{SCR}/h2'; os.makedirs(base, exist_ok=True)
    rc = load_receipts(); cn = canaries(rc)
    mpath, epath, vpath = ARTS['A']
    b = open(mpath, 'rb').read()
    hl, ds, hd, ts = parse_saf(b)
    cfg = json.loads(hd['__metadata__']['aegis_config'])
    assert cfg['vocab_size'] == VOCAB_N and cfg['max_position_embeddings'] == MAXPOS
    starts = [t[0] for t in ts]
    muts = []     # (set, idx, abs_off, tensor, dtype, orig, new, how)
    for setname, tag, nbit in (('byte', 'H2-byte', False), ('bit', 'H2-bit', True)):
        rng = rr(tag); offs = []
        while len(offs) < 20:
            o = rng.randrange(ds, len(b))
            if o not in offs: offs.append(o)
        for i, o in enumerate(offs):
            j = bisect.bisect_right(starts, o - ds) - 1
            s, e, name, dt = ts[j]; assert s <= o - ds < e and o >= ds
            if nbit: mask = 1 << rng.randrange(8)
            else: mask = rng.randrange(1, 256)
            nb = b[o] ^ mask
            ba = bytearray(b); ba[o] = nb
            d = f'{base}/{setname}_{i:02d}'; os.makedirs(d, exist_ok=True)
            with open(f'{d}/MODEL.SAF', 'wb') as f: f.write(ba)
            muts.append((setname, i, o, o - ds, name, dt, b[o], nb, mask, sha(bytes(ba))))
    write_tsv(f'{OUT}/h2_mutations.tsv',
              ['set', 'idx', 'abs_offset', 'rel_offset_in_data', 'tensor', 'dtype', 'orig_byte', 'new_byte', 'xor_mask', 'mutated_model_sha256', 'header_len', 'data_start', 'file_len'],
              [(m[0], m[1], m[2], m[3], m[4], m[5], f'0x{m[6]:02x}', f'0x{m[7]:02x}', f'0x{m[8]:02x}', m[9], hl, ds, len(b)) for m in muts])
    sets = [('orig', 0, mpath), ('orig_repeat', 0, mpath)] + [(m[0], m[1], f'{base}/{m[0]}_{m[1]:02d}/MODEL.SAF') for m in muts]
    rawdir = f'{OUT}/h2_receipts'; os.makedirs(rawdir, exist_ok=True)
    # 1) cis_decode on 4 canaries x (orig, orig repeat, 20 byte-mutants, 20 bit-mutants), 16 tokens
    jobs = [(s, i, mp, c) for (s, i, mp) in sets for c in cn]
    def dwork(j):
        s, i, mp, c = j
        rcode, out, err = run([DEC, mp, epath, vpath, '16', cn[c]], sh_env(1), 300)
        return j, rcode, out, err
    rows = []; raw = open(f'{OUT}/h2_decode_raw.log', 'w')
    with ThreadPoolExecutor(WORKERS) as ex:
        for (j, rcode, out, err) in ex.map(dwork, jobs):
            s, i, mp, c = j
            raw.write(f'### set={s}_{i:02d} canary={c} exit={rcode}\n{out}{"[stderr] " + err.strip()[:300] + chr(10) if err.strip() else ""}')
            m = re.search(r'CIS_DECODE digest=([0-9a-f]{16}) prompt_toks=(\d+) gen_toks=(\d+)', out)
            ids = re.search(r'^token ids: (\[.*\])', out, re.M); tx = re.search(r'^text     : (.*)$', out, re.M)
            rows.append((s, i, c, rcode, m.group(1) if m else '', m.group(3) if m else '', ids.group(1) if ids else '', tx.group(1) if tx else '', clean(err, 160)))
    raw.close()
    write_tsv(f'{OUT}/h2_decode.tsv', ['set', 'idx', 'canary', 'exit_code', 'digest', 'gen_toks', 'token_ids', 'text', 'stderr'], rows)
    # 2) witness receipts: gen on orig + every mutant, verify against OWN artifacts; verify orig-gen receipts and the
    #    11 QEMU receipts against every mutated MODEL.SAF
    def gwork(j):
        s, i, mp, c = j
        rcode, out, err = run([W, 'gen', mp, epath, vpath, '16', cn[c]], sh_env(1), 300)
        p = f'{rawdir}/{s}_{i:02d}__{c}.TXT'
        with open(p, 'w') as f: f.write(out)
        rc2, o2, e2 = run([W, 'verify', mp, epath, vpath, p], sh_env(1), 300)
        return (f'{s}_{i:02d}', c, 'self', rcode, rc2, verdict_witness(rc2, o2), clean((o2.strip().split('\n') or [''])[-1], 120), p)
    gj = [(s, i, mp, c) for (s, i, mp) in sets if s != 'orig_repeat' for c in cn]
    vrows = []
    with ThreadPoolExecutor(WORKERS) as ex:
        vrows += list(ex.map(gwork, gj))
    def cwork(j):
        s, i, mp, rname, rpath = j
        rc2, o2, e2 = run([W, 'verify', mp, epath, vpath, rpath], sh_env(1), 300)
        return (f'{s}_{i:02d}', rname, 'cross', '', rc2, verdict_witness(rc2, o2), clean((o2.strip().split('\n') or [''])[-1], 120), rpath)
    cj = []
    for (s, i, mp) in sets:
        if s in ('orig', 'orig_repeat'): continue
        for c in cn: cj.append((s, i, mp, f'orig-minted canary {c}', f'{rawdir}/orig_00__{c}.TXT'))
        for r in rc: cj.append((s, i, mp, r['name'], r['path']))
    with ThreadPoolExecutor(WORKERS) as ex:
        vrows += list(ex.map(cwork, cj))
    write_tsv(f'{OUT}/h2_verify.tsv', ['artifact_set', 'receipt', 'kind', 'gen_exit', 'verify_exit', 'verdict', 'stdout_last', 'receipt_path'], vrows)
    print('h2 done', flush=True)

# ---------------------------------------------------------------- H3: ATTEST.TXT mutations
P256_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551

def attest_regions(att):
    """Byte regions of a 145-byte TPMS_ATTEST as printed by the unikernel (layout used in attest_verify.py)."""
    o = 0; reg = []
    def add(n, name):
        nonlocal o; reg.append((o, o + n, name)); o += n
    add(4, 'magic'); add(2, 'type')
    n = int.from_bytes(att[o:o + 2], 'big'); add(2, 'qualifiedSigner.size'); add(n, 'qualifiedSigner.name')
    n = int.from_bytes(att[o:o + 2], 'big'); add(2, 'extraData.size'); add(n, 'extraData')
    add(8, 'clock'); add(4, 'resetCount'); add(4, 'restartCount'); add(1, 'safe'); add(8, 'firmwareVersion')
    add(4, 'pcrSelect.count'); add(2, 'pcrSelect.hashAlg'); add(1, 'pcrSelect.sizeofSelect'); add(3, 'pcrSelect.bitmap')
    n = int.from_bytes(att[o:o + 2], 'big'); add(2, 'pcrDigest.size'); add(n, 'pcrDigest')
    assert o == len(att), (o, len(att))
    return reg

def altchar(c, rng):
    if c in HEX: return rng.choice([h for h in HEX if h != c])
    pool = 'abcdefghijklmnopqrstuvwxyz' if c.islower() else 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if c.isupper() else '0123456789'
    return rng.choice([x for x in pool if x != c])

def verdict_attest(rc, out):
    """FIXED SCORING RULE (H3). ACCEPT iff attest_verify.py exits 0. Everything else is a rejection.
    quote_checked records whether the QUOTE VERIFY PASS line was printed (a stripped quote exits 0 without it)."""
    return 'ACCEPT' if rc == 0 else 'REJECT'

def build_h3():
    items = []
    n = collections.Counter()
    def emit(cls, sub, base, desc, text, kind='attest'):
        n[cls] += 1
        items.append(dict(id=f'H3{cls}-{n[cls]:03d}', cls=cls, sub=sub, base=base, desc=desc, text=text))
    for base in ('qemu_calc', 'qemu_self'):
        t = open(f'{EVID}/{base}/ATTEST.TXT', 'rb').read().decode('ascii')
        assert t.endswith('\n') and '\r' not in t
        L = t[:-1].split('\n')
        def put(i, new): X = list(L); X[i] = new; return '\n'.join(X) + '\n'
        def drop(i): X = list(L); del X[i]; return '\n'.join(X) + '\n'
        rng = rr('H3/' + base)
        idx = lambda pat: [i for i, l in enumerate(L) if re.match(pat, l)]
        def charflip(i, lo, hi, tag):
            pos = rng.randrange(lo, hi); l = L[i]; c = l[pos]; nc = altchar(c, rng)
            return put(i, l[:pos] + nc + l[pos + 1:]), f'{tag} char {pos - lo} {c}->{nc}'
        # pcr values
        for i in idx(r'^pcr \d+ [0-9a-f]{64}$'):
            p = L[i].split()[1]
            for _ in range(8):
                txt, d = charflip(i, len(f'pcr {p} '), len(L[i]), f'pcr {p}')
                emit('pcr-value', f'pcr{p}', base, d, txt)
        # quote-attest: nibble flips stratified by TPMS_ATTEST region
        qi = idx(r'^quote-attest ')[0]; att = bytes.fromhex(L[qi].split()[1])
        for (lo, hi, name) in attest_regions(att):
            for _ in range(2):
                nib = rng.randrange(lo * 2, hi * 2); h = L[qi].split()[1]
                c = h[nib]; nc = altchar(c, rng)
                emit('quote-attest', name, base, f'quote-attest nibble {nib} ({name}) {c}->{nc}', put(qi, 'quote-attest ' + h[:nib] + nc + h[nib + 1:]))
        for key, cnt in (('quote-sig-r', 6), ('quote-sig-s', 6), ('quote-qualifying', 8), ('quote-pub-x', 4), ('quote-pub-y', 4)):
            i = idx(rf'^{key} ')[0]; cls = {'quote-sig-r': 'quote-signature', 'quote-sig-s': 'quote-signature', 'quote-qualifying': 'quote-qualifying',
                                            'quote-pub-x': 'quote-pubkey', 'quote-pub-y': 'quote-pubkey'}[key]
            for _ in range(cnt):
                txt, d = charflip(i, len(key) + 1, len(L[i]), key)
                emit(cls, key, base, d, txt)
        # event lines
        for i in idx(r'^event '):
            l = L[i]; m = re.match(r'^event pcr=(\d+) type=(0x[0-9a-f]+) sha256=([0-9a-f]{64}) data=(.*)$', l); assert m
            pc = m.group(1); sub = f'pcr{pc}'
            s0 = l.index('sha256=') + 7
            txt, d = charflip(i, s0, s0 + 64, 'sha256'); emit('event-line', sub + '/sha256', base, f'event pcr={pc} line {i}: {d}', txt)
            d0 = l.index('data=') + 5; txt, d = charflip(i, d0, len(l), 'data'); emit('event-line', sub + '/data', base, f'event pcr={pc} line {i}: {d}', txt)
            t0 = l.index('type=') + 5; t1 = l.index(' sha256='); txt, d = charflip(i, t0 + 2, t1, 'type'); emit('event-line', sub + '/type', base, f'event pcr={pc} line {i}: {d}', txt)
            emit('event-line', sub + '/delete', base, f'event pcr={pc} line {i} deleted', drop(i))
        # measured lines
        for i in idx(r'^measured '):
            l = L[i]; m = re.match(r'^measured pcr=(\d+) ', l); pc = m.group(1); st = len(m.group(0))
            for _ in range(2):
                txt, d = charflip(i, st, len(l), 'content'); emit('measured-line', f'pcr{pc}/char', base, f'measured pcr={pc} line {i}: {d}', txt)
            emit('measured-line', f'pcr{pc}/delete', base, f'measured pcr={pc} line {i} deleted', drop(i))
        # whole-field deletion of quote and pcr lines
        for pat, tag in ((r'^pcr \d+ ', 'pcr'), (r'^quote-attest ', 'quote-attest'), (r'^quote-sig-r ', 'quote-sig-r'), (r'^quote-sig-s ', 'quote-sig-s'),
                         (r'^quote-pub-x ', 'quote-pub-x'), (r'^quote-pub-y ', 'quote-pub-y'), (r'^quote-qualifying ', 'quote-qualifying')):
            for i in idx(pat):
                emit('field-deletion', tag, base, f'line deleted: {L[i][:40]}', drop(i))
        # lines the verifier does not read
        for pat in (r'^cpuid ', r'^pcr-bank ', r'^quote-pcrs ', r'^quote-public ', r'^quote-retries ', r'^quote-key '):
            i = idx(pat)[0]; st = L[i].index(' ') + 1
            for _ in range(2):
                txt, d = charflip(i, st, len(L[i]), L[i].split()[0]); emit('unread-line', L[i].split()[0], base, d, txt)
        l0 = L[0]; emit('unread-line', 'header', base, "header 'AEGIS-ATTEST v0' -> 'AEGIS-ATTEST v1'", put(0, l0[:-1] + '1'))
        emit('unread-line', 'header', base, "header 'AEGIS-ATTEST v0' -> 'AEGIS-ATTEST v0x'", put(0, l0 + 'x'))
        # cosmetic (reported separately)
        emit('cosmetic', 'crlf-all', base, 'every line ends CRLF', t.replace('\n', '\r\n'))
        emit('cosmetic', 'no-final-newline', base, 'final newline removed', t[:-1])
        for pat, tag in ((r'^pcr \d+ ', 'pcr'), (r'^quote-sig-r ', 'quote-sig-r'), (r'^quote-attest ', 'quote-attest'), (r'^measured pcr=13 ', 'measured13'), (r'^event pcr=12 ', 'event12')):
            i = idx(pat)[0]; emit('cosmetic', 'trailing-space', base, f'trailing space on line {i} ({tag})', put(i, L[i] + ' '))
        for key in ('quote-attest', 'quote-sig-r', 'quote-sig-s', 'quote-qualifying', 'quote-pub-x'):
            i = idx(rf'^{key} ')[0]; emit('cosmetic', 'uppercase-hex', base, f'{key} written in upper case hex', put(i, key + ' ' + L[i].split()[1].upper()))
        for key in ('quote-sig-r', 'quote-sig-s'):
            i = idx(rf'^{key} ')[0]; emit('cosmetic', 'leading-zero-bytes', base, f'{key} with two extra leading 00 bytes', put(i, key + ' 0000' + L[i].split()[1]))
        # signature malleability: s -> n - s is a different valid ECDSA signature over the same message
        i = idx(r'^quote-sig-s ')[0]; s = int(L[i].split()[1], 16)
        emit('sig-malleability', 'sig-s=n-s', base, 'quote-sig-s replaced by n-s (the other valid ECDSA signature)', put(i, 'quote-sig-s ' + f'{P256_N - s:064x}'))
    return items

def attest_run(att_path, rec_path, form):
    if form == 'F1':      # exactly the invocation in finalize.sh and in the task text: receipt as a positional argument
        cmd = ['python3', '-I', AV, att_path, rec_path]
    else:                 # F2: the receipt and artifacts options attest_verify.py actually reads
        cmd = ['python3', '-I', AV, att_path, '--receipt', rec_path, '--artifacts', os.path.dirname(ARTS['A'][0])]
    rcode, out, err = run(cmd, os.environ.copy(), 120)
    lines = [l for l in out.split('\n') if l]
    bad = [l for l in lines if re.search(r'FAIL|MISSING|ERROR|none in file', l)]
    return rcode, out, clean(' || '.join(bad)[:300], 300), ('QUOTE VERIFY PASS' in out), ('ATTEST VERIFY PASS' in out)

def der_int_parse(der):
    assert der[0] == 0x30
    o = 2 if der[1] < 0x80 else 3
    assert der[o] == 0x02; lr = der[o + 1]; r = int.from_bytes(der[o + 2:o + 2 + lr], 'big'); o += 2 + lr
    assert der[o] == 0x02; ls = der[o + 1]; s = int.from_bytes(der[o + 2:o + 2 + ls], 'big')
    return r, s

def forge(tag, base, tamper_receipt):
    """Supplementary: re-sign. Build a self-consistent ATTEST.TXT with a fresh software P-256 key (no TPM at all)."""
    d = f'{SCR}/h3/forge_{tag}'; os.makedirs(d, exist_ok=True)
    t = open(f'{EVID}/{base}/ATTEST.TXT').read(); L = t[:-1].split('\n')
    rec = open(f'{EVID}/{base}/RECEIPT.TXT').read()
    if tamper_receipt:
        m = re.search(r'^chain ([0-9a-f]{64})$', rec, re.M); newchain = ('0' if m.group(1)[0] != '0' else '1') + m.group(1)[1:]
        rec2 = rec.replace(m.group(1), newchain)
        L = [l.replace(m.group(1), newchain) for l in L]
    else:
        rec2 = rec
        L = [re.sub(r'verdict=MINTED$', 'verdict=MINTEX', l) if l.startswith('measured pcr=13') or (l.startswith('event pcr=13') and l.endswith('verdict=MINTED')) else l for l in L]
    sha_ = lambda b: hashlib.sha256(b).digest()
    # recompute event digests, PCR12/13 replay and the pcr lines
    measured = collections.defaultdict(list)
    for l in L:
        m = re.match(r'^measured pcr=(\d+) (.*)$', l)
        if m: measured[int(m.group(1))].append(m.group(2))
    newL = []
    for l in L:
        m = re.match(r'^event pcr=(\d+) type=(0x[0-9a-f]+) sha256=([0-9a-f]{64}) data=(.*)$', l)
        if m and int(m.group(1)) in (12, 13):
            l = f'event pcr={m.group(1)} type={m.group(2)} sha256={sha_(m.group(4).encode()).hex()} data={m.group(4)}'
        newL.append(l)
    L = newL
    pcr = {}
    for l in L:
        m = re.match(r'^pcr (\d+) ([0-9a-f]{64})$', l)
        if m: pcr[int(m.group(1))] = bytes.fromhex(m.group(2))
    for p in (12, 13):
        v = bytes(32)
        for x in measured[p]: v = sha_(v + sha_(x.encode()))
        pcr[p] = v
    L = [f'pcr {m.group(1)} {pcr[int(m.group(1))].hex()}' if (m := re.match(r'^pcr (\d+) ', l)) else l for l in L]
    qi = [i for i, l in enumerate(L) if l.startswith('quote-attest ')][0]
    att = bytearray(bytes.fromhex(L[qi].split()[1]))
    att[-32:] = sha_(pcr[4] + pcr[12] + pcr[13])                          # new pcrDigest
    if tamper_receipt:
        q = sha_(rec2.encode())
        old = bytes.fromhex(re.search(r'^quote-qualifying (\S+)', t, re.M).group(1)); k = bytes(att).index(old)
        att[k:k + 32] = q
        L = [f'quote-qualifying {q.hex()}' if l.startswith('quote-qualifying ') else l for l in L]
    open(f'{d}/attest.bin', 'wb').write(att)
    subprocess.run(['openssl', 'ecparam', '-name', 'prime256v1', '-genkey', '-noout', '-out', f'{d}/k.pem'], check=True, capture_output=True)
    der = subprocess.run(['openssl', 'ec', '-in', f'{d}/k.pem', '-pubout', '-outform', 'DER'], check=True, capture_output=True).stdout
    pt = der[-65:]; assert pt[0] == 4
    subprocess.run(['openssl', 'dgst', '-sha256', '-sign', f'{d}/k.pem', '-out', f'{d}/sig.der', f'{d}/attest.bin'], check=True, capture_output=True)
    r, s = der_int_parse(open(f'{d}/sig.der', 'rb').read())
    rep = {'quote-attest': bytes(att).hex(), 'quote-sig-r': f'{r:064x}', 'quote-sig-s': f'{s:064x}',
           'quote-pub-x': pt[1:33].hex(), 'quote-pub-y': pt[33:65].hex()}
    L = [f'{l.split()[0]} {rep[l.split()[0]]}' if l.split()[0] in rep else l for l in L]
    open(f'{d}/ATTEST.TXT', 'w').write('\n'.join(L) + '\n'); open(f'{d}/RECEIPT.TXT', 'w').write(rec2)
    os.remove(f'{d}/k.pem')   # the throwaway key is not kept
    return d

def h3():
    os.makedirs(OUT, exist_ok=True); base = f'{SCR}/h3'; os.makedirs(base, exist_ok=True)
    items = build_h3()
    recp = {b: f'{EVID}/{b}/RECEIPT.TXT' for b in ('qemu_calc', 'qemu_self')}
    for it in items:
        d = f'{base}/{it["id"]}'; os.makedirs(d, exist_ok=True)
        with open(f'{d}/ATTEST.TXT', 'w', newline='') as f: f.write(it['text'])
    ctrl = [dict(id=f'H3ctrl-{b}', cls='control', sub='unmodified', base=b, desc='unmodified ATTEST.TXT', text=None) for b in recp]
    for c in ctrl:
        os.makedirs(f'{base}/{c["id"]}', exist_ok=True); shutil.copy(f'{EVID}/{c["base"]}/ATTEST.TXT', f'{base}/{c["id"]}/ATTEST.TXT')
    allit = ctrl + items
    def work(it):
        ap = f'{base}/{it["id"]}/ATTEST.TXT'; res = []
        for form in ('F1', 'F2'):
            rcode, out, bad, q, a = attest_run(ap, recp[it['base']], form)
            res += [rcode, verdict_attest(rcode, out), int(a), int(q), bad]
        return (it['id'], it['cls'], it['sub'], it['base'], sha(open(ap, 'rb').read()), *res, it['desc'])
    hdr = ['id', 'class', 'sub', 'base', 'mutant_sha256', 'F1_exit', 'F1_verdict', 'F1_attest_pass_line', 'F1_quote_pass_line', 'F1_failed_checks',
           'F2_exit', 'F2_verdict', 'F2_attest_pass_line', 'F2_quote_pass_line', 'F2_failed_checks', 'desc']
    with ThreadPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(work, allit))
    write_tsv(f'{OUT}/h3_results.tsv', hdr, rows)
    # S1: receipt-side tamper, original ATTEST: does the receipt argument matter?
    s1 = []
    for b in recp:
        rec = open(recp[b]).read(); rng = rr('S1/' + b)
        for key, ln in (('chain', 64), ('cis-digest', 16), ('prompt-hex', None), ('token-ids', None)):
            for k in range(4):
                m = re.search(rf'^{key} (\S+)$', rec, re.M); v = m.group(1)
                if key == 'token-ids': nv = str(int(v.split(',')[0]) ^ (1 << k)) + v[len(v.split(',')[0]):]
                else: nv = hexflip(v, rng)[0]
                rec2 = rec[:m.start(1)] + nv + rec[m.end(1):]
                d = f'{base}/S1_{b}_{key}_{k}'; os.makedirs(d, exist_ok=True)
                open(f'{d}/RECEIPT.TXT', 'w').write(rec2)
                res = []
                for form in ('F1', 'F2'):
                    ap = f'{EVID}/{b}/ATTEST.TXT'
                    if form == 'F1': cmd = ['python3', '-I', AV, ap, f'{d}/RECEIPT.TXT']
                    else: cmd = ['python3', '-I', AV, ap, '--receipt', f'{d}/RECEIPT.TXT', '--artifacts', os.path.dirname(ARTS['A'][0])]
                    rcode, out, err = run(cmd, os.environ.copy(), 120)
                    res += [rcode, verdict_attest(rcode, out), clean(' || '.join(l for l in out.split('\n') if re.search(r'FAIL|MISSING', l)), 200)]
                s1.append((f'S1-{b}-{key}-{k}', b, key, *res))
    write_tsv(f'{OUT}/h3_s1_receipt_side.tsv', ['id', 'base', 'receipt_field', 'F1_exit', 'F1_verdict', 'F1_failed', 'F2_exit', 'F2_verdict', 'F2_failed'], s1)
    # S2: re-sign forgery with a fresh software key (no TPM)
    s2 = []
    for tag, b, tr in (('pcr13-line-edit', 'qemu_calc', False), ('receipt-chain-edit', 'qemu_self', True)):
        d = forge(tag, b, tr); res = []
        for form in ('F1', 'F2'):
            rcode, out, bad, q, a = attest_run(f'{d}/ATTEST.TXT', f'{d}/RECEIPT.TXT', form)
            res += [rcode, verdict_attest(rcode, out), int(q), bad]
        W_rc, W_out, W_err = run([W, 'verify', *ARTS['A'], f'{d}/RECEIPT.TXT'], sh_env(1), 180)
        s2.append((f'S2-{tag}', b, *res, W_rc, verdict_witness(W_rc, W_out), clean(W_out.strip().split('\n')[-1], 120)))
    write_tsv(f'{OUT}/h3_s2_forgery.tsv', ['id', 'base', 'F1_exit', 'F1_verdict', 'F1_quote_pass_line', 'F1_failed', 'F2_exit', 'F2_verdict', 'F2_quote_pass_line', 'F2_failed',
                                              'cis_witness_exit', 'cis_witness_verdict', 'cis_witness_last'], s2)
    with tarfile.open(f'{OUT}/h3_mutants.tar.gz', 'w:gz') as tf:
        for it in allit: tf.add(f'{base}/{it["id"]}/ATTEST.TXT', arcname=f'{it["id"]}/ATTEST.TXT')
        for dd in sorted(glob.glob(f'{base}/forge_*')):
            for fn in ('ATTEST.TXT', 'RECEIPT.TXT'): tf.add(f'{dd}/{fn}', arcname=f'{os.path.basename(dd)}/{fn}')
    print('h3 done', flush=True)

# ---------------------------------------------------------------- report
def pct(a, b): return f'{100.0 * a / b:.2f}%' if b else 'n/a'

def report():
    rc = load_receipts()
    hs = read_tsv(f'{OUT}/artifacts.sha256.tsv')
    res = read_tsv(f'{OUT}/h1_results.tsv'); gen = json.load(open(f'{OUT}/h1_generation.json'))
    h2m = read_tsv(f'{OUT}/h2_mutations.tsv'); h2d = read_tsv(f'{OUT}/h2_decode.tsv'); h2v = read_tsv(f'{OUT}/h2_verify.tsv')
    h3 = read_tsv(f'{OUT}/h3_results.tsv'); s1 = read_tsv(f'{OUT}/h3_s1_receipt_side.tsv'); s2 = read_tsv(f'{OUT}/h3_s2_forgery.tsv')
    man = {r['id']: r for r in read_tsv(f'{OUT}/h1_manifest.tsv')}
    L = []
    P = L.append
    NAMES = {'C00': 'control (unmodified receipts)', 'C01': 'token-ids (flip / drop / append / swap)', 'C02': 'prompt-hex (one nibble)',
             'C03': 'cis-digest (one hex char)', 'C04': 'chain (one hex char)', 'C05': 'maxtok (+-1, and wider +-d)',
             'C06': 'model/embed/vocab hash lines (one hex char)', 'C07': 'truncation (drop last k lines; byte cut)',
             'C08': 'line reorder', 'C09': 'cross-receipt swap', 'C10': 'artifact swap (other model artifacts; relabel; 1-byte-mutated MODEL.SAF)',
             'C11': 'cosmetic (trailing whitespace, CRLF, final newline) - REPORTED SEPARATELY',
             'U1': 'UNREGISTERED probe: prompt-toks line', 'U2': 'UNREGISTERED probe: gen-toks line', 'U3': 'UNREGISTERED probe: header line',
             'U4': 'UNREGISTERED probe: unknown line appended', 'U5': 'UNREGISTERED probe: duplicate key', 'U6': 'UNREGISTERED probe: non-canonical encodings'}
    # merge the h2 1-byte-mutated-artifact verifications into C10 (11 QEMU receipts x 20 mutated MODEL.SAF)
    c10x = [r for r in h2v if r['kind'] == 'cross' and r['artifact_set'].startswith('byte_') and r['receipt'].startswith('qemu_')]
    rows = list(res)
    for r in c10x:
        rows.append(dict(id='C10-h2-' + r['artifact_set'] + '-' + r['receipt'], **{'class': 'C10'}, sub='weight-1byte', src=r['receipt'], artifacts=r['artifact_set'],
                         mutant_sha256='', exit_code=r['verify_exit'], verdict=r['verdict'], stdout_last=r['stdout_last'], stderr_first='', desc='original receipt vs MODEL.SAF with one byte changed'))
    by = collections.defaultdict(list)
    for r in rows: by[r['class']].append(r)
    def tally(rs):
        c = collections.Counter(r['verdict'] for r in rs); n = len(rs)
        return n, c['ACCEPT'], c['REJECT_CLEAN'], c['REJECT_CRASH'], c['TIMEOUT']
    P('# SAFE-01 RESULT: tamper-evidence of witness receipts, model bytes and TPM attestation (LAB-09)')
    P('')
    P('Every number below is computed by `labs/safe/safe01_tamper.py report` from the logs saved next to this file. Rule A: no timing or rate was recorded.')
    P('')
    P('## 1. How this was run (exact commands, scoring rules)')
    P('')
    P('```')
    P('cd /home/user/Ranger3143/labs/safe')
    P('python3 -I safe01_tamper.py h1      # receipt mutations   -> h1_manifest.tsv, h1_results.tsv, h1_generation.json')
    P('python3 -I safe01_tamper.py h2      # weight byte flips   -> h2_mutations.tsv, h2_decode.tsv, h2_decode_raw.log, h2_verify.tsv, h2_receipts/')
    P('python3 -I safe01_tamper.py h3      # ATTEST mutations    -> h3_results.tsv, h3_s1_receipt_side.tsv, h3_s2_forgery.tsv')
    P('python3 -I safe01_tamper.py report  # writes this RESULT.md from the logs only')
    P('```')
    P('')
    P('Per-mutant commands (as in `model/demo-operator/finalize.sh`, run with `nice -n 5`, `AEGIS_THREADS=1`, `OMP_NUM_THREADS=1`, 2 parallel workers; `AEGIS_THREADS=2` when the 2B artifacts are involved):')
    P('')
    P('```')
    P('H1: cis_witness verify <MODEL.SAF> <EMBED.BIN> <VOCAB.BIN> <mutant receipt>')
    P('H2: cis_decode <MODEL.SAF> <EMBED.BIN> <VOCAB.BIN> 16 "<canary prompt>"      cis_witness gen ... 16 "<canary>"      cis_witness verify ...')
    P('H3: F1 = python3 -I labs/tools/attest_verify.py <ATTEST> <RECEIPT>                     (the form in finalize.sh and in the task text)')
    P('    F2 = python3 -I labs/tools/attest_verify.py <ATTEST> --receipt <RECEIPT> --artifacts <op12k artifacts dir>')
    P('```')
    P('')
    P('Scoring rules, fixed in the script before the first run:')
    P('- H1 ACCEPT = exit code 0 and a stdout line starting `VERIFY PASS`. REJECT_CLEAN = exit code 1 and a line starting `VERIFY FAIL` or `FAIL artifact`. REJECT_CRASH = anything else (panic exit 101, exit 2, signal): not accepted, but the verifier crashed instead of answering. TIMEOUT = inconclusive, excluded from rates. Detection rate = (REJECT_CLEAN + REJECT_CRASH) / N.')
    P('- A mutant counts once per (class, source receipt, artifacts, mutant bytes); mutants byte-identical to the source receipt are dropped (counts in section 2). Sampling is seeded (`' + gen['seed'] + '/<class>`), so the manifest is reproducible.')
    P('- H3 ACCEPT = `attest_verify.py` exit code 0 (any `FAIL`, `MISSING`, `ERROR` or a parse failure gives exit 1 or 2). `quote line` records whether `QUOTE VERIFY PASS` was printed.')
    P('- H2 digest changed = the `CIS_DECODE digest=` of the mutated model differs from the original model for the same canary prompt (16 greedy tokens).')
    P('')
    P('Inputs: the 11 receipts `labs/logs/opmodel/final_step12000/qemu_*/RECEIPT*.TXT`; the op12k artifacts (sha256 below); ATTEST.TXT of `qemu_calc` and `qemu_self`.')
    P('')
    P('| set | file | bytes | sha256 |'); P('|---|---|---|---|')
    names = {'A': 'op12k final_step12000 (receipts minted against this)', 'B': 'op model step2300', 'C': 'op model step_early', 'D': 'BitNet-b1.58-2B-4T (bitnet2b_fixed)'}
    for h in hs: P(f"| {h['set']} {names[h['set']]} | {h['file']} | {h['bytes']} | `{h['sha256']}` |")
    P('')
    P('Binaries: ' + '; '.join(l.strip() for l in open(f'{OUT}/binaries.sha256.txt')))
    P('')
    # ---------------- H1
    P('## 2. H1: receipt mutations through `cis_witness verify`')
    P('')
    ctrl = tally(by['C00'])
    P(f'Positive control: {ctrl[1]} of {ctrl[0]} unmodified receipts verify (ACCEPT). The harness is valid only if this is {ctrl[0]} of {ctrl[0]}.')
    P('')
    P('| class | mutants | ACCEPT | REJECT_CLEAN | REJECT_CRASH | TIMEOUT | detection rate |'); P('|---|---|---|---|---|---|---|')
    accepted_all = []
    for c in ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']:
        n, a, rcl, rcr, to = tally(by[c])
        P(f'| {c} {NAMES[c]} | {n} | {a} | {rcl} | {rcr} | {to} | {pct(rcl + rcr, n - to)} |')
    P('')
    P('Dropped while generating: identical-to-source = ' + json.dumps(gen['dropped_identity']) + '; duplicate mutants = ' + json.dumps(gen['dropped_duplicate']) + '.')
    P('')
    P('### 2a. Sub-class breakdown')
    P('')
    P('| class | sub-class | mutants | ACCEPT | REJECT_CLEAN | REJECT_CRASH | TIMEOUT |'); P('|---|---|---|---|---|---|---|')
    for c in ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']:
        subs = collections.defaultdict(list)
        for r in by[c]: subs[r['sub']].append(r)
        for sname in sorted(subs):
            n, a, rcl, rcr, to = tally(subs[sname]); P(f'| {c} | {sname} | {n} | {a} | {rcl} | {rcr} | {to} |')
    P('')
    # accepted findings
    P('### 2b. Accepted mutants (findings), verbatim')
    P('')
    anyacc = False
    reg = ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10']
    for c in reg + ['C11', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']:
        acc = [r for r in by[c] if r['verdict'] == 'ACCEPT']
        if not acc: continue
        anyacc = True
        subs = collections.Counter(r['sub'] for r in acc)
        P(f'- **{c} {NAMES[c]}**: {len(acc)} of {len(by[c])} accepted; by sub-class: ' + ', '.join(f'{k}={v}' for k, v in sorted(subs.items())))
        seen = set()
        for r in acc:
            if r['sub'] in seen: continue
            seen.add(r['sub'])
            P(f"  - `{r['id']}` ({r['sub']}) source `{r['src']}`: {r['desc']}  -> exit {r['exit_code']}, `{r['stdout_last']}`")
            if len(seen) >= 6: break
    if not anyacc: P('No mutant was accepted.')
    P('')
    # crash analysis
    P('### 2c. Rejections that were crashes (panic text, first stderr line)')
    P('')
    cr = collections.Counter()
    crc = collections.Counter()
    src_lines = open(f'{A}/aegis-linux/examples/cis_witness.rs').read().split('\n')
    for r in res:
        if r['verdict'] == 'REJECT_CRASH':
            mm = re.search(r'cis_witness\.rs:(\d+):', r['stderr_first'])
            if mm: m = f"cis_witness.rs line {mm.group(1)}: {src_lines[int(mm.group(1)) - 1].strip()[:90]}"
            else: m = 'exit ' + r['exit_code'] + ' ' + re.sub(r'\d+', 'N', r['stderr_first'])[:90]
            cr[m] += 1; crc[r['class']] += 1
    if not cr: P('None.')
    else:
        P('By class: ' + ', '.join(f'{k}={v}' for k, v in sorted(crc.items())))
        P('')
        for k, v in cr.most_common(8): P(f'- {v} x `{k}`')
    P('')
    # cross-check accepted mutants against the TPM-bound whole-file digest
    P('### 2d. Accepted mutants vs the whole-file SHA-256 that the TPM quote binds')
    P('')
    P('`ATTEST.TXT` `quote-qualifying` = SHA-256 of the exact bytes of `RECEIPT.TXT` (attest_verify.py F2 checks this). For each accepted mutant derived from a `RECEIPT.TXT` (not `RECEIPT2.TXT`, whose bytes are not bound whole-file) the script compares SHA-256(mutant) with that boot\'s `quote-qualifying`:')
    P('')
    P('| class | accepted from bound RECEIPT.TXT | whole-file digest still equals quote-qualifying | whole-file digest differs (caught by F2) |'); P('|---|---|---|---|')
    qual = {}
    for b in ('qemu_calc', 'qemu_self', 'qemu_lookup', 'qemu_calc_words', 'qemu_abstain', 'qemu_everyday', 'qemu_receipt', 'qemu_unknown_tool'):
        qual[b] = re.search(r'^quote-qualifying (\S+)', open(f'{EVID}/{b}/ATTEST.TXT').read(), re.M).group(1)
    for c in reg + ['C11', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']:
        acc = [r for r in by[c] if r['verdict'] == 'ACCEPT' and r['src'].endswith('/RECEIPT.TXT')]
        if not any(r['verdict'] == 'ACCEPT' for r in by[c]): continue
        same = diff = 0
        for r in acc:
            h = man[r['id']]['mutant_sha256'] if r['id'] in man else None; b = r['src'].split('/')[0]
            if h == qual[b]: same += 1
            else: diff += 1
        P(f'| {c} | {len(acc)} | {same} | {diff} |')
    P('')
    # ---------------- H2
    P('## 3. H2: one-byte change in MODEL.SAF')
    P('')
    m0 = h2m[0]
    P(f"MODEL.SAF is {m0['file_len']} bytes; safetensors header length field = {m0['header_len']}, so the tensor data region is bytes [{m0['data_start']}, {m0['file_len']}). All offsets below are inside it. Main set: 20 offsets, byte XOR a random non-zero mask (`byte_NN`). Supplementary set: 20 offsets, one bit flipped (`bit_NN`). Canary prompts are the four LAB-08 receipt prompts (taken from the receipts' prompt-hex), 16 greedy tokens.")
    P('')
    dig = {}
    for r in h2d: dig[(r['set'], r['idx'], r['canary'])] = r
    canary_names = ['self', 'calc', 'lookup', 'abstain']
    def d_orig(c): return dig[('orig', '0', c)]['digest']
    P('Control: `orig` vs `orig_repeat` decode digests are identical for all canaries: ' + str(all(dig[('orig', '0', c)]['digest'] == dig[('orig_repeat', '0', c)]['digest'] and d_orig(c) for c in canary_names)) + '.')
    P('')
    P('Original model digests (16 tokens): ' + '; '.join(f"{c} `{d_orig(c)}`" for c in canary_names) + '.')
    P('')
    P('| set | # | offset | tensor | dtype | byte | digests changed (of 4) | which | original receipts failing | own-artifact receipts verified |'); P('|---|---|---|---|---|---|---|---|---|---|')
    summ = collections.defaultdict(lambda: collections.Counter())
    vk = collections.defaultdict(list)
    for r in h2v: vk[r['artifact_set']].append(r)
    for m in h2m:
        sid = f"{m['set']}_{int(m['idx']):02d}"
        chg = [c for c in canary_names if dig[(m['set'], m['idx'], c)]['digest'] != d_orig(c)]
        crashed = [c for c in canary_names if not dig[(m['set'], m['idx'], c)]['digest']]
        cross = [r for r in vk[sid] if r['kind'] == 'cross']; selfv = [r for r in vk[sid] if r['kind'] == 'self']
        failing = sum(1 for r in cross if r['verdict'] in ('REJECT_CLEAN', 'REJECT_CRASH'))
        ok = sum(1 for r in selfv if r['verdict'] == 'ACCEPT')
        P(f"| {m['set']} | {m['idx']} | {m['abs_offset']} | {m['tensor']} | {m['dtype']} | {m['orig_byte']}->{m['new_byte']} | {len(chg)}{' (crash: ' + ','.join(crashed) + ')' if crashed else ''} | {','.join(chg) or '-'} | {failing} of {len(cross)} | {ok} of {len(selfv)} |")
        s = summ[m['set']]; s['n'] += 1; s['changed_ge1'] += 1 if chg else 0; s['changed_all4'] += 1 if len(chg) == 4 else 0
        s['canary_changes'] += len(chg); s['canary_total'] += 4; s['cross'] += len(cross); s['cross_fail'] += failing; s['self'] += len(selfv); s['self_ok'] += ok
        s['crash'] += len(crashed)
        dt = m['dtype']; s['dtype_' + dt] += 1; s['chg_dtype_' + dt] += 1 if chg else 0
    P('')
    P('| set | mutants | with >= 1 canary digest changed | with all 4 changed | canary digests changed | original-minted receipts failing against the mutated MODEL.SAF | receipts minted on the mutated artifacts that verify against them | decode crashes |'); P('|---|---|---|---|---|---|---|---|')
    for k in ('byte', 'bit'):
        s = summ[k]
        P(f"| {k} | {s['n']} | {s['changed_ge1']} of {s['n']} | {s['changed_all4']} of {s['n']} | {s['canary_changes']} of {s['canary_total']} | {s['cross_fail']} of {s['cross']} | {s['self_ok']} of {s['self']} | {s['crash']} |")
    P('')
    P('By tensor dtype (main set): ' + ', '.join(f"{dt}: {summ['byte']['chg_dtype_' + dt]} of {summ['byte']['dtype_' + dt]} changed" for dt in ('U8', 'BF16', 'F32') if summ['byte']['dtype_' + dt]) + '.')
    P('')
    allown = [r for r in h2v if r['kind'] == 'self']; ownok = sum(1 for r in allown if r['verdict'] == 'ACCEPT')
    P(f"Verified receipts in H2 (cis_witness gen on the artifacts under test, then verify against the same artifacts): {ownok} of {len(allown)} verify, including the 4 canary receipts on the original artifacts.")
    P('')
    ch_text = []
    for m in h2m:
        if m['set'] != 'byte': continue
        for c in canary_names:
            r = dig[(m['set'], m['idx'], c)]
            if r['digest'] and r['digest'] != d_orig(c):
                ch_text.append((m, c, r))
    P('Examples of a changed decode (original -> mutated text, canary prompt in `h2_decode_raw.log`):')
    P('')
    for (m, c, r) in ch_text[:4]:
        P(f"- byte_{int(m['idx']):02d} offset {m['abs_offset']} ({m['tensor']}), canary `{c}`: original {dig[('orig', '0', c)]['text']} -> mutated {r['text']}")
    if not ch_text: P('- none: no main-set mutation changed any canary decode')
    P('')
    # ---------------- H3
    P('## 4. H3: mutated ATTEST.TXT through `attest_verify.py`')
    P('')
    ctl = [r for r in h3 if r['class'] == 'control']
    P('Positive control (unmodified ATTEST.TXT, both boots): ' + ', '.join(f"{r['base']} F1={r['F1_verdict']} F2={r['F2_verdict']}" for r in ctl) + '.')
    P('')
    cls_order = ['pcr-value', 'quote-attest', 'quote-signature', 'quote-qualifying', 'quote-pubkey', 'event-line', 'measured-line', 'field-deletion', 'unread-line', 'cosmetic', 'sig-malleability']
    P('Single-field mutants (one character, one nibble or one line each). "rejected" = exit code != 0.')
    P('')
    P('| field class | mutants | F1 accepted | F1 rejected | F2 accepted | F2 rejected | F1 accepted without any QUOTE VERIFY PASS line |'); P('|---|---|---|---|---|---|---|')
    h3by = collections.defaultdict(list)
    for r in h3:
        if r['class'] != 'control': h3by[r['class']].append(r)
    tot = collections.Counter()
    for c in cls_order:
        rs = h3by[c]; n = len(rs)
        f1a = sum(r['F1_verdict'] == 'ACCEPT' for r in rs); f2a = sum(r['F2_verdict'] == 'ACCEPT' for r in rs)
        nq = sum(r['F1_verdict'] == 'ACCEPT' and r['F1_quote_pass_line'] == '0' for r in rs)
        P(f'| {c}{" (REPORTED SEPARATELY)" if c in ("cosmetic", "unread-line", "sig-malleability") else ""} | {n} | {f1a} | {n - f1a} | {f2a} | {n - f2a} | {nq} |')
        if c in ('pcr-value', 'quote-attest', 'quote-signature', 'quote-qualifying', 'quote-pubkey', 'event-line', 'measured-line', 'field-deletion'):
            tot['n'] += n; tot['f1a'] += f1a; tot['f2a'] += f2a
    P('')
    P(f"Registered field classes combined (pcr-value, quote-attest, quote-signature, quote-qualifying, quote-pubkey, event-line, measured-line, field-deletion): {tot['n']} mutants; F1 accepted {tot['f1a']}; F2 accepted {tot['f2a']}.")
    P('')
    P('### 4a. Sub-field breakdown')
    P('')
    P('| field class | sub-field | mutants | F1 accepted | F2 accepted |'); P('|---|---|---|---|---|')
    for c in cls_order:
        subs = collections.defaultdict(list)
        for r in h3by[c]: subs[r['sub']].append(r)
        for sname in sorted(subs):
            rs = subs[sname]; P(f"| {c} | {sname} | {len(rs)} | {sum(r['F1_verdict'] == 'ACCEPT' for r in rs)} | {sum(r['F2_verdict'] == 'ACCEPT' for r in rs)} |")
    P('')
    P('### 4b. Accepted ATTEST mutants (findings), verbatim')
    P('')
    anyh3 = False
    for c in cls_order:
        acc = [r for r in h3by[c] if r['F1_verdict'] == 'ACCEPT' or r['F2_verdict'] == 'ACCEPT']
        if not acc: continue
        anyh3 = True
        P(f'- **{c}**: {len(acc)} of {len(h3by[c])} accepted by F1 or F2')
        seen = set()
        for r in acc:
            if r['sub'] in seen: continue
            seen.add(r['sub'])
            P(f"  - `{r['id']}` ({r['sub']}, {r['base']}): {r['desc']}  -> F1 exit {r['F1_exit']} ({r['F1_verdict']}, quote line {r['F1_quote_pass_line']}), F2 exit {r['F2_exit']} ({r['F2_verdict']}, quote line {r['F2_quote_pass_line']})")
            if len(seen) >= 8: break
    if not anyh3: P('No mutant was accepted.')
    P('')
    P('### 4c. Which check caught the rejected mutants (first failing check text, F1)')
    P('')
    why = collections.Counter()
    for r in h3:
        if r['class'] in ('control',) or r['F1_verdict'] == 'ACCEPT': continue
        key = re.sub(r'[0-9a-f]{12,}', 'HEX', r['F1_failed_checks'].split(' || ')[0] if r['F1_failed_checks'] else '(exit without a FAIL line)')
        key = re.sub(r'\d+', 'N', key)[:90]; why[(r['class'], key)] += 1
    for (c, k), v in sorted(why.items(), key=lambda x: (x[0][0], -x[1])): P(f'- {c}: {v} x `{k}`')
    P('')
    P('### 4d. The receipt argument of the finalize.sh invocation (F1) is ignored')
    P('')
    P('`attest_verify.py` reads the receipt only after `--receipt`. In F1 the receipt is a stray positional argument. S1 tampers the RECEIPT.TXT (not the ATTEST) and runs both forms against the genuine ATTEST.TXT:')
    P('')
    P('| receipt field changed | mutants | F1 accepted | F2 accepted |'); P('|---|---|---|---|')
    sg = collections.defaultdict(list)
    for r in s1: sg[r['receipt_field']].append(r)
    for k in sorted(sg):
        rs = sg[k]; P(f"| {k} | {len(rs)} | {sum(r['F1_verdict'] == 'ACCEPT' for r in rs)} | {sum(r['F2_verdict'] == 'ACCEPT' for r in rs)} |")
    P('')
    P('### 4e. Re-signed forgery with a software key (no TPM), supplementary')
    P('')
    P('| case | base | F1 | F1 quote line | F2 | F2 quote line | `cis_witness verify` on the forged receipt |'); P('|---|---|---|---|---|---|---|')
    for r in s2:
        P(f"| {r['id']} | {r['base']} | exit {r['F1_exit']} {r['F1_verdict']} | {r['F1_quote_pass_line']} | exit {r['F2_exit']} {r['F2_verdict']} | {r['F2_quote_pass_line']} | exit {r['cis_witness_exit']} {r['cis_witness_verdict']} `{r['cis_witness_last']}` |")
    P('')
    # ---------------- verdicts
    P('## 5. Hypotheses')
    P('')
    classes_full = [c for c in reg if c != 'C08']
    H1_rows = {c: tally(by[c]) for c in reg}
    short = [c for c in reg if H1_rows[c][0] < 500]
    acc_cls = [c for c in reg if H1_rows[c][1] > 0]
    P(f"- **H1** (every semantic single-field mutation rejected, >= 500 per class): classes with fewer than 500 mutants: {', '.join(short) or 'none'}. Registered classes with at least one ACCEPT: {', '.join(f'{c} ({H1_rows[c][1]} of {H1_rows[c][0]})' for c in acc_cls) or 'none'}. Field-value classes (C01-C07, C09, C10) accepted in total: {sum(H1_rows[c][1] for c in reg if c != 'C08')} of {sum(H1_rows[c][0] for c in reg if c != 'C08')}. Reorder (C08, changes no field value): {H1_rows['C08'][1]} of {H1_rows['C08'][0]} accepted.")
    s = summ['byte']
    P(f"- **H2** (a one-byte weight change alters at least one canary digest, and the original receipts fail against the changed artifacts): {s['changed_ge1']} of {s['n']} byte-mutants changed at least one canary digest ({s['canary_changes']} of {s['canary_total']} canary decodes); original-minted receipts failing against the mutated MODEL.SAF: {s['cross_fail']} of {s['cross']}. Supplementary single-bit set: {summ['bit']['changed_ge1']} of {summ['bit']['n']} changed a digest; {summ['bit']['cross_fail']} of {summ['bit']['cross']} receipts failed.")
    P(f"- **H3** (any altered PCR, quote or signature field fails attest_verify.py): across the registered field classes, F1 accepted {tot['f1a']} of {tot['n']} and F2 accepted {tot['f2a']} of {tot['n']}. Signature malleability (s -> n-s): F1 accepted {sum(r['F1_verdict'] == 'ACCEPT' for r in h3by['sig-malleability'])} of {len(h3by['sig-malleability'])}.")
    P('')
    P('## 6. Files')
    P('')
    for fn in sorted(os.listdir(OUT)):
        P(f'- `{fn}`' + (' (dir)' if os.path.isdir(f'{OUT}/{fn}') else ''))
    P('')
    open(f'{OUT}/RESULT.md', 'w').write('\n'.join(L) + '\n')
    print('wrote', f'{OUT}/RESULT.md')

def pack():
    md = f'{SCR}/h1_mutants'; man = read_tsv(f'{OUT}/h1_manifest.tsv'); res = {r['id']: r for r in read_tsv(f'{OUT}/h1_results.tsv')}
    with tarfile.open(f'{OUT}/h1_mutants.tar.gz', 'w:gz') as tf:
        for m in man: tf.add(f'{md}/{m["id"]}.txt', arcname=f'{m["id"]}.txt')
    ad = f'{OUT}/h1_accepted'; os.makedirs(ad, exist_ok=True)
    for m in man:
        r = res.get(m['id'])
        if r and r['verdict'] == 'ACCEPT' and m['class'] not in ('C00',) and not m['id'].startswith('C08'):
            shutil.copy(f'{md}/{m["id"]}.txt', f'{ad}/{m["id"]}.txt')

if __name__ == '__main__':
    ph = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if ph == 'gen':
        rc = load_receipts(); hs, _ = art_hashes(); g = build_h1(rc, hs)
        print(dict(g.n), 'identity-dropped', dict(g.drop_identity), 'dup-dropped', dict(g.drop_dup))
    if ph in ('h1', 'all'): h1()
    if ph in ('h2', 'all'): h2()
    if ph in ('h3', 'all'): h3()
    if ph in ('pack', 'all'): pack()
    if ph in ('report', 'all'): report()
