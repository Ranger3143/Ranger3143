#!/usr/bin/env python3
"""Host-side verifier for AEGIS-ATTEST v0 (ATTEST.TXT written by the unikernel). Pure stdlib + openssl.

usage: attest_verify.py ATTEST.TXT [--receipt RECEIPT.TXT] [--artifacts DIR]
                        [--strict] [--expect-pubkey HEX] [--allow-no-quote] [--reject-high-s] [--efi BOOTX64.EFI]
       attest_verify.py ATTEST.TXT --print-pubkey          (prints the quote's key x||y; NOT a verification)

exit 0 = every check passed; 1 = at least one FAIL; 2 = usage/parse error.  The receipt is NOT positional:
`attest_verify.py ATTEST.TXT RECEIPT.TXT` is a usage error (exit 2); write `--receipt RECEIPT.TXT`.

Checks (labs/tools/README-attest_verify.md has the full list and what each flag adds):
  PCR 12 / 13  replayed from the `measured` lines: PCR_n = SHA256(PCR_{n-1} || SHA256(line_n)), PCR_0 = 32 zero bytes,
               and compared with the `pcr` lines the unikernel read back from the TPM. Each `measured` line must have a
               matching `event` line (same PCR, same position, digest = SHA-256(line), data = line, type 0xd EV_IPL);
               an `event` line without a `measured` line is a FAIL.
  PCR 4        replayed with the same extend rule from the SHA-256 digests of its `event pcr=4` lines (the firmware's
               own log) and compared with the read-back value; PCR 4 events must be one of EV_EFI_ACTION / EV_SEPARATOR /
               EV_EFI_BOOT_SERVICES_APPLICATION, and the digests of the first two must equal SHA-256 of their logged data.
  quote        fail-closed: a missing or garbled quote is a FAIL unless --allow-no-quote. TPMS_ATTEST magic/type,
               extraData == quote-qualifying (== SHA-256(RECEIPT.TXT) with --receipt), pcrDigest == SHA-256 over the
               PCRs in the quote's own selection, ECDSA-P256/SHA-256 signature (openssl); every PCR the file reports must be in
               that selection; the unsigned quote-pcrs /
               quote-public / quote-key / quote-retries lines are cross-checked against the signed data.
  --expect-pubkey HEX   pins the signer (128 hex chars x||y, or 130 with the 04 prefix).
  --strict     canonical file form (exact grammar, lowercase hex, no CR / blank / trailing-space lines, fixed line
               order), a mandatory --receipt, and no --allow-no-quote.
  --efi FILE   PCR 4's EV_EFI_BOOT_SERVICES_APPLICATION digest must equal the Authenticode SHA-256 of FILE (the
               EFI binary that was booted) and its logged image length / link address must match that PE file.
  --reject-high-s       also refuse ECDSA s > n/2. libtpms does NOT normalise s (about half of genuine quotes are
               high-s), so this is deliberately not part of --strict.
"""
import argparse, hashlib, os, re, struct, subprocess, sys, tempfile

P256_N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
P256_P = 2**256 - 2**224 + 2**192 + 2**96 - 1
P256_B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
TPM_RH_OWNER = bytes.fromhex('40000001')
EV_IPL = 0xD
EV_SEPARATOR = 0x4
EV_EFI_ACTION = 0x80000007
EV_EFI_BOOT_SERVICES_APPLICATION = 0x80000003
# quote lines, in the order the unikernel writes them (aegis-uefi/src/attest.rs)
QKEYS = ['quote-pcrs', 'quote-qualifying', 'quote-pub-x', 'quote-pub-y', 'quote-public', 'quote-attest',
         'quote-sig-r', 'quote-sig-s', 'quote-retries', 'quote-key']
QHEX32 = ('quote-qualifying', 'quote-pub-x', 'quote-pub-y', 'quote-sig-r', 'quote-sig-s')
KEY_TAIL = 'transient (this boot)'      # constant tail of the unikernel's quote-key line
MAX_RETRIES = 16                        # two TPM submissions x fewer than 8 resends each (attest.rs)


def sha256(b): return hashlib.sha256(b).digest()


def extend_chain(digests):
    pcr = bytes(32)
    for d in digests:
        pcr = sha256(pcr + d)
    return pcr


def replay(lines):
    return extend_chain([sha256(l.encode()) for l in lines])


class Check:
    """Prints one `<text> PASS|FAIL` line per check and remembers whether everything passed."""
    def __init__(self): self.ok = True
    def __call__(self, text, good, suffix=''):
        good = bool(good); self.ok &= good
        print(f'{text} {"PASS" if good else "FAIL"}{suffix}')
        return good


# ----------------------------------------------------------------------------- DER / TPM structure helpers
def _der_len(n):
    return bytes([n]) if n < 128 else b'\x81' + bytes([n]) if n < 256 else b'\x82' + n.to_bytes(2, 'big')


def _der_int(b):
    b = b.lstrip(b'\x00') or b'\x00'
    if b[0] & 0x80: b = b'\x00' + b
    return b'\x02' + _der_len(len(b)) + b


def p256_spki(x, y):
    alg = bytes.fromhex('301306072a8648ce3d020106082a8648ce3d030107')
    pt = b'\x04' + x + y
    bits = b'\x03' + _der_len(len(pt) + 1) + b'\x00' + pt
    body = alg + bits
    return b'\x30' + _der_len(len(body)) + body


def on_curve(x, y):
    x = int.from_bytes(x, 'big'); y = int.from_bytes(y, 'big')
    return x < P256_P and y < P256_P and (y * y - (x * x * x - 3 * x + P256_B)) % P256_P == 0


def authenticode_sha256(path):
    """(Authenticode SHA-256 hex, file size, ImageBase) of a PE32+ image: the digest EDK2 extends into PCR 4."""
    d = open(path, 'rb').read()
    pe = struct.unpack_from('<I', d, 0x3C)[0]
    if d[pe:pe + 4] != b'PE\0\0': raise ValueError('no PE signature')
    nsec = struct.unpack_from('<H', d, pe + 6)[0]; osz = struct.unpack_from('<H', d, pe + 20)[0]
    opt = pe + 24
    if struct.unpack_from('<H', d, opt)[0] != 0x20B: raise ValueError('not a PE32+ image')
    chk = opt + 64; ddir = opt + 112 + 4 * 8                      # CheckSum; security (certificate) data directory entry
    cert_off, cert_sz = struct.unpack_from('<II', d, ddir + 4)
    hdr = struct.unpack_from('<I', d, opt + 60)[0]
    base = struct.unpack_from('<Q', d, opt + 24)[0]
    h = hashlib.sha256()
    h.update(d[:chk]); h.update(d[chk + 4:ddir]); h.update(d[ddir + 8:hdr])
    secs = sorted(struct.unpack_from('<II', d, opt + osz + 40 * i + 16)[::-1] for i in range(nsec))   # (PointerToRawData, SizeOfRawData)
    pos = hdr
    for rp, rs in secs:
        if rs: h.update(d[rp:rp + rs]); pos = rp + rs
    end = cert_off if cert_sz else len(d)
    if end > pos: h.update(d[pos:end])
    return h.hexdigest(), len(d), base


class Rd:
    """Bounds-checked big-endian reader for TPM structures."""
    def __init__(self, b): self.b, self.o = b, 0
    def take(self, n):
        if n < 0 or self.o + n > len(self.b): raise ValueError('truncated structure')
        v = self.b[self.o:self.o + n]; self.o += n; return v
    def u8(self): return self.take(1)[0]
    def u16(self): return int.from_bytes(self.take(2), 'big')
    def u32(self): return int.from_bytes(self.take(4), 'big')
    def b16(self): return self.take(self.u16())
    def left(self): return len(self.b) - self.o


def parse_attest(a):
    """TPMS_ATTEST of type QUOTE: magic type qualifiedSigner extraData clockInfo(17) firmwareVersion(8) TPMS_QUOTE_INFO."""
    r = Rd(a)
    d = {'magic': r.take(4), 'type': r.take(2), 'qsigner': r.b16(), 'extra': r.b16()}
    r.take(17); r.take(8)
    cnt = r.u32()
    if cnt > 16: raise ValueError('implausible PCR selection count')
    sels = []
    for _ in range(cnt):
        alg = r.u16(); sz = r.u8(); bm = r.take(sz)
        sels.append((alg, [8 * i + bit for i, byte in enumerate(bm) for bit in range(8) if byte >> bit & 1]))
    d['sels'] = sels; d['pcr_digest'] = r.b16(); d['trailing'] = r.left()
    return d


def parse_tpmt_public(b):
    """TPMT_PUBLIC of an ECC key (TPM 2.0 Part 2, 12.2.4)."""
    r = Rd(b)
    d = {'type': r.u16(), 'nameAlg': r.u16(), 'attrs': r.u32(), 'authPolicy': r.b16()}
    if d['type'] != 0x0023: raise ValueError(f'key type 0x{d["type"]:04x} is not TPM_ALG_ECC')
    d['sym'] = r.u16()
    if d['sym'] != 0x0010: raise ValueError('symmetric algorithm is not NULL')
    d['scheme'] = r.u16(); d['schemeHash'] = r.u16() if d['scheme'] != 0x0010 else None
    d['curve'] = r.u16(); d['kdf'] = r.u16()
    if d['kdf'] != 0x0010: r.u16()
    d['x'] = r.b16(); d['y'] = r.b16(); d['trailing'] = r.left()
    return d


# ----------------------------------------------------------------------------- arguments
class Args(argparse.ArgumentParser):
    def error(self, msg):
        print(f'attest_verify.py: error: {msg}', file=sys.stderr); sys.exit(2)


def parse_args(argv):
    p = Args(prog='attest_verify.py', add_help=False, allow_abbrev=False, usage=argparse.SUPPRESS)
    p.add_argument('attest', nargs='?')
    for f in ('--receipt', '--artifacts', '--expect-pubkey', '--efi'):
        p.add_argument(f, action='append')          # collected as lists so that a repeated option can be refused
    for f in ('--strict', '--allow-no-quote', '--reject-high-s', '--print-pubkey', '-h', '--help'):
        p.add_argument(f, action='store_true')
    a, rest = p.parse_known_args(argv)
    for f in ('receipt', 'artifacts', 'expect_pubkey', 'efi'):
        v = getattr(a, f)
        if v is not None and len(v) != 1: p.error(f"--{f.replace('_', '-')} given {len(v)} times; it takes exactly one value")
        setattr(a, f, v[0] if v else None)
    if a.help or a.h or a.attest is None:
        print(__doc__); sys.exit(0 if (a.help or a.h) else 2)
    pos = [t for t in rest if not t.startswith('-')]
    if pos:
        p.error(f"unexpected positional argument '{pos[0]}': the receipt is not positional, use --receipt {pos[0]}")
    if rest:
        p.error(f"unrecognized argument '{rest[0]}'")
    if a.strict and a.allow_no_quote: p.error('--strict and --allow-no-quote are mutually exclusive')
    if a.allow_no_quote and a.expect_pubkey is not None: p.error('--expect-pubkey needs a quote: it cannot be combined with --allow-no-quote')
    if a.expect_pubkey is not None:
        h = re.sub(r'[\s:]', '', a.expect_pubkey).lower()
        if h.startswith('0x'): h = h[2:]
        if len(h) == 130 and h.startswith('04'): h = h[2:]
        if not re.fullmatch(r'[0-9a-f]{128}', h): p.error('--expect-pubkey wants 128 hex chars (x||y) or 130 with the 04 prefix')
        a.expect_pubkey = bytes.fromhex(h)
    if a.artifacts is not None and not os.path.isdir(a.artifacts): p.error(f"--artifacts: '{a.artifacts}' is not a directory")
    if a.efi is not None:
        try: a.efi_info = authenticode_sha256(a.efi)
        except (OSError, ValueError, struct.error) as e: p.error(f"--efi: cannot hash '{a.efi}' as a PE image ({e})")
    return a


# ----------------------------------------------------------------------------- ATTEST.TXT parsing
RX_MEASURED = re.compile(r'^measured pcr=(\d+) (.*)$')
RX_EVENT = re.compile(r'^event pcr=(\d+) type=(0x[0-9a-f]+) sha256=([0-9a-f]{64}|-) data=(.*)$')
RX_PCR = re.compile(r'^pcr (\d+) ([0-9a-f]{64})$')
RX_CPUID = re.compile(r'^cpuid vendor=\S+ brand="[^"]*" family=\d+ model=\d+ stepping=\d+ hypervisor=\d+$')


class Parsed:
    def __init__(self):
        self.measured = {}          # pcr -> [line text]
        self.events = []            # dicts
        self.pcrs = {}              # pcr -> 32 bytes
        self.kv = {}                # quote-* -> value
        self.problems = []          # FAIL in every mode
        self.qproblems = []         # FAIL in every mode (quote lines)
        self.strict_problems = []   # FAIL only under --strict
        self.notes = []
        self.quote_seen = False


def parse_file(raw):
    """Line-by-line parse against the grammar the unikernel emits. Returns None if the header is not exactly v0."""
    P = Parsed()
    text = raw.decode('utf-8', 'replace').replace('\r', '')
    lines = text.split('\n')
    if lines and lines[-1] == '': lines.pop()
    else: P.strict_problems.append('file does not end with a newline')
    if b'\r' in raw: P.strict_problems.append("CR characters present (not the unikernel's LF form)")
    if any(not (0x20 <= b < 0x7f or b == 0x0a) for b in raw.replace(b'\r', b'')):
        P.strict_problems.append('non-ASCII or control characters present')
    if not lines or lines[0] != 'AEGIS-ATTEST v0':
        return None
    seen = set(); rank_last = 0; qorder = -1; last_pcr = -1
    for i, l in enumerate(lines):
        if i == 0: continue
        n = i + 1
        if l != l.strip(): P.strict_problems.append(f'line {n}: leading/trailing whitespace')
        rank = None
        if RX_MEASURED.match(l):
            m = RX_MEASURED.match(l); P.measured.setdefault(int(m.group(1)), []).append(m.group(2)); rank = 3
        elif l.startswith('measured '):
            P.problems.append(f'line {n}: malformed measured line'); rank = 3
        elif RX_EVENT.match(l):
            m = RX_EVENT.match(l)
            P.events.append(dict(i=i, pcr=int(m.group(1)), typ=int(m.group(2), 16), typs=m.group(2), sha=m.group(3), data=m.group(4), line=l)); rank = 4
        elif l.startswith('event '):
            P.problems.append(f'line {n}: malformed event line'); rank = 4
        elif RX_PCR.match(l):
            m = RX_PCR.match(l); k = int(m.group(1))
            if k in P.pcrs: P.problems.append(f'line {n}: duplicate pcr {k} line')
            P.pcrs[k] = bytes.fromhex(m.group(2)); rank = 5
            if k <= last_pcr: P.strict_problems.append(f'line {n}: pcr lines not in ascending order')
            last_pcr = k
        elif l.startswith('pcr '):
            P.problems.append(f'line {n}: malformed pcr line'); rank = 5
        elif l == 'pcr-bank sha256':
            if 'pcr-bank' in seen: P.problems.append(f'line {n}: duplicate pcr-bank line')
            seen.add('pcr-bank'); rank = 2
        elif l.startswith('pcr-bank'):
            P.problems.append(f'line {n}: pcr-bank line is not exactly "pcr-bank sha256"'); rank = 2
        elif l.startswith('cpuid '):
            if 'cpuid' in seen: P.problems.append(f'line {n}: duplicate cpuid line')
            seen.add('cpuid'); rank = 1
            if not RX_CPUID.match(l): P.strict_problems.append(f'line {n}: cpuid line does not match the unikernel grammar')
        elif l.startswith('quote-'):
            rank = 6; key = l.split(' ', 1)[0]
            if key == 'quote-error':
                P.qproblems.append(f'line {n}: unikernel reported {l[:80]!r}')
            elif key not in QKEYS:
                P.qproblems.append(f'line {n}: unknown quote line {key!r}')
            else:
                P.quote_seen = True
                m = re.match(r'^quote-key (.+)$', l) if key == 'quote-key' else re.match(r'^' + key + r' (\S+)$', l)
                if not m:
                    P.qproblems.append(f'line {n}: {key} line is malformed')
                else:
                    v = m.group(1)
                    if key in P.kv: P.qproblems.append(f'line {n}: duplicate {key} line')
                    P.kv[key] = v
                    if key == 'quote-pcrs':
                        if not re.fullmatch(r'\d+(,\d+)*', v): P.qproblems.append(f'line {n}: quote-pcrs is not a comma list of integers')
                    elif key == 'quote-retries':
                        if not re.fullmatch(r'\d+', v): P.qproblems.append(f'line {n}: quote-retries is not an integer')
                    elif key != 'quote-key':
                        if not re.fullmatch(r'(?:[0-9a-fA-F]{2})+', v): P.qproblems.append(f'line {n}: {key} is not hex')
                        if v != v.lower(): P.strict_problems.append(f'line {n}: {key} is not lowercase hex')
                        if key in QHEX32 and len(v) != 64: P.strict_problems.append(f'line {n}: {key} is not exactly 32 bytes')
                    qi = QKEYS.index(key)
                    if qi <= qorder: P.strict_problems.append(f'line {n}: {key} out of the canonical order')
                    qorder = max(qorder, qi)
        elif l.startswith(('pcr-read-error', 'error ', 'eventlog:')):
            P.problems.append(f'line {n}: unikernel reported {l[:80]!r}'); rank = 7
        elif l == '':
            P.strict_problems.append(f'line {n}: blank line')
        else:
            P.notes.append(f'line {n}: unrecognised line ignored: {l[:60]!r}')
            P.strict_problems.append(f'line {n}: unrecognised line {l[:40]!r}')
        if rank is not None:
            if rank < rank_last: P.strict_problems.append(f'line {n}: section out of the canonical order')
            rank_last = max(rank_last, rank)
    if 'pcr-bank' not in seen: P.problems.append('missing "pcr-bank sha256" line')
    if 'cpuid' not in seen: P.strict_problems.append('missing cpuid line')
    return P


# ----------------------------------------------------------------------------- ATTEST part (PCR / event-log / receipt)
def attest_part(P, args):
    ck = Check()
    for m in P.problems: ck(f'format: {m}:', False)
    if args.strict:
        for m in P.strict_problems: ck(f'format (--strict): {m}:', False)
    for m in P.notes: print(f'note: {m}')
    pcrs, measured = P.pcrs, P.measured
    ev_by = {}
    for e in P.events: ev_by.setdefault(e['pcr'], []).append(e)
    # PCR 12 / 13 (and any other measured PCR): replay of the measured lines against the TPM read-back
    for p in sorted(set(measured) | {p for p in (12, 13) if p in pcrs}):
        exp = replay(measured.get(p, [])); got = pcrs.get(p)
        ck(f'pcr{p}: replayed {exp.hex()[:32]}.. tpm {got.hex()[:32] if got else None}..', got == exp, f' ({len(measured.get(p, []))} events)')
    # the event log must carry the same lines: same PCR, same position, same digest, same data, type EV_IPL
    for p in sorted(set(measured) | {q for q in ev_by if q != 4}):
        mlines = measured.get(p, []); evs = ev_by.get(p, [])
        for k, l in enumerate(mlines):
            d = sha256(l.encode()).hex(); e = evs[k] if k < len(evs) else None
            hit = e is not None and e['sha'] == d and e['data'] == l
            ck.ok &= hit
            print(f'eventlog pcr={p} sha256={d[:16]}.. {"PASS" if hit else "MISSING"} :: {l[:60]}')
            if e is not None: ck(f'eventlog pcr={p} #{k} type={e["typs"]} must be 0xd (EV_IPL):', e['typ'] == EV_IPL)
        for k in range(len(mlines), len(evs)):
            ck(f'eventlog pcr={p} #{k} has no measured line :: {evs[k]["data"][:60]}:', False)
    # PCR 4: replay from the firmware's own event digests
    ev4 = ev_by.get(4, [])
    if 4 in pcrs or ev4:
        got = pcrs.get(4)
        exp = extend_chain([bytes.fromhex(e['sha']) for e in ev4 if e['sha'] != '-'])
        ck(f'pcr4: replayed {exp.hex()[:32]}.. tpm {got.hex()[:32] if got else None}..',
           got == exp and all(e['sha'] != '-' for e in ev4), f' ({len(ev4)} events from the TCG log)')
        for k, e in enumerate(ev4):
            t, dat, sha = e['typ'], e['data'], e['sha']
            tag = f'eventlog pcr=4 #{k} type={e["typs"]}'
            if t == EV_EFI_ACTION:
                ck(f'{tag} EV_EFI_ACTION: digest == SHA-256(data string):', not dat.startswith('hex:') and sha == sha256(dat.encode()).hex())
            elif t == EV_SEPARATOR:
                sep = re.fullmatch(r'hex:((?:[0-9a-f]{2}){4})', dat)
                ck(f'{tag} EV_SEPARATOR: 4-byte value, digest == SHA-256(value):', bool(sep) and sha == sha256(bytes.fromhex(sep.group(1))).hex())
            elif t == EV_EFI_BOOT_SERVICES_APPLICATION:
                ck(f'{tag} EV_EFI_BOOT_SERVICES_APPLICATION: image-load event data is well-formed hex:', bool(re.fullmatch(r'hex:(?:[0-9a-f]{2}){32,}', dat)))
                print(f'note: pcr4 #{k} digest is the PE image hash; the logged data is not covered by it (informational)')
            else:
                ck(f'{tag}: not one of the three event types the PC Client profile allows in PCR 4 (EV_EFI_ACTION, EV_SEPARATOR, EV_EFI_BOOT_SERVICES_APPLICATION):', False)
    if args.efi:
        ah, fsize, ibase = args.efi_info
        apps = [e for e in ev4 if e['typ'] == EV_EFI_BOOT_SERVICES_APPLICATION]
        hit = [e for e in apps if e['sha'] == ah]
        ck(f'pcr4 EV_EFI_BOOT_SERVICES_APPLICATION digest == Authenticode SHA-256 of {os.path.basename(args.efi)} ({ah[:16]}..):', bool(hit))
        if hit:
            m = re.match(r'hex:((?:[0-9a-f]{2}){32,})', hit[0]['data'])
            b = bytes.fromhex(m.group(1)) if m else b''
            ck('pcr4 image-load event: ImageLengthInMemory == size of --efi file and ImageLinkTimeAddress == its ImageBase:',
               len(b) >= 32 and int.from_bytes(b[8:16], 'little') == fsize and int.from_bytes(b[16:24], 'little') == ibase)
    if 4 in pcrs:
        print(f'pcr4 (firmware measurement of BOOTX64.EFI): {pcrs[4].hex()} ; {len(ev4)} event(s) in log')
        for e in ev4: print('   ', e['line'][:200])
    # local copies of the measured artifacts
    if args.artifacts:
        found = 0
        for l in measured.get(12, []):
            m = re.match(r'AEGIS-MEASURE v0 artifact=(\S+) bytes=(\d+) sha256=([0-9a-f]{64})', l)
            if not m: continue
            name = m.group(1); f = os.path.join(args.artifacts, name)
            if '/' in name: ck(f'artifact {name}: name contains a path separator:', False); continue
            if not os.path.isfile(f): print(f'artifact {name}: not in --artifacts dir, not checked (SKIP)'); continue
            found += 1
            h = hashlib.sha256(open(f, 'rb').read()).hexdigest()
            ck(f'artifact {name}: local sha256 {h[:16]}..', h == m.group(3) and os.path.getsize(f) == int(m.group(2)))
        if not found: ck('artifacts: --artifacts was given but none of the measured artifacts is in it:', False)
    # the receipt must be bound in a PCR 13 line
    if args.receipt:
        rt = open(args.receipt, 'rb').read().decode('utf-8', 'replace').replace('\r', '')
        chains = re.findall(r'^chain ([0-9a-f]{64})$', rt, re.M); cis = re.findall(r'^cis-digest ([0-9a-f]{16})$', rt, re.M)
        if len(chains) != 1 or len(cis) != 1:
            ck('receipt: needs exactly one chain line and one cis-digest line:', False)
        else:
            def toks(line): return dict(re.findall(r'(\S+?)=(\S+)', line))
            hit = any(toks(l).get('chain') == chains[0] and toks(l).get('cis-digest') == cis[0] for l in measured.get(13, []))
            ck(f'receipt chain {chains[0][:16]}.. bound in PCR13 line:', hit)
    elif args.strict:
        ck('receipt: --strict requires --receipt:', False)
    else:
        print('note: no --receipt given; the quote is not bound to any receipt')
    print('ATTEST VERIFY', 'PASS' if ck.ok else 'FAIL')
    return ck.ok


# ----------------------------------------------------------------------------- quote part
def quote_part(P, args):
    """True / False, or None when the file has no quote and --allow-no-quote was given."""
    kv = P.kv
    for m in P.qproblems: print(f'quote: {m} FAIL')
    if not P.quote_seen and not P.qproblems:
        if args.allow_no_quote:
            print('quote: none in file')
            print('WARNING: --allow-no-quote: no TPM signature covers this file; it is NOT origin-authenticated')
            return None
        print('quote: none in file FAIL (fail-closed: --allow-no-quote accepts a file that predates the quote)')
        return False
    missing = [k for k in QKEYS if k not in kv]
    if missing:
        print(f'quote: incomplete or garbled quote block, missing or unparsable {missing} FAIL')
        return False
    ck = Check(); ck.ok = not P.qproblems
    pcrs = P.pcrs
    try:
        attest = bytes.fromhex(kv['quote-attest']); pub_raw = bytes.fromhex(kv['quote-public']); qual = bytes.fromhex(kv['quote-qualifying'])
        x = bytes.fromhex(kv['quote-pub-x']); y = bytes.fromhex(kv['quote-pub-y'])
        r = bytes.fromhex(kv['quote-sig-r']); s_ = bytes.fromhex(kv['quote-sig-s'])
    except ValueError as e:
        print(f'quote: hex decoding failed ({e}) FAIL'); return False
    try:
        A = parse_attest(attest)
    except ValueError as e:
        print(f'quote attest does not parse as TPMS_ATTEST ({e}) FAIL'); return False
    magic = A['magic'].hex(); typ = A['type'].hex()
    ck(f'quote attest magic={magic} type={typ}', magic == 'ff544347' and typ == '8018')
    ck('quote attest ends with the TPMS_QUOTE_INFO (no trailing bytes):', A['trailing'] == 0)
    sel_pcrs = [p for alg, ps in A['sels'] for p in ps]
    ck(f'quote PCR selection is a single SHA-256 bank selection {sel_pcrs}:', len(A['sels']) == 1 and A['sels'][0][0] == 0x000B)
    claimed = set(pcrs) | set(P.measured) | {e['pcr'] for e in P.events}
    ck(f'every PCR the file reports {sorted(claimed)} is inside the quote selection {sel_pcrs} (nothing is claimed that the quote does not cover):', claimed <= set(sel_pcrs))
    ck(f'quote extraData == qualifying ({qual.hex()[:16]}..):', A['extra'] == qual)
    if args.receipt:
        ck('quote qualifying == SHA-256(RECEIPT.TXT):', sha256(open(args.receipt, 'rb').read()) == qual)
    comp = sha256(b''.join(pcrs[p] for p in sel_pcrs if p in pcrs))
    ck(f'quote pcrDigest over PCRs {sel_pcrs} == SHA-256(PCR values read back):', comp == A['pcr_digest'] and all(p in pcrs for p in sel_pcrs))
    # unsigned lines versus the signed TPMS_ATTEST and the parsed key
    qp = [int(v) for v in kv['quote-pcrs'].split(',')] if re.fullmatch(r'\d+(,\d+)*', kv['quote-pcrs']) else None
    ck(f'quote-pcrs line [{kv["quote-pcrs"]}] == PCR list in the signed TPMS_ATTEST {sel_pcrs}:', qp == sel_pcrs)
    K = None
    try:
        K = parse_tpmt_public(pub_raw); why = []
        if K['nameAlg'] != 0x000B: why.append('nameAlg is not SHA-256')
        if K['scheme'] != 0x0018 or K['schemeHash'] != 0x000B: why.append('scheme is not ECDSA/SHA-256')
        if K['curve'] != 0x0003: why.append('curve is not NIST P-256')
        if len(K['x']) != 32 or len(K['y']) != 32: why.append('point coordinates are not 32 bytes')
        if K['trailing']: why.append('bytes after the TPMT_PUBLIC')
        need = 0x2 | 0x10 | 0x10000 | 0x40000      # fixedTPM | fixedParent | restricted | sign
        if K['attrs'] & need != need or K['attrs'] & 0x20000: why.append(f'attributes 0x{K["attrs"]:08x} are not a fixed restricted signing key')
        if K['x'] != x or K['y'] != y: why.append('unique point != quote-pub-x/quote-pub-y')
        elif len(x) == 32 and len(y) == 32 and not on_curve(x, y): why.append('point is not on P-256')
        ck('quote-public is a fixed restricted ECC P-256 ECDSA/SHA-256 signing key whose point == quote-pub-x/y'
           + (f' ({"; ".join(why)})' if why else '') + ':', not why)
    except ValueError as e:
        ck(f'quote-public does not parse as TPMT_PUBLIC ({e}):', False)
    qn = b'\x00\x0b' + sha256(TPM_RH_OWNER + b'\x00\x0b' + sha256(pub_raw))
    owner = A['qsigner'] == qn
    ck('quote qualifiedSigner == H(TPM_RH_OWNER || Name(quote-public)) (the signed attest names this key, a primary under the owner hierarchy):', owner)
    desc = ''
    if K is not None:
        desc = ' '.join([{3: 'ecc-p256'}.get(K['curve'], f'curve-0x{K["curve"]:04x}'),
                         'ecdsa-sha256' if (K['scheme'], K['schemeHash']) == (0x18, 0x0B) else f'scheme-0x{K["scheme"]:04x}',
                         'owner-hierarchy' if owner else 'unverified-hierarchy', KEY_TAIL])
    ck(f'quote-key "{kv["quote-key"]}" == description derived from the signed data:', desc != '' and kv['quote-key'] == desc)
    rt = int(kv['quote-retries']) if kv['quote-retries'].isdigit() else None
    ck(f'quote-retries {kv["quote-retries"]} is an integer in 0..{MAX_RETRIES} (informational counter, outside the signature):', rt is not None and 0 <= rt <= MAX_RETRIES)
    # signature (over the key from the signed-data-consistent TPMT_PUBLIC when it parsed)
    high_s = int.from_bytes(s_, 'big') > P256_N // 2
    sig = _der_int(r) + _der_int(s_); sig = b'\x30' + _der_len(len(sig)) + sig
    px, py = (K['x'], K['y']) if K is not None and len(K['x']) == 32 and len(K['y']) == 32 else (x, y)
    with tempfile.TemporaryDirectory() as td:
        open(f'{td}/pub.der', 'wb').write(p256_spki(px, py)); open(f'{td}/sig.der', 'wb').write(sig); open(f'{td}/attest.bin', 'wb').write(attest)
        r0 = subprocess.run(['openssl', 'pkey', '-pubin', '-inform', 'DER', '-in', f'{td}/pub.der', '-out', f'{td}/pub.pem'], capture_output=True, text=True)
        if r0.returncode != 0:
            ck('quote signer key is rejected by openssl:', False)
        else:
            res = subprocess.run(['openssl', 'dgst', '-sha256', '-verify', f'{td}/pub.pem', '-signature', f'{td}/sig.der', f'{td}/attest.bin'], capture_output=True, text=True)
            ck(f'quote ECDSA-P256/SHA-256 signature over TPMS_ATTEST (openssl): {res.stdout.strip() or res.stderr.strip()}', 'Verified OK' in res.stdout)
            tam = bytearray(attest); tam[-1] ^= 1; open(f'{td}/tam.bin', 'wb').write(bytes(tam))   # negative control
            res2 = subprocess.run(['openssl', 'dgst', '-sha256', '-verify', f'{td}/pub.pem', '-signature', f'{td}/sig.der', f'{td}/tam.bin'], capture_output=True, text=True)
            ck('quote tampered attest rejected:', 'Verified OK' not in res2.stdout)
    if args.reject_high_s:
        ck('quote signature s <= n/2 (--reject-high-s):', not high_s)
    else:
        print(f'note: quote signature s is {"HIGH (> n/2)" if high_s else "low (<= n/2)"}; libtpms does not normalise s, so both are accepted unless --reject-high-s')
    if args.expect_pubkey is not None:
        ck(f'quote signer == pinned key ({args.expect_pubkey.hex()[:16]}..):', (px + py) == args.expect_pubkey)
    else:
        print('note: signer key not pinned (--expect-pubkey); the quote shows consistency with SOME P-256 key, not which TPM')
    print('quote pub-x', x.hex()[:16] + '..', 'clockInfo/firmwareVersion present; signer qualifiedName len', len(A['qsigner']))
    return ck.ok


def main(argv):
    args = parse_args(argv[1:])
    try:
        raw = open(args.attest, 'rb').read()
    except OSError as e:
        print(f'attest_verify.py: cannot read {args.attest}: {e}', file=sys.stderr); return 2
    if args.receipt is not None:
        try: open(args.receipt, 'rb').close()
        except OSError as e:
            print(f'attest_verify.py: cannot read receipt {args.receipt}: {e}', file=sys.stderr); return 2
    P = parse_file(raw)
    if P is None:
        print('FAIL: not an AEGIS-ATTEST v0 file'); return 2
    if args.print_pubkey:
        try:
            K = parse_tpmt_public(bytes.fromhex(P.kv['quote-public'])); print((K['x'] + K['y']).hex()); return 0
        except (KeyError, ValueError) as e:
            print(f'attest_verify.py: no usable quote-public line ({e})', file=sys.stderr); return 2
    rc = 0
    try:
        if not attest_part(P, args): rc = 1
    except Exception as e:
        print('ATTEST VERIFY ERROR', repr(e)); return 1
    try:
        q = quote_part(P, args)
        if q is not None:
            print('QUOTE VERIFY', 'PASS' if q else 'FAIL')
            if not q: rc = 1
    except Exception as e:
        print('QUOTE VERIFY ERROR', repr(e)); return 1
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
