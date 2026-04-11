# LOAM Parameter Alignment

Reference: Lin et al., "Exploiting Polygon Metadata to Understand Raster Maps" (SIGSPATIAL '23)

## Parameter Comparison

| Parameter | LOAM | Baseline (ours) | LOAM-aligned (ours) | Rationale |
|-----------|------|-----------------|---------------------|-----------|
| Input resolution | 1024×1024 | 256×256 | **1024×1024** | Fine spatial detail — zone boundaries, text, hatching patterns all need higher res |
| Batch size | 1 | 32 | **2** | Memory constraint at 1024px; bs=2 more stable than bs=1 |
| Optimizer | SGD | AdamW | **SGD** | Match LOAM; SGD + high momentum is well-suited for segmentation |
| Momentum | 0.999 | N/A (AdamW) | **0.999** | Smooths noisy gradients from small batch size |
| Learning rate | 1e-5 | 1e-4 | **1e-5** | Baseline overfits at epoch 9 with 1e-4; slower LR for careful convergence |
| Weight decay | 1e-8 | 1e-4 | **1e-8** | Near-zero — don't pull pretrained ResNet features away from learned values |
| Epochs | 40 | 15 | **40** | Longer training with lower LR; best checkpoint saved |
| Loss | Dice only | 0.5 BCE + 0.5 Dice | **Dice only** | BCE dominated by background pixels (98% in dense maps); Dice measures overlap directly |
| Min coverage | 25% | None | **5%** | LOAM's 25% is for patches; our full images have lower per-zone coverage, so 5% threshold |
| Scheduler | — | CosineAnnealingLR | CosineAnnealingLR | Unchanged |
| Grad clip | — | 1.0 | 1.0 | Unchanged |
| AMP | — | CUDA only | CUDA only | Unchanged |

## What we skipped (for now)

### SA-Net (Shuffle Attention)
LOAM uses SA-Net between encoder and decoder — splits channels into spatial and channel attention branches. Their ablation shows ~5% F1 drop without it. However:
- Our FiLM conditioning already covers the channel attention part
- Spatial attention helps LOAM because it works *with* their OCR text channel
- We don't do OCR, so the spatial attention benefit is smaller for us
- Code change to unet.py — not just a config tweak

**Decision**: Skip for now. Get results with training config changes first.

### Vision Encoder (DINOv2 / CLIP)
**Key insight from discussion**: Our model feeds raw RGB into a ResNet encoder that has no "understanding" of the map. LOAM compensates with 5 hand-crafted preprocessing channels (color thresholding, boundary detection, text matching, etc.) + auxiliary embeddings.

A more modern approach: use a pretrained vision model (DINOv2, CLIP) that already understands textures, text, colors, spatial layout from millions of images. This would be our version of LOAM's auxiliary info — learned instead of hand-crafted, no OCR pipeline needed.

Architecture sketch:
```
map image → DINOv2/CLIP → rich semantic features
                              ↓
                  "this map has 5 zones, 2 share red,
                   hatched patterns in NW region"
                              ↓
              feed into decoder alongside pattern query
```

**Decision**: Note as future direction. Significant architectural change.

## Files

| File | Purpose |
|------|---------|
| `trainer_loam.py` | Training loop with SGD + Dice loss |
| `train_loam.py` | CLI entry point for LOAM-aligned training |
| `train_loam.sh` | Shell script with all params set |
| `dataset.py` | Added `min_coverage` filter to `StratificationConfig` |
| `losses.py` | Unchanged — `DiceLoss` already existed |
| `unet.py` | Unchanged — same architecture |
| `trainer.py` | Unchanged — baseline preserved |
| `train.py` | Unchanged — baseline preserved |

## Command

```bash
bash model/zone_segmentation/train_loam.sh
```

## Results

*Pending — run not yet executed.*
