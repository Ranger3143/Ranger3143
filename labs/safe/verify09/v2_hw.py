"""LAB-09 VERIFY-2, HARDEN-WITNESS skeptic script (python3 -I, nice -n 5, OMP_NUM_THREADS=1, AEGIS_THREADS=1).

Usage: python3 -I v2_hw.py <section>
  recount   recompute the headline numbers from the saved TSVs (own csv reader, own class logic) + archive/manifest check
  rerun     random 30 SAFE-01 mutants (+ 12 from the crash/accept classes, + 6 touching the BitNet-2B artifacts) through the rebuilt cis_witness
  golden    golden fixtures: own strict-grammar regex on all 5, binary on m7, hash search for the other 4 artifact sets
  diff      own 480 random mutants of genuine receipts: old binary vs new default vs new strict (differential test)
  gen       gen byte-equivalence old vs new on my own prompts
"""
import sys, os, re, csv, random, hashlib, subprocess, tarfile, collections, glob, shutil
from concurrent.futures import ThreadPoolExecutor

R = '/home/user/Ranger3143'
A = '/home/user/aefinity-ai/alice-aegis'
S = '/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
V = f'{S}/verify2'
HW = f'{R}/labs/logs/safe/HARDEN-WITNESS'
S01 = f'{R}/labs/logs/safe/SAFE-01'
EVID = f'{R}/labs/logs/opmodel/final_step12000'
NEW = f'{A}/aegis-linux/target/release/examples/cis_witness'
OLD = f'{S}/harden/cis_witness.old'
GOLD = f'{A}/tests/golden'
M7 = f'{A}/model-lab/tinybit/m7_final_gate_work/artifacts'
OP = f'{S}/opmodel/exports/final_step12000/artifacts'


def tsv(path): return list(csv.DictReader(open(path, newline='', encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
def sha(b): return hashlib.sha256(b).hexdigest()
def fsha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''): h.update(c)
    return h.hexdigest()


def env(th=1): return dict(os.environ, OMP_NUM_THREADS='1', AEGIS_THREADS=str(th))


def run(cmd, th=1, timeout=300):
    try:
        p = subprocess.run(['nice', '-n', '5'] + cmd, capture_output=True, env=env(th), timeout=timeout)
        return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')
    except subprocess.TimeoutExpired:
        return None, '', 'TIMEOUT'


def verd(rc, out):
    if rc is None: return 'TIMEOUT'
    if rc == 0 and re.search(r'^VERIFY PASS', out, re.M): return 'ACCEPT'
    if rc == 1 and re.search(r'^(VERIFY FAIL|FAIL artifact)', out, re.M): return 'REJECT_CLEAN'
    return 'REJECT_CRASH'


def panic(rc, err): return rc is not None and (rc == 101 or rc < 0 or 'panicked at' in err)
def last(out):
    ls = [l for l in out.strip().split('\n') if l]
    return ls[-1] if ls else ''


def arts():
    d = {}
    for r in tsv(f'{S01}/artifacts.sha256.tsv'): d.setdefault(r['set'], {})[r['file']] = r['path']
    return {k: (v['MODEL.SAF'], v['EMBED.BIN'], v['VOCAB.BIN']) for k, v in d.items()}


# ------------------------------------------------------------------------------------------------ recount
def sec_recount():
    rows = tsv(f'{HW}/h1_rerun.tsv')
    print('h1_rerun rows:', len(rows))
    s01 = {r['id']: r for r in tsv(f'{S01}/h1_results.tsv')}
    h2 = tsv(f'{S01}/h2_verify.tsv')
    print('SAFE-01 h1_results rows:', len(s01), '; h2_verify rows:', len(h2), '; header', list(h2[0].keys())[:8])
    # old verdict column vs SAFE-01 recorded verdict for the receipt rows
    rec = [r for r in rows if r['id'] in s01]
    print('receipt rows with a SAFE-01 h1 verdict:', len(rec), '; old_verdict equals SAFE-01 verdict:', sum(1 for r in rec if r['old_verdict'] == s01[r['id']]['verdict']))
    print('non-h1 (weight) rows:', len(rows) - len(rec), 'ids sample:', [r['id'] for r in rows if r['id'] not in s01][:3])
    classes = sorted({r['class'] for r in rows})
    print('\nclass | n | old A/C/X | newdef A/C/X | strict A/C/X | panics old/def/strict')
    tot = collections.Counter()
    for c in classes:
        rs = [r for r in rows if r['class'] == c]
        f = lambda k, v: sum(1 for r in rs if r[k] == v)
        pn = lambda k: sum(1 for r in rs if r[k] == '1')
        print(f'{c:4s} {len(rs):5d} | {f("old_verdict","ACCEPT")}/{f("old_verdict","REJECT_CLEAN")}/{f("old_verdict","REJECT_CRASH")} | '
              f'{f("new_default_verdict","ACCEPT")}/{f("new_default_verdict","REJECT_CLEAN")}/{f("new_default_verdict","REJECT_CRASH")} | '
              f'{f("strict_verdict","ACCEPT")}/{f("strict_verdict","REJECT_CLEAN")}/{f("strict_verdict","REJECT_CRASH")} | '
              f'{"?"}/{pn("default_panic")}/{pn("strict_panic")}')
    nc = [r for r in rows if r['class'] in ('C08', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6')]
    print('\nC08+U1..U6 mutants:', len(nc), '; old ACCEPT', sum(1 for r in nc if r['old_verdict'] == 'ACCEPT'), '; new default ACCEPT', sum(1 for r in nc if r['new_default_verdict'] == 'ACCEPT'), '; strict ACCEPT', sum(1 for r in nc if r['strict_verdict'] == 'ACCEPT'))
    for c in ('C08', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6'):
        rs = [r for r in rows if r['class'] == c]
        print(f'   {c}: n={len(rs)} old ACCEPT={sum(1 for r in rs if r["old_verdict"]=="ACCEPT")} newdef ACCEPT={sum(1 for r in rs if r["new_default_verdict"]=="ACCEPT")} strict ACCEPT={sum(1 for r in rs if r["strict_verdict"]=="ACCEPT")}')
    c11 = [r for r in rows if r['class'] == 'C11']
    print('C11 cosmetic: n', len(c11), 'old ACCEPT', sum(1 for r in c11 if r['old_verdict'] == 'ACCEPT'), 'newdef', sum(1 for r in c11 if r['new_default_verdict'] == 'ACCEPT'), 'strict', sum(1 for r in c11 if r['strict_verdict'] == 'ACCEPT'))
    # panics: recount from exit codes myself, not from the panic column
    old_crash = [r for r in rows if r['old_verdict'] == 'REJECT_CRASH']
    print('\nold crash-rejects:', len(old_crash), dict(collections.Counter(r['class'] for r in old_crash)), '; old exit codes of those:', dict(collections.Counter(r['old_exit'] for r in old_crash)))
    print('new default exit codes over all rows:', dict(collections.Counter(r['default_exit'] for r in rows)))
    print('new strict  exit codes over all rows:', dict(collections.Counter(r['strict_exit'] for r in rows)))
    print('new default/strict exit 101 or other-than-0/1:', sum(1 for r in rows if r['default_exit'] not in ('0', '1')), sum(1 for r in rows if r['strict_exit'] not in ('0', '1')))
    print('stderr non-empty (default/strict):', sum(1 for r in rows if r['default_stderr_first']), sum(1 for r in rows if r['strict_stderr_first']))
    print('rows with a panic banner in the stderr first line:', sum(1 for r in rows for k in ('default_stderr_first', 'strict_stderr_first') if 'panicked' in r[k]))
    # verdict transitions
    tr = collections.Counter((r['old_verdict'], r['new_default_verdict']) for r in rows)
    print('old->new default transitions:', dict(tr))
    nocrash = [r for r in rows if r['old_verdict'] != 'REJECT_CRASH']
    print('non-crash rows:', len(nocrash), '; same exit code:', sum(1 for r in nocrash if r['old_exit'] == r['default_exit']), '; same last stdout line:', sum(1 for r in nocrash if r['old_stdout_last'] == r['default_stdout_last']))
    print('strict ACCEPT rows:', sum(1 for r in rows if r['strict_verdict'] == 'ACCEPT'), '; classes:', dict(collections.Counter(r['class'] for r in rows if r['strict_verdict'] == 'ACCEPT')), '; strict ACCEPT but default not:', sum(1 for r in rows if r['strict_verdict'] == 'ACCEPT' and r['new_default_verdict'] != 'ACCEPT'))
    print('TIMEOUT rows:', sum(1 for r in rows for k in ('old_verdict', 'new_default_verdict', 'strict_verdict') if r[k] == 'TIMEOUT'))
    # manifest + archive
    man = tsv(f'{S01}/h1_manifest.tsv'); bad = 0; n = 0
    with tarfile.open(f'{S01}/h1_mutants.tar.gz') as tf:
        mem = {os.path.basename(m.name): tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
    byid = {os.path.splitext(k)[0]: v for k, v in mem.items()}
    for r in man:
        bad += sha(byid[r['id']]) != r['mutant_sha256']
    print('\narchive members:', len(mem), '; manifest rows:', len(man), '; sha mismatches (mine):', bad, '; h1_rerun mutant_sha256 equals manifest:', sum(1 for r in rows if r['id'] in byid and r['mutant_sha256'] == sha(byid[r['id']])))
    # controls
    ct = tsv(f'{HW}/controls.tsv')
    print('\ncontrols.tsv rows:', len(ct), '; groups:', dict(collections.Counter((r['group'], r['mode'], r['verdict']) for r in ct)))
    fz = tsv(f'{HW}/fuzz.tsv')
    print('fuzz rows:', len(fz), '; default verdicts:', dict(collections.Counter(r['default_verdict'] for r in fz)), '; strict verdicts:', dict(collections.Counter(r['strict_verdict'] for r in fz)),
          '; panic flags:', sum(1 for r in fz if r['default_panic'] == '1'), sum(1 for r in fz if r['strict_panic'] == '1'), '; exit codes def/strict:', dict(collections.Counter(r['default_exit'] for r in fz)), dict(collections.Counter(r['strict_exit'] for r in fz)))
    ge = tsv(f'{HW}/gen_equivalence.tsv')
    print('gen_equivalence rows:', len(ge), list(ge[0].keys()))
    print('  identical:', [r.get('identical', r.get('old_new_identical', '?')) for r in ge])


# ------------------------------------------------------------------------------------------------ rerun
def sec_rerun():
    rows = {r['id']: r for r in tsv(f'{HW}/h1_rerun.tsv')}
    man = {r['id']: r for r in tsv(f'{S01}/h1_manifest.tsv')}
    AR = arts()
    d = f'{V}/h1'
    if not os.path.isdir(d):
        os.makedirs(d)
        with tarfile.open(f'{S01}/h1_mutants.tar.gz') as tf: tf.extractall(d, filter='data')
    files = {os.path.splitext(os.path.basename(p))[0]: p for p in glob.glob(f'{d}/**/*.txt', recursive=True)}
    rng = random.Random(20261008 + 3)
    ids = sorted(man)
    pick = rng.sample(ids, 30)
    extra = []
    crash = [i for i in ids if rows[i]['old_verdict'] == 'REJECT_CRASH' and man[i]['artifacts'] == 'AAA']
    acc = [i for i in ids if rows[i]['old_verdict'] == 'ACCEPT' and man[i]['artifacts'] == 'AAA' and rows[i]['class'] != 'C00']
    extra += rng.sample(crash, 6) + rng.sample(acc, 6)
    twob = [i for i in ids if 'D' in man[i]['artifacts']]
    extra += rng.sample(twob, 6)
    extra = [i for i in extra if i not in pick]

    def work(i):
        a = man[i]['artifacts']; art = [AR[k][j] for j, k in enumerate(a)]
        out = {}
        th = 2 if 'D' in a else 1
        for name, binary, extra_flags in (('old', OLD, []), ('def', NEW, []), ('strict', NEW, ['--strict'])):
            rc, so, se = run([binary, 'verify'] + extra_flags + art + [files[i]], th=th, timeout=900)
            out[name] = (rc, verd(rc, so), last(so), panic(rc, se))
        return i, out

    def check(group, idlist):
        with ThreadPoolExecutor(2) as ex: res = list(ex.map(work, idlist))
        bad = []; agree = collections.Counter()
        for i, o in res:
            r = rows[i]
            exp = {'old': (int(r['old_exit']), r['old_verdict'], r['old_stdout_last']),
                   'def': (int(r['default_exit']), r['new_default_verdict'], r['default_stdout_last']),
                   'strict': (int(r['strict_exit']), r['strict_verdict'], r['strict_stdout_last'])}
            for k in ('old', 'def', 'strict'):
                got = (o[k][0], o[k][1], o[k][2])
                ok = got == exp[k]
                agree[k] += ok
                if not ok: bad.append((i, k, got, exp[k]))
        print(f'\n[{group}] n={len(res)} classes={dict(collections.Counter(rows[i]["class"] for i, _ in res))}')
        print('   agreement with saved (exit, verdict, last stdout line): ' + str(dict(agree)) + ' ; disagreements:', bad)
        print('   panics new default/strict:', sum(o['def'][3] for _, o in res), sum(o['strict'][3] for _, o in res), '; old panics:', sum(o['old'][3] for _, o in res))
        print('   verdicts now: default', dict(collections.Counter(o['def'][1] for _, o in res)), 'strict', dict(collections.Counter(o['strict'][1] for _, o in res)), 'old', dict(collections.Counter(o['old'][1] for _, o in res)))
        return res
    r1 = check('random 30 of 6161 (seeded)', pick)
    print('   ids:', ' '.join(pick))
    check('6 old-crash + 6 old-accept (op12k) + 6 BitNet-2B-artifact mutants', extra)
    print('   ids:', ' '.join(extra))


# ------------------------------------------------------------------------------------------------ golden
CANON = [r'AEGIS-WITNESS v1-CIS', r'model [0-9a-f]{64}', r'embed [0-9a-f]{64}', r'vocab [0-9a-f]{64}', r'maxtok (0|[1-9][0-9]*)', r'prompt-hex ([0-9a-f]{2})+',
         r'prompt-toks (0|[1-9][0-9]*)', r'gen-toks (0|[1-9][0-9]*)', r'token-ids ((0|[1-9][0-9]*)(,(0|[1-9][0-9]*))*)?', r'cis-digest [0-9a-f]{16}', r'chain [0-9a-f]{64}']


def canon_ok(b):
    """My own implementation of the strict grammar, written from the RESULT.md description (not from the Rust)."""
    try: t = b.decode('ascii')
    except UnicodeDecodeError: return False
    if not t.endswith('\n') or t.endswith('\n\n'): return False
    if any((c != '\n' and not (0x20 <= ord(c) <= 0x7e)) for c in t): return False
    ls = t[:-1].split('\n')
    if len(ls) != 11: return False
    if not all(re.fullmatch(p, l) for p, l in zip(CANON, ls)): return False
    ids = ls[8].split(' ', 1)[1]
    n = 0 if ids == '' else len(ids.split(','))
    return n == int(ls[7].split(' ')[1])


def sec_golden():
    print('golden fixtures in tests/golden (git HEAD unchanged vs 3e3f465 checked separately):')
    for p in sorted(glob.glob(f'{GOLD}/witness_v1_*.receipt')):
        b = open(p, 'rb').read()
        print(f'  {os.path.basename(p):48s} sha256 {sha(b)[:16]} own-strict-grammar={canon_ok(b)}')
    # m7 replay
    g = f'{GOLD}/witness_v1_m7_once64.receipt'
    for mode, fl in (('default', []), ('strict', ['--strict'])):
        rc, so, se = run([NEW, 'verify'] + fl + [f'{M7}/MODEL.SAF', f'{M7}/EMBED.BIN', f'{M7}/VOCAB.BIN', g], th=1, timeout=900)
        print(f'  m7 {mode}: exit={rc} verdict={verd(rc, so)} last="{last(so)}"')
    rc, so, se = run([OLD, 'verify', f'{M7}/MODEL.SAF', f'{M7}/EMBED.BIN', f'{M7}/VOCAB.BIN', g], th=1, timeout=900)
    print(f'  m7 OLD binary default: exit={rc} verdict={verd(rc, so)} last="{last(so)}"')
    # other four: do their model hashes exist anywhere on this host?
    want = {}
    for p in sorted(glob.glob(f'{GOLD}/witness_v1_*.receipt')):
        t = open(p).read().split('\n')
        want[os.path.basename(p)] = {l.split(' ')[0]: l.split(' ')[1] for l in t if l.startswith(('model ', 'embed ', 'vocab '))}
    print('\nwanted artifact hashes (model/embed/vocab prefixes):')
    for k, v in want.items(): print('  ', k, {a: b[:12] for a, b in v.items()})
    cands = []
    for root in (S, '/home/user', '/tmp'):
        for dp, dn, fn in os.walk(root):
            if '/.git' in dp or '/target/' in dp or 'node_modules' in dp: continue
            for f in fn:
                if f in ('MODEL.SAF', 'EMBED.BIN', 'VOCAB.BIN') or f.endswith('.safetensors'):
                    cands.append(os.path.join(dp, f))
    cands = sorted(set(cands))
    print('\nMODEL.SAF/EMBED.BIN/VOCAB.BIN/*.safetensors candidates found:', len(cands))
    wanted_all = {h for v in want.values() for h in v.values()}
    hits = collections.defaultdict(list)
    seen = {}
    for c in cands:
        try:
            sz = os.path.getsize(c)
            key = (os.path.realpath(c))
            if key in seen: h = seen[key]
            else: h = fsha(c); seen[key] = h
        except OSError: continue
        if h in wanted_all: hits[h].append(c)
    print('candidate files whose sha256 equals a golden receipt hash:')
    for h, ps in hits.items():
        names = [k for k, v in want.items() if h in v.values()]
        print('  ', h[:16], '->', names, '|', ps[0])
    missing = {k: [a for a, b in v.items() if b not in hits] for k, v in want.items()}
    print('golden receipts with at least one artifact hash NOT found on this host:', {k: m for k, m in missing.items() if m})


# ------------------------------------------------------------------------------------------------ differential
def mutate(rng, base):
    b = bytearray(base)
    ops = rng.randint(1, 3)
    for _ in range(ops):
        k = rng.randrange(14)
        ls = bytes(b).split(b'\n')
        if k == 0 and len(b) > 1: b[rng.randrange(len(b))] = rng.choice(b'0123456789abcdefxyz +-,\t')
        elif k == 1 and len(b) > 4: i = rng.randrange(len(b) - 2); del b[i:i + rng.randint(1, 3)]
        elif k == 2: i = rng.randrange(len(b) + 1); b[i:i] = rng.choice([b'\r', b'\x00', b'\xff', b' ', b'\t', b'\xc3\xa9', b'+', b'0', b'\n'])
        elif k == 3 and len(ls) > 3: i, j = rng.sample(range(len(ls) - 1), 2); ls[i], ls[j] = ls[j], ls[i]; b = bytearray(b'\n'.join(ls))
        elif k == 4 and len(ls) > 3: i = rng.randrange(len(ls) - 1); ls.insert(i, ls[rng.randrange(len(ls) - 1)]); b = bytearray(b'\n'.join(ls))
        elif k == 5 and len(ls) > 3: i = rng.randrange(len(ls) - 1); del ls[i]; b = bytearray(b'\n'.join(ls))
        elif k == 6: b = bytearray(bytes(b).replace(b'maxtok ', b'maxtok ' + rng.choice([b'', b'+', b'0', b'-1', b'99999999999999999999', b'1e3', b' ']), 1))
        elif k == 7: b = bytearray(re.sub(rb'(prompt-toks|gen-toks) \d+', lambda m: m.group(1) + b' ' + str(rng.randint(0, 99)).encode(), bytes(b), count=1))
        elif k == 8: b = bytearray(bytes(b).upper() if rng.random() < .1 else re.sub(rb'prompt-hex ([0-9a-f]+)', lambda m: b'prompt-hex ' + m.group(1).upper(), bytes(b), count=1))
        elif k == 9: b = bytearray(bytes(b) + rng.choice([b'x-note hi\n', b'\n', b'junk', b'chain 00\n']))
        elif k == 10: b = bytearray(re.sub(rb'token-ids [0-9,]*', lambda m: b'token-ids ' + b','.join(str(rng.randint(0, 2 ** rng.choice([8, 16, 33]))).encode() for _ in range(rng.randint(0, 4))), bytes(b), count=1))
        elif k == 11 and len(b) > 10: b = bytearray(bytes(b)[:rng.randrange(1, len(b))])
        elif k == 12: b = bytearray(re.sub(rb'prompt-hex [0-9a-f]+', b'prompt-hex ' + rng.choice([b'', b'e9', b'c3a9', b'zz', b'41', b'4']), bytes(b), count=1))
        else: b = bytearray(re.sub(rb'(model|embed|vocab|chain|cis-digest) [0-9a-f]+', lambda m: m.group(1) + b' ' + m.group(0).split(b' ')[1][:rng.randint(0, 20)], bytes(b), count=1))
    return bytes(b)


def sec_diff():
    rng = random.Random(918273645)
    recs = sorted(glob.glob(f'{EVID}/qemu_*/RECEIPT*.TXT'))
    print('genuine receipts:', len(recs))
    art = [f'{OP}/MODEL.SAF', f'{OP}/EMBED.BIN', f'{OP}/VOCAB.BIN']
    os.makedirs(f'{V}/diff', exist_ok=True)
    jobs = []
    for n in range(480):
        base = open(rng.choice(recs), 'rb').read()
        m = mutate(rng, base)
        p = f'{V}/diff/m{n:04d}.txt'; open(p, 'wb').write(m)
        jobs.append((n, p, m))
    def work(j):
        n, p, m = j
        o = {}
        for name, binary, fl in (('old', OLD, []), ('def', NEW, []), ('strict', NEW, ['--strict'])):
            rc, so, se = run([binary, 'verify'] + fl + art + [p], th=1, timeout=300)
            o[name] = (rc, verd(rc, so), so, se, panic(rc, se))
        return n, m, o
    with ThreadPoolExecutor(2) as ex: res = list(ex.map(work, jobs))
    # (1) old non-crash -> new default identical (exit code AND full stdout)
    nocrash = [(n, o) for n, m, o in res if o['old'][1] != 'REJECT_CRASH']
    same = sum(1 for n, o in nocrash if o['old'][0] == o['def'][0] and o['old'][2] == o['def'][2])
    print('mutants:', len(res), '; old verdict counts:', dict(collections.Counter(o['old'][1] for _, _, o in res)))
    print('(1) old not crashing:', len(nocrash), '; new default identical exit code and full stdout:', same, '; differing ids:', [n for n, o in nocrash if not (o['old'][0] == o['def'][0] and o['old'][2] == o['def'][2])][:10])
    crash = [(n, o) for n, m, o in res if o['old'][1] == 'REJECT_CRASH']
    print('(2) old crashing:', len(crash), '; old exit codes', dict(collections.Counter(o['old'][0] for _, o in crash)), '; new default verdicts', dict(collections.Counter(o['def'][1] for _, o in crash)), '; new default exit codes', dict(collections.Counter(o['def'][0] for _, o in crash)), '; panic flags', sum(o['def'][4] for _, o in crash))
    print('(3) panics: old', sum(o['old'][4] for _, _, o in res), ' new default', sum(o['def'][4] for _, _, o in res), ' new strict', sum(o['strict'][4] for _, _, o in res))
    print('    new default exit codes', dict(collections.Counter(o['def'][0] for _, _, o in res)), ' strict', dict(collections.Counter(o['strict'][0] for _, _, o in res)))
    sa = [(n, m, o) for n, m, o in res if o['strict'][1] == 'ACCEPT']
    print('(4) strict ACCEPT:', len(sa), '; of those default also ACCEPT:', sum(1 for _, _, o in sa if o['def'][1] == 'ACCEPT'), '; byte-identical to a genuine receipt:', sum(1 for _, m, _ in sa if any(m == open(r, 'rb').read() for r in recs)), '; own-grammar canonical:', sum(1 for _, m, _ in sa if canon_ok(m)))
    da = [(n, m, o) for n, m, o in res if o['def'][1] == 'ACCEPT']
    print('    default ACCEPT:', len(da), '; of those strict-rejected:', sum(1 for _, _, o in da if o['strict'][1] != 'ACCEPT'), '; of those own-grammar NON-canonical:', sum(1 for _, m, _ in da if not canon_ok(m)))
    # strict reject but my grammar says canonical and default accepts?
    leak = [n for n, m, o in res if canon_ok(m) and o['def'][1] == 'ACCEPT' and o['strict'][1] != 'ACCEPT']
    print('(5) own-grammar canonical + default ACCEPT but strict rejects (strict stricter than my reading of its own spec):', leak[:10], len(leak))
    for n, m, o in res:
        if n in leak[:3]: print('    ', n, o['strict'][2].strip().split('\n')[-1])
    # every strict ACCEPT must have prompt-toks == actual: check own grammar plus compare receipts with a genuine line set
    print('(6) default ACCEPT mutants by what changed (first 6 shown):')
    for n, m, o in da[:6]:
        print('    ', n, repr(m[:70]), '...', o['def'][2].strip().split('\n')[-1][:70])


# ------------------------------------------------------------------------------------------------ gen
def sec_gen():
    art = [f'{OP}/MODEL.SAF', f'{OP}/EMBED.BIN', f'{OP}/VOCAB.BIN']
    prompts = [('Q: What is 12 + 30?\nA:', '8'), ('--strict', '5'), ('naïve café ☕ test', '4'), ('', '5'), ('x', '0'), ('Hello world, this is a test of the receipt writer.', '20'), ('Q: Who built you?\nA:', '1')]
    same = 0
    for p, mx in prompts:
        o = run([OLD, 'gen'] + art + [mx, p]); n = run([NEW, 'gen'] + art + [mx, p])
        ok = o[0] == n[0] and o[1] == n[1]
        same += ok
        verdicts = ''
        if n[0] == 0:
            f = f'{V}/gen_{abs(hash(p)) % 10**6}.txt'; open(f, 'w').write(n[1])
            v1 = run([NEW, 'verify'] + art + [f]); v2 = run([NEW, 'verify', '--strict'] + art + [f])
            verdicts = f' default={verd(v1[0], v1[1])} strict={verd(v2[0], v2[1])} canon={canon_ok(n[1].encode())}'
        print(f'  prompt={p[:30]!r:34s} max_new={mx:>3s} old exit={o[0]} new exit={n[0]} stdout identical={o[1] == n[1]} {verdicts}')
        if n[0] != 0: print('     new stderr:', n[2].strip().split('\n')[0][:120], '| old stderr:', o[2].strip().split('\n')[0][:100])
    print('gen byte-identical (exit and stdout):', same, 'of', len(prompts))
    # arg handling
    print('\nargument handling:')
    rc = run([NEW, 'verify'] + art); print('  verify with no receipt arg: exit', rc[0], '|', rc[2].strip().split('\n')[0][:80])
    rc = run([NEW, 'verify', '--strict'] + art + [f'{EVID}/qemu_calc/RECEIPT.TXT']); print('  verify --strict (flag right after mode): exit', rc[0], '|', last(rc[1]))
    rc = run([NEW, 'verify'] + art + [f'{EVID}/qemu_calc/RECEIPT.TXT', '--strict']); print('  verify ... receipt --strict (flag last): exit', rc[0], '|', last(rc[1]))
    rc = run([NEW, 'verify'] + art + ['/nonexistent']); print('  verify unreadable receipt: exit', rc[0], '|', rc[2].strip().split('\n')[0][:90])
    rc = run([OLD, 'verify'] + art + ['/nonexistent']); print('  OLD verify unreadable receipt: exit', rc[0], '|', rc[2].strip().split('\n')[0][:90])


def sec_extreme():
    art = [f'{OP}/MODEL.SAF', f'{OP}/EMBED.BIN', f'{OP}/VOCAB.BIN']
    g = open(f'{EVID}/qemu_calc/RECEIPT.TXT', 'rb').read()
    L = g.split(b'\n')
    def line(k, v):
        return b'\n'.join(v if l.startswith(k + b' ') else l for l in L)
    cases = {
        'empty file': b'', 'single newline': b'\n', 'only header': b'AEGIS-WITNESS v1-CIS\n', 'header no newline': b'AEGIS-WITNESS v1-CIS',
        'NUL x1000': b'\x00' * 1000, '5MB of a': b'a' * 5_000_000, '200k newlines': b'\n' * 200000, 'CR only': b'\r' * 100,
        'maxtok u64 max': line(b'maxtok', b'maxtok 18446744073709551615'), 'maxtok 2^64': line(b'maxtok', b'maxtok 18446744073709551616'),
        'maxtok 2^63': line(b'maxtok', b'maxtok 9223372036854775808'), 'maxtok huge digits': line(b'maxtok', b'maxtok ' + b'9' * 5000),
        'maxtok negative': line(b'maxtok', b'maxtok -1'), 'maxtok empty': line(b'maxtok', b'maxtok '), 'maxtok = usize::MAX-1': line(b'maxtok', b'maxtok 18446744073709551614'),
        'prompt-hex 1MB': line(b'prompt-hex', b'prompt-hex ' + b'41' * 500000), 'prompt-hex odd': line(b'prompt-hex', b'prompt-hex 4'), 'prompt-hex 0xc3 only': line(b'prompt-hex', b'prompt-hex c3'),
        'prompt-hex empty': line(b'prompt-hex', b'prompt-hex '), 'prompt-hex plus': line(b'prompt-hex', b'prompt-hex +1+2'),
        'token-ids 100k': line(b'token-ids', b'token-ids ' + b','.join([b'7'] * 100000)), 'token-ids huge id': line(b'token-ids', b'token-ids 4294967296'),
        'token-ids trailing comma': line(b'token-ids', b'token-ids 1,2,'), 'token-ids double comma': line(b'token-ids', b'token-ids 1,,2'),
        'model 1MB': line(b'model', b'model ' + b'a' * 1000000), 'chain multibyte': line(b'chain', 'chain é'.encode() + b'a' * 30), 'vocab multibyte at 16': line(b'vocab', b'vocab ' + b'a' * 15 + 'é'.encode() + b'a' * 40),
        'utf8 BOM': b'\xef\xbb\xbf' + g, 'utf16': g.decode().encode('utf-16'), 'all 0xff': b'\xff' * 4096,
        'duplicate every line': b'\n'.join(x for l in L for x in (l, l)), 'reversed lines': b'\n'.join(reversed(L)), 'lines joined by space': b' '.join(L),
    }
    os.makedirs(f'{V}/ext', exist_ok=True)
    pan = collections.Counter(); res = []
    for i, (name, data) in enumerate(cases.items()):
        pth = f'{V}/ext/e{i:02d}.txt'; open(pth, 'wb').write(data)
        row = [name]
        for mode, fl in (('def', []), ('strict', ['--strict'])):
            rc, so, se = run([NEW, 'verify'] + fl + art + [pth], th=1, timeout=300)
            pn = panic(rc, se); pan[mode] += pn
            row.append((rc, verd(rc, so), pn, last(so)[:70] or se.strip().split('\n')[0][:70]))
        res.append(row)
    for r in res: print(f'  {r[0]:26s} default={r[1][0]}/{r[1][1]}/panic={int(r[1][2])}  strict={r[2][0]}/{r[2][1]}/panic={int(r[2][2])} | {r[1][3]}')
    print('extreme inputs:', len(cases), '; panics default', pan['def'], 'strict', pan['strict'], '; exit codes default', dict(collections.Counter(r[1][0] for r in res)), 'strict', dict(collections.Counter(r[2][0] for r in res)))


if __name__ == '__main__':
    os.makedirs(V, exist_ok=True)
    {'recount': sec_recount, 'rerun': sec_rerun, 'golden': sec_golden, 'diff': sec_diff, 'gen': sec_gen, 'extreme': sec_extreme}[sys.argv[1]]()
