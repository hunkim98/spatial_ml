#!/usr/bin/env bash
# Train zone segmentation with NO stratification (original shuffle behavior).
# Use this as the control run — matches the previous wandb run config.
set -euo pipefail

python -m model.zone_segmentation.train \
    --data data/training/zoning_segmentation \
    --epochs 15 \
    --batch-size 32 \
    --image-size 256 \
    --lr 1e-4 \
    --num-workers 4 \
    --save-dir checkpoints/zone_seg_baseline \
    --no-stratify \
    "$@"
