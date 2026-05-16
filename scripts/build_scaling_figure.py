"""Build paper/figures/scaling_curve.png from the scaling-curve eval results.

Reads all available eval result dirs and plots mean F1 vs N fine-tune maps,
plus LOAM's reported median F1 0.809 (at N=14) as a horizontal reference.

Inputs (skipped if missing — handles partial completion gracefully):
    N=0  results/usgs_eval_vanilla_v2_tiled/results.json
    N=1  results/finetune_eval_pretrained_N1_e20/results.json
    N=2  results/finetune_eval_pretrained_e20/results.json     (1A)
    N=5  results/finetune_eval_pretrained_N5_e20/results.json
    N=10 results/finetune_eval_pretrained_N10_e20/results.json

Output:
    paper/figures/scaling_curve.png

Also dumps a tex snippet:
    paper/tables/scaling_table.tex (one row per N with mean F1 + CI)

Run after each new N completes (the run_scaling_curve.ps1 watcher does this).

Usage:
    python scripts/build_scaling_figure.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


SETUPS = [
    (0,  "results/usgs_eval_vanilla_v2_tiled/results.json",       "Zero-shot",      None),
    (1,  "results/finetune_eval_pretrained_N1_e20/results.json",  "1 fine-tune map", ["AR_StJoe"]),
    (2,  "results/finetune_eval_pretrained_e20/results.json",     "2 fine-tune maps",
         ["AR_StJoe", "AK_Dillingham"]),
    (5,  "results/finetune_eval_pretrained_N5_e20/results.json",  "5 fine-tune maps",
         ["AR_StJoe", "AK_Dillingham", "AK_Hughes", "CA_Elsinore", "AZ_GrandCanyon"]),
    (10, "results/finetune_eval_pretrained_N10_e20/results.json", "10 fine-tune maps",
         ["AR_StJoe", "AK_Dillingham", "AK_Hughes", "CA_Elsinore", "AZ_GrandCanyon",
          "CA_MarbleCanyon", "AZ_PipeSpring", "NV_HiddenHills", "NM_Sunshine", "OR_Camas"]),
]

LOAM_F1 = 0.809  # one prior supervised number on this benchmark, for reference only
SHOW_LOAM = False  # set True to overlay; default off to keep focus on our curve

OUT_PNG = Path("paper/figures/scaling_curve.png")
OUT_TEX = Path("paper/tables/scaling_table.tex")


def _bootstrap_mean(values: np.ndarray, n_boot: int = 2000, seed: int = 0
                    ) -> tuple[float, float, float]:
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


def main():
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for (n, path, label, excluded) in SETUPS:
        p = Path(path)
        if not p.exists():
            print(f"  N={n}: MISSING {path}")
            continue
        d = json.loads(p.read_text())
        per = d["per_feature"]
        # For zero-shot the eval was on all 24 maps; we restrict to the same
        # held-out set the fine-tune evals use (drop maps in `excluded` if any)
        if excluded:
            per = [r for r in per if r["map"] not in excluded]
        f1s = np.array([r["f1"] for r in per if r.get("f1") is not None])
        mean, lo, hi = _bootstrap_mean(f1s, seed=n)
        rows.append((n, label, mean, lo, hi, len(f1s),
                     len(set(r["map"] for r in per if r.get("f1") is not None))))
        print(f"  N={n}: mean F1 {mean:.4f}  CI [{lo:.4f}, {hi:.4f}]  ({len(f1s)} features)")

    if not rows:
        print("No data — exiting")
        return

    # -- Plot --
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ns = [r[0] for r in rows]
    means = [r[2] for r in rows]
    lo = [r[3] for r in rows]
    hi = [r[4] for r in rows]
    err = [[m - l for m, l in zip(means, lo)], [h - m for m, h in zip(means, hi)]]

    ax.errorbar(ns, means, yerr=err, fmt="o-", capsize=4, color="#1f77b4",
                linewidth=2, markersize=8, label="Pretrained $+$ fine-tune (ours)")
    if SHOW_LOAM:
        ax.axhline(LOAM_F1, color="gray", linestyle=":", linewidth=1,
                   alpha=0.7,
                   label=f"Prior supervised reference: ${LOAM_F1}$ at $N{{=}}14$")

    # Annotate each point with its mean F1
    for n, mean in zip(ns, means):
        ax.annotate(f"{mean:.3f}", xy=(n, mean), xytext=(5, 5),
                    textcoords="offset points", fontsize=9)

    ax.set_xlabel("$N$ = number of USGS fine-tune maps")
    ax.set_ylabel("Held-out mean F1 (bootstrap 95\\% CI)")
    ax.set_title("Annotation-efficiency curve on DARPA CMA validation")
    ax.grid(True, alpha=0.3)
    ax.set_xticks(ns)
    ax.set_xlim(-0.5, max(ns) + 2)
    upper = max(means) * 1.4 if not SHOW_LOAM else max(LOAM_F1, max(means)) * 1.15
    ax.set_ylim(0, upper)
    ax.legend(loc="upper left", fontsize=9)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT_PNG}")

    # -- Tex table --
    tex_lines = [
        "% Auto-generated by scripts/build_scaling_figure.py",
        "\\begin{table}[t]",
        "\\caption{Annotation-efficiency curve. Mean F1 with bootstrap "
        "95\\% CI on the held-out maps after fine-tuning the synthetic-pretrained "
        "model on $N$ USGS maps.}",
        "\\label{tab:scaling}",
        "\\centering\\small",
        "\\begin{tabular}{@{}rcccc@{}}",
        "\\toprule",
        "$N$ & Held-out maps & $n$ features & Mean F1 & 95\\% CI \\\\",
        "\\midrule",
    ]
    for (n, label, mean, lo_v, hi_v, n_feat, n_maps) in rows:
        tex_lines.append(
            f"{n} & {n_maps} & {n_feat} & {mean:.4f} & $[{lo_v:.4f}, {hi_v:.4f}]$ \\\\"
        )
    tex_lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ]
    OUT_TEX.write_text("\n".join(tex_lines))
    print(f"wrote {OUT_TEX}")


if __name__ == "__main__":
    main()
