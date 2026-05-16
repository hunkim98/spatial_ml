"""Evaluate zone segmentation model on USGS AI4CMA geological map data.

This tests domain transfer from synthetic zoning maps to real geological maps,
the same benchmark LOAM (SIGSPATIAL '23) uses (median F1=0.809).

Usage:
    python -m model.zone_segmentation.scripts.eval_usgs \
        --checkpoint checkpoints/zone_segmentation/best.pt \
        --usgs-dir usgs/ \
        --dataset validation \
        --work-dir /tmp/usgs_eval/ \
        --output-dir results/usgs_eval/ \
        --tile-size 512 \
        --tile-overlap 128 \
        --threshold 0.5 \
        --device mps \
        --save-viz \
        --max-maps 0
"""

import argparse
import json
import logging
import os
import shutil
import tarfile
import zipfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from tqdm import tqdm

from ..unet import PatternConditionedUNet
from ..unet_vanilla import VanillaUNet

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Device selection (same pattern as train.py)
# ---------------------------------------------------------------------------

def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def extract_dataset(
    usgs_dir: Path, dataset: str, work_dir: Path,
) -> tuple[Path, Path, Path]:
    """Extract USGS archives and return (map_dir, json_dir, gt_dir).

    For 'validation': extracts validation.tar.gz, updated_validation_jsons.tar.gz,
    and validation_answer_key.tar.gz.

    For 'evaluation': extracts evaluation.tar.gz and the answer key zip.
    """
    usgs_dir = Path(usgs_dir)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    if dataset == "validation":
        # Maps + original JSONs
        val_tar = usgs_dir / "validation.tar.gz"
        val_dir = work_dir / "validation"
        if not val_dir.exists():
            logger.info("Extracting %s ...", val_tar)
            with tarfile.open(val_tar) as tf:
                tf.extractall(work_dir)

        # Updated JSONs (overwrite originals)
        updated_tar = usgs_dir / "updated_validation_jsons.tar.gz"
        if updated_tar.exists():
            logger.info("Extracting updated JSONs from %s ...", updated_tar)
            with tarfile.open(updated_tar) as tf:
                tf.extractall(work_dir)
            # Copy updated JSONs into validation dir
            updated_dir = work_dir / "updated_validation_jsons"
            if updated_dir.exists():
                for f in updated_dir.glob("*.json"):
                    shutil.copy2(f, val_dir / f.name)

        # Ground truth rasters
        gt_tar = usgs_dir / "validation_answer_key.tar.gz"
        gt_dir = work_dir / "validation_rasters"
        if not gt_dir.exists():
            logger.info("Extracting GT rasters from %s ...", gt_tar)
            with tarfile.open(gt_tar) as tf:
                tf.extractall(work_dir)

        map_dir = val_dir
        json_dir = val_dir  # JSONs are co-located with maps
        return map_dir, json_dir, gt_dir

    elif dataset == "evaluation":
        # Maps + JSONs
        eval_tar = usgs_dir / "evaluation.tar.gz"
        eval_dir = work_dir / "eval_data_perfomer"
        if not eval_dir.exists():
            logger.info("Extracting %s ...", eval_tar)
            with tarfile.open(eval_tar) as tf:
                tf.extractall(work_dir)

        # Answer key
        gt_zip = usgs_dir / "AI4CMA_Map_Feature_Extraction_Challenge_Evaluation_Answer_Key.zip"
        gt_dir = work_dir / "evaluation_answer_key"
        if not gt_dir.exists() and gt_zip.exists():
            logger.info("Extracting GT from %s ...", gt_zip)
            with zipfile.ZipFile(gt_zip) as zf:
                zf.extractall(work_dir)

        map_dir = eval_dir
        json_dir = eval_dir
        return map_dir, json_dir, gt_dir

    else:
        raise ValueError(f"Unknown dataset: {dataset}")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_map_image(tif_path: Path) -> np.ndarray:
    """Load a GeoTIFF as (H, W, 3) uint8 RGB array.

    Falls back to PIL if rasterio is not available.
    """
    try:
        import rasterio
        with rasterio.open(tif_path) as src:
            # Read all bands — most maps have 3 (RGB) or 4 (RGBA)
            data = src.read()  # (C, H, W)
            if data.shape[0] >= 3:
                rgb = np.stack([data[0], data[1], data[2]], axis=-1)  # (H,W,3)
            elif data.shape[0] == 1:
                rgb = np.stack([data[0]] * 3, axis=-1)
            else:
                raise ValueError(f"Unexpected band count: {data.shape[0]}")
            return rgb.astype(np.uint8)
    except ImportError:
        logger.warning("rasterio not available, falling back to PIL for %s", tif_path)
        img = Image.open(tif_path).convert("RGB")
        return np.array(img)


def get_poly_features(json_path: Path) -> list[dict]:
    """Parse LabelMe JSON and return _poly features with label and bbox.

    Returns:
        List of dicts with keys: label, bbox (x_min, y_min, x_max, y_max)
    """
    with open(json_path) as f:
        data = json.load(f)

    features = []
    for shape in data.get("shapes", []):
        label = shape["label"]
        if "_poly" not in label:
            continue
        pts = shape["points"]
        # points: [[x_min, y_min], [x_max, y_max]] for rectangles
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bbox = (min(xs), min(ys), max(xs), max(ys))
        features.append({"label": label, "bbox": bbox})

    return features


def crop_legend_swatch(
    map_array: np.ndarray, bbox: tuple, clean: bool = True,
) -> Image.Image:
    """Crop legend swatch from map using bbox, clamp to bounds.

    USGS legend swatches contain text labels and black borders that don't
    appear in our training patterns (which are pure color/hatching samples
    from zone interiors). When clean=True, we remove text/border artifacts
    by extracting the dominant fill color.

    Args:
        map_array: (H, W, 3) uint8
        bbox: (x_min, y_min, x_max, y_max) in pixel coords (float)
        clean: if True, replace text/border pixels with dominant fill color

    Returns:
        32x32 RGB PIL Image (the pattern thumbnail)
    """
    h, w = map_array.shape[:2]
    x_min, y_min, x_max, y_max = bbox
    x_min = max(0, int(round(x_min)))
    y_min = max(0, int(round(y_min)))
    x_max = min(w, int(round(x_max)))
    y_max = min(h, int(round(y_max)))

    if x_max <= x_min or y_max <= y_min:
        logger.warning("Empty bbox after clamping: %s", bbox)
        return Image.new("RGB", (32, 32), (128, 128, 128))

    crop = map_array[y_min:y_max, x_min:x_max]  # (h, w, 3)

    if clean:
        crop = _clean_legend_swatch(crop)

    img = Image.fromarray(crop)
    return img.resize((32, 32), Image.BILINEAR)


def _clean_legend_swatch(crop: np.ndarray) -> np.ndarray:
    """Remove text labels and border lines from a legend swatch.

    Strategy:
    1. Inset by ~15% to remove black border lines
    2. Compute the median color of the inner region (robust to text outliers)
    3. Any pixel deviating significantly from the median is text/border → replace

    This produces a clean fill-color patch that matches what the model
    saw during training (pure color/pattern, no text).
    """
    ch, cw = crop.shape[:2]

    # Step 1: Inset to skip border lines (at least 2px, up to 15% of dim)
    inset_y = max(2, int(ch * 0.15))
    inset_x = max(2, int(cw * 0.15))
    inner = crop[inset_y:ch - inset_y, inset_x:cw - inset_x]

    if inner.size == 0:
        return crop  # too small to inset, return as-is

    # Step 2: Compute median color of inner region.
    # The median is robust to text outliers (text is typically <30% of pixels).
    pixels = inner.reshape(-1, 3).astype(np.float32)
    median_color = np.median(pixels, axis=0)

    # Step 3: Find pixels that deviate from the median color.
    # Use Euclidean distance in RGB space.
    full_pixels = crop.reshape(-1, 3).astype(np.float32)
    dist = np.sqrt(np.sum((full_pixels - median_color) ** 2, axis=-1))

    # Threshold: pixels more than 50 RGB units from the median are text/border.
    # This is generous — dark text on light fill differs by 150+ units.
    text_mask = dist > 50.0

    if text_mask.sum() == 0:
        return crop  # nothing to clean

    # Step 4: Replace text/border pixels with the median fill color
    result = crop.copy().reshape(-1, 3)
    result[text_mask] = median_color.astype(np.uint8)
    return result.reshape(crop.shape)


def load_gt_raster(gt_dir: Path, map_stem: str, label: str) -> np.ndarray | None:
    """Load ground truth binary raster: {map_stem}_{label}.tif → (H, W) uint8 0/1.

    Returns None if GT file not found.
    """
    gt_path = gt_dir / f"{map_stem}_{label}.tif"
    if not gt_path.exists():
        return None

    try:
        import rasterio
        with rasterio.open(gt_path) as src:
            data = src.read(1)  # single band
            return (data > 0).astype(np.uint8)
    except ImportError:
        img = Image.open(gt_path)
        data = np.array(img)
        if data.ndim == 3:
            data = data[:, :, 0]
        return (data > 0).astype(np.uint8)


# ---------------------------------------------------------------------------
# Tiled inference
# ---------------------------------------------------------------------------

class TiledSegmenter:
    """Wraps the model for tiled inference on large images."""

    def __init__(self, checkpoint: str, device: str = "cuda", tile_size: int = 512,
                 model_type: str = "resnet"):
        self.device = device
        self.tile_size = tile_size

        if model_type == "vanilla":
            self.model = VanillaUNet()
        else:
            self.model = PatternConditionedUNet(pretrained=False)
        state = torch.load(checkpoint, map_location=device, weights_only=True)
        self.model.load_state_dict(state)
        self.model.to(device)
        self.model.eval()

        self.image_transform = transforms.Compose([
            transforms.Resize((tile_size, tile_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        self.pattern_transform = transforms.Compose([
            transforms.Resize((32, 32)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    @torch.no_grad()
    def predict_tile(self, tile: Image.Image, pattern: Image.Image) -> np.ndarray:
        """Predict probability map for a single tile.

        Args:
            tile: map tile (any size, will be resized to tile_size)
            pattern: 32x32 pattern thumbnail

        Returns:
            (tile_h, tile_w) float32 probability map at original tile resolution
        """
        orig_w, orig_h = tile.size

        img_t = self.image_transform(tile).unsqueeze(0).to(self.device)
        pat_t = self.pattern_transform(pattern).unsqueeze(0).to(self.device)

        logits = self.model(img_t, pat_t)  # (1, 1, tile_size, tile_size)
        prob = torch.sigmoid(logits).squeeze().cpu().numpy()

        # Resize back to original tile resolution
        prob_img = Image.fromarray((prob * 255).astype(np.uint8))
        prob_img = prob_img.resize((orig_w, orig_h), Image.BILINEAR)
        return np.array(prob_img).astype(np.float32) / 255.0

    @torch.no_grad()
    def predict_tiles_batch(
        self, tiles: list[Image.Image], pattern: Image.Image, batch_size: int = 16
    ) -> list[np.ndarray]:
        """Predict probability maps for a batch of tiles with the same pattern.

        Args:
            tiles: list of map tile images
            pattern: 32x32 pattern thumbnail (same for all tiles)
            batch_size: number of tiles to process at once

        Returns:
            list of (tile_h, tile_w) float32 probability maps
        """
        pat_t = self.pattern_transform(pattern).to(self.device)
        results = []

        n_batches = (len(tiles) + batch_size - 1) // batch_size
        for i in tqdm(range(0, len(tiles), batch_size),
                       desc="    Tiles", total=n_batches, unit="batch",
                       leave=False, dynamic_ncols=True):
            batch_tiles = tiles[i:i + batch_size]
            orig_sizes = [(t.size[0], t.size[1]) for t in batch_tiles]

            img_batch = torch.stack(
                [self.image_transform(t) for t in batch_tiles]
            ).to(self.device)
            pat_batch = pat_t.unsqueeze(0).expand(len(batch_tiles), -1, -1, -1)

            logits = self.model(img_batch, pat_batch)
            probs = torch.sigmoid(logits).squeeze(1).cpu().numpy()

            for j, (ow, oh) in enumerate(orig_sizes):
                prob = probs[j]
                prob_img = Image.fromarray((prob * 255).astype(np.uint8))
                prob_img = prob_img.resize((ow, oh), Image.BILINEAR)
                results.append(np.array(prob_img).astype(np.float32) / 255.0)

        return results


def predict_tiled(
    segmenter: TiledSegmenter,
    map_pil: Image.Image,
    pattern_pil: Image.Image,
    tile_size: int = 512,
    overlap: int = 128,
    batch_size: int = 16,
) -> np.ndarray:
    """Run tiled inference on a full-resolution map.

    Args:
        segmenter: model wrapper
        map_pil: full-resolution map as PIL Image
        pattern_pil: 32x32 pattern thumbnail
        tile_size: tile size in pixels
        overlap: overlap between adjacent tiles
        batch_size: number of tiles per batch

    Returns:
        (H, W) float32 probability map at original resolution
    """
    w, h = map_pil.size
    stride = tile_size - overlap

    # Accumulator for probability averaging in overlap regions
    prob_sum = np.zeros((h, w), dtype=np.float64)
    count = np.zeros((h, w), dtype=np.float64)

    # Generate tile grid
    y_starts = list(range(0, h, stride))
    x_starts = list(range(0, w, stride))

    total_tiles = len(y_starts) * len(x_starts)
    logger.info("  Tiling: %dx%d map → %d tiles (size=%d, overlap=%d, batch=%d)",
                w, h, total_tiles, tile_size, overlap, batch_size)

    # Collect all tiles and their coordinates
    tiles = []
    coords = []
    for y0 in y_starts:
        for x0 in x_starts:
            y1 = min(y0 + tile_size, h)
            x1 = min(x0 + tile_size, w)
            y0_adj = max(0, y1 - tile_size)
            x0_adj = max(0, x1 - tile_size)

            tile = map_pil.crop((x0_adj, y0_adj, x1, y1))
            tiles.append(tile)
            coords.append((y0_adj, x0_adj, y1, x1))

    # Batched inference
    probs = segmenter.predict_tiles_batch(tiles, pattern_pil, batch_size=batch_size)

    # Accumulate
    for prob, (y0_adj, x0_adj, y1, x1) in zip(probs, coords):
        prob_sum[y0_adj:y1, x0_adj:x1] += prob
        count[y0_adj:y1, x0_adj:x1] += 1.0

    # Average overlapping predictions
    count = np.maximum(count, 1.0)
    return (prob_sum / count).astype(np.float32)


def predict_whole_map(
    segmenter: TiledSegmenter,
    map_pil: Image.Image,
    pattern_pil: Image.Image,
) -> np.ndarray:
    """Downsample whole map and run inference (fast, lower quality).

    Returns:
        (H, W) float32 probability map at original resolution
    """
    w, h = map_pil.size
    logger.info("  Whole-map mode: %dx%d → %dx%d", w, h,
                segmenter.tile_size, segmenter.tile_size)

    prob = segmenter.predict_tile(map_pil, pattern_pil)
    # prob is already at original resolution via predict_tile's resize
    return prob


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(pred_binary: np.ndarray, gt_binary: np.ndarray) -> dict:
    """Compute segmentation metrics between binary prediction and ground truth.

    Both inputs should be (H, W) uint8 with values 0/1.
    """
    pred = pred_binary.astype(bool).ravel()
    gt = gt_binary.astype(bool).ravel()

    tp = np.sum(pred & gt)
    fp = np.sum(pred & ~gt)
    fn = np.sum(~pred & gt)
    tn = np.sum(~pred & ~gt)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    intersection = tp
    union = tp + fp + fn
    iou = intersection / union if union > 0 else 0.0

    dice = 2 * intersection / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0

    total = pred.size
    return {
        "iou": float(iou),
        "dice": float(dice),
        "f1": float(f1),
        "precision": float(precision),
        "recall": float(recall),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "gt_positive_frac": float(np.sum(gt)) / total,
        "pred_positive_frac": float(np.sum(pred)) / total,
    }


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def save_viz(
    map_array: np.ndarray,
    pattern_img: Image.Image,
    gt_binary: np.ndarray | None,
    pred_binary: np.ndarray,
    metrics: dict,
    output_path: Path,
    max_display_size: int = 1024,
):
    """Save a 4-panel visualization: map crop around legend, pattern, GT, prediction."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Downsample for display if needed
    h, w = pred_binary.shape[:2]
    scale = min(1.0, max_display_size / max(h, w))
    disp_h, disp_w = int(h * scale), int(w * scale)

    map_disp = Image.fromarray(map_array).resize((disp_w, disp_h), Image.BILINEAR)
    pred_disp = Image.fromarray((pred_binary * 255).astype(np.uint8)).resize(
        (disp_w, disp_h), Image.NEAREST)

    n_panels = 4 if gt_binary is not None else 3
    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 5))

    axes[0].imshow(map_disp)
    axes[0].set_title("Map")
    axes[0].axis("off")

    axes[1].imshow(pattern_img.resize((128, 128), Image.NEAREST))
    axes[1].set_title("Pattern (32x32)")
    axes[1].axis("off")

    if gt_binary is not None:
        gt_disp = Image.fromarray((gt_binary * 255).astype(np.uint8)).resize(
            (disp_w, disp_h), Image.NEAREST)
        axes[2].imshow(gt_disp, cmap="gray")
        axes[2].set_title(f"GT (positive: {metrics['gt_positive_frac']:.3f})")
        axes[2].axis("off")

        axes[3].imshow(pred_disp, cmap="gray")
        axes[3].set_title(f"Pred (F1={metrics['f1']:.3f}, IoU={metrics['iou']:.3f})")
        axes[3].axis("off")
    else:
        axes[2].imshow(pred_disp, cmap="gray")
        axes[2].set_title(f"Pred (positive: {metrics['pred_positive_frac']:.3f})")
        axes[2].axis("off")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Per-map evaluation
# ---------------------------------------------------------------------------

def evaluate_map(
    segmenter: TiledSegmenter,
    map_path: Path,
    features: list[dict],
    gt_dir: Path | None,
    tile_size: int,
    tile_overlap: int,
    threshold: float,
    no_tile: bool,
    clean_pattern: bool,
    do_save_viz: bool,
    viz_dir: Path | None,
    batch_size: int = 4,
) -> list[dict]:
    """Evaluate all poly features for one map.

    Returns list of per-feature result dicts.
    """
    map_stem = map_path.stem
    logger.info("Loading map: %s", map_path.name)

    map_array = load_map_image(map_path)
    map_pil = Image.fromarray(map_array)
    h, w = map_array.shape[:2]
    logger.info("  Map size: %dx%d", w, h)

    results = []
    for feat in features:
        label = feat["label"]
        bbox = feat["bbox"]

        logger.info("  Feature: %s (bbox: %.0f,%.0f,%.0f,%.0f)",
                     label, *bbox)

        # Crop pattern swatch from legend
        pattern_img = crop_legend_swatch(map_array, bbox, clean=clean_pattern)

        # Run inference
        if no_tile:
            prob_map = predict_whole_map(segmenter, map_pil, pattern_img)
        else:
            prob_map = predict_tiled(
                segmenter, map_pil, pattern_img,
                tile_size=tile_size, overlap=tile_overlap,
                batch_size=batch_size,
            )

        pred_binary = (prob_map >= threshold).astype(np.uint8)

        # Load GT if available
        gt_binary = None
        if gt_dir is not None:
            gt_binary = load_gt_raster(gt_dir, map_stem, label)

        # Compute metrics
        if gt_binary is not None:
            # Ensure same shape
            if gt_binary.shape != pred_binary.shape:
                logger.warning("  Shape mismatch: GT %s vs pred %s — resizing GT",
                               gt_binary.shape, pred_binary.shape)
                gt_img = Image.fromarray(gt_binary * 255)
                gt_img = gt_img.resize((pred_binary.shape[1], pred_binary.shape[0]),
                                        Image.NEAREST)
                gt_binary = (np.array(gt_img) > 0).astype(np.uint8)

            metrics = compute_metrics(pred_binary, gt_binary)
        else:
            metrics = {
                "iou": None, "dice": None, "f1": None,
                "precision": None, "recall": None,
                "tp": None, "fp": None, "fn": None, "tn": None,
                "gt_positive_frac": None,
                "pred_positive_frac": float(np.mean(pred_binary)),
            }

        result = {
            "map": map_stem,
            "label": label,
            "map_w": w,
            "map_h": h,
            **metrics,
        }
        results.append(result)

        if metrics.get("f1") is not None:
            logger.info("    F1=%.4f  IoU=%.4f  Prec=%.4f  Rec=%.4f",
                         metrics["f1"], metrics["iou"],
                         metrics["precision"], metrics["recall"])

        # Save visualization
        if do_save_viz and viz_dir is not None:
            viz_path = viz_dir / map_stem / f"{label}.png"
            save_viz(map_array, pattern_img, gt_binary, pred_binary,
                     metrics, viz_path)

    return results


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_results(all_results: list[dict]) -> dict:
    """Compute aggregate statistics over all per-feature results."""
    # Filter to results with GT
    with_gt = [r for r in all_results if r["f1"] is not None]

    if not with_gt:
        return {
            "total_features": len(all_results),
            "features_with_gt": 0,
            "note": "No ground truth available for any features",
        }

    metric_keys = ["iou", "dice", "f1", "precision", "recall"]
    stats = {}
    for key in metric_keys:
        values = [r[key] for r in with_gt]
        stats[key] = {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }

    return {
        "total_features": len(all_results),
        "features_with_gt": len(with_gt),
        "unique_maps": len({r["map"] for r in all_results}),
        "metrics": stats,
    }


def format_summary(agg: dict, all_results: list[dict]) -> str:
    """Format a console-friendly summary."""
    lines = []
    lines.append("=" * 70)
    lines.append("USGS AI4CMA Evaluation Results")
    lines.append("=" * 70)
    lines.append(f"Total features evaluated:  {agg['total_features']}")
    lines.append(f"Features with ground truth: {agg.get('features_with_gt', 0)}")
    lines.append(f"Unique maps:               {agg.get('unique_maps', 0)}")
    lines.append("")

    if "metrics" in agg:
        lines.append(f"{'Metric':<12} {'Mean':>8} {'Median':>8} {'Std':>8} {'Min':>8} {'Max':>8}")
        lines.append("-" * 60)
        for key in ["f1", "iou", "dice", "precision", "recall"]:
            s = agg["metrics"][key]
            lines.append(
                f"{key:<12} {s['mean']:>8.4f} {s['median']:>8.4f} "
                f"{s['std']:>8.4f} {s['min']:>8.4f} {s['max']:>8.4f}"
            )
        lines.append("")
        lines.append("Comparison: LOAM (SIGSPATIAL '23) median F1 = 0.809")
        lines.append(f"            Ours                  median F1 = {agg['metrics']['f1']['median']:.3f}")
        lines.append("")
        lines.append("Note: LOAM uses pixel-weighted F1 (easy/hard); we report unweighted F1.")
    else:
        lines.append(agg.get("note", "No metrics computed."))

    lines.append("=" * 70)

    # Per-map breakdown (top/bottom 5 by F1)
    with_gt = [r for r in all_results if r["f1"] is not None]
    if with_gt:
        sorted_by_f1 = sorted(with_gt, key=lambda r: r["f1"], reverse=True)
        lines.append("")
        lines.append("Top 5 features by F1:")
        for r in sorted_by_f1[:5]:
            lines.append(f"  {r['map']}/{r['label']}: F1={r['f1']:.4f} IoU={r['iou']:.4f}")
        lines.append("")
        lines.append("Bottom 5 features by F1:")
        for r in sorted_by_f1[-5:]:
            lines.append(f"  {r['map']}/{r['label']}: F1={r['f1']:.4f} IoU={r['iou']:.4f}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate zone segmentation on USGS AI4CMA data"
    )
    parser.add_argument("--checkpoint", required=True,
                        help="Path to model checkpoint (.pt)")
    parser.add_argument("--usgs-dir", default="usgs/",
                        help="Directory containing USGS archives")
    parser.add_argument("--dataset", default="validation",
                        choices=["validation", "evaluation"],
                        help="Which dataset split to evaluate")
    parser.add_argument("--work-dir", default="/tmp/usgs_eval/",
                        help="Directory to extract archives into")
    parser.add_argument("--output-dir", default="results/usgs_eval/",
                        help="Directory for results output")
    parser.add_argument("--tile-size", type=int, default=512,
                        help="Tile size for inference (default: 512)")
    parser.add_argument("--tile-overlap", type=int, default=128,
                        help="Overlap between tiles (default: 128)")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Binarization threshold (default: 0.5)")
    parser.add_argument("--device", default=_pick_device(),
                        help="Device for inference")
    parser.add_argument("--no-tile", action="store_true",
                        help="Downsample whole map instead of tiling (faster, lower quality)")
    parser.add_argument("--no-clean-pattern", action="store_true",
                        help="Skip legend swatch cleaning (use raw crops with text/borders)")
    parser.add_argument("--save-viz", action="store_true",
                        help="Save visualization panels for each feature")
    parser.add_argument("--model-type", default="resnet",
                        choices=["resnet", "vanilla"],
                        help="Model architecture (default: resnet)")
    parser.add_argument("--skip-no-gt", action="store_true",
                        help="Skip maps that have no ground truth rasters (faster)")
    parser.add_argument("--max-maps", type=int, default=0,
                        help="Max maps to process (0 = all)")
    parser.add_argument("--batch-size", type=int, default=4,
                        help="Tile inference batch size (default: 4; lower = less VRAM)")
    parser.add_argument("--exclude-maps", nargs="+", default=[],
                        help="Map stems to skip (used for fine-tune held-out eval)")
    parser.add_argument("--no-wandb", action="store_true",
                        help="Disable W&B even if WANDB_API_KEY is set")
    parser.add_argument("--wandb-project", default="spatially-zone-segmentation")
    parser.add_argument("--wandb-run-name", default=None,
                        help="W&B run name (auto-generated from checkpoint+output-dir if omitted)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    usgs_dir = Path(args.usgs_dir)
    work_dir = Path(args.work_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 0. Optional W&B init — captures config + per-map metrics + final summary
    wandb_run = None
    has_key = bool(os.environ.get("WANDB_API_KEY"))
    use_wandb = (not args.no_wandb) and has_key
    if use_wandb:
        try:
            import wandb
            from datetime import datetime as _dt
            run_name = args.wandb_run_name or (
                f"eval-{Path(args.checkpoint).parent.name}-{Path(args.checkpoint).stem}-"
                f"{_dt.now().strftime('%Y%m%d-%H%M%S')}"
            )
            wandb_run = wandb.init(
                project=args.wandb_project,
                name=run_name,
                config={
                    "task": "eval_usgs",
                    "checkpoint": str(args.checkpoint),
                    "dataset": args.dataset,
                    "tile_size": args.tile_size,
                    "tile_overlap": args.tile_overlap,
                    "threshold": args.threshold,
                    "model_type": args.model_type,
                    "no_tile": args.no_tile,
                    "no_clean_pattern": args.no_clean_pattern,
                    "skip_no_gt": args.skip_no_gt,
                    "exclude_maps": list(args.exclude_maps),
                    "max_maps": args.max_maps,
                    "batch_size": args.batch_size,
                    "output_dir": str(args.output_dir),
                },
            )
            logger.info("W&B run: %s (project=%s)", wandb_run.name, args.wandb_project)
        except ImportError:
            logger.warning("wandb not installed — file-only logging")
        except Exception as exc:
            logger.warning("wandb init failed (%s) — file-only logging", exc)
    elif args.no_wandb:
        logger.info("W&B disabled by --no-wandb")
    elif not has_key:
        logger.info("WANDB_API_KEY not set — file-only logging")

    # 1. Extract data
    logger.info("Extracting dataset '%s' ...", args.dataset)
    map_dir, json_dir, gt_dir = extract_dataset(usgs_dir, args.dataset, work_dir)

    if not gt_dir.exists():
        logger.warning("GT directory %s not found — metrics will be unavailable", gt_dir)
        gt_dir = None

    # 2. Load model
    logger.info("Loading model from %s on %s", args.checkpoint, args.device)
    segmenter = TiledSegmenter(
        checkpoint=args.checkpoint,
        device=args.device,
        tile_size=args.tile_size,
        model_type=args.model_type,
    )

    # 3. Discover maps with JSON annotations
    json_files = sorted(json_dir.glob("*.json"))
    logger.info("Found %d JSON annotation files", len(json_files))

    if args.exclude_maps:
        excluded = set(args.exclude_maps)
        before = len(json_files)
        json_files = [j for j in json_files if j.stem not in excluded]
        logger.info("Excluded %d maps (%s) — %d remain",
                    before - len(json_files), ", ".join(sorted(excluded)), len(json_files))

    if args.max_maps > 0:
        json_files = json_files[:args.max_maps]
        logger.info("Limiting to %d maps", args.max_maps)

    # 4. Evaluate each map (with incremental saving and resume support)
    all_results = []
    viz_dir = output_dir / "viz" if args.save_viz else None
    results_path = output_dir / "results.json"
    summary_path = output_dir / "summary.txt"

    # Resume: load previously completed results and skip those maps
    completed_maps = set()
    if results_path.exists():
        try:
            with open(results_path) as f:
                prev = json.load(f)
            prev_results = prev.get("per_feature", [])
            if prev_results:
                all_results.extend(prev_results)
                completed_maps = {r["map"] for r in prev_results}
                logger.info(
                    "Resumed %d previous results from %d maps: %s",
                    len(prev_results), len(completed_maps),
                    ", ".join(sorted(completed_maps)),
                )
        except (json.JSONDecodeError, KeyError):
            logger.warning("Could not parse existing results.json — starting fresh")

    for json_path in tqdm(json_files, desc="Maps"):
        map_stem = json_path.stem

        # Skip already-completed maps (resume support)
        if map_stem in completed_maps:
            logger.info("Skipping %s (already completed in previous run)", map_stem)
            continue

        # Find corresponding TIF
        map_path = map_dir / f"{map_stem}.tif"
        if not map_path.exists():
            logger.warning("Map TIF not found: %s — skipping", map_path)
            continue

        # Get poly features from JSON
        features = get_poly_features(json_path)
        if not features:
            logger.info("No _poly features in %s — skipping", json_path.name)
            continue

        # Optionally skip maps without GT rasters
        if args.skip_no_gt and gt_dir is not None:
            has_any_gt = any(
                (gt_dir / f"{map_stem}_{f['label']}.tif").exists()
                for f in features
            )
            if not has_any_gt:
                logger.info("No GT rasters for %s — skipping (--skip-no-gt)", map_stem)
                continue

        logger.info("Processing %s (%d poly features)", map_stem, len(features))

        results = evaluate_map(
            segmenter=segmenter,
            map_path=map_path,
            features=features,
            gt_dir=gt_dir,
            tile_size=args.tile_size,
            tile_overlap=args.tile_overlap,
            threshold=args.threshold,
            no_tile=args.no_tile,
            clean_pattern=not args.no_clean_pattern,
            do_save_viz=args.save_viz,
            viz_dir=viz_dir,
            batch_size=args.batch_size,
        )
        all_results.extend(results)

        # Incremental save after each map so progress is not lost
        agg = aggregate_results(all_results)
        with open(results_path, "w") as f:
            json.dump({"summary": agg, "per_feature": all_results}, f, indent=2)
        logger.info("Saved incremental results (%d features so far)", len(all_results))

        # Log per-map summary to wandb (incremental, so progress is visible live)
        if wandb_run is not None:
            try:
                f1s = [r["f1"] for r in results if r.get("f1") is not None]
                if f1s:
                    wandb_run.log({
                        f"per_map/{map_stem}/mean_f1": float(np.mean(f1s)),
                        f"per_map/{map_stem}/median_f1": float(np.median(f1s)),
                        f"per_map/{map_stem}/n_features": len(f1s),
                        "running/maps_completed": len({r["map"] for r in all_results}),
                        "running/features_total": len(all_results),
                        "running/mean_f1": float(np.mean(
                            [r["f1"] for r in all_results if r.get("f1") is not None]
                        )),
                        "running/median_f1": float(np.median(
                            [r["f1"] for r in all_results if r.get("f1") is not None]
                        )),
                    })
            except Exception as exc:
                logger.warning("wandb per-map log failed: %s", exc)

    # 5. Final aggregate and save
    agg = aggregate_results(all_results)
    summary_text = format_summary(agg, all_results)

    print("\n" + summary_text)

    # Save final results
    with open(results_path, "w") as f:
        json.dump({"summary": agg, "per_feature": all_results}, f, indent=2)
    logger.info("Detailed results saved to %s", results_path)

    # Save summary
    with open(summary_path, "w") as f:
        f.write(summary_text)
    logger.info("Summary saved to %s", summary_path)

    # 6. Final wandb summary + artifact upload (durable cloud-side record)
    if wandb_run is not None:
        try:
            metrics = agg.get("metrics", {})
            wandb_run.summary["total_features"] = agg.get("total_features", 0)
            wandb_run.summary["features_with_gt"] = agg.get("features_with_gt", 0)
            wandb_run.summary["unique_maps"] = agg.get("unique_maps", 0)
            for metric_name in ("f1", "iou", "dice", "precision", "recall"):
                stats = metrics.get(metric_name, {})
                for stat in ("mean", "median", "std", "min", "max"):
                    if stat in stats and stats[stat] is not None:
                        wandb_run.summary[f"{metric_name}_{stat}"] = stats[stat]

            import wandb as _wb
            artifact = _wb.Artifact(
                name=f"eval-results-{Path(args.output_dir).name}",
                type="evaluation",
                description=f"USGS eval of {args.checkpoint} (excluded={args.exclude_maps})",
            )
            artifact.add_file(str(results_path))
            artifact.add_file(str(summary_path))
            wandb_run.log_artifact(artifact)
            logger.info("Logged eval artifact to W&B")
            wandb_run.finish()
        except Exception as exc:
            logger.warning("wandb final upload failed: %s", exc)


if __name__ == "__main__":
    main()
