# Zone Segmentation Trainer

Pattern-conditioned U-Net for extracting polygonal zones from raster zoning maps.
See `NOTES.md` for the research framing and architecture details.

## Layout
```
zone_segmentation/
  dataset.py          # PyTorch Dataset / DataLoader
  unet.py             # PatternConditionedUNet (ResNet-34 + FiLM)
  losses.py           # BCE + Dice
  metrics.py          # IoU / Dice / precision / recall / F1
  trainer.py          # Training loop with W&B tracking, AMP, history
  viz.py              # Plotting helpers (samples, predictions, history)
  train.py            # CLI entrypoint (`python -m model.zone_segmentation.train ...`)
  run.py              # Smoke test
  inference.py        # Inference + mask -> GeoJSON
  notebooks/
    zone_segmentation_demo.ipynb
  pyproject.toml      # Trainer-only deps (used by Dockerfile)
  Dockerfile          # CUDA-enabled image, runs on GPU or CPU
```

## Quickstart (local)
```bash
# uses CUDA if available, else MPS, else CPU
python -m model.zone_segmentation.train \
    --data data/training/zoning_segmentation \
    --epochs 5 --batch-size 2 --image-size 256
```

## Quickstart (Docker, mirrors ac215_Spatially)

Secrets: the trainer reads `WANDB_API_KEY` from the environment. The repo's
`secrets/teamspatially-project.env` already contains it. `docker compose` loads
it via `env_file`, so you don't have to pass it manually.

```bash
# build the image (one time)
docker compose build zone_segmentation_trainer

# train on GPU (one or more visible CUDA devices)
docker compose run --rm --gpus all zone_segmentation_trainer \
    python -m model.zone_segmentation.train \
        --data /data/training/zoning_segmentation \
        --epochs 20 --batch-size 4 --image-size 512

# train on CPU (no --gpus flag, same image)
docker compose run --rm zone_segmentation_trainer \
    python -m model.zone_segmentation.train \
        --data /data/training/zoning_segmentation \
        --epochs 5 --batch-size 2 --image-size 256
```

The trainer auto-picks `cuda` when a GPU is visible, otherwise `cpu`.
Same image, no rebuild — control GPU/CPU with the `--gpus` flag at run time.

When `WANDB_API_KEY` is set:
- Run name: `unet-film-e{epochs}-bs{bs}-{timestamp}`
- Project: `spatially-zone-segmentation`
- Logs `train/*`, `val/*`, `dataset/*` metrics, prediction-grid images, and
  the best checkpoint as a `wandb.Artifact`.

Outputs:
- `checkpoints/zone_segmentation/best.pt` — best by val IoU
- `checkpoints/zone_segmentation/history.json` — replay metrics offline
- `checkpoints/zone_segmentation/samples/epoch_NNN.png` — prediction snapshots

## USGS Evaluation (Cross-Domain Transfer)

Evaluate the trained model on USGS geological maps from the DARPA CMA benchmark.
This tests whether a model trained on synthetic zoning maps can segment real
geological maps without any fine-tuning.

### macOS / Linux
```bash
python -m model.zone_segmentation.scripts.eval_usgs \
    --checkpoint checkpoints/zone_seg_loam_vanilla_v2/best.pt \
    --usgs-dir usgs/ \
    --dataset validation \
    --device mps \
    --model-type vanilla \
    --skip-no-gt \
    --save-viz
```

### Windows (PowerShell)
```powershell
# Full tiled evaluation (~18 hours on GPU)
.\scripts\run_usgs_eval_tiled.ps1

# Quick whole-map evaluation (~20 min)
.\scripts\run_usgs_eval_tiled.ps1 -NoTile

# Limit to first 3 maps for a quick test
.\scripts\run_usgs_eval_tiled.ps1 -MaxMaps 3

# Use CPU
.\scripts\run_usgs_eval_tiled.ps1 -Device cpu
```

### Windows (Command Prompt)
```cmd
scripts\run_usgs_eval_tiled.bat
scripts\run_usgs_eval_tiled.bat cpu
```

### Key flags
| Flag | Description |
|------|-------------|
| `--model-type vanilla` | Use VanillaUNet (required for `zone_seg_loam_vanilla_v2` checkpoint) |
| `--skip-no-gt` | Skip maps without ground truth rasters (faster) |
| `--no-tile` | Downsample whole map to 512x512 instead of tiling (fast but lower quality) |
| `--save-viz` | Save 4-panel visualizations per feature |
| `--max-maps N` | Limit to first N maps (0 = all) |
| `--tile-size 512` | Tile size in pixels (default: 512) |
| `--tile-overlap 128` | Overlap between tiles (default: 128) |

### Output
Results are saved to `results/usgs_eval_*/`:
- `results.json` — per-feature metrics (F1, IoU, precision, recall)
- `summary.txt` — aggregate statistics
- `viz/` — visualization panels (map, pattern, GT, prediction)

## Notebook
```bash
jupyter lab model/zone_segmentation/notebooks/zone_segmentation_demo.ipynb
```
The notebook walks through dataset visualization, model architecture, a short
training run, history plots, and prediction visualizations. The W&B section is
optional.
