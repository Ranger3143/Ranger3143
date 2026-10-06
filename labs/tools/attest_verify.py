#!/usr/bin/env python3
"""Host-side verifier for AEGIS-ATTEST v0 (ATTEST.TXT written by the unikernel).

Replays PCR 12 (payload) and PCR 13 (receipt) from the `measured` lines:
    PCR_n = SHA256(PCR_{n-1} || SHA256(line_n)), PCR_0 = 32 zero bytes
and compares with the `pcr` lines the unikernel read back from the TPM via
TPM2_PCR_Read. Also cross-checks the measured artifact digests against local
files when given, and the receipt line against a RECEIPT.TXT. Pure stdlib.

usage: attest_verify.py ATTEST.TXT [--artifacts DIR] [--receipt RECEIPT.TXT]
exit 0 = every check passed; 1 = a mismatch; 2 = usage/parse error.
"""
import hashlib, os, re, sys

def sha256(b): return hashlib.sha256(b).digest()

def replay(lines):
    pcr = bytes(32)
    for l in lines:
        pcr = sha256(pcr + sha256(l.encode()))
    return pcr

def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    path = argv[1]; art = None; receipt = None
    if '--artifacts' in argv: art = argv[argv.index('--artifacts') + 1]
    if '--receipt' in argv: receipt = argv[argv.index('--receipt') + 1]
    text = open(path, 'rb').read().decode('utf-8', 'replace').replace('\r', '')
    if not text.startswith('AEGIS-ATTEST v0'):
        print('FAIL: not an AEGIS-ATTEST v0 file'); return 2
    measured = {}   # pcr -> [lines]
    pcrs = {}
    events = []
    for l in text.split('\n'):
        m = re.match(r'^measured pcr=(\d+) (.*)$', l)
        if m: measured.setdefault(int(m.group(1)), []).append(m.group(2)); continue
        m = re.match(r'^pcr (\d+) ([0-9a-f]{64})$', l)
        if m: pcrs[int(m.group(1))] = bytes.fromhex(m.group(2)); continue
        if l.startswith('event '): events.append(l)
    ok = True
    for p in sorted(measured):
        exp = replay(measured[p])
        got = pcrs.get(p)
        verdict = 'PASS' if got == exp else 'FAIL'
        ok &= got == exp
        print(f'pcr{p}: replayed {exp.hex()[:32]}.. tpm {got.hex()[:32] if got else None}.. {verdict} ({len(measured[p])} events)')
    # event log must carry the same digests as the measured lines
    for p, lines in measured.items():
        for l in lines:
            d = sha256(l.encode()).hex()
            hit = any((f'pcr={p} ' in e and d in e and l in e) for e in events)
            print(f'eventlog pcr={p} sha256={d[:16]}.. {"PASS" if hit else "MISSING"} :: {l[:60]}')
            ok &= hit
    if 4 in pcrs:
        pcr4_events = [e for e in events if e.startswith('event pcr=4 ')]
        print(f'pcr4 (firmware measurement of BOOTX64.EFI): {pcrs[4].hex()} ; {len(pcr4_events)} event(s) in log')
        for e in pcr4_events: print('   ', e[:200])
    if art:
        for l in measured.get(12, []):
            m = re.match(r'AEGIS-MEASURE v0 artifact=(\S+) bytes=(\d+) sha256=([0-9a-f]{64})', l)
            if not m: continue
            f = os.path.join(art, m.group(1))
            if os.path.exists(f):
                h = hashlib.sha256(open(f, 'rb').read()).hexdigest()
                res = 'PASS' if h == m.group(3) and os.path.getsize(f) == int(m.group(2)) else 'FAIL'
                ok &= res == 'PASS'
                print(f'artifact {m.group(1)}: local sha256 {h[:16]}.. {res}')
    if receipt:
        rt = open(receipt, 'rb').read().decode().replace('\r', '')
        chain = re.search(r'^chain ([0-9a-f]{64})$', rt, re.M)
        cis = re.search(r'^cis-digest ([0-9a-f]{16})$', rt, re.M)
        rl = measured.get(13, [])
        hit = any(chain and chain.group(1) in l and cis and cis.group(1) in l for l in rl)
        ok &= hit
        print(f'receipt chain {chain.group(1)[:16] if chain else None}.. bound in PCR13 line: {"PASS" if hit else "FAIL"}')
    print('ATTEST VERIFY', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Quote verification (AEGIS-ATTEST v0 `quote-*` lines), added once the unikernel
# signs PCRs 4,12,13 with a TPM-resident ECC P-256 attestation key:
#   quote-pcrs 4,12,13
#   quote-qualifying <hex32>      (= SHA-256 of RECEIPT.TXT bytes)
#   quote-pub-x <hex32>  quote-pub-y <hex32>   (TPMT_PUBLIC unique point)
#   quote-attest <hex>            (raw TPMS_ATTEST)
#   quote-sig-r <hex32> quote-sig-s <hex32>    (ECDSA/SHA-256)
# Checks: TPMS_ATTEST magic/type, extraData == qualifying, pcrDigest ==
# SHA-256(PCR4||PCR12||PCR13) from the `pcr` lines, and the ECDSA signature
# over SHA-256(attest) with OpenSSL (DER SPKI/ECDSA-Sig built here, stdlib only).
import subprocess, tempfile

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

def verify_quote(text, pcrs, receipt_path):
    kv = dict(re.findall(r'^(quote-[a-z-]+) (\S+)$', text, re.M))
    if 'quote-attest' not in kv:
        print('quote: none in file'); return None
    ok = True
    attest = bytes.fromhex(kv['quote-attest'])
    # TPMS_ATTEST: magic(4) type(2) TPM2B_NAME TPM2B_DATA clockInfo(17) fw(8) TPML_PCR_SELECTION TPM2B_DIGEST
    magic = attest[:4].hex(); typ = attest[4:6].hex()
    ok &= magic == 'ff544347' and typ == '8018'
    print(f'quote attest magic={magic} type={typ} {"PASS" if magic=="ff544347" and typ=="8018" else "FAIL"}')
    o = 6; n = int.from_bytes(attest[o:o+2], 'big'); o += 2 + n
    n = int.from_bytes(attest[o:o+2], 'big'); extra = attest[o+2:o+2+n]; o += 2 + n
    o += 17 + 8
    cnt = int.from_bytes(attest[o:o+4], 'big'); o += 4
    sel_pcrs = []
    for _ in range(cnt):
        alg = int.from_bytes(attest[o:o+2], 'big'); sz = attest[o+2]; sel = attest[o+3:o+3+sz]; o += 3 + sz
        for i, b in enumerate(sel):
            for bit in range(8):
                if b >> bit & 1: sel_pcrs.append(8*i + bit)
    n = int.from_bytes(attest[o:o+2], 'big'); pcr_digest = attest[o+2:o+2+n]
    qual = bytes.fromhex(kv.get('quote-qualifying', ''))
    r1 = extra == qual; ok &= r1
    print(f'quote extraData == qualifying ({qual.hex()[:16]}..): {"PASS" if r1 else "FAIL"}')
    if receipt_path and os.path.exists(receipt_path):
        rq = sha256(open(receipt_path, 'rb').read())
        r2 = rq == qual; ok &= r2
        print(f'quote qualifying == SHA-256(RECEIPT.TXT): {"PASS" if r2 else "FAIL"}')
    comp = sha256(b''.join(pcrs[p] for p in sel_pcrs if p in pcrs))
    r3 = comp == pcr_digest and all(p in pcrs for p in sel_pcrs); ok &= r3
    print(f'quote pcrDigest over PCRs {sel_pcrs} == SHA-256(PCR values read back): {"PASS" if r3 else "FAIL"}')
    x = bytes.fromhex(kv['quote-pub-x']); y = bytes.fromhex(kv['quote-pub-y'])
    r = bytes.fromhex(kv['quote-sig-r']); s_ = bytes.fromhex(kv['quote-sig-s'])
    sig = _der_int(r) + _der_int(s_); sig = b'\x30' + _der_len(len(sig)) + sig
    with tempfile.TemporaryDirectory() as td:
        open(f'{td}/pub.der', 'wb').write(p256_spki(x, y)); open(f'{td}/sig.der', 'wb').write(sig); open(f'{td}/attest.bin', 'wb').write(attest)
        subprocess.run(['openssl', 'pkey', '-pubin', '-inform', 'DER', '-in', f'{td}/pub.der', '-out', f'{td}/pub.pem'], check=True, capture_output=True)
        res = subprocess.run(['openssl', 'dgst', '-sha256', '-verify', f'{td}/pub.pem', '-signature', f'{td}/sig.der', f'{td}/attest.bin'], capture_output=True, text=True)
        r4 = 'Verified OK' in res.stdout; ok &= r4
        print(f'quote ECDSA-P256/SHA-256 signature over TPMS_ATTEST (openssl): {res.stdout.strip() or res.stderr.strip()} {"PASS" if r4 else "FAIL"}')
        # negative control: flip one byte of attest
        tam = bytearray(attest); tam[-1] ^= 1; open(f'{td}/tam.bin', 'wb').write(bytes(tam))
        res2 = subprocess.run(['openssl', 'dgst', '-sha256', '-verify', f'{td}/pub.pem', '-signature', f'{td}/sig.der', f'{td}/tam.bin'], capture_output=True, text=True)
        r5 = 'Verified OK' not in res2.stdout; ok &= r5
        print(f'quote tampered attest rejected: {"PASS" if r5 else "FAIL"}')
    print('quote pub-x', x.hex()[:16] + '..', 'clockInfo/firmwareVersion present; signer qualifiedName len', int.from_bytes(attest[6:8], 'big'))
    return ok

_orig_main = main
def main(argv):
    rc = _orig_main(argv)
    try:
        text = open(argv[1], 'rb').read().decode('utf-8', 'replace').replace('\r', '')
        pcrs = {int(m.group(1)): bytes.fromhex(m.group(2)) for m in re.finditer(r'^pcr (\d+) ([0-9a-f]{64})$', text, re.M)}
        receipt = argv[argv.index('--receipt') + 1] if '--receipt' in argv else None
        q = verify_quote(text, pcrs, receipt)
        if q is not None:
            print('QUOTE VERIFY', 'PASS' if q else 'FAIL')
            if not q: rc = 1
    except Exception as e:
        print('QUOTE VERIFY ERROR', e); rc = 1
    return rc

if __name__ == '__main__':
    sys.exit(main(sys.argv))
