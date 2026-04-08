"""Smoke-test the PatternConditionedUNet against the zoning_segmentation dataset.

Loads a handful of (image, pattern, mask) triplets, runs a forward pass,
computes a BCE loss, and does one backward step. Verifies that data and
model are wired up correctly without running a full training job.

Usage:
    python -m model.zone_segmentation.run \
        --data data/training/zoning_segmentation \
        --batch-size 2 --image-size 256 --num-batches 2
"""

import argparse
import logging

import torch
import torch.nn.functional as F

from .dataset import get_dataloaders
from .unet import PatternConditionedUNet


def main():
    parser = argparse.ArgumentParser(description="UNet smoke test")
    parser.add_argument("--data", default="data/training/zoning_segmentation")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--image-size", type=int, default=256)
    parser.add_argument("--num-batches", type=int, default=2)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--no-pretrained", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("smoke")

    log.info(f"Device: {args.device}")
    log.info(f"Dataset root: {args.data}")

    train_loader, val_loader = get_dataloaders(
        root=args.data,
        image_size=(args.image_size, args.image_size),
        batch_size=args.batch_size,
        num_workers=args.num_workers,
    )
    log.info(
        f"Train pairs: {len(train_loader.dataset)} | "
        f"Val pairs: {len(val_loader.dataset)}"
    )

    model = PatternConditionedUNet(pretrained=not args.no_pretrained).to(args.device)
    n_params = sum(p.numel() for p in model.parameters()) / 1e6
    log.info(f"Model loaded: PatternConditionedUNet ({n_params:.1f}M params)")

    optim = torch.optim.Adam(model.parameters(), lr=1e-4)

    model.train()
    for i, (image, pattern, mask) in enumerate(train_loader):
        if i >= args.num_batches:
            break
        image = image.to(args.device)
        pattern = pattern.to(args.device)
        mask = mask.to(args.device)

        logits = model(image, pattern)
        loss = F.binary_cross_entropy_with_logits(logits, mask)

        optim.zero_grad()
        loss.backward()
        optim.step()

        log.info(
            f"[batch {i}] image={tuple(image.shape)} pattern={tuple(pattern.shape)} "
            f"mask={tuple(mask.shape)} logits={tuple(logits.shape)} loss={loss.item():.4f}"
        )

    # Quick eval pass on one val batch
    model.eval()
    with torch.no_grad():
        for image, pattern, mask in val_loader:
            image = image.to(args.device)
            pattern = pattern.to(args.device)
            mask = mask.to(args.device)
            logits = model(image, pattern)
            val_loss = F.binary_cross_entropy_with_logits(logits, mask)
            log.info(f"[val] loss={val_loss.item():.4f}")
            break

    log.info("Smoke test passed.")


if __name__ == "__main__":
    main()
