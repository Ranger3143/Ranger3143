#!/bin/bash
# SAFE-01 S2: re-check the software-key forgeries kept in h3_mutants.tar.gz
S=/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad
AV=/home/user/Ranger3143/labs/tools/attest_verify.py
W=$S/verify09/s2; mkdir -p $W
tar xzf /home/user/Ranger3143/labs/logs/safe/SAFE-01/h3_mutants.tar.gz -C $W forge_pcr13-line-edit forge_receipt-chain-edit
for d in forge_pcr13-line-edit forge_receipt-chain-edit; do
  python3 -I $AV $W/$d/ATTEST.TXT $W/$d/RECEIPT.TXT >/dev/null; echo "$d F1(finalize.sh form) exit $?"
  python3 -I $AV $W/$d/ATTEST.TXT --receipt $W/$d/RECEIPT.TXT --artifacts $S/opmodel/exports/final_step12000/artifacts >/dev/null; echo "$d F2(--receipt) exit $?"
  /home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/cis_witness verify $S/opmodel/exports/final_step12000/artifacts/{MODEL.SAF,EMBED.BIN,VOCAB.BIN} $W/$d/RECEIPT.TXT | tail -1
done
