#!/bin/bash
# boot.sh + QMP screendumps at the given seconds after launch (TCG; correctness/appearance only).
# usage: boot_shot.sh <efi> <asset_dir> <out_dir> "<secs list>" [--tpm]
set -u
EFI=$1; ASSETS=$2; OUT=$3; SECS=$4; shift 4
TPM=0; for a in "$@"; do [ "$a" = "--tpm" ] && TPM=1; done
HERE=$(cd "$(dirname "$0")" && pwd)
OVMF_CODE=/usr/share/OVMF/OVMF_CODE_4M.fd; OVMF_VARS=/usr/share/OVMF/OVMF_VARS_4M.fd
rm -rf "$OUT"; mkdir -p "$OUT/esp" "$OUT/shots"
IMG="$OUT/disk.img"; truncate -s 64M "$IMG"; mformat -i "$IMG" -F ::; mmd -i "$IMG" ::/EFI ::/EFI/BOOT
mcopy -i "$IMG" "$EFI" ::/EFI/BOOT/BOOTX64.EFI
for f in MODEL.SAF EMBED.BIN VOCAB.BIN; do mcopy -i "$IMG" "$ASSETS/$f" ::/$f; done
for f in RECEIPT.TXT JOB.TXT MINT.TXT TABLE.TSV; do [ -f "$ASSETS/$f" ] && mcopy -i "$IMG" "$ASSETS/$f" ::/$f; done
cp "$OVMF_VARS" "$OUT/OVMF_VARS_4M.fd"
TPMARGS=""
if [ "$TPM" = 1 ]; then mkdir -p "$OUT/tpm"; swtpm socket --tpm2 --tpmstate dir="$OUT/tpm" --ctrl type=unixio,path="$OUT/tpm/sock" --log file="$OUT/tpm/swtpm.log",level=1 & SWTPM_PID=$!; sleep 1
  TPMARGS="-chardev socket,id=chrtpm,path=$OUT/tpm/sock -tpmdev emulator,id=tpm0,chardev=chrtpm -device tpm-tis,tpmdev=tpm0"; fi
QMP="$OUT/qmp.sock"
qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 4 -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" -drive if=pflash,format=raw,file="$OUT/OVMF_VARS_4M.fd" \
  -drive format=raw,file="$IMG" -device isa-debug-exit,iobase=0xf4,iosize=0x04 \
  -serial file:"$OUT/serial.log" -display none -vga std -no-reboot -qmp unix:"$QMP",server,nowait $TPMARGS &
QPID=$!
python3 - "$QMP" "$OUT/shots" "$SECS" << 'PY'
import json, socket, sys, time, os
sock_path, outdir, secs = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split()]
t0 = time.time()
def cmd(s, obj):
    s.sendall((json.dumps(obj) + '\n').encode()); time.sleep(0.3)
    try: return s.recv(65536)
    except Exception: return b''
for sec in secs:
    while time.time() - t0 < sec: time.sleep(0.2)
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.settimeout(5); s.connect(sock_path)
        s.recv(65536); cmd(s, {"execute": "qmp_capabilities"})
        fn = os.path.join(outdir, f"shot_{sec:03d}s.ppm"); r = cmd(s, {"execute": "screendump", "arguments": {"filename": fn}})
        print(f"screendump at {sec}s -> {fn} {r[:80]!r}"); s.close()
    except Exception as e:
        print(f"screendump at {sec}s failed: {e}")
PY
wait $QPID; RC=$?
[ "$TPM" = 1 ] && kill $SWTPM_PID 2>/dev/null
echo "qemu_exit=$RC (33 = success; appearance/correctness only)" | tee "$OUT/RESULT.txt"
for f in BOOTLOG.TXT ATTEST.TXT RECEIPT.TXT; do mcopy -n -i "$IMG" ::/$f "$OUT/esp/$f" 2>/dev/null; done
for p in "$OUT"/shots/*.ppm; do [ -f "$p" ] && python3 -I "$HERE/ppm2png.py" "$p" "${p%.ppm}.png"; done
ls -la "$OUT/shots" 2>/dev/null
