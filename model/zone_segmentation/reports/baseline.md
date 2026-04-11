# Baseline Run

wandb: `unet-film-e15-bs32-20260408-122635` (Windows/CUDA)

## Config

| Parameter | Value |
|-----------|-------|
| Epochs | 15 |
| Batch size | 32 |
| Image size | 256 |
| Learning rate | 1e-4 |
| Weight decay | 1e-4 |
| Grad clip | 1.0 |
| AMP | True |
| Scheduler | CosineAnnealingLR |
| Loss | BCEDiceLoss (0.5 BCE + 0.5 Dice) |
| Train/val split | Every 10th sample to val |
| Batching | Standard `shuffle=True` |
| Train pairs | 215,649 |
| Val pairs | 30,928 |

## Results

| Epoch | Train Loss | Train IoU | Val Loss | Val IoU | Val Dice | Val F1 |
|-------|-----------|-----------|----------|---------|----------|--------|
| 1     | 0.2957    | 0.2983    | 0.4295   | 0.2774  | 0.2937   | 0.1572 |
| 5     | 0.1970    | 0.3545    | 0.4171   | 0.2428  | 0.2628   | 0.1870 |
| 9     | 0.1347    | 0.3894    | 0.3977   | 0.2956  | 0.3148   | 0.2186 |
| 15    | 0.1112    | 0.4081    | 0.3894   | 0.2730  | 0.2932   | 0.2381 |

Best val IoU: **0.296** (epoch 9). Train loss kept decreasing while val plateaued — overfitting.

## Problems

### 1. Geographic data leakage

The `i % 10` split puts different renders of the same city into both train and val. Each of the 216 source GeoJSONs generates ~20 samples with identical polygon geometry (same streets, same zone boundaries, just different rendering styles). The model memorizes geography rather than learning pattern matching.

### 2. Extreme pair imbalance

246,644 total (image, zone) training pairs:

| Density bin | Samples | % of samples | Pairs | % of pairs |
|-------------|---------|-------------|-------|------------|
| Sparse (1-4 zones) | 1,161 | 27.5% | 2,720 | **1.1%** |
| Medium (5-15 zones) | 1,493 | 35.4% | 13,913 | **5.6%** |
| Dense (16+ zones) | 1,567 | 37.1% | 230,011 | **93.3%** |

With random shuffle, **93.3% of training pairs come from dense maps** — many small, ambiguous zones with tiny masks. The model is starved of clear learning signal from sparse maps with large, unambiguous masks.

## Command

```
python -m model.zone_segmentation.train --data data/training/zoning_segmentation --epochs 15 --batch-size 32 --image-size 256 --lr 1e-4 --num-workers 4 --save-dir checkpoints/zone_seg_baseline --no-stratify
```
