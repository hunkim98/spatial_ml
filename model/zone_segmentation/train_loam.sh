#!/usr/bin/env bash
# Train zone segmentation with LOAM-aligned parameters.
# Reference: Lin et al., SIGSPATIAL '23 (median F1=0.809)
#
# Key changes vs baseline:
#   1024px (was 256), bs=2 (was 32), SGD+momentum (was AdamW),
#   lr=1e-5 (was 1e-4), wd=1e-8 (was 1e-4), Dice loss (was BCE+Dice),
#   40 epochs (was 15), 5% min coverage filter (was none)
set -euo pipefail

python -m model.zone_segmentation.train_loam \
    --data data/training/zoning_segmentation \
    --epochs 40 \
    --batch-size 2 \
    --image-size 1024 \
    --lr 1e-5 \
    --momentum 0.999 \
    --weight-decay 1e-8 \
    --min-coverage 0.05 \
    --num-workers 4 \
    --save-dir checkpoints/zone_seg_loam \
    --val-fraction 0.15 \
    "$@"
