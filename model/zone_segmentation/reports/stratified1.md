# Stratified Sampling (Run 1)

## What changed from baseline

Same training config (epochs=15, batch_size=32, image_size=256, lr=1e-4). Only the data pipeline changed.

### 1. Source-aware train/val split

All samples from one `source_file` (GeoJSON) go entirely to train OR val — no geographic leakage. Greedy allocation balanced by density bin, targeting 15% val.

Result: 3,582 train (183 sources) / 639 val (33 sources), zero source overlap.

### 2. Stratified batch sampler

Custom `StratifiedBatchSampler` reorders all indices (no duplication) into diverse batches. Every index seen exactly once per epoch.

## Stratification key

**`density_bin` x `has_hatching` x `has_old_map`** = 3 x 2 x 2 = **12 strata**

### density_bin (sparse / medium / dense) — the critical axis

Based on **`n_zones`**: the number of **unique zone types** in the map (e.g., "R1", "C2", "Industrial").

This is NOT polygon count. A map with `n_zones=3` might contain hundreds of individual polygons, but only 3 distinct zone types, producing exactly 3 (image, pattern, mask) training pairs. A map with `n_zones=43` produces 43 pairs, each with a smaller mask.

Why this matters: the stratification criterion is the number of unique zone types per map, which directly determines:
- How many training pairs that map contributes
- How large each zone's mask is (sparse = large clear masks, dense = tiny fragmented masks)

Without stratification, dense maps dominate 93% of pairs simply because each map generates more pairs.

| Bin | n_zones | Rationale |
|-----|---------|-----------|
| sparse | 1-4 | Few zone types, large masks, clear learning signal |
| medium | 5-15 | Moderate complexity |
| dense | 16+ | Many zone types, small/ambiguous masks |

### has_hatching (59% of samples)

Hatched zones have diagonal lines, dots, or crosshatch patterns overlaid on color fill — a fundamentally different visual signal from solid-color zones. The model needs both in every batch to learn texture-invariant pattern matching.

### has_old_map (31% of samples)

Old-map effects (yellowing, fold lines, vignetting, desaturation) degrade color signal, forcing the model to rely on spatial structure rather than color matching alone.

## Fields considered but excluded

| Field | Why excluded |
|-------|-------------|
| `has_labels` | 91% positive — almost no discriminative signal |
| `has_basemap` | 66% positive, correlated with background, less impactful |
| `pixel_fraction` / `pixel_count` | Per-zone, not per-sample; already captured by density bin |
| `polygon_count` | Individual geometries per zone (e.g., "Residential" = 500 polygons). Highly correlated with n_zones. Excluded to keep strata at 12 instead of 48+ |

## Batch construction

1. Group all flat indices by strat key
2. Shuffle within each stratum
3. Round-robin schedule weighted by stratum size
4. For each batch, draw from schedule while enforcing **source diversity** (no two items from same GeoJSON in one batch)
5. Relax source constraint as fallback to avoid deadlock
6. `set_epoch()` gives different ordering each epoch (deterministic)

## Results

*Pending — run not yet executed.*

## Command

```
python -m model.zone_segmentation.train --data data/training/zoning_segmentation --epochs 15 --batch-size 32 --image-size 256 --lr 1e-4 --num-workers 4 --save-dir checkpoints/zone_seg_stratified --val-fraction 0.15
```
