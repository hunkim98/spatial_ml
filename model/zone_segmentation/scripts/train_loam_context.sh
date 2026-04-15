#!/usr/bin/env bash
# Train zone segmentation with context-aware model.
# Uses legend grid (all patterns) for inter-pattern context.
set -euo pipefail

python -m model.zone_segmentation.scripts.train_loam_context \
    --data data/training/zoning_segmentation \
    --epochs 15 \
    --batch-size 2 \
    --image-size 1024 \
    --legend-size 128 \
    --lr 1e-5 \
    --momentum 0.999 \
    --weight-decay 1e-8 \
    --min-coverage 0.005 \
    --num-workers 4 \
    --save-dir checkpoints/zone_seg_context \
    --val-fraction 0.05 \
    "$@"
