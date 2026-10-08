#!/bin/bash
# Derive the AEGIS-ATTEST attestation key from a swtpm state directory, WITHOUT using the guest's ATTEST.TXT.
#
# The unikernel signs its quote with the primary key
#     TPM2_CreatePrimary(owner, ECC P-256, ECDSA/SHA-256, restricted signing,
#                        fixedTPM|fixedParent|sensitiveDataOrigin|userWithAuth, empty unique)
# (aegis-uefi/src/attest.rs -> tpm2min::cmd::create_primary_ecc_p256). A primary key is a pure function of the
# TPM's owner seed and the template, so the host - which owns the swtpm state directory the VM booted with -
# can recompute the same public key later. That gives `attest_verify.py --expect-pubkey` a pin that the guest
# (and anyone who can edit ATTEST.TXT) cannot influence. Output: 128 lowercase hex chars, x||y of the key.
#
# usage: ak_from_swtpm.sh <swtpm-state-dir>        (the dir holding tpm2-00.permall; it is COPIED, never modified)
# needs: swtpm, tpm2-tools (tpm2_startup, tpm2_createprimary, tpm2_readpublic), python3
# exit 0 + key on stdout; non-zero + message on stderr otherwise.
set -u
ST=${1:-}
[ -n "$ST" ] && [ -f "$ST/tpm2-00.permall" ] || { echo "ak_from_swtpm: no tpm2-00.permall in '$ST'" >&2; exit 2; }
for t in swtpm tpm2_startup tpm2_createprimary tpm2_readpublic python3; do
  command -v $t >/dev/null || { echo "ak_from_swtpm: $t not installed" >&2; exit 3; }
done
W=$(mktemp -d "${AK_WORK:-${TMPDIR:-/tmp}}/ak_from_swtpm.XXXXXX") || exit 3
SP=
cleanup(){ [ -n "$SP" ] && kill $SP 2>/dev/null; wait $SP 2>/dev/null; rm -rf "$W"; }
trap cleanup EXIT
mkdir "$W/st" && cp "$ST/tpm2-00.permall" "$W/st/" || exit 3
# tcti-swtpm expects the control port to be the data port + 1: find a free pair
P1=$(python3 -I -c '
import socket, random
while True:
    p = random.randrange(20000, 60000); ok = True
    for q in (p, p + 1):
        s = socket.socket()
        try: s.bind(("127.0.0.1", q))
        except OSError: ok = False
        s.close()
    if ok: print(p); break')
P2=$((P1 + 1))
swtpm socket --tpm2 --tpmstate dir="$W/st" --server type=tcp,port=$P1,bindaddr=127.0.0.1 \
  --ctrl type=tcp,port=$P2,bindaddr=127.0.0.1 --flags not-need-init --log file="$W/swtpm.log",level=1 >/dev/null 2>&1 &
SP=$!
export TPM2TOOLS_TCTI="swtpm:host=127.0.0.1,port=$P1"
ok=0
for i in 1 2 3 4 5 6 7 8 9 10; do tpm2_startup -c >/dev/null 2>&1 && { ok=1; break; }; sleep 0.3; done
[ $ok = 1 ] || { echo "ak_from_swtpm: swtpm did not answer TPM2_Startup" >&2; exit 4; }
( cd "$W" && tpm2_createprimary -C o -g sha256 -G ecc256:ecdsa-sha256:null \
    -a 'fixedtpm|fixedparent|sensitivedataorigin|userwithauth|restricted|sign' -c prim.ctx >/dev/null 2>"$W/err" \
  && tpm2_readpublic -c prim.ctx -o pub.bin >/dev/null 2>>"$W/err" ) || { echo "ak_from_swtpm: tpm2-tools failed: $(tail -2 "$W/err" | tr '\n' ' ')" >&2; exit 5; }
# pub.bin = TPM2B_PUBLIC (u16 size) + TPMT_PUBLIC; the unique point is the last 2 x (u16 0x0020 + 32 bytes)
python3 -I - "$W/pub.bin" <<'PY'
import sys
b = open(sys.argv[1], 'rb').read()
n = int.from_bytes(b[:2], 'big'); t = b[2:2 + n]
assert len(t) == n and t[:2] == b'\x00\x23' and t[-68:-66] == b'\x00\x20' and t[-34:-32] == b'\x00\x20', 'unexpected TPMT_PUBLIC'
print(t[-66:-34].hex() + t[-32:].hex())
PY
