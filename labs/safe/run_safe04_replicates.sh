#!/bin/bash
# SAFE-04 supplementary replicates (NOT pre-registered): same data, same recipe, data-order seed 8 instead of 7. p5 first, then p0.
S=/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad
L=/home/user/Ranger3143/labs/logs/safe/SAFE-04
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
for p in ${@:-5 0}; do
  nice -n 5 python3 -I /home/user/Ranger3143/labs/safe/finetune_tinybit.py \
    --init $S/opmodel/checkpoints/op12k.pt --data $S/safe04/data/train_p$p.bin --val-data $S/opmodel/valid_op12k.bin \
    --out $S/safe04/ckpt/safe04_p${p}_s8.pt --steps 600 --batch 8 --block 512 --lr 2e-4 --warmup 20 --wd 0 --grad-clip 1.0 \
    --seed 8 --threads 4 --log-every 20 --val-every 100 --sampler epoch --tag safe04_p${p}_s8 2>&1 | grep --line-buffered -v Warning > $L/train_p${p}_s8.log
done
echo REPLICATES_DONE > $L/replicates_done.flag
