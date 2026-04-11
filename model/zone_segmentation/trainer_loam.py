"""LOAM-aligned training loop for the pattern-conditioned U-Net.

Differences from trainer.py (baseline):
    - SGD optimizer (momentum=0.999) instead of AdamW
    - Dice-only loss instead of BCE+Dice
    - Default lr=1e-5, weight_decay=1e-8, epochs=40
    - Everything else (AMP, grad clip, W&B, checkpointing) unchanged

Reference: Lin et al., "Exploiting Polygon Metadata to Understand Raster
Maps" (SIGSPATIAL '23)
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn
from torch.optim import SGD
from torch.optim.lr_scheduler import CosineAnnealingLR

from .losses import DiceLoss
from .metrics import dice_score, iou_score, precision_recall_f1

logger = logging.getLogger(__name__)


class TrainerLOAM:
    """Trains and evaluates the pattern-conditioned U-Net with LOAM-aligned params."""

    def __init__(
        self,
        model: nn.Module,
        train_loader,
        val_loader,
        lr: float = 1e-5,
        weight_decay: float = 1e-8,
        momentum: float = 0.999,
        epochs: int = 40,
        device: str = "cuda",
        save_dir: str = "checkpoints",
        grad_clip: float = 1.0,
        use_amp: bool | None = None,
        log_every: int = 10,
        sample_log_every: int = 2,
        wandb_project: str = "spatially-zone-segmentation",
        wandb_run_name: str | None = None,
        wandb_config: dict | None = None,
        use_wandb: bool | None = None,
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.epochs = epochs
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.grad_clip = grad_clip
        self.log_every = log_every
        self.sample_log_every = sample_log_every

        self.criterion = DiceLoss()
        self.optimizer = SGD(
            model.parameters(), lr=lr,
            weight_decay=weight_decay, momentum=momentum,
        )
        self.scheduler = CosineAnnealingLR(self.optimizer, T_max=max(1, epochs))

        # Mixed precision: default on for CUDA, off elsewhere
        if use_amp is None:
            use_amp = device == "cuda"
        self.use_amp = use_amp
        self.scaler = torch.amp.GradScaler("cuda", enabled=self.use_amp and device == "cuda")

        self.best_iou = 0.0
        self.global_step = 0
        self.history: dict[str, list] = {
            "epoch": [],
            "train_loss": [],
            "train_iou": [],
            "val_loss": [],
            "val_iou": [],
            "val_dice": [],
            "val_f1": [],
            "lr": [],
        }

        # W&B setup
        wandb_api_key = os.environ.get("WANDB_API_KEY")
        if use_wandb is None:
            use_wandb = bool(wandb_api_key)
        self.use_wandb = use_wandb
        self.wandb_run = None
        if self.use_wandb:
            if not wandb_api_key:
                raise ValueError(
                    "use_wandb=True but WANDB_API_KEY is not set. "
                    "Export it (e.g. via secrets/teamspatially-project.env) "
                    "or pass use_wandb=False."
                )
            try:
                import wandb  # noqa: F401

                masked = wandb_api_key[:4] + "…" + wandb_api_key[-4:] if len(wandb_api_key) > 8 else "***"
                logger.info(f"WANDB_API_KEY loaded ({masked})")

                self._init_wandb(
                    project=wandb_project,
                    run_name=wandb_run_name,
                    extra_config=wandb_config or {},
                    lr=lr,
                    weight_decay=weight_decay,
                    momentum=momentum,
                )
            except ImportError:
                logger.warning("wandb not installed — falling back to offline logging only.")
                self.use_wandb = False

    # ------------------------------------------------------------------ wandb
    def _init_wandb(self, project, run_name, extra_config, lr, weight_decay, momentum):
        import wandb

        if run_name is None:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            bs = self.train_loader.batch_size
            run_name = f"unet-film-loam-e{self.epochs}-bs{bs}-{ts}"

        config = {
            "model": "PatternConditionedUNet",
            "variant": "loam-aligned",
            "epochs": self.epochs,
            "batch_size": self.train_loader.batch_size,
            "learning_rate": lr,
            "weight_decay": weight_decay,
            "optimizer": "SGD",
            "momentum": momentum,
            "loss": "DiceLoss",
            "grad_clip": self.grad_clip,
            "amp": self.use_amp,
            "device": str(self.device),
            "train_size": len(self.train_loader.dataset),
            "val_size": len(self.val_loader.dataset),
            "n_params_m": sum(p.numel() for p in self.model.parameters()) / 1e6,
            **extra_config,
        }

        self.wandb_run = wandb.init(
            project=project,
            name=run_name,
            config=config,
            tags=["zone-segmentation", "unet", "film", "loam-aligned", "spatially"],
        )
        wandb.log(
            {
                "dataset/train_examples": len(self.train_loader.dataset),
                "dataset/val_examples": len(self.val_loader.dataset),
            }
        )
        logger.info(f"W&B run started: {run_name} (project={project})")

    def _wandb_log(self, payload: dict, step: int | None = None):
        if not self.use_wandb or self.wandb_run is None:
            return
        import wandb

        wandb.log(payload, step=step)

    # ----------------------------------------------------------------- epochs
    def train_one_epoch(self, epoch: int) -> dict:
        self.model.train()
        total_loss = 0.0
        total_iou = 0.0
        n_batches = 0

        for batch_idx, (images, patterns, masks) in enumerate(self.train_loader):
            images = images.to(self.device, non_blocking=True)
            patterns = patterns.to(self.device, non_blocking=True)
            masks = masks.to(self.device, non_blocking=True)

            self.optimizer.zero_grad(set_to_none=True)

            with torch.amp.autocast(
                device_type="cuda" if self.device == "cuda" else "cpu",
                enabled=self.use_amp,
            ):
                logits = self.model(images, patterns)
                loss = self.criterion(logits, masks)

            if self.scaler.is_enabled():
                self.scaler.scale(loss).backward()
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
                self.optimizer.step()

            total_loss += loss.item()
            total_iou += iou_score(logits.detach(), masks)
            n_batches += 1
            self.global_step += 1

            if batch_idx % self.log_every == 0:
                logger.info(
                    f"Epoch {epoch} [{batch_idx}/{len(self.train_loader)}] "
                    f"loss={loss.item():.4f}"
                )
                self._wandb_log(
                    {
                        "train/batch_loss": loss.item(),
                        "train/global_step": self.global_step,
                    },
                    step=self.global_step,
                )

        return {
            "train_loss": total_loss / max(1, n_batches),
            "train_iou": total_iou / max(1, n_batches),
        }

    @torch.no_grad()
    def validate(self) -> dict:
        self.model.eval()
        total_loss = 0.0
        total_iou = 0.0
        total_dice = 0.0
        total_f1 = 0.0
        n_batches = 0

        for images, patterns, masks in self.val_loader:
            images = images.to(self.device, non_blocking=True)
            patterns = patterns.to(self.device, non_blocking=True)
            masks = masks.to(self.device, non_blocking=True)

            logits = self.model(images, patterns)
            loss = self.criterion(logits, masks)
            _, _, f1 = precision_recall_f1(logits, masks)

            total_loss += loss.item()
            total_iou += iou_score(logits, masks)
            total_dice += dice_score(logits, masks)
            total_f1 += f1
            n_batches += 1

        return {
            "val_loss": total_loss / max(1, n_batches),
            "val_iou": total_iou / max(1, n_batches),
            "val_dice": total_dice / max(1, n_batches),
            "val_f1": total_f1 / max(1, n_batches),
        }

    # -------------------------------------------------------------- snapshots
    def _log_prediction_samples(self, epoch: int):
        """Save a prediction grid figure to disk and log it to W&B if active."""
        try:
            from .viz import make_prediction_grid
        except Exception as exc:  # matplotlib missing, etc.
            logger.warning(f"Skipping prediction snapshot ({exc})")
            return

        fig = make_prediction_grid(self.model, self.val_loader, self.device, n=4)
        out_dir = self.save_dir / "samples"
        out_dir.mkdir(exist_ok=True)
        path = out_dir / f"epoch_{epoch:03d}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight")

        if self.use_wandb and self.wandb_run is not None:
            import wandb

            self._wandb_log({"val/predictions": wandb.Image(str(path))}, step=self.global_step)

        import matplotlib.pyplot as plt

        plt.close(fig)

    # ------------------------------------------------------------------ main
    def train(self) -> dict:
        """Full training loop. Returns the per-epoch history dict."""
        logger.info(
            f"Training (LOAM-aligned): {self.epochs} epochs, "
            f"{len(self.train_loader)} train batches, "
            f"{len(self.val_loader)} val batches, "
            f"amp={self.use_amp}, wandb={self.use_wandb}"
        )

        for epoch in range(1, self.epochs + 1):
            # Update batch sampler RNG so each epoch gets a different ordering
            if hasattr(self.train_loader, "batch_sampler") and hasattr(
                self.train_loader.batch_sampler, "set_epoch"
            ):
                self.train_loader.batch_sampler.set_epoch(epoch)

            start = time.time()

            train_metrics = self.train_one_epoch(epoch)
            val_metrics = self.validate()
            self.scheduler.step()

            elapsed = time.time() - start
            lr = self.optimizer.param_groups[0]["lr"]

            self.history["epoch"].append(epoch)
            self.history["train_loss"].append(train_metrics["train_loss"])
            self.history["train_iou"].append(train_metrics["train_iou"])
            self.history["val_loss"].append(val_metrics["val_loss"])
            self.history["val_iou"].append(val_metrics["val_iou"])
            self.history["val_dice"].append(val_metrics["val_dice"])
            self.history["val_f1"].append(val_metrics["val_f1"])
            self.history["lr"].append(lr)

            logger.info(
                f"Epoch {epoch}/{self.epochs} ({elapsed:.0f}s) lr={lr:.6f} | "
                f"train_loss={train_metrics['train_loss']:.4f} "
                f"train_iou={train_metrics['train_iou']:.4f} | "
                f"val_loss={val_metrics['val_loss']:.4f} "
                f"val_iou={val_metrics['val_iou']:.4f} "
                f"val_dice={val_metrics['val_dice']:.4f} "
                f"val_f1={val_metrics['val_f1']:.4f}"
            )

            self._wandb_log(
                {
                    "train/epoch_loss": train_metrics["train_loss"],
                    "train/epoch_iou": train_metrics["train_iou"],
                    "val/epoch_loss": val_metrics["val_loss"],
                    "val/iou": val_metrics["val_iou"],
                    "val/dice": val_metrics["val_dice"],
                    "val/f1": val_metrics["val_f1"],
                    "train/lr": lr,
                    "epoch": epoch,
                    "epoch/elapsed_s": elapsed,
                },
                step=self.global_step,
            )

            # Save best model
            if val_metrics["val_iou"] > self.best_iou:
                self.best_iou = val_metrics["val_iou"]
                torch.save(self.model.state_dict(), self.save_dir / "best.pt")
                logger.info(f"  New best IoU: {self.best_iou:.4f}")

            # Save periodic checkpoint
            if epoch % 10 == 0:
                torch.save(
                    {
                        "epoch": epoch,
                        "model_state_dict": self.model.state_dict(),
                        "optimizer_state_dict": self.optimizer.state_dict(),
                        "best_iou": self.best_iou,
                    },
                    self.save_dir / f"checkpoint_epoch{epoch}.pt",
                )

            # Periodic prediction snapshots
            if self.sample_log_every and epoch % self.sample_log_every == 0:
                self._log_prediction_samples(epoch)

            # Persist history every epoch so plots survive crashes
            with open(self.save_dir / "history.json", "w") as f:
                json.dump(self.history, f, indent=2)

        # Save final model
        torch.save(self.model.state_dict(), self.save_dir / "final.pt")
        logger.info(f"Training complete. Best IoU: {self.best_iou:.4f}")

        # Final snapshot + W&B model artifact
        self._log_prediction_samples(self.epochs)
        if self.use_wandb and self.wandb_run is not None:
            import wandb

            artifact = wandb.Artifact(
                name="zone-segmentation-model-loam",
                type="model",
                description=f"PatternConditionedUNet (LOAM-aligned) best_iou={self.best_iou:.4f}",
            )
            artifact.add_file(str(self.save_dir / "best.pt"))
            artifact.add_file(str(self.save_dir / "history.json"))
            wandb.log_artifact(artifact)
            wandb.finish()

        return self.history
