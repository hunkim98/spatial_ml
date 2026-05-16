"""Generate a paper figure showing BOTH base-model pretraining on synthetic data
AND the three downstream fine-tune trajectories.

Output: paper/figures/training_curves.png

Left panel: base-model pretraining (40 epochs on synthetic) — train + val IoU/F1.
Right panel: three downstream fine-tunes (20 epochs each, USGS 2-map set).

Usage:
    python -m model.zone_segmentation.scripts.plot_training_curves
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


BASE_HIST = Path("checkpoints/zone_seg_loam_vanilla_v2/history.json")

FT_CONDITIONS = [
    ("checkpoints/finetune_pretrained/history.json", "Pretrained init, LR=1e-6", "#1f77b4", "-"),
    ("checkpoints/finetune_scratch/history.json", "Scratch init, matched LR=1e-6", "#d62728", "-"),
    ("checkpoints/finetune_scratch_lr1e-4/history.json", "Scratch init, fair LR=1e-4", "#ff7f0e", "--"),
]

OUT = Path("paper/figures/training_curves.png")


def main():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 3.8))

    # ----- Left: base-model pretraining on synthetic -----
    if BASE_HIST.exists():
        h = json.loads(BASE_HIST.read_text())
        ep = h["epoch"]
        axL.plot(ep, h["train_iou"], color="#2ca02c", label="Train IoU", linewidth=2)
        axL.plot(ep, h["val_iou"], color="#2ca02c", linestyle="--", label="Val IoU", linewidth=2)
        if "val_f1" in h:
            axL.plot(ep, h["val_f1"], color="#9467bd", linestyle=":", label="Val F1", linewidth=2)
        best_epoch = ep[h["val_iou"].index(max(h["val_iou"]))]
        axL.axvline(best_epoch, color="black", linestyle=":", linewidth=1)
        axL.text(best_epoch + 0.4, 0.05, f"best ckpt\nep {best_epoch}", fontsize=8, color="black")
    axL.set_xlabel("Epoch")
    axL.set_ylabel("Metric")
    axL.set_title("(a) Base-model pretraining on synthetic (40 ep)")
    axL.grid(True, alpha=0.3)
    axL.legend(loc="lower right", fontsize=9)
    axL.set_ylim(0, 0.75)

    # ----- Right: downstream fine-tunes (training F1 across 20 epochs) -----
    for path, label, color, ls in FT_CONDITIONS:
        p = Path(path)
        if not p.exists():
            print(f"skip {p}: missing")
            continue
        h = json.loads(p.read_text())
        ep = h["epoch"]
        axR.plot(ep, h["f1"], color=color, linestyle=ls, label=label, linewidth=2)

    # Encoder-unfreeze boundary (epoch 3) — only relevant for matched-LR runs
    axR.axvline(3.5, color="gray", linestyle=":", linewidth=1)
    axR.text(3.6, 0.07, "encoder\nunfrozen\n(matched LR)", fontsize=8, color="gray", va="bottom")
    axR.set_xlabel("Fine-tune epoch")
    axR.set_ylabel("Training F1 (on the 2 fine-tune maps)")
    axR.set_title("(b) USGS 2-map fine-tune from each init")
    axR.grid(True, alpha=0.3)
    axR.set_xlim(0.5, 20.5)
    axR.set_ylim(0, 0.75)
    axR.legend(loc="lower right", fontsize=9)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
