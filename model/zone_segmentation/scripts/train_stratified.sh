#!/usr/bin/env bash
# Train zone segmentation WITH stratified batch sampling.
# Same config as previous run, but with source-aware split + density-balanced batches.
set -euo pipefail

python -m model.zone_segmentation.scripts.train \
    --data data/training/zoning_segmentation \
    --epochs 15 \
    --batch-size 32 \
    --image-size 256 \
    --lr 1e-4 \
    --num-workers 4 \
    --save-dir checkpoints/zone_seg_stratified \
    --val-fraction 0.15 \
    "$@"
