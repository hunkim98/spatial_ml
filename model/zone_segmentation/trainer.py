"""Training loop for the pattern-conditioned U-Net."""

import logging
import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from .losses import BCEDiceLoss
from .metrics import dice_score, iou_score

logger = logging.getLogger(__name__)


class Trainer:
    """Trains and evaluates the pattern-conditioned U-Net."""

    def __init__(
        self,
        model: nn.Module,
        train_loader,
        val_loader,
        lr: float = 1e-4,
        weight_decay: float = 1e-4,
        epochs: int = 50,
        device: str = "cuda",
        save_dir: str = "checkpoints",
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.epochs = epochs
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.criterion = BCEDiceLoss()
        self.optimizer = AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
        self.scheduler = CosineAnnealingLR(self.optimizer, T_max=epochs)

        self.best_iou = 0.0

    def train_one_epoch(self, epoch: int) -> dict:
        self.model.train()
        total_loss = 0
        total_iou = 0
        n_batches = 0

        for batch_idx, (images, patterns, masks) in enumerate(self.train_loader):
            images = images.to(self.device)
            patterns = patterns.to(self.device)
            masks = masks.to(self.device)

            self.optimizer.zero_grad()
            logits = self.model(images, patterns)
            loss = self.criterion(logits, masks)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            total_iou += iou_score(logits.detach(), masks)
            n_batches += 1

            if batch_idx % 50 == 0:
                logger.info(
                    f"Epoch {epoch} [{batch_idx}/{len(self.train_loader)}] "
                    f"loss={loss.item():.4f}"
                )

        return {
            "train_loss": total_loss / max(1, n_batches),
            "train_iou": total_iou / max(1, n_batches),
        }

    @torch.no_grad()
    def validate(self) -> dict:
        self.model.eval()
        total_loss = 0
        total_iou = 0
        total_dice = 0
        n_batches = 0

        for images, patterns, masks in self.val_loader:
            images = images.to(self.device)
            patterns = patterns.to(self.device)
            masks = masks.to(self.device)

            logits = self.model(images, patterns)
            loss = self.criterion(logits, masks)

            total_loss += loss.item()
            total_iou += iou_score(logits, masks)
            total_dice += dice_score(logits, masks)
            n_batches += 1

        return {
            "val_loss": total_loss / max(1, n_batches),
            "val_iou": total_iou / max(1, n_batches),
            "val_dice": total_dice / max(1, n_batches),
        }

    def train(self):
        """Full training loop."""
        logger.info(
            f"Training: {self.epochs} epochs, "
            f"{len(self.train_loader)} train batches, "
            f"{len(self.val_loader)} val batches"
        )

        for epoch in range(1, self.epochs + 1):
            start = time.time()

            train_metrics = self.train_one_epoch(epoch)
            val_metrics = self.validate()
            self.scheduler.step()

            elapsed = time.time() - start
            lr = self.optimizer.param_groups[0]["lr"]

            logger.info(
                f"Epoch {epoch}/{self.epochs} ({elapsed:.0f}s) lr={lr:.6f} | "
                f"train_loss={train_metrics['train_loss']:.4f} "
                f"train_iou={train_metrics['train_iou']:.4f} | "
                f"val_loss={val_metrics['val_loss']:.4f} "
                f"val_iou={val_metrics['val_iou']:.4f} "
                f"val_dice={val_metrics['val_dice']:.4f}"
            )

            # Save best model
            if val_metrics["val_iou"] > self.best_iou:
                self.best_iou = val_metrics["val_iou"]
                torch.save(self.model.state_dict(), self.save_dir / "best.pt")
                logger.info(f"  New best IoU: {self.best_iou:.4f}")

            # Save periodic checkpoint
            if epoch % 10 == 0:
                torch.save({
                    "epoch": epoch,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "best_iou": self.best_iou,
                }, self.save_dir / f"checkpoint_epoch{epoch}.pt")

        # Save final model
        torch.save(self.model.state_dict(), self.save_dir / "final.pt")
        logger.info(f"Training complete. Best IoU: {self.best_iou:.4f}")
