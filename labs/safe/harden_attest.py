#!/usr/bin/env python3
"""LAB-09 HARDEN-ATTEST: re-run the SAFE-01 H3 attacks against the hardened labs/tools/attest_verify.py.

Run as:  python3 -I harden_attest.py {run|bytes|report}
  run     genuine boots (final_step12000 x8, dashboard, older), every SAFE-01 H3 mutant, S1 receipt tampering, S2 and S3
          forgeries, through the hardened verifier in four forms (P, D, T, L below); the pre-hardening verifier is re-run
          on the same inputs as a reproducibility check of the SAFE-01 "before" verdicts.
          Writes final_boots_recheck.log, h3_rerun.tsv, h3_s1_rerun.tsv, h3_forgery_rerun.tsv, genuine_all.tsv,
          final_boots_keys.tsv, provenance.txt into labs/logs/safe/HARDEN-ATTEST/.
  bytes   (additional, unregistered) exhaustive single-byte substitution: every byte position of qemu_calc/ATTEST.TXT and
          qemu_self/ATTEST.TXT replaced once, each mutant through form T -> h3_byteflip.tsv
  report  reads ONLY those saved logs and the SAFE-01 TSVs and writes RESULT.md (Rule B).

Forms (all `python3 -I`, nice -n 5):
  P  attest_verify.py ATTEST RECEIPT                                              (the old finalize.sh form: must be a usage error)
  D  attest_verify.py ATTEST --receipt RECEIPT                                    (hardened, default flags)
  T  attest_verify.py ATTEST --receipt RECEIPT --strict --expect-pubkey PIN --efi EFI   (the finalize.sh form)
  L  T + --reject-high-s
PIN is derived from the boot's swtpm state by labs/tools/ak_from_swtpm.sh, never from the ATTEST.TXT under test.
Rule A: no timing or rate is measured. Nothing under alice-aegis is modified.
"""
import sys, os, re, json, hashlib, subprocess, shutil, tarfile, collections, csv, glob, datetime
from concurrent.futures import ThreadPoolExecutor

R = '/home/user/Ranger3143'
S = '/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad'
EVID = f'{R}/labs/logs/opmodel/final_step12000'
DASH = f'{R}/labs/logs/dashboard'
OUT = f'{R}/labs/logs/safe/HARDEN-ATTEST'
SAFE01 = f'{R}/labs/logs/safe/SAFE-01'
AV = f'{R}/labs/tools/attest_verify.py'
AV_OLD = f'{OUT}/attest_verify_before.py'
AK_SH = f'{R}/labs/tools/ak_from_swtpm.sh'
EFI = f'{S}/qemu/aegis-uefi-gateway-qemutest.efi'
EFI_DASH = f'{S}/qemu/aegis-uefi-dash-qemutest.efi'
ARTDIR = f'{S}/opmodel/exports/final_step12000/artifacts'
SCR = f'{S}/harden_attest'
KINDS = ['abstain', 'calc', 'calc_words', 'everyday', 'lookup', 'receipt', 'self', 'unknown_tool']
OTHERS = {  # older ATTEST.TXT files on disk: name -> (dir, swtpm state dir if the boot's own state is known by name)
    'dashboard/mint': (f'{DASH}/mint', f'{S}/qemu/shot_mint_final2/tpm'),
    'dashboard/verify': (f'{DASH}/verify', f'{S}/qemu/shot_verify_final/tpm'),
    'opmodel/qemu_step2300_gateway_calc': (f'{R}/labs/logs/opmodel/qemu_step2300_gateway_calc', None),
    'opmodel/qemu_step2300_gateway_lookup': (f'{R}/labs/logs/opmodel/qemu_step2300_gateway_lookup', None),
    'opmodel/qemu_step2300_self': (f'{R}/labs/logs/opmodel/qemu_step2300_self', None),
    'qemu/run_attest_mint2': (f'{R}/labs/logs/qemu/run_attest_mint2', None),
    'qemu/run_attest_verify2': (f'{R}/labs/logs/qemu/run_attest_verify2', None),
}
P256_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
ENV = dict(os.environ, OMP_NUM_THREADS='1')
WORKERS = 2


def sha(b): return hashlib.sha256(b).hexdigest()
def filesha(p): return sha(open(p, 'rb').read())
def clean(s, n=300): return re.sub(r'[\t\r\n]+', ' | ', str(s)).strip()[:n]


def run(cmd, timeout=180):
    try:
        p = subprocess.run(['nice', '-n', '5'] + cmd, capture_output=True, env=ENV, timeout=timeout)
        return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')
    except subprocess.TimeoutExpired:
        return None, '', 'TIMEOUT'


def av(av_path, args): return run(['python3', '-I', av_path] + args)


def bad_lines(out):
    return [l for l in out.split('\n') if re.search(r'(FAIL|MISSING|ERROR)', l) and not l.startswith('note:')]


def verdict_after(rc, out, err):
    """FIXED SCORING RULE. ACCEPT iff exit 0 and both `ATTEST VERIFY PASS` and `QUOTE VERIFY PASS` were printed.
    REJECT iff exit 1 (a FAIL/MISSING/ERROR line). REJECT_USAGE iff exit 2. Everything else is an ANOMALY and is counted."""
    if rc is None: return 'ANOMALY_TIMEOUT'
    if rc == 0: return 'ACCEPT' if ('ATTEST VERIFY PASS' in out and 'QUOTE VERIFY PASS' in out) else 'ANOMALY_EXIT0_WITHOUT_PASS_LINES'
    if rc == 1: return 'REJECT' if 'Traceback' not in err else 'ANOMALY_TRACEBACK'
    if rc == 2: return 'REJECT_USAGE' if 'Traceback' not in err else 'ANOMALY_TRACEBACK'
    return 'ANOMALY_EXIT_%s' % rc


def verdict_before(rc): return 'ACCEPT' if rc == 0 else 'REJECT'


def write_tsv(path, header, rows):
    with open(path, 'w') as f:
        f.write('\t'.join(header) + '\n')
        for r in rows: f.write('\t'.join(clean(x) for x in r) + '\n')


def read_tsv(path):
    return list(csv.DictReader(open(path, newline=''), delimiter='\t'))


def pin_from_state(state_dir):
    env = dict(ENV, AK_WORK=SCR)
    p = subprocess.run(['nice', '-n', '5', 'bash', AK_SH, state_dir], capture_output=True, env=env, timeout=120)
    return p.stdout.decode().strip() if p.returncode == 0 else ''


def sig_s(attest_path):
    t = open(attest_path).read()
    return int(re.search(r'^quote-sig-s ([0-9a-fA-F]+)$', t, re.M).group(1), 16)


def key_of(attest_path):
    t = open(attest_path).read()
    return re.search(r'^quote-pub-x (\w+)$', t, re.M).group(1) + re.search(r'^quote-pub-y (\w+)$', t, re.M).group(1)


# ------------------------------------------------------------------------------------------- forgeries (S3)
def der_int_parse(der):
    assert der[0] == 0x30
    o = 2 if der[1] < 0x80 else 3
    assert der[o] == 0x02; lr = der[o + 1]; r = int.from_bytes(der[o + 2:o + 2 + lr], 'big'); o += 2 + lr
    assert der[o] == 0x02; ls = der[o + 1]; s = int.from_bytes(der[o + 2:o + 2 + ls], 'big')
    return r, s


def forge_consistent(tag, base, tamper_receipt):
    """S3 (new, supplementary): like SAFE-01's S2 forgery but fully self-consistent. The edited ATTEST.TXT is re-signed with
    a fresh software P-256 key AND the quote-public / quote-pub-x/y lines and the signed qualifiedSigner name are rewritten
    to that key, so every internal consistency check passes. Only a pinned signer can tell it from a TPM quote."""
    d = f'{SCR}/s3/{tag}'; os.makedirs(d, exist_ok=True)
    t = open(f'{EVID}/{base}/ATTEST.TXT').read(); L = t[:-1].split('\n')
    rec = open(f'{EVID}/{base}/RECEIPT.TXT').read()
    if tamper_receipt:
        m = re.search(r'^chain ([0-9a-f]{64})$', rec, re.M); newchain = ('0' if m.group(1)[0] != '0' else '1') + m.group(1)[1:]
        rec2 = rec.replace(m.group(1), newchain); L = [l.replace(m.group(1), newchain) for l in L]
    else:
        rec2 = rec
        L = [re.sub(r'verdict=MINTED$', 'verdict=MINTEX', l) if l.startswith('measured pcr=13') or (l.startswith('event pcr=13') and l.endswith('verdict=MINTED')) else l for l in L]
    h = lambda b: hashlib.sha256(b).digest()
    measured = collections.defaultdict(list)
    for l in L:
        m = re.match(r'^measured pcr=(\d+) (.*)$', l)
        if m: measured[int(m.group(1))].append(m.group(2))
    newL = []
    for l in L:
        m = re.match(r'^event pcr=(\d+) type=(0x[0-9a-f]+) sha256=([0-9a-f]{64}) data=(.*)$', l)
        if m and int(m.group(1)) in (12, 13): l = f'event pcr={m.group(1)} type={m.group(2)} sha256={h(m.group(4).encode()).hex()} data={m.group(4)}'
        newL.append(l)
    L = newL
    pcr = {int(m.group(1)): bytes.fromhex(m.group(2)) for l in L if (m := re.match(r'^pcr (\d+) ([0-9a-f]{64})$', l))}
    for p in (12, 13):
        v = bytes(32)
        for x in measured[p]: v = h(v + h(x.encode()))
        pcr[p] = v
    L = [f'pcr {m.group(1)} {pcr[int(m.group(1))].hex()}' if (m := re.match(r'^pcr (\d+) ', l)) else l for l in L]
    kvs = dict(re.findall(r'^(quote-[a-z-]+) (\S+)$', t, re.M))
    subprocess.run(['openssl', 'ecparam', '-name', 'prime256v1', '-genkey', '-noout', '-out', f'{d}/k.pem'], check=True, capture_output=True)
    der = subprocess.run(['openssl', 'ec', '-in', f'{d}/k.pem', '-pubout', '-outform', 'DER'], check=True, capture_output=True).stdout
    pt = der[-65:]; assert pt[0] == 4
    nx, ny = pt[1:33], pt[33:65]
    pub = bytearray(bytes.fromhex(kvs['quote-public'])); assert pub[-68:-66] == b'\x00\x20' and pub[-34:-32] == b'\x00\x20'
    pub[-66:-34] = nx; pub[-32:] = ny; pub = bytes(pub)
    qn = b'\x00\x0b' + h(bytes.fromhex('40000001') + b'\x00\x0b' + h(pub))
    att = bytearray(bytes.fromhex(kvs['quote-attest']))
    n = int.from_bytes(att[6:8], 'big'); assert n == 34
    att[8:8 + n] = qn                                                     # signed qualifiedSigner now names the software key
    att[-32:] = h(pcr[4] + pcr[12] + pcr[13])
    if tamper_receipt:
        q = h(rec2.encode()); old = bytes.fromhex(kvs['quote-qualifying']); k = bytes(att).index(old); att[k:k + 32] = q
        L = [f'quote-qualifying {q.hex()}' if l.startswith('quote-qualifying ') else l for l in L]
    open(f'{d}/attest.bin', 'wb').write(att)
    subprocess.run(['openssl', 'dgst', '-sha256', '-sign', f'{d}/k.pem', '-out', f'{d}/sig.der', f'{d}/attest.bin'], check=True, capture_output=True)
    r, s = der_int_parse(open(f'{d}/sig.der', 'rb').read())
    rep = {'quote-attest': bytes(att).hex(), 'quote-sig-r': f'{r:064x}', 'quote-sig-s': f'{s:064x}', 'quote-pub-x': nx.hex(), 'quote-pub-y': ny.hex(), 'quote-public': pub.hex()}
    L = [f'{l.split()[0]} {rep[l.split()[0]]}' if l.split()[0] in rep else l for l in L]
    open(f'{d}/ATTEST.TXT', 'w').write('\n'.join(L) + '\n'); open(f'{d}/RECEIPT.TXT', 'w').write(rec2)
    os.remove(f'{d}/k.pem')                                               # the throwaway key is not kept
    return d



def forge_unattested(base):
    """S4 (new, supplementary): a genuine ATTEST.TXT plus a fully self-consistent claim about PCR 14 (measured line, event line,
    pcr line). The quote selects only PCRs 4, 12, 13, so nothing signed covers it: the claim is unattested."""
    d = f'{SCR}/s4/{base}'; os.makedirs(d, exist_ok=True)
    t = open(f'{EVID}/{base}/ATTEST.TXT').read().split('\n')
    txt = 'AEGIS-MEASURE v0 artifact=EVIL.BIN bytes=1 sha256=' + '0' * 64
    dg = hashlib.sha256(txt.encode()).digest(); pcr = hashlib.sha256(bytes(32) + dg).hexdigest()
    i = max(k for k, l in enumerate(t) if l.startswith('measured pcr=13')); t.insert(i + 1, 'measured pcr=14 ' + txt)
    j = max(k for k, l in enumerate(t) if l.startswith('event pcr=13')); t.insert(j + 1, f'event pcr=14 type=0xd sha256={dg.hex()} data={txt}')
    k = [k for k, l in enumerate(t) if l.startswith('pcr 13')][0]; t.insert(k + 1, 'pcr 14 ' + pcr)
    open(f'{d}/ATTEST.TXT', 'w').write('\n'.join(t)); shutil.copy(f'{EVID}/{base}/RECEIPT.TXT', f'{d}/RECEIPT.TXT')
    return d

# ------------------------------------------------------------------------------------------- run
def forms(att, rec, pin, efi=EFI):
    return {
        'P': [att, rec],
        'D': [att, '--receipt', rec],
        'T': [att, '--receipt', rec, '--strict', '--expect-pubkey', pin, '--efi', efi],
        'L': [att, '--receipt', rec, '--strict', '--expect-pubkey', pin, '--efi', efi, '--reject-high-s'],
    }


def run_forms(att, rec, pin):
    res = {}
    for k, a in forms(att, rec, pin).items():
        rc, out, err = av(AV, a)
        why = (' || '.join(bad_lines(out)[:3]) or err.strip().split('\n')[-1]) if rc != 0 else ''
        res[k] = (rc, verdict_after(rc, out, err), clean(why, 300), int(bool(bad_lines(out))), out, err)
    return res


def do_run():
    os.makedirs(OUT, exist_ok=True); shutil.rmtree(f'{SCR}/s3', ignore_errors=True); shutil.rmtree(f'{SCR}/s4', ignore_errors=True); os.makedirs(SCR, exist_ok=True)
    log = open(f'{OUT}/run_harden.log', 'w')
    def say(*a):
        s = ' '.join(str(x) for x in a); print(s, flush=True); log.write(s + '\n'); log.flush()
    say('HARDEN-ATTEST run', datetime.date.today().isoformat())
    # provenance
    prov = {
        'attest_verify.py (hardened)': filesha(AV), 'attest_verify_before.py': filesha(AV_OLD),
        'ak_from_swtpm.sh': filesha(AK_SH), 'finalize.sh': filesha(f'{R}/model/demo-operator/finalize.sh'),
        'SAFE-01 h3_mutants.tar.gz': filesha(f'{SAFE01}/h3_mutants.tar.gz'), 'SAFE-01 h3_results.tsv': filesha(f'{SAFE01}/h3_results.tsv'),
        'FINALIZE.log (final_step12000, must stay unchanged)': filesha(f'{EVID}/FINALIZE.log'),
        'EFI aegis-uefi-gateway-qemutest.efi': filesha(EFI), 'EFI aegis-uefi-dash-qemutest.efi': filesha(EFI_DASH),
    }
    for k in KINDS:
        prov[f'qemu_{k}/ATTEST.TXT'] = filesha(f'{EVID}/qemu_{k}/ATTEST.TXT'); prov[f'qemu_{k}/RECEIPT.TXT'] = filesha(f'{EVID}/qemu_{k}/RECEIPT.TXT')
    with open(f'{OUT}/provenance.txt', 'w') as f:
        for k, v in prov.items(): f.write(f'{v}  {k}\n')
    say('openssl:', subprocess.run(['openssl', 'version'], capture_output=True, text=True).stdout.strip(), '| python', sys.version.split()[0])

    # --- keys and pins of the 8 final boots
    pins = {}; krows = []
    for k in KINDS:
        att = f'{EVID}/qemu_{k}/ATTEST.TXT'; st = f'{S}/qemu/shot_final_step12000_{k}/tpm'
        pin = pin_from_state(st); pins[k] = pin
        krows.append((f'qemu_{k}', key_of(att), pin, int(pin == key_of(att)), 'low' if sig_s(att) <= P256_N // 2 else 'high', f'{sig_s(att):064x}'))
    write_tsv(f'{OUT}/final_boots_keys.tsv', ['boot', 'quote_key_x_y', 'pin_derived_from_swtpm_state', 'pin_equals_quote_key', 'sig_s_form', 'sig_s'], krows)
    say('final boots: distinct quote keys =', len({r[1] for r in krows}), '; pins equal to quote key =', sum(r[3] for r in krows), 'of', len(krows),
        '; high-s =', sum(1 for r in krows if r[4] == 'high'))

    # --- (iii) the recheck log of the 8 final boots: exact finalize.sh invocation + controls
    rl = open(f'{OUT}/final_boots_recheck.log', 'w')
    def rsay(s=''): rl.write(s + '\n')
    rsay('HARDEN-ATTEST recheck of the 8 final_step12000 QEMU boots with the hardened labs/tools/attest_verify.py')
    rsay(f'verifier sha256 {filesha(AV)}   FINALIZE.log sha256 {filesha(f"{EVID}/FINALIZE.log")} (read-only, never edited)')
    rsay('For every boot: PIN = labs/tools/ak_from_swtpm.sh <that boot\'s own swtpm state dir>; the invocation is the one now in model/demo-operator/finalize.sh')
    rsay('')
    ctl = collections.OrderedDict()
    for i, k in enumerate(KINDS):
        att = f'{EVID}/qemu_{k}/ATTEST.TXT'; rec = f'{EVID}/qemu_{k}/RECEIPT.TXT'
        a = forms(att, rec, pins[k])['T']
        rc, out, err = av(AV, a)
        rsay(f'===== qemu_{k}')
        rsay(f'pin (derived from swtpm state of this boot): {pins[k]}')
        rsay('$ python3 -I labs/tools/attest_verify.py ' + ' '.join(x.replace(R + '/', '').replace(S, '$S') for x in a))
        rsay(out.rstrip()); rsay(f'exit={rc}  verdict={verdict_after(rc, out, err)}'); rsay('')
        ctl.setdefault('T finalize form', []).append(verdict_after(rc, out, err))
        r2 = run_forms(att, rec, pins[k])
        ctl.setdefault('D default flags', []).append(r2['D'][1]); ctl.setdefault('L T + --reject-high-s', []).append(r2['L'][1])
        ctl.setdefault('P old positional form', []).append(r2['P'][1])
        rc, out, err = av(AV, [att, '--receipt', rec, '--artifacts', ARTDIR]); ctl.setdefault('A default + --artifacts (op12k trio)', []).append(verdict_after(rc, out, err))
        nxt = KINDS[(i + 1) % len(KINDS)]
        rc, out, err = av(AV, [att, '--receipt', rec, '--strict', '--expect-pubkey', pins[nxt], '--efi', EFI]); ctl.setdefault('X1 control: pin of the next boot', []).append(verdict_after(rc, out, err))
        rc, out, err = av(AV, [att, '--receipt', f'{EVID}/qemu_{nxt}/RECEIPT.TXT', '--strict', '--expect-pubkey', pins[k], '--efi', EFI]); ctl.setdefault('X2 control: receipt of the next boot', []).append(verdict_after(rc, out, err))
        rc, out, err = av(AV, [att, '--receipt', rec, '--strict', '--expect-pubkey', pins[k], '--efi', EFI_DASH]); ctl.setdefault('X3 control: wrong EFI (dashboard image)', []).append(verdict_after(rc, out, err))
        rc, out, err = av(AV, [att, '--strict', '--expect-pubkey', pins[k], '--efi', EFI]); ctl.setdefault('X4 control: --strict without --receipt', []).append(verdict_after(rc, out, err))
    rsay('===== summary (verdict per boot, order: ' + ', '.join(KINDS) + ')')
    for name, v in ctl.items(): rsay(f'{name:45s} {collections.Counter(v).most_common()}')
    rsay(''); rsay('high-s boots (libtpms does not normalise s): ' + ', '.join(r[0] for r in krows if r[4] == 'high'))
    rl.close()
    json.dump({k: v for k, v in ctl.items()}, open(f'{OUT}/final_boots_controls.json', 'w'), indent=1)
    say('final boots T:', collections.Counter(ctl['T finalize form']), '| L:', collections.Counter(ctl['L T + --reject-high-s']), '| P:', collections.Counter(ctl['P old positional form']))

    # --- all 15 ATTEST.TXT files on disk
    gr = []
    allf = [(f'opmodel/final_step12000/qemu_{k}', f'{EVID}/qemu_{k}', f'{S}/qemu/shot_final_step12000_{k}/tpm') for k in KINDS] + [(n, d, st) for n, (d, st) in OTHERS.items()]
    for name, d, st in allf:
        att = f'{d}/ATTEST.TXT'; rec = f'{d}/RECEIPT.TXT'
        pin = pin_from_state(st) if st and os.path.isdir(st) else ''
        rcD, oD, eD = av(AV, [att, '--receipt', rec]); rcS, oS, eS = av(AV, [att, '--receipt', rec, '--strict'])
        if pin:
            rcT, oT, eT = av(AV, [att, '--receipt', rec, '--strict', '--expect-pubkey', pin]); vT = verdict_after(rcT, oT, eT)
        else: vT = 'n/a (no swtpm state mapped by name)'
        rcQ, oQ, eQ = av(AV, [att, '--receipt', rec, '--strict', '--reject-high-s'])
        rcP, oP, eP = av(AV_OLD, [att, rec]); rcP2, oP2, eP2 = av(AV_OLD, [att, '--receipt', rec])
        gr.append((name, 'low' if sig_s(att) <= P256_N // 2 else 'high', verdict_after(rcD, oD, eD), verdict_after(rcS, oS, eS), vT, verdict_after(rcQ, oQ, eQ),
                   verdict_before(rcP), verdict_before(rcP2), int(pin == key_of(att)) if pin else ''))
    write_tsv(f'{OUT}/genuine_all.tsv', ['attest', 'sig_s', 'D_default', 'strict_unpinned', 'T_strict_pinned_swtpm', 'strict_unpinned_reject_high_s', 'before_positional_form', 'before_receipt_form', 'pin_equals_key'], gr)
    say('genuine files:', len(gr), '; D accept', sum(1 for r in gr if r[2] == 'ACCEPT'), '; strict accept', sum(1 for r in gr if r[3] == 'ACCEPT'))

    # --- H3 mutants
    shutil.rmtree(f'{SCR}/h3_run', ignore_errors=True); os.makedirs(f'{SCR}/h3_run')
    with tarfile.open(f'{SAFE01}/h3_mutants.tar.gz') as tf: tf.extractall(f'{SCR}/h3_run', filter='data')
    rows = read_tsv(f'{SAFE01}/h3_results.tsv')
    recp = {b: f'{EVID}/{b}/RECEIPT.TXT' for b in ('qemu_calc', 'qemu_self')}
    pin_of = {'qemu_calc': pins['calc'], 'qemu_self': pins['self']}
    def work(r):
        ap = f'{SCR}/h3_run/{r["id"]}/ATTEST.TXT'; b = r['base']
        assert sha(open(ap, 'rb').read()) == r['mutant_sha256'], r['id']      # the extracted file is the one SAFE-01 scored
        res = run_forms(ap, recp[b], pin_of[b])
        o1 = av(AV_OLD, [ap, recp[b]])[0]; o2 = av(AV_OLD, [ap, '--receipt', recp[b], '--artifacts', ARTDIR])[0]
        return (r['id'], r['class'], r['sub'], r['base'], r['mutant_sha256'], r['F1_verdict'], r['F2_verdict'], verdict_before(o1), verdict_before(o2),
                res['P'][0], res['P'][1], res['D'][0], res['D'][1], res['T'][0], res['T'][1], res['L'][0], res['L'][1],
                int(any(res[k][3] and res[k][0] == 0 for k in 'DTL')), res['T'][2], r['desc'])
    with ThreadPoolExecutor(WORKERS) as ex: out = list(ex.map(work, rows))
    write_tsv(f'{OUT}/h3_rerun.tsv', ['id', 'class', 'sub', 'base', 'mutant_sha256', 'before_F1_safe01', 'before_F2_safe01', 'before_F1_remeasured', 'before_F2_remeasured',
                                      'after_P_exit', 'after_P', 'after_D_exit', 'after_D', 'after_T_exit', 'after_T', 'after_L_exit', 'after_L', 'exit0_with_fail_line', 'T_failed_checks', 'desc'], out)
    say('mutant rows:', len(out), '; before remeasured == SAFE-01 verdicts:', sum(1 for o in out if o[7] == o[5] and o[8] == o[6]), 'of', len(out),
        '; T accepted (incl. 2 controls):', sum(1 for o in out if o[14] == 'ACCEPT'), '; anomalies:', sum(1 for o in out for i in (10, 12, 14, 16) if o[i].startswith('ANOMALY')))

    # --- S1: tampered receipt, genuine ATTEST
    s1src = sorted(glob.glob(f'{S}/safe01/h3/S1_*/RECEIPT.TXT'))
    s1old = {r['id']: r for r in read_tsv(f'{SAFE01}/h3_s1_receipt_side.tsv')}
    s1 = []
    for p in s1src:
        m = re.match(r'.*/S1_(qemu_(?:calc|self))_([a-z-]+)_(\d)/RECEIPT.TXT$', p); b, fld, k = m.group(1), m.group(2), m.group(3)
        sid = f'S1-{b}-{fld}-{k}'; att = f'{EVID}/{b}/ATTEST.TXT'
        res = run_forms(att, p, pin_of[b]); o = s1old[sid]
        s1.append((sid, b, fld, filesha(p), o['F1_verdict'], o['F2_verdict'], res['P'][0], res['P'][1], res['D'][0], res['D'][1], res['T'][0], res['T'][1], res['L'][1], res['T'][2]))
    write_tsv(f'{OUT}/h3_s1_rerun.tsv', ['id', 'base', 'receipt_field', 'receipt_sha256', 'before_F1_safe01', 'before_F2_safe01', 'after_P_exit', 'after_P', 'after_D_exit', 'after_D', 'after_T_exit', 'after_T', 'after_L', 'T_failed_checks'], s1)
    say('S1 receipts:', len(s1), '; T accepted', sum(1 for r in s1 if r[11] == 'ACCEPT'), '; D accepted', sum(1 for r in s1 if r[9] == 'ACCEPT'))

    # --- S2 (SAFE-01 software-key forgeries) and S3 (consistent software-key forgeries)
    fr = []
    s2old = {r['id']: r for r in read_tsv(f'{SAFE01}/h3_s2_forgery.tsv')}
    def old2(d): return (verdict_before(av(AV_OLD, [f'{d}/ATTEST.TXT', f'{d}/RECEIPT.TXT'])[0]), verdict_before(av(AV_OLD, [f'{d}/ATTEST.TXT', '--receipt', f'{d}/RECEIPT.TXT', '--artifacts', ARTDIR])[0]))
    for tag, b in (('pcr13-line-edit', 'qemu_calc'), ('receipt-chain-edit', 'qemu_self')):
        d = f'{SCR}/h3_run/forge_{tag}'; res = run_forms(f'{d}/ATTEST.TXT', f'{d}/RECEIPT.TXT', pin_of[b]); o = s2old[f'S2-{tag}']
        fr.append((f'S2-{tag}', b, 'SAFE-01 re-sign with a software key (quote-public and signed qualifiedSigner left as the TPM key\'s)', o['F1_verdict'], o['F2_verdict'],
                   res['P'][0], res['P'][1], res['D'][0], res['D'][1], res['D'][2], res['T'][0], res['T'][1], res['T'][2], res['L'][1], *old2(d)))
    for tag, b, tr in (('pcr13-line-edit', 'qemu_calc', False), ('receipt-chain-edit', 'qemu_self', True)):
        d = forge_consistent(tag, b, tr); res = run_forms(f'{d}/ATTEST.TXT', f'{d}/RECEIPT.TXT', pin_of[b])
        fr.append((f'S3-{tag}', b, 'new: software key AND quote-public, quote-pub-x/y and signed qualifiedSigner rewritten to it (internally consistent)', 'n/a', 'n/a',
                   res['P'][0], res['P'][1], res['D'][0], res['D'][1], res['D'][2], res['T'][0], res['T'][1], res['T'][2], res['L'][1], *old2(d)))
    for b in ('qemu_calc', 'qemu_self'):
        d = forge_unattested(b); res = run_forms(f'{d}/ATTEST.TXT', f'{d}/RECEIPT.TXT', pin_of[b])
        fr.append((f'S4-pcr14-claim-{b}', b, 'new: genuine file plus a self-consistent measured/event/pcr claim for PCR 14, which the quote does not select', 'n/a', 'n/a',
                   res['P'][0], res['P'][1], res['D'][0], res['D'][1], res['D'][2], res['T'][0], res['T'][1], res['T'][2], res['L'][1], *old2(d)))
    write_tsv(f'{OUT}/h3_forgery_rerun.tsv', ['id', 'base', 'what', 'before_F1_safe01', 'before_F2_safe01', 'after_P_exit', 'after_P', 'after_D_exit', 'after_D', 'D_failed_checks',
                                              'after_T_exit', 'after_T', 'T_failed_checks', 'after_L', 'before_F1_remeasured', 'before_F2_remeasured'], fr)
    with tarfile.open(f'{OUT}/h3_s3_forgeries.tar.gz', 'w:gz') as tf:
        for tag in ('pcr13-line-edit', 'receipt-chain-edit'):
            for fn in ('ATTEST.TXT', 'RECEIPT.TXT'): tf.add(f'{SCR}/s3/{tag}/{fn}', arcname=f'forge_s3_{tag}/{fn}')
        for b in ('qemu_calc', 'qemu_self'):
            for fn in ('ATTEST.TXT', 'RECEIPT.TXT'): tf.add(f'{SCR}/s4/{b}/{fn}', arcname=f'forge_s4_pcr14_{b}/{fn}')
    say('forgeries:', [(r[0], r[8], r[11]) for r in fr])
    say('FINALIZE.log unchanged:', filesha(f'{EVID}/FINALIZE.log') == prov['FINALIZE.log (final_step12000, must stay unchanged)'])
    say('run done')
    log.close()



# ------------------------------------------------------------------------------------------- bytes (exhaustive single-byte substitution)
def subst(c):
    """One deterministic substitute per byte: hex digit -> next hex digit, other digit/letter -> next of its class, else 'X'/' '."""
    if c in '0123456789abcdef': return '0123456789abcdef'[('0123456789abcdef'.index(c) + 1) % 16]
    if c.isdigit(): return str((int(c) + 1) % 10)
    if c.islower(): return chr((ord(c) - 97 + 1) % 26 + 97)
    if c.isupper(): return chr((ord(c) - 65 + 1) % 26 + 65)
    return ' ' if c == '\n' else 'X'


def line_key(lines, ln):
    l = lines[ln]
    if ln == 0: return 'header'
    m = re.match(r'^(event pcr=\d+|measured pcr=\d+|pcr \d+|pcr-bank|cpuid|quote-[a-z-]+)', l)
    k = m.group(1) if m else 'other'
    if k.startswith('event pcr='): k += ' #%d' % sum(1 for x in lines[:ln] if x.startswith(k.split(' #')[0] + ' '))
    if k.startswith('measured pcr='): k += ' #%d' % sum(1 for x in lines[:ln] if x.startswith(k.split(' #')[0] + ' '))
    return k


def do_bytes():
    pins = {'qemu_calc': pin_from_state(f'{S}/qemu/shot_final_step12000_calc/tpm'), 'qemu_self': pin_from_state(f'{S}/qemu/shot_final_step12000_self/tpm')}
    os.makedirs(SCR, exist_ok=True); d = f'{SCR}/bytes'; shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    jobs = []
    for b in ('qemu_calc', 'qemu_self'):
        raw = open(f'{EVID}/{b}/ATTEST.TXT', 'rb').read().decode('ascii'); lines = raw.split('\n')
        starts = []; o = 0
        for l in lines: starts.append(o); o += len(l) + 1
        for i, c in enumerate(raw):
            ln = max(j for j, st in enumerate(starts) if st <= i)
            jobs.append((b, i, ln + 1, i - starts[ln], line_key(lines, ln), c, subst(c), raw[:i] + subst(c) + raw[i + 1:]))
    def work(job):
        b, i, ln, col, key, c, n, text = job
        p = f'{d}/{b}_{i}.txt'; open(p, 'w', newline='').write(text)
        rc, out, err = av(AV, [p, '--receipt', f'{EVID}/{b}/RECEIPT.TXT', '--strict', '--expect-pubkey', pins[b], '--efi', EFI])
        os.remove(p)
        return (b, i, ln, col, key, repr(c), repr(n), verdict_after(rc, out, err))
    with ThreadPoolExecutor(WORKERS) as ex: rows = list(ex.map(work, jobs))
    write_tsv(f'{OUT}/h3_byteflip.tsv', ['base', 'offset', 'line_no', 'col', 'line', 'orig', 'new', 'after_T'], rows)
    print('bytes done', len(rows), 'accepted', sum(1 for r in rows if r[7] == 'ACCEPT'), 'anomalies', sum(1 for r in rows if r[7].startswith('ANOMALY')))

# ------------------------------------------------------------------------------------------- report
def do_report():
    prov = {l.split('  ', 1)[1].strip(): l.split('  ', 1)[0] for l in open(f'{OUT}/provenance.txt')}
    keys = read_tsv(f'{OUT}/final_boots_keys.tsv'); gen = read_tsv(f'{OUT}/genuine_all.tsv')
    mut = read_tsv(f'{OUT}/h3_rerun.tsv'); s1 = read_tsv(f'{OUT}/h3_s1_rerun.tsv'); fr = read_tsv(f'{OUT}/h3_forgery_rerun.tsv')
    ctl = json.load(open(f'{OUT}/final_boots_controls.json'))
    ctrl = [m for m in mut if m['class'] == 'control']; mm = [m for m in mut if m['class'] != 'control']
    acc = lambda rows, k: sum(1 for r in rows if r[k] == 'ACCEPT')
    cnt = lambda rows, k, v: sum(1 for r in rows if r[k] == v)
    anomalies = sum(1 for m in mut for k in ('after_P', 'after_D', 'after_T', 'after_L') if m[k].startswith('ANOMALY')) \
        + sum(1 for r in s1 for k in ('after_P', 'after_D', 'after_T', 'after_L') if r[k].startswith('ANOMALY')) \
        + sum(1 for r in fr for k in ('after_P', 'after_D', 'after_T', 'after_L') if r[k].startswith('ANOMALY'))
    exit0_fail = sum(int(m['exit0_with_fail_line']) for m in mut)
    before_match = sum(1 for m in mut if m['before_F1_remeasured'] == m['before_F1_safe01'] and m['before_F2_remeasured'] == m['before_F2_safe01'])
    L = []; w = L.append
    def table(hdr, rows):
        w('| ' + ' | '.join(hdr) + ' |'); w('|' + '|'.join('---' for _ in hdr) + '|')
        for r in rows: w('| ' + ' | '.join(str(x) for x in r) + ' |')
        w('')
    w('# HARDEN-ATTEST RESULT: fail-closed attest_verify.py and finalize.sh (LAB-09 part 2, task G)')
    w('')
    w('Every number below is computed by `labs/safe/harden_attest.py report` from the TSV/log files in this directory and from the SAFE-01 TSVs. Rule A: no timing or rate anywhere. Rule B: every count is a count of rows in a saved file.')
    w('')
    # ---------------------------------------------------------------- summary numbers
    prev = [m for m in mm if m['before_F1_safe01'] == 'ACCEPT' or m['before_F2_safe01'] == 'ACCEPT']
    n_gen_T = sum(1 for k in ctl['T finalize form'] if k == 'ACCEPT')
    n_hs = sum(1 for k in keys if k['sig_s_form'] == 'high')
    w('## 0. Summary')
    w('')
    w(f'- **HA2 (genuine boots still pass): SUPPORTED.** The 8 `final_step12000` QEMU boots: {n_gen_T} of 8 accepted by the exact `finalize.sh` invocation (form T: `--receipt --strict --expect-pubkey <pin from the boot\'s own swtpm state> --efi <EFI>`), {ctl["D default flags"].count("ACCEPT")} of 8 by the default form D. All {len(gen)} ATTEST.TXT files on disk: {cnt(gen, "D_default", "ACCEPT")} accepted by D, {cnt(gen, "strict_unpinned", "ACCEPT")} by `--strict`.')
    sem = [m for m in prev if m['class'] != 'cosmetic']; cosm = [m for m in prev if m['class'] == 'cosmetic']
    w(f'- **HA1 (every previously accepted H3 mutant class is now rejected): PARTLY SUPPORTED.** SAFE-01 recorded {len(prev)} of the {len(mm)} H3 mutants as ACCEPT under F1 or F2 ({len(sem)} semantic edits and {len(cosm)} cosmetic re-encodings). The finalize form T accepts {sum(1 for m in sem if m["after_T"] == "ACCEPT")} of the {len(sem)} semantic ones and {sum(1 for m in cosm if m["after_T"] == "ACCEPT")} of the {len(cosm)} cosmetic ones; the default form D accepts {sum(1 for m in sem if m["after_D"] == "ACCEPT")} and {sum(1 for m in cosm if m["after_D"] == "ACCEPT")}; T plus `--reject-high-s` (L) accepts {sum(1 for m in sem if m["after_L"] == "ACCEPT")} and {sum(1 for m in cosm if m["after_L"] == "ACCEPT")}. The old positional form P is a usage error for {cnt(mm, "after_P", "REJECT_USAGE")} of {len(mm)} mutants. The T-accepted remainder is in four sub-fields, none of which is covered by any digest or signature (cpuid, quote-retries, the device-path part of the image-load event) or is a valid second signature (s -> n-s); section 4a lists every one.')
    w(f'- The 8 final boots have **{len({k["quote_key_x_y"] for k in keys})} distinct attestation keys**: every `boot_shot.sh --tpm` run creates a fresh swtpm state, hence a fresh owner seed. There is no shared "first boot" key. `finalize.sh` therefore pins each boot to the key re-derived from that boot\'s own swtpm state ({sum(int(k["pin_equals_quote_key"]) for k in keys)} of 8 derived keys equal the key in ATTEST.TXT).')
    w(f'- **libtpms does not normalise ECDSA s: {n_hs} of the 8 final boots have a high-s signature** ({len(gen) and cnt(gen, "sig_s", "high")} of {len(gen)} files on disk). `--strict` therefore does NOT reject high-s (it would fail {n_hs} genuine boots); the check is the separate opt-in flag `--reject-high-s`. Deviation from the task text, explained in section 6.')
    if os.path.exists(f'{OUT}/h3_byteflip.tsv'):
        bf0 = read_tsv(f'{OUT}/h3_byteflip.tsv')
        w(f'- Exhaustive single-byte substitution of both files (additional): {len(bf0)} mutants, {cnt(bf0, "after_T", "ACCEPT")} accepted by T, all of them in lines named in section 4c ({", ".join(sorted({r["line"] for r in bf0 if r["after_T"] == "ACCEPT"}))}), {sum(1 for r in bf0 if r["after_T"].startswith("ANOMALY"))} anomalies.')
    w('')
    # ---------------------------------------------------------------- how
    w('## 1. What was changed and how it was run')
    w('')
    w('Files: `labs/tools/attest_verify.py` (rewritten, same output lines), `labs/tools/ak_from_swtpm.sh` (new), `model/demo-operator/finalize.sh` (attest line), `labs/tools/README-attest_verify.md` (new), `labs/LAB-06-alice-boot-dashboard.md` (one example command that used the positional form), `labs/safe/harden_attest.py` (this experiment). Pre-hardening copies kept here: `attest_verify_before.py`, `finalize_before.sh`.')
    w('')
    w('```')
    w('cd /home/user/Ranger3143/labs/safe')
    w('python3 -I harden_attest.py run      # -> run_harden.log, final_boots_recheck.log, final_boots_keys.tsv, genuine_all.tsv, h3_rerun.tsv, h3_s1_rerun.tsv, h3_forgery_rerun.tsv, h3_s3_forgeries.tar.gz (S3 and S4)')
    w('python3 -I harden_attest.py bytes    # -> h3_byteflip.tsv (additional exhaustive single-byte substitution)')
    w('python3 -I harden_attest.py report   # -> RESULT.md')
    w('```')
    w('')
    w('SAFE-01\'s own scripts (`labs/safe/safe01_tamper.py`, `labs/safe/verify09/`) still call the old positional form and were not changed: its recorded numbers belong to `attest_verify_before.py`; re-running them against the hardened verifier would turn every F1 run into a usage error.')
    w('')
    w('Forms (every run `nice -n 5 python3 -I`, `OMP_NUM_THREADS=1`):')
    w('')
    w('```')
    w('P  attest_verify.py ATTEST RECEIPT                                                    old finalize.sh form (positional receipt)')
    w('D  attest_verify.py ATTEST --receipt RECEIPT                                          hardened, default flags')
    w('T  attest_verify.py ATTEST --receipt RECEIPT --strict --expect-pubkey PIN --efi EFI   the form now in finalize.sh')
    w('L  T --reject-high-s')
    w('```')
    w('')
    w('PIN is `labs/tools/ak_from_swtpm.sh <swtpm state dir of the boot>` (tpm2-tools `tpm2_createprimary` with the unikernel\'s template against a copy of the saved swtpm state), never read from the ATTEST.TXT under test. For the mutants of `qemu_calc` / `qemu_self` and for the forgeries the pin is that boot\'s derived key. EFI is `aegis-uefi-gateway-qemutest.efi`.')
    w('')
    w('Scoring rules fixed before the run (`verdict_after` in the script): ACCEPT = exit 0 and both `ATTEST VERIFY PASS` and `QUOTE VERIFY PASS` printed; REJECT = exit 1; REJECT_USAGE = exit 2; anything else (traceback, exit 0 without the PASS lines, timeout) is an ANOMALY and is counted. "Before" verdicts are the SAFE-01 values (`h3_results.tsv`, `h3_s1_receipt_side.tsv`, `h3_s2_forgery.tsv`: F1 = positional receipt, F2 = `--receipt --artifacts`); the pre-hardening verifier was also re-run on the same extracted mutants as a reproducibility check.')
    w('')
    w(f'Checks on the run itself: mutants whose extracted bytes equal SAFE-01\'s recorded sha256: {len(mut)} of {len(mut)} (the script asserts it); pre-hardening re-run agrees with the SAFE-01 F1/F2 verdicts on {before_match} of {len(mut)} rows; anomalies across all hardened runs (P, D, T, L): {anomalies}; hardened runs that printed a FAIL/MISSING/ERROR line and still exited 0: {exit0_fail}; the two unmodified controls: D {acc(ctrl, "after_D")} of {len(ctrl)}, T {acc(ctrl, "after_T")} of {len(ctrl)}, L {acc(ctrl, "after_L")} of {len(ctrl)} accepted.')
    w('')
    w('Input hashes (`provenance.txt`):')
    w('')
    w('```')
    for k, v in prov.items():
        if not re.match(r'qemu_', k): w(f'{v}  {k}')
    w('```')
    w('')
    # ---------------------------------------------------------------- genuine
    w('## 2. Genuine boots (HA2)')
    w('')
    w('Full verbatim output of the finalize.sh invocation for each of the 8 boots: `final_boots_recheck.log`. `FINALIZE.log` was not edited: ' + ('`run_harden.log` records its sha256 before and after as equal.' if any('FINALIZE.log unchanged: True' in l for l in open(f'{OUT}/run_harden.log')) else '**CHECK FAILED, FINALIZE.log changed.**'))
    w('')
    kinds = [k['boot'] for k in keys]
    rows = []
    for i, k in enumerate(kinds):
        rows.append((k, keys[i]['quote_key_x_y'][:16] + '..', keys[i]['sig_s_form'], ctl['T finalize form'][i], ctl['D default flags'][i], ctl['L T + --reject-high-s'][i], ctl['A default + --artifacts (op12k trio)'][i], ctl['P old positional form'][i]))
    table(['boot', 'AK x (first 8 bytes)', 'sig s', 'T (finalize form)', 'D', 'L (T + --reject-high-s)', 'default + --artifacts', 'P (old positional form)'], rows)
    w(f'Distinct attestation keys among the 8 boots: **{len({k["quote_key_x_y"] for k in keys})}**. Keys re-derived from each boot\'s own swtpm state equal the key in its ATTEST.TXT: **{sum(int(k["pin_equals_quote_key"]) for k in keys)} of 8** (`final_boots_keys.tsv`). Low-s signatures: {cnt(keys, "sig_s_form", "low")} of 8; high-s: {n_hs} of 8.')
    w('')
    w('Negative controls on the same 8 boots (each expected to be rejected):')
    w('')
    table(['control', 'rejected', 'of'], [(n, sum(1 for v in ctl[n] if v == 'REJECT'), len(ctl[n])) for n in ctl if n.startswith('X')])
    w('All ATTEST.TXT files found under `labs/logs/` (`genuine_all.tsv`):')
    w('')
    table(['file', 'sig s', 'D', '--strict (no pin)', 'T with swtpm-derived pin', '--strict --reject-high-s', 'before: positional form', 'before: --receipt form'],
          [(g['attest'], g['sig_s'], g['D_default'], g['strict_unpinned'], g['T_strict_pinned_swtpm'], g['strict_unpinned_reject_high_s'], g['before_positional_form'], g['before_receipt_form']) for g in gen])
    w('The dashboard and older boots have no `--efi` check in this table (different EFI images); "n/a" means no swtpm state directory could be mapped to that boot by name, so no independent pin was derived for it.')
    w('')
    # ---------------------------------------------------------------- mutants
    w('## 3. H3 mutants: class x {accepted before, accepted after}')
    w('')
    w(f'{len(mm)} mutants plus 2 unmodified controls (SAFE-01 `h3_results.tsv`, same files, sha256-checked). "before F1/F2" = SAFE-01 verdicts; "after P" = count of usage errors (exit 2) in the old positional form; D/T/L = accepted counts in the three hardened forms.')
    w('')
    by = collections.OrderedDict()
    for m in mm: by.setdefault((m['class'], m['sub']), []).append(m)
    def agg(rows):
        return (len(rows), cnt(rows, 'before_F1_safe01', 'ACCEPT'), cnt(rows, 'before_F2_safe01', 'ACCEPT'), cnt(rows, 'after_P', 'REJECT_USAGE'), acc(rows, 'after_D'), acc(rows, 'after_T'), acc(rows, 'after_L'))
    hdr = ['class', 'mutants', 'before F1 accepted', 'before F2 accepted', 'after P: usage error', 'after D accepted', 'after T accepted', 'after L accepted']
    cls = collections.OrderedDict()
    for m in mm: cls.setdefault(m['class'], []).append(m)
    table(hdr, [(c, *agg(r)) for c, r in cls.items()] + [('**all classes**', *agg(mm))])
    w('Sub-field detail:')
    w('')
    table(['class', 'sub-field'] + hdr[1:], [(c, s, *agg(r)) for (c, s), r in by.items()])
    # findings
    w('## 4. The seven SAFE-01 findings, mutant by mutant')
    w('')
    def sel(pred): return [m for m in mm if pred(m)]
    f1 = sel(lambda m: (m['class'] == 'field-deletion' and m['sub'] == 'quote-attest') or (m['class'] == 'cosmetic' and m['sub'] == 'trailing-space' and 'quote-attest' in m['desc']))
    f3 = sel(lambda m: m['class'] == 'event-line' and m['sub'].startswith('pcr4/'))
    f4 = sel(lambda m: m['class'] == 'event-line' and m['sub'] in ('pcr12/type', 'pcr13/type'))
    f5 = sel(lambda m: m['class'] == 'unread-line' and m['sub'] in ('quote-pcrs', 'quote-public', 'quote-retries', 'quote-key'))
    f6 = sel(lambda m: m['class'] == 'sig-malleability')
    f8 = sel(lambda m: m['class'] == 'measured-line' and m['sub'] == 'pcr13/delete')
    def fr_(rows, kb, ka): return (len(rows), sum(1 for r in rows if r[kb] == 'ACCEPT'))
    s1acc_b = sum(1 for r in s1 if r['before_F1_safe01'] == 'ACCEPT'); s1acc_b2 = sum(1 for r in s1 if r['before_F2_safe01'] == 'ACCEPT')
    s2 = [r for r in fr if r['id'].startswith('S2')]; s3 = [r for r in fr if r['id'].startswith('S3')]; s4 = [r for r in fr if r['id'].startswith('S4')]
    frows = [
        ('1 fail-open quote (quote-attest deleted or space-padded)', len(f1), cnt(f1, 'before_F1_safe01', 'ACCEPT'), cnt(f1, 'before_F2_safe01', 'ACCEPT'), acc(f1, 'after_D'), acc(f1, 'after_T'), acc(f1, 'after_L')),
        ('2 receipt ignored when passed positionally (S1: tampered RECEIPT.TXT, genuine ATTEST.TXT)', len(s1), s1acc_b, s1acc_b2, acc(s1, 'after_D'), acc(s1, 'after_T'), acc(s1, 'after_L')),
        ('3 PCR 4 event-log edits never replayed', len(f3), cnt(f3, 'before_F1_safe01', 'ACCEPT'), cnt(f3, 'before_F2_safe01', 'ACCEPT'), acc(f3, 'after_D'), acc(f3, 'after_T'), acc(f3, 'after_L')),
        ('4 type= of PCR 12/13 events unchecked', len(f4), cnt(f4, 'before_F1_safe01', 'ACCEPT'), cnt(f4, 'before_F2_safe01', 'ACCEPT'), acc(f4, 'after_D'), acc(f4, 'after_T'), acc(f4, 'after_L')),
        ('5 unread quote-pcrs / quote-public / quote-retries / quote-key lines', len(f5), cnt(f5, 'before_F1_safe01', 'ACCEPT'), cnt(f5, 'before_F2_safe01', 'ACCEPT'), acc(f5, 'after_D'), acc(f5, 'after_T'), acc(f5, 'after_L')),
        ('6 ECDSA malleability s -> n-s', len(f6), cnt(f6, 'before_F1_safe01', 'ACCEPT'), cnt(f6, 'before_F2_safe01', 'ACCEPT'), acc(f6, 'after_D'), acc(f6, 'after_T'), acc(f6, 'after_L')),
        ('7 re-sign with a software key, SAFE-01 S2 (quote-public left as the TPM key)', len(s2), sum(1 for r in s2 if r['before_F1_safe01'] == 'ACCEPT'), sum(1 for r in s2 if r['before_F2_safe01'] == 'ACCEPT'), acc(s2, 'after_D'), acc(s2, 'after_T'), acc(s2, 'after_L')),
        ('7b re-sign with a software key, new S3 (internally consistent forgery)', len(s3), 'n/a', 'n/a', acc(s3, 'after_D'), acc(s3, 'after_T'), acc(s3, 'after_L')),
        ('7c (new, S4) self-consistent measured/event/pcr claim about PCR 14, which the quote does not select', len(s4), sum(1 for r in s4 if r['before_F1_remeasured'] == 'ACCEPT'), sum(1 for r in s4 if r['before_F2_remeasured'] == 'ACCEPT'), acc(s4, 'after_D'), acc(s4, 'after_T'), acc(s4, 'after_L')),
        ('(extra) last `measured pcr=13` line deleted', len(f8), cnt(f8, 'before_F1_safe01', 'ACCEPT'), cnt(f8, 'before_F2_safe01', 'ACCEPT'), acc(f8, 'after_D'), acc(f8, 'after_T'), acc(f8, 'after_L')),
    ]
    table(['finding', 'mutants', 'before F1 accepted', 'before F2 accepted', 'after D accepted', 'after T accepted', 'after L accepted'], frows)
    w(f'Old positional form P on the findings sets: usage error for {cnt(mm, "after_P", "REJECT_USAGE")} of {len(mm)} mutants, {cnt(s1, "after_P", "REJECT_USAGE")} of {len(s1)} S1 receipts and {cnt(fr, "after_P", "REJECT_USAGE")} of {len(fr)} forgeries; accepted: {acc(mm, "after_P") + acc(s1, "after_P") + acc(fr, "after_P")}.')
    w('')
    w('### 4a. Residual accepted mutants in form T (verbatim ids), and why no verifier can reject them')
    w('')
    resid = [m for m in mm if m['after_T'] == 'ACCEPT']
    reason = {
        'pcr4/data': 'the data field of the EV_EFI_BOOT_SERVICES_APPLICATION event (image address, device path) is informational: PCR 4 is extended with the PE image hash, not with the data; no digest covers it. `--efi` binds the digest and the image length / link address; the flipped nibble here lies outside those fields.',
        'cpuid': 'the `cpuid` line is in no PCR and not in the quote; it is unauthenticated metadata. Closing this needs the unikernel to measure it (a change in aegis-uefi, not done here).',
        'quote-retries': 'a counter the unikernel prints outside the signed data; any integer in 0..16 is plausible. Only the format and range are checked.',
        'sig-s=n-s': 'a valid second signature over the same signed bytes; it cannot be told from a genuine high-s signature. See section 6.',
    }
    table(['id', 'class / sub-field', 'what was changed', 'why accepted'], [(m['id'], f'{m["class"]} / {m["sub"]}', m['desc'], reason.get(m['sub'], '?')) for m in resid])
    w(f'Residual accepted mutants in T: {len(resid)}; of these in L (adds `--reject-high-s`): {sum(1 for m in resid if m["after_L"] == "ACCEPT")}. By sub-field: ' + ', '.join(f'{s}: {n}' for s, n in collections.Counter(m['sub'] for m in resid).items()) + '.')
    w('')
    w('### 4b. Cosmetic variants (semantically equivalent encodings; reported separately, as in SAFE-01)')
    w('')
    cos = [m for m in mm if m['class'] == 'cosmetic']
    table(['sub-field', 'mutants', 'before F1 accepted', 'before F2 accepted', 'after D accepted', 'after T accepted'],
          [(s, len(r), cnt(r, 'before_F1_safe01', 'ACCEPT'), cnt(r, 'before_F2_safe01', 'ACCEPT'), acc(r, 'after_D'), acc(r, 'after_T')) for s, r in
           ((s, [m for m in cos if m['sub'] == s]) for s in collections.OrderedDict((m['sub'], 1) for m in cos))])
    w('D keeps accepting encodings that decode to the same bytes (CRLF, missing final newline, upper-case hex, extra leading zero bytes of r/s); `--strict` rejects every non-canonical form. Trailing spaces are rejected in every mode because the line then no longer parses.')
    w('')
    # ---------------------------------------------------------------- exhaustive single-byte substitution
    if os.path.exists(f'{OUT}/h3_byteflip.tsv'):
        bf = read_tsv(f'{OUT}/h3_byteflip.tsv')
        w('### 4c. Exhaustive single-byte substitution (additional, not in the pre-registration)')
        w('')
        w(f'Every byte position of `qemu_calc/ATTEST.TXT` and `qemu_self/ATTEST.TXT` was replaced once (hex digit -> next hex digit, other digit/letter -> next of its class, anything else -> `X`, newline -> space) and the result run through form T (`h3_byteflip.tsv`): {len(bf)} mutants, {cnt(bf, "after_T", "ACCEPT")} accepted, {sum(1 for r in bf if r["after_T"].startswith("ANOMALY"))} anomalies. Controls: the unmodified files are accepted by T (section 3).')
        w('')
        bl = collections.OrderedDict()
        for r in bf: bl.setdefault((r['base'], r['line']), []).append(r)
        def ranges(cols):
            cols = sorted(cols); out = []; a = b = None
            for c in cols:
                if a is None: a = b = c
                elif c == b + 1: b = c
                else: out.append((a, b)); a = b = c
            if a is not None: out.append((a, b))
            return ', '.join(f'{x}' if x == y else f'{x}-{y}' for x, y in out)
        known = {'cpuid': 'informational CPU identity string, in no PCR and not in the quote', 'quote-retries': 'unsigned counter, any digit is in range',
                 'event pcr=4 #2': 'image-load event data outside the fields `--efi` binds (see 4a)'}
        accl = [(k, v) for k, v in bl.items() if any(r['after_T'] == 'ACCEPT' for r in v)]
        table(['file', 'line', 'bytes tested', 'accepted by T', 'accepted columns (0-based, in the line)', 'why'],
              [(k[0], k[1], len(v), sum(1 for r in v if r['after_T'] == 'ACCEPT'), ranges([int(r['col']) for r in v if r['after_T'] == 'ACCEPT']), known.get(k[1], '**UNEXPECTED, investigate**')) for k, v in accl])
        w(f'Lines in which every substituted byte was rejected: {len(bl) - len(accl)} of {len(bl)} (file, line) pairs. Total bytes in the two files: {len(bf)}; rejected: {cnt(bf, "after_T", "REJECT")}; accepted: {cnt(bf, "after_T", "ACCEPT")} (of which in the lines named above: {sum(sum(1 for r in v if r["after_T"] == "ACCEPT") for k, v in accl if k[1] in known)}).')
        w('')
    # ---------------------------------------------------------------- S1/S2/S3
    w('## 5. Tampered receipts (S1), software-key forgeries (S2, S3) and an unattested claim (S4)')
    w('')
    by1 = collections.OrderedDict()
    for r in s1: by1.setdefault(r['receipt_field'], []).append(r)
    table(['receipt field changed', 'receipts', 'before F1 accepted', 'before F2 accepted', 'after P: usage error', 'after D accepted', 'after T accepted'],
          [(f, len(r), cnt(r, 'before_F1_safe01', 'ACCEPT'), cnt(r, 'before_F2_safe01', 'ACCEPT'), cnt(r, 'after_P', 'REJECT_USAGE'), acc(r, 'after_D'), acc(r, 'after_T')) for f, r in by1.items()])
    table(['id', 'base', 'before F1', 'before F2', 'after P', 'after D', 'after T', 'after L', 'first failed checks in T'],
          [(r['id'], r['base'], r['before_F1_safe01'] if r['before_F1_safe01'] != 'n/a' else r['before_F1_remeasured'] + ' (re-measured)', r['before_F2_safe01'] if r['before_F2_safe01'] != 'n/a' else r['before_F2_remeasured'] + ' (re-measured)',
            r['after_P'], r['after_D'], r['after_T'], r['after_L'], r['T_failed_checks']) for r in fr])
    w('S4 (new here, also an addition to the pre-registration) appends a self-consistent measured/event/pcr claim about PCR 14. The quote selects only PCRs 4, 12 and 13, so nothing signed covers PCR 14; the pre-hardening verifier replays it and passes it, the hardened one fails any file that reports a PCR outside the quote selection (' + f'D accepts {acc(s4, "after_D")} of {len(s4)}, T accepts {acc(s4, "after_T")} of {len(s4)}; before, re-measured: F1 {cnt(s4, "before_F1_remeasured", "ACCEPT")} and F2 {cnt(s4, "before_F2_remeasured", "ACCEPT")} accepted).')
    w('')
    w('S2 is SAFE-01\'s forgery: re-signed with a software key but `quote-public` and the signed qualifiedSigner still describe the TPM key, so the hardened default form D already rejects it (first failed check shown in the D column of `h3_forgery_rerun.tsv`). S3 (new here, labelled as an addition to the pre-registration) rewrites those too and is internally consistent: D accepts it, and only the pin (`--expect-pubkey`) rejects it. That is the whole value of the pin: without it the quote proves consistency with some P-256 key, not which TPM.')
    w('')
    d_s2 = '; '.join(f'{r["id"]}: {r["D_failed_checks"]}' for r in s2)
    w(f'D on S2: {d_s2}')
    w('')
    # ---------------------------------------------------------------- hypotheses + deviations
    w('## 6. Hypotheses, deviations and what is not covered')
    w('')
    unacc = [f for f in frows if isinstance(f[5], int) and f[5] == 0]
    def rj(rows, k='after_T'): return f'{sum(1 for r in rows if r[k] != "ACCEPT")} of {len(rows)}'
    w(f'- **HA1.** Verdict: PARTLY SUPPORTED. Rejected by T, per SAFE-01 finding: 1 fail-open quote {rj(f1)}; 2 receipt ignored (S1) {rj(s1)}; 3 PCR 4 edits {rj(f3)}; 4 type= of PCR 12/13 events {rj(f4)}; 5 unread quote lines {rj(f5)} (quote-pcrs / quote-public / quote-key: {rj([m for m in f5 if m["sub"] != "quote-retries"])}); 6 malleation {rj(f6)} (by L: {rj(f6, "after_L")}); 7 software-key re-sign {rj(s2)} (S2) and {rj(s3)} (S3, internally consistent; D rejects {rj(s3, "after_D")}). Findings 1, 2, 4 and 7 are closed completely in T. Finding 3 leaves {sum(1 for m in resid if m["sub"] == "pcr4/data")} mutant (device-path bytes of the image-load event, in no digest), finding 5 leaves {sum(1 for m in resid if m["sub"] == "quote-retries")} (the `quote-retries` counter, outside the signature), finding 6 is closed only by the opt-in `--reject-high-s` and then only for low-s originals. `cpuid` ({sum(1 for m in resid if m["sub"] == "cpuid")} mutants, SAFE-01 "unread" class but not one of the seven findings) is likewise unauthenticated.')
    w(f'- **HA2.** Verdict: SUPPORTED. 8 of 8 final boots pass form T; {cnt(gen, "D_default", "ACCEPT")} of {len(gen)} files on disk pass D and {cnt(gen, "strict_unpinned", "ACCEPT")} of {len(gen)} pass `--strict`.')
    w('- **Deviation from the task text, (f) low-s.** The task asked to reject s > n/2 under `--strict` and, if any genuine file is high-s, to make the check `--strict`-only. Empirically '
      f'{n_hs} of the 8 final boots ({cnt(gen, "sig_s", "high")} of {len(gen)} files on disk) are high-s: libtpms/swtpm does not normalise s. A `--strict` that rejects high-s would fail {n_hs} genuine boots in `finalize.sh`, which the same task requires to use `--strict`. So `--strict` does not include the check; `--reject-high-s` is a separate opt-in flag (form L). It does not stop malleation in general: a genuine high-s quote can be turned into a valid low-s quote by anyone, and L accepts that. Malleability does not let anyone sign new content (the signed TPMS_ATTEST is unchanged); it only matters if a signature is used as an identifier.')
    w('- **Deviation, (g) pin source.** The task said to take the key from the first boot of the same swtpm state. The 8 boots do not share a state (8 distinct keys), so that rule has nothing to pin to. `finalize.sh` instead re-derives each boot\'s key from that boot\'s own swtpm state with `labs/tools/ak_from_swtpm.sh`; the pin never comes from the ATTEST.TXT being checked. `AEGIS_AK_PIN` overrides it with an enrolled key; `attest_verify.py --print-pubkey` gives the trust-on-first-use alternative for a file you have not seen before.')
    w('- **Addition, `--efi`.** Not asked for. PCR 4\'s third digest equals the Authenticode SHA-256 of `aegis-uefi-gateway-qemutest.efi` in all 8 boots, so `finalize.sh` passes `--efi $EFI` and thereby also checks which binary booted (and, with it, the image length and link address in the logged event data). Optional flag.')
    w('- **Addition, quote-selection check.** A file that reports a PCR the quote does not select (a `pcr`, `measured` or `event` line for PCR 14, say) now fails: that claim would be consistent with itself and covered by no signature (S4).')
    w('- **Addition, `finalize.sh` exit status.** It now exits 1 after its summary if any boot is not verified (attestation failed, ATTEST.TXT/RECEIPT.TXT missing, or no pin could be derived). Before, a failed or skipped check was invisible.')
    w('- **Not covered, stated plainly.** `cpuid`, `quote-retries`, the clock/reset counters inside TPMS_ATTEST, and the data field of the EV_EFI_BOOT_SERVICES_APPLICATION event are not bound by any digest or signature (they are checked for format only). `RECEIPT2.TXT` of the three tool-use boots is not passed to attest_verify.py (its chain is in the second PCR 13 line, which the replay covers, but nothing compares the file). `swtpm` is a software TPM with no EK certificate: a pin proves "the TPM whose owner seed the host holds", not hardware provenance (LAB-04 limitation 5 still applies on real iron).')
    w('')
    w('## 7. Files in this directory')
    w('')
    for fn in sorted(os.listdir(OUT)):
        w(f'- `{fn}`')
    w('')
    open(f'{OUT}/RESULT.md', 'w').write('\n'.join(L))
    print('RESULT.md written', len(L), 'lines')


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('run', 'bytes', 'report'):
        print(__doc__); sys.exit(2)
    {'run': do_run, 'bytes': do_bytes, 'report': do_report}[sys.argv[1]]()
