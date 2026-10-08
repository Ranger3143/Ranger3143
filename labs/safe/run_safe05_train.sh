#!/bin/bash
# SAFE-05 fine-tune: the SAFE-04 recipe, unchanged, on the defended mix. One run, seed 7, 4 threads, nothing else running.
# usage: run_safe05_train.sh [defended|defused]   (defused = SUPPLEMENTARY SAFE-05b, trained after the primary verdict was written)
V=${1:-defended}
S=/tmp/claude-0/-home-user/11951ea1-b2cb-58ef-9690-04278a7c68c7/scratchpad
L=/home/user/Ranger3143/labs/logs/safe/SAFE-05
FLAG=$L/train_done.flag; [ "$V" != "defended" ] && FLAG=$L/train_done_$V.flag
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4
mkdir -p $S/safe05/ckpt
nice -n 5 python3 -I /home/user/Ranger3143/labs/safe/finetune_tinybit.py \
  --init $S/opmodel/checkpoints/op12k.pt --data $S/safe05/data/train_$V.bin --val-data $S/opmodel/valid_op12k.bin \
  --out $S/safe05/ckpt/safe05_$V.pt --steps 600 --batch 8 --block 512 --lr 2e-4 --warmup 20 --wd 0 --grad-clip 1.0 \
  --seed 7 --threads 4 --log-every 20 --val-every 100 --sampler epoch --tag safe05_$V 2>&1 | grep --line-buffered -v Warning > $L/train_$V.log
echo ALL_DONE > $FLAG
