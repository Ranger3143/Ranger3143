#!/bin/bash
# SAFE-01 side check: do all genuine boots pass the stricter attest_verify form (--receipt, --artifacts)?
S=/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad
EV=/home/user/Ranger3143/labs/logs/opmodel/final_step12000
AV=/home/user/Ranger3143/labs/tools/attest_verify.py
for d in $EV/qemu_*; do
  [ -f $d/ATTEST.TXT ] || continue
  python3 -I $AV $d/ATTEST.TXT $d/RECEIPT.TXT >/dev/null 2>&1; f1=$?
  python3 -I $AV $d/ATTEST.TXT --receipt $d/RECEIPT.TXT --artifacts $S/opmodel/exports/final_step12000/artifacts >/dev/null 2>&1; f2=$?
  echo "$(basename $d) F1 exit $f1  F2 exit $f2"
done
