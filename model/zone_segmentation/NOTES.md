# Zone Segmentation — Research Notes

## Problem Statement
Extract polygonal features from raster map images using a visual pattern query.
- **Input**: map image + pattern thumbnail (32×32 crop of the target zone)
- **Output**: binary mask of the target zone

## Key Prior Work: LOAM (SIGSPATIAL '23)
Lin et al., "Exploiting Polygon Metadata to Understand Raster Maps"

### What LOAM does
1. **5 hand-crafted preprocessing channels** from the map + legend swatch:
   - Adaptive Color Thresholding (with conditional dilation)
   - Dynamic Color Thresholding
   - Color-Set Matching
   - Boundary Detection
   - Color Differencing
2. **Text-Pattern Matching** via OCR
3. **Auxiliary-Info Embedding** (color variety, number of keys, complexity)
4. **Custom CNN** with Dual-Scale Channel Attention + Spatial Attention
5. Trained on **14 real USGS maps** (536 keys), tested on 24 maps (849 keys)
6. **Median F1 = 0.809** (weighted, with 0.3 weight for easy pixels, 0.7 for hard)

### LOAM's strengths
- Domain-specific preprocessing captures expert knowledge about map reading
- Handles color shift, translucent symbols, similar colors between keys
- Uses text labels as disambiguation cues

### LOAM's weaknesses
- **Brittle preprocessing**: 5 hand-crafted channels won't transfer to non-USGS maps
- **Tiny training set**: 14 maps — overfitting risk
- **Not end-to-end**: each preprocessing step has tuned parameters (α=2, β=0.25)
- **No synthetic data**: relies entirely on manually annotated real maps

## Our Approach
Pattern-conditioned U-Net pretrained on synthetic zoning map data.

### Architecture
- **Encoder**: ResNet-34 pretrained (standard 3-channel RGB)
- **Pattern conditioning**: 32×32 thumbnail → CNN → 256-dim → FiLM modulation
- **Decoder**: 4-level U-Net with skip connections, FiLM at each level
- **Output**: 1-channel sigmoid (binary mask)
- **Loss**: BCE + Dice

### Key differences from LOAM
| Aspect | LOAM | Ours |
|--------|------|------|
| Preprocessing | 5 hand-crafted bitmap channels | None (raw RGB) |
| Architecture | Custom CNN + dual attention | U-Net + FiLM conditioning |
| Training data | 14 real maps (manual annotation) | ~4,000 synthetic maps (automated) |
| Query type | Legend swatch (color only) | Pattern thumbnail (color + texture) |
| Text awareness | OCR text-pattern matching | Text rendered in training images |
| Domain specificity | USGS geological maps only | Any colored/patterned polygon map |
| Reproducibility | Requires manual annotation | Fully automated pipeline |

### Our potential contribution
1. **Synthetic pretraining pipeline** — generates unlimited paired (image, pattern, mask) training data from real GeoJSON sources with randomized rendering
2. **End-to-end learning** — replaces 5 hand-crafted preprocessing steps with a single learned model
3. **Pattern-based query** — handles both solid colors and hatched/dot patterns, not just color matching
4. **Zero manual annotation** — entire training set is programmatically generated

### Success criteria
- **Baseline**: IoU > 0.75 on synthetic test set (proves architecture works)
- **Transfer**: F1 > 0.70 on real USGS maps (competitive with LOAM's 0.809)
- **Ablation**: show value of synthetic pretraining, augmentation types, pattern vs color query

### Framing for paper
> "We present a synthetic data pipeline for training pattern-conditioned segmentation models to extract polygonal features from raster maps. Using real-world zoning GeoJSONs, we generate thousands of paired training samples with varied rendering styles. A simple U-Net baseline pretrained on this synthetic data approaches the performance of heavily-engineered approaches trained on real data, without requiring manual annotation."

## Dataset Statistics
- **Source**: 219 US city zoning GeoJSONs
- **Samples**: ~4,380 map images
- **Training pairs**: ~30,000-50,000 (image, pattern, mask) triplets
- **Augmentations**: random colors (HSV), rotation (0-360°), page sizes (8 options), basemaps (Light Gray/Topo), labels (Arcade formatting), hatching (10 Esri styles), old-map effects, boundary blur, resolution variation
- **Pattern size**: 32×32 thumbnails from zone interior
- **Annotation**: rotation, basemap, has_labels, has_hatching, old_map_intensity, n_zones, zone_coverage, per-zone pattern_type and pixel_fraction
