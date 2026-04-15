"""Entry point for context-aware zone segmentation training.

Uses ContextUNet — vanilla U-Net conditioned on both the target pattern
AND a legend grid image showing ALL patterns for the map.

Usage:
    python -m model.zone_segmentation.train_loam_context \
        --data data/training/zoning_segmentation
"""

import argparse
import logging
import os
import sys

import torch

from ..dataset import StratificationConfig
from ..dataset_context import get_context_dataloaders
from ..trainer_context import TrainerContext
from ..unet_context import ContextUNet


def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main():
    parser = argparse.ArgumentParser(description="Train zone segmentation (context-aware)")
    parser.add_argument("--data", required=True, help="Path to dataset root")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--image-size", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--momentum", type=float, default=0.999)
    parser.add_argument("--weight-decay", type=float, default=1e-8)
    parser.add_argument("--min-coverage", type=float, default=0.005)
    parser.add_argument("--legend-size", type=int, default=128)
    parser.add_argument("--device", default=_pick_device())
    parser.add_argument("--save-dir", default="checkpoints/zone_seg_context")
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--no-wandb", action="store_true")
    parser.add_argument("--wandb-project", default="spatially-zone-segmentation")
    parser.add_argument("--no-stratify", action="store_true")
    parser.add_argument("--val-fraction", type=float, default=0.05)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    sys.stderr = sys.stdout
    logger = logging.getLogger(__name__)

    has_wandb_key = bool(os.environ.get("WANDB_API_KEY"))
    use_wandb = (not args.no_wandb) and has_wandb_key

    print("=" * 80)
    print("Zone Segmentation Training (Context-Aware)")
    print("=" * 80)
    print(f"Dataset:      {args.data}")
    print(f"Device:       {args.device}")
    print(f"Model:        ContextUNet (vanilla + legend encoder)")
    print(f"Epochs:       {args.epochs}")
    print(f"Batch size:   {args.batch_size}")
    print(f"Image size:   {args.image_size}")
    print(f"Legend size:   {args.legend_size}")
    print(f"Optimizer:    SGD (momentum={args.momentum})")
    print(f"LR:           {args.lr}")
    print(f"Weight decay: {args.weight_decay}")
    print(f"Loss:         Dice only")
    print(f"Min coverage: {args.min_coverage:.1%}")
    print(f"Save dir:     {args.save_dir}")
    print(f"W&B:          {'enabled (' + args.wandb_project + ')' if use_wandb else 'disabled'}")
    if not has_wandb_key:
        print("              (set WANDB_API_KEY in env or via secrets/*.env to enable)")
    print(f"Stratified:   {'disabled' if args.no_stratify else 'enabled'}")
    print(f"Val frac:     {args.val_fraction}")
    print("=" * 80)

    # Data
    strat_config = StratificationConfig(
        val_fraction=args.val_fraction,
        use_stratified_batches=not args.no_stratify,
        min_coverage=args.min_coverage,
    )
    train_loader, val_loader = get_context_dataloaders(
        root=args.data,
        image_size=(args.image_size, args.image_size),
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        stratification=strat_config,
        legend_size=args.legend_size,
    )
    logger.info(
        f"Train: {len(train_loader.dataset)} pairs, "
        f"Val: {len(val_loader.dataset)} pairs"
    )

    # Model
    model = ContextUNet()
    n_params = sum(p.numel() for p in model.parameters()) / 1e6
    logger.info(f"Model: ContextUNet ({n_params:.1f}M params)")

    # Train
    trainer = TrainerContext(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        lr=args.lr,
        weight_decay=args.weight_decay,
        momentum=args.momentum,
        epochs=args.epochs,
        device=args.device,
        save_dir=args.save_dir,
        use_wandb=use_wandb,
        wandb_project=args.wandb_project,
        wandb_config={
            "image_size": args.image_size,
            "min_coverage": args.min_coverage,
            "legend_size": args.legend_size,
        },
    )
    trainer.train()

    print("\n" + "=" * 80)
    print("Training completed (context-aware).")
    print(f"Best checkpoint: {args.save_dir}/best.pt")
    if use_wandb:
        print("View results at: https://wandb.ai")
    print("=" * 80)


if __name__ == "__main__":
    main()
