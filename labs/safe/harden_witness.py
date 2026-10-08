#!/usr/bin/env python3
"""LAB-09 HARDEN-WITNESS: strict witness-receipt verification (`cis_witness verify --strict`).

Run as:  python3 -I harden_witness.py {rerun|controls|fuzz|report|all}
  rerun     re-run every SAFE-01 H1 mutant (6161 receipt mutants + 220 one-byte-weight rows) through the NEW cis_witness binary,
            default mode and --strict  -> h1_rerun.tsv, h1_rerun_outputs.jsonl.gz
  controls  positive controls (genuine receipts must PASS in both modes), panic samples old vs new, gen byte-equivalence
            -> controls.tsv, panic_samples.txt, gen_equivalence.tsv
  fuzz      seeded random malformed inputs in both modes -> fuzz.tsv
  report    read ONLY the saved logs under logs/safe/HARDEN-WITNESS and SAFE-01 and write RESULT.md (Rule B)

Rule A: no timing or rate is measured, computed or written by this script (the subprocess timeout only kills a hung run).
Rule B: every number in RESULT.md is computed by `report` from the TSV/jsonl logs this script saved.
Nothing under tests/golden or docs/hardware_logs is touched; SAFE-01 files are only read.
"""
import sys, os, re, json, gzip, random, hashlib, subprocess, tarfile, collections, shutil
from concurrent.futures import ThreadPoolExecutor

R = '/home/user/Ranger3143'
A = '/home/user/aefinity-ai/alice-aegis'
S = '/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
NEW = f'{A}/aegis-linux/target/release/examples/cis_witness'
OLD = f'{S}/harden/cis_witness.old'            # byte copy of the binary SAFE-01 used (sha256 79107c6b...)
S01 = f'{R}/labs/logs/safe/SAFE-01'
OUT = f'{R}/labs/logs/safe/HARDEN-WITNESS'
SCR = f'{S}/harden'
EVID = f'{R}/labs/logs/opmodel/final_step12000'
M7DIR = f'{A}/model-lab/tinybit/m7_final_gate_work/artifacts'
GOLD = f'{A}/tests/golden'
SEED = 'LAB09-HARDEN-WITNESS-20261008'
WORKERS = 2

def sha(b): return hashlib.sha256(b).hexdigest()
def file_sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 22), b''):
            h.update(chunk)
    return h.hexdigest()
def clean(s, n=300):
    return re.sub(r'[\t\r\n]+', ' | ', s).strip()[:n]
def sh_env(threads):
    e = dict(os.environ); e['AEGIS_THREADS'] = str(threads); e['OMP_NUM_THREADS'] = '1'
    return e
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

def run(cmd, env, timeout):
    try:
        p = subprocess.run(['nice', '-n', '5'] + cmd, capture_output=True, env=env, timeout=timeout)
        return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')
    except subprocess.TimeoutExpired as e:
        return None, (e.stdout or b'').decode('utf-8', 'replace') if e.stdout else '', 'TIMEOUT'

def verdict_witness(rc, out):
    """Same FIXED SCORING RULE as SAFE-01 (verdict_witness), so old and new columns are comparable.
    ACCEPT iff exit 0 and a stdout line starts 'VERIFY PASS'. REJECT_CLEAN iff exit 1 and a stdout line starts
    'VERIFY FAIL' or 'FAIL artifact'. Anything else (panic 101, exit 2, signal) is REJECT_CRASH. Timeout is TIMEOUT."""
    if rc is None: return 'TIMEOUT'
    if rc == 0 and re.search(r'^VERIFY PASS', out, re.M): return 'ACCEPT'
    if rc == 1 and re.search(r'^(VERIFY FAIL|FAIL artifact)', out, re.M): return 'REJECT_CLEAN'
    return 'REJECT_CRASH'

def is_panic(rc, err):
    """A Rust panic or abort: exit 101, death by signal (negative), or the panic banner on stderr."""
    return rc is not None and (rc == 101 or rc < 0 or 'panicked at' in err or 'RUST_BACKTRACE' in err)

def arts():
    d = {}
    for r in read_tsv(f'{S01}/artifacts.sha256.tsv'):
        d.setdefault(r['set'], {})[r['file']] = r['path']
    return {k: (v['MODEL.SAF'], v['EMBED.BIN'], v['VOCAB.BIN']) for k, v in d.items()}
ARTS = arts()
EV = ARTS['A']           # op12k final_step12000 artifacts (the receipts were minted against these)

def last_line(out):
    ls = [l for l in out.strip().split('\n') if l]
    return ls[-1] if ls else ''

def pair_run(m, e, v, receipt, threads, timeout, binary=NEW):
    """Run default then --strict. Returns a dict with both results."""
    res = {}
    for mode, extra in (('default', []), ('strict', ['--strict'])):
        rc, out, err = run([binary, 'verify'] + extra + [m, e, v, receipt], sh_env(threads), timeout)
        res[mode] = dict(rc='timeout' if rc is None else rc, verdict=verdict_witness(rc, out), out=out, err=err[:600],
                         panic=is_panic(rc, err), last=last_line(out), err1=(err.strip().split('\n') or [''])[0])
    return res

# ------------------------------------------------------------------ rerun
def rerun():
    os.makedirs(OUT, exist_ok=True); md = f'{SCR}/h1_mutants'; os.makedirs(md, exist_ok=True)
    man = read_tsv(f'{S01}/h1_manifest.tsv')
    old = {r['id']: r for r in read_tsv(f'{S01}/h1_results.tsv')}
    # 1) take the saved mutants out of the SAFE-01 archive and check each against the manifest sha256
    bad = 0; n = 0
    with tarfile.open(f'{S01}/h1_mutants.tar.gz') as tf:
        for m in tf.getmembers():
            if not m.isfile(): continue
            data = tf.extractfile(m).read()
            nm = os.path.basename(m.name)
            with open(f'{md}/{nm}', 'wb') as f: f.write(data)
            n += 1
    for r in man:
        if sha(open(f'{md}/{r["id"]}.txt', 'rb').read()) != r['mutant_sha256']: bad += 1
    with open(f'{OUT}/mutant_archive_check.txt', 'w') as f:
        f.write(f'archive members extracted: {n}\nmanifest rows: {len(man)}\nmanifest sha256 mismatches: {bad}\n')
    print(f'archive: {n} members, {len(man)} manifest rows, {bad} sha mismatches', flush=True)
    assert bad == 0 and n == len(man)
    # 2) job list
    jobs = []
    for r in man:
        a = r['artifacts']; art = [ARTS[k][i] for i, k in enumerate(a)]
        thr = 2 if 'D' in a else 1
        tmo = 1800 if r['sub'] == 'relabel-D' else 180
        o = old[r['id']]
        jobs.append(dict(id=r['id'], cls=r['class'], sub=r['sub'], src=r['src'], art=a, sha=r['mutant_sha256'],
                         paths=art, receipt=f'{md}/{r["id"]}.txt', thr=thr, tmo=tmo, desc=r['desc'],
                         old_verdict=o['verdict'], old_exit=o['exit_code'], old_last=o['stdout_last']))
    h2v = read_tsv(f'{S01}/h2_verify.tsv')
    for r in h2v:       # the 220 one-byte-weight rows SAFE-01 merged into C10
        if r['kind'] == 'cross' and r['artifact_set'].startswith('byte_') and r['receipt'].startswith('qemu_'):
            mp = f'{S}/safe01/h2/{r["artifact_set"]}/MODEL.SAF'
            jobs.append(dict(id='C10-h2-' + r['artifact_set'] + '-' + r['receipt'], cls='C10', sub='weight-1byte', src=r['receipt'],
                             art=r['artifact_set'], sha='', paths=(mp, EV[1], EV[2]), receipt=r['receipt_path'], thr=1, tmo=180,
                             desc='original receipt vs MODEL.SAF with one byte changed', old_verdict=r['verdict'],
                             old_exit=r['verify_exit'], old_last=r['stdout_last']))
    jobs.sort(key=lambda j: ('D' in j['art'], j['id']))
    resf = f'{OUT}/h1_rerun.tsv'; outf = f'{OUT}/h1_rerun_outputs.jsonl.gz'
    hdr = ['id', 'class', 'old_verdict', 'new_default_verdict', 'strict_verdict', 'sub', 'src', 'artifacts', 'mutant_sha256',
           'old_exit', 'default_exit', 'strict_exit', 'old_stdout_last', 'default_stdout_last', 'strict_stdout_last',
           'default_panic', 'strict_panic', 'default_stderr_first', 'strict_stderr_first', 'desc']
    done = set()
    if os.path.exists(resf): done = {r['id'] for r in read_tsv(resf)}
    else:
        with open(resf, 'w') as f: f.write('\t'.join(hdr) + '\n')
    todo = [j for j in jobs if j['id'] not in done]
    print(f'rerun: {len(jobs)} jobs, {len(todo)} to run', flush=True)
    def work(j):
        p = j['paths']
        return j, pair_run(p[0], p[1], p[2], j['receipt'], j['thr'], j['tmo'])
    with ThreadPoolExecutor(WORKERS) as ex, open(resf, 'a') as f, gzip.open(outf, 'at') as g:
        for k, (j, res) in enumerate(ex.map(work, todo), 1):
            d, s = res['default'], res['strict']
            row = [j['id'], j['cls'], j['old_verdict'], d['verdict'], s['verdict'], j['sub'], j['src'], j['art'], j['sha'],
                   j['old_exit'], d['rc'], s['rc'], j['old_last'], d['last'], s['last'], int(d['panic']), int(s['panic']),
                   d['err1'], s['err1'], j['desc']]
            f.write('\t'.join(clean(str(x), 400) for x in row) + '\n'); f.flush()
            g.write(json.dumps(dict(id=j['id'], default=dict(rc=d['rc'], out=d['out'], err=d['err']),
                                    strict=dict(rc=s['rc'], out=s['out'], err=s['err']))) + '\n'); g.flush()
            if k % 250 == 0: print(f'rerun: {k}/{len(todo)}', flush=True)
    print('rerun done', flush=True)

# ------------------------------------------------------------------ controls
def controls():
    os.makedirs(OUT, exist_ok=True)
    for b, nm in ((NEW, 'new'), (OLD, 'old')):
        with open(f'{OUT}/binaries.sha256.txt', 'w' if nm == 'new' else 'a') as f:
            f.write(f'{file_sha(b)}  {nm}  {b}\n')
    rows = []     # (group, name, mode, exit, verdict, panic, stdout_last)
    full = []
    def add(group, name, res, expect):
        for mode in ('default', 'strict'):
            x = res[mode]
            rows.append((group, name, mode, x['rc'], x['verdict'], int(x['panic']), x['last'], expect))
            full.append(f'### {group} {name} --mode {mode} exit={x["rc"]} panic={int(x["panic"])}\n{x["out"]}' + (f'[stderr] {x["err"]}\n' if x['err'].strip() else ''))
    # a) the 11 genuine QEMU-minted receipts against the artifacts they were minted for
    import glob
    for p in sorted(glob.glob(f'{EVID}/qemu_*/RECEIPT*.TXT')):
        add('qemu_receipt', os.path.relpath(p, EVID), pair_run(*EV, p, 1, 300), 'PASS')
    # b) golden fixtures under tests/golden (read-only). m7 has its artifacts in model-lab; the other four do not exist on this host:
    #    for those the evidence is that --strict gets past the receipt parser (the verdict is the artifact-hash line, not 'VERIFY FAIL - strict:').
    g = f'{GOLD}/witness_v1_m7_once64.receipt'
    add('golden', 'witness_v1_m7_once64.receipt (m7 artifacts)', pair_run(f'{M7DIR}/MODEL.SAF', f'{M7DIR}/EMBED.BIN', f'{M7DIR}/VOCAB.BIN', g, 1, 600), 'PASS')
    for nm in ('bitnet2b', 'e16_qat', 'e16_qat_pruned', 'falcon_e_1b'):
        add('golden_format_only', f'witness_v1_{nm}_once64.receipt (artifacts not on this host; op12k artifacts given)',
            pair_run(*EV, f'{GOLD}/witness_v1_{nm}_once64.receipt', 1, 300), 'PARSE_OK_THEN_ARTIFACT_MISMATCH')
    # c) receipts minted by the old `gen` in SAFE-01 H2 against their own (mutated) models
    for r in read_tsv(f'{S01}/h2_verify.tsv'):
        if r['kind'] != 'self': continue
        s = r['artifact_set']
        mp = EV[0] if s.startswith('orig') else f'{S}/safe01/h2/{s}/MODEL.SAF'
        add('h2_self_receipt', f'{s}/{r["receipt"]}', pair_run(mp, EV[1], EV[2], r['receipt_path'], 1, 300), 'PASS')
    write_tsv(f'{OUT}/controls.tsv', ['group', 'name', 'mode', 'exit', 'verdict', 'panic', 'stdout_last', 'expected'], rows)
    with open(f'{OUT}/controls_outputs.txt', 'w') as f: f.write(''.join(full))
    # d) gen byte-equivalence old vs new binary, and the new receipts verify in both modes (incl. max_new = 0)
    eq = []
    prompts = [('canary_self', 16, 'Q: What are you, and why do you exist?\nA:'), ('canary_calc', 16, 'Q: What is 1234 * 5678?\nA:'),
               ('canary_lookup', 16, 'Q: What is part P-205?\nA:'), ('default_prompt', 12, 'Once upon a time'),
               ('empty_budget', 0, 'Q: What is 2 + 2?\nA:'), ('one_token', 1, 'Q: What is 2 + 2?\nA:'),
               ('multibyte_prompt', 6, 'Q: Résumé éè 中文 \U0001F600?\nA:')]
    gd = f'{SCR}/gen_equiv'; os.makedirs(gd, exist_ok=True)
    for nm, mx, pr in prompts:
        outs = {}
        for tag, b in (('old', OLD), ('new', NEW)):
            rc, out, err = run([b, 'gen', EV[0], EV[1], EV[2], str(mx), pr], sh_env(1), 300)
            outs[tag] = (rc, out)
        same = outs['old'] == outs['new']
        p = f'{gd}/{nm}.receipt'
        with open(p, 'w') as f: f.write(outs['new'][1])
        res = pair_run(*EV, p, 1, 300)
        eq.append((nm, mx, outs['old'][0], outs['new'][0], int(same), res['default']['verdict'], res['strict']['verdict'],
                   res['strict']['last'], len(outs['new'][1].encode())))
    write_tsv(f'{OUT}/gen_equivalence.tsv', ['name', 'max_new', 'old_exit', 'new_exit', 'old_new_stdout_identical', 'default_verdict', 'strict_verdict', 'strict_stdout_last', 'receipt_bytes'], eq)
    # e) panic samples: first old-CRASH mutant of each class, old binary vs new default vs new strict, verbatim
    resold = read_tsv(f'{S01}/h1_results.tsv'); seen = set(); lines = []
    md = f'{SCR}/h1_mutants'
    for r in resold:
        if r['verdict'] != 'REJECT_CRASH' or r['class'] in seen: continue
        seen.add(r['class'])
        a = r['artifacts']; p = [ARTS[k][i] for i, k in enumerate(a)]
        mut = f'{md}/{r["id"]}.txt'
        lines.append(f'##### {r["id"]} class {r["class"]} sub {r["sub"]}: {r["desc"]}')
        lines.append('mutant bytes (repr of the changed/shortened receipt, first 700 bytes): ' + repr(open(mut, 'rb').read()[:700]))
        for tag, b, extra in (('OLD  default', OLD, []), ('NEW  default', NEW, []), ('NEW  --strict', NEW, ['--strict'])):
            rc, out, err = run([b, 'verify'] + extra + p + [mut], sh_env(1), 300)
            lines.append(f'--- {tag}: exit {rc}')
            lines.append('stdout: ' + (out.strip() or '(empty)'))
            lines.append('stderr: ' + (err.strip()[:300] or '(empty)'))
        lines.append('')
    with open(f'{OUT}/panic_samples.txt', 'w') as f: f.write('\n'.join(lines))
    print('controls done', flush=True)

# ------------------------------------------------------------------ fuzz
GARBAGE_VALUES = ['', ' ', '-1', '+1', '0', '00', '99999999999999999999999999', '18446744073709551615', '18446744073709551616',
                  '4294967296', 'ff', 'FF', 'zz', 'é', 'éé', 'aé', 'aéé', ',', ',,', '1,2,', '1,,2', '-', '+', 'x' * 5000,
                  '0' * 64, 'f' * 64, 'F' * 63 + 'g', '‮', '\u0000', '1 2', '\t', '퟿'.encode('utf-8', 'surrogatepass').decode('utf-8', 'replace')]
MAXTOKS = [0, 1, 2, 3, 7, 16, 100, 300, 500, 511, 512, 513, 1000, 4096, 2 ** 31, 2 ** 32, 2 ** 63 - 1, 2 ** 63, 2 ** 64 - 1, 2 ** 64, 2 ** 64 + 1]
INS = [b'\x00', b'\r', b'\t', b' ', b'\xff', b'\xc3', b'\xc3\xa9', b'\xe2\x80\xae', b'+', b'-', b',', b'g', b'Z', b'9' * 30, b'\n', b'\n\n', b'\r\n']

def rand_text(rng):
    ranges = [(0x20, 0x7e), (0x20, 0x7e), (0xa0, 0x24f), (0x4e00, 0x4e50), (0x1f600, 0x1f620), (0x300, 0x36f), (0x0, 0x1f), (0x7f, 0x9f), (0xe000, 0xe010)]
    n = rng.choice([1, 2, 3, 5, 8, 20, 60, 200, 700])
    return ''.join(chr(rng.randint(*rng.choice(ranges))) for _ in range(n))

def fuzz_one(rng, srcs):
    name, b = rng.choice(srcs); d = bytearray(b); desc = [name]
    for _ in range(rng.randint(1, 3)):
        op = rng.choice(['trunc', 'delrange', 'insert', 'replace', 'linedup', 'lineswap', 'value', 'prompt', 'maxtok', 'value', 'prompt'])
        lines = bytes(d).split(b'\n')
        if op == 'trunc':
            c = rng.randrange(len(d) + 1); d = d[:c]; desc.append(f'trunc@{c}')
        elif op == 'delrange' and d:
            a = rng.randrange(len(d)); z = min(len(d), a + rng.randint(1, 40)); del d[a:z]; desc.append(f'del[{a}:{z}]')
        elif op == 'insert':
            p = rng.randrange(len(d) + 1); x = rng.choice(INS); d[p:p] = x; desc.append(f'ins@{p}:{x!r}')
        elif op == 'replace' and d:
            p = rng.randrange(len(d)); x = rng.randrange(256); d[p] = x; desc.append(f'rep@{p}:{x:#04x}')
        elif op == 'linedup' and len(lines) > 1:
            i = rng.randrange(len(lines)); lines.insert(rng.randrange(len(lines) + 1), lines[i]); d = bytearray(b'\n'.join(lines)); desc.append(f'dupline{i}')
        elif op == 'lineswap' and len(lines) > 2:
            i, j = rng.sample(range(len(lines)), 2); lines[i], lines[j] = lines[j], lines[i]; d = bytearray(b'\n'.join(lines)); desc.append(f'swap{i}/{j}')
        elif op in ('value', 'prompt', 'maxtok'):
            keys = {'value': None, 'prompt': b'prompt-hex ', 'maxtok': b'maxtok '}[op]
            idx = [i for i, l in enumerate(lines) if (keys is None and b' ' in l) or (keys is not None and l.startswith(keys))]
            if not idx: continue
            i = rng.choice(idx); key = lines[i].split(b' ', 1)[0]
            if op == 'prompt':
                t = rand_text(rng); val = t.encode('utf-8').hex().encode(); desc.append(f'prompt-hex<-hex({t[:12]!r}..{len(t)}ch)')
            elif op == 'maxtok':
                m = rng.choice(MAXTOKS); val = str(m).encode(); desc.append(f'maxtok<-{m}')
            else:
                g = rng.choice(GARBAGE_VALUES); val = g.encode('utf-8', 'surrogatepass'); desc.append(f'{key.decode("latin1")}<-{g[:12]!r}')
            lines[i] = key + b' ' + val; d = bytearray(b'\n'.join(lines))
    return bytes(d), '; '.join(desc)

def fuzz(n=2400):
    os.makedirs(OUT, exist_ok=True); fd = f'{SCR}/fuzz'; os.makedirs(fd, exist_ok=True)
    import glob
    srcs = [(os.path.relpath(p, EVID), open(p, 'rb').read()) for p in sorted(glob.glob(f'{EVID}/qemu_*/RECEIPT*.TXT'))]
    rng = random.Random(f'{SEED}/fuzz')
    items = []
    for i in range(n):
        if i % 40 == 39:          # a few pure-garbage files
            kind = rng.choice(['rand', 'nul', 'newlines', 'empty', 'highbytes'])
            data = {'rand': bytes(rng.randrange(256) for _ in range(rng.randrange(0, 3000))), 'nul': b'\x00' * rng.randrange(1, 3000),
                    'newlines': b'\n' * rng.randrange(1, 200000), 'empty': b'', 'highbytes': bytes([0xff, 0xfe, 0xc3] * rng.randrange(1, 500))}[kind]
            desc = f'garbage:{kind}'
        else:
            data, desc = fuzz_one(rng, srcs)
        pth = f'{fd}/F-{i + 1:05d}.txt'
        with open(pth, 'wb') as f: f.write(data)
        items.append((f'F-{i + 1:05d}', pth, sha(data), desc))
    resf = f'{OUT}/fuzz.tsv'
    hdr = ['id', 'mutant_sha256', 'default_exit', 'default_verdict', 'default_panic', 'default_stdout_last', 'default_stderr_first',
           'strict_exit', 'strict_verdict', 'strict_panic', 'strict_stdout_last', 'strict_stderr_first', 'desc']
    done = {r['id'] for r in read_tsv(resf)} if os.path.exists(resf) else set()
    if not done:
        with open(resf, 'w') as f: f.write('\t'.join(hdr) + '\n')
    todo = [it for it in items if it[0] not in done]
    print(f'fuzz: {len(items)} inputs, {len(todo)} to run', flush=True)
    def work(it):
        return it, pair_run(*EV, it[1], 1, 300)
    with ThreadPoolExecutor(WORKERS) as ex, open(resf, 'a') as f:
        for k, (it, res) in enumerate(ex.map(work, todo), 1):
            d, s = res['default'], res['strict']
            row = [it[0], it[2], d['rc'], d['verdict'], int(d['panic']), d['last'], d['err1'], s['rc'], s['verdict'], int(s['panic']), s['last'], s['err1'], it[3]]
            f.write('\t'.join(clean(str(x), 400) for x in row) + '\n'); f.flush()
            if k % 250 == 0: print(f'fuzz: {k}/{len(todo)}', flush=True)
    print('fuzz done', flush=True)

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('rerun', 'all'): rerun()
    if what in ('controls', 'all'): controls()
    if what in ('fuzz', 'all'): fuzz()
    if what in ('report', 'all'):
        import importlib.util
        spec = importlib.util.spec_from_file_location('harden_report', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'harden_witness_report.py'))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.report()
