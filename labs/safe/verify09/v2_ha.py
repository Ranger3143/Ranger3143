"""LAB-09 VERIFY-2, HARDEN-ATTEST skeptic script (python3 -I, nice -n 5, OMP_NUM_THREADS=1).

Usage: python3 -I v2_ha.py <section>
  recount   recompute every headline number from the saved TSVs of HARDEN-ATTEST (own csv reader, own class logic)
  genuine   independent crypto core + hardened verifier on the 8 final boots and all 15 ATTEST.TXT on disk, negative controls
  mutants   independent crypto core over all 351 mutant files, cross-tabulated with the saved T verdicts
  rerun     random 30 mutants (seeded) through the hardened verifier in forms P, D, T, L, compared with the saved verdicts
  byteflip  recount of h3_byteflip.tsv + own random single-byte substitutions through form T
  forgery   S1 sample re-run, S2/S3/S4 forgeries re-run, finalize.sh diff
"""
import sys, os, re, csv, json, random, hashlib, subprocess, tarfile, collections, importlib.util, shutil
from concurrent.futures import ThreadPoolExecutor

R = '/home/user/Ranger3143'
S = '/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
V = f'{S}/verify2'
HA = f'{R}/labs/logs/safe/HARDEN-ATTEST'
SAFE01 = f'{R}/labs/logs/safe/SAFE-01'
EVID = f'{R}/labs/logs/opmodel/final_step12000'
AV = f'{R}/labs/tools/attest_verify.py'
AK = f'{R}/labs/tools/ak_from_swtpm.sh'
EFI = f'{S}/qemu/aegis-uefi-gateway-qemutest.efi'
EFI_DASH = f'{S}/qemu/aegis-uefi-dash-qemutest.efi'
KINDS = ['abstain', 'calc', 'calc_words', 'everyday', 'lookup', 'receipt', 'self', 'unknown_tool']
ENV = dict(os.environ, OMP_NUM_THREADS='1')
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551

spec = importlib.util.spec_from_file_location('v2core', f'{R}/labs/safe/verify09/v2_attestcore.py')
core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)


def tsv(path): return list(csv.DictReader(open(path, newline=''), delimiter='\t'))
def sha(b): return hashlib.sha256(b).hexdigest()


def run(cmd, timeout=180):
    try:
        p = subprocess.run(['nice', '-n', '5'] + cmd, capture_output=True, env=ENV, timeout=timeout)
        return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')
    except subprocess.TimeoutExpired:
        return None, '', 'TIMEOUT'


def verdict(rc, out, err):
    """My own scoring: ACCEPT iff exit 0 and both PASS lines; REJECT iff exit 1; USAGE iff exit 2; else ANOMALY."""
    if rc is None: return 'ANOMALY'
    if rc == 0: return 'ACCEPT' if ('ATTEST VERIFY PASS' in out and 'QUOTE VERIFY PASS' in out) else 'ANOMALY'
    if rc == 1: return 'REJECT' if 'Traceback' not in err else 'ANOMALY'
    if rc == 2: return 'USAGE' if 'Traceback' not in err else 'ANOMALY'
    return 'ANOMALY'


def av(args): return run(['python3', '-I', AV] + args)


def pin_from_state(st):
    env = dict(ENV, AK_WORK=f'{V}/ak')
    os.makedirs(f'{V}/ak', exist_ok=True)
    p = subprocess.run(['nice', '-n', '5', 'bash', AK, st], capture_output=True, env=env, timeout=120)
    return p.stdout.decode().strip() if p.returncode == 0 else ''


def forms(att, rec, pin, efi=EFI):
    return {'P': [att, rec], 'D': [att, '--receipt', rec],
            'T': [att, '--receipt', rec, '--strict', '--expect-pubkey', pin, '--efi', efi],
            'L': [att, '--receipt', rec, '--strict', '--expect-pubkey', pin, '--efi', efi, '--reject-high-s']}


def pins():
    d = {}
    for k in KINDS:
        d[k] = pin_from_state(f'{S}/qemu/shot_final_step12000_{k}/tpm')
    return d


def extract_h3():
    d = f'{V}/h3'
    if not os.path.isdir(d):
        os.makedirs(d)
        with tarfile.open(f'{SAFE01}/h3_mutants.tar.gz') as tf: tf.extractall(d, filter='data')
    return d


def pct(a, b): return f'{a}/{b}'


# ------------------------------------------------------------------------------------------------ recount
def sec_recount():
    rows = tsv(f'{HA}/h3_rerun.tsv'); old = {r['id']: r for r in tsv(f'{SAFE01}/h3_results.tsv')}
    print('rows in h3_rerun.tsv:', len(rows), '; ids in SAFE-01 h3_results.tsv:', len(old))
    print('every h3_rerun id present in SAFE-01 h3_results:', all(r['id'] in old for r in rows))
    print('mutant_sha256 equals SAFE-01 recorded sha256:', sum(1 for r in rows if r['mutant_sha256'] == old[r['id']]['mutant_sha256']), 'of', len(rows))
    print('before_F1/F2 columns equal SAFE-01 F1_verdict/F2_verdict:', sum(1 for r in rows if (r['before_F1_safe01'], r['before_F2_safe01']) == (old[r['id']]['F1_verdict'], old[r['id']]['F2_verdict'])), 'of', len(rows))
    mut = [r for r in rows if r['class'] != 'control']; ctl = [r for r in rows if r['class'] == 'control']
    print('mutants (excl. controls):', len(mut), '; controls:', len(ctl))
    acc = lambda rs, k: sum(1 for r in rs if r[k] == 'ACCEPT')
    print('accepted before F1/F2:', acc(mut, 'before_F1_safe01'), acc(mut, 'before_F2_safe01'))
    print('accepted after D/T/L:', acc(mut, 'after_D'), acc(mut, 'after_T'), acc(mut, 'after_L'))
    print('controls accepted D/T/L:', acc(ctl, 'after_D'), acc(ctl, 'after_T'), acc(ctl, 'after_L'))
    print('P usage error (exit 2):', sum(1 for r in mut if r['after_P_exit'] == '2' and r['after_P'] == 'REJECT_USAGE'), 'of', len(mut))
    print('any non-ACCEPT/REJECT/REJECT_USAGE verdict (anomaly):', sum(1 for r in rows for k in ('after_P', 'after_D', 'after_T', 'after_L') if r[k] not in ('ACCEPT', 'REJECT', 'REJECT_USAGE')))
    # own check of the verdict/exit consistency
    bad = 0
    for r in rows:
        for f in 'PDTL':
            e, v = r[f'after_{f}_exit'], r[f'after_{f}']
            if (e, v) not in (('0', 'ACCEPT'), ('1', 'REJECT'), ('2', 'REJECT_USAGE')): bad += 1
    print('exit-code/verdict inconsistencies:', bad)
    # old accepted semantic vs cosmetic: SAFE-01 split
    sem = [r for r in mut if r['class'] != 'cosmetic']; cos = [r for r in mut if r['class'] == 'cosmetic']
    old_acc = [r for r in mut if r['before_F1_safe01'] == 'ACCEPT' or r['before_F2_safe01'] == 'ACCEPT']
    old_sem = [r for r in old_acc if r['class'] != 'cosmetic']; old_cos = [r for r in old_acc if r['class'] == 'cosmetic']
    print('SAFE-01 accepted under F1 or F2:', len(old_acc), '= semantic', len(old_sem), '+ cosmetic', len(old_cos))
    for f in 'DTL':
        print(f'  of the {len(old_sem)} semantic / {len(old_cos)} cosmetic: {f} accepts', sum(1 for r in old_sem if r[f'after_{f}'] == 'ACCEPT'), '/', sum(1 for r in old_cos if r[f'after_{f}'] == 'ACCEPT'))
    # class table
    print('\nclass: n | F1 F2 D T L accepted')
    for c in sorted({r['class'] for r in mut}):
        rs = [r for r in mut if r['class'] == c]
        print(f'  {c:18s} {len(rs):4d} | ' + ' '.join(str(acc(rs, k)) for k in ('before_F1_safe01', 'before_F2_safe01', 'after_D', 'after_T', 'after_L')))
    # findings, own mapping
    def fnd(r):
        c, s, d = r['class'], r['sub'], r['desc']
        if (c == 'field-deletion' and s == 'quote-attest') or (c == 'cosmetic' and s == 'trailing-space' and 'quote-attest' in d): return '1 fail-open quote'
        if c == 'event-line' and s.startswith('pcr4/'): return '3 PCR4 event edits'
        if c == 'event-line' and s in ('pcr12/type', 'pcr13/type'): return '4 type= of PCR12/13 events'
        if c == 'unread-line' and s in ('quote-pcrs', 'quote-public', 'quote-retries', 'quote-key'): return '5 unread quote-* lines'
        if c == 'sig-malleability': return '6 malleability'
        if c == 'measured-line' and s == 'pcr13/delete': return 'extra: last measured pcr=13 deleted'
        return None
    print('\nfinding: n | F1 F2 D T L accepted')
    g = collections.OrderedDict()
    for r in mut:
        f = fnd(r)
        if f: g.setdefault(f, []).append(r)
    for f, rs in sorted(g.items()):
        print(f'  {f:38s} {len(rs):3d} | ' + ' '.join(str(acc(rs, k)) for k in ('before_F1_safe01', 'before_F2_safe01', 'after_D', 'after_T', 'after_L')))
    print('\nresidual T-accepted mutants:')
    res = [r for r in mut if r['after_T'] == 'ACCEPT']
    for r in res: print('  ', r['id'], r['class'], r['sub'], '|', r['desc'], '| before F1/F2', r['before_F1_safe01'], r['before_F2_safe01'], '| L', r['after_L'])
    print('  by sub-field:', dict(collections.Counter(r['sub'] for r in res)))
    # S1
    s1 = tsv(f'{HA}/h3_s1_rerun.tsv')
    print('\nS1 rows:', len(s1), '; before F1/F2 accepted:', acc(s1, 'before_F1_safe01'), acc(s1, 'before_F2_safe01'), '; after P usage:', sum(1 for r in s1 if r['after_P'] == 'REJECT_USAGE'), '; D/T accepted:', acc(s1, 'after_D'), acc(s1, 'after_T'))
    fr = tsv(f'{HA}/h3_forgery_rerun.tsv')
    print('forgery rows:', len(fr))
    for r in fr: print('  ', r['id'], 'D', r['after_D'], 'T', r['after_T'], 'L', r['after_L'], 'P', r['after_P'])
    # genuine
    gk = tsv(f'{HA}/final_boots_keys.tsv')
    print('\nfinal boot keys: distinct', len({r['quote_key_x_y'] for r in gk}), '; pin==key', sum(int(r['pin_equals_quote_key']) for r in gk), 'of', len(gk), '; high-s (saved column)', sum(1 for r in gk if r['sig_s_form'] == 'high'))
    print('  own high-s count from sig_s column (> n/2):', sum(1 for r in gk if int(r['sig_s'], 16) > N // 2), '; pin string == quote key string:', sum(1 for r in gk if r['quote_key_x_y'] == r['pin_derived_from_swtpm_state']))
    ga = tsv(f'{HA}/genuine_all.tsv')
    print('genuine_all rows:', len(ga), '; D', sum(1 for r in ga if r['D_default'] == 'ACCEPT'), '; strict', sum(1 for r in ga if r['strict_unpinned'] == 'ACCEPT'),
          '; T pinned', sum(1 for r in ga if r['T_strict_pinned_swtpm'] == 'ACCEPT'), '; strict+reject-high-s', sum(1 for r in ga if r['strict_unpinned_reject_high_s'] == 'ACCEPT'),
          '; high-s', sum(1 for r in ga if r['sig_s'] == 'high'))
    fb = tsv(f'{HA}/h3_byteflip.tsv')
    print('\nbyteflip rows:', len(fb), '; accepted by T:', sum(1 for r in fb if r['after_T'] == 'ACCEPT'), '; verdict values:', dict(collections.Counter(r['after_T'] for r in fb)))
    cnt = collections.Counter((r['base'], r['line']) for r in fb if r['after_T'] == 'ACCEPT')
    print('  accepted by (base, line):', dict(cnt))
    tot = collections.Counter((r['base'], r['line']) for r in fb)
    print('  (file, line) pairs total:', len(tot), '; fully rejected pairs:', sum(1 for k in tot if cnt.get(k, 0) == 0))
    print('  bytes per base:', dict(collections.Counter(r['base'] for r in fb)))
    # first-column ranges of accepted for cpuid
    for key in (('qemu_calc', 'cpuid'), ('qemu_calc', 'event pcr=4 #2'), ('qemu_calc', 'quote-retries')):
        cols = sorted(int(r['col']) for r in fb if (r['base'], r['line']) == key and r['after_T'] == 'ACCEPT')
        print('  ', key, 'accepted cols', cols[:6], '...', len(cols))
    # finalize.sh invocation
    fz = open(f'{R}/model/demo-operator/finalize.sh').read()
    print('\nfinalize.sh contains --receipt --strict --expect-pubkey --efi:', all(x in fz for x in ('--receipt', '--strict', '--expect-pubkey', '--efi')))
    print('finalize.sh still contains the old positional call "attest_verify.py $E/ATTEST.TXT $E/RECEIPT.TXT":', bool(re.search(r'\$AV \$E/ATTEST.TXT \$E/RECEIPT.TXT(?! )', fz)))


# ------------------------------------------------------------------------------------------------ genuine
def sec_genuine():
    pn = pins()
    print('pins derived by me from each boot swtpm state: ', {k: pn[k][:16] for k in KINDS})
    keys = {k: core.pubkey_of(f'{EVID}/qemu_{k}/ATTEST.TXT') for k in KINDS}
    print('my pin == quote key in ATTEST.TXT:', sum(1 for k in KINDS if pn[k] == keys[k]), 'of 8 ; distinct pins:', len(set(pn.values())))
    print('\nindependent core (own ECDSA, own replay) on the 8 final boots:')
    for k in KINDS:
        c = core.core(f'{EVID}/qemu_{k}/ATTEST.TXT', f'{EVID}/qemu_{k}/RECEIPT.TXT')
        print(f'  {k:14s} core_ok={c["core_ok"]} sig_s_low={c["sig_s_low"]} failed={c["failed"]}')
    print('\nhardened verifier, exact finalize.sh form (T), D, L, A(=D+--artifacts is not rerun), controls:')
    tally = collections.defaultdict(list)
    for i, k in enumerate(KINDS):
        att, rec = f'{EVID}/qemu_{k}/ATTEST.TXT', f'{EVID}/qemu_{k}/RECEIPT.TXT'
        f = forms(att, rec, pn[k])
        for name in 'PDTL':
            tally[name].append(verdict(*av(f[name])))
        nxt = KINDS[(i + 1) % 8]
        tally['X1 pin of next boot'].append(verdict(*av([att, '--receipt', rec, '--strict', '--expect-pubkey', pn[nxt], '--efi', EFI])))
        tally['X2 receipt of next boot'].append(verdict(*av([att, '--receipt', f'{EVID}/qemu_{nxt}/RECEIPT.TXT', '--strict', '--expect-pubkey', pn[k], '--efi', EFI])))
        tally['X3 wrong EFI'].append(verdict(*av([att, '--receipt', rec, '--strict', '--expect-pubkey', pn[k], '--efi', EFI_DASH])))
        tally['X4 strict without --receipt'].append(verdict(*av([att, '--strict', '--expect-pubkey', pn[k], '--efi', EFI])))
        tally['X5 receipt omitted entirely'].append(verdict(*av([att])))
    for k, v in tally.items(): print(f'  {k:32s} {collections.Counter(v).most_common()}')
    # all 15 files
    print('\nall ATTEST.TXT under labs/logs:')
    files = sorted(os.popen(f'find {R}/labs/logs -name ATTEST.TXT').read().split())
    print('  found', len(files))
    ok_d = ok_s = ok_core = 0
    for f in files:
        rec = os.path.join(os.path.dirname(f), 'RECEIPT.TXT')
        d = verdict(*av([f, '--receipt', rec])); s = verdict(*av([f, '--receipt', rec, '--strict']))
        c = core.core(f, rec)
        ok_d += d == 'ACCEPT'; ok_s += s == 'ACCEPT'; ok_core += c['core_ok']
        print(f'  {f.replace(R + "/labs/logs/", ""):55s} D={d} strict={s} core_ok={c["core_ok"]} low-s={c["sig_s_low"]} failed={c["failed"]}')
    print(f'  totals: D {ok_d}/{len(files)} strict {ok_s}/{len(files)} core {ok_core}/{len(files)}')
    print('\nFINALIZE.log sha256 now:', sha(open(f'{EVID}/FINALIZE.log', 'rb').read()))


# ------------------------------------------------------------------------------------------------ mutants (core cross-tab)
def sec_mutants():
    d = extract_h3(); rows = tsv(f'{HA}/h3_rerun.tsv')
    recp = {b: f'{EVID}/{b}/RECEIPT.TXT' for b in ('qemu_calc', 'qemu_self')}
    xt = collections.Counter(); false_accept = []; core_ok_but_T_reject = collections.Counter(); core_fail_reasons = collections.Counter()
    for r in rows:
        ap = f'{d}/{r["id"]}/ATTEST.TXT'
        if not os.path.exists(ap): ap = f'{d}/{r["id"]}'
        c = core.core(ap, recp[r['base']])
        T = r['after_T']
        xt[(c['core_ok'], T)] += 1
        if T == 'ACCEPT' and not c['core_ok']: false_accept.append((r['id'], c['failed']))
        if c['core_ok'] and T != 'ACCEPT': core_ok_but_T_reject[(r['class'], r['sub'])] += 1
        if not c['core_ok']:
            for f in c['failed']: core_fail_reasons[f] += 1
    print('rows:', len(rows))
    print('cross-tab (my core_ok, saved T verdict):', dict(xt))
    print('T accepted but my independent core says inconsistent (false accepts):', false_accept)
    print('core consistent but T rejected, by (class, sub):', dict(core_ok_but_T_reject))
    print('my-core failure reasons among mutants (a mutant can have several):', dict(core_fail_reasons))
    # the 10 residuals: show that the signature really verifies
    res = [r for r in rows if r['after_T'] == 'ACCEPT' and r['class'] != 'control']
    print('\nresiduals, my core:')
    for r in res:
        ap = f'{d}/{r["id"]}/ATTEST.TXT'
        if not os.path.exists(ap): ap = f'{d}/{r["id"]}'
        c = core.core(ap, recp[r['base']])
        print('  ', r['id'], r['sub'], 'core_ok', c['core_ok'], 'sig_s_low', c['sig_s_low'], 'failed', c['failed'])


# ------------------------------------------------------------------------------------------------ rerun 30
def sec_rerun():
    d = extract_h3(); rows = tsv(f'{HA}/h3_rerun.tsv')
    mut = [r for r in rows if r['class'] != 'control']
    rng = random.Random(20261008 + 2)
    pick = rng.sample(mut, 30)
    # make sure the sample is not trivially all rejects: report composition, do not alter
    pn = pins()
    print('pins (mine): calc', pn['calc'][:16], 'self', pn['self'][:16])
    recp = {'qemu_calc': f'{EVID}/qemu_calc/RECEIPT.TXT', 'qemu_self': f'{EVID}/qemu_self/RECEIPT.TXT'}
    pinb = {'qemu_calc': pn['calc'], 'qemu_self': pn['self']}
    def work(r):
        ap = f'{d}/{r["id"]}/ATTEST.TXT'
        if not os.path.exists(ap): ap = f'{d}/{r["id"]}'
        assert sha(open(ap, 'rb').read()) == r['mutant_sha256']
        f = forms(ap, recp[r['base']], pinb[r['base']])
        return r, {k: verdict(*av(f[k])) for k in 'PDTL'}
    with ThreadPoolExecutor(2) as ex: out = list(ex.map(work, pick))
    agree = collections.Counter(); bad = []
    for r, v in out:
        for k in 'PDTL':
            saved = r[f'after_{k}']
            saved = 'USAGE' if saved == 'REJECT_USAGE' else saved
            agree[k] += v[k] == saved
            if v[k] != saved: bad.append((r['id'], k, v[k], saved))
    print('sample of 30 (seeded):', collections.Counter((r['class']) for r, _ in out))
    print('sample ids:', ' '.join(r['id'] for r, _ in out))
    print('agreement with the saved verdicts per form (of 30):', dict(agree), '; disagreements:', bad)
    print('sample verdicts D/T/L accepted:', {k: sum(1 for _, v in out if v[k] == 'ACCEPT') for k in 'DTL'}, '; P usage:', sum(1 for _, v in out if v['P'] == 'USAGE'))
    print('sample members accepted by saved F1 (SAFE-01):', sum(1 for r, _ in out if r['before_F1_safe01'] == 'ACCEPT'))
    # second sample, biased to the previously accepted ones (all 88 old-accepted are not rerun here, but 30 of them)
    old = [r for r in mut if r['before_F1_safe01'] == 'ACCEPT' or r['before_F2_safe01'] == 'ACCEPT']
    pick2 = rng.sample(old, 30)
    with ThreadPoolExecutor(2) as ex: out2 = list(ex.map(work, pick2))
    agree2 = collections.Counter(); bad2 = []
    for r, v in out2:
        for k in 'PDTL':
            saved = r[f'after_{k}']; saved = 'USAGE' if saved == 'REJECT_USAGE' else saved
            agree2[k] += v[k] == saved
            if v[k] != saved: bad2.append((r['id'], k, v[k], saved))
    print('\nsecond sample: 30 of the 88 SAFE-01-accepted mutants:', collections.Counter(r['class'] for r, _ in out2))
    print('agreement per form (of 30):', dict(agree2), '; disagreements:', bad2)
    print('accepted D/T/L:', {k: sum(1 for _, v in out2 if v[k] == 'ACCEPT') for k in 'DTL'}, '; accepted ids under T:', [r['id'] for r, v in out2 if v['T'] == 'ACCEPT'])


# ------------------------------------------------------------------------------------------------ byteflip
def sec_byteflip():
    pn = pins()
    rng = random.Random(7771)
    res = []
    for base, kind in (('qemu_calc', 'calc'), ('qemu_self', 'self')):
        orig = open(f'{EVID}/{base}/ATTEST.TXT', 'rb').read()
        # line spans
        spans = []; o = 0
        for ln in orig.split(b'\n'):
            spans.append((o, o + len(ln), ln)); o += len(ln) + 1
        def lname(off):
            for i, (a, b, ln) in enumerate(spans):
                if a <= off <= b: return i, ln
        # sample: 130 uniform random bytes + every byte of the three claimed-soft lines is NOT used (to test the claim from outside): 60 random bytes inside each of cpuid, event pcr=4 #2, quote-retries
        offs = rng.sample(range(len(orig)), 130)
        for i, (a, b, ln) in enumerate(spans):
            if ln.startswith(b'cpuid') or ln.startswith(b'quote-retries') or (ln.startswith(b'event pcr=4') and b'type=0x80000003' in ln):
                offs += rng.sample(range(a, b), min(60, b - a)) if ln.startswith(b'cpuid') or ln.startswith(b'event') else list(range(a, b))
        offs = sorted(set(offs))
        for off in offs:
            c = orig[off:off + 1]
            # own substitution rule: different from the report's "next char" rule: random other char from the same class, or X
            if c in b'0123456789abcdef': pool = [x for x in b'0123456789abcdef' if x != c[0]]
            elif c.isalpha(): pool = [x for x in b'ghijklmnopqrstuvwxyzGHIJKLMNOPQRSTUVWXYZ' if x != c[0]]
            elif c.isdigit(): pool = [x for x in b'0123456789' if x != c[0]]
            elif c == b'\n': pool = [0x20]
            else: pool = [ord('X'), ord('0')]
            nb = bytes([rng.choice(pool)])
            res.append((base, kind, off, orig[:off] + nb + orig[off + 1:], lname(off)))
    os.makedirs(f'{V}/bf', exist_ok=True)
    def work(j):
        i, (base, kind, off, data, (li, ln)) = j
        p = f'{V}/bf/{i}.TXT'; open(p, 'wb').write(data)
        f = forms(p, f'{EVID}/{base}/RECEIPT.TXT', pn[kind])['T']
        v = verdict(*av(f)); os.remove(p)
        return (base, off, li, ln[:14].decode('latin1'), v)
    with ThreadPoolExecutor(2) as ex: out = list(ex.map(work, list(enumerate(res))))
    print('own single-byte substitutions through form T:', len(out), '; verdicts:', dict(collections.Counter(o[4] for o in out)))
    acc = [o for o in out if o[4] == 'ACCEPT']
    lines = collections.Counter(re.sub(r'(event pcr=4).*', r'\1', o[3].strip()) for o in acc)
    print('accepted by line prefix:', dict(lines))
    soft = lambda s: s.startswith('cpuid') or s.startswith('quote-retries') or s.startswith('event pcr=4')
    print('accepted outside the three claimed-soft lines (cpuid, event pcr=4, quote-retries):', [o for o in acc if not soft(o[3])])
    print('accepted event pcr=4 lines are all the third (image-load) event:', all(('type=0x80000003' in open(f'{EVID}/{o[0]}/ATTEST.TXT').read().split('\n')[o[2]]) for o in acc if o[3].startswith('event pcr=4')))
    print('anomalies:', sum(1 for o in out if o[4] == 'ANOMALY'))
    print('rejected lines among sample (prefix counts):', dict(collections.Counter(o[3].strip()[:12] for o in out if o[4] != 'ACCEPT')))


# ------------------------------------------------------------------------------------------------ forgery
def sec_forgery():
    pn = pins(); d = extract_h3()
    # S1 sample
    rng = random.Random(4242)
    s1src = sorted(os.popen(f'ls -d {S}/safe01/h3/S1_*/RECEIPT.TXT').read().split())
    print('S1 receipts on disk:', len(s1src))
    pick = rng.sample(s1src, 12)
    out = []
    for p in pick:
        m = re.match(r'.*/S1_(qemu_(?:calc|self))_([a-z-]+)_(\d)/RECEIPT.TXT$', p); b = m.group(1); kind = b[5:]
        att = f'{EVID}/{b}/ATTEST.TXT'
        f = forms(att, p, pn[kind])
        out.append((p.split('/')[-2], {k: verdict(*av(f[k])) for k in 'PDTL'}))
    for o in out: print('  ', o[0], o[1])
    print('S1 sample: D accepts', sum(1 for _, v in out if v['D'] == 'ACCEPT'), 'T accepts', sum(1 for _, v in out if v['T'] == 'ACCEPT'), 'P usage', sum(1 for _, v in out if v['P'] == 'USAGE'), 'of', len(out))
    # forgeries
    fd = f'{V}/forge'; shutil.rmtree(fd, ignore_errors=True); os.makedirs(fd)
    with tarfile.open(f'{HA}/h3_s3_forgeries.tar.gz') as tf:
        names = tf.getnames(); tf.extractall(fd, filter='data')
    print('\nforgery tarball members:', len(names), names[:12])
    dirs = sorted({n.split('/')[0] for n in names if '/' in n})
    for dn in dirs:
        base = 'qemu_calc' if 'calc' in dn else 'qemu_self'; kind = base[5:]
        att = f'{fd}/{dn}/ATTEST.TXT'; rec = f'{fd}/{dn}/RECEIPT.TXT'
        if not os.path.exists(att): continue
        f = forms(att, rec, pn[kind])
        v = {k: verdict(*av(f[k])) for k in 'PDTL'}
        c = core.core(att, rec)
        print(f'  {dn:36s} {v}  my_core_ok={c["core_ok"]} failed={c["failed"]} key==pin:{core.pubkey_of(att) == pn[kind]}')
    for dn in ('forge_pcr13-line-edit', 'forge_receipt-chain-edit'):
        att = f'{d}/{dn}/ATTEST.TXT'
        if os.path.exists(att):
            base = 'qemu_calc' if 'pcr13' in dn else 'qemu_self'; kind = base[5:]
            f = forms(att, f'{d}/{dn}/RECEIPT.TXT', pn[kind]); v = {k: verdict(*av(f[k])) for k in 'PDTL'}
            c = core.core(att, f'{d}/{dn}/RECEIPT.TXT')
            print(f'  SAFE-01 S2 {dn:30s} {v}  my_core_ok={c["core_ok"]} failed={c["failed"]}')
    # finalize diff
    print('\n--- diff finalize_before.sh finalize.sh')
    print(subprocess.run(['diff', f'{HA}/finalize_before.sh', f'{R}/model/demo-operator/finalize.sh'], capture_output=True, text=True).stdout[:6000])


if __name__ == '__main__':
    os.makedirs(V, exist_ok=True)
    {'recount': sec_recount, 'genuine': sec_genuine, 'mutants': sec_mutants, 'rerun': sec_rerun, 'byteflip': sec_byteflip, 'forgery': sec_forgery}[sys.argv[1]]()
