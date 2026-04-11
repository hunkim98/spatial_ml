"""Entry point for LOAM-aligned zone segmentation training.

LOAM-aligned parameters (vs baseline):
    - 1024x1024 input (was 256)
    - Batch size 2 (was 32)
    - SGD with momentum 0.999 (was AdamW)
    - LR 1e-5 (was 1e-4)
    - Weight decay 1e-8 (was 1e-4)
    - 40 epochs (was 15)
    - Dice-only loss (was BCE+Dice)
    - 5% min coverage filter (was none)

Usage:
    python -m model.zone_segmentation.train_loam \
        --data data/training/zoning_segmentation
"""

import argparse
import logging
import os
import sys

import torch

from .dataset import StratificationConfig, get_dataloaders
from .trainer_loam import TrainerLOAM
from .unet import PatternConditionedUNet


def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main():
    parser = argparse.ArgumentParser(description="Train zone segmentation (LOAM-aligned)")
    parser.add_argument("--data", required=True, help="Path to dataset root")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--image-size", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=1e-5)
    parser.add_argument("--momentum", type=float, default=0.999)
    parser.add_argument("--weight-decay", type=float, default=1e-8)
    parser.add_argument("--min-coverage", type=float, default=0.05,
                        help="Min fraction of positive pixels per zone (default 0.05 = 5%%)")
    parser.add_argument("--device", default=_pick_device())
    parser.add_argument("--save-dir", default="checkpoints/zone_seg_loam")
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--no-wandb", action="store_true")
    parser.add_argument("--wandb-project", default="spatially-zone-segmentation")
    parser.add_argument("--no-stratify", action="store_true")
    parser.add_argument("--val-fraction", type=float, default=0.15)
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
    print("Zone Segmentation Training (LOAM-aligned)")
    print("=" * 80)
    print(f"Dataset:      {args.data}")
    print(f"Device:       {args.device}")
    print(f"Epochs:       {args.epochs}")
    print(f"Batch size:   {args.batch_size}")
    print(f"Image size:   {args.image_size}")
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
    train_loader, val_loader = get_dataloaders(
        root=args.data,
        image_size=(args.image_size, args.image_size),
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        stratification=strat_config,
    )
    logger.info(
        f"Train: {len(train_loader.dataset)} pairs, "
        f"Val: {len(val_loader.dataset)} pairs"
    )

    # Model
    model = PatternConditionedUNet(pretrained=True)
    n_params = sum(p.numel() for p in model.parameters()) / 1e6
    logger.info(f"Model: PatternConditionedUNet ({n_params:.1f}M params)")

    # Train
    trainer = TrainerLOAM(
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
        },
    )
    trainer.train()

    print("\n" + "=" * 80)
    print("Training completed (LOAM-aligned).")
    print(f"Best checkpoint: {args.save_dir}/best.pt")
    if use_wandb:
        print("View results at: https://wandb.ai")
    print("=" * 80)


if __name__ == "__main__":
    main()
