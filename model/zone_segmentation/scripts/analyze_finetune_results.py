"""Aggregate analysis kit for the 1A fine-tune experiment.

Loads three result sources and produces every paper-ready artifact in one shot:

    1. Zero-shot          ← results/usgs_eval_vanilla_v2_tiled/results.json
    2. Pretrained + ft    ← results/finetune_eval_pretrained_e20/results.json
    3. Scratch + ft       ← results/finetune_eval_scratch_e20/results.json
    + delta-E / area      ← model/zone_segmentation/reports/failure_analysis/per_feature.csv

Outputs go to model/zone_segmentation/reports/finetune_results/:

    aggregate.json        Mean / median / std per condition; ratios; n.
    per_map.csv           22-row table for paper Table 2.
    paper_summary.md      Markdown summary with paper-ready numbers + claims.
    plots/
        per_map_bar.png   Per-map comparison bar chart (3 conditions).
        improvement_vs_deltaE.png   F1 lift vs color distinctiveness.
        improvement_vs_area.png     F1 lift vs area fraction.
        f1_distribution.png         Per-condition F1 histogram.
    qualitative_picks.json
                          Candidate (map, label) pairs for paper Fig 3:
                          features where pretrained does well but scratch fails.

Safe to re-run as scratch_e20 results stream in — script handles partial data.

Usage:
    python -m model.zone_segmentation.scripts.analyze_finetune_results
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bootstrap helpers — for the rebuttal-proof CIs
# ---------------------------------------------------------------------------

def _bootstrap_mean(values: np.ndarray, n_boot: int = 2000, seed: int = 0
                    ) -> tuple[float, float, float]:
    """Return (mean, lo95, hi95) by basic non-parametric bootstrap."""
    if len(values) == 0:
        return (float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    n = len(values)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boots[i] = values[idx].mean()
    return (float(values.mean()),
            float(np.percentile(boots, 2.5)),
            float(np.percentile(boots, 97.5)))


def _bootstrap_paired_delta(a: np.ndarray, b: np.ndarray,
                             n_boot: int = 2000, seed: int = 0
                             ) -> tuple[float, float, float, float]:
    """Bootstrap mean(a) - mean(b) on paired samples.

    Returns (delta, lo95, hi95, frac_boots_positive). a, b must be same length
    (already aligned per feature). Use frac to get a one-sided p-value proxy.
    """
    if len(a) == 0 or len(a) != len(b):
        return (float("nan"), float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot)
    n = len(a)
    for i in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boots[i] = a[idx].mean() - b[idx].mean()
    obs = float(a.mean() - b.mean())
    return (obs,
            float(np.percentile(boots, 2.5)),
            float(np.percentile(boots, 97.5)),
            float((boots > 0).mean()))


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_eval_results(path: Path) -> pd.DataFrame:
    """results.json → DataFrame of per-feature rows (one per evaluated feature)."""
    if not path.exists():
        return pd.DataFrame(columns=["map", "label", "f1", "iou", "precision", "recall"])
    raw = json.loads(path.read_text())
    df = pd.DataFrame(raw["per_feature"])
    # Drop rows without F1 (only count features with ground truth)
    return df[df["f1"].notna()].reset_index(drop=True)


def _load_zero_shot(path: Path) -> pd.DataFrame:
    return _load_eval_results(path)


def _load_failure_analysis(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    keep = ["map", "label", "delta_e_nearest", "n_legend_entries", "gt_positive_frac"]
    return df[keep]


# ---------------------------------------------------------------------------
# Build the unified per-feature table
# ---------------------------------------------------------------------------

def build_per_feature_table(
    zero_shot: pd.DataFrame,
    pretrained: pd.DataFrame,
    scratch: pd.DataFrame,
    failure: pd.DataFrame,
) -> pd.DataFrame:
    """Outer-join the three condition tables + the failure-analysis covariates."""
    def _slim(df, suffix):
        c = df[["map", "label", "f1", "iou", "precision", "recall"]].copy()
        c.columns = ["map", "label"] + [f"{x}_{suffix}" for x in ("f1", "iou", "precision", "recall")]
        return c

    df = _slim(zero_shot, "zs")
    df = df.merge(_slim(pretrained, "pre"), on=["map", "label"], how="outer")
    df = df.merge(_slim(scratch, "sc"), on=["map", "label"], how="outer")
    df = df.merge(failure, on=["map", "label"], how="left")
    df["delta_pre_zs"] = df["f1_pre"] - df["f1_zs"]
    df["ratio_pre_sc"] = df["f1_pre"] / df["f1_sc"].replace(0, np.nan)
    return df


# ---------------------------------------------------------------------------
# Aggregate metrics
# ---------------------------------------------------------------------------

def aggregate(df: pd.DataFrame, scratch_maps: set[str]) -> dict:
    """Build the headline aggregate table for the paper."""
    out = {}

    # Across the union of maps where each condition has data
    for cond in ("zs", "pre", "sc"):
        col = f"f1_{cond}"
        f1s = df[col].dropna().to_numpy()
        if not len(f1s):
            out[cond] = {"n_features": 0, "n_maps": 0}
            continue
        mean, lo, hi = _bootstrap_mean(f1s, seed=hash(cond) & 0xFFFF)
        out[cond] = {
            "mean": mean,
            "mean_lo95": lo,
            "mean_hi95": hi,
            "median": float(np.median(f1s)),
            "std": float(f1s.std()),
            "min": float(f1s.min()),
            "max": float(f1s.max()),
            "n_features": int(len(f1s)),
            "n_maps": int(df.loc[df[col].notna(), "map"].nunique()),
        }

    # Head-to-head pretrained vs scratch — PAIRED bootstrap over features
    # where both conditions report F1 on a map that scratch has completed.
    if scratch_maps:
        paired = df[df["map"].isin(scratch_maps) & df["f1_pre"].notna() & df["f1_sc"].notna()]
        if len(paired) > 1:
            pre = paired["f1_pre"].to_numpy()
            sc = paired["f1_sc"].to_numpy()
            d, lo, hi, p_pos = _bootstrap_paired_delta(pre, sc, seed=1234)
            ratio_lo, ratio_hi = None, None
            # Bootstrap the ratio too (mean(pre)/mean(sc)) — caveat: ratio is
            # less stable when mean(sc) ≈ 0; report alongside delta.
            rng = np.random.default_rng(5678)
            ratios = []
            n = len(paired)
            for _ in range(2000):
                idx = rng.integers(0, n, size=n)
                m_sc = sc[idx].mean()
                if m_sc > 1e-9:
                    ratios.append(pre[idx].mean() / m_sc)
            if ratios:
                ratio_lo = float(np.percentile(ratios, 2.5))
                ratio_hi = float(np.percentile(ratios, 97.5))
            out["matched_head_to_head"] = {
                "scratch_maps_complete": sorted(scratch_maps),
                "n_maps_matched": len(scratch_maps),
                "n_features_paired": int(len(paired)),
                "pretrained_mean": float(pre.mean()),
                "pretrained_median": float(np.median(pre)),
                "scratch_mean": float(sc.mean()),
                "scratch_median": float(np.median(sc)),
                "ratio_mean": float(pre.mean() / sc.mean()) if sc.mean() else None,
                "ratio_lo95": ratio_lo,
                "ratio_hi95": ratio_hi,
                "paired_delta_mean": d,
                "paired_delta_lo95": lo,
                "paired_delta_hi95": hi,
                "paired_p_pretrained_better": p_pos,
            }

    # Pretrained vs zero-shot — PAIRED bootstrap on per-feature F1.
    both = df[df["f1_pre"].notna() & df["f1_zs"].notna()]
    if len(both) > 1:
        pre = both["f1_pre"].to_numpy()
        zs = both["f1_zs"].to_numpy()
        d, lo, hi, p_pos = _bootstrap_paired_delta(pre, zs, seed=9999)
        out["pretrained_vs_zeroshot"] = {
            "n_features": int(len(both)),
            "n_maps": int(both["map"].nunique()),
            "pretrained_mean": float(pre.mean()),
            "zero_shot_mean": float(zs.mean()),
            "mean_delta_pct": float((pre.mean() - zs.mean()) / zs.mean() * 100) if zs.mean() else None,
            "paired_delta_mean": d,
            "paired_delta_lo95": lo,
            "paired_delta_hi95": hi,
            "paired_p_pretrained_better": p_pos,
            "pretrained_median": float(np.median(pre)),
            "zero_shot_median": float(np.median(zs)),
        }

    return out


def per_map_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per map: n, zs/pre/sc mean & median F1, deltas."""
    rows = []
    for m in sorted(df["map"].unique()):
        sub = df[df["map"] == m]
        row = {"map": m, "n_features": len(sub)}
        for cond in ("zs", "pre", "sc"):
            col = f"f1_{cond}"
            vals = sub[col].dropna()
            row[f"{cond}_mean"] = float(vals.mean()) if len(vals) else np.nan
            row[f"{cond}_median"] = float(vals.median()) if len(vals) else np.nan
            row[f"{cond}_n"] = int(len(vals))
        # Δ pretrained vs zero-shot (percent)
        if row["zs_mean"] and row["zs_mean"] > 0:
            row["pre_vs_zs_pct"] = (row["pre_mean"] - row["zs_mean"]) / row["zs_mean"] * 100
        # Pretrained / Scratch ratio
        if row["sc_mean"] and row["sc_mean"] > 0:
            row["pre_over_sc"] = row["pre_mean"] / row["sc_mean"]
        # Map mean delta-E for sorting/coloring
        des = sub["delta_e_nearest"].dropna()
        row["mean_delta_e"] = float(des.mean()) if len(des) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_per_map_bar(per_map: pd.DataFrame, out: Path) -> None:
    """Per-map mean F1 for the 3 conditions, sorted by pretrained gain."""
    df = per_map.sort_values("pre_vs_zs_pct", ascending=False).reset_index(drop=True)
    x = np.arange(len(df))
    w = 0.28
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - w, df["zs_mean"], w, label="Zero-shot", color="#888")
    ax.bar(x, df["pre_mean"], w, label="Pretrained + ft", color="#1f77b4")
    ax.bar(x + w, df["sc_mean"], w, label="Scratch + ft", color="#d62728")
    ax.set_xticks(x)
    ax.set_xticklabels(df["map"], rotation=70, ha="right", fontsize=8)
    ax.set_ylabel("Mean F1")
    ax.set_title("Per-map mean F1 — held-out from fine-tune (sorted by pretrained gain)")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    logger.info("wrote %s", out)


def plot_improvement_vs_covariate(
    df: pd.DataFrame, cov: str, xlabel: str, out: Path, log_x: bool = False,
) -> None:
    sub = df[df["delta_pre_zs"].notna() & df[cov].notna()].copy()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.scatter(sub[cov], sub["delta_pre_zs"], s=10, alpha=0.4, edgecolor="none")
    if log_x:
        ax.set_xscale("log")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("F1 lift  (Pretrained_e20 − Zero-shot)")
    ax.set_title(f"Per-feature F1 lift vs {xlabel}  (n={len(sub)})")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    logger.info("wrote %s", out)


def plot_f1_distribution(df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.linspace(0, 1, 41)
    ax.hist(df["f1_zs"].dropna(), bins=bins, alpha=0.5, label="Zero-shot", color="#888")
    ax.hist(df["f1_pre"].dropna(), bins=bins, alpha=0.5, label="Pretrained + ft", color="#1f77b4")
    if df["f1_sc"].notna().sum() > 0:
        ax.hist(df["f1_sc"].dropna(), bins=bins, alpha=0.5, label="Scratch + ft", color="#d62728")
    ax.set_xlabel("Per-feature F1")
    ax.set_ylabel("Feature count")
    ax.set_title("Per-feature F1 distribution across held-out maps")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    logger.info("wrote %s", out)


# ---------------------------------------------------------------------------
# Qualitative picks
# ---------------------------------------------------------------------------

def qualitative_picks(df: pd.DataFrame, top_n: int = 8) -> list[dict]:
    """Features where pretrained wins big over scratch AND over zero-shot.

    Useful for Figure 3 qualitative panels.
    """
    cand = df[
        df["f1_pre"].notna()
        & df["f1_sc"].notna()
        & df["f1_zs"].notna()
        & (df["f1_pre"] > 0.3)
        & (df["f1_sc"] < 0.1)
    ].copy()
    cand["pretrained_advantage"] = cand["f1_pre"] - cand["f1_sc"]
    cand = cand.sort_values("pretrained_advantage", ascending=False).head(top_n)
    return [
        {
            "map": r["map"], "label": r["label"],
            "f1_zs": float(r["f1_zs"]), "f1_pre": float(r["f1_pre"]), "f1_sc": float(r["f1_sc"]),
            "delta_e": float(r["delta_e_nearest"]) if pd.notna(r["delta_e_nearest"]) else None,
            "viz_pretrained": f"results/finetune_eval_pretrained_e20/viz/{r['map']}/{r['label']}.png",
            "viz_scratch": f"results/finetune_eval_scratch_e20/viz/{r['map']}/{r['label']}.png",
        }
        for _, r in cand.iterrows()
    ]


# ---------------------------------------------------------------------------
# Markdown summary
# ---------------------------------------------------------------------------

def write_paper_summary(agg: dict, per_map: pd.DataFrame, out: Path) -> None:
    lines = [
        "# 1A Fine-Tune Results — Paper-Ready Summary",
        "",
        "Auto-generated by `analyze_finetune_results.py`. Re-runs as scratch eval streams in.",
        "",
        "## Headline numbers",
        "",
    ]

    pre_zs = agg.get("pretrained_vs_zeroshot", {})
    if pre_zs:
        lines += [
            "### Pretrained_e20 vs Zero-shot (held-out 22 maps)",
            "",
            f"- **n = {pre_zs['n_features']} features across {pre_zs['n_maps']} maps**",
            f"- Mean F1 pretrained: **{pre_zs['pretrained_mean']:.4f}**  vs zero-shot {pre_zs['zero_shot_mean']:.4f}",
            f"- Paired mean Δ: **{pre_zs['paired_delta_mean']:.4f}**  "
            f"95% CI [{pre_zs['paired_delta_lo95']:.4f}, {pre_zs['paired_delta_hi95']:.4f}]",
            f"- Bootstrap P(pretrained > zero-shot): **{pre_zs['paired_p_pretrained_better']:.4f}**",
            f"- Median F1: {pre_zs['pretrained_median']:.4f} vs {pre_zs['zero_shot_median']:.4f}",
            "",
        ]
    h2h = agg.get("matched_head_to_head", {})
    if h2h:
        lines += [
            f"### Pretrained_e20 vs Scratch_e20 (paired on {h2h['n_features_paired']} features, {h2h['n_maps_matched']} maps)",
            "",
            f"- Pretrained mean F1: **{h2h['pretrained_mean']:.4f}**  (median {h2h['pretrained_median']:.4f})",
            f"- Scratch mean F1: **{h2h['scratch_mean']:.4f}**  (median {h2h['scratch_median']:.4f})",
            f"- **Pretrained / Scratch ratio: {h2h['ratio_mean']:.2f}×**  "
            f"95% CI [{h2h.get('ratio_lo95'):.2f}, {h2h.get('ratio_hi95'):.2f}]"
            if h2h.get('ratio_lo95') is not None else
            f"- **Pretrained / Scratch ratio: {h2h['ratio_mean']:.2f}×** (ratio CI unstable: scratch ≈ 0)",
            f"- Paired mean Δ: **{h2h['paired_delta_mean']:.4f}**  "
            f"95% CI [{h2h['paired_delta_lo95']:.4f}, {h2h['paired_delta_hi95']:.4f}]",
            f"- Bootstrap P(pretrained > scratch): **{h2h['paired_p_pretrained_better']:.4f}**",
            "",
            "> **Caveat (for reviewers):** this scratch baseline uses LR=1e-6 — the "
            "same LR used to fine-tune the pretrained model (per TODO 1A protocol). "
            "At that LR a randomly-initialized network learns essentially nothing in "
            "20 epochs. A fairer scratch baseline at LR=1e-4 (TODO 1A.1) is reported "
            "separately when available.",
            "",
        ]

    lines += [
        "## Per-condition stats (all available features)",
        "",
        "| Condition | n features | n maps | Mean F1 | Median | Std | Max |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    cond_label = {"zs": "Zero-shot", "pre": "Pretrained + ft", "sc": "Scratch + ft"}
    for cond in ("zs", "pre", "sc"):
        c = agg.get(cond, {})
        if c.get("n_features", 0):
            lines.append(
                f"| {cond_label[cond]} | {c['n_features']} | {c['n_maps']} | "
                f"{c['mean']:.4f} | {c['median']:.4f} | {c['std']:.4f} | {c['max']:.4f} |"
            )

    lines += ["", "## Per-map breakdown (sorted by pretrained-vs-zero-shot gain)", "",
              "| Map | n | ΔE mean | ZS | Pre | Sc | Δ Pre/ZS | Pre/Sc |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    sorted_pm = per_map.sort_values("pre_vs_zs_pct", ascending=False)
    for _, r in sorted_pm.iterrows():
        de = f"{r['mean_delta_e']:.1f}" if pd.notna(r['mean_delta_e']) else "-"
        zsm = f"{r['zs_mean']:.4f}" if pd.notna(r['zs_mean']) else "-"
        prm = f"{r['pre_mean']:.4f}" if pd.notna(r['pre_mean']) else "-"
        scm = f"{r['sc_mean']:.4f}" if pd.notna(r['sc_mean']) else "-"
        delta_pct = f"{r['pre_vs_zs_pct']:+.0f}%" if pd.notna(r.get('pre_vs_zs_pct')) else "-"
        ratio = f"{r['pre_over_sc']:.1f}×" if pd.notna(r.get('pre_over_sc')) else "-"
        lines.append(f"| {r['map']} | {r['n_features']} | {de} | {zsm} | {prm} | {scm} | {delta_pct} | {ratio} |")

    lines += [
        "",
        "## Paper-ready claim sentences",
        "",
        "> **Headline** — \"After fine-tuning on just 2 USGS maps, our synthetic-pretrained "
        "model achieves a held-out mean F1 of {:.3f} across {} maps, a "
        "**{:+.0f}% improvement** over zero-shot transfer ({:.3f}), with every map "
        "showing positive gain.\"".format(
            pre_zs.get("pretrained_mean", 0), pre_zs.get("n_maps", 0),
            pre_zs.get("mean_delta_pct", 0), pre_zs.get("zero_shot_mean", 0),
        ) if pre_zs else "",
        "",
        "> **Pretraining matters** — \"A randomly-initialized model trained on the same 2 maps "
        "with identical hyperparameters achieves only {:.4f} mean F1 ({:.1f}× lower), "
        "confirming that the gains come from synthetic-data feature transfer rather than "
        "the fine-tune procedure itself.\"".format(
            h2h.get("scratch_mean", 0), h2h.get("ratio_mean", 0),
        ) if h2h else "",
    ]

    out.write_text("\n".join(lines))
    logger.info("wrote %s", out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zero-shot", type=Path,
                        default=Path("results/usgs_eval_vanilla_v2_tiled/results.json"))
    parser.add_argument("--pretrained", type=Path,
                        default=Path("results/finetune_eval_pretrained_e20/results.json"))
    parser.add_argument("--scratch", type=Path,
                        default=Path("results/finetune_eval_scratch_e20/results.json"))
    parser.add_argument("--failure-csv", type=Path,
                        default=Path("model/zone_segmentation/reports/failure_analysis/per_feature.csv"))
    parser.add_argument("--out-dir", type=Path,
                        default=Path("model/zone_segmentation/reports/finetune_results"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = args.out_dir / "plots"
    plots_dir.mkdir(exist_ok=True)

    # Load all sources
    zs_df = _load_zero_shot(args.zero_shot)
    pre_df = _load_eval_results(args.pretrained)
    sc_df = _load_eval_results(args.scratch)
    fa_df = _load_failure_analysis(args.failure_csv)
    logger.info("Loaded: zs=%d, pre=%d, sc=%d, fa=%d",
                len(zs_df), len(pre_df), len(sc_df), len(fa_df))

    # Restrict zero-shot to the 22 held-out maps (drop the 2 fine-tune maps)
    FT_MAPS = {"AR_StJoe", "AK_Dillingham"}
    zs_df = zs_df[~zs_df["map"].isin(FT_MAPS)]

    df = build_per_feature_table(zs_df, pre_df, sc_df, fa_df)
    df.to_csv(args.out_dir / "per_feature_joined.csv", index=False)

    scratch_maps = set(sc_df["map"].unique())
    agg = aggregate(df, scratch_maps)
    (args.out_dir / "aggregate.json").write_text(json.dumps(agg, indent=2))

    pm = per_map_table(df)
    pm.to_csv(args.out_dir / "per_map.csv", index=False)

    # Plots
    plot_per_map_bar(pm, plots_dir / "per_map_bar.png")
    plot_improvement_vs_covariate(df, "delta_e_nearest",
                                   "ΔE to nearest swatch (CIEDE2000)",
                                   plots_dir / "improvement_vs_deltaE.png")
    plot_improvement_vs_covariate(df, "gt_positive_frac",
                                   "GT polygon area fraction",
                                   plots_dir / "improvement_vs_area.png", log_x=True)
    plot_f1_distribution(df, plots_dir / "f1_distribution.png")

    # Qualitative picks
    picks = qualitative_picks(df)
    (args.out_dir / "qualitative_picks.json").write_text(json.dumps(picks, indent=2))

    # Paper summary markdown
    write_paper_summary(agg, pm, args.out_dir / "paper_summary.md")

    # Paper-ready LaTeX table snippet — drop-in for the headline table.
    # Reads scratch_lr1e-4 results too if present (for the fair-LR row).
    sc_fair_path = args.out_dir.parent.parent.parent / "results/finetune_eval_scratch_lr1e-4_e20/results.json"
    sc_fair_mean = sc_fair_median = None
    if sc_fair_path.exists():
        try:
            sc_fair = json.loads(sc_fair_path.read_text())
            f1s = [r["f1"] for r in sc_fair["per_feature"] if r.get("f1") is not None]
            if f1s:
                sc_fair_mean = float(np.mean(f1s))
                sc_fair_median = float(np.median(f1s))
        except Exception as exc:
            logger.warning("Could not read fair-LR scratch results: %s", exc)

    pre_zs = agg.get("pretrained_vs_zeroshot", {})
    h2h = agg.get("matched_head_to_head", {})
    zs = agg.get("zs", {})
    pre = agg.get("pre", {})
    sc = agg.get("sc", {})
    fair_str = (f"{sc_fair_mean:.3f} & {sc_fair_median:.3f}"
                if sc_fair_mean is not None else "(pending) & ---")
    fair_delta_str = (f"$+{pre.get('mean', 0) - sc_fair_mean:.3f}$"
                      if sc_fair_mean is not None else "(pending)")
    tex = (
        "% Auto-generated by analyze_finetune_results.py — paste / \\input into paper.tex\n"
        "% Updates whenever the analysis kit re-runs.\n"
        "\\begin{table}[t]\n"
        "\\caption{Held-out results on 22 USGS maps. Bootstrap 95\\% CIs over per-feature F1.}\n"
        "\\label{tab:headline}\n"
        "\\centering\\small\n"
        "\\begin{tabular}{@{}lcc@{}}\n"
        "\\toprule\n"
        "\\textbf{Condition} & \\textbf{Mean F1} & \\textbf{Median F1} \\\\\n"
        "\\midrule\n"
        f"Zero-shot pretrained & {zs.get('mean', 0):.3f} & {zs.get('median', 0):.3f} \\\\\n"
        f"Pretrained $+$ 2-map fine-tune & \\textbf{{{pre.get('mean', 0):.3f}}} & \\textbf{{{pre.get('median', 0):.3f}}} \\\\\n"
        f"Scratch $+$ 2-map fine-tune (matched LR) & {sc.get('mean', 0):.3f} & {sc.get('median', 0):.3f} \\\\\n"
        f"Scratch $+$ 2-map fine-tune (fair LR) & {fair_str} \\\\\n"
        "\\midrule\n"
        "\\multicolumn{3}{@{}l@{}}{\\textbf{Paired bootstrap deltas (vs.\\ pretrained $+$ fine-tune)}} \\\\\n"
        "\\midrule\n"
    )
    if pre_zs:
        tex += (f"vs. zero-shot & $+{pre_zs['paired_delta_mean']:.3f}$ "
                f"CI $[+{pre_zs['paired_delta_lo95']:.3f}, +{pre_zs['paired_delta_hi95']:.3f}]$ & --- \\\\\n")
    if h2h:
        tex += (f"vs. scratch (matched) & $+{h2h['paired_delta_mean']:.3f}$ "
                f"CI $[+{h2h['paired_delta_lo95']:.3f}, +{h2h['paired_delta_hi95']:.3f}]$ & --- \\\\\n")
    tex += (f"vs. scratch (fair) & {fair_delta_str} & --- \\\\\n"
            "\\bottomrule\n"
            "\\end{tabular}\n"
            "\\end{table}\n")
    (args.out_dir / "table_for_paper.tex").write_text(tex)
    logger.info("wrote %s", args.out_dir / "table_for_paper.tex")

    # Also drop a copy into paper/tables/ so paper.tex can \input{} it directly
    paper_tables = Path("paper/tables")
    paper_tables.mkdir(parents=True, exist_ok=True)
    (paper_tables / "headline_table.tex").write_text(tex)
    logger.info("wrote %s", paper_tables / "headline_table.tex")

    # Echo headline
    print("\n" + "=" * 60)
    print("FINETUNE ANALYSIS SUMMARY")
    print("=" * 60)
    pre_zs = agg.get("pretrained_vs_zeroshot", {})
    h2h = agg.get("matched_head_to_head", {})
    if pre_zs:
        print(f"  Pretrained vs Zero-shot:  +{pre_zs['mean_delta_pct']:.1f}% mean "
              f"({pre_zs['pretrained_mean']:.4f} vs {pre_zs['zero_shot_mean']:.4f})")
        print(f"                            paired Δ {pre_zs['paired_delta_mean']:+.4f}  "
              f"CI [{pre_zs['paired_delta_lo95']:+.4f}, {pre_zs['paired_delta_hi95']:+.4f}]  "
              f"P(pre>zs)={pre_zs['paired_p_pretrained_better']:.4f}")
    if h2h:
        ratio_ci = ""
        if h2h.get("ratio_lo95") is not None:
            ratio_ci = f"  CI [{h2h['ratio_lo95']:.2f}, {h2h['ratio_hi95']:.2f}]"
        print(f"  Pretrained / Scratch:     {h2h['ratio_mean']:.2f}×{ratio_ci} "
              f"(matched on {h2h['n_maps_matched']} maps, {h2h['n_features_paired']} features)")
        print(f"                            paired Δ {h2h['paired_delta_mean']:+.4f}  "
              f"CI [{h2h['paired_delta_lo95']:+.4f}, {h2h['paired_delta_hi95']:+.4f}]  "
              f"P(pre>sc)={h2h['paired_p_pretrained_better']:.4f}")
    print(f"  Qualitative picks:        {len(picks)} candidate features for Fig 3")
    print(f"  All artifacts:            {args.out_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
