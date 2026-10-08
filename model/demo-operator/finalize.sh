#!/bin/bash
# Final-checkpoint pipeline for the demo operator model:
#   export -> repack -> engine round-trip gate -> demo decodes -> QEMU boots
#   (self / receipt / calc / lookup / abstain / everyday prompts through the
#   firmware gateway image) -> host verification of every receipt and quote
#   -> evidence copied into the Ranger3143 repo. Rule A: no timing recorded.
# usage: finalize.sh <ckpt> <tag>     (tag e.g. final_step12000)
set -u
CK=$1; TAG=$2
O=/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad/opmodel
S=/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad
R=/home/user/Ranger3143
EFI=$S/qemu/aegis-uefi-gateway-qemutest.efi
W=/home/user/aefinity-ai/alice-aegis/aegis-linux/target/release/examples/cis_witness
AV=$R/labs/tools/attest_verify.py
OUT=$R/labs/logs/opmodel/$TAG; mkdir -p $OUT $R/labs/screenshots/dashboard
LOG=$OUT/FINALIZE.log; : > $LOG
log(){ echo "$*" | tee -a $LOG; }

log "== export + gate: $CK"
cp $CK $O/checkpoints/$TAG.pt
(cd $O && OMP_NUM_THREADS=1 python3 export_gate.py --ckpt checkpoints/$TAG.pt --name $TAG) > $OUT/export_gate.out 2>&1
grep -E "^\[gate\]|^\[a\]|^\[b\]|^\[c\]|>>>|^\[d\]" $OUT/export_gate.out | cut -c1-240 | tee -a $LOG
cp $O/exports/$TAG/{GATE.log,SUMMARY.json,heldout.txt} $OUT/
A=$O/exports/$TAG/artifacts
mkdir -p $R/model/demo-operator/artifacts_$TAG && cp $A/VOCAB.BIN $R/model/demo-operator/artifacts_$TAG/ && sha256sum $A/MODEL.SAF $A/EMBED.BIN $A/VOCAB.BIN > $R/model/demo-operator/artifacts_$TAG/SHA256SUMS && cp $O/exports/$TAG/hf/config.json $R/model/demo-operator/artifacts_$TAG/ 2>/dev/null

log "== behaviour probe"
(cd $O && OMP_NUM_THREADS=1 python3 eval_ops.py --ckpt checkpoints/$TAG.pt --tokenizer tokenizer_op12k.json --show 3 --json $OUT/eval_$TAG.json) 2>&1 | grep -v Warning > $OUT/eval_$TAG.txt
tail -8 $OUT/eval_$TAG.txt | tee -a $LOG

log "== LAB-07 tool-call suites on the final artifacts (same items, same harness, same binary)"
AT=/home/user/aefinity-ai/alice-aegis/demo/agent-trace/eval/run_suite.sh
for v in T1:$R/labs/logs/toolcall_2b/suite.tsv T0:$O/suite_t0.tsv ext:$R/labs/logs/toolcall_2b_ext/ext_suite.tsv ext_T2:$R/labs/logs/toolcall_2b_ext/ext_suite_t2.tsv; do
  tag=${v%%:*}; suite=${v#*:}; SO=$O/suite_${TAG}_$tag; rm -rf $SO
  AEGIS_ARTIFACTS=$A nice -n 5 $AT $suite $SO > $SO.log 2>&1
  python3 -I $R/labs/logs/toolcall_2b/score.py $SO/summary.tsv > $SO/SCORE.txt
  python3 -I $O/suite_compare.py $suite $SO > $SO/COMPARE.txt
  D=$OUT/suite_$tag; mkdir -p $D; cp -r $SO/{summary.tsv,SCORE.txt,COMPARE.txt,RUN.txt,timing.tsv,receipts,prompts} $D/; cp $SO.log $D/run_suite.log
  log "-- suite $tag"; grep -E "^\[|correct-arg|no-tool|OVERALL|RED FLAGS|^  - " $SO/SCORE.txt | cut -c1-110 | tee -a $LOG; tail -1 $SO/COMPARE.txt | tee -a $LOG
done

log "== QEMU boots through the gateway image (swtpm)"
for k in self receipt calc calc_words lookup abstain everyday unknown_tool; do
  D=$O/exports/$TAG/assets/$k; [ -d $D ] || continue
  (cd $S/qemu && ./boot_shot.sh $EFI $D ./shot_${TAG}_$k "14 18 22 26 30 34" --tpm > shot_${TAG}_$k.log 2>&1)
  RUN=$S/qemu/shot_${TAG}_$k; E=$OUT/qemu_$k; mkdir -p $E
  cp $RUN/esp/BOOTLOG.TXT $RUN/esp/ATTEST.TXT $RUN/RESULT.txt $E/ 2>/dev/null
  for f in RECEIPT.TXT RECEIPT2.TXT; do mcopy -n -i $RUN/disk.img ::/$f $E/$f 2>/dev/null; done
  cp $RUN/tpm/swtpm.log $E/ 2>/dev/null
  LASTPNG=$(ls $RUN/shots/*.png 2>/dev/null | tail -1); [ -n "$LASTPNG" ] && cp $LASTPNG $R/labs/screenshots/dashboard/20_opmodel_${TAG}_$k.png
  log "-- $k: $(grep -oE 'qemu_exit=[0-9]+' $RUN/RESULT.txt 2>/dev/null)"
  grep -E "STAGE (M|T|M2)" $E/BOOTLOG.TXT 2>/dev/null | cut -c1-140 | tee -a $LOG
  for f in RECEIPT.TXT RECEIPT2.TXT; do
    [ -f $E/$f ] || continue
    V=$($W verify $A/MODEL.SAF $A/EMBED.BIN $A/VOCAB.BIN $E/$f 2>&1 | tail -1 | cut -c1-70)
    log "   $f: $(grep -E '^(maxtok|gen-toks|cis-digest)' $E/$f | tr '\n' ' ') -> $V"
    python3 - "$E/$f" <<'PY' | tee -a $LOG
import sys,binascii
h=[l.split()[1] for l in open(sys.argv[1]) if l.startswith('prompt-hex')][0]
ids=[l.split(' ',1)[1] for l in open(sys.argv[1]) if l.startswith('token-ids')][0]
print('      prompt:', repr(binascii.unhexlify(h).decode('ascii','replace'))[:160])
PY
  done
  [ -f $E/ATTEST.TXT ] && log "   attest: $(python3 -I $AV $E/ATTEST.TXT $E/RECEIPT.TXT 2>&1 | grep -E 'VERIFY (PASS|FAIL)' | tr '\n' ' ')"
done

log "== decoded demo answers (engine, Linux cis_decode; see export_gate.out [d] lines)"
grep -E "^\[d\]" $OUT/export_gate.out | cut -c1-300 | tee -a $LOG
log "== done: $OUT"
