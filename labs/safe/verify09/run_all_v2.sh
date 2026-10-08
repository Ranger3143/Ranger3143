#!/bin/bash
# LAB-09 VERIFY-2 (part 2 skeptic pass) runner. Read-only with respect to the experiments' logs; scratch goes to the scratchpad.
# Rule A: nothing here records a duration. Every script runs as python3 -I, nice -n 5, OMP_NUM_THREADS=1.
cd /home/user/Ranger3143/labs/safe/verify09
LOG=/home/user/Ranger3143/labs/logs/safe/VERIFY-2
export OMP_NUM_THREADS=1 AEGIS_THREADS=1
run() { name=$1; shift; echo "== $name"; nice -n 5 "$@" > $LOG/$name.log 2>&1; echo "   exit $?"; }
# HARDEN-ATTEST
run HA_recount        python3 -I v2_ha.py recount
run HA_genuine        python3 -I v2_ha.py genuine
run HA_mutants_core   python3 -I v2_ha.py mutants
run HA_rerun30        python3 -I v2_ha.py rerun
run HA_byteflip_own   python3 -I v2_ha.py byteflip
run HA_forgery_s1     python3 -I v2_ha.py forgery
# HARDEN-WITNESS
run HW_recount        python3 -I v2_hw.py recount
run HW_rerun          python3 -I v2_hw.py rerun
run HW_golden         python3 -I v2_hw.py golden
run HW_diff           python3 -I v2_hw.py diff
run HW_gen            python3 -I v2_hw.py gen
run HW_extreme        python3 -I v2_hw.py extreme
run HW_prompt_length  python3 -I v2_hw_dos.py
run HW_h2self         python3 -I v2_hw_h2self.py
( cd /home/user/aefinity-ai/alice-aegis/aegis-linux && nice -n 5 cargo test --release --example cis_witness --offline > $LOG/HW_cargo_test_cis_witness.log 2>&1
  nice -n 5 cargo test -p aegis-core --release --offline > $LOG/HW_cargo_test_aegis_core.log 2>&1 )
# SAFE-05
run S5_score          python3 -I v2_s5.py score
run S5_verify         python3 -I v2_s5.py verify
run S5_heldout        python3 -I v2_s5.py heldout
run S5_extra          python3 -I v2_s5.py extra
