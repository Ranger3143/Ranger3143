#!/bin/bash
# Start a fresh swtpm (TPM 2.0) on TCP 2321/2322, run tpm2min-cli against it,
# then shut swtpm down.  All artefacts land in ./out.
set -uo pipefail
LAB="$(cd "$(dirname "$0")" && pwd)"
STATE="$LAB/swtpm-state"; OUT="$LAB/out"
PORT="${PORT:-2321}"; CTRL="${CTRL:-2322}"
rm -rf "$STATE" "$OUT"; mkdir -p "$STATE" "$OUT"

swtpm socket --tpm2 --tpmstate "dir=$STATE" \
  --server "type=tcp,port=$PORT" --ctrl "type=tcp,port=$CTRL" \
  --flags not-need-init,startup-clear \
  --log "file=$OUT/swtpm.log,level=20" &
SWTPM_PID=$!
trap 'kill $SWTPM_PID 2>/dev/null; wait $SWTPM_PID 2>/dev/null' EXIT

# wait for the control port to accept connections (does not touch the data channel)
for _ in $(seq 1 100); do
  python3 -c "import socket,sys; s=socket.socket(); s.settimeout(0.2); s.connect(('127.0.0.1',$CTRL)); s.close()" 2>/dev/null && break
  sleep 0.1
done

echo "swtpm $(swtpm --version | head -1) pid=$SWTPM_PID data=$PORT ctrl=$CTRL"
( cd "$LAB" && cargo run --quiet --release -p tpm2min-cli -- --port "$PORT" --out "$OUT" --verify-py "$LAB/verify_quote.py" "$@" ) 2>&1 | tee "$OUT/cli_output.txt"
RC=${PIPESTATUS[0]}
echo "tpm2min-cli exit code: $RC"
exit $RC
