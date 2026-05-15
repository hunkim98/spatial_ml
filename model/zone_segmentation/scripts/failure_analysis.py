"""Per-feature failure analysis for the USGS evaluation.

Implements paper/TODO.md Priority 1B: turn "median F1 = 0.016" into "F1 succeeds
predictably under condition X" by correlating per-feature F1 with measurable
characteristics of each (map, swatch).

For each evaluated feature, computes:
    - F1, IoU, precision, recall            (from results.json)
    - gt_positive_frac (= polygon area)     (from results.json)
    - delta-E to nearest other swatch        (CIEDE2000, computed here)
    - n_legend_entries                       (count of poly features in same map)

Produces:
    reports/failure_analysis/
        per_feature.csv                  one row per feature with all attributes
        swatches_cache.json              cached swatch RGBs (so re-runs are fast)
        plots/
            f1_vs_deltaE.png             scatter
            f1_vs_area.png               scatter
            f1_by_n_keys.png             box plot
            f1_by_deltaE_bin.png         bar chart
        analysis.md                      written summary: correlations + tables

Usage:
    python -m model.zone_segmentation.scripts.failure_analysis \
        --results results/usgs_eval_vanilla_v2_tiled/results.json \
        --usgs-dir usgs --work-dir $env:TEMP/usgs_eval \
        --out-dir model/zone_segmentation/reports/failure_analysis
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy import stats
from skimage.color import deltaE_ciede2000, rgb2lab
from tqdm import tqdm

from .eval_usgs import (
    crop_legend_swatch,
    extract_dataset,
    get_poly_features,
    load_map_image,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Swatch caching
# ---------------------------------------------------------------------------

def _swatch_pil_to_rgb(pil: Image.Image) -> tuple[int, int, int]:
    """Mean RGB of the cleaned swatch crop."""
    arr = np.array(pil)
    if arr.size == 0:
        return (128, 128, 128)
    rgb = arr.reshape(-1, 3).mean(axis=0).round().astype(int)
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]))


def build_swatches_cache(
    map_names: list[str],
    map_dir: Path,
    json_dir: Path,
    cache_path: Path,
) -> dict[str, dict[str, list[int]]]:
    """For each map, compute one cleaned-swatch RGB per poly feature. Cache to JSON.

    Returns dict {map_name: {label: [r,g,b]}}.
    """
    if cache_path.exists():
        logger.info("Loading swatches cache from %s", cache_path)
        return json.loads(cache_path.read_text())

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache: dict[str, dict[str, list[int]]] = {}
    missing_tifs: list[str] = []

    for name in tqdm(map_names, desc="Cache swatches"):
        tif = map_dir / f"{name}.tif"
        jsn = json_dir / f"{name}.json"
        if not tif.exists():
            missing_tifs.append(name)
            continue
        if not jsn.exists():
            logger.warning("Missing JSON: %s", jsn)
            continue

        try:
            map_arr = load_map_image(tif)
        except Exception as exc:
            logger.warning("Failed to load %s: %s", tif, exc)
            continue

        features = get_poly_features(jsn)
        per_label: dict[str, list[int]] = {}
        for f in features:
            try:
                pil = crop_legend_swatch(map_arr, f["bbox"], clean=True)
                per_label[f["label"]] = list(_swatch_pil_to_rgb(pil))
            except Exception as exc:
                logger.warning("Swatch fail %s/%s: %s", name, f["label"], exc)
        cache[name] = per_label

    if missing_tifs:
        logger.warning("Missing TIFs (skipped): %s", missing_tifs)

    cache_path.write_text(json.dumps(cache, indent=2))
    logger.info("Wrote swatches cache to %s (%d maps)", cache_path, len(cache))
    return cache


# ---------------------------------------------------------------------------
# Delta-E
# ---------------------------------------------------------------------------

def _rgb_to_lab(rgb: tuple[int, int, int]) -> np.ndarray:
    """Single RGB triple → Lab via skimage. Returns shape (3,)."""
    arr = np.array([[list(rgb)]], dtype=np.uint8) / 255.0
    return rgb2lab(arr)[0, 0]


def nearest_deltaE(
    target_rgb: tuple[int, int, int],
    other_rgbs: list[tuple[int, int, int]],
) -> tuple[float, str | None]:
    """Min CIEDE2000 from target to any of the others.

    Returns (delta_e, idx_of_nearest_in_list).
    """
    if not other_rgbs:
        return (float("inf"), None)
    target_lab = _rgb_to_lab(target_rgb)
    others_lab = np.stack([_rgb_to_lab(c) for c in other_rgbs], axis=0)
    target_lab_b = np.broadcast_to(target_lab, others_lab.shape)
    deltas = deltaE_ciede2000(target_lab_b, others_lab)
    idx = int(np.argmin(deltas))
    return float(deltas[idx]), idx


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def _scatter(ax, x, y, xlabel, ylabel, title):
    ax.scatter(x, y, s=10, alpha=0.45, edgecolor="none")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)


def make_plots(df: pd.DataFrame, out_dir: Path) -> dict:
    """Create the four plots specified in TODO.md and return correlation summary."""
    out_dir.mkdir(parents=True, exist_ok=True)
    eval_df = df[df["f1"].notna() & df["delta_e_nearest"].notna()].copy()

    # 1. F1 vs delta-E
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    _scatter(ax, eval_df["delta_e_nearest"], eval_df["f1"],
             "CIEDE2000 to nearest other swatch", "F1",
             f"F1 vs Delta-E (n={len(eval_df)})")
    fig.tight_layout()
    fig.savefig(out_dir / "f1_vs_deltaE.png", dpi=120)
    plt.close(fig)

    # 2. F1 vs area
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    _scatter(ax, eval_df["gt_positive_frac"], eval_df["f1"],
             "GT polygon area fraction", "F1",
             f"F1 vs Area Fraction (n={len(eval_df)})")
    ax.set_xscale("log")
    fig.tight_layout()
    fig.savefig(out_dir / "f1_vs_area.png", dpi=120)
    plt.close(fig)

    # 3. Box plot: F1 by # legend entries (binned)
    bins = [0, 10, 20, 30, 50, 999]
    labels = ["1-10", "11-20", "21-30", "31-50", "51+"]
    eval_df["n_keys_bin"] = pd.cut(eval_df["n_legend_entries"],
                                    bins=bins, labels=labels, include_lowest=True)
    grouped = [eval_df[eval_df["n_keys_bin"] == lbl]["f1"].dropna() for lbl in labels]
    counts = [len(g) for g in grouped]
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.boxplot(grouped, tick_labels=[f"{l}\n(n={c})" for l, c in zip(labels, counts)])
    ax.set_xlabel("Number of legend entries in map")
    ax.set_ylabel("F1")
    ax.set_title("F1 distribution by legend size")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out_dir / "f1_by_n_keys.png", dpi=120)
    plt.close(fig)

    # 4. Bar: mean F1 by Delta-E bin
    de_bins = [0, 5, 10, 15, 20, 30, 50, 999]
    de_labels = ["<5", "5-10", "10-15", "15-20", "20-30", "30-50", "50+"]
    eval_df["delta_e_bin"] = pd.cut(eval_df["delta_e_nearest"],
                                     bins=de_bins, labels=de_labels, include_lowest=True)
    means = eval_df.groupby("delta_e_bin", observed=True)["f1"].mean()
    counts = eval_df.groupby("delta_e_bin", observed=True)["f1"].count()
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    bars = ax.bar(range(len(means)), means.values)
    ax.set_xticks(range(len(means)))
    ax.set_xticklabels([f"{lbl}\n(n={c})" for lbl, c in zip(means.index, counts.values)])
    ax.set_xlabel("CIEDE2000 to nearest other swatch (binned)")
    ax.set_ylabel("Mean F1")
    ax.set_title("Mean F1 by color-distinctiveness bin")
    ax.grid(True, alpha=0.3, axis="y")
    for b, v in zip(bars, means.values):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{v:.3f}",
                ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "f1_by_deltaE_bin.png", dpi=120)
    plt.close(fig)

    # Correlations
    pearson_de = stats.pearsonr(eval_df["delta_e_nearest"], eval_df["f1"])
    spearman_de = stats.spearmanr(eval_df["delta_e_nearest"], eval_df["f1"])
    pearson_area = stats.pearsonr(np.log10(eval_df["gt_positive_frac"].clip(lower=1e-9)),
                                   eval_df["f1"])
    spearman_area = stats.spearmanr(eval_df["gt_positive_frac"], eval_df["f1"])

    high = eval_df[eval_df["delta_e_nearest"] > 30]["f1"]
    low = eval_df[eval_df["delta_e_nearest"] < 15]["f1"]

    return {
        "n_features_analyzed": len(eval_df),
        "pearson_f1_vs_deltaE": (pearson_de.statistic, pearson_de.pvalue),
        "spearman_f1_vs_deltaE": (spearman_de.statistic, spearman_de.pvalue),
        "pearson_f1_vs_log_area": (pearson_area.statistic, pearson_area.pvalue),
        "spearman_f1_vs_area": (spearman_area.statistic, spearman_area.pvalue),
        "mean_f1_high_deltaE": (float(high.mean()) if len(high) else None, len(high)),
        "mean_f1_low_deltaE": (float(low.mean()) if len(low) else None, len(low)),
        "median_f1_high_deltaE": (float(high.median()) if len(high) else None, len(high)),
        "median_f1_low_deltaE": (float(low.median()) if len(low) else None, len(low)),
    }


def write_report(df: pd.DataFrame, summary: dict, out_dir: Path) -> None:
    out = out_dir / "analysis.md"

    eval_df = df[df["f1"].notna()].copy()

    def _fmt_corr(r, p):
        return f"r={r:.3f}, p={p:.2e}"

    lines = [
        "# USGS Failure Analysis (Priority 1B)",
        "",
        f"**Source**: `results/usgs_eval_vanilla_v2_tiled/results.json`",
        f"**Total features evaluated**: {len(df)}",
        f"**Features used in analysis** (with delta-E + F1): {summary['n_features_analyzed']}",
        "",
        "## Headline correlations",
        "",
        "| Predictor | Pearson | Spearman |",
        "|---|---|---|",
        f"| Delta-E to nearest swatch | {_fmt_corr(*summary['pearson_f1_vs_deltaE'])} | {_fmt_corr(*summary['spearman_f1_vs_deltaE'])} |",
        f"| log10(area fraction) | {_fmt_corr(*summary['pearson_f1_vs_log_area'])} | {_fmt_corr(*summary['spearman_f1_vs_area'])} |",
        "",
        "## Distinctiveness gating",
        "",
        f"| Subset | n | Mean F1 | Median F1 |",
        f"|---|---:|---:|---:|",
        f"| Delta-E < 15 (confusable) | {summary['mean_f1_low_deltaE'][1]} | {summary['mean_f1_low_deltaE'][0]:.4f} | {summary['median_f1_low_deltaE'][0]:.4f} |",
        f"| Delta-E > 30 (distinctive) | {summary['mean_f1_high_deltaE'][1]} | {summary['mean_f1_high_deltaE'][0]:.4f} | {summary['median_f1_high_deltaE'][0]:.4f} |",
        "",
        "## Top 10 features by F1",
        "",
        "| map | label | F1 | delta-E | area_frac | n_keys |",
        "|---|---|---:|---:|---:|---:|",
    ]
    top = eval_df.sort_values("f1", ascending=False).head(10)
    for _, row in top.iterrows():
        lines.append(f"| {row['map']} | {row['label']} | {row['f1']:.3f} | "
                     f"{row.get('delta_e_nearest', float('nan')):.1f} | "
                     f"{row['gt_positive_frac']:.4f} | {int(row['n_legend_entries'])} |")

    lines += [
        "",
        "## Bottom 10 features by F1 (excluding F1=0)",
        "",
        "| map | label | F1 | delta-E | area_frac | n_keys |",
        "|---|---|---:|---:|---:|---:|",
    ]
    nonzero = eval_df[eval_df["f1"] > 0].sort_values("f1", ascending=True).head(10)
    for _, row in nonzero.iterrows():
        lines.append(f"| {row['map']} | {row['label']} | {row['f1']:.3f} | "
                     f"{row.get('delta_e_nearest', float('nan')):.1f} | "
                     f"{row['gt_positive_frac']:.4f} | {int(row['n_legend_entries'])} |")

    lines += [
        "",
        "## Plots",
        "",
        "- `plots/f1_vs_deltaE.png`",
        "- `plots/f1_vs_area.png`",
        "- `plots/f1_by_n_keys.png`",
        "- `plots/f1_by_deltaE_bin.png`",
        "",
        "## Per-feature CSV",
        "",
        "`per_feature.csv` has all rows for paper-ready tables.",
    ]

    out.write_text("\n".join(lines))
    logger.info("Wrote analysis report → %s", out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path,
                        default=Path("results/usgs_eval_vanilla_v2_tiled/results.json"))
    parser.add_argument("--usgs-dir", type=Path, default=Path("usgs"))
    parser.add_argument("--dataset", default="validation",
                        choices=["validation", "evaluation"])
    parser.add_argument("--work-dir", type=Path,
                        default=Path("C:/Users/piljo/AppData/Local/Temp/usgs_eval"))
    parser.add_argument("--out-dir", type=Path,
                        default=Path("model/zone_segmentation/reports/failure_analysis"))
    parser.add_argument("--force-recache", action="store_true",
                        help="Rebuild swatches_cache.json even if it exists")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = args.out_dir / "swatches_cache.json"
    if args.force_recache and cache_path.exists():
        cache_path.unlink()

    # 1. Load results
    raw = json.loads(args.results.read_text())
    per_feature = raw["per_feature"]
    df = pd.DataFrame(per_feature)
    map_names = sorted(df["map"].unique().tolist())
    logger.info("Loaded %d features across %d maps", len(df), len(map_names))

    # 2. Extract USGS data (idempotent — skips if already extracted)
    map_dir, json_dir, _ = extract_dataset(args.usgs_dir, args.dataset, args.work_dir)

    # 3. Build / load swatches cache
    swatches = build_swatches_cache(map_names, map_dir, json_dir, cache_path)

    # 4. Augment df with delta-E + n_legend_entries
    delta_es = []
    n_keys = []
    target_rgbs = []
    for _, row in df.iterrows():
        m, lbl = row["map"], row["label"]
        per_label = swatches.get(m, {})
        if not per_label or lbl not in per_label:
            delta_es.append(np.nan)
            n_keys.append(np.nan)
            target_rgbs.append(None)
            continue
        target = tuple(per_label[lbl])
        others = [tuple(v) for k, v in per_label.items() if k != lbl]
        de, _ = nearest_deltaE(target, others)
        delta_es.append(de)
        n_keys.append(len(per_label))
        target_rgbs.append(target)

    df["delta_e_nearest"] = delta_es
    df["n_legend_entries"] = n_keys
    df["target_rgb"] = [str(c) if c else "" for c in target_rgbs]

    # 5. Save CSV
    df.to_csv(args.out_dir / "per_feature.csv", index=False)
    logger.info("Wrote per_feature.csv (%d rows)", len(df))

    # 6. Plots + correlations
    plots_dir = args.out_dir / "plots"
    summary = make_plots(df, plots_dir)
    logger.info("Plots → %s", plots_dir)

    # 7. Report
    write_report(df, summary, args.out_dir)

    # 8. Echo headline numbers
    print("\n" + "=" * 60)
    print("FAILURE ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"  Features analyzed:          {summary['n_features_analyzed']}")
    print(f"  Pearson F1 vs delta-E:      r={summary['pearson_f1_vs_deltaE'][0]:.3f}  "
          f"p={summary['pearson_f1_vs_deltaE'][1]:.2e}")
    print(f"  Spearman F1 vs delta-E:     r={summary['spearman_f1_vs_deltaE'][0]:.3f}")
    print(f"  Pearson F1 vs log10(area):  r={summary['pearson_f1_vs_log_area'][0]:.3f}")
    print(f"  Mean F1 (delta-E < 15):     {summary['mean_f1_low_deltaE'][0]:.4f} (n={summary['mean_f1_low_deltaE'][1]})")
    print(f"  Mean F1 (delta-E > 30):     {summary['mean_f1_high_deltaE'][0]:.4f} (n={summary['mean_f1_high_deltaE'][1]})")
    print("=" * 60)


if __name__ == "__main__":
    main()
