# Spatial ML

## Project Overview
ML pipeline for extracting and understanding zoning data from US city maps and ordinances.

## Key Components
- **collector/** — Scrapers for zoning ordinances (docx from municipal code sites)
- **processor/** — Data processing pipeline
  - `map_renderer/` — Renders synthetic zoning maps from GeoJSON with randomized styles
  - `zoning_map/` & `zoning_map_geopandas/` — GeoJSON → map processing
  - `docx_to_markdown/`, `pdf_to_markdown/` — Document conversion
- **model/** — ML models
  - `zone_segmentation/` — Pattern-conditioned U-Net for extracting zones from raster maps
  - `zoning_codes_extract/` — Zoning code extraction
- **pytorch_processor/** — PyTorch-based zoning data processing
- **frontend/** — Next.js web app (Supabase backend)
- **resources/** — Test data and results
- **scripts/** — Utility scripts

## Zone Segmentation Model (model/zone_segmentation/)
This is the active research focus. See `model/zone_segmentation/NOTES.md` for full details.

- **Task**: Given a map image + 32×32 pattern thumbnail → predict binary mask of target zone
- **Architecture**: ResNet-34 encoder + FiLM conditioning + U-Net decoder, BCE+Dice loss
- **Training data**: ~4,380 synthetic maps from 219 US city zoning GeoJSONs (~30-50K triplets)
- **Baseline comparison**: LOAM (SIGSPATIAL '23, median F1=0.809) — uses 5 hand-crafted preprocessing channels; ours is end-to-end with zero manual annotation
- **Key contribution**: Synthetic data pipeline generating unlimited (image, pattern, mask) training pairs

## USGS AI4CMA Evaluation (model/zone_segmentation/scripts/eval_usgs.py)
Evaluates our model against the USGS AI4CMA geological map benchmark — the same data LOAM uses (median F1=0.809). This is a **domain transfer** test: model trained on synthetic zoning maps, evaluated on real geological maps.

- **Data**: `usgs/` directory contains archives (validation.tar.gz, evaluation.tar.gz, answer keys). Script auto-extracts to a work directory.
- **Tiled inference**: Large USGS maps (6K–18K px) are tiled into overlapping 512×512 patches with overlap averaging, matching LOAM's tiling approach.
- **Legend swatch → pattern**: The JSON annotations provide legend swatch bounding boxes. Raw crops contain text labels + borders that don't match our training patterns (pure color/hatching from zone interiors). A cleaning step extracts the dominant fill color by computing the median RGB and replacing outlier (text/border) pixels. Use `--no-clean-pattern` to skip.
- **Metrics**: IoU, Dice, F1, precision, recall per feature. Reports unweighted F1 (LOAM uses pixel-weighted F1 with easy/hard distinction).
- **Usage**: `python -m model.zone_segmentation.scripts.eval_usgs --checkpoint <path> --usgs-dir usgs/ --dataset validation --device mps --save-viz`

## Tech Stack
- Python 3.11 (uv for package management)
- PyTorch (segmentation model)
- Next.js / Supabase (frontend)
- DVC (data versioning)
- Docker (collector service)
