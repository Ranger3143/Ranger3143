#!/bin/bash
# QEMU/OVMF boot harness for the A.L.I.C.E. unikernel (correctness only — Rule A).
# Mirrors xtask boot-test (q35, accel=tcg, -cpu max, -smp 4, -m 2048, isa-debug-exit,
# success = exit 33) and adds an optional software TPM 2.0 (swtpm) on tpm-tis.
#
# usage: boot.sh <efi> <asset_dir> <out_dir> [--tpm] [--timeout SECS] [--extra "qemu args"]
set -u
EFI=$1; ASSETS=$2; OUT=$3; shift 3
TPM=0; TIMEOUT=1800; EXTRA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --tpm) TPM=1;;
    --timeout) TIMEOUT=$2; shift;;
    --extra) EXTRA=$2; shift;;
  esac; shift
done
OVMF_CODE=/usr/share/OVMF/OVMF_CODE_4M.fd
OVMF_VARS=/usr/share/OVMF/OVMF_VARS_4M.fd
rm -rf "$OUT"; mkdir -p "$OUT/esp"
# Real FAT32 image via mtools (QEMU's fat:rw: vvfat driver loses guest-written
# files — observed 2026-10-06: BOOTLOG/ATTEST/RECEIPT never reached the host dir).
IMG="$OUT/disk.img"; SIZE_MB=${IMG_MB:-64}
truncate -s "${SIZE_MB}M" "$IMG"; mformat -i "$IMG" -F ::; mmd -i "$IMG" ::/EFI ::/EFI/BOOT
mcopy -i "$IMG" "$EFI" ::/EFI/BOOT/BOOTX64.EFI
for f in MODEL.SAF EMBED.BIN VOCAB.BIN; do mcopy -i "$IMG" "$ASSETS/$f" ::/$f; done
for f in RECEIPT.TXT JOB.TXT MINT.TXT; do [ -f "$ASSETS/$f" ] && mcopy -i "$IMG" "$ASSETS/$f" ::/$f; done
cp "$OVMF_VARS" "$OUT/OVMF_VARS_4M.fd"
TPMARGS=""
if [ "$TPM" = 1 ]; then
  mkdir -p "$OUT/tpm"
  swtpm socket --tpm2 --tpmstate dir="$OUT/tpm" --ctrl type=unixio,path="$OUT/tpm/sock" \
      --log file="$OUT/tpm/swtpm.log",level=5 &
  SWTPM_PID=$!
  sleep 1
  TPMARGS="-chardev socket,id=chrtpm,path=$OUT/tpm/sock -tpmdev emulator,id=tpm0,chardev=chrtpm -device tpm-tis,tpmdev=tpm0"
fi
START=$(date +%s)
timeout "$TIMEOUT" qemu-system-x86_64 -machine q35,accel=tcg -cpu max -smp 4 -m 2048 \
  -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
  -drive if=pflash,format=raw,file="$OUT/OVMF_VARS_4M.fd" \
  -drive format=raw,file="$IMG" \
  -device isa-debug-exit,iobase=0xf4,iosize=0x04 \
  -serial file:"$OUT/serial.log" -display none -no-reboot $TPMARGS $EXTRA
RC=$?
END=$(date +%s)
[ "$TPM" = 1 ] && kill $SWTPM_PID 2>/dev/null
echo "qemu_exit=$RC wall_s=$((END-START)) (33 = unikernel success signal; Rule A: no perf meaning)" | tee "$OUT/RESULT.txt"
for f in BOOTLOG.TXT ATTEST.TXT RECEIPT.TXT; do mcopy -n -i "$IMG" ::/$f "$OUT/esp/$f" 2>/dev/null; done
[ -f "$OUT/esp/BOOTLOG.TXT" ] && { echo "--- BOOTLOG.TXT (tail) ---"; tr -d '\r' < "$OUT/esp/BOOTLOG.TXT" | tail -40; }
exit $RC
