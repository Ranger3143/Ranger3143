"""Independent attestation core check for LAB-09 VERIFY-2 (written by the skeptic, no code taken from attest_verify.py).

Pure python: SHA-256 via hashlib, ECDSA-P256 verification with big integers (no openssl), PCR replay, TPMS_ATTEST parse.
core(att_path, rec_path) -> dict of named boolean checks; core_ok = all of the cryptographic-consistency checks.
"""
import hashlib, re

p = 0xffffffff00000001000000000000000000000000ffffffffffffffffffffffff
A = p - 3
B = 0x5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b
GX = 0x6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296
GY = 0x4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5
N = 0xffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551
assert (GY * GY - (GX ** 3 + A * GX + B)) % p == 0


def _add(P, Q):
    if P is None: return Q
    if Q is None: return P
    (x1, y1), (x2, y2) = P, Q
    if x1 == x2:
        if (y1 + y2) % p == 0: return None
        l = (3 * x1 * x1 + A) * pow(2 * y1, -1, p) % p
    else:
        l = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (l * l - x1 - x2) % p
    return (x3, (l * (x1 - x3) - y1) % p)


def _mul(k, P):
    R = None
    while k:
        if k & 1: R = _add(R, P)
        P = _add(P, P); k >>= 1
    return R


def ecdsa_verify(x, y, digest32, r, s):
    if not (0 < r < N and 0 < s < N): return False
    if (y * y - (x ** 3 + A * x + B)) % p != 0: return False
    z = int.from_bytes(digest32, 'big'); w = pow(s, -1, N)
    pt = _add(_mul(z * w % N, (GX, GY)), _mul(r * w % N, (x, y)))
    return pt is not None and pt[0] % N == r


def sha(b): return hashlib.sha256(b).digest()


def parse_attest(t):
    """TPMS_ATTEST of a quote, strict length accounting. Returns dict or raises."""
    o = 0
    def take(n):
        nonlocal o
        if o + n > len(t): raise ValueError('short')
        v = t[o:o + n]; o += n; return v
    d = {}
    d['magic'] = take(4); d['type'] = take(2)
    n = int.from_bytes(take(2), 'big'); d['qsigner'] = take(n)
    n = int.from_bytes(take(2), 'big'); d['extra'] = take(n)
    d['clock'] = take(8); d['reset'] = take(4); d['restart'] = take(4); d['safe'] = take(1); d['fw'] = take(8)
    cnt = int.from_bytes(take(4), 'big'); sel = []
    for _ in range(cnt):
        alg = int.from_bytes(take(2), 'big'); sz = take(1)[0]; bm = take(sz); sel.append((alg, sz, bm))
    n = int.from_bytes(take(2), 'big'); d['pcrdigest'] = take(n)
    d['sel'] = sel; d['trailing'] = len(t) - o
    return d


def read_att(path):
    lines = open(path, 'rb').read().decode('utf-8', 'replace').split('\n')
    return [l.rstrip('\r') for l in lines]


def core(att_path, rec_path):
    res = {}
    try:
        L = read_att(att_path)
        kv = {}
        pcr = {}; events = []; measured = []
        for l in L:
            if l.startswith('pcr ') and re.fullmatch(r'pcr (\d+) ([0-9a-f]{64})', l):
                m = re.fullmatch(r'pcr (\d+) ([0-9a-f]{64})', l); pcr[int(m.group(1))] = bytes.fromhex(m.group(2))
            elif l.startswith('event pcr='):
                m = re.fullmatch(r'event pcr=(\d+) type=(0x[0-9a-f]+) sha256=([0-9a-f]{64}) data=(.*)', l)
                events.append(None if not m else (int(m.group(1)), int(m.group(2), 16), bytes.fromhex(m.group(3)), m.group(4)))
            elif l.startswith('measured pcr='):
                m = re.fullmatch(r'measured pcr=(\d+) (.*)', l)
                measured.append(None if not m else (int(m.group(1)), m.group(2)))
            else:
                m = re.fullmatch(r'(quote-[a-z-]+) (.*)', l)
                if m and m.group(1) not in kv: kv[m.group(1)] = m.group(2)
        hx = lambda k: bytes.fromhex(kv[k])
        att = hx('quote-attest'); q = parse_attest(att)
        res['attest_magic_type'] = q['magic'] == bytes.fromhex('ff544347') and q['type'] == bytes.fromhex('8018') and q['trailing'] == 0
        rec = open(rec_path, 'rb').read()
        res['extra_eq_qualifying_eq_sha_receipt'] = q['extra'] == hx('quote-qualifying') == sha(rec)
        sel = q['sel']
        pl = []
        if len(sel) == 1 and sel[0][0] == 0x000b:
            for i, byte in enumerate(sel[0][2]):
                for b in range(8):
                    if byte >> b & 1: pl.append(i * 8 + b)
        res['sel_is_single_sha256_4_12_13'] = sel and len(sel) == 1 and pl == [4, 12, 13]
        res['pcrdigest_matches_pcr_lines'] = (not events and False) or (q['pcrdigest'] == sha(b''.join(pcr[i] for i in pl)))
        res['quote_pcrs_line'] = kv['quote-pcrs'] == ','.join(str(i) for i in pl)
        x = int(kv['quote-pub-x'], 16); y = int(kv['quote-pub-y'], 16); r = int(kv['quote-sig-r'], 16); s = int(kv['quote-sig-s'], 16)
        res['ecdsa_sig_valid'] = ecdsa_verify(x, y, sha(att), r, s)
        res['sig_s_low'] = s <= N // 2
        pub = hx('quote-public')
        res['quote_public_contains_xy'] = pub.endswith(b'\x00\x20' + x.to_bytes(32, 'big') + b'\x00\x20' + y.to_bytes(32, 'big'))
        name = b'\x00\x0b' + sha(pub)
        qn = b'\x00\x0b' + sha(bytes.fromhex('40000001') + name)
        res['qualified_signer_matches_public'] = q['qsigner'] == qn
        # event replay
        ok_replay = True; ok_digest = True
        for P in (4, 12, 13):
            cur = b'\x00' * 32
            for e in events:
                if e is None: ok_replay = False; continue
                if e[0] == P: cur = sha(cur + e[2])
            if pcr.get(P) != cur: ok_replay = False
        res['pcr_replay_4_12_13'] = ok_replay
        for e in events:
            if e is None: ok_digest = False; continue
            if e[1] in (0xd, 0x80000007) and sha(e[3].encode()) != e[2]: ok_digest = False
            if e[1] == 0x4:
                m = re.fullmatch(r'hex:([0-9a-f]*)', e[3])
                if not m or sha(bytes.fromhex(m.group(1))) != e[2]: ok_digest = False
        res['event_digests_eq_sha_data'] = ok_digest
        ev1213 = [(e[0], e[3]) for e in events if e and e[0] in (12, 13)]
        res['measured_lines_eq_events'] = (None not in measured) and measured == ev1213
        chain = re.search(rb'^chain ([0-9a-f]{64})$', rec, re.M).group(1).decode()
        res['receipt_chain_in_pcr13'] = any(m and m[0] == 13 and ('chain=' + chain) in m[1] for m in measured)
    except Exception as ex:
        res['EXC'] = repr(ex)[:80]
    keys = ['attest_magic_type', 'extra_eq_qualifying_eq_sha_receipt', 'sel_is_single_sha256_4_12_13', 'pcrdigest_matches_pcr_lines', 'quote_pcrs_line',
            'ecdsa_sig_valid', 'quote_public_contains_xy', 'qualified_signer_matches_public', 'pcr_replay_4_12_13', 'event_digests_eq_sha_data',
            'measured_lines_eq_events', 'receipt_chain_in_pcr13']
    res['core_ok'] = 'EXC' not in res and all(bool(res.get(k)) for k in keys)
    res['failed'] = [k for k in keys if not res.get(k)] + (['EXC'] if 'EXC' in res else [])
    return res


def pubkey_of(att_path):
    t = open(att_path, 'rb').read().decode('utf-8', 'replace')
    return re.search(r'^quote-pub-x (\S+)$', t, re.M).group(1) + re.search(r'^quote-pub-y (\S+)$', t, re.M).group(1)


if __name__ == '__main__':
    import sys
    r = core(sys.argv[1], sys.argv[2]); print(r)
