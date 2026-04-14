"""Entry point for training the zone segmentation model.

Usage (local):
    python -m model.zone_segmentation.scripts.train \
        --data data/training/zoning_segmentation \
        --epochs 50 \
        --batch-size 4 \
        --image-size 512

Inside Docker (with secrets/teamspatially-project.env mounted):
    docker compose run --rm zone_segmentation_trainer \
        python -m model.zone_segmentation.train --data /data/training/zoning_segmentation --epochs 5
"""

import argparse
import logging
import os
import sys

import torch

from ..dataset import StratificationConfig, get_dataloaders
from ..trainer import Trainer
from ..unet import PatternConditionedUNet


def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def main():
    parser = argparse.ArgumentParser(description="Train zone segmentation model")
    parser.add_argument("--data", required=True, help="Path to dataset root")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--device", default=_pick_device())
    parser.add_argument("--save-dir", default="checkpoints/zone_segmentation")
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument(
        "--no-wandb",
        action="store_true",
        help="Disable W&B even if WANDB_API_KEY is set",
    )
    parser.add_argument(
        "--wandb-project",
        default="spatially-zone-segmentation",
        help="W&B project name",
    )
    parser.add_argument(
        "--no-stratify",
        action="store_true",
        help="Disable stratified batch sampling (use standard shuffle)",
    )
    parser.add_argument(
        "--val-fraction", type=float, default=0.05,
        help="Fraction of source GeoJSONs to hold out for validation",
    )
    args = parser.parse_args()

    # Send logs to stdout (matches ac215_Spatially convention so GCP doesn't flag them as errors).
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
    print("Zone Segmentation Training")
    print("=" * 80)
    print(f"Dataset:    {args.data}")
    print(f"Device:     {args.device}")
    print(f"Epochs:     {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Image size: {args.image_size}")
    print(f"LR:         {args.lr}")
    print(f"Save dir:   {args.save_dir}")
    print(f"W&B:        {'enabled (' + args.wandb_project + ')' if use_wandb else 'disabled'}")
    if not has_wandb_key:
        print("            (set WANDB_API_KEY in env or via secrets/*.env to enable)")
    print(f"Stratified: {'disabled' if args.no_stratify else 'enabled'}")
    print(f"Val frac:   {args.val_fraction}")
    print("=" * 80)

    # Data
    strat_config = StratificationConfig(
        val_fraction=args.val_fraction,
        use_stratified_batches=not args.no_stratify,
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
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        lr=args.lr,
        epochs=args.epochs,
        device=args.device,
        save_dir=args.save_dir,
        use_wandb=use_wandb,
        wandb_project=args.wandb_project,
        wandb_config={"image_size": args.image_size},
    )
    trainer.train()

    print("\n" + "=" * 80)
    print("Training completed.")
    print(f"Best checkpoint: {args.save_dir}/best.pt")
    if use_wandb:
        print("View results at: https://wandb.ai")
    print("=" * 80)


if __name__ == "__main__":
    main()
