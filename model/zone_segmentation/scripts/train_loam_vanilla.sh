#!/usr/bin/env bash
# Train zone segmentation with LOAM-aligned params + vanilla U-Net.
# Same training config as train_loam.sh but without pretrained ResNet backbone.
# This matches LOAM's encoder architecture more closely.
set -euo pipefail

python -m model.zone_segmentation.scripts.train_loam_vanilla \
    --data data/training/zoning_segmentation \
    --epochs 15 \
    --batch-size 2 \
    --image-size 1024 \
    --lr 1e-5 \
    --momentum 0.999 \
    --weight-decay 1e-8 \
    --min-coverage 0.05 \
    --num-workers 4 \
    --save-dir checkpoints/zone_seg_loam_vanilla \
    --val-fraction 0.05 \
    "$@"
