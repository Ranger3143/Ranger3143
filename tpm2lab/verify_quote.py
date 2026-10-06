#!/usr/bin/env python3
"""Independent TPM2 quote verifier (no tpm2min code, no tpm2-tools).

usage: verify_quote.py pub.pem attest.bin sig_rs.hex qualifying.hex pcr4.hex pcr12.hex name.hex

Parses TPMS_ATTEST by hand (TPM 2.0 Part 2 s10.12.8), recomputes the PCR
composite, and verifies the ECDSA-P256/SHA-256 signature with python
`cryptography` over SHA256(TPMS_ATTEST).  Exit code 0 iff every check passes.
"""
import hashlib, struct, sys

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.exceptions import InvalidSignature

TPM_GENERATED_VALUE = 0xFF544347
TPM_ST_ATTEST_QUOTE = 0x8018
TPM_ALG_SHA256 = 0x000B
TPM_RH_OWNER = 0x40000001


def rd(buf, off, fmt):
    v = struct.unpack_from(">" + fmt, buf, off)
    return v if len(v) > 1 else v[0], off + struct.calcsize(">" + fmt)


def rd2b(buf, off):
    n, off = rd(buf, off, "H")
    return buf[off:off + n], off + n


def parse_attest(a):
    off = 0
    magic, off = rd(a, off, "I")
    typ, off = rd(a, off, "H")
    qsigner, off = rd2b(a, off)
    extra, off = rd2b(a, off)
    clock, reset, restart, safe = struct.unpack_from(">IIIB", a, off)[0:4] if False else (None,)*4
    clock, off = rd(a, off, "Q")
    reset, off = rd(a, off, "I")
    restart, off = rd(a, off, "I")
    safe, off = rd(a, off, "B")
    fw, off = rd(a, off, "Q")
    count, off = rd(a, off, "I")
    sels = []
    for _ in range(count):
        alg, off = rd(a, off, "H")
        sz, off = rd(a, off, "B")
        bitmap = a[off:off + sz]; off += sz
        pcrs = [i for i in range(sz * 8) if bitmap[i // 8] & (1 << (i % 8))]
        sels.append((alg, pcrs))
    pcr_digest, off = rd2b(a, off)
    assert off == len(a), "trailing bytes in TPMS_ATTEST"
    return dict(magic=magic, type=typ, qualified_signer=qsigner, extra=extra, clock=clock,
                reset=reset, restart=restart, safe=safe, fw=fw, sels=sels, pcr_digest=pcr_digest)


def main(argv):
    pub_pem, attest_f, sig_f, q_f, p4_f, p12_f, name_f = argv[1:8]
    attest = open(attest_f, "rb").read()
    rs = bytes.fromhex(open(sig_f).read().strip())
    qual = bytes.fromhex(open(q_f).read().strip())
    pcr4 = bytes.fromhex(open(p4_f).read().strip())
    pcr12 = bytes.fromhex(open(p12_f).read().strip())
    name = bytes.fromhex(open(name_f).read().strip())
    pub = serialization.load_pem_public_key(open(pub_pem, "rb").read())

    a = parse_attest(attest)
    results = []
    results.append(("magic == 0xff544347", a["magic"] == TPM_GENERATED_VALUE))
    results.append(("type == TPM_ST_ATTEST_QUOTE", a["type"] == TPM_ST_ATTEST_QUOTE))
    results.append(("extraData == qualifyingData", a["extra"] == qual))
    results.append(("pcrSelect == [(sha256, [4, 12])]", a["sels"] == [(TPM_ALG_SHA256, [4, 12])]))
    comp = hashlib.sha256(pcr4 + pcr12).digest()
    results.append(("pcrDigest == sha256(PCR4||PCR12)", a["pcr_digest"] == comp))
    qn = b"\x00\x0b" + hashlib.sha256(struct.pack(">I", TPM_RH_OWNER) + name).digest()
    results.append(("qualifiedSigner == 000b||sha256(TPM_RH_OWNER||name)", a["qualified_signer"] == qn))
    r, s = int.from_bytes(rs[:32], "big"), int.from_bytes(rs[32:], "big")
    der = encode_dss_signature(r, s)
    try:
        pub.verify(der, attest, ec.ECDSA(hashes.SHA256()))
        sig_ok = True
    except InvalidSignature:
        sig_ok = False
    results.append(("ECDSA-P256/SHA256 signature over TPMS_ATTEST verifies", sig_ok))
    # negative control
    try:
        pub.verify(der, attest[:-1] + bytes([attest[-1] ^ 1]), ec.ECDSA(hashes.SHA256()))
        neg_ok = False
    except InvalidSignature:
        neg_ok = True
    results.append(("tampered attest is rejected", neg_ok))

    print("python verifier: curve=%s key_size=%d" % (pub.curve.name, pub.key_size))
    print("  clock=%d reset=%d restart=%d safe=%d fw=0x%016x" % (a["clock"], a["reset"], a["restart"], a["safe"], a["fw"]))
    ok = True
    for n, p in results:
        print("  [%s] %s" % ("PASS" if p else "FAIL", n))
        ok &= p
    print("python verifier overall: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
