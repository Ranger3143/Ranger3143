#!/bin/bash
# LAB-09 verify phase runner. Every script is read-only with respect to the experiments' logs; scratch goes to the scratchpad.
cd /home/user/Ranger3143/labs/safe/verify09
LOG=/home/user/Ranger3143/labs/logs/safe/VERIFY
export OMP_NUM_THREADS=1
run() { name=$1; shift; echo "== $name" ; nice -n 5 "$@" > $LOG/$name.log 2>&1; echo "   exit $?"; }
run SAFE-01_h1_recount        python3 -I v01_h1.py
run SAFE-01_h2_recount        python3 -I v01_h2.py
run SAFE-01_h2_mutation_rebuild python3 -I v01_h2b.py
run SAFE-01_h2_redecode       python3 -I v01_h2c.py
run SAFE-01_h2_ppl            python3 -I v01_h2d.py
run SAFE-01_h3_recount        python3 -I v01_h3.py
run SAFE-01_s2_forgery_recheck bash v01_s2.sh
run SAFE-01_genuine_boots_both_forms bash v01_f2_all.sh
run SAFE-01_h1_rerun_sample   python3 -I v01_h1b.py
run SAFE-01_h3_rerun_all      python3 -I v01_h3b.py
run SAFE-02_recount           python3 -I v02.py
run SAFE-02_diagnostics       python3 -I v02b.py
run SAFE-02_rerun_verify      python3 -I v02_ver.py
run SAFE-02_decoder_ctx_check python3 -I v02c.py
run SAFE-02_tables_and_lookup_outputs python3 -I v02d.py
run SAFE-02_h5_echo_vs_exec   python3 -I v02e.py
run SAFE-03_recount           python3 -I v03.py
run SAFE-03_extras            python3 -I v03b.py
run SAFE-03_rerun_verify      python3 -I v03_ver.py
run SAFE-03_op12k_openers     python3 -I v03c.py
run SAFE-04_detection_recount python3 -I v04_det.py
run SAFE-04_eval_recount_torch_outputs python3 -I v04_eval.py
run SAFE-04_poison_and_leakage python3 -I v04b.py
run SAFE-04_engine_independent python3 -I v04_engine.py
run SAFE-04_rerun_verify      python3 -I v04_ver.py
run STATS                     python3 -I v00_stats.py
echo ALL_DONE > $LOG/ALL_DONE.flag
