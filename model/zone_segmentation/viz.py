"""Visualization helpers for the zone segmentation model.

Reusable plotting functions used by both the training loop (for W&B logging
and on-disk artifacts) and the demo notebook.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

# ImageNet normalization stats — must match dataset.py
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def denormalize(tensor: torch.Tensor) -> np.ndarray:
    """Undo ImageNet normalization. (C, H, W) → (H, W, C) uint8-like float in [0, 1]."""
    arr = tensor.detach().cpu().numpy().transpose(1, 2, 0)
    arr = arr * IMAGENET_STD + IMAGENET_MEAN
    return np.clip(arr, 0.0, 1.0)


def plot_dataset_samples(dataset, n: int = 6, seed: int = 0):
    """Plot a grid of (image, pattern, mask) triplets from a dataset.

    Returns the matplotlib figure.
    """
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(seed)
    indices = rng.choice(len(dataset), size=min(n, len(dataset)), replace=False)

    fig, axes = plt.subplots(len(indices), 3, figsize=(9, 3 * len(indices)))
    if len(indices) == 1:
        axes = axes[None, :]

    for row, idx in enumerate(indices):
        image, pattern, mask = dataset[int(idx)]
        axes[row, 0].imshow(denormalize(image))
        axes[row, 0].set_title(f"image #{idx}")
        axes[row, 0].axis("off")

        axes[row, 1].imshow(denormalize(pattern))
        axes[row, 1].set_title("pattern (32×32)")
        axes[row, 1].axis("off")

        axes[row, 2].imshow(mask.squeeze().cpu().numpy(), cmap="gray", vmin=0, vmax=1)
        axes[row, 2].set_title("ground-truth mask")
        axes[row, 2].axis("off")

    fig.tight_layout()
    return fig


def make_prediction_grid(
    model,
    loader,
    device: str,
    n: int = 8,
    threshold: float = 0.5,
):
    """Build a matplotlib figure with image / pattern / GT / pred / overlay columns.

    Samples from spread-out batches so the grid shows diverse sources,
    not just consecutive items from one batch.

    Returns the matplotlib figure. Caller is responsible for closing it.
    """
    import matplotlib.pyplot as plt

    was_training = model.training
    model.eval()

    # Pick n evenly-spaced batches so we see different sources
    n_batches = len(loader)
    if n_batches == 0:
        model.train(was_training)
        fig, ax = plt.subplots(1, 1, figsize=(4, 2))
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    step = max(1, n_batches // n)
    target_indices = set(range(0, n_batches, step))

    rows = []
    with torch.no_grad():
        for batch_idx, (images, patterns, masks) in enumerate(loader):
            if batch_idx not in target_indices:
                continue

            images = images.to(device)
            patterns = patterns.to(device)
            logits = model(images, patterns)
            probs = torch.sigmoid(logits).cpu()
            preds = (probs > threshold).float()

            # Take one sample from each selected batch
            rows.append(
                {
                    "image": denormalize(images[0]),
                    "pattern": denormalize(patterns[0]),
                    "mask": masks[0].squeeze().cpu().numpy(),
                    "prob": probs[0].squeeze().cpu().numpy(),
                    "pred": preds[0].squeeze().cpu().numpy(),
                }
            )
            if len(rows) >= n:
                break

    if was_training:
        model.train()

    fig, axes = plt.subplots(len(rows), 5, figsize=(15, 3 * len(rows)))
    if len(rows) == 1:
        axes = axes[None, :]

    for r, row in enumerate(rows):
        axes[r, 0].imshow(row["image"])
        axes[r, 0].set_title("image")
        axes[r, 1].imshow(row["pattern"])
        axes[r, 1].set_title("pattern")
        axes[r, 2].imshow(row["mask"], cmap="gray", vmin=0, vmax=1)
        axes[r, 2].set_title("ground truth")
        axes[r, 3].imshow(row["prob"], cmap="viridis", vmin=0, vmax=1)
        axes[r, 3].set_title("predicted prob")
        # Overlay: image with red prediction mask
        overlay = row["image"].copy()
        red = np.zeros_like(overlay)
        red[..., 0] = 1.0
        alpha = 0.45 * row["pred"][..., None]
        overlay = overlay * (1 - alpha) + red * alpha
        axes[r, 4].imshow(np.clip(overlay, 0, 1))
        axes[r, 4].set_title("overlay")
        for c in range(5):
            axes[r, c].axis("off")

    fig.tight_layout()
    return fig


def make_prediction_grid_context(
    model,
    loader,
    device: str,
    n: int = 8,
    threshold: float = 0.5,
):
    """Like make_prediction_grid but for context-aware models (4-tuple batches).

    Expects loader to yield (images, patterns, legends, masks).
    Adds a legend column to the grid.
    """
    import matplotlib.pyplot as plt

    was_training = model.training
    model.eval()

    n_batches = len(loader)
    if n_batches == 0:
        model.train(was_training)
        fig, ax = plt.subplots(1, 1, figsize=(4, 2))
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    step = max(1, n_batches // n)
    target_indices = set(range(0, n_batches, step))

    rows = []
    with torch.no_grad():
        for batch_idx, (images, patterns, legends, masks) in enumerate(loader):
            if batch_idx not in target_indices:
                continue

            images = images.to(device)
            patterns = patterns.to(device)
            legends = legends.to(device)
            logits = model(images, patterns, legends)
            probs = torch.sigmoid(logits).cpu()
            preds = (probs > threshold).float()

            rows.append(
                {
                    "image": denormalize(images[0]),
                    "pattern": denormalize(patterns[0]),
                    "legend": denormalize(legends[0]),
                    "mask": masks[0].squeeze().cpu().numpy(),
                    "prob": probs[0].squeeze().cpu().numpy(),
                    "pred": preds[0].squeeze().cpu().numpy(),
                }
            )
            if len(rows) >= n:
                break

    if was_training:
        model.train()

    fig, axes = plt.subplots(len(rows), 6, figsize=(18, 3 * len(rows)))
    if len(rows) == 1:
        axes = axes[None, :]

    for r, row in enumerate(rows):
        axes[r, 0].imshow(row["image"])
        axes[r, 0].set_title("image")
        axes[r, 1].imshow(row["pattern"])
        axes[r, 1].set_title("pattern")
        axes[r, 2].imshow(row["legend"])
        axes[r, 2].set_title("legend")
        axes[r, 3].imshow(row["mask"], cmap="gray", vmin=0, vmax=1)
        axes[r, 3].set_title("ground truth")
        axes[r, 4].imshow(row["prob"], cmap="viridis", vmin=0, vmax=1)
        axes[r, 4].set_title("predicted prob")
        overlay = row["image"].copy()
        red = np.zeros_like(overlay)
        red[..., 0] = 1.0
        alpha = 0.45 * row["pred"][..., None]
        overlay = overlay * (1 - alpha) + red * alpha
        axes[r, 5].imshow(np.clip(overlay, 0, 1))
        axes[r, 5].set_title("overlay")
        for c in range(6):
            axes[r, c].axis("off")

    fig.tight_layout()
    return fig


def plot_history(history: dict, save_path: str | Path | None = None):
    """Plot loss / IoU / Dice curves from a Trainer history dict.

    history schema:
        {
            "epoch": [1, 2, ...],
            "train_loss": [...], "val_loss": [...],
            "train_iou": [...], "val_iou": [...],
            "val_dice": [...], "val_f1": [...],
            "lr": [...],
        }
    """
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    epochs = history["epoch"]

    axes[0].plot(epochs, history["train_loss"], label="train", marker="o")
    axes[0].plot(epochs, history["val_loss"], label="val", marker="o")
    axes[0].set_xlabel("epoch")
    axes[0].set_ylabel("loss")
    axes[0].set_title("Loss")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(epochs, history["train_iou"], label="train IoU", marker="o")
    axes[1].plot(epochs, history["val_iou"], label="val IoU", marker="o")
    if "val_dice" in history:
        axes[1].plot(epochs, history["val_dice"], label="val Dice", marker="o")
    axes[1].set_xlabel("epoch")
    axes[1].set_ylabel("score")
    axes[1].set_title("Segmentation metrics")
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    axes[1].set_ylim(0, 1)

    if "lr" in history:
        axes[2].plot(epochs, history["lr"], marker="o", color="C2")
        axes[2].set_xlabel("epoch")
        axes[2].set_ylabel("learning rate")
        axes[2].set_title("LR schedule")
        axes[2].grid(alpha=0.3)

    fig.tight_layout()
    if save_path is not None:
        fig.savefig(save_path, dpi=120, bbox_inches="tight")
    return fig
