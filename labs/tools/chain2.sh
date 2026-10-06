#!/bin/bash
# wait for the timed-decode job (CPU quiet) before building/booting
until [ "$(grep -c CIS_DECODE_TIMED_SUMMARY /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/cis_decode_timed_threads_run1.log 2>/dev/null)" -ge 3 ] || grep -q "^error" /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/cis_decode_timed_threads_run1.log 2>/dev/null; do sleep 5; done
echo "=== timed decode done; building unikernel with quote ==="
cd /home/user/aefinity-ai/alice-aegis/aegis-uefi && ./build_hardfloat.sh --qemu-test 2>&1 | grep -E "^error|-->|Built|AVX2 sanity|OK:|FATAL" | grep -v "warning" | head -30
[ -f target/x86_64-uefi-hardfloat/release/aegis-uefi.efi ] || { echo BUILD_FAILED; exit 1; }
sha256sum target/x86_64-uefi-hardfloat/release/aegis-uefi.efi
cp target/x86_64-uefi-hardfloat/release/aegis-uefi.efi /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/aegis-uefi-attest-qemutest.efi
cd /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu
echo "=== QEMU: TPM + RECEIPT (verify, attested, quote) ==="
./boot.sh /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/aegis-uefi-attest-qemutest.efi /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/assets_m7_receipt ./run_attest_verify2 --tpm 2>&1 | tail -30
echo "=== QEMU: TPM + MINT (mint, attested, quote) ==="
./boot.sh /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/aegis-uefi-attest-qemutest.efi /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/qemu/assets_m7_mint ./run_attest_mint2 --tpm 2>&1 | tail -30
A=/home/user/aefinity-ai/alice-aegis/model-lab/tinybit/m7_final_gate_work/artifacts
for r in run_attest_verify2 run_attest_mint2; do echo "=== attest_verify $r ==="; python3 -I /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/attest_verify.py $r/esp/ATTEST.TXT --artifacts $A --receipt $r/esp/RECEIPT.TXT 2>&1 | tee /tmp/claude-0/-home-user-Ranger3143/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/labs/attest_verify_$r.log; done
echo CHAIN2_DONE
