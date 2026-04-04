"""Entry point for training the zone segmentation model.

Usage:
    python -m model.zone_segmentation.train \
        --data data/training/zoning_segmentation \
        --epochs 50 \
        --batch-size 4 \
        --image-size 512
"""

import argparse
import logging

import torch

from .dataset import get_dataloaders
from .trainer import Trainer
from .unet import PatternConditionedUNet


def main():
    parser = argparse.ArgumentParser(description="Train zone segmentation model")
    parser.add_argument("--data", required=True, help="Path to dataset root")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--save-dir", default="checkpoints/zone_segmentation")
    parser.add_argument("--num-workers", type=int, default=4)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info(f"Device: {args.device}")
    logger.info(f"Dataset: {args.data}")

    # Data
    train_loader, val_loader = get_dataloaders(
        root=args.data,
        image_size=(args.image_size, args.image_size),
        batch_size=args.batch_size,
        num_workers=args.num_workers,
    )
    logger.info(f"Train: {len(train_loader.dataset)} pairs, Val: {len(val_loader.dataset)} pairs")

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
    )
    trainer.train()


if __name__ == "__main__":
    main()
