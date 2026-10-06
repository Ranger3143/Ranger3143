#!/bin/bash
set -o pipefail
cd /home/user/aefinity-ai/alice-aegis/aegis-uefi && ./build_hardfloat.sh --qemu-test 2>&1 | grep -E "^error|-->|Built|AVX2 sanity|OK:|FATAL" | head -30
[ -f target/x86_64-uefi-hardfloat/release/aegis-uefi.efi ] || { echo BUILD_FAILED; exit 1; }
sha256sum target/x86_64-uefi-hardfloat/release/aegis-uefi.efi
cp target/x86_64-uefi-hardfloat/release/aegis-uefi.efi /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/aegis-uefi-attest-qemutest.efi
echo "=== membw 1T ==="; cd /home/user/aefinity-ai/alice-aegis/aegis-linux && ./target/release/examples/membw 1024 5 1 2>&1 | grep -v "^  " > /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/membw_1t_run2.log; grep -v "^#" /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/membw_1t_run2.log | head -30
echo "=== membw 4T ==="; ./target/release/examples/membw 1024 5 4 2>&1 | grep -v "^  " > /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/membw_4t_run2.log; grep -v "^#" /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/membw_4t_run2.log | head -30
cd /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu
echo "=== QEMU: TPM + RECEIPT (verify, attested) ==="
./boot.sh /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/aegis-uefi-attest-qemutest.efi /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/assets_m7_receipt ./run_attest_verify --tpm 2>&1 | tail -45
echo "=== QEMU: TPM + MINT (mint, attested) ==="
./boot.sh /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/aegis-uefi-attest-qemutest.efi /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/assets_m7_mint ./run_attest_mint --tpm 2>&1 | tail -45
echo CHAIN1_DONE
