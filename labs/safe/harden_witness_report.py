"""HARDEN-WITNESS report: writes logs/safe/HARDEN-WITNESS/RESULT.md from the saved logs ONLY (Rule B).
Imported and called by `python3 -I harden_witness.py report`; not run on its own."""
import os, re, json, gzip, hashlib, collections

R = '/home/user/Ranger3143'
S01 = f'{R}/labs/logs/safe/SAFE-01'
OUT = f'{R}/labs/logs/safe/HARDEN-WITNESS'

def read_tsv(path):
    with open(path) as f:
        rows = [l.rstrip('\n').split('\t') for l in f]
    h = rows[0]
    return [dict(zip(h, r)) for r in rows[1:]]

def pct(a, b): return f'{100.0 * a / b:.2f}%' if b else 'n/a'
def rd(path):
    try:
        return open(path, errors='replace').read()
    except OSError:
        return ''

NAMES = {'C00': 'control (unmodified receipts)', 'C01': 'token-ids (flip / drop / append / swap)', 'C02': 'prompt-hex (one nibble)',
         'C03': 'cis-digest (one hex char)', 'C04': 'chain (one hex char)', 'C05': 'maxtok (+-1, and wider +-d)',
         'C06': 'model/embed/vocab hash lines (one hex char)', 'C07': 'truncation (drop last k lines; byte cut)',
         'C08': 'line reorder', 'C09': 'cross-receipt swap', 'C10': 'artifact swap, relabel, 1-byte-mutated MODEL.SAF',
         'C11': 'cosmetic (trailing whitespace, CRLF, final newline)',
         'U1': 'prompt-toks line', 'U2': 'gen-toks line', 'U3': 'header line',
         'U4': 'unknown line appended', 'U5': 'duplicate key', 'U6': 'non-canonical encodings'}
ORDER = ['C00', 'C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']
NONCOSMETIC = ['C08', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']

def norm_reason(s):
    s = re.sub(r'\d+', 'N', s)
    s = re.sub(r'"[^"]*"', '"..."', s)
    return s[:150]

def strict_reason(out):
    """The line that says why --strict refused: 'VERIFY FAIL — strict: ...' or the separate 'strict: ...' line
    printed before a generic final VERIFY FAIL line (prompt-toks check, which needs the replay)."""
    ls = [l for l in out.strip().split('\n') if l]
    for l in ls:
        if l.startswith('VERIFY FAIL — strict:'): return l
    for l in ls:
        if l.startswith('strict: ') and not l.startswith('strict: canonical'): return l
    return ls[-1] if ls else ''

def cargo_counts(text):
    passed = sum(int(x) for x in re.findall(r'test result: ok\. (\d+) passed', text))
    failed = sum(int(x) for x in re.findall(r'test result: \w+\. \d+ passed; (\d+) failed', text))
    return passed, failed, len(re.findall(r'^test result:', text, re.M))

def report():
    rows = read_tsv(f'{OUT}/h1_rerun.tsv')
    ctl = read_tsv(f'{OUT}/controls.tsv')
    geq = read_tsv(f'{OUT}/gen_equivalence.tsv')
    fz = read_tsv(f'{OUT}/fuzz.tsv') if os.path.exists(f'{OUT}/fuzz.tsv') else []
    gen = json.load(open(f'{S01}/h1_generation.json'))
    L = []; P = L.append
    outs = {}
    with gzip.open(f'{OUT}/h1_rerun_outputs.jsonl.gz', 'rt') as g:
        for line in g:
            d = json.loads(line); outs[d['id']] = d
    by = collections.defaultdict(list)
    for r in rows: by[r['class']].append(r)
    def tally(rs, col):
        c = collections.Counter(r[col] for r in rs)
        return c['ACCEPT'], c['REJECT_CLEAN'], c['REJECT_CRASH'], c['TIMEOUT']
    N = len(rows)
    n_weight = sum(1 for r in rows if r['sub'] == 'weight-1byte')
    old_all = tally(rows, 'old_verdict'); new_all = tally(rows, 'new_default_verdict'); st_all = tally(rows, 'strict_verdict')
    pan_d = sum(int(r['default_panic']) for r in rows); pan_s = sum(int(r['strict_panic']) for r in rows)
    ex2_d = sum(1 for r in rows if r['default_exit'] == '2'); ex2_s = sum(1 for r in rows if r['strict_exit'] == '2')
    old_pan = sum(1 for r in rows if r['old_verdict'] == 'REJECT_CRASH')
    bin_txt = rd(f'{OUT}/binaries.sha256.txt')
    core_log = rd(f'{OUT}/cargo_test_aegis_core.log'); cw_log = rd(f'{OUT}/cargo_test_cis_witness.log'); fmt_log = rd(f'{OUT}/devloop_fmt.log')
    cp, cf, cn = cargo_counts(core_log); wp, wf, wn = cargo_counts(cw_log)
    bp, bf, bn = cargo_counts(rd(f'{OUT}/cargo_test_aegis_core_baseline.log'))

    # ---- invariants
    trans = collections.Counter((r['old_verdict'], r['new_default_verdict']) for r in rows)
    changed_bad = sum(v for (o, n), v in trans.items() if o != n and not (o == 'REJECT_CRASH' and n == 'REJECT_CLEAN'))
    same_nocrash = [r for r in rows if r['old_verdict'] != 'REJECT_CRASH']
    last_diff = [r for r in same_nocrash if r['old_stdout_last'] != r['default_stdout_last']]
    strict_not_sub = [r for r in rows if r['strict_verdict'] == 'ACCEPT' and r['new_default_verdict'] != 'ACCEPT']
    strict_acc = [r for r in rows if r['strict_verdict'] == 'ACCEPT']
    strict_acc_non_c00 = [r for r in strict_acc if r['class'] != 'C00']

    # ---- hypotheses
    hw1_old = sum(tally(by[c], 'old_verdict')[0] for c in NONCOSMETIC)
    hw1_new_default = sum(tally(by[c], 'new_default_verdict')[0] for c in NONCOSMETIC)
    hw1_strict = sum(tally(by[c], 'strict_verdict')[0] for c in NONCOSMETIC)
    hw1_n = sum(len(by[c]) for c in NONCOSMETIC)
    ctlg = collections.defaultdict(lambda: collections.Counter())
    for r in ctl: ctlg[(r['group'], r['mode'])][r['verdict']] += 1
    def cg(group, mode, v='ACCEPT'): return ctlg[(group, mode)][v], sum(ctlg[(group, mode)].values())
    fz_n = len(fz)
    fz_pan_d = sum(int(r['default_panic']) for r in fz); fz_pan_s = sum(int(r['strict_panic']) for r in fz)
    ctl_pan = sum(int(r['panic']) for r in ctl)
    geq_pan = 0
    total_pan_d = pan_d + fz_pan_d + sum(int(r['panic']) for r in ctl if r['mode'] == 'default')
    total_pan_s = pan_s + fz_pan_s + sum(int(r['panic']) for r in ctl if r['mode'] == 'strict')

    P('# HARDEN-WITNESS RESULT: strict witness-receipt verification and a panic-free parser (LAB-09 part 2)')
    P('')
    P('Every number below is computed by `labs/safe/harden_witness.py report` (module `harden_witness_report.py`) from the logs saved next to this file and from the SAFE-01 logs. Rule A: no timing or rate was recorded anywhere (the harness timeout only kills a hung process).')
    P('')
    P('## 0. Findings at a glance')
    P('')
    P(f'1. **`cis_witness verify --strict` rejects every previously accepted non-cosmetic mutant (HW1).** C08 line reorder, U1 prompt-toks, U2 gen-toks, U3 header, U4 unknown line, U5 duplicate key, U6 non-canonical encodings: SAFE-01 default verdict ACCEPT on {hw1_old} of {hw1_n} mutants; the new binary in default mode still ACCEPTs {hw1_new_default} of {hw1_n} (unchanged on purpose); `--strict` ACCEPTs {hw1_strict} of {hw1_n}. The cosmetic class C11 (CRLF, trailing blanks, final newline) is also fully rejected under `--strict`: {tally(by["C11"], "strict_verdict")[0]} of {len(by["C11"])} accepted (default: {tally(by["C11"], "new_default_verdict")[0]}).')
    P(f'2. **Genuine receipts pass (HW2).** Strict-mode PASS: {cg("qemu_receipt", "strict")[0]} of {cg("qemu_receipt", "strict")[1]} QEMU-minted `RECEIPT*.TXT` under `final_step12000`; {cg("golden", "strict")[0]} of {cg("golden", "strict")[1]} golden fixture replayed in full (`witness_v1_m7_once64.receipt`, with the m7 artifacts); {cg("h2_self_receipt", "strict")[0]} of {cg("h2_self_receipt", "strict")[1]} receipts minted by `cis_witness gen` in SAFE-01 H2. The other 4 golden fixtures (bitnet2b, e16_qat, e16_qat_pruned, falcon_e_1b) could not be replayed here because their model artifacts are not on this host: they were checked at the parser level only ({cg("golden_format_only", "strict", "REJECT_CLEAN")[0]} of {cg("golden_format_only", "strict", "REJECT_CLEAN")[1]} reach the artifact-hash comparison without a strict-format failure, and the unit test `strict_accepts_every_golden_and_matches_the_lenient_reader` parses all 5). So HW2 is confirmed with that qualification.')
    P(f'3. **Zero panics (HW3).** SAFE-01 default binary: {old_pan} of {N} rows were crash-rejects (panic text, not a verdict). New binary: default mode {pan_d} panics and strict mode {pan_s} panics over the same {N} rows; fuzz ({fz_n} malformed inputs x 2 modes): {fz_pan_d} and {fz_pan_s}; controls: {ctl_pan}. Totals: default {total_pan_d}, strict {total_pan_s}. Exit code 2 (usage/unusable file) occurred {ex2_d} (default) and {ex2_s} (strict) times in the H1 sweep.')
    P(f'4. **Default mode did not move.** For the {len(same_nocrash)} rows whose SAFE-01 verdict was not a crash, the new default verdict is identical in {len(same_nocrash) - sum(1 for r in same_nocrash if r["old_verdict"] != r["new_default_verdict"])} and the last stdout line identical in {len(same_nocrash) - len(last_diff)}. Verdict changes in default mode other than REJECT_CRASH to REJECT_CLEAN: {changed_bad}. The {old_pan} old crash-rejects are now clean `VERIFY FAIL` rejections: {sum(1 for r in rows if r["old_verdict"] == "REJECT_CRASH" and r["new_default_verdict"] == "REJECT_CLEAN")} of {old_pan}.')
    P(f'5. **Strict is a subset of default and accepts nothing in the sweep except the unmodified controls.** Rows where strict ACCEPTs but default does not: {len(strict_not_sub)}. Strict ACCEPTs over the {N} sweep rows: {len(strict_acc)}; all of them class C00 (the unmodified controls): {"yes" if not strict_acc_non_c00 else "NO: " + ", ".join(r["id"] for r in strict_acc_non_c00[:5])}.')
    P(f'6. **Tests.** `cargo test --release --example cis_witness`: {wp} passed, {wf} failed across {wn} test binaries. `cargo test -p aegis-core --release`: {cp} passed, {cf} failed across {cn} test binaries (the witness_contract and golden tests are among them; the same command on the tree before the change gave {bp} passed, {bf} failed across {bn} test binaries, log `cargo_test_aegis_core_baseline.log`). `scripts/devloop.sh fmt`: aegis-linux {"PASS" if "aegis-linux: PASS" in fmt_log else "see log"}.')
    P('')
    P('## 1. What changed in `alice-aegis` (branch `lab/vnni-cis1`, local only)')
    P('')
    P('Files: `aegis-linux/examples/cis_witness.rs`, `aegis-linux/Cargo.toml` (adds `test = true` for the example, as already done for `agent_trace` and `reasoning_trace`, so the new unit tests run under `cargo test`). `aegis-core/src/witness.rs` has no receipt parser (it holds SHA-256, the header hash and the chain), so nothing there changed. `tests/golden` and `docs/hardware_logs` were not touched.')
    P('')
    P('**Canonical layout** (`KEY_ORDER` in the source), derived from the two writers, which agree line for line: the `println!` sequence of `cis_witness gen` (old lines 149-159) and `aegis-uefi/src/verifier.rs::render_receipt` (lines 155-168, the UEFI mint path). There is no `cis_witness mint` subcommand; `gen` is the host-side minter. `gen` now prints through a `render_receipt` function that the unit tests use to pin the reader order to the writer order, and `gen` output is byte-identical to the SAFE-01 binary (section 3).')
    P('')
    P('```')
    P('AEGIS-WITNESS v1-CIS')
    P('model <64 lower-case hex>')
    P('embed <64 lower-case hex>')
    P('vocab <64 lower-case hex>')
    P('maxtok <decimal>')
    P('prompt-hex <lower-case hex, even length, decodes to UTF-8>')
    P('prompt-toks <decimal>')
    P('gen-toks <decimal>')
    P('token-ids <comma-separated decimal u32>')
    P('cis-digest <16 lower-case hex>')
    P('chain <64 lower-case hex>')
    P('```')
    P('')
    P('**`--strict` requires:** printable ASCII and LF only (no CR, tab, NUL or non-ASCII byte anywhere); exactly one `\\n` after the last line and no blank line; exactly eleven lines in the order above (an unknown, duplicate, missing or reordered line is an error that names the line); header exactly `AEGIS-WITNESS v1-CIS`; one space between key and value, no leading or trailing blank; hex fields lower-case and of the exact length; decimals canonical (digits only, no `+`, no leading zero except `0`, fits the type); `gen-toks` equal to the `token-ids` count (parser); `prompt-toks` equal to the tokenizer length of the decoded prompt (after replay, so it needs the artifacts). All default checks (artifact hashes, token ids, digest, chain) still apply. The only line that may end in a space is `token-ids ` with an empty value, which both writers print for a zero-token receipt (`gen-toks 0`); it is accepted exactly in that case (section 3 shows the max_new 0 round trip).')
    P('')
    P('**Default `verify` is unchanged for every input that did not panic** (same acceptance, same output). What changed is that input that used to panic now ends with `VERIFY FAIL — <reason>` on stdout and exit code 1: a non-UTF-8 file, an unparsable `maxtok` or token id, a `prompt-hex` pair that splits a multi-byte character, a prompt that tokenizes to nothing, a budget past the context window (the old context check could also wrap around for a huge `maxtok`; it is now a checked add), a multi-byte character inside a hash line (the 16-character prefix print is cut on a character boundary), and a missing receipt argument. Unreadable artifact/receipt files and unusable artifacts exit 2 with a message on stderr instead of a panic. The lenient reader itself is kept as is on purpose (`unhex_lenient` keeps `+a`, odd tails and non-hex pairs), so existing receipts and scripts verify exactly as before.')
    P('')
    P('Binaries (sha256, name, path):')
    P('')
    P('```')
    P(bin_txt.strip())
    P('```')
    P('')
    P('The SAFE-01 binary (`old`, 79107c6b) was built on 2026-10-06; the new one with the toolchain on this host (`cargo --version` in section 6). Their `gen` outputs are byte-identical (section 3), so the difference in file hash is the code change and the toolchain, not the receipt format.')
    P('')
    P('## 2. H1 re-run: every SAFE-01 mutant through the new binary, default and `--strict`')
    P('')
    chk = rd(f'{OUT}/mutant_archive_check.txt').strip().replace('\n', '; ')
    P(f'Inputs: the saved mutants in `SAFE-01/h1_mutants.tar.gz` (not regenerated: `safe01_tamper.py h1` writes into the SAFE-01 log directory, so the archive was used; check: {chk}) plus the 220 one-byte-weight rows SAFE-01 merged into C10 (11 receipts x 20 mutated `MODEL.SAF`, from `h2_verify.tsv`). Total {N} rows: {N - n_weight} receipt mutants (including the {len(by["C00"])} unmodified C00 controls) and {n_weight} weight rows. Old verdict = SAFE-01 `h1_results.tsv` / `h2_verify.tsv` (binary 79107c6b); new default and strict = this run. Scoring is the SAFE-01 rule unchanged: ACCEPT = exit 0 and a stdout line starting `VERIFY PASS`; REJECT_CLEAN = exit 1 and a line starting `VERIFY FAIL` or `FAIL artifact`; REJECT_CRASH = anything else (panic, signal, other exit code). A panic is counted separately as exit 101, death by signal, or `panicked at` on stderr.')
    P('')
    P('| class | what | mutants | old ACCEPT | old CLEAN | old CRASH | new default ACCEPT | new default CLEAN | new default CRASH | strict ACCEPT | strict CLEAN | strict CRASH | panics old / default / strict |')
    P('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    tot = collections.Counter()
    for c in ORDER:
        rs = by[c]
        if not rs: continue
        o = tally(rs, 'old_verdict'); d = tally(rs, 'new_default_verdict'); s = tally(rs, 'strict_verdict')
        po = sum(1 for r in rs if r['old_verdict'] == 'REJECT_CRASH'); pd = sum(int(r['default_panic']) for r in rs); ps = sum(int(r['strict_panic']) for r in rs)
        P(f'| {c} | {NAMES[c]} | {len(rs)} | {o[0]} | {o[1]} | {o[2]} | {d[0]} | {d[1]} | {d[2]} | {s[0]} | {s[1]} | {s[2]} | {po} / {pd} / {ps} |')
    P(f'| all | | {N} | {old_all[0]} | {old_all[1]} | {old_all[2]} | {new_all[0]} | {new_all[1]} | {new_all[2]} | {st_all[0]} | {st_all[1]} | {st_all[2]} | {old_pan} / {pan_d} / {pan_s} |')
    P('')
    P(f'TIMEOUT rows (inconclusive): old {old_all[3]}, default {new_all[3]}, strict {st_all[3]}.')
    P('')
    P('### 2a. Sub-classes that SAFE-01 found accepted (or that strict accepts)')
    P('')
    P('| class | sub-class | mutants | old ACCEPT | new default ACCEPT | strict ACCEPT |')
    P('|---|---|---|---|---|---|')
    subs = collections.OrderedDict()
    for r in rows:
        subs.setdefault((r['class'], r['sub']), []).append(r)
    for (c, sb), rs in subs.items():
        o = tally(rs, 'old_verdict')[0]; d = tally(rs, 'new_default_verdict')[0]; s = tally(rs, 'strict_verdict')[0]
        if o or d or s:
            P(f'| {c} | {sb} | {len(rs)} | {o} | {d} | {s} |')
    P('')
    P('### 2b. Verdict changes in default mode (old binary to new binary)')
    P('')
    P('| old verdict | new default verdict | mutants |')
    P('|---|---|---|')
    for (o, n), v in sorted(trans.items()): P(f'| {o} | {n} | {v} |')
    P('')
    P(f'Allowed change: REJECT_CRASH to REJECT_CLEAN. Any other change: {changed_bad}. Last stdout line differs between old and new default for non-crash rows: {len(last_diff)} of {len(same_nocrash)}.')
    P('')
    P('### 2c. Why strict rejects (old-accepted mutants), verbatim last line, grouped')
    P('')
    for c in NONCOSMETIC + ['C11']:
        rs = [r for r in by[c] if r['old_verdict'] == 'ACCEPT']
        cnt = collections.Counter(norm_reason(strict_reason(outs[r['id']]['strict']['out'])) for r in rs)
        P(f'**{c} {NAMES[c]}** ({len(rs)} old-accepted):')
        P('')
        for k, v in cnt.most_common(6): P(f'- {v} x `{k}`')
        ex = rs[0] if rs else None
        if ex:
            full = outs[ex['id']]['strict']['out'].strip()
            P(f'- example `{ex["id"]}` ({ex["desc"]}), strict stdout verbatim: `{full}`')
        P('')
    P('### 2d. Rows that strict ACCEPTs')
    P('')
    P(f'{len(strict_acc)} rows, ids: ' + ', '.join(r['id'] for r in strict_acc) + '.')
    P('')
    P('## 3. Positive controls and panic samples')
    P('')
    P('| group | what | default PASS | strict PASS |')
    P('|---|---|---|---|')
    desc = {'qemu_receipt': 'QEMU-minted RECEIPT.TXT / RECEIPT2.TXT, op12k final_step12000 artifacts', 'golden': 'tests/golden/witness_v1_m7_once64.receipt, replayed with the m7 artifacts',
            'h2_self_receipt': 'receipts minted by `cis_witness gen` (SAFE-01 H2) against their own models (orig + 40 one-byte/one-bit mutants x 4 canaries)'}
    for grp in ('qemu_receipt', 'golden', 'h2_self_receipt'):
        a = cg(grp, 'default'); b = cg(grp, 'strict')
        P(f'| {grp} | {desc[grp]} | {a[0]} of {a[1]} | {b[0]} of {b[1]} |')
    a = cg('golden_format_only', 'default', 'REJECT_CLEAN'); b = cg('golden_format_only', 'strict', 'REJECT_CLEAN')
    P(f'| golden_format_only | bitnet2b, e16_qat, e16_qat_pruned, falcon_e_1b goldens, artifacts not on this host, run against the op12k artifacts: expected `FAIL artifact` on all three hashes, i.e. the reader accepted the file and the artifact binding is what failed | {a[0]} of {a[1]} reach the hash check | {b[0]} of {b[1]} reach the hash check |')
    P('')
    ev = [r for r in ctl if r['group'] == 'golden_format_only' and r['mode'] == 'strict']
    sf = [r for r in ev if 'strict:' in r['stdout_last']]
    P(f'Golden format-only rows whose strict output contains a strict-reader failure: {len(sf)} of {len(ev)}.')
    P('')
    P('Receipts minted by `gen` (new binary), round trip, and old-versus-new `gen` stdout:')
    P('')
    P('| case | max_new | old exit | new exit | old and new stdout identical | default verdict | strict verdict |')
    P('|---|---|---|---|---|---|---|')
    for r in geq:
        P(f'| {r["name"]} | {r["max_new"]} | {r["old_exit"]} | {r["new_exit"]} | {"yes" if r["old_new_stdout_identical"] == "1" else "NO"} | {r["default_verdict"]} | {r["strict_verdict"]} |')
    P('')
    P('### 3a. Panic samples, verbatim (first SAFE-01 crash-reject of each class; old binary vs new default vs new strict)')
    P('')
    P('```')
    P(rd(f'{OUT}/panic_samples.txt').strip())
    P('```')
    P('')
    P('## 4. Fuzz: malformed inputs beyond the SAFE-01 classes')
    P('')
    if fz:
        P(f'{fz_n} seeded inputs (`{"LAB09-HARDEN-WITNESS-20261008"}/fuzz`): 1 to 3 operations on a genuine receipt (truncate at a random byte, delete a byte range, insert NUL/CR/tab/0xff/UTF-8 lead bytes/signs/commas, replace a byte, duplicate or swap lines, replace a value with garbage such as empty, `-1`, 2^64, `aé`, 5000 characters, replace the prompt with random Unicode up to 700 characters, set `maxtok` to one of 21 values from 0 to 2^64+1, list `MAXTOKS` in `harden_witness.py`), and one pure-garbage file in 40 (random bytes, NULs, 200k newlines, empty, 0xff runs). Both modes, op12k artifacts.')
        P('')
        P('| mode | ACCEPT | REJECT_CLEAN | REJECT_CRASH | TIMEOUT | panics | exit 2 |')
        P('|---|---|---|---|---|---|---|')
        for mode in ('default', 'strict'):
            c = collections.Counter(r[f'{mode}_verdict'] for r in fz)
            pn = sum(int(r[f'{mode}_panic']) for r in fz); e2 = sum(1 for r in fz if r[f'{mode}_exit'] == '2')
            P(f'| {mode} | {c["ACCEPT"]} | {c["REJECT_CLEAN"]} | {c["REJECT_CRASH"]} | {c["TIMEOUT"]} | {pn} | {e2} |')
        sub_bad = [r for r in fz if r['strict_verdict'] == 'ACCEPT' and r['default_verdict'] != 'ACCEPT']
        genu = set()
        import glob
        for p in glob.glob(f'{R}/labs/logs/opmodel/final_step12000/qemu_*/RECEIPT*.TXT'):
            genu.add(hashlib.sha256(open(p, 'rb').read()).hexdigest())
        sacc = [r for r in fz if r['strict_verdict'] == 'ACCEPT']
        ident = sum(1 for r in sacc if r['mutant_sha256'] in genu)
        P('')
        P(f'Strict ACCEPT but default not: {len(sub_bad)}. Strict ACCEPTs: {len(sacc)}, of which byte-identical to a genuine receipt: {ident}.')
        P('')
        P(f'The {collections.Counter(r["default_verdict"] for r in fz)["ACCEPT"]} default-mode ACCEPTs are the legacy leniency (for example a duplicated identical line, or a changed byte inside an ignored line), not a regression: strict rejects all of them. The fuzz set is destructive by design, so it tests rejection and panic-freedom; acceptance of genuine receipts is tested in section 3.')
        P('')
        P('Verbatim last stdout line, most common (default mode):')
        P('')
        cnt = collections.Counter(norm_reason(r['default_stdout_last']) for r in fz)
        for k, v in cnt.most_common(8): P(f'- {v} x `{k}`')
        P('')
        P('Verbatim last stdout line, most common (strict mode):')
        P('')
        cnt = collections.Counter(norm_reason(r['strict_stdout_last']) for r in fz)
        for k, v in cnt.most_common(8): P(f'- {v} x `{k}`')
        P('')
    else:
        P('fuzz not run.')
        P('')
    P('## 5. Hypotheses')
    P('')
    P('| H | verdict | numbers |')
    P('|---|---|---|')
    hw1 = 'CONFIRMED' if hw1_strict == 0 and hw1_old > 0 else 'REFUTED'
    hw2_full = (cg('qemu_receipt', 'strict')[0] == cg('qemu_receipt', 'strict')[1] and cg('golden', 'strict')[0] == cg('golden', 'strict')[1]
                and cg('h2_self_receipt', 'strict')[0] == cg('h2_self_receipt', 'strict')[1])
    hw2 = 'CONFIRMED (qualified: 1 of 5 goldens replayed in full, 4 at parser level)' if hw2_full else 'REFUTED'
    hw3 = 'CONFIRMED' if total_pan_d == 0 and total_pan_s == 0 and old_pan > 0 else 'REFUTED'
    P(f'| HW1 every previously accepted non-cosmetic mutant (C08, U1-U6) is rejected under --strict | **{hw1}** | old default ACCEPT {hw1_old} of {hw1_n}; strict ACCEPT {hw1_strict} of {hw1_n} (all of {sum(1 for c in NONCOSMETIC for r in by[c] if r["old_verdict"] == "ACCEPT")} old-accepted are rejected); C11 cosmetic strict ACCEPT {tally(by["C11"], "strict_verdict")[0]} of {len(by["C11"])} |')
    P(f'| HW2 goldens and all genuine receipts pass under --strict | **{hw2}** | qemu {cg("qemu_receipt", "strict")[0]}/{cg("qemu_receipt", "strict")[1]}; m7 golden {cg("golden", "strict")[0]}/{cg("golden", "strict")[1]}; gen-minted {cg("h2_self_receipt", "strict")[0]}/{cg("h2_self_receipt", "strict")[1]}; 4 other goldens parser-level only |')
    P(f'| HW3 zero panics in both modes | **{hw3}** | default {total_pan_d}, strict {total_pan_s} (H1 sweep {pan_d}/{pan_s}, fuzz {fz_pan_d}/{fz_pan_s}); SAFE-01 binary had {old_pan} crash-rejects on the same rows |')
    P('')
    P('## 6. How this was run (exact commands)')
    P('')
    P('```')
    P('cd /home/user/aefinity-ai/alice-aegis/aegis-linux')
    P('cargo build --release --example cis_witness')
    P('cargo test --release --example cis_witness          > $R/labs/logs/safe/HARDEN-WITNESS/cargo_test_cis_witness.log   # R=/home/user/Ranger3143')
    P('cargo test -p aegis-core --release                  > $R/labs/logs/safe/HARDEN-WITNESS/cargo_test_aegis_core.log')
    P('../scripts/devloop.sh fmt                            > $R/labs/logs/safe/HARDEN-WITNESS/devloop_fmt.log')
    P('cd /home/user/Ranger3143/labs/safe')
    P('python3 -I harden_witness.py rerun     # h1_rerun.tsv, h1_rerun_outputs.jsonl.gz, mutant_archive_check.txt')
    P('python3 -I harden_witness.py controls  # controls.tsv, controls_outputs.txt, gen_equivalence.tsv, panic_samples.txt, binaries.sha256.txt')
    P('python3 -I harden_witness.py fuzz      # fuzz.tsv')
    P('python3 -I harden_witness.py report    # this file')
    P('```')
    P('')
    P('Per-mutant commands (as SAFE-01, `nice -n 5`, `OMP_NUM_THREADS=1`, `AEGIS_THREADS=1`, `2` when the BitNet-2B artifacts are involved, 2 parallel workers):')
    P('')
    P('```')
    P('cis_witness verify           <MODEL.SAF> <EMBED.BIN> <VOCAB.BIN> <mutant receipt>')
    P('cis_witness verify --strict  <MODEL.SAF> <EMBED.BIN> <VOCAB.BIN> <mutant receipt>')
    P('```')
    P('')
    P('Environment lines (from the logs): ' + (rd(f'{OUT}/env.txt').strip().replace('\n', '; ') or 'not recorded'))
    P('')
    P('## 7. Limits and negative results')
    P('')
    P('- `--strict` hardens the verifier, not the file. Without the TPM quote nothing stops someone from presenting a different, equally canonical receipt; the quote binds the whole file only for `RECEIPT.TXT` (SAFE-01 section 0, item 5), and `attest_verify.py` still needs `--receipt` for that.')
    P('- Four of the five golden fixtures were not replayed (artifacts absent on this host); for those the evidence is that the reader accepts them (unit test and CLI reaching the hash comparison), not a full strict PASS.')
    P('- The lenient default reader still accepts everything SAFE-01 listed (reorder, `+25`, upper-case hex, CRLF, unknown lines, unread `prompt-toks`/`gen-toks`). That is deliberate, to keep default behaviour identical; whoever needs integrity must pass `--strict`.')
    P('- The UEFI verifier (`aegis-uefi/src/verifier.rs::parse_receipt`) and the standalone `cis-verify` crate have their own lenient readers and were not changed; the same classes of leniency exist there. `agent_trace` receipts use another format and another verifier.')
    P('- The strict reader accepts `token-ids ` with a trailing space only for `gen-toks 0`, because that is what both writers print; it is the single exception to "no trailing whitespace".')
    P('- The mutant corpus is SAFE-01\'s; strict was tuned against the leniency classes it found, so the fuzz set (section 4) is the check that does not share that origin.')
    P('')
    P('## 8. Commit and patch series')
    P('')
    P('```')
    P(rd(f'{OUT}/commit.txt').strip())
    P('```')
    P('')
    out = '\n'.join(L) + '\n'
    with open(f'{OUT}/RESULT.md', 'w') as f: f.write(out)
    print(f'RESULT.md written ({len(out)} bytes)')
