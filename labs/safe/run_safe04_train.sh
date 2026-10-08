#!/bin/bash
# SAFE-04 fine-tunes: p5 first (the pre-registered headline), then p0, then p1. One at a time, 4 threads, nothing else running.
# usage: run_safe04_train.sh [p ...]   (default: 5 0 1)
S=/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad
L=/home/user/Ranger3143/labs/logs/safe/SAFE-04
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
mkdir -p $S/safe04/ckpt
for p in ${@:-5 0 1}; do
  nice -n 5 python3 -I /home/user/Ranger3143/labs/safe/finetune_tinybit.py \
    --init $S/opmodel/checkpoints/op12k.pt --data $S/safe04/data/train_p$p.bin --val-data $S/opmodel/valid_op12k.bin \
    --out $S/safe04/ckpt/safe04_p$p.pt --steps 600 --batch 8 --block 512 --lr 2e-4 --warmup 20 --wd 0 --grad-clip 1.0 \
    --seed 7 --threads 4 --log-every 20 --val-every 100 --sampler epoch --tag safe04_p$p 2>&1 | grep --line-buffered -v Warning > $L/train_p$p.log
done
echo ALL_DONE > $L/train_done.flag
